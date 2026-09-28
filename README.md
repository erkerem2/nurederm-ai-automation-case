# Customer Message Automation Case

Part A is implemented as a Python CLI with OpenAI Chat Completions, Gemini, and an
explicit manual demo mode. Part B has not started; it follows the Part A review.
The program prepares drafts for a representative. It does not send customer messages.

## Timing

- Assignment received: 2026-09-28 11:00, Europe/Istanbul (reported by the user).
- Implementation started: 2026-09-28 11:23, Europe/Istanbul.
- First live DummyJSON run completed: 2026-09-28 11:32, Europe/Istanbul.
- Target for all checks: 13:45; submission deadline: 14:00.
- Overall completion: pending Part B and final review.

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
- `run_metadata.json`: provider, model, timestamps, input hash, and technical errors.

The delivered sample output uses manually reviewed classifications and a real
DummyJSON lookup. It is not presented as an OpenAI or Gemini result.

## API Configuration

The local `.env` has empty key fields and is ignored by Git. `.env.example` is the
shareable template. After cloning, create `.env` from that template locally.

```dotenv
CLASSIFIER_PROVIDER=manual
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
HTTP_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=2
LLM_MIN_INTERVAL_SECONDS=15
CLASSIFICATION_PROMPT_PATH=prompts/classift_prompt.txt
```

Fill the key for the chosen provider. Either set `CLASSIFIER_PROVIDER` to `openai`
or `gemini`, or select it explicitly on the command line:

```powershell
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider openai --output-dir A-mesaj-otomasyonu/runs/openai
.\.venv\Scripts\python.exe A-mesaj-otomasyonu/main.py --provider gemini --output-dir A-mesaj-otomasyonu/runs/gemini
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
Runtime prompts live together in `prompts/`; edits take effect on the next run.

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
- Product, price, and policy questions hand off because a verified store knowledge source has not been supplied. Product search is an optional bonus and is not implemented yet.
- Spam receives an empty response draft. Links in customer messages are never opened.
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
and 2 `diger`. Twelve messages were handed off. Messages 2 and 6 had verified order
details, message 1 failed ownership verification, message 3 was not found, and
message 8 had verified order details plus an unresolved price question.

Thirty offline tests pass. OpenAI has only been checked with contract tests because
no OpenAI key was supplied. Gemini was also called live after its key was added:
six messages succeeded in the initial unpaced run, but a full 15-message acceptance
run could not be completed. A subsequent run using the external prompt file had
two successful classifications, one HTTP 503, and twelve HTTP 429 errors. The API
then explicitly reported an exhausted free-tier limit of 20 requests/day for this
project/model. See `A-mesaj-otomasyonu/verification.md` for the attempt history.
The delivered main outputs remain the successful manual + live DummyJSON run;
failed Gemini results are not substituted or described as successful.

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

`prompts.json` is the canonical ordered record of user-authored prompts from the
start of this conversation, including corrections. Original message timestamps
are unavailable and have not been fabricated. System/environment messages are
excluded. Runtime classification instructions live in `prompts/classift_prompt.txt`
and are selected through `CLASSIFICATION_PROMPT_PATH` in `.env`. Run metadata
records the loaded prompt's SHA-256 hash without copying its content.

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Gemini generateContent structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en)
- [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)

Git commits, pushes, repository publication, and submission are handled by the user.
