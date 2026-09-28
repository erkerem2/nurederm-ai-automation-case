# Customer Message Automation Case

Part A is implemented as a Python CLI with OpenAI Chat Completions, Gemini, and an
explicit manual demo mode. Part B is an importable n8n workflow in `B-n8n/`
(see [B-n8n/akis-aciklama.md](B-n8n/akis-aciklama.md)). The Part A program prepares
drafts for a representative. It does not send customer messages.

## Timing

- Assignment received: 2026-09-28 11:00, Europe/Istanbul (reported by the user).
- Implementation started: 2026-09-28 11:23, Europe/Istanbul.
- First live DummyJSON run completed: 2026-09-28 11:32, Europe/Istanbul.
- Target for all checks: 13:45; submission deadline: 14:00.
- 12:11: work continued with Claude Code after the Codex usage limit was reached.
- Part B workflow and verification script completed: 12:18, Europe/Istanbul.
- First successful live Gemini classification of all 15 messages: 12:38.
- **Completed: ~12:35, Europe/Istanbul** (Part A, Part B and the product-search bonus).
  The HTML summary, the repeatable live acceptance script and this documentation
  were finished afterwards, before 13:00.

## Where We Got Stuck / What Is Not Finished

- **Gemini free tier quota.** The free tier allows 20 requests/day per project and
  model. Sending one request per message (15 per run) plus retries used it up in the
  first live attempts, so a full 15-message run on `gemini-3.8-flash` never completed.
  A regenerated key did not help because it belonged to the same project and shared
  the same quota. The fix was a batch mode (all messages in one request, retries
  off) and switching to `gemini-2.5-flash-lite`, which then classified all 15
  messages in one request with results identical to the manual reference.
  `gemini-3.7-flash` did not answer even a minimal request within 60-90 s.
- **No OpenAI key.** The OpenAI Chat Completions adapter is implemented and covered by
  request/response contract tests, but has never been called with a real key.
- **Key not saved to `.env`.** The regenerated Gemini key had not been saved in the
  editor, so two batch attempts got HTTP 401 before this was noticed.
- **Codex usage limit.** Work started with Codex; its usage limit was reached around
  12:10 and the rest was done with Claude Code. Both tools' prompts are in `promptlar/`.
- **Connection drops.** The Codex session disconnected twice (prompts 8 and 13), and
  one paced Gemini run was interrupted without output.
- **Not finished:** n8n was not installed or run live, so there is no execution
  screenshot (the workflow's Code nodes are verified with Node.js instead). The
  test store has no matching cosmetics, so the product-search bonus never lists a
  product for the supplied messages (the matched path is unit-tested).

## Quick Start

Python 3.12 was used for verification. Run these commands from the repository root
in PowerShell. No activation or PowerShell execution-policy change is necessary.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider manual
```

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.
The manual run needs internet access for DummyJSON but does not need an LLM key.
Input paths default relative to the script, so launching from another directory
does not change which input is read.

Outputs in `A-mesaj-otomasyonu/`:

- `talepler.json`: one ticket per input message, in the original order.
- `ozet.txt`: the same one-page summary printed to the terminal.
- `ozet.html`: the same summary as a single-page HTML report (counts plus a ticket
  table); open it directly in a browser.
- `run_metadata.json`: provider, model, timestamps, input hash, and technical errors.

The delivered sample output uses the coding assistant's own classifications (first
made with Codex, then independently re-reviewed by Claude Code, which agreed on all 15
topics) together with real DummyJSON lookups. It is deliberately not the free-tier
Gemini result: production would use a stronger model, and the Gemini run is kept only
as live-integration evidence in `A-mesaj-otomasyonu/live_runs/gemini-batch/`.

## API Configuration

The local `.env` has empty key fields and is ignored by Git. `.env.example` is the
shareable template. After cloning, create `.env` from that template locally.

```dotenv
CLASSIFIER_PROVIDER=manual
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=2
LLM_MIN_INTERVAL_SECONDS=15
CLASSIFICATION_PROMPT_PATH=A-mesaj-otomasyonu/llm_prompts/classify_prompt.txt
```

Fill the key for the chosen provider. Either set `CLASSIFIER_PROVIDER` to `openai`
or `gemini`, or select it explicitly on the command line:

```powershell
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider openai --output-dir A-mesaj-otomasyonu/runs/openai
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider gemini --output-dir A-mesaj-otomasyonu/runs/gemini
```

For low-quota accounts, `--batch` classifies all messages (up to 50) in a single
API request and `--max-retries 0` disables retries, so a full live check costs
exactly one request. The batch response is accepted only if it contains exactly one
valid classification for every supplied message ID; otherwise every message is
handed off with a technical error.

```powershell
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider gemini --batch --max-retries 0 --output-dir A-mesaj-otomasyonu/runs/gemini-batch
```

Provider comparison runs go into ignored `runs/` directories to preserve the
submitted demo outputs. Provider selection is explicit; entering a key alone does
not switch modes. Only the selected provider receives the message text. Customer
IDs, channel metadata, and fetched carts are not added to the classification prompt.
Environment variables already set by the process take precedence over `.env`.
`LLM_MIN_INTERVAL_SECONDS` spaces requests for low-quota accounts; the example
uses 15 seconds. This is configurable, not a guarantee that any account quota is
sufficient. A 15-message live run therefore takes at least about 3.5 minutes.
Both providers load their system instructions from `CLASSIFICATION_PROMPT_PATH`.
Relative paths are resolved from the repository root, not the shell's working
directory. An unreadable or empty prompt file stops API mode before any requests.
The classification prompt is few-shot: one invented example per topic (none taken
from `mesajlar.json`), including one multi-intent example with a secondary topic.
The live Gemini verification ran on the previous zero-shot version of the prompt
(its SHA-256 is in that run's metadata), before `istenmeyen_mesaj` existed, so it labels
message 7 as `diger` with the old spam flag; the current prompt has not been evaluated live.
Runtime LLM prompts live in `A-mesaj-otomasyonu/llm_prompts/`, separate from the user prompt history; edits take effect on the next run.

Models are configurable and require access in the corresponding API account.
Both adapters request structured JSON and validate the result locally. OpenAI
uses `/v1/chat/completions`; Gemini uses `generateContent`. There is no automatic
cross-provider fallback and no local LLM integration.

## Processing Decisions

The application has separate input/domain validation, provider adapters, HTTP
transport, order access, and response policy modules. Code identifiers and system
prompts are English. Customer-facing drafts, the operator summary, and ticket
notes are Turkish. Product names retain the API's original text.

The topic names intentionally differ from the supplied brief at the user's request:

| Brief | Output |
| --- | --- |
| `urun-sorusu` | `urun_sorusu` |
| `fiyat` | `fiyat` |
| `siparis-durumu` | `siparis_durumu` |
| `iade-sikayet` | `iade_sikayet` |
| `istenmeyen-etki` | `hassas_konu` |
| — | `istenmeyen_mesaj` (added: ads, follower selling, scams) |
| `diger` | `diger` |

The output keys remain exactly `id`, `konu`, `devret`, `cevap_taslagi`, and `not`.
The original `case-brief.md` and `mesajlar.json` are unchanged.

- The LLM classifies intent only. It cannot generate customer responses or authorize an order lookup result.
- Sensitive and return/complaint topics always hand off without diagnosis, treatment, or product recommendations. Sensitive secondary intents override an order intent.
- An explicit order number is extracted from the original text. Missing or multiple numbers prompt clarification and handoff; unrelated prices and sizes are not treated as order IDs.
- A cart's integer `userId` must equal the input `musteri_id`. The response `id` must match the requested cart. No product or total fields are read for a mismatched owner.
- Only validated product titles, positive quantities, and the `total` field appear in a verified order draft. The API does not provide shipment status, delivery dates, or a currency field, so these are not invented.
- A missing cart (HTTP 404) is a normal handoff. Network errors and malformed responses are technical failures and also hand off safely.
- Message 8 keeps `siparis_durumu` as its main topic and records the additional `fiyat` intent in the note; the unanswered price question causes handoff.
- Message 12 asks a general shipping-policy question, so it is `diger`. Message 15 asks about product/brand policy, so it is `urun_sorusu`.
- Product, price, and policy questions hand off because a verified store knowledge source has not been supplied. Bonus product search: for `urun_sorusu` / `fiyat`, the classifier also returns a short English `product_query` (validated as 1-60 keyword characters). The program calls `GET https://dummyjson.com/products/search`, keeps only `beauty`, `skin-care` and `fragrances` items whose title contains every query word (the store search also matches descriptions, e.g. "cream" returns "Ice Cream"), and lists at most three with their API price. The message is still handed off: catalog data never answers suitability, ingredient or policy questions. For the supplied messages (retinol serum, moisturizer, vitamin c serum, toner) the test store has no cosmetic match, so the drafts say so instead of suggesting an unrelated product. A catalog failure is reported as a technical error.
- `istenmeyen_mesaj` (unsolicited ads and similar; added at the user's request, replacing the earlier `is_spam` flag so the label lives in one place) receives an empty draft and no handoff. It cannot carry secondary topics, so a real complaint cannot be hidden behind a spam label. Links in customer messages are never opened.
- `manual` accepts only an exact ID/text match from `manual_classifications.json`. A new or edited message is flagged for human review with a technical error, not silently assigned a stored label.

## Failure Handling

HTTP requests use connection/read timeouts and bounded retries for connection
failures, timeouts, HTTP 429, and HTTP 5xx. Authentication failures are not retried.
Permanent provider errors (400, 401, 403, 404) and an explicitly reported daily
Gemini quota exhaustion stop further provider requests for
that run; remaining messages receive explicit failure handoffs.
Redirects are disabled. Logs and ticket notes exclude raw provider errors, HTTP
headers, and authentication values. Output files are replaced atomically per file.

Exit codes:

- `0`: all messages processed, including normal human handoffs and missing carts.
- `1`: configuration, input, or filesystem failure; no successful run is claimed.
- `2`: output produced, but at least one message had a technical failure; see metadata.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s A-mesaj-otomasyonu -p "test_*.py" -v
```

The tests run without real API keys and mock all network requests. They cover
ownership leakage, sensitive handoffs, multi-intent messages, missing/ambiguous
orders, invalid input and API data, bounded retries, provider request formats,
refusals, truncated responses, exact manual matching, output schemas, and exit codes.
Temporary test files are created inside the project and removed after testing.

The real DummyJSON sample run processed 15 messages with no technical errors:
4 `urun_sorusu`, 2 `fiyat`, 5 `siparis_durumu`, 1 `iade_sikayet`, 1 `hassas_konu`,
1 `istenmeyen_mesaj` (message 7) and 1 `diger`. Twelve messages were handed off. Messages 2 and 6 had verified order
details, message 1 failed ownership verification, message 3 was not found, and
message 8 had verified order details plus an unresolved price question.

Thirty-eight offline tests pass. OpenAI has only been checked with contract tests because
no OpenAI key was supplied. Gemini was also called live after its key was added:
six messages succeeded in the initial unpaced run, but a full 15-message acceptance
run could not be completed. A subsequent run using the external prompt file had
two successful classifications, one HTTP 503, and twelve HTTP 429 errors. The API
then explicitly reported an exhausted free-tier limit of 20 requests/day for this
project/model. See `A-mesaj-otomasyonu/verification.md` for the attempt history.
Two single-request batch attempts (12:03 and 12:11) returned HTTP 401, i.e. the
configured key was rejected; the key had not been updated in `.env` after it was
regenerated. At 12:38 a single batch request on `gemini-2.5-flash-lite` (the project's quota for
`gemini-3.8-flash` was exhausted) classified all 15 messages with no technical
errors. Topic and handoff decisions matched the manual reference for 15/15 messages,
including ownership checks, sensitive handoffs and message 8's secondary price intent;
extracted product queries matched except "moisturizer cream" vs "moisturizing cream"
(the reference now uses "moisturizer").
The committed evidence is in `A-mesaj-otomasyonu/live_runs/gemini-batch/`.
`gemini-2.5-flash-lite` is therefore the default Gemini model.
The delivered main outputs remain the successful manual + live DummyJSON run;
failed Gemini results are not substituted or described as successful.

## Part B: n8n Price Monitor

`B-n8n/workflow.json` is adapted from the n8n template
[Competitor price monitoring with web scraping, Google Sheets & Telegram (#4640)](https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets-and-telegram/).
It runs daily at 09:00 (Europe/Istanbul), follows `rel="next"` pagination over all
laptop pages, stores numeric prices with a timestamp in Google Sheets, reports new
products and price changes in one Telegram message, and routes every failure to a
Telegram alert followed by Stop and Error. Setup, the change list against the
template, and limitations are in [B-n8n/akis-aciklama.md](B-n8n/akis-aciklama.md).

n8n was not run live. The Code-node JavaScript is verified by extracting it from
`workflow.json` and executing it with Node.js (18 checks, including a live scrape
of 20 pages / 117 products):

```powershell
node B-n8n/tests/verify_workflow.mjs
```

## Live Acceptance Checks

`A-mesaj-otomasyonu/tests/live_acceptance.py` re-checks the delivered outputs
against the real DummyJSON API and the repository state (36 checks). Order numbers
are extracted with the application's own parser, not hard-coded. It verifies the
output schema, sensitive handoffs, that a foreign cart's titles, total and owner
never appear in any ticket, CLI failure exits, that no API key is committable, and
that the original case files are unchanged. A deliberately injected leak makes it fail.

```powershell
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/tests/live_acceptance.py
```

## Deployment Boundary

This is a production-oriented processing component, not a deployed messaging
service. The case treats `musteri_id` in the input file as trusted identity. A real
WhatsApp/Instagram integration must supply it from a verified, authenticated
customer mapping rather than from user-editable message content or JSON.

Before automatic customer sending, the service also needs representative-reviewed
classification evaluations, a verified product/policy knowledge source, durable
job storage and deduplication, and operational monitoring. Currently every output
is a draft; the program neither sends messages nor performs refunds. LLM topic
classification can still be wrong even when its output matches the JSON schema.

## Prompt History and Sources

`promptlar/` holds every user-authored prompt verbatim and in order, including
failed attempts and corrections: `A-claude-code.md` (planning, Part A and the
Codex-to-Claude-Code handover), `B-n8n.md` (Part B), and `proje-sonu.json` (the
final wrap-up prompts). Each prompt keeps its sequence number and phase label.
Prompts 1-13 were sent to Codex and 14 onward to Claude Code. Original message timestamps
are unavailable and have not been fabricated. System/environment messages are
excluded. Runtime classification instructions live in `A-mesaj-otomasyonu/llm_prompts/classify_prompt.txt`
and are selected through `CLASSIFICATION_PROMPT_PATH` in `.env`. Run metadata
records the loaded prompt's SHA-256 hash without copying its content.

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Gemini generateContent structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en)
- [Gemini 2.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite)

Git commits, pushes, repository publication, and submission are handled by the user.
