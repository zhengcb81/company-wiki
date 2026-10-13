"""Storage routing is one ordered include/exclude decision across versions."""
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config
from company_wiki.source_catalog.models import RootSpec, RouteSpec
from company_wiki.source_catalog.policy_2x import load_root_policy_2x
from company_wiki.source_catalog.policy_3x import load_root_policy_3x

LOADERS = [(load_catalog_config, "1.0"), (load_root_policy_2x, "1.0"), (load_root_policy_3x, "3.0")]


def _load(tmp_path, loader, version, routes):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"schema_version": version, "catalog_dir": "catalog",
        "roots": [{"root_id": "arbitrary-root", "path": "资料 中文 根", "kind": "directory",
                   "adapter_id": "sidecar_filing_v1", "routes": routes}]}), encoding="utf-8")
    return loader(path, project_root=tmp_path).roots[0]


@pytest.mark.parametrize("loader,version", LOADERS)
def test_overlapping_routes_use_order_for_non_sample_paths(tmp_path, loader, version):
    root = _load(tmp_path, loader, version, [
        {"include": ["issuer-x/**"], "adapter_id": "company_raw_v1"},
        {"include": ["issuer-x/**"], "adapter_id": "dayu_filing_v1"},
    ])
    assert root.first_matching_route("issuer-x/new.pdf") is root.routes[0]
    assert replace(root, routes=tuple(reversed(root.routes))).first_matching_route("issuer-x/new.pdf").adapter_id == "dayu_filing_v1"


@pytest.mark.parametrize("loader,version", LOADERS)
def test_excludes_do_not_trigger_false_overlap_rejection(tmp_path, loader, version):
    root = _load(tmp_path, loader, version, [
        {"include": ["**/*.pdf"], "exclude": ["financial_reports/**"], "adapter_id": "company_raw_v1"},
        {"include": ["financial_reports/**"], "adapter_id": "sidecar_filing_v1"},
    ])
    assert root.first_matching_route("financial_reports/annual/2025.pdf") is root.routes[1]
    assert root.route_matches("financial_reports/annual/2025.pdf")
    assert root.first_matching_route("issuer-x/brief.pdf") is root.routes[0]


@pytest.mark.parametrize("loader,version", LOADERS)
@pytest.mark.parametrize("fields", [
    {"include": "*.pdf"}, {"include": ["*.pdf"], "exclude": [3]},
    {"include": ["*.pdf"], "adapter_id": "unknown_adapter"},
    {"include": ["*.pdf"], "admission_profile_id": "unknown_profile"},
])
def test_invalid_route_shape_or_unknown_ports_still_refused(tmp_path, loader, version, fields):
    with pytest.raises(CatalogConfigError):
        _load(tmp_path, loader, version, [fields])


def test_empty_routes_and_empty_override_keep_default_adapter():
    root = RootSpec("r", Path("unused"), "directory", adapter_id="sidecar_filing_v1")
    assert root.first_matching_route("anything.pdf") is None
    assert not root.route_matches("anything.pdf")
    assert replace(root, routes=(RouteSpec(include=("资料/**",)),)).first_matching_route("资料") is not None
