"""Real bounded adapter discovery registers raw and serves a public SourceRef."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits, LocalReadBudget
from company_wiki.source_catalog.local_reconcile import _discover_source_groups
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader


def _raw(root):
    path = root / "示例 公司" / "投资者沟通.txt"
    path.parent.mkdir(parents=True)
    data = "公司正在拓展出海业务，尚未确认新订单。".encode()
    path.write_bytes(data)
    path.with_name(path.name + ".source.json").write_text(json.dumps({
        "company_name": "示例 公司", "market": "CN", "security_id": "600000",
        "document_kind": "investor_relations", "source_title": "示例公司投资者沟通",
        "source_url": "https://example.test/investors/notes.txt",
        "published_date": "2026-10-01", "provider": "cninfo",
        "provider_document_id": "ir-2026-10-01", "language": "zh-CN",
        "retrieved_at": "2026-10-02T00:00:00Z", "adapter_name": "fixture",
        "adapter_version": "1.0.0", "content_sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data), "mime_type": "text/plain",
    }, ensure_ascii=False), encoding="utf-8")
    return path, data


def _identity():
    return SimpleNamespace(canonical_name="示例 公司", ticker="600000", security_id="600000")


def test_same_company_layout_in_two_configured_directory_roots(tmp_path):
    roots = tuple(RootSpec(name, tmp_path / (name + " 中文 根"), "directory",
                           adapter_id="company_raw_v1", reusable_for_filing=True)
                  for name in ("external_one", "external_two"))
    for root in roots:
        root.path.mkdir(parents=True)
    cat = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", roots,
                                    reusable_root_kinds=("directory",)))
    cat.scan()
    originals = [_raw(root.path) for root in roots]
    before = {path: path.read_bytes() for root in roots for path in root.path.rglob("*") if path.is_file()}
    try:
        assert _discover_source_groups(cat, _identity(), LocalReadBudget(LocalPrepareLimits()))
        request = SourceRequest(entity="示例 公司", market="CN", security_id="600000",
                                document_kind="investor_relations", as_of_date="2026-10-13")
        reader = SourceVersionReader(cat)
        result = reader.query_local(request)
        assert result.status == "found"
        ref = result.matches[0]
        assert reader.open_version(ref, purpose="source_export").data == originals[0][1]
        rows = cat.reader.exact_source_locations(ref.document_id, ref.source_id)
        assert {row["root_id"] for row in rows} == {root.root_id for root in roots}
        assert not _discover_source_groups(cat, _identity(), LocalReadBudget(LocalPrepareLimits()))
        assert {path: path.read_bytes() for path in before} == before
    finally:
        cat.close()


def test_adapter_discovery_obeys_existing_aggregate_entry_budget(tmp_path):
    root = RootSpec("independent_root", tmp_path / "资料 根", "directory",
                    adapter_id="company_raw_v1", reusable_for_filing=True)
    root.path.mkdir(parents=True)
    cat = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", (root,)))
    cat.scan()
    original, _ = _raw(root.path)
    before = original.read_bytes()
    try:
        with pytest.raises(SourceReadError, match="local_discovery_entry_limit"):
            _discover_source_groups(cat, _identity(), LocalReadBudget(
                LocalPrepareLimits(max_discovery_entries=1)))
        assert original.read_bytes() == before
        assert not list(root.path.rglob("*.tmp"))
    finally:
        cat.close()


def test_real_scanner_and_discovery_share_first_route_owner_for_sidecar_group(tmp_path):
    from company_wiki.source_catalog.models import RouteSpec
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root = RootSpec("route-root", tmp_path / "配置 根", "directory",
                    adapter_id="sidecar_filing_v1", reusable_for_filing=True,
                    routes=(RouteSpec(include=("**/*.txt",), adapter_id="company_raw_v1",
                                      admission_profile_id="financial_evidence_v1"),
                            RouteSpec(include=("**",), adapter_id="dayu_filing_v1")))
    root.path.mkdir(parents=True)
    original, data = _raw(root.path)
    candidates, _, _ = scan_root_strategy(root, (), v2_scan_shadow=True)
    group = [item for item in candidates if item.group_key == original.relative_to(root.path).as_posix()]
    assert {item.role for item in group} == {"original_primary", "metadata"}
    assert {item.root.adapter_id for item in group} == {"company_raw_v1"}
    assert {item.root.admission_profile_id for item in group} == {"financial_evidence_v1"}
    assert len({item.relative_path for item in candidates}) == len(candidates)
    cat = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", (root,)))
    try:
        # Do not scan: initialize empty catalog to prove local preparation uses
        # the same route owner and the same caller-owned discovery budget.
        cat.store
        assert _discover_source_groups(cat, _identity(), LocalReadBudget(LocalPrepareLimits()))
        reader = SourceVersionReader(cat)
        result = reader.query_local(SourceRequest(entity="示例 公司", market="CN",
            security_id="600000", document_kind="investor_relations", as_of_date="2026-10-13"))
        assert result.status == "found"
        assert reader.open_version(result.matches[0], purpose="source_export").data == data
        assert original.read_bytes() == data
    finally:
        cat.close()


def test_distinct_layout_discovery_shares_one_aggregate_group_budget(tmp_path):
    from company_wiki.source_catalog.models import RouteSpec

    root = RootSpec("mixed-layout", tmp_path / "mixed", "directory",
                    adapter_id="company_raw_v1", reusable_for_filing=True,
                    routes=(RouteSpec(include=("600000/filings/**",), adapter_id="dayu_filing_v1"),))
    original, data = _raw(root.path)
    filing = root.path / "600000" / "filings" / "one"
    filing.mkdir(parents=True)
    (filing / "original.htm").write_bytes(b"<html>actual filing</html>")
    (filing / "meta.json").write_text(json.dumps({"primary_document": "original.htm"}), encoding="utf-8")
    cat = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", (root,)))
    budget = LocalReadBudget(LocalPrepareLimits(max_discovery_groups=1))
    try:
        cat.store
        with pytest.raises(SourceReadError, match="local_source_group_limit"):
            _discover_source_groups(cat, _identity(), budget)
        assert budget.discovery_groups == 2  # second layout does not get a new allowance
        assert original.read_bytes() == data
        assert (filing / "original.htm").read_bytes() == b"<html>actual filing</html>"
    finally:
        cat.close()


def test_route_only_root_drives_real_source_catalog_scan(tmp_path):
    from company_wiki.source_catalog.models import RouteSpec

    root = RootSpec("route-only", tmp_path / "資料 根", "directory",
                    reusable_for_filing=True,
                    routes=(RouteSpec(include=("**/*.txt",), adapter_id="company_raw_v1"),))
    original, data = _raw(root.path)
    cat = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", (root,)))
    try:
        report = cat.scan()
        assert report.errors == 0
        assert dict(report.strategy) == {root.root_id: "adapter"}
        reader = SourceVersionReader(cat)
        result = reader.query_local(SourceRequest(entity="示例 公司", market="CN", security_id="600000",
            document_kind="investor_relations", as_of_date="2026-10-13"))
        assert result.status == "found"
        assert reader.open_version(result.matches[0], purpose="source_export").data == data
        assert original.read_bytes() == data
    finally:
        cat.close()
