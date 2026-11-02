# CWP final CI test migrations — independent review

PASS_ENGINEERING_TEST_MIGRATION_SCOPE. No actionable P1/P2 finding. The three frozen tests and four adjacent product dependencies matched the author manifest before and after review. The reviewer changed no product source, canonical tests, Git state or main PWF.

The migration follows the authorized contract: source-body path strings remain data, while path-bearing source_path/claim_id metadata remains forbidden; canonical selected evidence still has to match the parsed original. The new positive select fixture uses the real parsed unit's parser/version/coordinates rather than a synthetic parser identity. The intermediate two fixture failures therefore exposed a meaningful replay check and were corrected without weakening it. Fabricated content and metadata-path negative cases remain.

Cumulative source provenance is validated JSON, not a fixed-size permission token. The new test compares the complete merged evidence and patch, verifies query projections and exact original bytes, checks idempotence, and retains genuine invalid-JSON and binding/value/locator negatives. Product validation still occurs before the single atomic write boundary.

Independent execution: four unseen controls passed in 2.13 seconds: a real source-path PDF → exact parsed span → summary preserving the same text; forged body under the same genuine parser/coordinates refused as PARSER_INCOMPLETE; genuine span with physical source_path metadata refused as INPUT_SCHEMA_INVALID; and a different large Unicode/English provenance payload preserved completely with repeat/no-growth and malformed/bad-binding controls. An existing claim_id-path negative also passed in 1.77 seconds. Both handler failure controls had zero effects; summary used only ReplayModel.

Five selected cases passed in total. Full 24-case/Unit suites were not repeated. The existing asyncio_mode pytest warning under disabled plugin autoload was nonblocking. No real model, download, original-document access, global installation or credentials were used. Raw logs, JUnit, exact independent probe and source seals are archived beside the JSON evidence pointers.

The companion JSON records native cleanup of the owned temporary test tree. Accept this engineering test-only scope, then observe the exact normal CI after ROOT publication. This report does not sign off H1 contexts, real summary/cache/RF adoption or the entire PWF goal.
