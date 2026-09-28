# Part A Verification

Date: 2026-09-28. Times below are Europe/Istanbul (UTC+03:00).

## Automated Tests

30 offline tests passed with Python 3.12.10. All automated test network calls are
mocked; they do not prove live provider availability or general model accuracy.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s A-mesaj-otomasyonu -p "test_*.py" -v
```

Coverage includes cross-customer data leakage, sensitive-topic priority and
handoff, missing and ambiguous order numbers, malformed cart data, provider
refusals and invalid JSON, retry limits, request pacing, permanent provider
failures, daily quota exhaustion, external prompt loading and hash provenance,
input validation, output schema, and nonzero exit status on technical failures.

## Successful Case Run

At 11:32, manual classification of the supplied messages plus actual DummyJSON
requests produced 15 tickets, 12 human handoffs, and zero technical errors.
These are the committed-ready `talepler.json`, `ozet.txt`, and `run_metadata.json`.

- Message 1: owner mismatch, no order details exposed.
- Messages 2 and 6: matching owner, verified products and totals.
- Message 3: missing order, clean warning and handoff.
- Messages 4 and 5: sensitive/return handoff, no diagnosis or recommendation.
- Message 7: spam, no draft, no link opened.
- Message 8: verified order plus an unresolved price question preserved for handoff.
- Other product/price/policy questions: human handoff due to missing verified knowledge.

## Live Gemini Attempts

1. At 11:35, the first request format returned HTTP 400. The API rejected the new
   `responseFormat.text.mimeType` value. The adapter was changed to the supported
   `responseMimeType` + `responseJsonSchema` configuration.
2. The next request revealed that `gemini-2.5-flash` was unavailable to this new
   account. The API recommended `gemini-3.8-flash`; configuration was updated.
3. At 11:37-11:38, the unpaced 15-message run successfully classified messages
   1, 2, 3, 4, 5, and 15. Nine messages received HTTP 429. The successful messages
   matched the manual topic reference, including the sensitive/return cases and
   the ownership-protected order case. This was a degraded run, not a full pass.
4. A paced attempt was interrupted by the connection loss and left no completed
   output. It is not counted as a successful test.
5. At 11:43-11:46, the external-prompt run used `gemini-3.8-flash` and a 15-second
   minimum interval. Messages 1 and 3 were successfully classified; message 2
   received HTTP 503; messages 4-15 received HTTP 429. The output status is
   `degraded`. A sanitized diagnostic then identified the quota as
   `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value `20`.
6. After discovering the daily limit, the transport was changed to recognize
   structured `google.rpc.QuotaFailure` details and stop retrying a daily quota
   failure. The classifier stops remaining provider calls for that run and creates
   explicit human-review tickets. Offline tests cover this change; no further
   live requests were made after daily quota exhaustion was confirmed.

The final live run's prompt SHA-256 was:
`cf4270c3bae7d9d3366e18d9b07cf6ecb40b00a455b38b581d7c59d5ca07baaa`.
Its input SHA-256 was:
`e431d6ea36046f284ffa1dfc44904398423d30faf6a90553684a534b738c553a`.

Local diagnostic output files are in the ignored `runs/gemini/` and
`runs/gemini-paced/` directories. This report retains their relevant results
without including API credentials or raw provider error bodies.

7. To keep free-tier usage minimal, a batch mode was added: all 15 messages are
   classified in one request (`--batch`) with retries disabled (`--max-retries 0`).
   The response must contain exactly one valid classification per supplied ID.
   Two single-request batch attempts (12:03 and 12:11) both returned HTTP 401:
   the configured key was rejected. The key in `.env` had not been changed since
   11:43, although the user had regenerated it, so the likely cause is a revoked
   key rather than a code change. The batch run's local output is in the ignored
   `runs/gemini-batch/` directory; its prompt SHA-256 differs because the batch
   instructions were appended to the prompt file.

8. After the regenerated key was saved to `.env` (12:40), authentication passed,
   but the single batch request on `gemini-3.8-flash` returned a structured daily
   quota error (`http_429_daily_quota`): the new key belongs to the same project
   and shares its exhausted 20 requests/day. `models.list` (no generation quota)
   showed other Flash models. Two batch requests on `gemini-3.7-flash` and one
   minimal "Say OK" probe all timed out (90 s / 60 s) without any response, so
   that endpoint was unresponsive for this account; no further requests were sent.
   Timeouts were previously reported as `network_unavailable`; they now have their
   own `timeout` error code so a slow provider is distinguishable from no network.

## Product Search Bonus

The manual run at 12:58 performed four real `/products/search` calls (messages 9,
10, 11 and 13). None returned a cosmetic product whose title matches the query, so
all four drafts state that no catalog match was found and hand off. The matched
path, category/title filtering, catalog failures and query validation are covered
by offline tests. Live LLM extraction of `product_query` has not been verified.

## Outstanding Verification

- A complete 15-message Gemini acceptance run still needs an available quota.
- OpenAI live verification still needs an OpenAI API key.
- Runtime prompts are editable through `CLASSIFICATION_PROMPT_PATH`; future
  prompt/model changes need a fresh evaluation.
- A live batch run with a valid Gemini key has not succeeded yet.

No commits or pushes were performed by the coding assistant. The original
`case-brief.md` and `mesajlar.json` were not modified.
