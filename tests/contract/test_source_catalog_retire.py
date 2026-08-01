"""Phase 15.5: CLI retire command — soft delete with audit, no physical
deletion; retired documents are excluded from query/resolver results."""

from __future__ import annotations

import json
from pathlib import Path


def _catalog(tmp_path: Path):
    """A project with one scanned document and a usable CLI config."""
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog

    project = tmp_path / "project"
    company = project / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    company.mkdir(parents=True)
    (company / "2026-02-20_Acme_2025_annual_report.txt").write_text(
        "ACME FY2025 audited annual report.", encoding="utf-8"
    )
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(project / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                "    path: '" + str(project / "companies").replace("\\", "/") + "'",
                "    priority: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    config = load_catalog_config(config_path, project_root=project)
    catalog = SourceCatalog(config)
    catalog.scan()
    return project, config_path, catalog


def test_cli_retire_document_soft_deletes_with_audit(tmp_path, capsys):
    """`documents retire` must turn the document and its locations into
    retired (soft delete, nothing physically removed) and write an audit row
    with reason/created_by (Phase 15.5)."""
    from company_wiki.source_catalog.cli import main

    project, config_path, catalog = _catalog(tmp_path)
    document_id = catalog.query(limit=1)[0]["document_id"]

    rc = main(
        [
            "--config",
            str(config_path),
            "documents",
            "retire",
            "--document-id",
            document_id,
            "--reason",
            "placeholder-cleanup",
            "--created-by",
            "phase-15.5-test",
        ]
    )

    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert output["document_id"] == document_id
    assert output["source_status"] == "retired"

    # default query excludes retired documents
    assert catalog.query(limit=10) == []
    # explicit source_status=retired still sees it
    retired = catalog.query(limit=10, source_status="retired")
    assert len(retired) == 1
    assert retired[0]["document_id"] == document_id
    assert retired[0]["source_status"] == "retired"
    # locations are retired too
    assert all(
        location["location_status"] == "retired" for location in retired[0]["locations"]
    )
    # audit row exists with reason and actor
    audit = catalog.store.fetchall(
        "SELECT * FROM document_retire_audit WHERE document_id=?", (document_id,)
    )
    assert len(audit) == 1
    assert audit[0]["reason"] == "placeholder-cleanup"
    assert audit[0]["created_by"] == "phase-15.5-test"


def test_cli_retire_unknown_document_fails_without_partial_writes(tmp_path, capsys):
    from company_wiki.source_catalog.cli import main

    project, config_path, catalog = _catalog(tmp_path)

    rc = main(
        [
            "--config",
            str(config_path),
            "documents",
            "retire",
            "--document-id",
            "urn:company-wiki:document:sha256:" + "f" * 64,
            "--reason",
            "cleanup",
        ]
    )

    assert rc != 0
    assert catalog.query(limit=10) != []


def test_scan_does_not_revive_retired_document(tmp_path):
    """A retired document must stay retired across rescans even when its file
    is still on disk: retirement is a terminal state until the user acts
    (Phase 15.6 batch governance)."""
    from company_wiki.source_catalog.cli import main
    from company_wiki.source_catalog.service import SourceCatalog

    project, config_path, catalog = _catalog(tmp_path)
    document_id = catalog.query(limit=1)[0]["document_id"]
    main(
        [
            "--config",
            str(config_path),
            "documents",
            "retire",
            "--document-id",
            document_id,
            "--reason",
            "test-terminal-state",
        ]
    )

    # file is still on disk; a rescan must NOT reactivate the document
    catalog.scan()

    remaining = catalog.query(limit=10, source_status="retired")
    assert len(remaining) == 1
    assert remaining[0]["document_id"] == document_id
    assert remaining[0]["source_status"] == "retired"
    # locations of a retired document stay retired too (no partial state)
    assert all(
        location["location_status"] == "retired"
        for location in remaining[0]["locations"]
    )
    assert catalog.query(limit=10) == []


def test_resolver_never_reuses_retired_document(tmp_path):
    """A retired document must never be reused by the resolver (Phase 15.5)."""
    from company_wiki.source_catalog.cli import main
    from company_wiki.source_catalog.resolver import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    project, config_path, catalog = _catalog(tmp_path)
    document_id = catalog.query(limit=1)[0]["document_id"]
    main(
        [
            "--config",
            str(config_path),
            "documents",
            "retire",
            "--document-id",
            document_id,
            "--reason",
            "cleanup",
        ]
    )

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Acme",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
    )

    assert result.status is ResolutionStatus.MISSING
    assert result.reason == "no_existing_source_satisfies_request"
