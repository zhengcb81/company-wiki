"""TDD contracts for location ranking and physical availability ownership."""

from __future__ import annotations

import ast
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from company_wiki.source_catalog.location_annotation import (
    CatalogLocationCandidate,
    annotate_locations,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.catalog_query_contract import (
    CatalogDocumentCandidate,
    CatalogDocumentCandidateQuery,
    CatalogQueryUnavailable,
)
from company_wiki.source_catalog.models import SourceCopyAvailability
from company_wiki.source_catalog.models import SourceCopyAvailabilityRequest
from company_wiki.source_catalog.service import SourceCatalog


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki"


def _tree(relative: str) -> ast.Module:
    path = SOURCE_ROOT / relative
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_method(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def test_location_annotations_are_immutable_and_keep_duplicate_semantics():
    first = CatalogLocationCandidate(
        location_id="loc-a",
        source_id="sha256:abc",
        root_id="root-a",
        relative_path="reports/2025.pdf",
        role="original_primary",
        location_status="active",
        root_priority=10,
        manifest_json=None,
    )
    second = CatalogLocationCandidate(
        location_id="loc-b",
        source_id="sha256:abc",
        root_id="root-b",
        relative_path="reports/2025-copy.pdf",
        role="original_primary",
        location_status="active",
        root_priority=20,
        manifest_json=None,
    )

    ranked = annotate_locations("doc-a", (first, second))

    assert isinstance(ranked, tuple)
    assert [item.candidate_rank for item in ranked] == [1, 2]
    assert [item.is_canonical for item in ranked] == [True, False]
    assert ranked[1].duplicate_relation == "exact_copy"
    assert ranked[1].canonical_location_id == "loc-a"
    assert first.relative_path == "reports/2025.pdf"
    with pytest.raises(FrozenInstanceError):
        first.relative_path = "mutated.pdf"


def test_catalog_annotation_api_uses_typed_candidates_and_never_mutates_rows():
    service = _tree("source_catalog/service.py")
    method = _class_method(service, "SourceCatalog", "annotate_locations")
    annotation = ast.unparse(method.args.args[1].annotation)

    assert "CatalogLocationCandidate" in annotation
    assert "dict" not in annotation
    assert "tuple" in ast.unparse(method.returns)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"update", "clear", "pop"}
        for node in ast.walk(method)
    ), "annotation must return values instead of mutating caller-owned rows"


def test_company_source_index_uses_catalog_availability_port_only():
    tree = _tree("source_catalog/company_source_index.py")
    method = _class_method(tree, "CompanySourceIndex", "_copy_state")
    calls = [
        ast.unparse(node.func)
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
    ]

    assert any("catalog.source_copy_availability" in call for call in calls)
    assert not any(
        isinstance(node, ast.Attribute)
        and node.attr in {"reader", "config", "path", "isfile", "is_file"}
        for node in ast.walk(method)
    ), "CompanySourceIndex must not inspect catalog rows or physical paths"

    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"connect", "isfile", "is_file"}
        for node in ast.walk(tree)
    ), "CompanySourceIndex must not open the database or inspect filesystem paths"


def test_company_source_index_uses_catalog_query_port_not_sql_or_reader():
    tree = _tree("source_catalog/company_source_index.py")
    query_methods = {
        name: _class_method(tree, "CompanySourceIndex", name)
        for name in ("_company_known", "_candidate_rows")
    }
    for method_name, method in query_methods.items():
        calls = [
            ast.unparse(node.func)
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
        ]
        assert any("catalog.document_candidates" in call for call in calls), method_name
        assert not any(
            isinstance(node, ast.Attribute)
            and node.attr in {"reader", "fetchall", "fetchone"}
            for node in ast.walk(method)
        ), f"{method_name} must not query catalog storage"

    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module in {"identity_candidates", "reader"}
        for node in ast.walk(tree)
    ), "the company index must use Catalog's query contract"
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
        and node.value.attr == "catalog"
        and node.attr == "config"
        for node in ast.walk(tree)
    ), "catalog configuration must stay behind its public port"


def test_catalog_candidate_query_is_typed_and_pathless():
    assert CatalogDocumentCandidateQuery.__dataclass_params__.frozen
    query = CatalogDocumentCandidateQuery(
        identity_tokens=("entity:acme",),
        limit=10,
        as_of_date="2026-11-11",
        document_kinds=("annual_report",),
        after_document_id=None,
        order="published_date",
    )
    assert query.identity_tokens == ("entity:acme",)
    assert not any(
        field in CatalogDocumentCandidateQuery.__annotations__
        for field in ("path", "absolute_path", "root", "root_spec")
    )


@pytest.mark.parametrize(
    "values",
    [
        {"identity_tokens": ["entity:acme"], "limit": 1},
        {"identity_tokens": ("entity:acme",), "limit": True},
        {
            "identity_tokens": ("entity:acme",),
            "limit": 1,
            "after_document_id": "doc-a",
            "order": "published_date",
        },
    ],
)
def test_catalog_candidate_query_rejects_mutable_or_incoherent_inputs(values):
    with pytest.raises((TypeError, ValueError)):
        CatalogDocumentCandidateQuery(**values)


def test_candidate_metadata_is_deeply_immutable_and_exported_as_a_copy():
    candidate = CatalogDocumentCandidate(
        document_id="doc-a",
        source_id="sha256:abc",
        title="Report",
        document_kind="annual_report",
        published_date="2026-11-01",
        source_status="active",
        metadata={"nested": {"labels": ["one"]}},
        content_sha256="a" * 64,
        byte_size=100,
        mime_type="application/pdf",
        entities=(),
    )

    with pytest.raises(TypeError):
        candidate.metadata["nested"]["new"] = "value"
    assert candidate.metadata["nested"]["labels"] == ("one",)
    exported = candidate.metadata_as_dict()
    exported["nested"]["labels"].append("two")
    assert candidate.metadata["nested"]["labels"] == ("one",)


def test_catalog_candidate_port_returns_typed_results_without_sql_rows():
    service = _tree("source_catalog/service.py")
    method = _class_method(service, "SourceCatalog", "document_candidates")
    assert "CatalogDocumentCandidateQuery" in ast.unparse(method.args.args[1].annotation)
    returned = ast.unparse(method.returns)
    assert "tuple" in returned and "CatalogDocumentCandidate" in returned
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sqlite3"
        and node.attr == "Row"
        for node in ast.walk(method)
    ), "the public result must not expose SQLite row objects"
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CatalogQueryUnavailable"
        for node in ast.walk(method)
    ), "storage exceptions must be translated to the Catalog query contract"


def test_catalog_candidate_port_translates_identity_index_read_failure(monkeypatch):
    from company_wiki.source_catalog import identity_candidates

    catalog = object.__new__(SourceCatalog)
    catalog._reader = object()

    def broken_identity_index(_reader, _tokens):
        raise sqlite3.OperationalError("identity index unavailable")

    monkeypatch.setattr(
        identity_candidates, "identity_candidate_clause", broken_identity_index
    )
    query = CatalogDocumentCandidateQuery(identity_tokens=("entity:acme",), limit=1)

    with pytest.raises(CatalogQueryUnavailable, match="catalog_unavailable"):
        catalog.document_candidates(query)


@pytest.mark.parametrize("bad_mtime", [None, "not-a-time"])
def test_bad_optional_mtime_does_not_block_duplicate_inventory(tmp_path, bad_mtime):
    class DuplicateLocationReader:
        def fetchall(self, sql, _parameters=()):
            if "FROM document_entities" in sql:
                return [{"document_id": "doc-a", "name": "Acme"}]
            return [
                {
                    "location_id": "loc-a",
                    "document_id": "doc-a",
                    "root_id": "root-a",
                    "relative_path": "reports/a.pdf",
                    "absolute_path": "C:/raw/a.pdf",
                    "source_id": "sha256:abc",
                    "role": "original_primary",
                    "location_status": "active",
                    "observed_size": 10,
                    "observed_mtime_ns": 1,
                    "root_priority": 10,
                    "title": "Annual report",
                    "document_kind": "annual_report",
                    "published_date": "2026-01-01",
                    "content_sha256": "a" * 64,
                    "manifest_json": None,
                },
                {
                    "location_id": "loc-b",
                    "document_id": "doc-a",
                    "root_id": "root-b",
                    "relative_path": "reports/b.pdf",
                    "absolute_path": "D:/raw/b.pdf",
                    "source_id": "sha256:abc",
                    "role": "original_primary",
                    "location_status": "active",
                    "observed_size": 10,
                    "observed_mtime_ns": bad_mtime,
                    "root_priority": 20,
                    "title": "Annual report",
                    "document_kind": "annual_report",
                    "published_date": "2026-01-01",
                    "content_sha256": "a" * 64,
                    "manifest_json": None,
                },
            ]

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / "catalog",
            roots=(RootSpec("raw", tmp_path / "raw", "directory"),),
        )
    )
    catalog._reader = DuplicateLocationReader()

    from company_wiki.source_catalog.duplicate_cleanup import DuplicateCleanupService

    inventory = DuplicateCleanupService(catalog).list_groups()

    assert inventory["total_groups"] == 1
    assert inventory["total_reclaimable_copies"] == 1


def test_duplicate_cleanup_uses_a_catalog_owned_typed_inventory_query():
    duplicate_cleanup = _tree("source_catalog/duplicate_cleanup.py")
    assert any(
        isinstance(node, ast.Attribute)
        and node.attr == "duplicate_cleanup_location_records"
        for node in ast.walk(duplicate_cleanup)
    )
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
        and node.value.attr == "catalog"
        and node.attr in {"reader", "config"}
        for node in ast.walk(duplicate_cleanup)
    )

    service = _tree("source_catalog/service.py")
    method = _class_method(service, "SourceCatalog", "duplicate_cleanup_location_records")
    assert "CatalogDuplicateLocationRecord" in ast.unparse(method.returns)


@pytest.mark.parametrize("relative_path", ["../escape.pdf", "C:/outside.pdf"])
def test_invalid_registered_location_does_not_increase_copy_count(tmp_path, relative_path):
    root_path = tmp_path / "raw"
    root_path.mkdir()

    class LocationReader:
        def exact_source_locations(self, _document_id, _source_id):
            return [
                {
                    "location_id": "loc-invalid",
                    "document_id": "doc-a",
                    "source_id": "sha256:abc",
                    "root_id": "raw",
                    "relative_path": relative_path,
                    "role": "original_primary",
                    "location_status": "active",
                    "manifest_json": '{"content_sha256":"' + "a" * 64 + '"}',
                }
            ]

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / "catalog",
            roots=(RootSpec("raw", root_path, "directory"),),
        )
    )
    catalog._reader = LocationReader()

    observed = catalog.source_copy_availability(
        SourceCopyAvailabilityRequest(
            document_id="doc-a",
            source_id="sha256:abc",
            document_kind="annual_report",
            byte_size=100,
            content_sha256="a" * 64,
        )
    )

    assert observed == SourceCopyAvailability(copy_count=0, readable=False)


def test_catalog_availability_port_is_a_pathless_typed_result():
    models = _tree("source_catalog/models.py")
    availability = next(
        node for node in models.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceCopyAvailability"
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dataclass"
        and any(keyword.arg == "frozen" and keyword.value.value is True for keyword in node.keywords)
        for node in availability.decorator_list
    )
    fields = {
        node.target.id
        for node in availability.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert fields == {"copy_count", "readable"}
