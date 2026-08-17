"""ZR-401 gate tests: RootPolicy 3.0 strict loader + snapshot export.

3.0 removes implicit permission expansion:
- schema_version MUST be "3.0"; an N-1 1.x/2.x config is rejected with a
  migration hint (never silently upgraded);
- privacy_class is REQUIRED per root (no default): external roots
  (kind != company_raw) must be private_user; company_raw must be public;
- external roots can never be a canonical write target;
- unknown root fields fail closed;
- reusable external roots must be read_only.

``export_root_policy_3x`` returns a versioned, privacy-redacted snapshot
hash (paths become tokens) — the envelope-binding hash (ZR-404).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.config import CatalogConfigError  # noqa: E402
from company_wiki.source_catalog.policy_3x import (  # noqa: E402
    ALLOWED_ROOT_FIELDS_3X,
    ROOT_POLICY_3X_SCHEMA,
    ROOT_POLICY_3X_SCHEMA_VERSION,
    export_root_policy_3x,
    load_root_policy_3x,
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
        "privacy_class": '"private_user"',
    }
    fields.update({k: str(v) for k, v in root_fields.items()})
    body = "\n".join(f"    {key}: {value}" for key, value in fields.items())
    return (
        'schema_version: "3.0"\n'
        'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
        "roots:\n"
        f"  -\n{body}\n"
    )


def _load3x(tmp_path, text: str):
    path = _write(tmp_path / "source_catalog.yaml", text)
    return load_root_policy_3x(path, project_root=tmp_path)


# --- 3.0 schema / N-N-1 ------------------------------------------------


def test_schema_versioned() -> None:
    assert ROOT_POLICY_3X_SCHEMA_VERSION == "3.0"
    assert ROOT_POLICY_3X_SCHEMA == "root-policy-3.0"
    assert "privacy_class" in ALLOWED_ROOT_FIELDS_3X


def test_3x_external_root_private_user_loads(tmp_path) -> None:
    cfg = _load3x(tmp_path, _config_text("root_a"))
    assert cfg.roots[0].root_id == "root_a"
    assert cfg.roots[0].privacy_class == "private_user"
    assert cfg.roots[0].read_only is True


def test_nn1_rejects_1x_and_2x_schema(tmp_path) -> None:
    """N/N-1: schema_version 1.x/2.x is rejected by the 3.0 loader with a
    migration hint — never silently upgraded."""
    for bad_schema in ("1.0", "2.0", "9.9", ""):
        text = _config_text("root_a").replace('schema_version: "3.0"',
                                              f'schema_version: "{bad_schema}"')
        with pytest.raises(CatalogConfigError, match="schema_version"):
            _load3x(tmp_path, text)


# --- privacy_class: no implicit permission expansion --------------------


def test_3x_missing_privacy_class_fails(tmp_path) -> None:
    text = _config_text("root_a").replace('    privacy_class: "private_user"\n', "")
    with pytest.raises(CatalogConfigError, match="privacy_class"):
        _load3x(tmp_path, text)


def test_3x_external_root_public_fails(tmp_path) -> None:
    """An external root declared public is a config error — no implicit
    public for private data."""
    with pytest.raises(CatalogConfigError, match="private_user"):
        _load3x(tmp_path, _config_text("root_a", privacy_class='"public"'))


def test_3x_company_raw_public_loads(tmp_path) -> None:
    cfg = _load3x(
        tmp_path,
        _config_text(
            "company_raw",
            kind='"company_raw"',
            privacy_class='"public"',
            canonical_write_target='"/tmp/companies"',
            read_only="false",
        ),
    )
    assert cfg.roots[0].kind == "company_raw"
    assert cfg.roots[0].privacy_class == "public"


def test_3x_company_raw_private_fails(tmp_path) -> None:
    """company_raw declared private is a config error (inverted)."""
    with pytest.raises(CatalogConfigError, match="public"):
        _load3x(
            tmp_path,
            _config_text(
                "company_raw",
                kind='"company_raw"',
                privacy_class='"private_user"',
                canonical_write_target='"/tmp/companies"',
                read_only="false",
            ),
        )


# --- external write target / unknown fields / read_only ----------------


def test_3x_external_root_write_target_fails(tmp_path) -> None:
    """External roots can never be a canonical write target — load fails."""
    with pytest.raises(CatalogConfigError, match="write target"):
        _load3x(
            tmp_path,
            _config_text("root_a", canonical_write_target='"/tmp/out"',
                         read_only="false"),
        )


def test_3x_unknown_root_field_fails(tmp_path) -> None:
    with pytest.raises(CatalogConfigError, match="unknown fields"):
        _load3x(tmp_path, _config_text("root_a", bogus_field='"x"'))


def test_3x_reusable_external_root_must_be_read_only(tmp_path) -> None:
    with pytest.raises(CatalogConfigError, match="read_only"):
        _load3x(
            tmp_path,
            _config_text("root_a", read_only="false", canonical_write_target="null"),
        )


# --- snapshot export: versioned + privacy-redacted + deterministic -----


def test_export_3x_snapshot_privacy_redacted_and_deterministic(tmp_path) -> None:
    cfg = _load3x(tmp_path, _config_text("root_a"))
    first_hash, first_policy = export_root_policy_3x(cfg, project_root=tmp_path)
    second_hash, second_policy = export_root_policy_3x(cfg, project_root=tmp_path)
    assert len(first_hash) == 64
    assert first_hash == second_hash  # deterministic
    assert first_policy == second_policy
    assert first_policy["schema_version"] == "3.0"
    assert first_policy["schema"] == "root-policy-3.0"
    root = first_policy["roots"][0]
    # path is a token, never an absolute path
    assert "/tmp/root" not in json.dumps(first_policy)
    assert root["path_ref"].startswith("${PROJECT_ROOT}/") or \
        root["path_ref"] == "<redacted-absolute-path>"
    assert root["privacy_class"] == "private_user"


def test_export_3x_hash_changes_when_privacy_changes(tmp_path) -> None:
    public_cfg = _load3x(
        tmp_path,
        _config_text(
            "company_raw", kind='"company_raw"', privacy_class='"public"',
            canonical_write_target='"/tmp/companies"', read_only="false",
        ),
    )
    private_hash, _ = export_root_policy_3x(public_cfg, project_root=tmp_path)
    # Changing the privacy class changes the snapshot hash.
    other = _load3x(
        tmp_path,
        _config_text(
            "company_raw", kind='"company_raw"', privacy_class='"public"',
            canonical_write_target='"/tmp/other"', read_only="false",
        ),
    )
    other_hash, _ = export_root_policy_3x(other, project_root=tmp_path)
    assert private_hash != other_hash
