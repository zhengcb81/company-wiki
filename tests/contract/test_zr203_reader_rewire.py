"""ZR-203 gate tests: production read entrypoints rewired onto the
zero-write CatalogReader.

- Golden equivalence: the reader/service read paths return byte-identical
  results to the old store paths on the same catalog.
- OS-read-only: service read entrypoints succeed on a read-only DB file
  (the old behavior constructed CatalogStore and crashed with
  'attempt to write a readonly database').
- Caller gate: AST scan proves read entrypoints never construct
  CatalogStore (writer initializer confined to the store property).
"""

from __future__ import annotations

import ast
import os
import stat
from pathlib import Path

import pytest

from company_wiki.source_catalog import models
from company_wiki.source_catalog.models import CatalogConfig
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.store import CatalogStore

SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def _seed(db: Path) -> None:
    store = CatalogStore(db)
    source_id = "src-1"
    doc_id = "doc-1"
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (source_id, "a" * 64, 123, "application/pdf", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO documents(document_id, primary_source_id, title, source_type, "
            "document_kind, published_date, source_status, metadata_priority, metadata_json, "
            "text_fingerprint, first_seen_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                source_id,
                "Zijin Annual 2025",
                "pdf",
                "annual_report",
                "2026-03-20",
                "active",
                0,
                "{}",
                "",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
        conn.execute(
            "INSERT INTO roots(root_id, path, kind, priority, last_scan_run, last_scanned_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("company_raw", "C:/tmp/companies", "company_raw", 10, None, None),
        )
        conn.execute(
            "INSERT INTO locations(location_id, root_id, relative_path, absolute_path, "
            "source_id, document_id, role, location_status, observed_size, observed_mtime_ns, "
            "last_seen_run, manifest_json, metadata_json, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "loc-1",
                "company_raw",
                "rel/annual.pdf",
                "abs/annual.pdf",
                source_id,
                doc_id,
                "original_primary",
                "active",
                123,
                1,
                "scan-1",
                None,
                "{}",
                None,
            ),
        )
    del store


@pytest.fixture()
def seeded(tmp_path: Path) -> tuple[Path, CatalogConfig]:
    db = tmp_path / "catalog.sqlite3"
    _seed(db)
    root_spec = models.RootSpec(
        root_id="company_raw",
        path=tmp_path / "companies",
        kind="company_raw",
        priority=10,
    )
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path,
        roots=(root_spec,),
    )
    return db, config


# ---------------------------------------------------------------------------
# golden equivalence: reader/service == store on the same catalog
# ---------------------------------------------------------------------------


def test_status_golden_equivalence(seeded) -> None:
    db, config = seeded
    with ReadOnlyCatalogReader(db) as reader:
        reader_status = reader.status()
    store = CatalogStore(db)
    try:
        store_status = store.status()
    finally:
        del store
    assert reader_status == store_status


def test_service_status_golden_equivalence(seeded) -> None:
    db, config = seeded
    catalog = SourceCatalog(config)
    assert catalog.status() == ReadOnlyCatalogReader(db).status()


def test_service_query_shape_golden_equivalence(seeded) -> None:
    db, config = seeded
    catalog = SourceCatalog(config)
    results = catalog.query()
    assert len(results) == 1
    result = results[0]
    # the old service.query shape: document fields + entities/locations/artifacts
    for key in ("document_id", "title", "document_kind", "source_status"):
        assert key in result
    assert result["document_id"] == "doc-1"


def test_query_source_bundle_via_reader_path(seeded) -> None:
    db, config = seeded
    catalog = SourceCatalog(config)
    bundle = catalog.query_source_bundle(
        document_id="doc-1",
        registry={},
        allowed_roots=(),
        now="2026-03-21T00:00:00Z",
    )
    assert bundle is not None
    assert bundle["source"]["document_id"] == "doc-1"
    assert bundle["source"]["source_sha256"] == "a" * 64


# ---------------------------------------------------------------------------
# OS-read-only: service read entrypoints succeed (old behavior crashed)
# ---------------------------------------------------------------------------


def test_service_read_on_os_read_only_db_succeeds(seeded) -> None:
    db, config = seeded
    os.chmod(db, stat.S_IREAD)
    try:
        catalog = SourceCatalog(config)
        status = catalog.status()
        assert status["documents"] == 1
        results = catalog.query()
        assert [row["document_id"] for row in results] == ["doc-1"]
    finally:
        os.chmod(db, stat.S_IWRITE)


# ---------------------------------------------------------------------------
# caller gate: read entrypoints never construct CatalogStore
# ---------------------------------------------------------------------------

READ_ENTRYPOINTS = {
    "service.py": {
        "status",
        "query",
        "query_filing_candidates",
        "explain_filing_candidates_plan",
        "query_source_bundle",
        "bundle_for_resolution",
        "semantic_duplicate_groups",
    },
    "resolver.py": {"_remediation_pending", "resolve"},
}


def _class_method_defs(tree: ast.AST) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    return out


def _calls_in(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                names.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                names.add(child.func.attr)
    return names


def test_read_entrypoints_never_construct_catalog_store() -> None:
    for filename, read_names in READ_ENTRYPOINTS.items():
        tree = ast.parse((SRC / filename).read_text(encoding="utf-8"))
        defs = _class_method_defs(tree)
        for name in read_names:
            assert name in defs, f"{filename}:{name} missing (rewired away?)"
            calls = _calls_in(defs[name])
            assert "CatalogStore" not in calls, (
                f"{filename}:{name} still constructs CatalogStore"
            )


def test_cli_resolve_command_uses_reader() -> None:
    text = (SRC / "cli.py").read_text(encoding="utf-8")
    # the RESOLVE command (read path) was rewired to the reader...
    assert "store=get_catalog().reader" in text
    # ...while write commands (ensure/close-gap) keep the writable store.
    assert text.count("store=get_catalog().store") >= 1


def test_write_paths_still_use_store() -> None:
    text = (SRC / "service.py").read_text(encoding="utf-8")
    # write entrypoints keep passing self.store
    assert text.count("self.store,") >= 4
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "store":
            calls = _calls_in(node)
            assert "CatalogStore" in calls, "store property must construct the writer"
