# WP01 source transport implementation

## Goal
Keep raw /1 and projected /2 behavior; add bounded compact /3 with full bundle lineage, one exact-parent verification per read, and correct nonperiod capture capability.

## Phases
1. Interface/fixture inspection: complete
2. Meaningful capability and compact-wire RED: complete
3. Owner-only implementation: complete
4. Focused GREEN and public producer fixtures: complete
5. Handoff and STOP: complete

## Next Step
STOP. ROOT/WP03 own the remaining cross-repository G1 and fixture consumption/cleanup.

## Limits
0 provider/HTTP/model calls; no production raw/config writes, no commit/push/install. ROOT owns final cross-repo G1.

## Errors encountered
- Initial sidecar_filing_v1 fixture lacked required registration facts: corrected fixture to existing company_raw source path before preserving meaningful RED.
- Replay harness initially selected canonical repo by wrong parent ordinal: corrected to explicit ancestor containing src/company_wiki before any input open.
- Windows default GBK read failed on UTF8 replay script: explicit UTF8 used.
- Replay DB table guessed source_locations: corrected to actual reader locations table; prior owned scratch DB contains no raw files and will be removed after inspection.
- Resigned pointer RED initially changed span ID without updating summary citation: corrected fixture to maintain valid citation so native locator replay rejects the forged pointer.
- Final Ruff caught three test one-line branches: expanded only these branches.
