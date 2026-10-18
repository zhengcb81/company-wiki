"""Card section 5.1: the catalog-switch guard and the skip semantics.

``CWP_P4_CATALOG_CONFIG`` must resolve under ``tmp_path`` or this card's
``fixtures/``; pointing it at production config is the one hard failure the card
permits.  Every other missing input is a skip carrying a readable reason, or a
failure when ``CWP_P4_REQUIRE=1``.
"""

from __future__ import annotations

import pytest

from .conftest import skip_or_fail
from .support import constants as C
from .support import environment as E


def test_production_config_is_refused(p4_case) -> None:
    """Pointing the switch at production config raises; it never skips."""
    case = p4_case()
    with pytest.raises(E.ProductionConfigRefused) as excinfo:
        E.assert_catalog_config_allowed(C.PRODUCTION_CATALOG_CONFIG)
    assert C.ENV_CATALOG in str(excinfo.value), (
        f"the refusal must name {C.ENV_CATALOG}; got {excinfo.value!s}"
    )
    case.check("production_config_refused", "pass",
               {"reason": "hard failure as designed"})
    case.settle("pass")


def test_outside_fixture_roots_is_refused(p4_case) -> None:
    """An existing file outside tmp_path and fixtures/ is refused too."""
    case = p4_case()
    outside = C.REPO_ROOT / "pyproject.toml"
    assert outside.is_file(), f"probe target must exist for this test: {outside}"
    with pytest.raises(E.ProductionConfigRefused) as excinfo:
        E.assert_catalog_config_allowed(outside)
    assert "tmp_path" in str(excinfo.value), (
        f"the refusal must point at the allowed roots; got {excinfo.value!s}"
    )
    case.check("outside_roots_refused", "pass", {"path": str(outside)})
    case.settle("pass")


def test_skip_or_fail_semantics(monkeypatch, p4_case) -> None:
    """Without the require flag a missing input skips; with it, it fails."""
    case = p4_case()
    monkeypatch.delenv(C.ENV_REQUIRE, raising=False)
    with pytest.raises(pytest.skip.Exception) as skipped:
        skip_or_fail("probe reason")
    assert "probe reason" in str(skipped.value), (
        f"the skip must carry its reason; got {skipped.value!s}"
    )

    monkeypatch.setenv(C.ENV_REQUIRE, "1")
    with pytest.raises(pytest.fail.Exception) as failed:
        skip_or_fail("probe reason")
    assert "CWP_P4_REQUIRE=1" in str(failed.value), (
        f"the failure must explain the require flag; got {failed.value!s}"
    )
    case.check("require_flag_turns_skip_into_fail", "pass",
               {"reason": "both branches observed"})
    case.settle("pass")
