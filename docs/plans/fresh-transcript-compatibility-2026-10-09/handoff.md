# Transcript compatibility handoff

Branch: codex/fresh-transcript-compat-20261009. Base:7762bfd1c5542fbc37e606c361cb6d661b0f02c3. Exclusive worktree:C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki.

## Cause and changes

Product compatibility defect: duplicated transcript version lists rejected preserved0.1.0. One explicit transcript parser contract now selects original legacy layout for0.1.0/0.1.1 and natural-body layout for0.2.0, consumed by parsing, generation identity and replay. PDF shared0.1.1 remains separate. Unknown versions return named errors; old packages never fall back to current semantics.

Two original retrieval REDs were fixture declaration errors: correctly produced0.2.0 packages were declared with PDF-shared0.1.1. Pre-fix actual identity proof shows a correctly declared0.2.0 package already replays. Only fixture setup now follows actual parser_component identity; original behavior and tampering assertions unchanged. Supported-version mismatch remains rejected.

Explicit official transcript_html replay reuses existing bounded original-byte extractor and material line/hash verification. Raw path comes only from trusted caller mapping; package paths are never read. Source ID/SHA, text/SHA and locator guards remain strict.

Concentrated suite uncovered unrelated stale all-format1.0.0 PPTX transport assertion. Same RED reproduced on untouched base in an owned temporary code/synthetic-test archive. MAIN authorized only test expected versions from separate declared PPTX1.1.0/HTML1.0.0 constants; all actual transport/read/replay/locator/cleanup assertions retained.

## Exact changed implementation/test paths

- src/company_wiki/automation/narrative_formats.py
- src/company_wiki/source_catalog/narrative_evidence.py
- src/company_wiki/source_catalog/narrative_retrieval.py
- tests/unit/test_narrative_retrieval.py
- tests/unit/test_transcript_parser_compatibility.py
- tests/integration/test_narrative_format_transport.py
- This own plan directory only.

## Validation

Original exact RED3FAIL0.97s; exact3+new13GREEN16PASS0.73s. Final concentrated responsibility202PASS/1SKIP4.28s. Skip only optional CWP_R6_HTML_SAMPLE absent. Focused ruff clean,mypy evidence+retrieval2files clean,diff-check clean.

True preserved MSFT HTML:273436bytes,SHA bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656.481 extracted lines,body90–414,515units,41selected/verified/indexed/resolver-replayed spans and groups;query models4hits resolved. Exact bytes/SHA/mtime unchanged. Owned TEMP and TEMP/TMP env restored; external/provider/modelcalls0,cost0. No original copied into Git. This proves the selected-only in-memory bundle resolver; catalog/StockWiki consumer API acceptance is not claimed.

For independent replay, pin PYTHONPATH to this worktree/src and run replay_real_msft.py with --raw pointing to the preserved mFresh original and --output pointing to a new owned result file. The harness asserts its loaded resolver belongs to the same worktree and performs no model/provider call. Plain python may otherwise load an editable MAIN installation.

MAIN owns independent acceptance, merge, normal fullunit push gate and exact CI. This worker performed no push, merge, installation, production config/raw write or cross-repo write.

## Independent acceptance P2 follow-up

Independent review's21 focused tests passed but exposed mutable external bundle/cache ownership. Fixed with a deep construction snapshot of source-record dictionaries; raw-path mapping was already independently owned. An existing resolver consumes its frozen initial input, so external contract/evidence/locator/SHA changes do not rebind its cached replay. A newly constructed resolver consumes new input and still rejects unknown/mismatched parser versions, invalid text/SHA and locators. No per-call parse added; same-reader repeated resolve and resolve_group prove one parser call. Raw source SHA is still checked on every read.

Follow-up writes only narrative_retrieval.py, test_transcript_parser_compatibility.py and this PWF. Ownership RED5FAIL/1PASS0.80s retained; compatibility+retrievalGREEN31PASS1.06s; latest concentration208PASS/1SKIP4.38s. Real MSFT rerun41/41 in real_msft_replay_snapshot.json retains90–414body,481lines,515units,4queryhits,immutable source bytes/SHA/mtime,TEMP/env restoration andzero model/provider/cost. Existing earlier RED/initial classification/PPTX base proofs unchanged. MAIN must independently reaccept this latest branch tip before merge/push/install.
