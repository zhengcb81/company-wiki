# Findings

Author 16-vector E2E claims 11 PASS / 5 REJECT_OK; original 12 unit tests do not prevent false green aggregation. ROOT readonly inspection found:

- _handle_reject accepts any nonempty Exception, including RuntimeError; conversion catches all errors and an empty attempt list passes.
- run_case copies cumulative engine.refs, M08-C bypasses adapter, NativeRef JSON omits actual request/result.
- Unknown assertions skip absent fields; empty assertions pass; bool is accepted as numeric.
- M04 compares helper months only, not forecast annual result; M06 hardcodes deferred amount 20.
- Final command status ignores CLI failure, readonly drift and failed cleanup; empty/incomplete matrices can pass.
- Scratch is removed but newly created owned-root remains; prior report files can be overwritten.
- Card combinations are broader than delivered vectors. Acquisition/control, joint volume/price, gross/net/cannibalization and future actual/WAPE require explicit coverage accounting rather than claiming all eight classes fully covered.

Fix owner is engineering tool; no RF core defect has yet been established. Original assertions must remain, added tests expose these shared failure classes.

## ROOT verification

Behavioral RED: 22 failed / 1 passed (8.23s). Corrected shared mechanisms; original assertions unchanged. Final 36 passed / 4.19s and native E2E 16 vectors 11PASS/5REJECT_OK, 1.394767s; three actual CLI returncodes 0/2/0 with correct contract reason/schema; owned root absent restored, readonly unchanged.

ROOT first E2E deliberately enforced new annual checks and found ROOT's fixture arithmetic constants wrong: actual fixture inputs are (100+50)*1.1^n, not 144/172.8. Corrected expected from fixture input arithmetic, added whole-matrix regression so this cannot hide behind cleanup-only unit tests. Diagnostic retained without duplicate payload.

Author fixed inputs all SHA match; five engineering file handoff hashes stale despite clean Git HEAD (not merely LF/CRLF). Repository path in author handoff incorrect. These are diagnostics; actual author commits/bytes are frozen, no extra approval chain.

Normal ROOT commit 8dc2671040f4330d3b54d1bea1d17246130f9c2a. First normal pre-push: static/type checks green; 387PASS+36 subtests, 3 failures because isolated worktree lacks default sibling FF/CWP directories. Existing explicit FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT selects actual readonly repositories; retry uses this supported configuration, no hook/test bypass.

Tool execution accepted; full card combination coverage PARTIAL. Detailed closure plan: mother W07 ROOT-rf-remaining-coverage.md. No core support claims inferred from missing tests. Single compressed native report plus small receipt; ROOT record footprint approximately330KB, not repeated multi-MB raw payloads.

Normal push and local main fast-forward completed:8dc2671040f4330d3b54d1bea1d17246130f9c2a; author commits included.390PASS+36subtests/32.07s, exact quality CI38168556914 SUCCESS.150 WIP file SHAs unchanged; engineering-only no skill sync. Full card coverage remains PARTIAL.
