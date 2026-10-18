# DU11 source-priority allocation

Owner: internal GOLD lane. Selected plan `PLAN_ID=du11-source-priority-2026-10-18`, `PWF_PLAN_ROOT=docs/plans`. Parent owns all other production files and mother PWF.

## Scope and frozen interface

- Only `automation/narrative_model_extractive.py`, if necessary `document_understanding/source_cards.py`, own `tests/unit/du11_source_priority/` and this plan directory.
- Consume actual support span `structured_value`: complete tuple `reading_priority` (int, lower first), `reading_value_band` (`meaningful_fact` before `description`), `reading_score` (nonnegative int, higher first). Reject bool-as-int and incomplete/invalid tuples.
- Per task use best complete actual support tuple. Context cannot lend priority. Missing/invalid metadata keeps its native slot; only known-metadata slots are stably reordered. Stable native tie breaker. Restore final claims/audit native order.
- Whole original cards only; same UTF8 draft/final/report caps, same references/IDs/membership/dedup/lazy text, no model/IO/second store. Bind actual allocator semantic identity through constant and existing boundary hash. Legacy v4 unchanged.

## Phases

1. A portable behavior RED: complete (17FAIL/3PASS; additional actual-cap RED retained).
2. B bounded allocator implementation and concentrated relevant tests: complete (56PASS/5.84s).
3. C final SHA freeze and parent-arranged independent review: complete (ET22PASS; precise SHA review).
4. Offline actual source engineering probe: complete; source quality remains OPEN / HK regression needs ROOT repair.

## Next Step

ROOT repairs the new continuity.finish regression using the controlled HK ablation, then performs final integrated source/content acceptance. Do not merge source-quality changes on the strength of allocator tests alone.

## Errors

Expected REDs preserved: native-first-fit selected wrong card (17FAIL/3PASS); boundary constant missing; default-cap sample initially fit the short tail and was strengthened to an actually capacity-constrained whole card before production implementation. Strengthened default-cap RED failed exactly because its important tail was deferred. No runtime failure observed in the final56PASS.
