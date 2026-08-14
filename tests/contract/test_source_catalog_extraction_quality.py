"""Contracts for deterministic, read-only extraction-quality diagnostics."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sqlite3

import pytest


def _catalog_module():
    return importlib.import_module("company_wiki.source_catalog")


def _quality_module():
    return importlib.import_module("company_wiki.source_catalog.extraction_quality")


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


def _catalog(tmp_path: Path, *, content: str = "Alpha.\n\nBeta.", normalize=True):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    (source_root / "report.txt").write_text(content, encoding="utf-8")
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
    if normalize:
        catalog.normalize()
    row = catalog.store.fetchone(
        "SELECT document_id,primary_source_id FROM documents LIMIT 1"
    )
    return {
        "catalog": catalog,
        "config_path": config_path,
        "source_root": source_root,
        "document_id": row["document_id"],
        "source_id": row["primary_source_id"],
    }


def _pdf_catalog(tmp_path: Path, *, corrupt: bool = False):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    pdf_path = source_root / "report.pdf"
    if corrupt:
        pdf_path.write_bytes(b"not-a-pdf")
    else:
        fitz = pytest.importorskip("fitz")
        document = fitz.open()
        page = document.new_page(width=300, height=300)
        page.insert_text((50, 50), "Trustworthy first page.")
        document.new_page(width=300, height=300)
        document.save(pdf_path)
        document.close()
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("documents", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    row = catalog.store.fetchone(
        "SELECT document_id,primary_source_id FROM documents LIMIT 1"
    )
    return {
        "catalog": catalog,
        "source_root": source_root,
        "document_id": row["document_id"],
        "source_id": row["primary_source_id"],
    }


def test_healthy_report_is_usable_bounded_and_never_returns_span_bodies(tmp_path):
    fixture = _catalog(
        tmp_path,
        content="One.\n\nTwo.\n\nThree.\n\nFour.",
    )
    public = _catalog_module()
    quality = _quality_module()
    service = quality.ExtractionQualityService(fixture["catalog"].config.database_path)

    payload = service.assess(
        document_id=fixture["document_id"], locator_limit=2
    ).to_dict()

    assert public.ExtractionQualityService is quality.ExtractionQualityService
    assert payload["schema_version"] == "1.0.0"
    assert payload["quality_state"] == "usable"
    assert payload["reason_codes"] == []
    assert payload["identity"] == {
        "document_id": fixture["document_id"],
        "source_id": fixture["source_id"],
    }
    assert payload["counts"] == {
        "spans": 4,
        "usable_output_spans": 4,
        "parsed": 4,
        "partial": 0,
        "failed": 0,
        "quarantined": 0,
    }
    assert len(payload["locator_references"]) == 2
    assert payload["locator_references_truncated"] is True
    assert [item["locator"] for item in payload["locator_references"]] == sorted(
        item["locator"] for item in payload["locator_references"]
    )
    encoded = json.dumps(payload, sort_keys=True)
    for forbidden in (
        '"raw_text"',
        '"structured_value"',
        '"absolute_path"',
        '"artifact_path"',
        '"target_price"',
        '"rating"',
    ):
        assert forbidden not in encoded


def test_partial_page_aware_pdf_requires_review_with_exact_reasons(tmp_path):
    fixture = _pdf_catalog(tmp_path)
    quality = _quality_module()

    payload = (
        quality.ExtractionQualityService(fixture["catalog"].config.database_path)
        .assess(source_id=fixture["source_id"])
        .to_dict()
    )

    assert payload["quality_state"] == "review_required"
    assert payload["reason_codes"] == [
        "normalization_partial",
        "failed_evidence",
        "quality_flags_require_review",
    ]
    assert payload["counts"]["usable_output_spans"] >= 1
    assert payload["counts"]["failed"] == 1
    assert "empty_output" in payload["normalization"]["quality_flags"]


@pytest.mark.parametrize(
    ("mode", "expected_reasons"),
    (
        ("pending", ["normalization_pending", "no_usable_evidence"]),
        (
            "unsupported",
            ["normalization_unsupported", "no_usable_evidence"],
        ),
    ),
)
def test_pending_or_unsupported_normalization_is_unavailable(
    tmp_path, mode, expected_reasons
):
    fixture = (
        _catalog(tmp_path, normalize=False)
        if mode == "pending"
        else _pdf_catalog(tmp_path, corrupt=True)
    )
    quality = _quality_module()

    payload = (
        quality.ExtractionQualityService(fixture["catalog"].config.database_path)
        .assess(document_id=fixture["document_id"])
        .to_dict()
    )

    assert payload["quality_state"] == "unavailable"
    assert payload["reason_codes"] == expected_reasons
    assert payload["counts"]["spans"] == 0


def test_quarantined_source_without_active_raw_is_unavailable(tmp_path):
    fixture = _catalog(tmp_path)
    quality = _quality_module()
    with fixture["catalog"].store.transaction() as connection:
        connection.execute(
            "UPDATE documents SET source_status='quarantined' WHERE document_id=?",
            (fixture["document_id"],),
        )
        connection.execute(
            "UPDATE locations SET location_status='missing' WHERE document_id=?",
            (fixture["document_id"],),
        )

    payload = (
        quality.ExtractionQualityService(fixture["catalog"].config.database_path)
        .assess(document_id=fixture["document_id"])
        .to_dict()
    )

    assert payload["quality_state"] == "unavailable"
    assert payload["reason_codes"] == [
        "source_quarantined",
        "no_active_source_location",
    ]
    assert payload["source"]["active_location_count"] == 0


@pytest.mark.parametrize("corruption", ("span_json", "artifact_span_count"))
def test_corrupt_persisted_quality_inputs_fail_integrity(tmp_path, corruption):
    fixture = _catalog(tmp_path)
    quality = _quality_module()
    with fixture["catalog"].store.transaction() as connection:
        if corruption == "span_json":
            connection.execute(
                "UPDATE evidence_spans SET span_json='{}' WHERE document_id=?",
                (fixture["document_id"],),
            )
        else:
            row = connection.execute(
                "SELECT artifact_id,metadata_json FROM artifacts "
                "WHERE document_id=? AND artifact_role='normalized'",
                (fixture["document_id"],),
            ).fetchone()
            metadata = json.loads(row["metadata_json"])
            metadata["span_count"] += 1
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (json.dumps(metadata, sort_keys=True), row["artifact_id"]),
            )

    with pytest.raises(quality.ExtractionQualityIntegrityError):
        quality.ExtractionQualityService(
            fixture["catalog"].config.database_path
        ).assess(document_id=fixture["document_id"])


def test_invalid_unknown_and_ambiguous_identity_fail_closed(tmp_path):
    fixture = _catalog(tmp_path)
    quality = _quality_module()
    service = quality.ExtractionQualityService(fixture["catalog"].config.database_path)

    with pytest.raises(quality.ExtractionQualityInputError, match="exactly one"):
        service.assess()
    with pytest.raises(quality.ExtractionQualityInputError, match="exactly one"):
        service.assess(
            source_id=fixture["source_id"], document_id=fixture["document_id"]
        )
    with pytest.raises(quality.ExtractionQualityInputError, match="locator_limit"):
        service.assess(document_id=fixture["document_id"], locator_limit=0)
    with pytest.raises(quality.ExtractionQualityNotFoundError):
        service.assess(document_id="urn:company-wiki:document:sha256:" + "0" * 64)

    duplicate_document_id = "urn:company-wiki:document:sha256:" + "f" * 64
    with fixture["catalog"].store.transaction() as connection:
        source = connection.execute(
            "SELECT * FROM documents WHERE document_id=?",
            (fixture["document_id"],),
        ).fetchone()
        connection.execute(
            """INSERT INTO documents(document_id,primary_source_id,title,source_type,
            document_kind,published_date,source_status,metadata_priority,metadata_json,
            first_seen_at,last_seen_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
            (
                duplicate_document_id,
                fixture["source_id"],
                "Duplicate identity fixture",
                source["source_type"],
                source["document_kind"],
                None,
                "active",
                0,
                "{}",
            ),
        )
    with pytest.raises(quality.ExtractionQualityAmbiguousError):
        service.assess(source_id=fixture["source_id"])


def test_assessment_uses_mode_ro_no_write_sql_and_preserves_file_trees(
    tmp_path, monkeypatch
):
    fixture = _catalog(tmp_path)
    quality = _quality_module()
    before_catalog = _tree_identity(fixture["catalog"].config.catalog_dir)
    before_sources = _tree_identity(fixture["source_root"])
    connections: list[str] = []
    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connections.append(str(database))
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(quality.sqlite3, "connect", traced_connect)
    quality.ExtractionQualityService(fixture["catalog"].config.database_path).assess(
        document_id=fixture["document_id"]
    )

    assert connections and all("mode=ro" in value for value in connections)
    assert not any(
        statement.lstrip()
        .upper()
        .startswith(
            ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")
        )
        for statement in statements
    )
    assert _tree_identity(fixture["catalog"].config.catalog_dir) == before_catalog
    assert _tree_identity(fixture["source_root"]) == before_sources


def test_assessment_read_connection_uses_long_busy_timeout(tmp_path, monkeypatch):
    """The read-only connection must tolerate the worker's write bursts: the
    busy_timeout matches the main store read connection (30s), not a shorter
    legacy 5s value that surfaced as spurious 'database is locked' during the
    ADR-008 portfolio E2E (worker write burst vs read-only query)."""
    fixture = _catalog(tmp_path)
    quality = _quality_module()
    statements: list[str] = []
    real_connect = sqlite3.connect

    def traced_connect(database, *args, **kwargs):
        connection = real_connect(database, *args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(quality.sqlite3, "connect", traced_connect)
    quality.ExtractionQualityService(fixture["catalog"].config.database_path).assess(
        document_id=fixture["document_id"]
    )

    assert any("busy_timeout=30000" in s for s in statements)


def test_extraction_quality_cli_emits_machine_readable_body_free_result(
    tmp_path, capsys
):
    fixture = _catalog(tmp_path)
    from company_wiki.source_catalog.cli import main

    assert (
        main(
            [
                "--config",
                str(fixture["config_path"]),
                "extraction-quality",
                "--document-id",
                fixture["document_id"],
                "--locator-limit",
                "1",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["quality_state"] == "usable"
    assert len(payload["locator_references"]) == 1
    assert "raw_text" not in json.dumps(payload)


def test_extraction_quality_cli_missing_database_does_not_initialize_catalog(
    tmp_path, capsys
):
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
    from company_wiki.source_catalog.cli import main

    result = main(
        [
            "--config",
            str(config_path),
            "extraction-quality",
            "--document-id",
            "urn:company-wiki:document:sha256:" + "0" * 64,
        ]
    )

    assert result == 1
    assert json.loads(capsys.readouterr().err)["error_type"] == ("fatal")
    assert not (project / ".source_catalog").exists()


def test_extraction_quality_contract_documents_source_only_boundary():
    root = Path(__file__).resolve().parents[2]
    contract = (root / "docs" / "contracts" / "extraction-quality-v1.md").read_text(
        encoding="utf-8"
    )
    operations = (root / "docs" / "source-catalog.md").read_text(encoding="utf-8")

    for phrase in (
        "usable",
        "review_required",
        "unavailable",
        "source/extraction quality only",
        "mode=ro",
        "raw_text",
        "locator references",
    ):
        assert phrase in contract
    assert "extraction-quality" in operations
    assert "不包含投资结论" in operations
