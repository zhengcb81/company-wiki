# FC-901 Independent Review Report — legacy artifact binding migration (dry-run bucketing)

- Reviewer: `reviewer-fc901-independent` (distinct agent from `fc901-implementer`)
- Review checkout: `C:/Users/郑曾波/Projects/.fcap-review/fc-901` (detached-HEAD worktree, never touched the implementer's tree)
- Reviewed at: 2026-08-11T07:34:38Z
- Verdict: **accepted**

## 1. Clean checkout + triplet verification

```
$ git -C worktree rev-parse HEAD
07422f98d9946ef8a54e77a85661c3c6cb46bdf7          # == result triplet wiki hash
$ git status --short                               # empty -> clean
```

| Repo | HEAD | Expected (result triplet) | Match |
|---|---|---|---|
| wiki (worktree + main `C:/Users/郑曾波/Projects/company-wiki`) | `07422f98d9946ef8a54e77a85661c3c6cb46bdf7` | `07422f9...` | yes |
| revenue (`C:/Users/郑曾波/Projects/revenue-forecast`) | `3617335bb63c8c5c2483edf71a56c06e035cb95c` | `3617335...` | yes |
| filing (`C:/Users/郑曾波/Projects/filing-fetch`) | `81d9cd98c6c6a680c859b20917fd9d47db707564` | `81d9cd9...` | yes |

Result triplet matches; base triplet verified identical to the plan's declared base.

## 2. Plan + command-registry hashes

```
$ sha256sum revenue-forecast/audit_review/2026-08-09_full_completion_assurance_plan/task_plan.md
0bc6b9f7d6707e470e55c22759d37c18404172081ecd176d2883e184c61fafaa   # == expected 0bc6b9f7...
$ sha256sum revenue-forecast/compatibility/command_registry.json
215b8077169126b2c4a5eca9d8d6237f291757c2559f6ae6e0ae8ff1c806b089   # == expected 215b8077...
```

Both match the reference hashes.

## 3. Dependency receipts

```
FC-405 -> accepted | reviewed_at: 2026-08-10
FC-704 -> accepted | reviewed_at: 2026-08-11
```

Both required dependency reviewer receipts exist and carry `verdict: accepted` with dates matching the plan.

## 4. Implementer receipt sha256

```
$ sha256sum company-wiki/assurance/fc/FC-901/11_implementer_receipt.json
eee459844a0cdc654968468a4b2c4cd8504f7a8ef865e83c831c8791a8610111
```

Cross-checked its declared base/result triplet, allowed/changed files, scenario notes, and command results against my own measurements — all consistent. (Trusted only as cross-reference; acceptance is re-proven below.)

## 5. Diff base..result

```
$ git diff 9907a3b8869b8c33c520ddb25195bbc57034c8d8..HEAD --stat
 assurance/fc/FC-901/03_change_contract.md          |  91 +++++
 .../source_catalog/artifact_backfill.py            | 345 +++++++++++++++++++
 .../test_source_catalog_artifact_backfill.py       | 375 +++++++++++++++++++++
 3 files changed, 811 insertions(+)

$ git diff ... --name-only | grep -c llm_cost_log   # 0 -> llm_cost_log.csv NOT in diff
```

Changed files = exactly the FC-901 allowlist (3 new files). `llm_cost_log.csv` absent. No existing production/test file modified.

## 6. Adversarial code review

### Bucket mapping matches contract exactly
`_REASON_TO_BUCKET` maps `artifact_hash_mismatch` + `artifact_hash_malformed` -> `hash_mismatch`, `artifact_file_missing` -> `missing_bytes`, `artifact_generator_unregistered` -> `unknown_generator`; every other reason falls to `legacy_unbound` via the default. Verified against `artifact_handle.py` (grep of all `_reject` reasons, lines 62-128): all 12 reject codes present in the gate, and the mapping table covers the contract's required set. `artifact_source_sha_mismatch` / `artifact_source_binding_mismatch` / status / schema / created_at / path_outside_root are NOT in the table -> legacy_unbound, per contract. Null `primary_source_id` or missing source row -> `legacy_unbound, "no_provable_source_lineage"` before the gate runs (contract: "no matching sources row ... goes to legacy_unbound").

### Dry-run = zero writes
All writes (`executescript(_BINDINGS_DDL)`, `INSERT OR IGNORE`, `con.commit()`) are inside `if mode == "apply" and result.proposals:` (line 273). The dry-run path executes only the single SELECT (line 226) with `ORDER BY a.artifact_id`. No INSERT/UPDATE/DDL reachable in dry-run mode. Verified at byte level (see step 9).

### Apply writes only artifact_bindings
The only INSERT targets `artifact_bindings` (shadow rows with `visibility_state='shadow'`, `created_by='fc-901'`). `artifacts`/`documents`/`sources` are never written or deleted (grep for DELETE/UPDATE found only the docstring mention). Idempotency: `UNIQUE(artifact_id)` in DDL + `INSERT OR IGNORE` + pre-check `SELECT 1 FROM artifact_bindings WHERE artifact_id=?` that records `skipped_already_bound` instead of inserting.

### MIG-05: no guessing
Proposals copy real column values (`source_id`, `content_sha256`, `generator_name/version` from the artifacts row) — nothing is derived from file names or paths. When provenance cannot be assembled the artifact goes to legacy_unbound before any proposal is built. No `period`/`fiscal_year` anywhere in the module (grep).

### No root special-casing / hardcoded paths / dead code
No absolute paths in the module (grep). `allowed_roots` is a caller-provided tuple passed through to `validate_artifact`. All 9 imports (hashlib, json, sqlite3, dataclass, field, Path, Any, ArtifactHandle, validate_artifact) are used. No `@pytest.mark.skip`/`xfail`/TODO/FIXME in module or tests (grep).

### Deterministic ordering / reconciliation cannot double-count
SQL orders by `artifact_id`; `as_dict()` re-sorts rows by artifact_id, proposals by key, capacity by key; `result_hash` = sha256 of `sort_keys=True` canonical JSON. Bucket counters (`bindable` etc.) and the `as_dict()["buckets"]` dict both derive from the same single source — `rows` via `_bucket_total` — so a divergence between counters, buckets dict, and rows is structurally impossible. `_classify` returns exactly one of the five bucket strings, and each loop iteration appends exactly one row per artifact row (`input += 1` at the same iteration), so `closed` (`input == sum`) is a genuine conservation check: an unknown bucket, a dropped row, or a duplicated row would make `closed` False. No path exists for double-counting to satisfy the invariant.

## 7. Command replay (from the worktree, `python -B`)

| Command | Result |
|---|---|
| `python -B -m pytest tests/contract/test_source_catalog_artifact_backfill.py -q` | **11 passed** in 2.44s |
| `python -B -m ruff check src/company_wiki/source_catalog/artifact_backfill.py tests/contract/test_source_catalog_artifact_backfill.py` | **All checks passed**, exit 0 |
| `python -B -m pytest tests/ -q` | **2209 passed, 1 skipped, 2 failed in 579.20s** |
| `python -B -m company_wiki.source_catalog.artifact_backfill --help` | CLI usage printed (caller>=1 edge live) |

Full-suite failures, both exactly the pre-existing PORT-01 pair in `tests/contract/test_check_unique_test_symbols.py`:

```
FAILED tests/contract/test_check_unique_test_symbols.py::test_duplicate_test_definition_fails
FAILED tests/contract/test_check_unique_test_symbols.py::test_syntax_error_is_reported_as_failure
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd4 in position 21: invalid continuation byte
```

This is the documented Windows GBK-locale failure (the test file's own comment at line 25: "child prints UTF-8; Windows GBK locale would break text=True"). The FC-901 diff touches neither that file nor `tools/` nor any subprocess code — these failures are environment-caused and pre-existing. No other failure = no new regressions.

### RED replay (module absent)
Materialized base `9907a3b` src+tests into a scratch dir via `git archive`, copied the FC-901 test file in, ran it:

```
E   ModuleNotFoundError: No module named 'company_wiki.source_catalog.artifact_backfill'
ERROR tests/contract/test_source_catalog_artifact_backfill.py (1 error during collection)
```

The RED was a genuine module-absence ImportError — not a syntax/fixture/environment artifact. (Also confirmed the file does not exist at base: `git diff` shows it as a new file.)

## 8. Mutation replay (scratch backup, restore, verify)

Both mutations applied to a backup copy of the module, single test re-run, module restored, focused suite re-run green.

### FC-901-M1 — delete `"artifact_hash_mismatch": "hash_mismatch",` from `_REASON_TO_BUCKET`
```
FAILED tests/contract/test_source_catalog_artifact_backfill.py::test_ab07_bucket_conservation
E   AssertionError: assert 0 == 1        # hash_mismatch=0, legacy_unbound=2
1 failed, 10 deselected in 0.74s
```
**Killed.**

### FC-901-M2 — `if mode == "apply" and result.proposals:` -> `if result.proposals:`
```
FAILED tests/contract/test_source_catalog_artifact_backfill.py::test_ab01_dry_run_writes_nothing
E   Differing items: {'bindings': 1} != {'bindings': 0}
1 failed, 10 deselected in 0.75s
```
**Killed.**

Restoration proof: after both restores, `git diff --stat` empty and re-run of the focused suite:
```
tests\contract\test_source_catalog_artifact_backfill.py ........... [100%]
============================= 11 passed in 1.39s ==============================
```
plus `git status --short` empty (worktree pristine).

## 9. Side-effect reconciliation (independent, file-level)

Independent script (fixture replicated outside the test suite): one bindable artifact; dry-run over the catalog.

```
dry-run catalog bytes unchanged: True        # sha256 before == after
dry-run result: input=1 bindable=1 closed=True
only catalog+artifact files exist: True      # no stray files
```

Stronger than row counts: the catalog DB file bytes are bit-identical after dry-run. The in-suite assertions (test_ab01: artifacts + artifact_bindings counts unchanged, bindings == 0) also passed.

## 10. Rollback

`test_ab10_apply_is_reversible_by_shadow_delete` passed within the 11: `DELETE FROM artifact_bindings WHERE created_by='fc-901'` leaves 0 bindings and the artifacts table row count unchanged. Independent spot check:

```
apply created bindings: 1 | after rollback: 0 | artifacts rows: 1
```

Rollback contract (`DELETE ... WHERE created_by='fc-901'`) matches the change contract exactly.

## 11. CodeGraph reachability

- `run_artifact_backfill` — new production symbol; caller >= 1 satisfied by in-module CLI `main()` (verified by reading source at line 327 and the `--help` smoke test).
- Reuse edge: `_classify` -> `validate_artifact` (from `artifact_handle.py`). CodeGraph search confirms `validate_artifact` at `src/company_wiki/source_catalog/artifact_handle.py:78` with the exact signature used `(artifact, *, source, registry, allowed_roots, now) -> ArtifactHandle`.
- Note: the company-wiki CodeGraph index predates this commit (does not yet list `artifact_backfill.py`); the file is confirmed present on disk in both the main tree and the review worktree, so this is index lag, not missing code. Static reachability evidence is complete.
- No legacy call edge removed in this FC (diff adds 3 files, modifies nothing).

## 12. Conclusions

- No unresolved findings.
- All mandatory replay commands executed; focused 11/11, ruff clean, full suite 2209/1/2 with only the pre-authorized PORT-01 GBK pair failing; both mutations killed; RED proven genuine; side-effect reconciliation and rollback verified independently.
- Verdict: **accepted**.
