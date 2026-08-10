"""FC-304 RED/acceptance tests: unknown future root, config-only.

A temp ``future_lake`` root + sidecar adapter must be usable by changing
ONLY the config (2.x RootPolicy) — no scanner/resolver product-code edits.
EX-08 runs config load -> adapter dispatch -> candidate pipeline.  An
architecture gate scans production Python for root-ID / kind / Dropbox
path special-casing (a future root must never require product-code
changes).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _future_root(tmp_path: Path) -> RootSpec:
    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    (root_dir / "x.pdf").write_bytes(b"x")
    (root_dir / "x.source.json").write_text(
        '{"fiscal_year": 2025, "provider": "example"}', encoding="utf-8"
    )
    return RootSpec(
        root_id="future_lake",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )


# --- EX-08: config-only future root flows the whole chain ------------------


def test_ex08_config_only_future_root_scan(tmp_path):
    """A 2.x config with a future_lake root loads, and the v2 shadow path
    produces candidates — no product-code edits."""
    from company_wiki.source_catalog.policy_2x import load_root_policy_2x
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    (root_dir / "x.pdf").write_bytes(b"x")
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(tmp_path / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  -",
                "    root_id: future_lake",
                "    kind: directory",
                "    path: '" + str(root_dir).replace("\\", "/") + "'",
                "    adapter_id: sidecar_filing_v1",
                "    admission_profile_id: financial_evidence_v1",
                "    read_only: true",
                "    reusable_for_filing: true",
                "    allowed_document_kinds: ['annual_report']",
                "    priority: 10",
                "    cohort: future-cohort",
                "    canonical_write_target: null",
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_root_policy_2x(config_path, project_root=tmp_path)
    assert cfg.roots[0].root_id == "future_lake"
    root = cfg.roots[0]
    candidates, _, _ = scan_root_strategy(root, (), v2_scan_shadow=True)
    assert any(c.relative_path.endswith("x.pdf") for c in candidates)


def test_ex08_future_root_export_snapshot(tmp_path):
    """The future root appears in the 2.x policy snapshot with its explicit
    fields — consumers see it without any code knowledge of the root."""
    from company_wiki.source_catalog.policy_2x import (
        export_policy_2x,
        load_root_policy_2x,
    )

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(tmp_path / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  -",
                "    root_id: future_lake",
                "    kind: directory",
                "    path: '" + str(root_dir).replace("\\", "/") + "'",
                "    adapter_id: sidecar_filing_v1",
                "    admission_profile_id: financial_evidence_v1",
                "    read_only: true",
                "    reusable_for_filing: true",
                "    allowed_document_kinds: ['annual_report']",
                "    priority: 10",
                "    cohort: future-cohort",
                "    canonical_write_target: null",
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_root_policy_2x(config_path, project_root=tmp_path)
    _, policy = export_policy_2x(cfg)
    roots = {r["root_id"]: r for r in policy["roots"]}
    assert "future_lake" in roots
    assert roots["future_lake"]["adapter_id"] == "sidecar_filing_v1"
    assert roots["future_lake"]["cohort"] == "future-cohort"


# --- architecture gate: no root-ID / kind / Dropbox special-casing ---------


def test_gate_no_root_id_hardcode_in_production(tmp_path):
    """Production Python must not contain hardcoded root IDs or Dropbox
    paths — a future root must never require code edits."""
    from company_wiki.source_catalog.architecture_gate import (
        no_root_specific_hardcode,
    )

    ok, violations = no_root_specific_hardcode()
    assert ok, f"root-specific hardcodes: {violations}"


def test_gate_detects_root_id_hardcode(tmp_path):
    """Adversarial: a temp module hardcoding a root ID must trip the gate."""
    from company_wiki.source_catalog.architecture_gate import (
        no_root_specific_hardcode,
    )

    (tmp_path / "evil.py").write_text(
        'ROOT = "dropbox_stock"\nif root_id == "company_raw":\n    pass\n',
        encoding="utf-8",
    )
    ok, violations = no_root_specific_hardcode(tmp_path)
    assert not ok
    assert any("dropbox_stock" in item for item in violations)
    assert any("company_raw" in item for item in violations)


# --- EX-08 mutation: config-only must stay config-only ----------------------


def test_ex08_future_root_requires_no_scanner_edit(tmp_path):
    """The v2 dispatch resolves the future root through the registry —
    mutation: removing the adapter from the registry must fail the config
    load (fail closed), never silently fall back to kind-based guessing."""
    from company_wiki.source_catalog.policy_2x import load_root_policy_2x

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(tmp_path / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  -",
                "    root_id: future_lake",
                "    kind: directory",
                "    path: '" + str(root_dir).replace("\\", "/") + "'",
                "    adapter_id: not_registered_v1",
                "    admission_profile_id: financial_evidence_v1",
                "    read_only: true",
                "    reusable_for_filing: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_root_policy_2x(config_path, project_root=tmp_path)
