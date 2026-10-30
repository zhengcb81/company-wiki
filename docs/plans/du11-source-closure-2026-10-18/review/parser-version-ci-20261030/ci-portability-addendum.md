# W21 CI portability addendum

2026-10-30. Independent read-only review: **PASS**, no blocking findings. Scope is solely `tests/unit/test_w21_pdf_runtime_launch.py::test_child_environment_omits_parent_python_search_config` at ROOT HEAD `1e4e9eb51804cd1857ad73245880320efa6171d8` plus the current uncommitted fixture diff.

Linux has no ambient `SYSTEMROOT`; the production child environment correctly preserves only allowlisted variables that actually exist. The original test incorrectly assumed that a Windows host variable always existed. Explicit monkeypatch values for `PATH` and `SYSTEMROOT` make the preservation fixture independent of the host. The existing presence assertion remains, and the new exact-value assertion verifies that values are retained unchanged. This test does not launch a child while the synthetic PATH is active, and monkeypatch restores the environment after the test.

The production owner `narrative_pdf_enhancement.py` has no diff against HEAD. This patch neither changes its allowlist nor teaches production to manufacture missing OS variables. No production behavior, resource bound, source proof, parser identity or canonical SDK C2 status changes.

Frozen file: `tests/unit/test_w21_pdf_runtime_launch.py`, 8,682 raw bytes.

- Raw SHA-256: `0b77af14dded28a4741f37721612147084826d6f90d8489144b356aadd063693`
- CRLF-to-LF normalized SHA-256: `ef65b760922147977487c03c614e09cfd3708ffc7c59fb1fcaf85d697b40d58e`

Read ROOT's `root-env-green.txt`: two W21 launch/guard modules, **20 passed in 2.57s** on Windows. No tests or SDK runs were repeated by this reviewer. This provides focused local validation; the next Linux CI must verify portability. CI run `41020271499` remains FAILED and is not retroactively green. The other 33 PDF/TXT fixture failures and their separate 113-test review are outside this addendum. W21 canonical SDK C2/aligned enhancement remains PARTIAL/OPEN.

This exact fixture change is acceptable to commit and publish with ROOT's separately reviewed fixes. Machine-readable freeze and receipt SHA are in `ci-portability-addendum.json`.
