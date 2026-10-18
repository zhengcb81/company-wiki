# F4 source-card allocation handoff

Implementation frozen for ROOT independent review; not independently accepted yet.

## Files

- `src/company_wiki/automation/narrative_model_extractive.py`: sole production change. Existing `source_cards.py`, summary task membership, public summary and original source stores untouched.
- `tests/unit/du11_source_priority/test_source_priority.py`:22 portable tests.
- This separate plan directory and bounded test logs/receipt only. Other worktree modifications belong to ROOT/other lanes.

## Interface

Before pre-POST allocation, `_source_allocation_order` reads only each task's actual support spans: `reading_priority` strictint (lower), `reading_value_band` meaningful_fact then description, `reading_score` strict nonnegativeint (higher). Best complete support tuple represents an indivisible card; context does not lend priority. Cards without a valid complete tuple retain their native slot. Remaining metadata slots stably sort by tuple and original ordinal. No text recognition, company/gold/task-ID heuristic, model or I/O.

Existing exact escaped UTF8 whole-card fitting and parent/support/context dedup remain. Only admitted cards materialize original quote text. All execution rows and claims return to native task order; all original keys, evidence/context IDs, bindings and public fields remain. Source priority does not turn a source into a fact or publication permission. Current64KiB final/56KiB draft/32KiB report bounds are unchanged. No second POST or budget reset.

`SOURCE_CARD_ALLOCATION_VERSION` explicitly enters existing model boundary identity; current protocol dependency hashing binds actual owner bytes. Explicitv4 behavior remains unchanged. ROOT owns projecting three fields for0.9 sources; this lane does not claim that production source metadata is wired/tested yet.

## Test evidence and limits

- RED before implementation:17FAIL/3PASS/5.06s, actual late-card first-fit defect and missing allocator version. Separate true default56KiB capacity RED preserved.
- Concentrated GREEN:22new +18existing extractive +16existing summary-task tests =56PASS/5.84s. Actual isolated module path validated; hermetic no network/models/PDF/config/original IO. Includes strict bool/invalid fields, context non-borrowing, multispan support, known-slot fallback, deterministic tie/order, complete group quotation, actual default cap and lazy oversized rejection; old dedup/whole quote/v4 tests reused.
- No source semantic business admission is implemented here; no claim to fix CN/HK actors/context/table quality or complete real C.
- Independent review must verify source/test SHAs in JSON and all confirmed findings before ROOT accepts. This author did not self-sign an independent review.
