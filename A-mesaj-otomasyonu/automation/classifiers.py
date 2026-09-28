import json
import re
import time
from pathlib import Path
from typing import Protocol

from .domain import Classification, ConfigurationError, Message, ProviderError, Topic
from .http_client import HttpError, JsonClient


SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "enum": [topic.value for topic in Topic]},
        "secondary_topics": {"type": "array", "items": {"type": "string", "enum": [topic.value for topic in Topic]}},
        "is_spam": {"type": "boolean"},
    },
    "required": ["topic", "secondary_topics", "is_spam"],
    "additionalProperties": False,
}

def load_prompt(path: Path) -> str:
    try:
        prompt = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        raise ConfigurationError("classification_prompt_unreadable") from None
    if not prompt.strip():
        raise ConfigurationError("classification_prompt_empty")
    return prompt


class Classifier(Protocol):
    name: str
    model: str | None

    def classify(self, message: Message) -> Classification: ...


class ManualClassifier:
    name = "manual"
    model = None

    def __init__(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.entries = {item["id"]: item for item in data["messages"]}
        except (OSError, ValueError, KeyError, TypeError):
            raise ConfigurationError("manual_fixture_invalid") from None

    def classify(self, message: Message) -> Classification:
        entry = self.entries.get(message.id)
        if not entry or entry["message"] != message.text:
            raise ProviderError("manual_message_not_reviewed")
        return Classification.parse(entry["classification"])


class ApiClassifier:
    def __init__(self, client: JsonClient, api_key: str, model: str, system_prompt: str, min_interval: float = 0,
                 clock=time.monotonic, sleep=time.sleep):
        if not api_key.strip():
            raise ConfigurationError(f"{self.name}_api_key_missing")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise ConfigurationError(f"{self.name}_model_invalid")
        if not system_prompt.strip():
            raise ConfigurationError("classification_prompt_empty")
        self.client = client
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.permanent_error = None
        self.min_interval = min_interval
        self.clock = clock
        self.sleep = sleep
        self.next_request_at = 0.0

    def classify(self, message: Message) -> Classification:
        if self.permanent_error:
            raise ProviderError(self.permanent_error)
        delay = self.next_request_at - self.clock()
        if delay > 0:
            self.sleep(delay)
        self.next_request_at = self.clock() + self.min_interval
        try:
            data = self.fetch(message.text)
            return Classification.parse(json.loads(data))
        except HttpError as error:
            if str(error) in {"http_400", "http_401", "http_403", "http_404", "http_429_daily_quota"}:
                self.permanent_error = f"{self.name}_{error}"
            raise ProviderError(f"{self.name}_{error}") from None
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise ProviderError(f"{self.name}_invalid_response") from None


class OpenAIClassifier(ApiClassifier):
    name = "openai"

    def fetch(self, text: str) -> str:
        data = self.client.request(
            "POST", "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={
                "model": self.model,
                "store": False,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": json.dumps({"customer_message": text}, ensure_ascii=False)},
                ],
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": "message_classification", "strict": True, "schema": SCHEMA,
                }},
            },
        )
        choice = data["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
            raise ProviderError("openai_incomplete_or_refused")
        return choice["message"]["content"]


class GeminiClassifier(ApiClassifier):
    name = "gemini"

    def fetch(self, text: str) -> str:
        data = self.client.request(
            "POST", f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            payload={
                "systemInstruction": {"parts": [{"text": self.system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": json.dumps({"customer_message": text}, ensure_ascii=False)}]}],
                "generationConfig": {
                    "responseMimeType": "application/json", "responseJsonSchema": SCHEMA,
                },
            },
        )
        candidate = data["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise ProviderError("gemini_incomplete_or_blocked")
        return "".join(part["text"] for part in candidate["content"]["parts"] if not part.get("thought"))
