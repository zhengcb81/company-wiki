# FF publication preflight — read-only preparation

Status: read-only inventory complete; ROOT subsequently authorized narrow JSON-output/common-focused-table repairs, not yet executed in this receipt. FF remains isolated at a9c2dcf7de2e70f50cb18caa8b4b038464391f9d. No main checkout/author tree/install writes, test execution, API, original or config/key reads for this preflight.

## Actual normal push and CI scope

`.githooks/pre-push` (active core.hooksPath=.githooks) always calls `tools/pre_push_gate.py --skip-install-sync --ci-tests`. This is a fixed35-file `tools/ci_tests.py::CI_TESTS` surface, not changed-file selection. Prior static stages are ruff, compileall, import smoke, public-contract mypy, unique test symbols, host assumptions, optional sibling config-doctor and root plan verifier/BOM; failures propagate. Installed skill drift is deliberately skipped by this hook. The focused child gets UTF8, no bytecode/cache/autoload and one owned Temp, timeout900. `--run-tests` would be a separate full-suite manual path; normal hook does not select it.

Remote `.github/workflows/quality.yml` runs this same `tools/ci_tests.py` once after static/type checks and the diagnostic. It does not run all tests. Current table includes four older transcript modules but none of the DU11 selection/contract/new-reader tests, so recent common fixes can escape this regression surface. ROOT authorized adding only pure selection+stubbed contract+new-reader controls to this one table, leaving heavy frozen-source E2E out of every push. No new gate layer is needed.

## Nine prior full-suite failures: accurate interpretation

Author final full-suite claim1320PASS/9FAIL/16SKIP is supported by its own and original independent review observations. However committed independent reviewer_report.md explicitly qualifies baseline equivalence: **8 reproduce at f1a939e5; ninth is live sibling CWP vendored-copy drift**. Do not repeat “all9 are the same frozen baseline”. The five relevant files (four test files plus complexity tool) are unchanged from f1a939e5 after line-ending normalization, so none is introduced by the current transcript patch; this does not erase unresolved roots.

- **4 complexity tests** are selected by normal focused push. They are the four subprocess JSON-consumer cases (two parametrized valid-source cases, invalid-source measurement and missing input), not score threshold assertions. The tool uses its own AST branch diagnostic, no radon/mccabe dependency, no complexity acceptance limit. `main` prints `ensure_ascii=False`; a Chinese Windows Temp path becomes GBK stdout while the test explicitly decodes UTF8. The historic reviewer reports UnicodeDecodeError and stdoutNone. The committed receipt only summarizes those stacks; individual raw four-failure logs are not preserved, so this is source-supported causal diagnosis, not a fresh rerun claim. The focused runner's current UTF8 environment masks this mismatch, but the CLI protocol remains host-dependent. ROOT approved a real Chinese-path/forced-nonUTF8 RED and a common ASCII-JSON producer repair; no threshold increase, case deletion or hook skip.
- **3 FC803 minimal-download cases** are outside focused push. Historical ensure exit1 reproduced at base according to independent review. Their actual deeper provider/fixture-contract reason cannot be established from the committed summary alone; its harness depends on live editable CWP plus temporary acquisition configuration. Keep this OPEN rather than asserting all are environment-only or rerunning full suite in preparation.
- **1 policy501 case** is outside focused push. The test expects the obsolete phrase `exactly schema_version`; current config owner correctly rejects the forbidden independent allowlist with a newer schema/optional-fields explanation. This is a stale diagnostic-text expectation, not evidence that an allowlist bypass was accepted. Preserve the semantic rejection test when later maintaining it.
- **1 host-assumption vendored-copy assertion** is outside focused behavior push (the separate guard still runs its own roots). It compares current sibling sources, so external source drift changes its result without an FF change. This is the specific ninth non-frozen-baseline observation, not reason to weaken current source validation.

## Actual CI dependency pin: publishing master alone is insufficient

Quality workflow clones **revenue-forecast remote default HEAD**, then invokes its `tools/ci_checkout_siblings.py --manifest compatibility/current.json --sibling-root ... --skip filing`. That manifest chooses CWP, and the workflow exports that checkout as PYTHONPATH/FILING_FETCH_V2_WIKI_SRC. It also materializes FF at the project-locator path for the existing doctor.

Read-only local RF HEAD and cached origin/main both resolve f8002f5fc8f56533c814f1616b7ecb68016f35e4; its committed `compatibility/current.json` (manifest_version FCAP-2026-08-09-r2) pins wiki6cd9b6d7ca4faee3348fdd8afcf70bf7e3d6a5fb and filing5001dcbef1845a08e90cda6f2a86365610a662af. This is a **cached/local observation**, not a new assertion about latest remote state. Therefore ROOT must check the concentrated dependency-pin owner and publish the compatible CWP producer through the intended registry path before treating new FF remote CI as compatible. This worker does not edit RF's historical/current manifest or other repositories to make tests pass. ROOT's explicit confirmation of actual remote producer flag still governs the ordered publication step.

## Three logical skills, two physical targets

- `.agents/skills/filing-fetch` is a physical directory.
- `.claude/skills/filing-fetch` is a Junction to that same `.agents` directory.
- `.codex/skills/filing-fetch` is a separate physical directory.

For3runtime files there are9logical addresses but **6physical selected writes**. `transcript_reuse_selection.py` is absent from both physical roots. Current source desired SHA and actual old SHA are the same across the two roots:

| Runtime | Old installed SHA | Desired reviewed SHA |
|---|---|---|
| transcript_companion.py |5cbba8dcdb15f9d61a232d6f15fc2b40ed2320f2b26226e85a5d2dbf4db3f7f7|7e3f28a5928270850af308b9d20f4187cbaa985f1e0a5b4dffb83c3a1c0084be|
| transcript_tool_transport.py |6b2a74890d84050f562b7440eb8d80048ade1fc30b2426c6bac439b0418eb19a|4bb18006bb608c3dc706a6ca3f70e77fe03513798ff815b464aad208a8f33026|
| transcript_reuse_selection.py |MISSING|8591e9968d5d23c4e056a32062ea4b4fdbac63c3421523d921f3176d93823231|

After producer publication and normal FF integration, use the existing selective `sync_installs_b3.py --install --file ...` service (or its exact selected-write primitive), resolve root aliases and deduplicate physical paths, recheck these old hashes/missing state immediately before writing, and touch only these3relative paths per physical root. Keep config/output/credentials and other files intact. Add the new dependency file before a dependent runtime could import it; final fresh-process import/identity check is needed because hash-complete is not execution proof. No installer or configuration reader was run in this preflight. Exact logical/physical file addresses and SHA values are in JSON.

## Next step

Carry out ROOT's newly authorized isolated JSON-output TDD repair and update the unique focused table; give that delta to a distinct reviewer. FF transport4bb18006 remains frozen. Wait for ROOT confirmation that CWP producer is remote and CI concentrated pin is correctly selected before merging/pushing FF or synchronizing installed skills. No new authorization file, provider or gate.

## Follow-up after the read-only snapshot

ROOT authorized implementation in isolated FF: realGBK/Chinese-path2RED plus common-table1RED, then ASCII JSON owner fix and3pure focused modules.135relatedPASS5.29s, Ruff4filePASS, transport4bb remains frozen; distinct reviewer pending. The35-file list above is the actual original preflight observation; current proposed table is38. No RF/main/install source changed. Separate exact4fileSHA handoff is FF docs/plans/du11-root-reception-2026-10-18/publication-maintenance-handoff.json. This addendum does not promote that delta to independently accepted/publicly released.
