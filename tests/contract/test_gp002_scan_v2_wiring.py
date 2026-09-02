"""GP-002 RED/acceptance: the physical scan entry must follow the
activation snapshot's v2_scan_shadow flag (D-1 gap closure).

Review finding D-1: ``scan_catalog`` accepted ``v2_scan_shadow`` but never
forwarded it into ``_scan_catalog_impl`` -> ``scan_root_strategy``, so the
production scan always ran the v1 branch even though the runtime policy
snapshot (``.source_catalog/runtime_policy.json``) has ``v2_scan_shadow:
true`` (verified: production snapshot hash 732ee618...).  ``cutover_decision``
had no production caller.

Contracts driven by this module:

  GP2-01  ``scan_catalog(..., v2_scan_shadow=True)`` must run every root
          through ``scan_root_strategy(..., v2_scan_shadow=True)`` — both
          the dry-run branch and the real (store-writing) branch.
  GP2-02  ``SourceCatalog.scan()`` must resolve the flag from the runtime
          policy snapshot: v2 when the snapshot flag is on, v1 when the
          snapshot is absent (legacy default), fail-closed when the
          snapshot exists but is invalid.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.scanner import scan_catalog, scan_root_strategy
from company_wiki.source_catalog.store import CatalogStore

# --- GP2-01: scan_catalog forwards the flag into scan_root_strategy --------


def _project(tmp_path: Path) -> tuple[Path, RootSpec]:
    project = tmp_path / "project"
    companies = project / "companies" / "Acme" / "raw"
    companies.mkdir(parents=True)
    (companies / "2025.pdf").write_bytes(b"pdf-2025")
    root = RootSpec(
        root_id="company_raw",
        path=project / "companies",
        kind="company_raw",
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )
    return project, root


def _config(project: Path, root: RootSpec) -> CatalogConfig:
    return CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        reusable_root_kinds=("company_raw",),
        roots=(root,),
    )


def test_gp2_01_real_scan_forwards_v2_flag(tmp_path, monkeypatch) -> None:
    """A REAL scan with v2_scan_shadow=True must reach scan_root_strategy
    with v2_scan_shadow=True (today it silently runs v1)."""
    project, root = _project(tmp_path)
    config = _config(project, root)
    store = CatalogStore(config.database_path)
    observed: list[bool | None] = []
    original = scan_root_strategy

    def spy(root_spec, names, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return original(root_spec, names, **kwargs)

    monkeypatch.setattr("company_wiki.source_catalog.scanner.scan_root_strategy", spy)
    report = scan_catalog(config, store, v2_scan_shadow=True)
    assert report.files_seen >= 1
    assert observed and all(flag is True for flag in observed), (
        f"scan_root_strategy must receive v2_scan_shadow=True on a real "
        f"v2 scan (got {observed})"
    )


def test_gp2_01_dry_run_forwards_v2_flag(tmp_path, monkeypatch) -> None:
    """The dry-run branch must forward the flag too.  A v2 dry shadow is
    gated (FC-305: two consecutive zero-diff rounds), so the test passes
    ``zero_diff_rounds=2`` to represent two recorded clean rounds."""
    project, root = _project(tmp_path)
    config = _config(project, root)
    observed: list[bool | None] = []
    original = scan_root_strategy

    def spy(root_spec, names, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return original(root_spec, names, **kwargs)

    monkeypatch.setattr("company_wiki.source_catalog.scanner.scan_root_strategy", spy)
    scan_catalog(
        config,
        None,
        dry_run=True,
        v2_scan_shadow=True,
        zero_diff_rounds=2,
    )
    assert observed and all(flag is True for flag in observed), (
        f"dry-run scan must forward v2_scan_shadow=True (got {observed})"
    )


def test_gp2_01_flag_off_forwards_false(tmp_path, monkeypatch) -> None:
    """v2_scan_shadow=False (explicit) stays v1 through the seam."""
    project, root = _project(tmp_path)
    config = _config(project, root)
    store = CatalogStore(config.database_path)
    observed: list[bool | None] = []
    original = scan_root_strategy

    def spy(root_spec, names, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return original(root_spec, names, **kwargs)

    monkeypatch.setattr("company_wiki.source_catalog.scanner.scan_root_strategy", spy)
    scan_catalog(config, store, v2_scan_shadow=False)
    assert observed and all(flag is False for flag in observed), (
        f"v1 scan must forward v2_scan_shadow=False (got {observed})"
    )


# --- GP2-02: SourceCatalog.scan() follows the activation snapshot ----------


def _snapshot(project: Path, *, v2_scan_shadow: bool) -> None:
    from company_wiki.source_catalog.runtime_policy import snapshot_hash

    payload = {
        "schema_version": "1.0",
        "policy_hash": "c" * 64,
        "flags": {
            "v2_scan_shadow": v2_scan_shadow,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        "current_epoch": "e1",
        "active_cohorts": ["c1"],
        "updated_at": "2026-09-02T00:00:00Z",
    }
    payload["snapshot_sha256"] = snapshot_hash(payload)
    catalog_dir = project / ".source_catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "runtime_policy.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _scan_with_spy(
    project: Path, root: RootSpec, monkeypatch
) -> list[bool | None]:
    config = _config(project, root)
    catalog = SourceCatalog(config)
    observed: list[bool | None] = []

    def fake_scan_catalog(*args, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return scan_catalog(config, catalog.store, dry_run=kwargs.get("dry_run", False), root_ids=kwargs.get("root_ids"), v2_scan_shadow=kwargs.get("v2_scan_shadow", False))

    monkeypatch.setattr(
        "company_wiki.source_catalog.service.scan_catalog", fake_scan_catalog
    )
    catalog.scan()
    catalog.close()
    return observed


def test_gp2_02_snapshot_v2_on_routes_real_scan_to_v2(tmp_path, monkeypatch) -> None:
    """When the activation snapshot says v2_scan_shadow=true, the physical
    scan entry must forward v2 to the scanner seam."""
    project, root = _project(tmp_path)
    _snapshot(project, v2_scan_shadow=True)
    observed = _scan_with_spy(project, root, monkeypatch)
    assert observed == [True], (
        f"SourceCatalog.scan() must forward v2 when the snapshot flag is on "
        f"(got {observed})"
    )


def test_gp2_02_no_snapshot_stays_v1(tmp_path, monkeypatch) -> None:
    """No runtime policy file = legacy default v1 (backward compatible for
    temp projects and tooling that never activated a snapshot)."""
    project, root = _project(tmp_path)
    observed = _scan_with_spy(project, root, monkeypatch)
    assert observed == [False], (
        f"SourceCatalog.scan() without a snapshot must stay v1 (got {observed})"
    )


def test_gp2_02_snapshot_v2_dry_run_stays_v1(tmp_path, monkeypatch) -> None:
    """A plain dry-run diagnostic must NOT become a gated v2 dry shadow:
    snapshot v2 on + dry_run=True still runs the v1 branch (explicit
    v2 dry shadow with recorded rounds is an FC-305 operation handled at
    the scanner layer)."""
    project, root = _project(tmp_path)
    _snapshot(project, v2_scan_shadow=True)
    config = _config(project, root)
    catalog = SourceCatalog(config)
    observed: list[bool | None] = []

    def fake_scan_catalog(*args, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return scan_catalog(
            config,
            None,
            dry_run=True,
            root_ids=kwargs.get("root_ids"),
            v2_scan_shadow=kwargs.get("v2_scan_shadow", False),
        )

    monkeypatch.setattr(
        "company_wiki.source_catalog.service.scan_catalog", fake_scan_catalog
    )
    catalog.scan(dry_run=True)
    catalog.close()
    assert observed == [False], (
        f"dry-run must stay v1 even with a v2 snapshot (got {observed})"
    )


def test_gp2_02_corrupt_snapshot_degrades_to_v1(tmp_path, monkeypatch) -> None:
    """A present-but-invalid snapshot degrades to v1 for scanning (no
    crash): scanning is a read-heavy catalog operation with no external
    data exposure, so silent v1 is safe.  (The LLM exit gate in GP-003
    applies stricter fail-closed semantics.)"""
    project, root = _project(tmp_path)
    catalog_dir = project / ".source_catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "runtime_policy.json").write_text(
        "{not-json", encoding="utf-8"
    )
    config = _config(project, root)
    catalog = SourceCatalog(config)
    observed: list[bool | None] = []
    original = scan_root_strategy

    def spy(root_spec, names, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return original(root_spec, names, **kwargs)

    monkeypatch.setattr("company_wiki.source_catalog.scanner.scan_root_strategy", spy)
    report = catalog.scan()
    assert report.files_seen >= 1
    assert observed and all(flag is False for flag in observed), (
        f"corrupt snapshot must degrade to v1 (got {observed})"
    )
