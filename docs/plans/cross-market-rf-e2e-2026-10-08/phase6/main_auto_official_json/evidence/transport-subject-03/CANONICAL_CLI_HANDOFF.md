# P7 explicit canonical producer public CLI E2E

## Delivery and result

Unique new file: tests/integration/test_official_json_canonical_cli_e2e.py. Three test functions, six final cases. No production or support fixture edits by this task, no commits, no vendor calls. Existing support creates owned TEMP originals/catalogs and loopback HTTP. Final file SHA is in canonical-cli-handoff.json.

The original three full public cross-boundary cases PASS in46.79 seconds. After root requested shape coverage, only the three new list/dict/null parameter cases ran and PASS in8.76 seconds. The already passing full canonical processing/reuse path was not redundantly repeated. Exact argv, actual receipts of test execution and TEMP cleanup are saved in canonical-cli-green.log/json and canonical-cli-shape-green.log/json.

## Actual public boundary checks

The test invokes source_catalog.cli official project with explicit projection_version1.0.2 over two genuine imported shared pages. Forward and reverse parent inputs produce identical complete public response bytes, projection ID and digest. The projection is persisted by the production CLI; separate new CLI processes reopen it by ID for replay and export. Both true parents are present, selected record count is two, exported EvidenceSpan producer is cwp_official_json1.0.2, while the sealed JSON structure parser remains1.0.1.

The resulting neutral subject enters the real production batch CLI. One actual loopback model POST consumes the real model-request2; select/summarize/verify all succeed in the same AUTO store and compact to terminal2 pins. Actual synthetic usage is92 tokens/111 micro-USD, no unknown/unsettled reservations. Public metadata reference2 discovery and read2 validate exact subject/generation/artifact SHA and size, both true mother pages and original replay. Read bundle and actual selected spans report producer1.0.2; subject.adapter structure_parser_version remains1.0.1.

A third public reverse-order construction returns identical bytes and identity. Another batch run reuses the exact earlier artifact ref, creates no jobs and makes zero new model calls or newly charged usage. This proves canonical identity survives public CLI, persistence, source adaptation, generation, publication, public read and exact generation reuse.

The legacy test keeps default omission and explicit1.0.1 byte-equivalent for the same input order; reversing pages retains historical distinct IDs and parent enumeration order. The initial fixture's sealed old projection ID remains unchanged.

The parameter negative test refuses unsupported string9.9.9 and non-string list/dict/null with typed exit2, empty stdout and bounded failure JSON, no raw traceback/path leak, no new projection JSON or AUTO DB. This is input shape correctness, not a permission or artificial approval gate.

## TDD evidence

Initial canonical RED:2 FAIL/1 PASS,11.85 seconds. Actual public CLI ignored1.0.2 and returned1.0.1; unsupported9.9.9 was likewise ignored. Root passed only an explicitly present projection_version to the producer, leaving omission/default/old wire unchanged.

New shape RED:2 FAIL/1 PASS,10.48 seconds. List/dict actually returned exit1 and unhashable TypeError traceback; null already produced a typed refusal. Root added a pre-builder string shape guard raising ProjectionError invalid_projection_version, keeping source-owned producer validation for strings. Only these three new negatives reran after that fix. All RED logs remain.

## Restoration and test placement

Every test snapshots original raw/sidecar/config bytes, restores owned fixture state and removes the whole owned project directory. Effective pytest basetemp cleanup reports removed:true. No original migration, provider capture, live LLM, installed skill or shared PWF edits occur. These spawned-worker/public subprocess checks belong to a large integration node, not a repeated commit permission. Ruff on the unique new file passes; root separately owns source static/consolidated verification. This test delivery does not claim full project or every AUTO plan is complete.
