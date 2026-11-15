# Pre-push documentation classification and pytest cleanup review

## Result

Independent review: **PASS** on working tree based on `HEAD=e592b3b53ddc15f3148f2270efe69d132b993baf`. The reviewed implementation and tests are bound to the SHA-256 values below. The fix changes CWP test/developer tooling only; it does not change product source, acquisition, or M3 owner exit conditions.

## Changes and root causes

1. Root-level `PLANNING_STATUS.md`, `progress.md`, `findings.md`, and `task_plan.md` were missing from the explicit documentation-only range classifier. A PWF-only push therefore ran the fixed smoke and was mislabeled as runtime/configuration. The allowlist now names those four Markdown files. Unknown, mixed, runtime, and configuration ranges still run the existing fixed smoke. The generic reason now says only that the range is not positively classified as documentation.
2. Local bare Git pushes create Windows loose objects with the ReadOnly attribute. Pytest's owned short-path fallback used `shutil.rmtree(..., ignore_errors=True)`, swallowed 441 PermissionErrors, and left its `.cwpt-*` scratch tree behind. Cleanup now retries permission failures after clearing ReadOnly, but first uses `os.lstat` to refuse symlinks and Windows reparse points. The always-running reparse regression verifies no chmod call and an unchanged read-only sentinel.

## TDD and validation

- Pre-push RED: `python -m pytest tests/unit/test_pre_push_gate.py -k 'proven_documentation_range or daily_runtime_config' -q` produced 12 failures / 4 passes before the range fix. After the fix, the same selection passed 16 / 16.
- Read-only Git object cleanup was reproduced with a synthetic readonly object: before the cleanup fix, `pytest_unconfigure` left the fallback directory and reported `removed=false`; after the fix, the owned fallback directory is removed and reports `removed=true`.
- Final bounded validation, run in the normal host context because sandbox policy blocks local subprocess access to temporary bare Git remotes: `python -m pytest tests/contract/test_short_basetemp_convention.py tests/unit/test_pre_push_gate.py tests/unit/test_daily_push_policy.py -q` → **57 passed, 1 skipped in 13.04s**. The skipped case creates a real symlink; this account cannot create one. Its synthetic Windows reparse-point control ran and passed.
- `ruff check conftest.py tests/contract/test_short_basetemp_convention.py tools/pre_push_gate.py tests/unit/test_pre_push_gate.py` passed; `git diff --check` passed. Pytest cleanup receipt: `removed=true`.
- The exact prior external test scratch root `.cwpt-033fe3e9d352` was verified to contain only the four fixtures from this run, checked for active processes and reparse points, had readonly bits cleared within that exact root, and was removed. The latest pytest-created external fallback was absent after its `removed=true` receipt. No production data was touched.

## Independent source/test review

The reviewer checked classification scope, preservation of the runtime/mixed/unknown smoke, cleanup retry behavior, and the symlink/reparse protection. It returned **PASS**. It noted the theoretical `lstat`-to-`chmod` race if an owned temporary tree were concurrently replaced by an adversary; this helper is limited to a freshly-created unique pytest-owned scratch directory and is not a general-purpose hostile-tree deletion API.

| File | SHA-256 |
|---|---|
| `conftest.py` | `027360128a6cf50d6d72f0467a5443f1adcd5132276f39d0bedb89ef0163aaa4` |
| `tests/contract/test_short_basetemp_convention.py` | `a82cfa2b823769eae529d7711e9f17220df411f93dd5631c87d426424bb041dc` |
| `tools/pre_push_gate.py` | `962a42d32d70f1b1d5a867c5687b18c26c5b40b1b1c1c2a5f0b38cde536bd0d4` |
| `tests/unit/test_pre_push_gate.py` | `4d95960c0355beaa1f75a312062f3b91c5b6d12b17266d5c01b2af9bf0b1d140` |

Full GitHub Actions CI for the eventual commit is not yet verified.
