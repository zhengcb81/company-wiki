"""Policy versions share shape validation instead of coercing user input."""
import pytest
import yaml

from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config
from company_wiki.source_catalog.policy_2x import load_root_policy_2x
from company_wiki.source_catalog.policy_3x import load_root_policy_3x


@pytest.mark.parametrize("loader,version", [
    (load_catalog_config, "1.0"), (load_root_policy_2x, "1.0"), (load_root_policy_3x, "3.0")
])
@pytest.mark.parametrize("value", ["false", "true", 0, 1, [], {}])
def test_reusable_flag_never_coerces_malformed_values(tmp_path, loader, version, value):
    payload = {"schema_version": version, "catalog_dir": "catalog", "roots": [{
        "root_id": "sources", "path": "data", "kind": "directory",
        "read_only": True, "reusable_for_filing": value,
    }]}
    config = tmp_path / "source_catalog.yaml"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CatalogConfigError, match="reusable_for_filing must be a boolean"):
        loader(config, project_root=tmp_path)


@pytest.mark.parametrize("missing", ["schema_version", "catalog_dir", "roots"])
def test_policy_loader_reports_missing_required_fields(tmp_path, missing):
    payload = {"schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
        "root_id": "sources", "path": "data", "kind": "directory",
    }]}
    del payload[missing]
    config = tmp_path / "source_catalog.yaml"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CatalogConfigError, match="schema_version/catalog_dir/roots"):
        load_root_policy_2x(config, project_root=tmp_path)


@pytest.mark.parametrize("loader,version", [
    (load_catalog_config, "1.0"), (load_root_policy_2x, "1.0"), (load_root_policy_3x, "3.0")
])
@pytest.mark.parametrize("value", [True, False, None])
def test_valid_policy_flags_remain_compatible(tmp_path, loader, version, value):
    payload = {"schema_version": version, "catalog_dir": "catalog", "roots": [{
        "root_id": "sources", "path": "data", "kind": "directory",
        "read_only": True, "reusable_for_filing": value,
    }]}
    config = tmp_path / "source_catalog.yaml"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    assert loader(config, project_root=tmp_path).roots[0].reusable_for_filing is value
