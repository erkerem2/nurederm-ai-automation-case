import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

from dotenv import load_dotenv

from automation.classifiers import BatchClassifier, GeminiClassifier, ManualClassifier, OpenAIClassifier, load_prompt
from automation.domain import AutomationError, ConfigurationError, Topic, load_messages
from automation.http_client import JsonClient
from automation.orders import OrderClient
from automation.service import MessageService


APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent


def write_atomic(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_parser():
    parser = argparse.ArgumentParser(description="Classify customer messages and prepare verified response drafts.")
    parser.add_argument("--provider", choices=("manual", "openai", "gemini"), help="Overrides CLASSIFIER_PROVIDER in .env")
    parser.add_argument("--input", type=Path, default=ROOT / "mesajlar.json")
    parser.add_argument("--output-dir", type=Path, default=APP_DIR)
    parser.add_argument("--batch", action="store_true", help="Classify up to 50 messages in one API request")
    parser.add_argument("--max-retries", type=int, help="Override HTTP_MAX_RETRIES; use 0 for a one-attempt quota check")
    return parser


def run(args) -> int:
    load_dotenv(ROOT / ".env", override=False)
    provider = args.provider or os.getenv("CLASSIFIER_PROVIDER", "manual")
    if provider not in ("manual", "openai", "gemini"):
        raise ConfigurationError("classifier_provider_invalid")
    try:
        timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        retries = int(os.getenv("HTTP_MAX_RETRIES", "2"))
        if getattr(args, "max_retries", None) is not None:
            retries = args.max_retries
        min_interval = float(os.getenv("LLM_MIN_INTERVAL_SECONDS", "0"))
        if not math.isfinite(timeout) or not 1 <= timeout <= 120 or not 0 <= retries <= 3:
            raise ValueError
        if not math.isfinite(min_interval) or not 0 <= min_interval <= 60:
            raise ValueError
    except ValueError:
        raise ConfigurationError("http_configuration_invalid") from None
    messages = load_messages(args.input)
    client = JsonClient(timeout, retries)
    started_at = datetime.now(timezone.utc).isoformat()
    prompt_hash = None
    try:
        if provider == "manual":
            classifier = ManualClassifier(APP_DIR / "manual_classifications.json")
        else:
            factory = OpenAIClassifier if provider == "openai" else GeminiClassifier
            default_model = "gpt-4.1-mini" if provider == "openai" else "gemini-3.8-flash"
            prompt_path = Path(os.getenv("CLASSIFICATION_PROMPT_PATH", "prompts/classify_prompt.txt"))
            system_prompt = load_prompt(prompt_path if prompt_path.is_absolute() else ROOT / prompt_path)
            prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
            classifier = factory(client, os.getenv(f"{provider.upper()}_API_KEY", ""),
                                 os.getenv(f"{provider.upper()}_MODEL", default_model),
                                 system_prompt=system_prompt, min_interval=min_interval)
            if getattr(args, "batch", False):
                classifier = BatchClassifier(classifier, messages)
        service = MessageService(classifier, OrderClient(client))
        results = []
        for index, message in enumerate(messages, start=1):
            results.append(service.process(message))
            if provider != "manual":
                print(f"İşlenen mesaj: {index}/{len(messages)}", file=sys.stderr, flush=True)
    finally:
        client.close()
    tickets = [result.ticket.to_dict() for result in results]
    counts = Counter(ticket["konu"] for ticket in tickets)
    errors = [{"message_id": result.ticket.id, "code": result.error_code} for result in results if result.error_code]
    lines = ["MÜŞTERİ TALEPLERİ ÖZETİ", f"Sınıflandırma: {provider}", f"Model: {classifier.model or '-'}", ""]
    lines.extend(f"{topic.value}: {counts[topic.value]}" for topic in Topic)
    lines.extend(["", f"Toplam: {len(tickets)}", f"Temsilciye devredilecek: {sum(ticket['devret'] for ticket in tickets)}",
                  f"Teknik hata: {len(errors)}"])
    if provider == "manual":
        lines.append("Manuel demo: yalnızca önceden incelenmiş mesajlar; canlı LLM çağrısı yok.")
    summary = "\n".join(lines) + "\n"
    metadata = {
        "started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider, "model": classifier.model,
        "classification_mode": "batch" if provider != "manual" and getattr(args, "batch", False) else "single",
        "max_retries": retries,
        "min_interval_seconds": min_interval if provider != "manual" else 0,
        "classification_prompt_sha256": prompt_hash,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "message_count": len(tickets), "technical_errors": errors,
        "status": "degraded" if errors else "completed", "order_source": "https://dummyjson.com",
    }
    write_atomic(args.output_dir / "talepler.json", json.dumps(tickets, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    write_atomic(args.output_dir / "ozet.txt", summary)
    write_atomic(args.output_dir / "run_metadata.json", json.dumps(metadata, indent=2) + "\n")
    print(summary)
    return 2 if errors else 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        return run(args)
    except AutomationError as error:
        print(f"İşlem başlatılamadı: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Dosya okuma veya yazma işlemi tamamlanamadı.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
