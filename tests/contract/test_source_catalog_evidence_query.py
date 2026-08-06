"""Contracts for exact, read-only source-catalog EvidenceSpan queries."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest


def _catalog_module():
    return importlib.import_module("company_wiki.source_catalog")


def _query_module():
    return importlib.import_module("company_wiki.source_catalog.evidence_query")


def _tree_identity(root: Path) -> tuple[tuple[str, int, int, str], ...]:
    if not root.exists():
        return ()
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        stat = path.stat()
        rows.append(
            (
                path.relative_to(root).as_posix(),
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return tuple(rows)


def _draw_table_page(page: Any) -> None:
    page.insert_text((50, 25), "Narrative before table")
    page.insert_text((50, 190), "Narrative after table")
    for x in (50, 150, 250):
        page.draw_line((x, 50), (x, 150))
    for y in (50, 100, 150):
        page.draw_line((50, y), (250, y))
    for point, value in (
        ((65, 80), "A"),
        ((165, 80), "B"),
        ((65, 130), "1"),
        ((165, 130), "2"),
    ):
        page.insert_text(point, value)


@pytest.fixture
def evidence_catalog(tmp_path):
    module = _catalog_module()
    fitz = pytest.importorskip("fitz")
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    pdf_path = source_root / "report.pdf"
    document = fitz.open()
    _draw_table_page(document.new_page(width=300, height=300))
    document.new_page(width=300, height=300)
    document.save(pdf_path)
    document.close()
    (source_root / "report-copy.pdf").write_bytes(pdf_path.read_bytes())
    (source_root / "other.txt").write_text("Other source paragraph.", encoding="utf-8")
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
schema_version: '1.0'
catalog_dir: '${{PROJECT_ROOT}}/.source_catalog'
roots:
  - root_id: documents
    kind: directory
    path: '{source_root.as_posix()}'
""".strip(),
        encoding="utf-8",
    )
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("documents", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    main = catalog.store.fetchone(
        "SELECT source_id,document_id FROM evidence_spans "
        "WHERE table_index IS NOT NULL LIMIT 1"
    )
    other = catalog.store.fetchone(
        "SELECT primary_source_id FROM documents WHERE document_id<>? "
        "AND primary_source_id IS NOT NULL LIMIT 1",
        (main["document_id"],),
    )
    spans = [
        json.loads(row["span_json"])
        for row in catalog.store.fetchall(
            "SELECT span_json FROM evidence_spans WHERE source_id=? ORDER BY locator",
            (main["source_id"],),
        )
    ]
    return {
        "catalog": catalog,
        "config_path": config_path,
        "source_root": source_root,
        "source_id": main["source_id"],
        "document_id": main["document_id"],
        "other_source_id": other["primary_source_id"],
        "spans": spans,
    }


def _span_by_kind(fixture: dict[str, Any], kind: str) -> dict[str, Any]:
    for span in fixture["spans"]:
        coordinates = span["coordinates"]
        if kind == "paragraph" and coordinates["paragraph_index"] is not None:
            return span
        if kind == "table" and coordinates["table_index"] is not None:
            return span
        if (
            kind == "empty"
            and coordinates["page_number"] == 2
            and coordinates["paragraph_index"] is None
            and coordinates["table_index"] is None
        ):
            return span
    raise AssertionError(f"missing {kind} fixture span")


def test_exact_lookup_returns_validated_span_document_source_and_locations(
    evidence_catalog,
):
    public = _catalog_module()
    query = _query_module()
    service = query.EvidenceQueryService(
        evidence_catalog["catalog"].config.database_path
    )

    assert public.EvidenceQueryService is query.EvidenceQueryService
    for kind in ("paragraph", "table", "empty"):
        expected = _span_by_kind(evidence_catalog, kind)
        payload = service.lookup(
            source_id=evidence_catalog["source_id"],
            locator=expected["locator"],
        ).to_dict()
        assert payload["schema_version"] == "1.0.0"
        assert payload["span"] == expected
        assert payload["source"] == {
            "source_id": evidence_catalog["source_id"],
            "content_sha256": evidence_catalog["source_id"].rsplit(":", 1)[-1],
            "byte_size": payload["source"]["byte_size"],
            "mime_type": "application/pdf",
        }
        assert payload["document"]["document_id"] == evidence_catalog["document_id"]
        assert len(payload["locations"]) == 2
        assert {item["location_status"] for item in payload["locations"]} == {"active"}
        assert {Path(item["absolute_path"]).name for item in payload["locations"]} == {
            "report.pdf",
            "report-copy.pdf",
        }
        assert "artifacts" not in payload
        assert "summary" not in payload


def test_list_spans_is_stable_bounded_and_supports_exact_source_or_document(
    evidence_catalog,
):
    query = _query_module()
    service = query.EvidenceQueryService(
        evidence_catalog["catalog"].config.database_path
    )

    first = service.list_spans(
        source_id=evidence_catalog["source_id"], limit=3, offset=0
    ).to_dict()
    second = service.list_spans(
        source_id=evidence_catalog["source_id"], limit=3, offset=3
    ).to_dict()
    by_document = service.list_spans(
        document_id=evidence_catalog["document_id"], limit=100, offset=0
    ).to_dict()

    expected_locators = sorted(item["locator"] for item in evidence_catalog["spans"])
    assert first["total"] == len(expected_locators) == 7
    assert first["limit"] == 3 and first["offset"] == 0
    assert len(first["items"]) == 3
    combined = first["items"] + second["items"] + by_document["items"][6:]
    assert [item["span"]["locator"] for item in combined] == expected_locators
    assert [item["span"]["locator"] for item in by_document["items"]] == (
        expected_locators
    )


def test_invalid_unknown_and_source_locator_mismatch_fail_closed(evidence_catalog):
    query = _query_module()
    service = query.EvidenceQueryService(
        evidence_catalog["catalog"].config.database_path
    )
    valid_locator = _span_by_kind(evidence_catalog, "table")["locator"]

    with pytest.raises(query.EvidenceQueryInputError, match="source_id"):
        service.lookup(source_id="not-a-source", locator=valid_locator)
    with pytest.raises(query.EvidenceQueryInputError, match="locator"):
        service.lookup(
            source_id=evidence_catalog["source_id"],
            locator="loc:v1/paragraph:0/page:1",
        )
    with pytest.raises(query.EvidenceQueryNotFoundError):
        service.lookup(
            source_id="urn:company-wiki:source:sha256:" + "0" * 64,
            locator=valid_locator,
        )
    with pytest.raises(query.EvidenceQueryNotFoundError):
        service.lookup(
            source_id=evidence_catalog["other_source_id"],
            locator=valid_locator,
        )
    with pytest.raises(query.EvidenceQueryInputError, match="exactly one"):
        service.list_spans(
            source_id=evidence_catalog["source_id"],
            document_id=evidence_catalog["document_id"],
        )
    with pytest.raises(query.EvidenceQueryInputError, match="limit"):
        service.list_spans(source_id=evidence_catalog["source_id"], limit=0)


def test_missing_database_is_unavailable_without_creating_parent(tmp_path):
    query = _query_module()
    database = tmp_path / "missing" / "catalog.sqlite3"
    service = query.EvidenceQueryService(database)

    with pytest.raises(query.EvidenceQueryUnavailableError):
        service.lookup(
            source_id="urn:company-wiki:source:sha256:" + "0" * 64,
            locator="loc:v1/page:1",
        )

    assert not database.parent.exists()


def test_corrupt_persisted_span_fails_integrity_validation(evidence_catalog):
    query = _query_module()
    catalog = evidence_catalog["catalog"]
    target = _span_by_kind(evidence_catalog, "paragraph")
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE evidence_spans SET span_json='{}' WHERE span_id=?",
            (target["span_id"],),
        )
    service = query.EvidenceQueryService(catalog.config.database_path)

    with pytest.raises(query.EvidenceQueryIntegrityError, match="span"):
        service.lookup(
            source_id=evidence_catalog["source_id"],
            locator=target["locator"],
        )


def test_runtime_queries_use_read_only_sql_and_leave_database_and_sources_unchanged(
    evidence_catalog, monkeypatch
):
    query = _query_module()
    catalog = evidence_catalog["catalog"]
    before_database = _tree_identity(catalog.config.catalog_dir)
    before_sources = _tree_identity(evidence_catalog["source_root"])
    connections: list[str] = []
    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connections.append(str(database))
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(query.sqlite3, "connect", traced_connect)
    service = query.EvidenceQueryService(catalog.config.database_path)
    target = _span_by_kind(evidence_catalog, "paragraph")

    service.lookup(source_id=evidence_catalog["source_id"], locator=target["locator"])
    service.list_spans(source_id=evidence_catalog["source_id"], limit=2)

    assert connections and all("mode=ro" in value for value in connections)
    assert not any(
        statement.lstrip()
        .upper()
        .startswith(
            ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")
        )
        for statement in statements
    )
    assert _tree_identity(catalog.config.catalog_dir) == before_database
    assert _tree_identity(evidence_catalog["source_root"]) == before_sources


def test_runtime_queries_use_long_busy_timeout_read_connection(
    evidence_catalog, monkeypatch
):
    """The read-only EvidenceSpan connection must tolerate worker write
    bursts: its busy_timeout matches the main store read connection (30s),
    not a shorter legacy 5s value that surfaced as spurious 'database is
    locked' during the ADR-008 portfolio E2E."""
    query = _query_module()
    catalog = evidence_catalog["catalog"]
    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(query.sqlite3, "connect", traced_connect)
    service = query.EvidenceQueryService(catalog.config.database_path)
    target = _span_by_kind(evidence_catalog, "paragraph")

    service.lookup(source_id=evidence_catalog["source_id"], locator=target["locator"])

    assert any("busy_timeout=30000" in s for s in statements)


def test_evidence_cli_lookup_and_list_emit_machine_readable_results(
    evidence_catalog, capsys
):
    from company_wiki.source_catalog.cli import main

    target = _span_by_kind(evidence_catalog, "table")
    common = ["--config", str(evidence_catalog["config_path"])]

    assert (
        main(
            common
            + [
                "evidence",
                "--source-id",
                evidence_catalog["source_id"],
                "--locator",
                target["locator"],
            ]
        )
        == 0
    )
    lookup = json.loads(capsys.readouterr().out)
    assert lookup["span"]["span_id"] == target["span_id"]
    assert (
        main(
            common
            + [
                "evidence-list",
                "--source-id",
                evidence_catalog["source_id"],
                "--limit",
                "2",
            ]
        )
        == 0
    )
    listed = json.loads(capsys.readouterr().out)
    assert listed["total"] == 7
    assert len(listed["items"]) == 2


def test_evidence_cli_missing_database_fails_without_initializing_catalog(
    tmp_path, capsys
):
    from company_wiki.source_catalog.cli import main

    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
schema_version: '1.0'
catalog_dir: '${{PROJECT_ROOT}}/.source_catalog'
roots:
  - root_id: documents
    kind: directory
    path: '{source_root.as_posix()}'
""".strip(),
        encoding="utf-8",
    )

    result = main(
        [
            "--config",
            str(config_path),
            "evidence",
            "--source-id",
            "urn:company-wiki:source:sha256:" + "0" * 64,
            "--locator",
            "loc:v1/page:1",
        ]
    )

    assert result == 1
    error = json.loads(capsys.readouterr().err)
    assert error["error_type"] == "EvidenceQueryUnavailableError"
    assert not (project / ".source_catalog").exists()


def test_evidence_query_contract_documents_exact_read_only_boundary():
    root = Path(__file__).resolve().parents[2]
    contract = (root / "docs" / "contracts" / "evidence-query-v1.md").read_text(
        encoding="utf-8"
    )
    operations = (root / "docs" / "source-catalog.md").read_text(encoding="utf-8")

    for phrase in (
        "source_id",
        "locator",
        "EvidenceSpan.from_dict()",
        "mode=ro",
        "immutable=1",
        "fails unavailable",
    ):
        assert phrase in contract
    assert "evidence-list" in operations
    assert "不做模糊匹配" in operations
