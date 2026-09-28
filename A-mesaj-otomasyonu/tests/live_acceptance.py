"""Live acceptance checks against real DummyJSON data and the repository state.

Not part of the offline unit suite (the file name does not match test_*.py) because it
needs network access. Order numbers are extracted from each message with the same
function the application uses, so the checks do not hard-code carts or message IDs.

Usage (from the repository root):
    python A-mesaj-otomasyonu/tests/live_acceptance.py [OUTPUT_DIR ...]
Defaults to the delivered output and the committed live Gemini run.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import requests
from dotenv import dotenv_values

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from automation.domain import Topic  # noqa: E402
from automation.orders import extract_order_ids  # noqa: E402

ALLOWED = {topic.value for topic in Topic}
KEYS = {"id", "konu", "devret", "cevap_taslagi", "not"}
results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail and not condition else ""))


def money(value) -> str:
    return f"{value:.2f}".replace(".", ",")


def fetch_cart(cart_id: int):
    response = requests.get(f"https://dummyjson.com/carts/{cart_id}", timeout=20)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def check_output(folder: Path, messages: list[dict]):
    label = folder.relative_to(ROOT).as_posix()
    tickets = json.loads((folder / "talepler.json").read_text(encoding="utf-8"))
    meta = json.loads((folder / "run_metadata.json").read_text(encoding="utf-8"))
    summary = (folder / "ozet.txt").read_text(encoding="utf-8")
    by_id = {ticket["id"]: ticket for ticket in tickets}

    check(f"{label}: one ticket per message, input order", [t["id"] for t in tickets] == [m["id"] for m in messages])
    check(f"{label}: exact output keys", all(set(t) == KEYS for t in tickets))
    check(f"{label}: valid topic and boolean devret", all(t["konu"] in ALLOWED and type(t["devret"]) is bool for t in tickets))
    check(f"{label}: iade_sikayet / hassas_konu always handed off",
          all(t["devret"] for t in tickets if t["konu"] in (Topic.RETURN, Topic.SENSITIVE)))
    check(f"{label}: sensitive drafts contain no recommendation or diagnosis wording",
          not any(word in t["cevap_taslagi"].lower() for t in tickets if t["konu"] in (Topic.RETURN, Topic.SENSITIVE)
                  for word in ("öner", "krem", "serum", "sürün", "kullanın", "alerji", "tedavi")))
    check(f"{label}: run completed without technical errors", meta["status"] == "completed" and not meta["technical_errors"])
    check(f"{label}: text summary matches tickets",
          all(f"{topic}: {sum(t['konu'] == topic for t in tickets)}" in summary for topic in ALLOWED)
          and f"Temsilciye devredilecek: {sum(t['devret'] for t in tickets)}" in summary)
    if (folder / "ozet.html").exists():
        page = (folder / "ozet.html").read_text(encoding="utf-8")
        check(f"{label}: HTML summary lists every ticket", page.count("<tr><td>") == len(tickets))

    # Ownership: every order lookup is re-done against the live API.
    owned_titles, foreign = set(), []
    for message in messages:
        ticket = by_id[message["id"]]
        if ticket["konu"] != Topic.ORDER:
            continue
        ids = extract_order_ids(message["mesaj"])
        if len(ids) != 1:
            check(f"{label}: msg {message['id']} ambiguous order number handed off", ticket["devret"])
            continue
        cart = fetch_cart(ids[0])
        if cart is None:
            check(f"{label}: msg {message['id']} missing cart {ids[0]} -> warning + handoff",
                  ticket["devret"] and "bulunamadı" in ticket["cevap_taslagi"])
        elif cart["userId"] == message["musteri_id"]:
            titles = [product["title"] for product in cart["products"]]
            owned_titles.update(titles)
            check(f"{label}: msg {message['id']} own cart {ids[0]} -> all titles and total in draft",
                  all(title in ticket["cevap_taslagi"] for title in titles) and money(cart["total"]) in ticket["cevap_taslagi"])
        else:
            foreign.append((message["id"], ids[0], cart))
            text = json.dumps(ticket, ensure_ascii=False)
            leaked = [p["title"] for p in cart["products"] if p["title"] in text]
            leaked += [v for v in (money(cart["total"]), str(cart["total"])) if v in text]
            check(f"{label}: msg {message['id']} foreign cart {ids[0]} (owner {cart['userId']} != {message['musteri_id']}) "
                  "-> handoff, no details in ticket", ticket["devret"] and not leaked, str(leaked))

    # Titles that exist only in foreign carts must not appear in any ticket at all.
    blob = json.dumps(tickets, ensure_ascii=False)
    for message_id, cart_id, cart in foreign:
        unique = [p["title"] for p in cart["products"] if p["title"] not in owned_titles and p["title"] in blob]
        check(f"{label}: titles unique to foreign cart {cart_id} appear in no ticket", not unique, str(unique))


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, str(APP_DIR / "main.py"), *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", env={**os.environ, **(env or {})})


def check_cli(scratch: Path):
    result = run_cli("--provider", "manual", "--output-dir", str(scratch / "manual"))
    check("cli: manual run exits 0", result.returncode == 0, result.stderr[-300:])
    delivered = json.loads((APP_DIR / "talepler.json").read_text(encoding="utf-8"))
    rerun = json.loads((scratch / "manual" / "talepler.json").read_text(encoding="utf-8"))
    check("cli: fresh run reproduces delivered talepler.json", rerun == delivered)
    result = run_cli("--provider", "openai", "--output-dir", str(scratch / "nokey"), env={"OPENAI_API_KEY": ""})
    check("cli: missing API key -> exit 1 before any request", result.returncode == 1 and "api_key_missing" in result.stderr)
    result = run_cli("--provider", "gemini", "--output-dir", str(scratch / "noprompt"),
                     env={"GEMINI_API_KEY": "placeholder", "CLASSIFICATION_PROMPT_PATH": "missing/prompt.txt"})
    check("cli: unreadable prompt -> exit 1 before any request",
          result.returncode == 1 and "classification_prompt_unreadable" in result.stderr)
    result = run_cli("--input", str(scratch / "missing.json"), "--output-dir", str(scratch / "noinput"))
    check("cli: missing input -> exit 1", result.returncode == 1)


def check_repository():
    git = lambda *args: subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    files = git("ls-files", "--cached", "--others", "--exclude-standard").stdout.split()
    blocked = [f for f in files if f == ".env" or f == "LOCAL_PROGRESS.md" or f.startswith((".venv/", "A-mesaj-otomasyonu/runs/"))]
    check("repo: .env, .venv, runs/ and private notes are not committable", not blocked, str(blocked))
    secrets = [value for key, value in dotenv_values(ROOT / ".env").items() if key.endswith("_API_KEY") and value]
    leaks = [f for f in files if (ROOT / f).is_file()
             and any(secret in (ROOT / f).read_text(encoding="utf-8", errors="ignore") for secret in secrets)]
    check("repo: no API key value in any committable file", not leaks, str(leaks))
    first = git("log", "--diff-filter=A", "--format=%H", "--", "mesajlar.json").stdout.split()
    unchanged = first and git("diff", "--quiet", first[-1], "--", "case-brief.md", "mesajlar.json").returncode == 0
    check("repo: case-brief.md and mesajlar.json unchanged since first added", unchanged)


def main() -> int:
    messages = json.loads((ROOT / "mesajlar.json").read_text(encoding="utf-8"))
    folders = [Path(arg).resolve() for arg in sys.argv[1:]] or [APP_DIR, APP_DIR / "live_runs" / "gemini-batch"]
    for folder in folders:
        check_output(folder, messages)
    check_cli(APP_DIR / "runs" / "acceptance")
    check_repository()
    print(f"\n{sum(results)}/{len(results)} live acceptance checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
