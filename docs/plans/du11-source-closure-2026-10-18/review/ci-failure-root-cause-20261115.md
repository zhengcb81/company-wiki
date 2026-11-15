# CWP CI failure root cause and repair — 2026-11-15

## Scope

- Failed source run: GitHub Actions `43749426185`, job `132919838860` (“Run focused regression suite once”).
- The anonymous GitHub Actions log endpoint returned HTTP 403. No credentials were extracted or reused. Diagnosis used the named regressions, focused local reproduction, runtime inspection, and the review of the exact diff.
- This review covers the CWP fixes in the current worktree. It does not claim the whole CI run passed; the exact pushed SHA's GitHub CI is still required.

## Root causes and changes

| Area | Root cause | Change and regression |
|---|---|---|
| Joined narrative reference | A default reference for a joined group used the later member's predecessor scope, which included an earlier member of the same group. The owner rejected that internal member as an invalid external antecedent, losing a valid joined reference. | Default to the first source-ordered member's predecessor window. Added `test_joined_reference_uses_the_scope_before_the_whole_group`. Production package construction is source ordered; the internal constructor contract is now documented. |
| Large operating table | 79 eligible rows were sent together through a prose semantic-group path whose bound is for joined prose. `ValueError` became unresolved candidate relevance even though the table was already structurally qualified and budget remained. | Keep table-purpose's exact qualification and eligible-row/context selection, then return its structural qualification instead of constructing a prose group. Downstream facts and semantic admission remain. The 80-row regression asserts complete source assessment. |
| Planned PDF observation | Production planned scanning calls `pdf_text_blocks`, while the test patched only `_pdf_text_blocks`; the test therefore observed zero calls on a valid route. | Patch both names in the test. No production PDF behavior changed. |
| Work-budget fixture | The old 85×text fixture predated a real bounded negative-route resource scan, which legitimately costs an additional pass. The expected budget was stale. | Calibrate the fixture to 90×text. It still asserts unchanged classification and positive work below the bound. Runtime budgets were not relaxed. |
| Paid-response replay assertion | The decoder now reports condition-scope loss on c6 and c10 as well as the existing c15/c18/c19 diagnostics. The test expected only the older set. | Update expected IDs to c6/c10/c15/c18/c19. The archived public projection remains frozen and unchanged. Offline replay confirmed c6/c10 use `possible_condition_scope_loss`. |

## Why hooks missed it

`.pre-commit-config.yaml` intentionally runs static checks and does not run pytest. The previous fixed daily push smoke also did not include these regression cases. This explains the gap; it is not evidence that static pre-commit can prove runtime correctness. The daily push list now includes five exact cases (14 total including the prior nine), one representing the shared planned-PDF alias path. The list is fixed, remains under the existing 180-second cap, and does not expand with changed-file count. The other planned-PDF parameter variants remain in GitHub's full suite.

## Validation

- Affected ten test files: **236 passed**, 19.96 seconds, Python 3.13.9.
- Daily push fast smoke: **23 passed**, 12.11 seconds; cleanup receipt `removed=true`.
- `mypy`: 490 source files passed.
- Ruff and `git diff --check`: passed.
- Independent read-only review: no blocking issue found. It confirmed table qualification/filtering and downstream admission, the bounded fixed push list, both PDF reader names, the budget rationale, and the joined-group source-order construction. The reviewer did not run tests.
- Python 3.14.2 produced one grammar-scanner mismatch that passed under Python 3.13.9. Python 3.12, used by CI, is not installed locally; the remote exact-head run remains authoritative.
- No full unit suite was run locally. No source originals, provider settings, APIs, or external repositories were touched.

## State

Local fixes and focused checks are green. The fix is not complete for publication purposes until committed, pushed, and checked against the exact GitHub Actions SHA. Do not describe local push smoke or local targeted tests as full remote CI success.
