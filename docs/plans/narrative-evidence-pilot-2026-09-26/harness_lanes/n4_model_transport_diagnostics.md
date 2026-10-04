# N4-T1：MiniMax transport error diagnostics and budget settlement

Status: ACCEPTED / INTEGRATED / PUBLISHED TO MAIN (5de9154, included in 66808ee)
Card date: 2026-10-04
Owner: isolated harness; MAIN owns final live-provider and cross-layer acceptance.

外线 4a53080 已 cherry-pick；MAIN 跨层 114 项和新增 HTTP 400 持久账本端到端 1 项通过。见 [验收收据](results/n4t1_model_transport_acceptance_2026-10-04.md)。N4-T2/N4C仍待完成，不重新派发 T1。

## Goal

Make one bounded model attempt diagnosable without retaining provider response bodies, prompt text, source text, API keys, or full URLs. Preserve the existing conservative budget rule: once an HTTP request may have reached the provider, unknown usage remains charged at the reservation bound.

The current N4C run recorded one unknown reservation ($0.005258) and no final artifact. Source inspection found a definite classification gap: NarrativeHTTPModel raises ModelHTTPError with a status, but BudgetedNarrativeCaller currently treats it as generic MODEL_RESPONSE_INVALID and drops that status. Therefore the persisted receipt cannot distinguish an HTTP rejection from a malformed 2xx response. Do not guess which one happened in the old run.

## Worktree and exclusive write set

Use a dedicated company-wiki worktree outside the MAIN checkout, starting from current committed main. Parallel execution requires a separate worktree for each card. Sequential execution may reuse one dedicated worktree: finish and commit N4-T1, finish its tests, then start N4-T2. Record each card's own base/head commit range; N4-T2's base may be N4-T1's delivered head. Preserve committed N4-T1 work rather than resetting the directory. No extra approval is needed between cards.

Write only:

- src/company_wiki/automation/narrative_http_model.py
- src/company_wiki/automation/narrative_model_caller.py
- src/company_wiki/automation/narrative_summarize.py, only if the safe diagnostic must pass through the handler
- tests/unit/test_narrative_http_model.py
- tests/unit/test_narrative_model_caller.py
- tests/unit/test_narrative_summarize_handler.py
- a lane handoff report in this card's handoff section or a returned report; do not edit shared task_plan.md, progress.md, findings.md, configuration, or another lane's files.

Do not edit source_catalog selectors, narrative batch orchestration, shared wire schemas, CI workflows, production catalog/raw data, config/source_acquisition.yaml, the failed run database, or any other repository.

## Frozen interface and behavior

1. Keep the request's current public schema and one-request-per-attempt rule. No retry loop inside the adapter.
2. Preserve the provider HTTP status as a safe diagnostic. Never copy an error body, prompt, response text, API key, authorization header, or query-bearing URL into an exception, log, result, or receipt.
3. Keep HTTP 429 as the existing rate-limit result. Give other 4xx responses a stable terminal HTTP-error classification and 5xx responses a retryable HTTP-error classification. Include only the integer HTTP status in a bounded, documented diagnostic field or safe detail.
4. Keep malformed/empty 2xx response envelopes distinct from HTTP status failures. The official MiniMax Chat Completions example documents choices[0].message.content as a string and usage.prompt_tokens/completion_tokens. The implementation may accept only the existing compatible shape; do not add provider-specific fallbacks without a test and documented evidence.
5. Do not claim that the old paid request's root cause is known. The old receipt has no status or response digest.
6. Keep the existing accounting rule: a request that may have been sent but has no verified usage stays usage_status=unknown and is charged at its reservation bound. Never settle a sent request at zero merely because the provider returned an error.

## Test-first implementation

Add deterministic local fake-server or fake-connection tests. Tests must assert both the visible classification and that sentinel secrets/provider bodies do not appear in captured errors or output.

Cover these cases:

- documented successful Chat Completions envelope with usage is parsed and settled;
- HTTP 400 is terminal and its numeric status is visible without the response body;
- HTTP 5xx is retryable and its numeric status is visible;
- HTTP 429 retains existing rate-limit behavior;
- malformed 2xx JSON, missing choices, non-string content, and empty content remain safe bounded failures;
- budget ledger remains conservatively unknown for an attempted HTTP request without valid usage, and settles to zero only when the code proves the HTTP call never began;
- handler/result serialization stays within the current result contract.

First demonstrate RED on the focused case(s), then implement. No live network call, real model, credentials, production source, or expense is permitted in this lane.

## Tests and finish

Run the focused tests:

~~~powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -p no:cacheprovider --basetemp tmp/n4t1-test tests/unit/test_narrative_http_model.py tests/unit/test_narrative_model_caller.py tests/unit/test_narrative_summarize_handler.py
~~~

Also run Ruff on only the changed Python files and git diff --check. Keep the test root inside this worktree, verify it was not relocated, and remove only that exact generated root after the test exits.

Commit and push the lane branch; do not merge to main. Return a short handoff with base/head SHA, exact changed paths, RED/GREEN commands and durations, classifications added, confirmation that no network/provider/credential/source was used, and any remaining limitation. MAIN will run the shared selected contracts and one bounded real-source check after integrating this lane with N4-T2.

## MAIN integration boundary

MAIN owns the real MiniMax request and total $0.10 / 60,000-token batch cap. MAIN must use a new run ID after local tests pass; it must not retry the old unknown reservation. This lane must not edit the N4C run ledger or charge.
