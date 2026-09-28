from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path


class Topic(StrEnum):
    PRODUCT = "urun_sorusu"
    PRICE = "fiyat"
    ORDER = "siparis_durumu"
    RETURN = "iade_sikayet"
    SENSITIVE = "hassas_konu"
    OTHER = "diger"


class AutomationError(Exception):
    """A sanitized operational error safe to report without response bodies."""


class ConfigurationError(AutomationError):
    pass


class InputError(AutomationError):
    pass


class ProviderError(AutomationError):
    pass


class CartError(AutomationError):
    pass


@dataclass(frozen=True)
class Message:
    id: int
    channel: str
    customer_id: int
    text: str


@dataclass(frozen=True)
class Classification:
    topic: Topic
    secondary_topics: tuple[Topic, ...] = ()
    is_spam: bool = False

    @classmethod
    def parse(cls, value: object) -> "Classification":
        if not isinstance(value, dict) or set(value) != {"topic", "secondary_topics", "is_spam"}:
            raise ProviderError("classification_invalid_schema")
        try:
            topic = Topic(value["topic"])
            secondary = value["secondary_topics"]
            if not isinstance(secondary, list) or len(secondary) > len(Topic) - 1:
                raise ValueError
            topics = tuple(Topic(item) for item in secondary)
            if topic in topics or len(set(topics)) != len(topics):
                raise ValueError
            if type(value["is_spam"]) is not bool:
                raise ValueError
            # Sensitive intent always wins, including when a model marks it secondary.
            all_topics = (topic, *topics)
            primary = next((item for item in (Topic.SENSITIVE, Topic.RETURN, Topic.ORDER)
                            if item in all_topics), topic)
            if value["is_spam"] and any(item != Topic.OTHER for item in all_topics):
                raise ValueError
            return cls(primary, tuple(item for item in all_topics if item != primary), value["is_spam"])
        except (ValueError, TypeError):
            raise ProviderError("classification_invalid_schema") from None


@dataclass(frozen=True)
class Ticket:
    id: int
    topic: Topic
    handoff: bool
    draft: str
    note: str

    def to_dict(self) -> dict:
        return {"id": self.id, "konu": self.topic.value, "devret": self.handoff,
                "cevap_taslagi": self.draft, "not": self.note}


def load_messages(path: Path) -> list[Message]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise InputError("input_unreadable_or_invalid_json") from None
    if not isinstance(data, list) or not data:
        raise InputError("input_must_be_nonempty_array")
    messages = []
    seen = set()
    for item in data:
        if not isinstance(item, dict) or set(item) != {"id", "kanal", "musteri_id", "mesaj"}:
            raise InputError("input_invalid_fields")
        if any(type(item[key]) is not int or item[key] <= 0 for key in ("id", "musteri_id")):
            raise InputError("input_invalid_identifier")
        if item["id"] in seen:
            raise InputError("input_duplicate_id")
        if item["kanal"] not in ("whatsapp", "instagram"):
            raise InputError("input_invalid_channel")
        if not isinstance(item["mesaj"], str) or not item["mesaj"].strip() or len(item["mesaj"]) > 10000:
            raise InputError("input_invalid_message")
        seen.add(item["id"])
        messages.append(Message(item["id"], item["kanal"], item["musteri_id"], item["mesaj"]))
    return messages
