"""WU-301 RED/audit tests: RootPolicy v2 config gates CFG-01..08."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config  # noqa: E402


def _write_config(tmp_path: Path, roots: list[dict], **top) -> Path:
    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": roots,
    }
    payload.update(top)
    path = tmp_path / "source_catalog.yaml"
    path.write_text(
        _yaml(payload), encoding="utf-8"
    )
    return path


def _yaml(obj) -> str:
    import yaml

    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)


def _root(**fields) -> dict:
    base = {
        "root_id": "test_root",
        "path": "${PROJECT_ROOT}/test_root",
        "kind": "directory",
    }
    base.update(fields)
    return base


def test_cfg01_unregistered_adapter_rejected(tmp_path):
    cfg = _write_config(tmp_path, [_root(adapter_id="unknown_adapter_v9")])
    with pytest.raises(CatalogConfigError, match="adapter"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg02_unknown_admission_profile_rejected(tmp_path):
    cfg = _write_config(tmp_path, [_root(admission_profile_id="mystery_profile")])
    with pytest.raises(CatalogConfigError, match="profile"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg03_duplicate_root_id_rejected(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(root_id="dup"),
        _root(root_id="dup", path="${PROJECT_ROOT}/other"),
    ])
    with pytest.raises(CatalogConfigError, match="duplicate|dup"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg04_unresolved_variable_rejected(tmp_path):
    cfg = _write_config(tmp_path, [_root(path="${UNKNOWN_VAR}/x")])
    with pytest.raises(CatalogConfigError, match="UNKNOWN_VAR|unresolved"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg05_reusable_external_root_not_readonly_rejected(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(read_only=False, reusable_for_filing=True)
    ])
    with pytest.raises(CatalogConfigError, match="read.only|read_only"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg06_overlapping_routes_rejected(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(routes=[
            {"include": ["**/*.pdf"], "adapter_id": "sidecar_filing_v1"},
            {"include": ["financial_reports/**"], "adapter_id": "sidecar_filing_v1"},
        ])
    ])
    with pytest.raises(CatalogConfigError, match="overlap|route"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg07_generic_document_as_filing_rejected(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(adapter_id="generic_document_v1", reusable_for_filing=True)
    ])
    with pytest.raises(CatalogConfigError, match="filing|generic"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_cfg08_same_physical_file_two_routes_rejected(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(routes=[
            {"include": ["**/annual/*.pdf"], "adapter_id": "sidecar_filing_v1"},
            {"include": ["**/*.pdf"], "adapter_id": "generic_document_v1"},
        ])
    ])
    with pytest.raises(CatalogConfigError, match="overlap|route"):
        load_catalog_config(cfg, project_root=tmp_path)


def test_v2_valid_config_loads(tmp_path):
    cfg = _write_config(tmp_path, [
        _root(
            adapter_id="sidecar_filing_v1",
            admission_profile_id="financial_evidence_v1",
            read_only=True,
            reusable_for_filing=True,
            routes=[{"include": ["**/annual/*.pdf"], "adapter_id": "sidecar_filing_v1"}],
        )
    ])
    config = load_catalog_config(cfg, project_root=tmp_path)
    root = config.roots[0]
    assert root.adapter_id == "sidecar_filing_v1"
    assert root.read_only is True
    assert root.reusable_for_filing is True
    assert len(root.routes) == 1


def test_v1_config_still_loads(tmp_path):
    """v1 配置（无 v2 字段）行为不变。"""
    cfg = _write_config(tmp_path, [
        {"root_id": "company_raw", "path": "${PROJECT_ROOT}/companies", "kind": "company_raw"}
    ])
    config = load_catalog_config(cfg, project_root=tmp_path)
    assert config.roots[0].adapter_id is None
    assert config.roots[0].read_only is True
