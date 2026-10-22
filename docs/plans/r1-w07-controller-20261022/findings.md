# Findings

- Configured NarrativeHTTPModel.generate supports response_sink after complete bounded HTTP bytes and before envelope decode.
- v5 worker_factory creates PaidResponseArtifacts; BudgetedNarrativeCaller.capture writes object and attach_paid_response. Legacy 0.8 does not enable this writer.
- Current protocol: selector 0.9.0; reading-model-input/5; reading-source-extractive/5.0.0; narrative-model-request/6 ranking decisions, not model-authored summary prose.
- Phase-C gold-conditioned observer and generate-level forbid_post are unsuitable for holdout paid replay.
- The controller will observe actual HTTP POSTs and native states. RF consumed parameter/formula remains a separate ROOT handoff, explicitly not_consumed.


## Preflight boundary: evidence, not a second native run

The actual configured preview is the same UTF-8 adapter request body and configured output limit; the bound is `len(body) + 128 + max_output_tokens`. Two rejected experiments are retained as real RED: a nonpaid RETRYABLE native run cannot resume terminal dependencies; a separate preview run leaves the same-generation recovery owner and blocks the formal run. No SQLite/locator cleanup was used to hide either failure. Neither is treated as a new production recovery requirement.

The final preview instead composes the existing public Config → batch source events → NarrativeSelectHandler → build_model_request → NarrativeHTTPModel.request_bytes chain. Its explicit in-memory preview context is non-native and never creates/claims a task or signs a lease. The existing pure materialize_plan builds DTOs only; no AutomationStore is constructed. Normalization uses the same project configuration and from_snapshot worker setup. Preview does not claim a final frozen generation: the actual formal native run alone owns that manifest.

Formal configured CLI execution compares request bytes both before the native caller can reserve and immediately before the actual HTTP request. The original secret-free body is kept once. A changed output configuration is a named zero-POST refusal. Preview cannot reduce model output settings to fit a budget. Source references, configured fingerprints and actual v5 generation are passed onward; availability/reviewer gold are not injected into model input.

## Test layering

Fast spec/body contract tests live in unit/. Multi-process configured lifecycle tests live in integration/ and run explicitly at acceptance nodes. Previous full runs took 68.73s and 121.80s under concurrent load, which is why they were moved out of unit CI. CI/precommit is unchanged; there is no new permission flag.
