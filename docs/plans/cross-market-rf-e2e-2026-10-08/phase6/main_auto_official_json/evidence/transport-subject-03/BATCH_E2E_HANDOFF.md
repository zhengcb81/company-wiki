# Mixed official JSON public CLI E2E — final handoff

## Result and boundary

Five actual public production CLI E2E tests PASS in80.38 seconds, NODE04. No external provider/model destination was used: nine total real HTTP POSTs went only to127.0.0.1. This validates the mixed batch source/worker/ledger/publication/transport node with independent synthetic originals; it does not claim real-provider, full-production AUTO or every remaining MAIN plan is complete. No commits were created.

Files: tests/integration/test_official_json_batch_e2e.py and tests/support/official_json_batch_fixture.py. Their exact SHA256 and result are in batch-e2e-handoff.json. Root/pipeline owners integrated production sources; the separately delegated common ledger repair is documented in RUN_PROMPT_HANDOFF.md.

## Reproduce

Use the repository isolated pytest runner with plugin autoload disabled, explicit timeout/async plugins, bytecode/cache disabled and owned TEMP basetemp. The exact successful argv and time are saved in batch-e2e-node-04.json. Selected test: tests/integration/test_official_json_batch_e2e.py. Run this at the large integration node; do not add every spawned-worker scenario as a commit permission.

The fixture scans one real TXT, imports two actual shared official JSON pages containing two issuers through the production importer and persists both actual projections. It writes config/catalog.json and all request/DB/work artifacts under an owned TEMP project. Real public batch subprocesses run the same select/summarize/verify workers and AUTO store. A local HTTP endpoint checks actual raw model-request1.4 vs projected model-request2 inputs and responds from actual supplied evidence; there are no fabricated HandlerResults or hand-mutated successful jobs.

## Verified checkpoints

- First mixed A+B+TXT run: exactly one POST per missing item, three successful jobs per item, correctly compacted projection terminal2/raw terminal1, actual synthetic ledger276 tokens/333 micro-USD. No unsettled or unknown reservations.
- Public projected reference2 discovery and read2: exact subject/generation/ref pins, artifact full SHA and byte size, verified original locator replay. Full expected issuer identity stores unknown fields, while request constraints retain the concrete actual provider company ID.
- Source semantics: each issuer selects native spans from both real mother pages, preserves management/investor_question roles and original zh/en language, excludes provider translations, and never mixes the other issuer's record IDs. Raw TXT still returns the legacy ref1/bundle2.
- Resume of the exact completed run: no new POST, unchanged ledger and refs, no repeated paid request. Separate identical run: zero POST, zero newly charged usage, zero new jobs and identical published refs.
- Explicit refresh: three new POSTs and newly visible artifact versions; terminal and public replay checks repeat. Partial hit: initial A costs one POST, mixed A+B+TXT then costs only B/raw two POSTs, retains A's artifact pin and creates six jobs.
- Preparation negatives: changed second-parent bytes, inactive second parent, valid but absent projection identity. Each fails before any model POST or AUTO DB materialization and reports no published artifact/zero charges.
- Every case: original raw+sidecar bytes and config unchanged, mutation fixture explicitly restored, whole owned project removed, prior test directory contents restored. Pytest effective basetemp cleanup reports removed:true.

The nine synthetic HTTP calls account for828 tokens/999 micro-USD under test pricing across separately charged runs; these are test ledger values, not external supplier charges.

## RED history and systemic corrections

Initial transitional RED was1FAIL/3PASS while dispatcher lacked projection_loader; the temporary constructor mismatch was fixed by the owner. Stable NODE01 then exposed the true common ledger defect: run.prompt_version raw1.7.0 was compared to projection official-json/1.0.0 and a binding conflict was mislabeled as budget exhaustion. Ledger now derives each job's exact prompt from immutable binding.job_prompt_versions, preserving old absent-map behavior and real caps.

NODE02 made correct HTTP calls and settled usage, then failed terminal compaction. A temporary sys.settrace entry point around the actual public CLI captured store._compact_terminal_narrative's identical single-prompt assumption; source owners made terminal compaction and reservation share the pure model_prompt_version helper. Trace stores code location and safe synthetic exception message only; no locals/credentials or complete temporary database are retained.

NODE03 passed processing/compaction/partial reuse but the test's read2 request included null issuer constraints. The fixture now sends actual concrete constraints and validates shape with NarrativeReadRequest before the public subprocess. No production safety or source/issuer/replay assertion was relaxed. NODE04 passes all five tests. Original RED, NODE01/02/03 logs and code-only trace remain alongside the final result.

## Static verification

Final Ruff check on the two E2E files, unique ledger source and new ledger responsibility test passes. Ledger51 new+old tests and mypy also pass; see RUN_PROMPT_HANDOFF.md. No provider, production configuration, installation copies or shared PWF were changed by this package.
