import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from automation.classifiers import GeminiClassifier, ManualClassifier, OpenAIClassifier, SCHEMA
from automation.domain import Classification, ConfigurationError, InputError, Message, ProviderError, Topic, load_messages
from automation.http_client import HttpError, JsonClient
from automation.orders import OrderClient, extract_order_ids
from automation.service import MessageService
import main


APP_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = APP_DIR.parent


def classification(topic="siparis_durumu", secondary=None, spam=False):
    return {"topic": topic, "secondary_topics": secondary or [], "is_spam": spam}


def response(status=200, body=None):
    result = Mock(status_code=status, headers={})
    result.json.return_value = body
    return result


def owned_cart():
    return {"id": 3, "userId": 3, "products": [{"title": "Test product", "quantity": 2}], "total": 125.50}


class ClassificationTests(unittest.TestCase):
    def test_secondary_sensitive_topic_overrides_order_and_spam_cannot_hide_it(self):
        result = Classification.parse(classification(secondary=["hassas_konu", "fiyat"]))
        self.assertEqual(result.topic, Topic.SENSITIVE)
        self.assertIn(Topic.ORDER, result.secondary_topics)
        with self.assertRaises(ProviderError):
            Classification.parse(classification("diger", ["hassas_konu"], True))

    def test_invalid_schemas_fail_closed(self):
        for data in [None, [], {}, classification("istenmeyen-etki"),
                     classification(secondary=["siparis_durumu"]), classification(spam="false"),
                     {**classification(), "draft": "invented"}, classification(secondary=["fiyat", "fiyat"])]:
            with self.subTest(data=data), self.assertRaises(ProviderError):
                Classification.parse(data)

    def test_all_manual_inputs_are_exactly_reviewed(self):
        classifier = ManualClassifier(APP_DIR / "manual_classifications.json")
        messages = load_messages(WORKSPACE / "mesajlar.json")
        topics = [classifier.classify(message).topic for message in messages]
        self.assertEqual(len(topics), 15)
        self.assertEqual(topics.count(Topic.ORDER), 5)
        self.assertEqual(topics[3], Topic.SENSITIVE)
        self.assertEqual(topics[11], Topic.OTHER)
        with self.assertRaises(ProviderError):
            classifier.classify(Message(1, "whatsapp", 7, "A changed message"))
        with self.assertRaises(ProviderError):
            classifier.classify(Message(100, "whatsapp", 7, messages[0].text))


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.message = Message(6, "instagram", 3, "Hi, where is my order #3?")

    def test_openai_chat_completions_contract(self):
        self.client.request.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(classification())}}]}
        result = OpenAIClassifier(self.client, "test-key", "test-model").classify(self.message)
        self.assertEqual(result.topic, Topic.ORDER)
        args, kwargs = self.client.request.call_args
        self.assertEqual(args, ("POST", "https://api.openai.com/v1/chat/completions"))
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer test-key"})
        body = kwargs["payload"]
        self.assertEqual(body["response_format"]["json_schema"]["schema"], SCHEMA)
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertFalse(body["store"])
        user_data = json.loads(body["messages"][1]["content"])
        self.assertEqual(user_data, {"customer_message": self.message.text})

    def test_gemini_contract_and_thought_exclusion(self):
        self.client.request.return_value = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "private reasoning", "thought": True}, {"text": json.dumps(classification())}
        ]}}]}
        result = GeminiClassifier(self.client, "test-key", "test-model").classify(self.message)
        self.assertEqual(result.topic, Topic.ORDER)
        args, kwargs = self.client.request.call_args
        self.assertEqual(args[1], "https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent")
        self.assertNotIn("test-key", args[1])
        self.assertEqual(kwargs["headers"], {"x-goog-api-key": "test-key"})
        self.assertEqual(kwargs["payload"]["generationConfig"]["responseFormat"]["text"]["schema"], SCHEMA)

    def test_refusal_truncation_invalid_json_and_missing_candidates_fail(self):
        bad_openai = [
            {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
            {"choices": [{"finish_reason": "stop", "message": {"refusal": "No"}}]},
            {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]},
            {"choices": []}, {"choices": [None]},
        ]
        for payload in bad_openai:
            with self.subTest(payload=payload), self.assertRaises(ProviderError):
                self.client.request.return_value = payload
                OpenAIClassifier(self.client, "test-key", "test-model").classify(self.message)
        for payload in [{}, {"candidates": []}, {"candidates": [{"finishReason": "SAFETY"}]}]:
            with self.subTest(payload=payload), self.assertRaises(ProviderError):
                self.client.request.return_value = payload
                GeminiClassifier(self.client, "test-key", "test-model").classify(self.message)

    def test_keys_required_and_model_path_not_injectable(self):
        for factory in (OpenAIClassifier, GeminiClassifier):
            with self.assertRaises(ConfigurationError):
                factory(self.client, "", "model")
            with self.assertRaises(ConfigurationError):
                factory(self.client, "key", "model?key=secret")
        self.client.request.assert_not_called()


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.classifier = Mock(name="classifier")
        self.classifier.name = "openai"
        self.classifier.classify.return_value = Classification.parse(classification())
        self.orders = Mock()
        self.orders.fetch.return_value = owned_cart()
        self.service = MessageService(self.classifier, self.orders)
        self.message = Message(6, "instagram", 3, "Hi, where is my order #3?")

    def test_matching_owner_gets_only_verified_details(self):
        result = self.service.process(self.message)
        self.assertFalse(result.ticket.handoff)
        self.assertIn("Test product (2 adet)", result.ticket.draft)
        self.assertIn("125,50", result.ticket.draft)
        self.assertIn("teslim tarihi görüntülenemiyor", result.ticket.draft)
        self.orders.fetch.assert_called_once_with(3)

    def test_mismatched_owner_never_exposes_details_anywhere(self):
        self.orders.fetch.return_value = {"id": 3, "userId": 999, "products": [{"title": "SECRET PRODUCT"}], "total": 987654.32}
        result = self.service.process(self.message)
        serialized = json.dumps(result.ticket.to_dict())
        self.assertTrue(result.ticket.handoff)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("987654", serialized)
        self.assertNotIn("999", serialized)

    def test_sensitive_and_return_never_call_order_api_or_recommend(self):
        for topic in (Topic.SENSITIVE, Topic.RETURN):
            with self.subTest(topic=topic):
                self.classifier.classify.return_value = Classification(topic)
                result = self.service.process(self.message)
                self.assertTrue(result.ticket.handoff)
                self.assertNotIn("Test product", result.ticket.draft)
                self.assertIn("temsilcimize", result.ticket.draft)
        self.orders.fetch.assert_not_called()

    def test_provider_failure_hands_off_without_order_lookup(self):
        self.classifier.classify.side_effect = ProviderError("openai_http_429")
        result = self.service.process(self.message)
        self.assertTrue(result.ticket.handoff)
        self.assertEqual(result.error_code, "openai_http_429")
        self.orders.fetch.assert_not_called()

    def test_multiple_and_missing_order_ids_do_not_guess(self):
        for text in ("Siparişim nerede?", "order #3 and order #5"):
            with self.subTest(text=text):
                result = self.service.process(Message(1, "whatsapp", 3, text))
                self.assertTrue(result.ticket.handoff)
        self.orders.fetch.assert_not_called()

    def test_404_is_clean_handoff_and_not_technical_failure(self):
        self.orders.fetch.return_value = None
        result = self.service.process(self.message)
        self.assertTrue(result.ticket.handoff)
        self.assertIn("bulunamadı", result.ticket.draft)
        self.assertIsNone(result.error_code)

    def test_malformed_cart_is_not_reported_as_verified(self):
        mutations = [{"id": 7}, {"userId": "3"}, {"userId": True}, {"products": []},
                     {"total": math.nan}, {"total": -1}, {"total": "125.50"},
                     {"products": [{"title": "Product", "quantity": True}]}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.orders.fetch.return_value = {**owned_cart(), **mutation}
                result = self.service.process(self.message)
                self.assertTrue(result.ticket.handoff)
                self.assertIsNotNone(result.error_code)
                self.assertNotIn("Test product", result.ticket.draft)

    def test_secondary_price_is_retained_and_handed_off(self):
        self.classifier.classify.return_value = Classification.parse(classification(secondary=["fiyat"]))
        result = self.service.process(self.message)
        self.assertEqual(result.ticket.topic, Topic.ORDER)
        self.assertTrue(result.ticket.handoff)
        self.assertIn("fiyat", result.ticket.note)

    def test_spam_generates_no_reply(self):
        self.classifier.classify.return_value = Classification(Topic.OTHER, is_spam=True)
        result = self.service.process(self.message)
        self.assertEqual(result.ticket.draft, "")
        self.assertFalse(result.ticket.handoff)
        self.orders.fetch.assert_not_called()

    def test_product_question_does_not_invent_facts(self):
        self.classifier.classify.return_value = Classification(Topic.PRODUCT)
        result = self.service.process(self.message)
        self.assertTrue(result.ticket.handoff)
        self.assertIn("doğrulanmış", result.ticket.draft)
        self.orders.fetch.assert_not_called()


class TransportTests(unittest.TestCase):
    def test_retry_is_bounded_and_404_is_not_retried(self):
        session, sleep = Mock(), Mock()
        session.request.side_effect = [response(429), response(503), response(200, {"ok": True})]
        client = JsonClient(session=session, sleep=sleep)
        self.assertEqual(client.request("GET", "https://example.com"), {"ok": True})
        self.assertEqual(session.request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertFalse(session.request.call_args.kwargs["allow_redirects"])
        session.request.side_effect = None
        session.request.return_value = response(404)
        session.request.reset_mock()
        self.assertIsNone(client.request("GET", "https://example.com", allow_not_found=True))
        self.assertEqual(session.request.call_count, 1)

    def test_errors_do_not_include_secret_or_response_body(self):
        session = Mock()
        for status in (401, 403, 302):
            session.request.return_value = response(status, {"error": "SECRET KEY"})
            with self.subTest(status=status), self.assertRaises(HttpError) as caught:
                JsonClient(session=session).request("POST", "https://example.com")
            self.assertNotIn("SECRET", str(caught.exception))
        session.request.side_effect = requests.Timeout("SECRET KEY")
        with self.assertRaises(HttpError) as caught:
            JsonClient(session=session, sleep=Mock()).request("POST", "https://example.com")
        self.assertEqual(str(caught.exception), "network_unavailable")

    def test_invalid_json_is_not_retried(self):
        session = Mock()
        session.request.return_value = response(200)
        session.request.return_value.json.side_effect = ValueError("private data")
        with self.assertRaises(HttpError):
            JsonClient(session=session).request("GET", "https://example.com")
        self.assertEqual(session.request.call_count, 1)

    def test_cart_transport_failure_is_reported(self):
        session = Mock()
        session.request.side_effect = requests.Timeout()
        service = MessageService(ManualClassifier(APP_DIR / "manual_classifications.json"),
                                 OrderClient(JsonClient(session=session, sleep=Mock())))
        message = load_messages(WORKSPACE / "mesajlar.json")[0]
        result = service.process(message)
        self.assertTrue(result.ticket.handoff)
        self.assertEqual(result.error_code, "cart_network_unavailable")


class InputAndRunTests(unittest.TestCase):
    def test_order_number_patterns_ignore_prices_and_sizes(self):
        for text, expected in [
            ("12 numaralı siparişim", [12]), ("Sipariş no: 5", [5]),
            ("SİPARİŞ #4", [4]), ("Hi, order #3?", [3]),
            ("200 ml tonik 150 TL mi?", []), ("order #3, order #3", [3]),
            ("order #3 and order #5", [3, 5]), ("order #1234567890", []),
        ]:
            with self.subTest(text=text):
                self.assertEqual(extract_order_ids(text), expected)

    def test_invalid_input_fails_before_network(self):
        valid = {"id": 1, "kanal": "whatsapp", "musteri_id": 1, "mesaj": "Test"}
        samples = [[], {}, [valid, valid], [{**valid, "id": True}], [{**valid, "mesaj": " "}],
                   [{**valid, "musteri_id": -1}], [{**valid, "kanal": "email"}]]
        with tempfile.TemporaryDirectory(dir=APP_DIR) as folder:
            path = Path(folder) / "input.json"
            for data in samples:
                with self.subTest(data=data), self.assertRaises(InputError):
                    path.write_text(json.dumps(data), encoding="utf-8")
                    load_messages(path)

    def test_pipeline_output_schema_summary_and_provenance(self):
        def fetch(order_id):
            if order_id == 9999:
                return None
            return {**deepcopy(owned_cart()), "id": order_id, "userId": order_id}
        with tempfile.TemporaryDirectory(dir=APP_DIR) as folder, \
                patch.object(OrderClient, "fetch", side_effect=fetch), \
                patch.dict(os.environ, {"HTTP_MAX_RETRIES": "0", "HTTP_TIMEOUT_SECONDS": "5"}), \
                redirect_stdout(io.StringIO()):
            target = Path(folder)
            args = argparse.Namespace(provider="manual", input=WORKSPACE / "mesajlar.json", output_dir=target)
            self.assertEqual(main.run(args), 0)
            tickets = json.loads((target / "talepler.json").read_text(encoding="utf-8"))
            self.assertEqual(len(tickets), 15)
            self.assertEqual([item["id"] for item in tickets], list(range(1, 16)))
            self.assertTrue(all(set(item) == {"id", "konu", "devret", "cevap_taslagi", "not"} for item in tickets))
            self.assertTrue(all(type(item["devret"]) is bool for item in tickets))
            self.assertTrue(tickets[0]["devret"])
            self.assertFalse(tickets[1]["devret"])
            self.assertFalse(tickets[5]["devret"])
            self.assertEqual(tickets[6]["cevap_taslagi"], "")
            self.assertIn("Toplam: 15", (target / "ozet.txt").read_text(encoding="utf-8"))
            metadata = json.loads((target / "run_metadata.json").read_text())
            self.assertEqual(metadata["provider"], "manual")
            self.assertEqual(metadata["status"], "completed")

    def test_technical_failure_writes_handoffs_but_returns_nonzero(self):
        with tempfile.TemporaryDirectory(dir=APP_DIR) as folder, \
                patch.object(ManualClassifier, "classify", side_effect=ProviderError("manual_message_not_reviewed")), \
                redirect_stdout(io.StringIO()):
            target = Path(folder)
            args = argparse.Namespace(provider="manual", input=WORKSPACE / "mesajlar.json", output_dir=target)
            self.assertEqual(main.run(args), 2)
            metadata = json.loads((target / "run_metadata.json").read_text())
            self.assertEqual(metadata["status"], "degraded")
            self.assertEqual(len(metadata["technical_errors"]), 15)


if __name__ == "__main__":
    unittest.main()
