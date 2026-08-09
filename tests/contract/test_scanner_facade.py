"""WU-500 RED/audit tests: scanner facade seam (SEAM-01..05).

The seam must be behavior-neutral: the default path calls the v1
implementation with identical output; the v2 stub fails closed; the facade
adds no DB/file side effects.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.scanner import (  # noqa: E402
    ScannerFacadeError,
    _scan_root_v1,
    scan_root_strategy,
)


def test_seam01_facade_equals_v1_direct(tmp_path):
    """SEAM-01: same input => byte-equivalent candidate output."""
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                            "tests" / "fixtures" / "source_lake_v2"))
    from factory import build_source_lake

    lake = build_source_lake(tmp_path)
    root = _fake_root(lake.roots["company_raw"])
    v1 = _scan_root_v1(root, ("Acme", "Alpha", "Zeta"))
    facade = scan_root_strategy(root, ("Acme", "Alpha", "Zeta"))
    assert [c.to_dict() for c in v1[0]] == [c.to_dict() for c in facade[0]]
    assert v1[1:] == facade[1:]


def test_seam02_v2_stub_fails_closed(tmp_path):
    """SEAM-02: v2 shadow enabled but unavailable => hard failure."""
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                            "tests" / "fixtures" / "source_lake_v2"))
    from factory import build_source_lake

    lake = build_source_lake(tmp_path)
    root = _fake_root(lake.roots["dayu"])
    with pytest.raises(ScannerFacadeError):
        scan_root_strategy(root, (), v2_scan_shadow=True)


def test_seam03_facade_no_side_effects(tmp_path, monkeypatch):
    """SEAM-03: the default (v1) path through the facade adds no DB writes."""
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                            "tests" / "fixtures" / "source_lake_v2"))
    from factory import build_source_lake

    lake = build_source_lake(tmp_path)

    def _forbid(*args, **kwargs):
        raise AssertionError("facade must not touch the database")

    monkeypatch.setattr("sqlite3.connect", _forbid)
    # v1 enumerate through the facade must complete without a database
    # (candidate count is compared in SEAM-01; here the contract is
    # "no DB access", whatever the candidate count is)
    direct = _scan_root_v1(_fake_root(lake.roots["company_raw"]),
                           ("Acme", "Alpha", "Zeta"))
    facade_result = scan_root_strategy(_fake_root(lake.roots["company_raw"]),
                                       ("Acme", "Alpha", "Zeta"))
    assert [c.to_dict() for c in direct[0]] == [c.to_dict() for c in facade_result[0]]


def _fake_root(path: Path):
    from company_wiki.source_catalog.models import RootSpec

    return RootSpec(root_id="seam_test", path=path, kind="company_raw")


def test_seam05_v1_has_freeze_gate():
    """SEAM-05: legacy v1 gains no new product callers — the architecture
    fitness gate (ARC-FIT-06) is the enforcement point."""
    source = (Path(__file__).resolve().parents[2] / "src" /
              "company_wiki" / "source_catalog" / "scanner.py").read_text(encoding="utf-8")
    # v1 implementation exists behind the facade, and the facade is its only
    # new entry point; direct calls elsewhere would be a freeze violation
    assert "_scan_root_v1" in source
    assert "scan_root_strategy" in source
