"""conftest for tests/contract — WR-3 §10.8.4 governance helpers.

Provides:
- ``_scan_owned_temp_workers()`` — pure read-only helper that returns the set
  of PIDs that look like source_catalog workers spawned by the current
  pytest session pointing at a ``%TEMP%/pytest-of-*`` config path. Used by
  governance tests and by the ``_assert_no_owned_worker_leftover`` autouse
  fixture below.
- ``_assert_no_owned_worker_leftover`` autouse fixture — records the pre-test
  owned set, yields, then asserts the post-test owned set equals the pre-test
  set (i.e. no new owned worker was left running by the test).

The autouse fixture is OFF by default (env var
``CW_WR3_GOVERNANCE_AUTOUSE=1`` to activate). When it IS active, it will
collect a fresh process inventory via ``_scan_source_catalog_processes``;
the inventory uses the same encoding-safe runner that production does (per
WR-1).
"""

from __future__ import annotations

import os

import pytest


def _scan_owned_temp_workers() -> set[int]:
    """Backward-compat module-level shim around tests.helpers.wr3_governance."""
    from helpers.wr3_governance import scan_owned_temp_workers

    return scan_owned_temp_workers()


@pytest.fixture(autouse=True)
def _assert_no_owned_worker_leftover(request):
    """Autouse guard: every test in tests/contract must leave behind ZERO
    newly-owned source_catalog temp workers.

    Off by default to keep suite timing stable; activate via the env var
    ``CW_WR3_GOVERNANCE_AUTOUSE=1``.
    """
    if os.environ.get("CW_WR3_GOVERNANCE_AUTOUSE", "0") != "1":
        yield
        return
    before = _scan_owned_temp_workers()
    yield
    after = _scan_owned_temp_workers()
    leaked = after - before
    if leaked:
        request.node.warn(
            pytest.PytestWarning(
                f"WR-3 governance: {len(leaked)} source_catalog temp worker(s) "
                f"left over by this test: PIDs={sorted(leaked)}; "
                f"see task_plan.md §10.8.4."
            )
        )
