# Fixed71 PPTX partial diagnosis

HEAD8479b8ad1eae5031ca6d01d5e540824cafa4a60f. Actual check is FAIL: `partial; reason=None; document_errors=[[]]`. This is not evidence that complete/verified source processing succeeded.

## Confirmed common cause

`Suite.setup()` exports `[src,scripts,config,tools/dayu_sdk_bridge.py]` from current CWP HEAD. The committed `config/local_ocr.json` is copied into the isolated wiki. The PPTX format request has no normalization override, max_seconds30 and outer40. `narrative_batch._run_owned` constructs `NarrativeNormalization.from_project(... enabled=True)` for fresh PPTX. Pure identity-only inspection proves2.0.0 with inherited config,1.1.0 with explicitly disabled config; no adapter/engine/inference was created. Thus the prior pure-parser capability-gap fixture silently became configured native OCR. The old real22-page parser receipt took145.549077s; a30s whole-deck OCR invocation can expire before a terminal selection error is stored.

## Exact actual visibility limits

The new report retained actual aggregate partial, no top-level reason, and empty document-error list. It records pytest command26 (107.645s, return1, stdout2371B/SHA), and PPTX CLI processPID50512. Runner deletes subprocess stdout/stderr after hashing; Suite.full discards pytest failure body and only carries selected JUnit properties. `test_root_restored_absent=true` confirms original DB/jobs/requests/raw batch JSON/XML are gone. Exact select/summary/verify states, artifact publication, budget/reservation balances and bundle quality cannot now be recovered. All such fields in diagnosis.json remain null as unavailable, not zero/absent. No completed stages or artifact are claimed. Actual deadline-in-OCR is strongly supported, but the exact interrupted stage is not proven by retained telemetry.

## Minimal repair/TDD design

1. Offline replay export must use explicit fixture configuration, never inherit arbitrary host local_ocr.json. Pure fixture binds parser1.1.0/no OCR snapshot even when the host HEAD has valid OCR config. Existing live/current configured snapshot behavior stays explicit and preserved.
2. Before assertions/cleanup, record tiny actual runtime evidence: batch JSON budget/doc status/pin, each scoped job stage/status/error/result kind, active/terminal attempts, whitelisted actual reservation states and charges, source/parser quality counts and public replay status if available. No DB/raw/text copies; missing evidence stays null.
3. Deterministic RED for accidental host OCR inheritance and telemetry lost at cleanup; preserve unrelated errors/partial/deadline as FAIL unless existing exact unpublished named capability gap and zero model budget/calls proof permits BLOCKED. Never accept arbitrary partial.
4. One owned tiny image-only PPTX through public finite CLI with declared pure config should yield named unpublished PARSER_INCOMPLETE with no model call; validate actual jobs/ledger before cleanup. Separate synthetic nonterminal/deadline example remains FAIL. This does not require original22OCR or full71. MAIN real configured whole-deck paid node owns successful bundle/count/public replay acceptance.

Only read operations and pure config/identity composition were performed in this diagnosis:0 OCR,0 engine init,0 supplier,0 source/config/PWF/old-report mutations.
