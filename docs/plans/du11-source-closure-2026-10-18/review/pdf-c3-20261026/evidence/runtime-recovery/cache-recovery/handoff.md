# C3 completed-cache recovery handoff

Status: IMPLEMENTED; awaiting ROOT independent review. No commit or push by this worker. Changed only `src/company_wiki/automation/narrative_batch.py`, `src/company_wiki/automation/narrative_generation.py` (ROOT's explicit extension for proven eager identity bug), and new `tests/unit/test_narrative_batch_recovery.py`. Original integration file remains byte-for-byte unchanged; its SHA matches prior independent diagnosis.

## Root cause and design

The binding decoder previously called `_validate_normalization_binding` before discovering that an invocation only needs a completed historical publication. That method requires full equality with today's PdfReading recipe, so a valid old parser/runtime/implementation identity was treated as an invalid frozen record after deployment. A second actual RED showed `generation_manifest` still called current `parser_component` even when the caller supplied its complete frozen recipe, then discarded the current result.

History and executability now have separate proofs:

- Binding decode keeps request hash, exact members/events/jobs, source facts, frozen generation hash, original accounting, and model options. It never rewrites the frozen recipe or selects an old SDK.
- Completed output uses existing publication metadata to compare the full frozen generation and its hash. Every recipe field remains significant. Removing a recipe and rehashing cannot disguise a modern publication as legacy. The existing generation owner resolves base to final selection generation; its check compares the complete base including recipe. Truly pre-generation/pre-recipe historical publications retain the existing public-read contract.
- Existing public readers still own current SourceRef/root bytes and evidence/locator replay. A historical completed record is not itself a claim that today's content checks have succeeded.
- Any path that actually resumes work (pending/paid response/activation recovery) must pass the original strict normalization/recipe validation before runtime activation or workers. New generation freezing retains strict validation. SDK/backend/options drift is never admitted for execution.
- `generation_manifest` uses explicitly supplied recipe identity directly; new generation without supplied recipe still obtains its real current reading recipe. There is no version whitelist, fake callback, new ledger/database, cache, SDK chooser, or approval chain.

## RED and verification

- Original exact parser upgrade node: **RED**, `BATCH_FROZEN_BINDING_INVALID`, process 19.693s, 0 actual provider calls. `red.log/xml` + `red-receipt.json`; PID gone, TEMP restored absent.
- Deep owner RED: `units-final-0.log/xml`, both request schemas failed because decoder reached forbidden current `describe_recipe` through `generation_manifest -> parser_component`. Corrected in generation owner; schema1/2 now retain original recipe without reader instantiation.
- Base/final RED: `final-selection-red-0.log/xml`, new exact generation check first rejected a valid base→final identity. Fixed by existing `reading_candidate_manifest`, not by ignoring fields; retained unit checks exact base recipe drift rejection.
- Final recovery unit file: **25 passed**, `cross-run-final-0.log/xml`, process 2.232s. Covers all recipe metadata equality, missing/malformed publication proof, recipe removal, genuine legacy records, immutable request source/model/profile/limit, both binding schemas, completed zero-execution path, incomplete/unactivated strict admission, and unknown recipe rejection.
- Original exact parser node: **1 passed**, `verified-final-1.log/xml`, process 26.442s, exit 0. All original assertions intact: old output/budget/jobs immutable, new run uses distinct upgraded generation, repeat no work, actual parser traces old/current, source/foreign-job protection. This preceded only the separately covered base→final resolution addition; no other changed branch.
- Actual PDF cross-run cache: **1 passed**, `cross-run-final-1.log/xml`, process 36.887s. Original configured fixture runs twice and requires one loopback summary POST in total, zero new run budget, same exact public pin/bundle and original reservations.
- Actual schema2 paid outbox/default upgrade: **1 passed**, `paid-resume-0.log/xml`, process 34.770s. Original fixture checks one old loopback POST, no repeat POST during paid/activation restore or cross-run reuse, unchanged charge and public old selector.
- Related existing units: batch **17 passed** (`final-unit-1.log/xml`), generation **12 passed** (`owner-final-1.log/xml`). Counts overlap with earlier runs; do not sum executions.
- Final `mypy --platform linux` both edited source files: PASS (`mypy-linux-final.log`). Scoped `git diff --check`: PASS.

Initial original-node GREEN assertions completed in 47.42s but plugin process shutdown reached the 55s harness boundary. `green.log/xml` retained; that invocation is not counted as a successful exit. Two subsequent exact runs exited 0. Early new-test fixture enum/time-field/syntax mistakes are retained in `unit-red*`, `decoder-final*`, and `final-unit-0`; corrected without reducing assertions. Plugin-free focused runs produce only the harmless existing `asyncio_mode` unknown-config warning because no selected test is async.

## Final binding, bounds and limits

`handoff.json` contains raw and normalized-LF SHA for all three changed files and unchanged original integration. Final LF SHA:

- narrative_batch.py: `770d482454bce479c1b737272e5d115b0608f2d5b43de5b8acd654c87f2c1a39`
- narrative_generation.py: `caf25bdd7d8903c975341feb07a07452768e7896f30a9a95ba0bd81a200fd2e4`
- test_narrative_batch_recovery.py: `76aa67b4bf64f9d3504f2541b32be99493986e4e1f67eb95c564c692e22d5f34`

All integration runs used normal host `C:/Miniconda/python.exe`, explicit worker-owned TEMP/TMP under this handoff directory, Windows Job assignment before child stdin release, and bounded per-node process waits. Final receipts confirm every owned PID absent and every TEMP restored absent; no directories remain here. Production config diff is empty. No real supplier call, download, production catalog/AUTO DB write, source-original copy/modification, global skills write, hooks/gate edit, other-repo write, commit or push. Other agents' concurrent files were left alone.

The parser-upgrade policy fixture has no narrative POST, so it does not alone prove paid PDF model-content compatibility. Paid fixture recovery and PDF cross-run cache are separately verified; real-document content/semantic C3 acceptance remains ROOT's separate main task. ROOT should independently inspect these three final files and run the necessary final node before integrating normally.
