# W03 implementation and replay

## Owner and scope

Assigned worktree C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki, branch codex/fresh-summary-20261009, base d6444ef9. Source write set: automation/narrative_model.py, narrative_http_model.py, narrative_model_caller.py, narrative_summarize.py. Selector/parser/official acquisition/FF/ET/RF/CI/hooks are not edited. PublicSummaryClaim/SourceSummaryDraft DTO and public source identities remain unchanged.

## One-call interface

1. from_selection projects every selected original row, e-aliases and source-backed g-alias member lists from existing selected_summary_input. Rawtext/role/quality remain intact. Full canonical group identity is in the input hash.
2. HTTP request_bytes binds compact output planning to the actual configured max output tokens. Existing model, output field, endpoint, temperature, thinking/reasoning and limit are unchanged. The same reservation still hashes actual HTTP bytes. Target <=8 material claims/180chars is only a documented prompt heuristic; maximum20claims/280chars and actual token/byte caps remain authoritative.
3. Model may declare evidence_group_ids:[g..] plus explicit evidence_ids. Every declared group needs all its supplied members; no automatic expansion. Unknown/malformed/null declaration or missing member discards whole claim. All-invalid fails with a static rule; good sibling is retained with summaryneeds_review. Explicit[]/legacy narrower claims stay consumable with deterministic partialcontext diagnostic. No human permission path.
4. Alias/canonical-ID duplicate citations, external IDs, references beyond actual selected count, >20claims and >280char producer claims are invalid. Existing persisted long summaries remain readable through canonical result/bundle readers. Schema1.4/prompt1.7 invalidates new-generation caches.
5. Provider length completion carries only static finish_reason:length and bounded integer UTF8contentbytes through the existing terminal failure; supplied paired usage settles exactly once. No body/reasoning/key copied to diagnostics, no blind retry and no new queue/run ledger.

## Test replay

Use normal OS Python with UTF8, bytecode/cache disabled and a TemporaryDirectory basetemp. Only minimal Windows OS variables are inherited (SYSTEMROOT/WINDIR/PATH/COMSPEC/TEMP/TMP/USERPROFILE/APPDATA/LOCALAPPDATA); no provider credential read. tests/conftest blocks sockets; existing real HTTP adapter/CLI fixtures allow only their explicit127.0.0.1 stubs.

New contract modules: tests/contract/test_narrative_output_plan.py and tests/contract/test_summary_group_coverage.py (29 cases). Shared source-derived synthetic fixtures explain their provenance and distinguish old sealed US3membergroup from corrected W02-style2membercommercialgroup plus unrelated consumerbullet.

Concentrated responsibility bundle: these2modules + unit model_request, model_aliases, model_usage, model_caller, http_model, summarize_handler, model_config, run_store, partial_summary + integration narrative_batch_budget_and_resume. Main publication runner must include the new contract modules alongside its shared fast contract set; this lane cannot edit CI/hooks.

Independent grouped review reports are separate immutable stages. Failures remain recorded; final acceptance does not claim any real-provider or company semantic M3 acceptance.

## MAIN handoff

After localM2 review/commit, MAIN integrates source commit, verifies exact current main and normal hooks/CI, then uses installation_delta.json for selected runtime files as applicable. Do not sync config, credentials, output or complete skill directory. Preserve all sealed original attempts.

M3 must independently rerun sameCN annual/HKc4/USc3/c5 in fresh attempts with configured provider/current cumulativeUSD20/2M budget, actual usage and fulloriginal locators. Teststub planning compliance never proves realmodelcompliance; realtruncation remains terminal/accounted. Group mechanical coverage never proves proposition entailment. W12 owns same-input/no-new-charge reuse receipts.
