# W18 ROOT independent intake review

Reviewed author HEAD `b697bcf9b84de52b9d47c811554043e10ef2b551`, implementation/review binding `faa488a7cdbfe0f0aec953bb6cdfcf52baf7813e`. Read all seven Python tool files, both tests, manifest/current gold samples, correction ledger, all independent reports, findings and handoff. Author worktree remained read only; explicit worktree Git status was clean. Full base..HEAD diff has 45 allowed paths and no production src/config edits. Later commits after reviewed implementation only alter documentation/review/correction wording, consistent with the card's no-repeat-review exception.

## Verdict

**NOT YET ROOT ACCEPTED**. The oracle/baseline delivery is valuable and may be imported with targeted fixes; its product failures are valid findings, not grounds to demand artificial green source coverage. Do not conflate source-side delivery completeness with summary/RF semantic acceptance.

## Confirmed findings to resolve in one ROOT-owned correction node

### R1 — Bootstrap overwrites an existing config even on rejected input (P2)

`tools/holdout_replay/__main__.py:72-80` creates/reuses the requested lake and writes `source_catalog.yaml` before checking each source binding and before source-root containment. `bootstrap.json` is also unconditional at line 121. A mistaken existing lake argument can damage prior evidence/config, including returning exit 2 *after* rewriting it. H11's success/failure no-overwrite rule was not actually covered for this command.

Independent neutral probe: existing config sentinel + out-of-root binding gives exit 2, `old_config_preserved=false`. Fix by validating bindings/SHA/containment first, allocating a new owned lake atomically, never overwriting existing config/catalog/receipts, and using failure cleanup limited to newly allocated content. Do not introduce a human approval mechanism.

### R2 — Attempt allocation and refusal rewrite old evidence (P2)

`runner.py:49-59,107-108` uses a check then `mkdir(exist_ok=True)`: concurrent invocations can choose the same attempt. The explicit existing-result branch protects a result file and restores the sentinel, but line 235 always rewrites `attempt.json`. The author's no-overwrite unit test asserts only result/sentinel bytes, missing the receipt.

Independent neutral probe forced the author's own tested reuse scenario: sample status `refused`, `old_receipt_preserved=false`. Allocate each attempt with atomic exclusive mkdir/retry; an already owned/existing attempt must be rejected without modifying any old file. Test whole-directory inventory, not only two files, and a same-stamp collision.

### R3 — Changed original is accepted as successful observation (P2)

`worker.py:220` records whether original SHA changed, but `runner.py:210-214` accepts any zero-exit result unless it reports a sent request. A payload reporting `original_unchanged=false` and unequal before/after hashes still produces sample `ok`, overall `ok`.

Independent neutral probe confirmed exactly that result. Validate the source-bound result identity and its integrity outcome, retain failed payload bytes, and return an invalid/failed observation with a precise reason. Compilation/semantic product gaps can remain honest non-success observations without deleting evidence.

### R4 — Financial-only mandatory gold conflicts with current user scope (P2)

`gold/w18-cn-beigene-h1-2024.json:46,79` makes `h1-loss-narrowed` and `h1-rd-ratio-drop` required_business; the former consists solely of net-income and cash-flow statement cells. The latest instruction explicitly routes historical financial statements to Sina instead of requiring PDF extraction. Move financial-only scalar/table checks to correctness_if_emitted (or equivalent optional correctness), preserving them as useful numeric traps. A revenue target with the business-growth causal sentence can remain business-relevant without treating all statement cells as mandatory. Audit other gold files for the same obligation mistake. Version and explain this scope correction; retain v1/v3 and baseline results.

### R5 — Neutral PDF is created but never replayed (P2)

`test_runner_boundaries.py:224` writes `acme-note.pdf`, yet the fixture mapping only contains TXT and HTML, and `make_mini_manifest` only supports these keys. Therefore the claimed neutral PDF/TXT/HTML chain does not include PDF. Add the PDF to manifest/bindings with its real PDF MIME/independent quote and assert it actually executes; use the current frozen ROOT commit as well as legacy baseline where appropriate. The real baseline has PDFs, so this is a neutral test coverage gap rather than proof of a broken production PDF engine.

### R6 — Cross-drug reasoning and incomplete local support in gold (P3)

`h1-bgb16673-300.reason` currently cites the Sonrotoclax target as corroboration for BGB-16673's phase-3 date. They are different drugs. I independently read physical pages 9,25,26 of the real H1 source through PyMuPDF, read only. Page 26 contains BGB's own FDA and Q4 2024/Q1 2025 plan sentences: bind the target directly to this paragraph instead of another drug. The fact's existing anchor stops before both sentences, despite `must_preserve` demanding FDA indication details. Similarly `h1-sonrotoclax-plan` demands fast-track eligibility absent from its two quoted anchors; `h1-rd-ratio-drop` demands 81.12/25.87 while its anchor only contains 55.25. Extend source-bound minimal support for retained demands. These truths are in the source; the defect is insufficient local evidence/incorrect corroboration, not a demonstrated false source fact.

## Positive findings and interpretation

- Gold commit `5e4488bb` at 10:21:12Z predates first candidate attempt by roughly 76 min, consistent with reported receipts. Corrections are versioned with reasons, initial oracle is retained; revised gold is not a fresh untouched holdout and must be labelled accordingly.
- Three markets, five distinct companies, eight distinct SHAs and PDF/HTML/DOCX carriers meet breadth. Prior-use scope is explicitly documented rather than asserting global novelty from name alone.
- No model POST is present in the reviewed call path: configured_preview serializes request bytes, not a network request. Zero network fields are construction claims, not observed instrumentation.
- Default direct selector and pinned 0.9 compile path are now disclosed separately. The old default direct parser/selector observation is a diagnostic baseline, **not a measurement of the entire PDF-C1 production owner**; causal comparisons must keep this generation difference visible.
- All targets are not_reviewed for summary. Quote matching or a DU mechanical PASS is not semantic truth/summary/RF acceptance. ROOT should not advertise 10/96 or 16/96 as completed semantic business coverage.
- Product findings F1/F2 are not yet proven root causes: direct observer uses normalized DOCX while delivery prose claims parse_transcript_text, and selector generations differ. Preserve raw failures, correct the explanation, then use actual production routing probes.
- Complete-scope review is bound to implementation commit and post-commit source changes are absent. Some SHA fields in handoff are truncated and pinned at an older code commit; use final full hashes in ROOT receipt for reproducibility rather than rejecting the entire delivery over documentation style.

## Execution evidence and limits

`probe_boundaries.py` imports only the fully reviewed tool functions and replaces producer validation/subprocess/source resolution with neutral mocks. It does not run author test suites, real source batches, LLM/provider calls, downloaders or author shell scripts. All probe writes were inside this independent scratch directory; temporary probe root restored absent. Actual outputs: `probe-results.json`.

ROOT owns isolated deployment, actual test suites, fresh candidate real replay and final corrected-version review. This intake does not pre-sign those unexecuted steps.
