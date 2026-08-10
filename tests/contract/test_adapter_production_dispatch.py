"""FC-302 RED/acceptance tests: production AdapterRegistry dispatch.

The scanner facade must dispatch root scans through the registered
adapter (effective route) — SidecarFilingAdapter / CompanyRawAdapter /
DayuAdapter must each have a production caller; the v2 shadow path calls
the adapter instead of raising 'unavailable'; scanner keeps writing
unified candidates, never a root-specific metadata container.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _root(*, kind: str, adapter_id: str, root_id: str = "root_x") -> RootSpec:
    return RootSpec(
        root_id=root_id,
        path=Path("/tmp/root_x"),
        kind=kind,
        adapter_id=adapter_id,
        read_only=True,
        reusable_for_filing=True,
    )


# --- dispatch resolves the registered adapter for a root ----------------


def test_dispatch_sidecar_adapter_by_id():
    from company_wiki.source_catalog.adapter_dispatch import adapter_for

    root = _root(kind="directory", adapter_id="sidecar_filing_v1")
    adapter = adapter_for(root)
    assert adapter.adapter_id == "sidecar_filing_v1"


def test_dispatch_company_raw_adapter_by_id():
    from company_wiki.source_catalog.adapter_dispatch import adapter_for

    root = _root(kind="company_raw", adapter_id="company_raw_v1")
    adapter = adapter_for(root)
    assert adapter.adapter_id == "company_raw_v1"


def test_dispatch_dayu_adapter_by_id():
    from company_wiki.source_catalog.adapter_dispatch import adapter_for

    root = _root(kind="dayu_portfolio", adapter_id="dayu_filing_v1")
    adapter = adapter_for(root)
    assert adapter.adapter_id == "dayu_filing_v1"


def test_dispatch_unknown_adapter_fails_closed():
    from company_wiki.source_catalog.adapter_dispatch import (
        AdapterDispatchError,
        adapter_for,
    )

    root = _root(kind="directory", adapter_id="not_registered_v1")
    with pytest.raises(AdapterDispatchError, match="not registered"):
        adapter_for(root)


def test_dispatch_missing_adapter_id_fails_closed():
    from company_wiki.source_catalog.adapter_dispatch import (
        AdapterDispatchError,
        adapter_for,
    )

    root = _root(kind="directory", adapter_id=None)
    with pytest.raises(AdapterDispatchError, match="no adapter_id"):
        adapter_for(root)


# --- scanner facade: v2 shadow path calls the adapter ---------------------


def test_v2_shadow_dispatch_calls_sidecar_adapter(tmp_path):
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root_dir = tmp_path / "root"
    root_dir.mkdir()
    (root_dir / "a.pdf").write_bytes(b"hello")
    (root_dir / "a.source.json").write_text(
        '{"fiscal_year": 2025}', encoding="utf-8"
    )
    root = RootSpec(
        root_id="dropbox_stock",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )
    result = scan_root_strategy(
        root, (), v2_scan_shadow=True,
    )
    # the adapter produced candidates (not 'v2 scanner unavailable')
    assert result is not None
    assert len(result[0]) >= 1
    assert any(
        candidate.relative_path.endswith("a.pdf")
        for candidate in result[0]
    )


def test_v2_shadow_dispatch_company_raw_adapter(tmp_path):
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root_dir = tmp_path / "companies" / "Acme" / "raw"
    root_dir.mkdir(parents=True)
    (root_dir / "2025.pdf").write_bytes(b"pdf")
    root = RootSpec(
        root_id="company_raw",
        path=tmp_path / "companies",
        kind="company_raw",
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )
    result = scan_root_strategy(root, ("Acme",), v2_scan_shadow=True)
    assert result is not None
    assert any(
        candidate.relative_path.endswith("2025.pdf")
        for candidate in result[0]
    )


# --- adapter classes have production callers ------------------------------


def test_adapters_reachable_from_production_dispatch():
    """The three adapters must be named in the production dispatch module
    (adapter_dispatch), not only in tests."""
    import inspect

    from company_wiki.source_catalog import adapter_dispatch

    source = inspect.getsource(adapter_dispatch)
    for adapter_id in (
        "sidecar_filing_v1",
        "company_raw_v1",
        "dayu_filing_v1",
    ):
        assert adapter_id in source, (
            f"{adapter_id} missing from production dispatch"
        )


# --- scanner keeps unified candidates (no root-specific containers) -------


def test_scan_root_strategy_v1_behavior_unchanged(tmp_path):
    """The v1 path must still work exactly as before (no adapter rewrite
    of the operational scanner)."""
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root_dir = tmp_path / "companies" / "Acme" / "raw"
    root_dir.mkdir(parents=True)
    (root_dir / "2025.pdf").write_bytes(b"pdf")
    (root_dir / "2025.source.json").write_text(
        '{"fiscal_year": 2025}', encoding="utf-8"
    )
    root = RootSpec(
        root_id="company_raw",
        path=tmp_path / "companies",
        kind="company_raw",
        adapter_id=None,
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )
    candidates, excluded, policy_excluded = scan_root_strategy(
        root, ("Acme",), v2_scan_shadow=False,
    )
    assert excluded == 0
    assert any(c.role == "original_primary" for c in candidates)
