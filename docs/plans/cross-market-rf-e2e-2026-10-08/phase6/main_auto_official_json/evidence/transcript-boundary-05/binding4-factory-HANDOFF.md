# Worker factory source-kind scope repair — complete handoff

Status: implementation complete, source stable, accepted by ROOT. No further source or test writes by this lane.

## Actual RED and cause

Source agent owns `tests/integration/test_narrative_legacy_effort_history.py`. Its actual `[2]` test runs source scan, a request/2 with only a raw item, coordinator binding/4, spawned compute/model workers, and publication. Before this repair, both worker roles raise `NARRATIVE_RUN_EXECUTION_MISMATCH` in `_generation_values`: the factory requires projection prompt/request-schema/adapter versions merely because the request container uses binding/4. A raw-only container legitimately freezes generation/1 and has none of those unused projection fields. The actual RED log is `binding4-raw-red.log`, with command and independent TEMP cleanup in its JSON.

## One-file production repair

Changed only `src/company_wiki/automation/narrative_worker_factory.py`. `_contains_projected_work` reads actual frozen manifest source inputs and the referenced settings schema. An explicit official-json subject or a referenced generation/2 record triggers all three existing exact projection version comparisons. Raw-only binding/4 does not need unused projection versions. Malformed versions containers and invalid generation SHAs remain refused; older binding/no-binding behavior remains. No new database read, parser duplication, manual gate, bypass, or provider call.

## Verification and final owner

15 pure source-scope controls passed: raw-only admission; current projected admission; each of the three projected version fields missing or wrong; mixed raw/projected missing-version refusal and current admission; referenced generation/2 cannot bypass checks even with missing subject fields; malformed versions refusal; invalid generation SHA refusal; and legacy absent binding. Ruff and mypy each report zero for this source. Proof in `binding4-factory-scope-proof.json`. Owned static TEMP removed, zero vendor requests.

The source agent received the stable source SHA and runs the final actual legacy/raw, mixed five, and empty-native one regressions in its single combined package. ROOT owns final prepublication/static/hook checks. Their actual GREEN results belong to their evidence; this lane does not mislabel pure controls as a complete actual CLI regression. No additional test round or filesystem-lock investigation is required here.

## Stable SHA and ownership

- Changed source SHA: `69733204127ac7b1e7d76c2d3c3b206d9f1cf32c4f43a9d4007f4364b022457e`.
- Source-agent-owned actual test SHA at handoff: `57828622b410a6e54020027085e9def2b3d61a98a52eaa74a4599e0978283412`. This lane did not modify that test.
- This lane writes only this agreed supplemental evidence plus the one production source; no shared PWF edits, commits, source originals, runtime configuration, external providers, or external LLMs.
