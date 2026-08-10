"""FC-301 RED/acceptance tests: RootPolicy 2.x loader/doctor.

2.x makes every root's adapter, admission profile, read_only,
reusable_for_filing, allowed kinds, cohort and canonical write target
explicit (no kind-based guessing, ADR-010 / architecture_target section 3).
Loading must reject external roots that are writable, unknown
adapter/profile, widening routes, and duplicate roots.  A 1.x->2.x doctor
reports migration status WITHOUT changing production scan behavior.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.config import (  # noqa: E402
    CatalogConfigError,
    load_catalog_config,
)


def _write(path: Path, payload: str) -> Path:
    path.write_text(payload, encoding="utf-8")
    return path


def _config_text(root_id: str, **root_fields) -> str:
    fields = {
        "root_id": root_id,
        "kind": '"directory"',
        "path": '"/tmp/root"',
        "adapter_id": '"sidecar_filing_v1"',
        "admission_profile_id": '"financial_evidence_v1"',
        "read_only": "true",
        "reusable_for_filing": "true",
        "allowed_document_kinds": '["annual_report"]',
        "priority": "10",
        "cohort": '"cohort-a"',
        "canonical_write_target": "null",
    }
    fields.update({k: str(v) for k, v in root_fields.items()})
    body = "\n".join(f"    {key}: {value}" for key, value in fields.items())
    return (
        'schema_version: "1.0"\n'
        'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
        "roots:\n"
        f"  -\n{body}\n"
    )


def _load2x(tmp_path, text: str):
    """Load via the 2.x loader (schema 2.0) with per-root explicit policy."""
    from company_wiki.source_catalog.policy_2x import load_root_policy_2x

    path = _write(tmp_path / "source_catalog.yaml", text)
    return load_root_policy_2x(path, project_root=tmp_path)


# --- 2.x explicit root policy loads ----------------------------------------


def test_2x_explicit_root_policy_loads(tmp_path):
    cfg = _load2x(tmp_path, _config_text("root_a"))
    assert cfg.roots[0].root_id == "root_a"
    assert cfg.roots[0].adapter_id == "sidecar_filing_v1"
    assert cfg.roots[0].admission_profile_id == "financial_evidence_v1"
    assert cfg.roots[0].read_only is True
    assert cfg.roots[0].reusable_for_filing is True
    assert cfg.roots[0].allowed_document_kinds == ("annual_report",)
    assert cfg.roots[0].cohort == "cohort-a"
    assert cfg.roots[0].canonical_write_target is None


def test_2x_company_raw_can_be_write_target(tmp_path):
    cfg = _load2x(
        tmp_path,
        _config_text(
            "company_raw",
            kind="company_raw",
            adapter_id='"company_raw_v1"',
            read_only="false",
            canonical_write_target='"companies"',
        ),
    )
    assert cfg.roots[0].canonical_write_target == "companies"
    assert cfg.roots[0].read_only is False


# --- fail-closed rejections ------------------------------------------------


def test_2x_external_root_writable_rejected(tmp_path):
    """Only company_raw may be a write target; an external root (directory /
    dayu_portfolio kind) with a write target must fail closed."""
    with pytest.raises(CatalogConfigError):
        _load2x(
            tmp_path,
            _config_text(
                "dropbox_stock",
                kind="directory",
                canonical_write_target='"companies"',
            ),
        )


def test_2x_unknown_adapter_rejected(tmp_path):
    with pytest.raises(CatalogConfigError):
        _load2x(tmp_path, _config_text("root_a", adapter_id='"nope_adapter"'))


def test_2x_unknown_profile_rejected(tmp_path):
    with pytest.raises(CatalogConfigError):
        _load2x(
            tmp_path,
            _config_text("root_a", admission_profile_id='"nope_profile"'),
        )


def test_2x_duplicate_root_rejected(tmp_path):
    # one config with two roots sharing the same root_id
    header = (
        'schema_version: "1.0"\n'
        'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
        "roots:\n"
    )
    body = _config_text("root_a").split("roots:\n", 1)[1]
    text = header + body + body
    with pytest.raises(CatalogConfigError):
        _load2x(tmp_path, text)


def test_2x_widening_route_rejected(tmp_path):
    """A route whose allowed kinds exceed the root's allowed kinds is a
    widening route (route must be a subset of the root policy)."""
    with pytest.raises(CatalogConfigError):
        _load2x(
            tmp_path,
            _config_text(
                "root_a",
                routes='[{include: ["*.pdf"], exclude: [], '
                'allowed_document_kinds: ["research_report"]}]',
            ),
        )


# --- N/N-1: 1.x configs keep loading (read-only fallback) ------------------


def test_1x_config_still_loads_via_legacy_loader(tmp_path):
    path = _write(
        tmp_path / "source_catalog.yaml",
        (
            'schema_version: "1.0"\n'
            'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
            'reusable_root_kinds: [company_raw, dayu_portfolio, directory]\n'
            "roots:\n"
            "  - root_id: company_raw\n"
            "    kind: company_raw\n"
            '    path: "${PROJECT_ROOT}/companies"\n'
            "    priority: 10\n"
        ),
    )
    cfg = load_catalog_config(path, project_root=tmp_path)  # 1.x loader
    assert cfg.roots[0].root_id == "company_raw"


# --- 1.x -> 2.x doctor ------------------------------------------------------


def test_doctor_reports_1x_as_legacy(tmp_path):
    from company_wiki.source_catalog.policy_2x import doctor_root_policy

    path = _write(
        tmp_path / "source_catalog.yaml",
        (
            'schema_version: "1.0"\n'
            'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
            "roots:\n"
            "  - root_id: company_raw\n"
            "    kind: company_raw\n"
            '    path: "${PROJECT_ROOT}/companies"\n'
        ),
    )
    report = doctor_root_policy(path, project_root=tmp_path)
    assert report["schema"] == "1.0"
    assert report["policy_version"] == "1.x"
    assert any("adapter_id" in item or "adapter" in item
               for item in report["missing_2x_fields"])


def test_doctor_reports_2x_as_current(tmp_path):
    from company_wiki.source_catalog.policy_2x import doctor_root_policy

    path = _write(tmp_path / "source_catalog.yaml", _config_text("root_a"))
    report = doctor_root_policy(path, project_root=tmp_path)
    assert report["schema"] == "1.0"  # YAML schema stays 1.0 (additive)
    assert report["policy_version"] == "2.x"
    assert report["missing_2x_fields"] == []


def test_doctor_2x_export_snapshot_hashes(tmp_path):
    """The 2.x export produces a canonical RootPolicySnapshot 2.0 with the
    contract fields and a stable hash (filing consumes only the hash)."""
    from company_wiki.source_catalog.policy_2x import export_policy_2x

    cfg = _load2x(tmp_path, _config_text("root_a"))
    policy_hash, policy = export_policy_2x(cfg)
    assert len(policy_hash) == 64
    assert policy["schema_version"] == "2.0"
    root = policy["roots"][0]
    for field in (
        "root_id", "path_ref", "adapter_id", "admission_profile_id",
        "read_only", "reusable_for_filing", "allowed_document_kinds",
        "canonical_write_target", "priority", "cohort",
    ):
        assert field in root, f"missing 2.x field {field}"
    # deterministic: same config -> same hash
    again = export_policy_2x(cfg)
    assert again[0] == policy_hash
