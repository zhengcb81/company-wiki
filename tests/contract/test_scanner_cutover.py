"""FC-305 RED/acceptance tests: scanner cutover with v1 read-only fallback.

The v2 scanner is enabled per-cohort through the RuntimePolicySnapshot's
v2_scan_shadow flag; v1 remains the read-only fallback.  Two consecutive
shadow diff=0 rounds are required before production dry shadow; a real
root's before/after fingerprint must be identical across the cutover.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _root(tmp_path: Path, *, root_id: str = "company_raw") -> RootSpec:
    root_dir = tmp_path / "companies" / "Acme" / "raw"
    root_dir.mkdir(parents=True)
    (root_dir / "2025.pdf").write_bytes(b"pdf-2025")
    (root_dir / "2025.source.json").write_text(
        '{"fiscal_year": 2025, "provider": "example"}', encoding="utf-8"
    )
    return RootSpec(
        root_id=root_id,
        path=tmp_path / "companies",
        kind="company_raw",
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )


# --- per-cohort v2 enablement via the runtime policy ------------------------


def test_v2_scan_enabled_by_snapshot_flag(tmp_path):
    """When the runtime policy's v2_scan_shadow is true, the scan pipeline
    runs the v2 adapter; when false, v1 runs."""
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root = _root(tmp_path)
    v2 = scan_root_strategy(root, ("Acme",), v2_scan_shadow=True)[0]
    v1 = scan_root_strategy(root, ("Acme",), v2_scan_shadow=False)[0]
    assert any(c.relative_path.endswith("2025.pdf") for c in v2)
    assert any(c.relative_path.endswith("2025.pdf") for c in v1)


def test_cutover_decision_reads_snapshot_flag(tmp_path):
    """cutover_decision(snapshot) returns v2 when v2_scan_shadow is on and
    v1 (with fallback available) otherwise."""
    from company_wiki.source_catalog.scanner import cutover_decision

    v2_snapshot = {
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": True, "v2_persist_assertions": False,
            "v2_resolve_shadow": False, "v2_resolve_active": False,
            "v2_bundle_active": False, "legacy_bridge_enabled": True,
        },
        "current_epoch": None,
        "active_cohorts": [],
        "policy_hash": "a" * 64,
        "updated_at": "2026-08-10T00:00:00Z",
    }
    assert cutover_decision(v2_snapshot) == "v2"
    v1_snapshot = dict(v2_snapshot)
    v1_snapshot["flags"] = dict(v2_snapshot["flags"])
    v1_snapshot["flags"]["v2_scan_shadow"] = False
    assert cutover_decision(v1_snapshot) == "v1"


# --- two consecutive shadow diff=0 rounds before production dry shadow ------


def test_two_zero_diff_rounds_required(tmp_path):
    """gate_production_dry_shadow requires two consecutive shadow diff=0
    rounds; one zero round is not enough; a diff in any required round
    fails the gate."""
    from company_wiki.source_catalog.scanner import gate_production_dry_shadow

    # two consecutive zero-diff rounds recorded -> gate passes
    assert gate_production_dry_shadow([[], []], rounds_required=2) is True
    # only one round recorded -> not enough
    assert gate_production_dry_shadow([[]], rounds_required=2) is False
    # a diff in the second required round -> fails
    assert gate_production_dry_shadow(
        [[], [("2025.pdf", "role")]], rounds_required=2
    ) is False
    # rounds_required below 2 is a misuse -> fails closed
    assert gate_production_dry_shadow([[], []], rounds_required=1) is False


def test_production_dry_shadow_refused_without_gate(tmp_path):
    """scan_catalog with v2 enabled must refuse to run a production dry
    shadow when the two-round zero-diff gate has not passed."""
    from company_wiki.source_catalog.scanner import (
        CutoverGateError,
        scan_catalog,
    )
    from company_wiki.source_catalog.config import load_catalog_config

    project = tmp_path / "project"
    (project / "companies" / "Acme" / "raw").mkdir(parents=True)
    (project / "companies" / "Acme" / "raw" / "2025.pdf").write_bytes(b"x")
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(project / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                "    path: '" + str(project / "companies").replace("\\", "/") + "'",
                "    priority: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    config = load_catalog_config(config_path, project_root=project)
    # v2 enabled with only ONE recorded zero-diff round -> gate refused
    with pytest.raises(CutoverGateError):
        scan_catalog(
            config,
            None,
            dry_run=True,
            v2_scan_shadow=True,
            zero_diff_rounds=1,
        )


# --- real root before/after fingerprint invariant ---------------------------


def test_root_fingerprint_unchanged_across_cutover(tmp_path):
    """The same root scanned by v1 and v2 must produce the same root
    fingerprint (paths + sizes + hashes) — the cutover must not change
    what the catalog sees."""
    from company_wiki.source_catalog.scanner import (
        root_fingerprint,
        scan_root_strategy,
    )

    root = _root(tmp_path)
    v1 = scan_root_strategy(root, ("Acme",), v2_scan_shadow=False)[0]
    v2 = scan_root_strategy(root, ("Acme",), v2_scan_shadow=True)[0]
    fp1 = root_fingerprint(v1)
    fp2 = root_fingerprint(v2)
    # v2 emits primaries with the same content; the fingerprint is the
    # stable file identity (path + size + content hash)
    assert fp1["files"] == fp2["files"], (
        f"root fingerprint changed across cutover: {fp1['files']} != {fp2['files']}"
    )
