# FC-902 Independent Review Report

Reviewer: `reviewer-fc902-independent` (independent of `fc902-implementer`)
Clean checkout: `C:/Users/郑曾波/Projects/.fcap-review/fc-902` (detached HEAD)
Reviewed: 2026-08-11 · Verdict: **accepted**

## 1. Checkout + triplet verification

- Worktree HEAD == `364bc5946b1f8eec57d2e195686262e94ebb085e` (result wiki hash) — exact match.
- `git status --porcelain` empty (clean) at start and after all replays.
- Three repos' HEADs (read-only `git rev-parse`):
  - revenue `C:/Users/郑曾波/Projects/revenue-forecast` = `ca213c9c80d1ba7de1aab26fdc777ef30ac21472` ✓
  - filing `C:/Users/郑曾波/Projects/filing-fetch` = `81d9cd98c6c6a680c859b20917fd9d47db707564` ✓
  - wiki `C:/Users/郑曾波/Projects/company-wiki` = `364bc5946b1f8eec57d2e195686262e94ebb085e` ✓
  - Matches result_triplet exactly; revenue/filing unchanged from base_triplet. ✓

## 2. Reference hash recomputation

- Plan `audit_review/2026-08-09_full_completion_assurance_plan/task_plan.md` sha256 =
  `0bc6b9f7d6707e470e55c22759d37c18404172081ecd176d2883e184c61fafaa` ✓ (matches receipt)
- Command registry `compatibility/command_registry.json` sha256 =
  `215b8077169126b2c4a5eca9d8d6237f291757c2559f6ae6e0ae8ff1c806b089` ✓ (matches receipt)

## 3. Dependency receipts

- `company-wiki/assurance/fc/FC-901/12_reviewer_receipt.json` exists, `verdict: accepted`,
  reviewer identity `reviewer-fc901-independent` (distinct). Its commit (16bf9b2) is the FC-902
  base — not invalidated by FC-902. ✓

## 4. Implementer receipt integrity

- sha256(`company-wiki/assurance/fc/FC-902/11_implementer_receipt.json`) =
  `6fdfdb35f4e328a255c2d6840a456bf7493e560bdd494139225f946bd3dc2477`
- Receipt states `status: independent_review`, consistent with awaiting this review.

## 5. Diff scope (base 16bf9b2..HEAD 364bc59)

`git diff --stat`: exactly 7 files, all in the FC-902 allowlist:

| File | Delta |
|---|---|
| assurance/fc/FC-902/03_change_contract.md | +81 (design doc) |
| src/company_wiki/source_catalog/cli.py | +7 |
| src/company_wiki/source_catalog/close_gap.py | +5/-1 |
| src/company_wiki/source_catalog/resolver.py | +36 |
| src/company_wiki/source_catalog/service.py | +59 |
| src/company_wiki/source_catalog/source_bundle.py | +63 |
| tests/contract/test_fc902_bundle_in_resolver.py | +302 (new) |

- `llm_cost_log.csv` NOT in the diff ✓ · no user-dirty paths · no out-of-contract changes.

## 6. Adversarial code review (diff + full file reads)

- **Envelope fail-closed**: `build_resolution_envelope(..., bundle=None)` sets
  `bundle_status="unavailable"` with None; a dict WITH `bundle_hash` → `available` +
  `bundle_hash` + `bundle`; a non-dict or hash-less dict → `ValueError` (fail closed).
  `to_dict()` carries both new fields. FC-704 behavior preserved (`test_env06` green in the 35).
- **Snapshot consistency**: `query_source_bundle(..., expected_content_sha256=...)` returns
  `None` when the catalog `sources.content_sha256` differs from the handle's claim —
  no stale/forged bundle path exists anywhere.
- **Unknown role**: role gate `if role not in KNOWN_ARTIFACT_ROLES` sits BEFORE
  `validate_artifact`; `_unknown_role` builds `ArtifactHandle(reusable=False,
  reason="artifact_role_unknown")`. Verified `validate_artifact` itself has NO role check —
  the gate is load-bearing (mutation M1 killed the test).
- **GENERATOR_REGISTRY**: values are `models.py` constants —
  `NORMALIZER_VERSION=SUMMARIZER_VERSION=SECTION_EXTRACTOR_VERSION="1.0.0"`; keys are the
  three in-house generator names. Single validation registry (no duplicate literals in src;
  producer-side name constants in normalizer/llm_summarizer/section_extractor/store are the
  producers writing the artifacts table, not validation registries).
- **No import cycle**: service.py does NOT import resolver.py — `bundle_for_resolution` checks
  `status.value in ("reused_exact", "reused_equivalent")` strings. resolver→service is
  one-directional; source_bundle imports only artifact_dag/artifact_handle/models. Function-level
  imports in service.py (`build_source_bundle`, `GENERATOR_REGISTRY`) are lazy-safe.
- **SELECT-only**: `query_source_bundle` uses `fetchone`/`fetchall` only; envelope body reads the
  journal via `read_all()` and never appends; no INSERT/UPDATE/DELETE/commit in any changed path.
  The only writes in service.py are unrelated export helpers (`_atomic_write`/`_write_csv`).
- **No dead code**: `_unknown_role` and `GENERATOR_REGISTRY` both referenced; envelope fields
  consumed via `to_dict` on both CLI paths and close-gap. No skip/xfail in the new test module
  (full read of 302 lines). `_utc_now()` format matches the handle `created_at` regex
  (`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z`).
- **RED proof**: `git show 16bf9b2:.../source_bundle.py | grep -c GENERATOR_REGISTRY` = 0
  (absent at base → test module import of GENERATOR_REGISTRY is an ImportError RED);
  present at HEAD (source_bundle.py:1, test:4).

## 7. Replayed commands (all with `python -B`)

| Command | Result |
|---|---|
| `pytest tests/contract/test_fc902_bundle_in_resolver.py -q` | **7 passed** (3.01s) |
| `pytest tests/contract/test_source_catalog_source_bundle.py tests/contract/test_resolution_envelope_fc704.py tests/contract/test_source_catalog_query_bundle.py tests/contract/test_source_catalog_artifact_handle.py -q` | **35 passed** (1.73s) |
| `ruff check` (5 production modules + new test) | clean, exit 0 |
| `py_compile` (5 production modules) | OK |
| `pytest tests/ -q` (full wiki suite, 570s) | **2215 passed / 1 skipped / 3 failed** |

**Full-suite deviation — investigated, not an FC-902 failure:**
Expected baseline was 2216 passed / 2 failed (PORT-01 pair). Observed a third failure:
`test_source_catalog_worker_bootstrap.py::test_terminating_supervisor_does_not_leave_an_orphan_worker`.
Evidence of pre-existence and non-attribution:
- Fails stochastically in ISOLATION at HEAD: 1 of 9 runs, failure duration 10.94s =
  its internal 10s child-start deadline exceeded (real subprocess spawn, Windows-only test).
- Reproduced at the BASE commit in a scratch worktree (`16bf9b2`): 1 of 8 runs failed with the
  identical signature (11.02s). Scratch worktree removed afterwards.
- Its import graph (control.py → code_identity) contains no FC-902-changed module; the changed
  modules (source_bundle/resolver/service/cli/close_gap) are not executed by this test, and
  FC-901's full run (same suite) passed it — stochastic.
- Conclusion: pre-existing load/timing flake, out of FC-902 scope, zero new failures introduced.
  Counts attributable to FC-902: 2215 = 2208 base-passed + 7 new FC-902 tests; the 1 skipped
  test and the 2 PORT-01 GBK failures are unchanged.

## 8. Mutation replays (temp copy → mutate → single test → confirm FAIL → restore)

| Mutation | Edit | Test | Result |
|---|---|---|---|
| FC-902-M1 | `if role not in KNOWN_ARTIFACT_ROLES:` → `if False and ...` (source_bundle.py:117) | test_b04_unknown_role_fail_closed | **FAILED** → killed ✓ |
| FC-902-M2 | `if (expected_content_sha256 is not None` → `if False and (...` (service.py:400) | test_b03_snapshot_consistency_fail_closed | **FAILED** → killed ✓ |
| FC-902-M3 | `if bundle is not None:` → `if False and ...` (resolver.py:428) | test_b01_available_bundle_on_reuse | **FAILED** → killed ✓ |

All three reverted from backups; `git status` clean; focused suite re-run: **7 passed** (1.12s). ✓

## 9. Side-effect reconciliation

- Catalog write budget 0 confirmed by code reading (SELECT-only everywhere in the bundle/envelope
  path) and `test_env08` (envelope build never creates the journal) green in the 35.
- CLI resolve/ensure paths documented and read as SELECT-only; close-gap `_finalize` wiring is the
  only addition and does not write.

## 10. Rollback

- Additive contract (new envelope fields with None-defaults, new helper, wiring, new test file);
  revert = revert commit `364bc59`; no data written. `rollback.required = false`.

## Findings

- `unresolved_findings: []` — no FC-902 defect found.
- Observed-environment note (non-blocking, pre-existing): the worker-bootstrap orphan test is a
  stochastic Windows timing flake (fails ~1/8-1/9 solo runs at both base and result commits);
  candidate for a future FC-1205/portability-style hardening, out of FC-902 scope.
