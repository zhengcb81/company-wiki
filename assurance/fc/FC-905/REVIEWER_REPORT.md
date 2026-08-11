# FC-905-a Independent Review Report

- Reviewer: `reviewer-fc905a-independent` (distinct session from implementer `fc905a-implementer`)
- Review checkout: `C:/Users/郑曾波/Projects/.fcap-review/fc-905` (detached-HEAD worktree, never touched implementer's tree)
- Reviewed at: 2026-08-11T19:15:24Z
- Verdict: **accepted**

## 1. Triplet verification

| Repo | Expected (result triplet) | Observed HEAD | Match |
|---|---|---|---|
| revenue | `b9994dc4f67f1943379a1c830b34e0dfe307e117` | `b9994dc4f67f1943379a1c830b34e0dfe307e117` | yes |
| filing | `959d04cdbe2115c8e01fa39a2d5dfe748cc4fedd` | `959d04cdbe2115c8e01fa39a2d5dfe748cc4fedd` | yes |
| wiki | `d76e461496e43e7696dc2dc763ec1d443f4a484e` | `d76e461496e43e7696dc2dc763ec1d443f4a484e` | yes |

Worktree `git status --porcelain` empty at start and end; HEAD commit `d76e461 feat(fc-905a): trusted capture evidence on the resolution envelope`.

## 2. Hash recomputation

| Artifact | Expected sha256 | Recomputed | Match |
|---|---|---|---|
| task_plan.md | `0bc6b9f7d6707e470e55c22759d37c18404172081ecd176d2883e184c61fafaa` | same | yes |
| command_registry.json | `215b8077169126b2c4a5eca9d8d6237f291757c2559f6ae6e0ae8ff1c806b089` | same | yes |
| implementer receipt (11_implementer_receipt.json) | — | `ba4c98c68de16f45e2b81e9a12d83b38bbbbe405f84de3150a686279df3376ca` | recorded |

## 3. Dependency receipt

`revenue-forecast/assurance/fc/FC-904/12_reviewer_receipt.json` exists, schema 2.0, fc_id FC-904, reviewer `reviewer-fc904-independent`, verdict **accepted**. Not invalidated by any later commit (filing/revenue HEADs unchanged in the triplet).

## 4. Diff stat vs base wiki fd4f50b

```
 assurance/fc/FC-905/03_change_contract_fc905a.md   |  75 ++++++
 src/company_wiki/source_catalog/cli.py             |   2 +
 src/company_wiki/source_catalog/close_gap.py       |   3 +-
 src/company_wiki/source_catalog/producer_events.py |  36 +++
 .../source_catalog/prompt_injection.py             | 118 +++++++++
 src/company_wiki/source_catalog/resolver.py        |  37 ++-
 src/company_wiki/source_catalog/store.py           |  35 +++
 tests/contract/test_fc905_receipt_envelope.py      | 295 +++++++++++++++++
```

8 files — exactly the FC-905-a allowlist. Producer code (normalizer/llm_summarizer/section_extractor) untouched.

## 5. Adversarial code checks (all pass)

1. **Trigger**: `trg_artifact_producer_event AFTER INSERT ON artifacts` journals every INSERT with role->type CASE (normalized/sections→parser, summary/consumer_analysis→llm, else→other) — matches contract verbatim. All `NEW.*` columns (`artifact_id`, `document_id`, `artifact_role`, `generator_name`, `generator_version`) exist in the artifacts DDL. DDL idempotent (`IF NOT EXISTS` everywhere).
2. **No FK on producer_events.document_id** — confirmed in DDL (comment documents intent); the journal is append-only history and must never block artifact writes or focus_cleanup document deletion. **focus_cleanup suite replayed: 7 passed** (the FK was the discovered breakage).
3. **Absent review receipt → explicit `not_reviewed`** — resolver defaults `prompt_injection_status = "not_reviewed"`, only replaced when `review is not None`; never faked.
4. **Malformed receipt → not_reviewed** — `read_prompt_injection_review` returns None on: missing row, JSON decode error, non-dict metadata, non-dict receipt, wrong schema_version, unknown status. Malformed is never trusted.
5. **parser_calls/llm_calls only from journal; no store → None** — defaults None; populated exclusively inside `if store is not None and resolution.matches:` from `count_producer_events` (SELECT COUNT over producer_events by event_type). Without a store absent evidence is None, never 0.
6. **Envelope path SELECT-only** — reads use `store.fetchone` (SELECT / SELECT COUNT); no execute/UPDATE in resolve/ensure/close-gap envelope path. `record_prompt_injection_review` (the only writer) has **zero production callers** (grep across src: only defined in prompt_injection.py, called from tests).
7. **record_prompt_injection_review fail-closed** — rejects: empty document_id, status outside enum {not_detected, detected_and_ignored}, empty reviewer, non-`^[0-9a-f]{64}$` evidence, wrong schema_version, unknown document (raises).
8. **Producer code untouched** — diff stat proof (above).
9. **Ruff clean** — `python -B -m ruff check` on the 6 production modules + new test: "All checks passed!".

Call-edge check: `read_prompt_injection_review` + `count_producer_events` each have exactly one production caller — `build_resolution_envelope` (resolver.py:455-462), called from cli resolve/ensure and close_gap._finalize. `SourceCatalog.store` is a lazy `CatalogStore` property (service.py:46-49) with `fetchone` (store.py:1156); same store object already used by focus_cleanup.

## 6. Replayed commands (all in the clean worktree, `python -B`)

| Command | Result |
|---|---|
| `python -B -m pytest tests/contract/test_fc905_receipt_envelope.py -q` | **9 passed** (2.38s) |
| `python -B -m pytest tests/contract/test_resolution_envelope_fc704.py tests/contract/test_fc902_bundle_in_resolver.py tests/contract/test_source_catalog_query_bundle.py tests/contract/test_source_catalog_source_bundle.py -q` | **30 passed** (2.30s) |
| `python -B -m pytest tests/contract/test_source_catalog_focus_cleanup.py -q` | **7 passed** (29.62s) — FK-fix proof |
| `python -B -m ruff check` (6 prod modules + new test) | **All checks passed** |
| `python -B -m pytest tests/ -q` (full suite, registry id wiki.unit.full) — run **twice** | Run 1: **2225 passed, 2 failed, 1 skipped** (436.56s); Run 2: **2225 passed, 2 failed, 1 skipped** (411.95s). Collected 2228 both runs. |

Full-suite failures (identical in both runs, re-verified individually):
- `tests/contract/test_check_unique_test_symbols.py::test_duplicate_test_definition_fails` — `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd4 ...` (subprocess GBK output on Windows) — pre-existing PORT-01 family, FC-1205 finding #31.
- `tests/contract/test_check_unique_test_symbols.py::test_syntax_error_is_reported_as_failure` — same UnicodeDecodeError — pre-existing PORT-01 family.

The third expected failure (`test_terminating_supervisor_does_not_leave_an_orphan_worker`, known timing flake proven at base in FC-902 review) **passed in both runs** — a flake passing is not a NEW failure; the observed failure set is a strict subset of the expected set. **Zero new failures.**

Skip (both runs): `tests/contract/test_dropbox_root_policy_fc501.py:135` — `pytest.skip("symlinks not supported on this host")`, environment skip, pre-existing.

## 7. RED replay (symbols absent at base)

```
git show fd4f50b:src/company_wiki/source_catalog/prompt_injection.py  -> fatal: path exists on disk, but not in 'fd4f50b...' (exit 128)
git show fd4f50b:src/company_wiki/source_catalog/producer_events.py  -> fatal: path exists on disk, but not in 'fd4f50b...' (exit 128)
```

Both new modules absent at base — RED phase genuine.

## 8. Mutations (all replayed, temp copy → mutate → single test → FAIL → restore)

| ID | Mutation | Test | Result |
|---|---|---|---|
| FC-905a-M1 | resolver: `review = read_prompt_injection_review(...)` → `review = None` | test_pi01_reviewed_not_detected_forwarded | **FAILED** — killed |
| FC-905a-M2 | resolver: counts → `{"parser_calls": None, "llm_calls": None}` | test_pi05_counts_from_journal_not_output | **FAILED** — killed |
| FC-905a-M3 | store.py: trigger DDL block removed entirely (comment through `END;`, 875 chars; pyc cleared) | test_pi07_trigger_journals_artifact_insert | **FAILED** — killed |
| FC-905a-M4 | resolver: `else: prompt_injection_status = "not_detected"` after review read | test_pi03_no_review_is_explicit_not_reviewed | **FAILED** — killed |

Each restore verified via `git diff --stat` (clean); final `git status --porcelain` empty, HEAD still `d76e461`; focused suite re-passed **9/9**.

## 9. Side-effect reconciliation

- Envelope path writes: 0 (SELECT-only, verified in diff + grep).
- Journal rows: 1 per artifact INSERT, exclusively from the trigger; no other `INSERT INTO producer_events` anywhere.
- External root writes / deletions / LLM / parser calls in the change: 0.
- Test DDL re-creation per tmp_path; no production database touched.

## 10. Rollback

Required (DDL + schema changes). Proven by construction: `DROP TRIGGER trg_artifact_producer_event; DROP TABLE producer_events;` is the exact inverse of the self-contained `CREATE ... IF NOT EXISTS` statements (M3 demonstrated removing the trigger block leaves the suite healthy); review receipts live in `documents.metadata_json` and are reversible by rewrite; envelope field additions revert by commit.

## 11. Observations (non-blocking, no findings recorded)

1. Role→type mapping tests exercise only `normalized→parser` and `summary→llm`; `sections`, `consumer_analysis`, and the `else→other` branches are covered by code reading only (CASE matches contract exactly).
2. The malformed-receipt→not_reviewed reader path (bad JSON / bad schema / bad status) is guarded in code but not directly test-covered; the never-fake invariant itself is enforced by M1/M4-killed tests.

## 12. Conclusion

All mandatory commands replayed, all 5 scenarios passed, all 4 mutations killed, side effects reconciled, rollback proven, zero unresolved findings. **Verdict: accepted** (producer-side half of FC-905; FC-905-b consumer side remains pending).
