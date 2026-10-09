# Transcript compatibility repair

Owner: fresh_transcript_compatibility. Isolated branch codex/fresh-transcript-compat-20261009, base 7762bfd1.

## Goal
Restore exact transcript 0.1.0 / 0.1.1 compatibility and current 0.2.0 replay using one actual per-format/version contract. Preserve source text, SHA and locator guards; unknown or forged versions fail closed.

## Phases
- [x] Reproduce the three exact push-gate failures before source changes.
- [x] Add compact legacy/current retrieval and unknown-version regression coverage.
- [x] Repair parser identity and retrieval dispatch in assigned files.
- [x] Run concentrated responsibility tests and read-only real MSFT index/query/resolve replay.
- [x] Commit source, tests and this plan with normal hooks and hand off to MAIN.

## Write boundary
Only src/company_wiki/automation/narrative_formats.py, src/company_wiki/source_catalog/narrative_evidence.py, src/company_wiki/source_catalog/narrative_retrieval.py, associated tests and this plan. No main/shared plans/config/CI/hooks/raw/installations or cross-repo writes.

## Next Step
MAIN independently reaccepts the latest snapshot-ownership branch tip, then owns merge, normal fullunit push gate and exact CI. This worker follow-up is complete.

## Errors
- Sandbox Git status falsely reported not-a-work-tree; normal OS Git status was clean.
- Delegated module paths omit src/company_wiki prefix; tracked file inventory resolved exact source paths.

## Error classification corrections
- Original assumption that resolver current parser metadata was a product defect was disproved. Correctly declared current producer 0.2.0 identity replays before the fix; old fixture declared PDF-shared 0.1.1 incorrectly. Two original assertions stay intact, fixture declaration now follows parser_component. Strict mismatch guard remains.
- Initial new HTML fixture had only one natural speaker; existing body proof requires two. Corrected synthetic fixture before genuine dispatch RED.
- Standalone Python harness initially loaded editable MAIN, rather than the assigned worktree. Pin PYTHONPATH to this worktree/src and assert loaded resolver path. No installation change.
- Real harness initially assumed every row has context_group_id; use the resolver public fallback to evidence_id. Source replay itself passed; no product change.

## Final validation
- Exact original RED3FAIL/0.97s; current correctly declared identity succeeds before source fix.
- Exact3 + new13 compatibility guard GREEN16PASS/0.73s.
- Final responsibility202PASS/1SKIP4.28s; optional real SEC original not supplied.
- Actual MSFT current parser0.2.0:481lines,body90–414,515units,41selected/verified/indexed/replayed,4model-query hits resolved. Source bytes/SHA/mtime and TEMP restored.
- Focused ruff clean; mypy evidence/retrieval2files clean; git diff --check clean.
- PPTX fixture version correction separately authorized after exact unchanged-base RED; no PPTX/normalization source changed.

## Independent acceptance follow-up

- [x] Reproduce external mutation of nested contract/evidence/locator/SHA after resolver construction and cache population.
- [x] Freeze constructor snapshot ownership; new resolver still rejects bad external input.
- [x] Prove same-reader repeated calls parse once, fresh valid legacy packages still replay, and real MSFT remains41/41.
- [x] Run concentrated checks, ordinary commit and updated handoff; MAIN repeats independent acceptance.

P2 final checks:ownership/retrieval31PASS1.06s;full concentrated responsibility208PASS/1SKIP4.38s;realMSFT41/41 retained with source bytes/SHA/mtime/TEMP unchanged;mypy retrieval clean;ruff source/test clean;diff-check clean. Earlier evidence preserved.
