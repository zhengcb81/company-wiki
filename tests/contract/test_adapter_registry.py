"""WU-302 RED/audit tests: adapter registry — ID/version/capability gates."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.registry import (  # noqa: E402
    REGISTERED_ADAPTERS,
    admission_profile,
    registered_adapter,
)
from company_wiki.source_catalog.config import (  # noqa: E402
    CatalogConfigError,
    load_catalog_config,
)


def test_unknown_adapter_id_fails_closed():
    assert registered_adapter("nope_v99") is None


def test_registered_adapter_has_version_and_capabilities():
    for adapter_id, entry in REGISTERED_ADAPTERS.items():
        assert isinstance(entry.get("version"), str) and entry["version"]
        assert isinstance(entry.get("capabilities"), tuple) and entry["capabilities"]
        assert entry.get("admission_profile_id") in {
            "financial_evidence_v1", "generic_document_v1"
        }


def test_config_cannot_reference_module_path():
    """D-011: configuration must never import code paths."""
    cfg = (
        "schema_version: '1.0'\n"
        "catalog_dir: ${PROJECT_ROOT}/.source_catalog\n"
        "roots:\n"
        "  - root_id: evil\n"
        "    path: ${PROJECT_ROOT}/evil\n"
        "    kind: directory\n"
        "    adapter_id: company_wiki.source_catalog.adapters.sidecar\n"
    )
    path = Path("tests/fixtures/tmp_evil_config.yaml")
    path.write_text(cfg, encoding="utf-8")
    try:
        with pytest.raises(CatalogConfigError):
            load_catalog_config(path, project_root=Path("."))
    finally:
        path.unlink(missing_ok=True)


def test_future_root_reuses_sidecar_adapter(tmp_path):
    """A future_root with the same adapter/profile works with config only."""
    import yaml

    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [
            {
                "root_id": "future_root",
                "path": "${PROJECT_ROOT}/future_data",
                "kind": "directory",
                "adapter_id": "sidecar_filing_v1",
                "admission_profile_id": "financial_evidence_v1",
                "read_only": True,
                "reusable_for_filing": True,
            }
        ],
    }
    cfg = tmp_path / "source_catalog.yaml"
    cfg.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    config = load_catalog_config(cfg, project_root=tmp_path)
    assert config.roots[0].adapter_id == "sidecar_filing_v1"
    assert config.roots[0].reusable_for_filing is True


def test_generic_adapter_cannot_serve_filing():
    assert "filing" not in registered_adapter("generic_document_v1")["capabilities"]
    assert admission_profile("generic_document_v1")["allows_filing"] is False
