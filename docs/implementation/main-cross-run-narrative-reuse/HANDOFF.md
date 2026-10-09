# Main cross-run narrative reuse — handoff

## Delivery

- Owner: main_official_flow_finish. Isolated branch codex/main-cross-run-narrative-reuse-20261009, base f788a07aa7a6e12b8cc2228c44931ca2df1e68ed.
- Implementation commit: 002824df4c3275d171e22fd56f94b946095c0690, normal hooks passed. This scoped handoff commit contains evidence and the stricter mandatory completed POST-loss test. The final commit ID is reported to MAIN after commit and is not self-recorded in its own file.
- Scope: five production automation/artifact modules, eight owned/new responsibility test files, this package. No new task/budget DB, source catalog schema/table, research state, permissions, human-signoff or provider integrations.
- Strict POST-loss completion depends on MAIN budget correction ce116dddb07184d99fe8fa9661171d2bc4aa88cc. Only its run-store module was tested as a temporary overlay, restored byte-for-byte. Do not cherry-pick the full MAIN commit into this branch; it contains unrelated MAIN plans. MAIN already owns the actual correction.

## Root cause and implementation

Request/run/budget policy affects original job identity; removing run ID would violate unique run-job ownership. Stable per-source generation now identifies existing complete visible artifacts. Each current run freezes an exact artifact pin in existing binding_json; misses alone receive its normal three AUTO jobs. Historical reservations stay in the original run. Artifacts retain their original work/effect and generation facts; current raw admission and public reads apply current policies/facts.

The source-generation manifest includes exact SourceRef, effective source class/title/kind/language, actual carrier parser, prompt/model/request/selector/bundle/producer/material versions, profile and effective generation model options. It excludes run ID, other sources, budget/time/storage/pricing/key-env/read-policy/physical root. Existing artifact metadata_json stores generation_manifest and generation_sha256. `visible_generation_candidates` performs bounded read-only same-source lookup (default 32, maximum 100), permitting a compatible prior generation behind a newer incompatible one. A corrupt matching artifact is refused, not converted into permission to spend.

All-hit uses read-only artifacts, no CatalogStore constructor, no worker activation/model reservation and no worst-case final preflight. It still measures actual owned persistent growth. Mixed hit/miss owns only new miss jobs. Publication uses the existing dispatcher/AUTO outbox; no alternate pipeline or ledger.

## Interfaces for MAIN

- `generation_manifest(request, payload, *, execution_versions, parser_components=None)`, `generation_sha256(manifest)`, `find_reuse_pin(...)`, `read_reuse_pin(...)` live in automation/narrative_generation.py.
- Supply normalization owner's actual pathless normalization_identity result through parser_components at `_run_owned`'s generation_manifest call. No guessed OCR fingerprint is embedded. Physical model paths are rejected. HTML uses its own parser_component and does not absorb global PPTX version changes.
- Current single whole-source coverage gate: `read_reuse_pin` requires coverage_complete plus selected/completed or skipped_no_narrative/summary_not_needed. There is no second gate in batch/artifact lookup. MAIN's OCR integration must allow selected/completed derivations with honest whole-source recall=false after every selected locator is replayed; skips still need complete coverage/no evidence. MAIN owns this shared TDD change. Existing quality needs_review can mean source/extraction quality; it is not itself evidence of an unfinished summary.
- Optional `refresh: true` in narrative-batch-request/1 forces a new generation in a new run. Default/explicit false preserve old wire/hash; exact refresh resume adds no calls; changing intent for an old run is refused.
- Internal `narrative-batch-binding/3` includes shared generation_settings, compact generation_manifests entries (settings_sha256, generation_sha256, source_inputs), reused_artifact_pins, current source facts and only owned miss event IDs. /1 and /2 resume semantics remain. 100-source regression proves the unchanged 262144-byte persistence limit.
- `narrative-generation-recovery/1` at catalog/narrative-generations/<generation_sha256>.json has exactly schema_version, automation_db, run_id. It points to the original existing AUTO and copies no jobs, statuses or accounting. Sorted OS generation locks serialize live cross-DB callers; original AUTO run/jobs/outbox/reservations determine recovery. Known terminal/settled/no-pending-publication state or exact visible proof retires the locator. Missing or unknown origin requires BATCH_GENERATION_RECOVERY_REQUIRED; it is not a permanent canonical AUTO path gate.
- Public SourceRef/SourceExport/narrative-ref/read DTOs unchanged. Current read expected_source still requires canonical_entity_id, market, security_id, document_kind, fiscal_year, fiscal_period (unknown nonfinancial fields may be null). Actual reads verify current source/hash/size, selected locator replay, original language and translate=false. A reused document result adds generation_status=reused while retaining artifact_ref shape.

## Verified boundaries

| Case | Actual result |
| --- | --- |
| Default configured HTML/PDF/TXT A then B | First three RED had 2 POST each; now one POST total per carrier, same pin, current public replay |
| Execution-only changes, different AUTO, moved raw root, tiny valid final/scratch limits | Hit, zero own tokens/cost and no CatalogStore construction |
| Parser/model/title/lang/kind/profile/fingerprint causal changes | Different generation; actual parser and forged attribution tested |
| Older compatible artifact behind newer incompatible one | Exact compatible prior pin |
| Refresh and failed refresh | New refresh one POST; exact resume zero; failure leaves old public bytes readable; known terminal pointer can retire |
| Missing/tampered/partial/prepared/legacy generation | No false hit/no duplicate spend on corrupt exact candidate |
| Mixed hit/miss | Existing pin plus only three new jobs/92 receipt tokens for miss |
| Concurrent same / different AUTO | Same DB named busy/retry; cross-DB waits for published candidate; one POST total |
| ACK then activation interrupted | Other DB recovery refusal before DB creation; origin outbox recovery publishes with zero additional POST; then other DB/read hit |
| POST then coordinator hard-killed | Before recovery one POST, no other DB/object. MAIN budget overlay restores owner to completed, old unknown fee retained; then other DB/read hit |

Final POST-loss artifact is 4069 bytes, SHA 9110e0833f1dc3fa44fc2e24faecdc113700210c2682c4e3f18a929d9062a2e8. There are two loopback POST total (lost request plus recovery), one unknown / zero unsettled reservation and 3474 conservative tokens / 3893 microUSD. Old unknown 3382/3782 remains; known recovery adds 92/111. Successful select/summarize/verify results each one, one effect and one visible object. New run has zero own charge, same exact pin, public locator_count=1/replay_status=verified, en/translate=false and zero added POST. No supplier requests occurred; these are engineering fixtures, not completed real-company supplier research.

## Test evidence

Exact commands, runner elapsed time, pytest summaries and config/TEMP assertions are in validation-index.json and the unmodified per-command .json/.txt files. Pytest time differs from wrapper time; do not add overlapping suites as a unique test total.

- GREEN-responsibility: 69 PASS / pytest 61.66s (implementation code gate; original budget case still allowed its old terminal behavior then).
- GREEN-compatibility: 143 PASS / 1 explicit external real-input skip / pytest 68.26s. Existing select/verify/model/evidence/public transport and batch contracts.
- GREEN-boundaries: 14 PASS / 1 explicit external real-input skip / pytest 166.56s; additional configured carrier/refresh/error paths.
- GREEN-integrated-kill-recovery-final: 1 PASS / pytest 10.90s, **mandatory completed**, temporary MAIN budget file only. The own base budget file alone is not claimed to satisfy this stricter test.
- GREEN-ruff and GREEN-final-ruff: --no-cache passed. Code normal hooks passed; no bypass flags.

Retained failed evidence is also indexed: RED-generation-identity collection import; GREEN-carrier-provenance wrong bundle.parser implementation; GREEN-outbox Windows spawn main-guard fixture; GREEN-final-flow guessed results table; GREEN-integrated-kill-recovery root-level public config fixture. Assertions and source contracts were retained. Real causal RED includes duplicate POST, bad per-carrier identity/provenance, expanded 100-source binding overflow, false visible-pointer refresh block, worst-case hit storage preflight and writer construction on hits. Filename GREEN does not make a failed run accepted.

## Billing/root-cause dependency and hygiene

budget-root-cause.md gives the exact existing store chain/columns. pre-budget-fix-kill-proof.json preserves actual old budget_exhausted, no local final effects/objects and full unknown charge. flow-proof.json holds corrected completion and public read receipts without full raw bundles/model response bodies. The corrected budget aggregation treats retries of one summarize job as one final-output slot; supplier tokens/cost continue to sum across attempts. Distinct jobs remain independent, and actual physical guards stay active.

budget-overlay-receipt.json records source commit, temporary authorization, old/restored SHA cfd28629ba573d09731830d7a6c5ed8baa45a89df70c5adfecae6b6d70156d83 and overlay SHA 219340d3c96273588b222842bec615b72ba2deb65148df974b47cfa8492d336b. validate_budget_overlay.py is the reproducible explicitly authorized single-file test overlay; finally restores even after failure. No overlay enters the scoped commit.

Every finished owned runner TEMP ends absent; protected production config hashes before/after match. Originals/foreign AUTO jobs stay untouched. No new index, installation, provider acquisition, production change, shared PWF write, other repository write, main merge or push. Legacy artifacts without truthful generation metadata are not inferred as hits. Unsupported historical parser locator replay remains a named read refusal, not SHA-only success. MAIN merges this owned code/test/docs, its budget correction and actual OCR composition, then verifies the exact merged main branch.
