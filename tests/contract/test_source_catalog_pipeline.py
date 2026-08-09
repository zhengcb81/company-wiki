"""Contracts for the multi-root, source-only document catalog."""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3

import pytest


def _catalog_module():
    return importlib.import_module("company_wiki.source_catalog")


def _snapshot(root: Path) -> tuple[tuple[str, int, int, str], ...]:
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


def _write_dayu_filing(portfolio: Path) -> Path:
    filing = portfolio / "ACME" / "filings" / "fil_0001"
    filing.mkdir(parents=True)
    primary = filing / "annual.htm"
    primary.write_text(
        "<html><body><h1>ACME Annual Report</h1><p>Revenue was 100.</p></body></html>",
        encoding="utf-8",
    )
    attachment = filing / "facts.xml"
    attachment.write_text("<facts><revenue>100</revenue></facts>", encoding="utf-8")
    meta = {
        "ticker": "ACME",
        "document_id": "fil_0001",
        "source_title": "ACME 2025 Annual Report",
        "form_type": "10-K",
        "filing_date": "2026-02-20",
        "fiscal_year": 2025,
        "primary_document": "annual.htm",
        "selected_primary_document": "annual.htm",
        "ingest_complete": True,
        "source_url": "https://example.invalid/acme/fil_0001",
        "files": [
            {"name": "annual.htm", "source": "original"},
            {"name": "facts.xml", "source": "original"},
        ],
    }
    (filing / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    return primary


def _config(module, *, project: Path, company: Path, dropbox: Path, portfolio: Path):
    return module.CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(
            module.RootSpec("company_raw", company, "company_raw", priority=10),
            module.RootSpec("dropbox_stock", dropbox, "directory", priority=30),
            module.RootSpec("dayu_portfolio", portfolio, "dayu_portfolio", priority=20),
        ),
    )


def test_scan_deduplicates_content_but_preserves_every_location_and_dayu_bundle(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    company = project / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    portfolio = tmp_path / "dayu" / "portfolio"
    company_file = company / "Acme" / "raw" / "reports" / "2025 annual.txt"
    company_file.parent.mkdir(parents=True)
    company_file.write_text("ACME annual source text. Revenue was 100.", encoding="utf-8")
    dropbox.mkdir(parents=True)
    (dropbox / "Acme duplicate.txt").write_bytes(company_file.read_bytes())
    (dropbox / "tool.py").write_text("raise SystemExit", encoding="utf-8")
    _write_dayu_filing(portfolio)
    before = (_snapshot(company), _snapshot(dropbox), _snapshot(portfolio))

    catalog = module.SourceCatalog(
        _config(
            module,
            project=project,
            company=company,
            dropbox=dropbox,
            portfolio=portfolio,
        )
    )
    report = catalog.scan()
    status = catalog.status()

    assert report.files_seen == 5
    assert report.locations_active == 5
    assert report.files_excluded == 1
    assert status["sources"] == 4
    assert status["documents"] == 2
    assert status["active_locations"] == 5
    duplicate = catalog.query(text="Acme", limit=20)
    annual = [row for row in duplicate if row["title"] == "2025 annual"]
    assert len(annual) == 1
    assert len(annual[0]["locations"]) == 2
    dayu = [row for row in duplicate if row["title"] == "ACME 2025 Annual Report"]
    assert dayu[0]["document_kind"] == "annual_report"
    assert dayu[0]["source_status"] == "active"
    assert {item["role"] for item in dayu[0]["locations"]} == {
        "original_primary",
        "original_attachment",
        "metadata",
    }
    assert (_snapshot(company), _snapshot(dropbox), _snapshot(portfolio)) == before


def test_repeated_empty_source_is_a_known_quarantine_and_recovers(tmp_path):
    from company_wiki.source_catalog.store import read_pipeline_status

    module = _catalog_module()
    project = tmp_path / "project"
    company = project / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    portfolio = tmp_path / "dayu" / "portfolio"
    company.mkdir(parents=True)
    dropbox.mkdir(parents=True)
    portfolio.mkdir(parents=True)
    source = dropbox / "医疗器械选股20250622" / "data" / "Product_Revenue_Forecast_Model.xlsx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"")
    catalog = module.SourceCatalog(
        _config(
            module,
            project=project,
            company=company,
            dropbox=dropbox,
            portfolio=portfolio,
        )
    )

    first = catalog.scan()
    second = catalog.scan()
    pipeline = read_pipeline_status(catalog.config.database_path)

    assert first.errors == 1
    assert first.new_errors == 1
    assert first.known_quarantined == 0
    assert second.errors == 1
    assert second.new_errors == 0
    assert second.known_quarantined == 1
    assert second.error_details == (
        {
            "root_id": "dropbox_stock",
            "relative_path": "医疗器械选股20250622/data/Product_Revenue_Forecast_Model.xlsx",
            "error": "SourceManifestError: source file is empty",
            "unchanged": True,
        },
    )
    assert pipeline["markdown"]["blocked"] == 1
    assert pipeline["markdown"]["blocked_quarantined"] == 1
    assert pipeline["markdown"]["blocked_incomplete"] == 0
    assert pipeline["markdown"]["blocked_other"] == 0
    assert pipeline["last_scan"]["new_errors"] == 0
    assert pipeline["last_scan"]["known_quarantined"] == 1

    with catalog.store.transaction() as connection:
        latest = connection.execute(
            "SELECT run_id,report_json FROM scan_runs ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        legacy_report = json.loads(latest["report_json"])
        for field in ("new_errors", "known_quarantined", "error_details"):
            legacy_report.pop(field)
        connection.execute(
            "UPDATE scan_runs SET report_json=? WHERE run_id=?",
            (json.dumps(legacy_report), latest["run_id"]),
        )
    legacy_pipeline = read_pipeline_status(catalog.config.database_path)
    assert legacy_pipeline["last_scan"]["new_errors"] is None
    assert legacy_pipeline["last_scan"]["known_quarantined"] is None
    assert legacy_pipeline["last_scan"]["error_details"] == [
        {
            "root_id": "dropbox_stock",
            "relative_path": "医疗器械选股20250622/data/Product_Revenue_Forecast_Model.xlsx",
            "error": "SourceManifestError: source file is empty",
            "unchanged": None,
        }
    ]

    source.write_bytes(b"valid workbook placeholder")
    recovered = catalog.scan()
    recovered_pipeline = read_pipeline_status(catalog.config.database_path)

    assert recovered.errors == 0
    assert recovered.new_errors == 0
    assert recovered.known_quarantined == 0
    assert recovered_pipeline["markdown"]["blocked"] == 0
    assert recovered_pipeline["markdown"]["blocked_quarantined"] == 0


def test_exact_duplicate_index_marks_canonical_and_extra_original_locations(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    company = project / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    portfolio = tmp_path / "dayu" / "portfolio"
    company_file = company / "Acme" / "raw" / "financial_reports" / "annual" / "2025 annual.txt"
    company_file.parent.mkdir(parents=True)
    company_file.write_text("ACME FY2025 audited annual report.", encoding="utf-8")
    dropbox.mkdir(parents=True)
    duplicate_file = dropbox / "renamed-by-another-downloader.txt"
    duplicate_file.write_bytes(company_file.read_bytes())
    portfolio.mkdir(parents=True)
    before = (_snapshot(company), _snapshot(dropbox), _snapshot(portfolio))
    catalog = module.SourceCatalog(
        _config(
            module,
            project=project,
            company=company,
            dropbox=dropbox,
            portfolio=portfolio,
        )
    )

    catalog.scan()

    document = catalog.query(text="2025 annual", limit=10)[0]
    assert document["duplicate_status"] == "exact_copy"
    assert document["exact_original_copy_count"] == 2
    assert document["exact_duplicate_location_count"] == 1
    assert document["exact_duplicate_group_id"].startswith(
        "urn:company-wiki:duplicate:exact:sha256:"
    )
    original_locations = [
        item for item in document["locations"] if item["role"] == "original_primary"
    ]
    canonical = [item for item in original_locations if item["is_canonical"]]
    copies = [item for item in original_locations if item["duplicate_relation"] == "exact_copy"]
    assert len(canonical) == 1
    assert canonical[0]["root_id"] == "company_raw"
    assert canonical[0]["canonical_location_id"] == canonical[0]["location_id"]
    assert len(copies) == 1
    assert copies[0]["root_id"] == "dropbox_stock"
    assert copies[0]["canonical_location_id"] == canonical[0]["location_id"]

    groups = catalog.duplicate_groups()
    assert groups == [
        {
            "duplicate_group_id": document["exact_duplicate_group_id"],
            "relation_type": "exact_copy",
            "document_id": document["document_id"],
            "source_id": document["source_id"],
            "canonical_location_id": canonical[0]["location_id"],
            "canonical_path": canonical[0]["absolute_path"],
            "exact_original_copy_count": 2,
            "exact_duplicate_location_count": 1,
            "duplicate_location_ids": copies[0]["location_id"],
            "duplicate_paths": copies[0]["absolute_path"],
            "match_basis": "document_id+source_id+sha256",
            "confidence": 1.0,
        }
    ]

    export_progress = []
    exported = catalog.export_indexes(
        progress=lambda **details: export_progress.append(details)
    )
    assert [item["current"] for item in export_progress] == list(range(1, 13))
    assert all(item["total"] == 12 for item in export_progress)
    assert [item["detail"] for item in export_progress[:5]] == [
        "loading catalog documents",
        "building exact duplicate groups",
        "building semantic duplicate groups",
        "loading export journals",
        "building export rows",
    ]
    assert exported["locations_csv"].is_file()
    assert exported["duplicates_csv"].is_file()
    with exported["documents_csv"].open(encoding="utf-8-sig", newline="") as stream:
        document_rows = list(csv.DictReader(stream))
    assert document_rows[0]["duplicate_status"] == "exact_copy"
    assert document_rows[0]["exact_original_copy_count"] == "2"
    with exported["locations_csv"].open(encoding="utf-8-sig", newline="") as stream:
        location_rows = list(csv.DictReader(stream))
    assert {row["duplicate_relation"] for row in location_rows} == {"", "exact_copy"}
    with exported["duplicates_csv"].open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 1
    assert "Exact duplicate groups: 1" in exported["index_md"].read_text(encoding="utf-8")
    assert (_snapshot(company), _snapshot(dropbox), _snapshot(portfolio)) == before


def test_shared_sidecar_blob_is_not_an_exact_document_duplicate(tmp_path):
    """Metadata-only bundles (only meta.json, no preferred file) are not
    indexed at all (Phase 15.4), so identical sidecar blobs can never become
    exact document duplicates."""
    module = _catalog_module()
    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    first = portfolio / "ACME" / "filings" / "fil_one"
    second = portfolio / "BETA" / "filings" / "fil_two"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    for directory in (first, second):
        (directory / "meta.json").write_text("{}", encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("dayu", portfolio, "dayu_portfolio"),),
        )
    )

    catalog.scan()

    assert catalog.status()["sources"] == 0
    assert catalog.status()["documents"] == 0
    assert catalog.duplicate_groups() == []


def test_scan_is_idempotent_and_tombstones_missing_locations_without_deleting_sources(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "report.txt"
    source.write_text("Immutable report body.", encoding="utf-8")
    config = module.CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(module.RootSpec("external", source_root, "directory"),),
    )
    catalog = module.SourceCatalog(config)

    first = catalog.scan()
    with catalog.store.transaction() as connection:
        connection.execute(
            "INSERT INTO scan_runs(run_id,started_at,status) VALUES('stale-run','2026-01-01T00:00:00Z','running')"
        )
    second = catalog.scan()
    assert second.files_hashed == 0
    assert second.files_reused == 1
    assert catalog.status()["sources"] == 1
    assert first.locations_active == second.locations_active == 1
    assert catalog.store.fetchone(
        "SELECT status FROM scan_runs WHERE run_id='stale-run'"
    )["status"] == "interrupted"

    source.unlink()
    third = catalog.scan()
    status = catalog.status()
    assert third.locations_missing == 1
    assert status["sources"] == 1
    assert status["active_locations"] == 0
    assert status["missing_locations"] == 1


def test_scan_run_is_committed_before_enumeration_progress(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "report.txt").write_text("source evidence", encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    visible_runs = []

    def observe_progress(**details):
        if details["detail"] != "enumerating root external" or visible_runs:
            return
        with sqlite3.connect(catalog.config.database_path) as connection:
            visible_runs.extend(
                connection.execute(
                    "SELECT run_id,status FROM scan_runs WHERE status='running'"
                ).fetchall()
            )

    report = catalog.scan(progress=observe_progress)

    assert visible_runs == [(report.run_id, "running")]


def test_enumeration_exception_persists_an_interrupted_scan_run(tmp_path, monkeypatch):
    module = _catalog_module()
    import company_wiki.source_catalog.scanner as scanner

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )

    def fail_enumeration(*_args, **_kwargs):
        raise RuntimeError("enumeration fixture failure")

    monkeypatch.setattr(scanner, "_scan_root_v1", fail_enumeration)

    with pytest.raises(RuntimeError, match="enumeration fixture failure"):
        catalog.scan()

    run = catalog.store.fetchone(
        "SELECT status,completed_at FROM scan_runs ORDER BY started_at DESC LIMIT 1"
    )
    assert run is not None
    assert run["status"] == "interrupted"
    assert run["completed_at"]


def test_normalize_summarize_and_export_index_every_original_and_derived_artifact(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    text_path = source_root / "brief.txt"
    text_path.write_text(
        "First material fact about operations.\n\nSecond source fact about customers.",
        encoding="utf-8",
    )
    html_path = source_root / "meeting.html"
    html_path.write_text(
        "<html><body><h1>Investor Meeting</h1><p>Management discussed capacity.</p></body></html>",
        encoding="utf-8",
    )
    before = _snapshot(source_root)
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )

    catalog.scan()
    normalized = catalog.normalize()
    summarized = catalog.summarize()
    exported = catalog.export_indexes()

    assert normalized.completed == 2
    assert summarized.completed == 2
    assert exported["artifacts_csv"].is_file()
    assert exported["documents_csv"].is_file()
    assert exported["index_md"].is_file()
    with exported["artifacts_csv"].open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    assert {row["artifact_role"] for row in rows} == {
        "original",
        "normalized",
        "summary",
    }
    normalized_rows = [row for row in rows if row["artifact_role"] == "normalized"]
    for row in normalized_rows:
        content = Path(row["path"]).read_text(encoding="utf-8")
        assert "source_id:" in content
        assert "artifact_role: normalized" in content
        assert "locator" in content
    summary_rows = [row for row in rows if row["artifact_role"] == "summary"]
    for row in summary_rows:
        content = Path(row["path"]).read_text(encoding="utf-8")
        assert "summary_method: extractive" in content
        assert "## 内容要点" in content
        assert "目标价" not in content
        assert "买入评级" not in content
    brief_summary = next(row for row in summary_rows if row["title"] == "brief")
    assert "First material fact about operations" in Path(brief_summary["path"]).read_text(
        encoding="utf-8"
    )
    assert _snapshot(source_root) == before


def test_dayu_metadata_only_bundle_is_not_indexed(tmp_path):
    """A dayu bundle with only meta.json (no preferred file) must NOT be
    indexed as a placeholder document (Phase 15.4): re-scanning a stale dayu
    portfolio must never re-create identity-less, byte-less documents."""
    module = _catalog_module()
    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "ACME" / "filings" / "fil_meta_only"
    filing.mkdir(parents=True)
    (filing / "meta.json").write_text(
        json.dumps(
            {
                "ticker": "ACME",
                "document_id": "fil_meta_only",
                "source_title": "Metadata-only filing",
                "form_type": "10-K",
                "ingest_complete": True,
            }
        ),
        encoding="utf-8",
    )
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("dayu", portfolio, "dayu_portfolio"),),
        )
    )

    catalog.scan()

    assert catalog.query(limit=10) == []


def test_page_aware_pdf_and_office_adapters_emit_markdown_or_truthful_stub(tmp_path):
    module = _catalog_module()
    fitz = pytest.importorskip("fitz")
    docx = pytest.importorskip("docx")
    openpyxl = pytest.importorskip("openpyxl")
    pptx = pytest.importorskip("pptx")
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()

    pdf_path = source_root / "annual_report.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Annual report page one")
    page = pdf.new_page()
    page.insert_text((72, 72), "Annual report page two")
    pdf.save(pdf_path)
    pdf.close()

    docx_path = source_root / "investor_relations.docx"
    document = docx.Document()
    document.add_heading("Investor Relations", level=1)
    document.add_paragraph("Capacity reached 100 units.")
    document.save(docx_path)

    xlsx_path = source_root / "financials.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Results"
    sheet.append(["Metric", "Value"])
    sheet.append(["Revenue", 100])
    workbook.save(xlsx_path)

    pptx_path = source_root / "roadshow.pptx"
    deck = pptx.Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = "Roadshow"
    slide.placeholders[1].text = "Customer count reached 10."
    deck.save(pptx_path)

    old_ppt = source_root / "legacy.ppt"
    old_ppt.write_bytes(b"legacy binary presentation")

    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("documents", source_root, "directory"),),
        )
    )
    catalog.scan()
    result = catalog.normalize()
    rows = catalog.query(limit=20)

    assert result.completed == 4
    assert result.unsupported == 1
    assert result.failed == 0
    by_title = {row["title"]: row for row in rows}
    pdf_content = Path(by_title["annual_report"]["normalized_path"]).read_text(encoding="utf-8")
    assert "## Page 1" in pdf_content
    assert "## Page 2" in pdf_content
    assert "loc:v1/page:1" in pdf_content
    assert "Capacity reached 100 units" in Path(
        by_title["investor_relations"]["normalized_path"]
    ).read_text(encoding="utf-8")
    assert "| Metric | Value |" in Path(by_title["financials"]["normalized_path"]).read_text(
        encoding="utf-8"
    )
    assert "## Slide 1" in Path(by_title["roadshow"]["normalized_path"]).read_text(
        encoding="utf-8"
    )
    legacy_content = Path(by_title["legacy"]["normalized_path"]).read_text(encoding="utf-8")
    assert "normalization_status: unsupported" in legacy_content
    assert "unsupported_format" in legacy_content


def test_config_templates_resolve_without_embedding_machine_specific_absolute_paths(tmp_path, monkeypatch):
    module = _catalog_module()
    project = tmp_path / "project"
    profile = tmp_path / "profile"
    monkeypatch.setenv("USERPROFILE", str(profile))
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
schema_version: '1.0'
catalog_dir: '${PROJECT_ROOT}/.source_catalog'
roots:
  - root_id: company_raw
    kind: company_raw
    path: '${PROJECT_ROOT}/companies'
  - root_id: dropbox_stock
    kind: directory
    path: '${USER_PROFILE}/Dropbox/Stock'
""".strip(),
        encoding="utf-8",
    )

    config = module.load_catalog_config(config_path, project_root=project)

    assert config.catalog_dir == project / ".source_catalog"
    assert config.roots[0].path == project / "companies"
    assert config.roots[1].path == profile / "Dropbox" / "Stock"


def test_cli_dry_run_is_read_only_and_real_scan_is_queryable(tmp_path, capsys):
    _catalog_module()
    from company_wiki.source_catalog.cli import main

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "report.txt").write_text("Source-only report text.", encoding="utf-8")
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
schema_version: '1.0'
catalog_dir: '${{PROJECT_ROOT}}/.source_catalog'
roots:
  - root_id: source
    kind: directory
    path: '{source_root.as_posix()}'
""".strip(),
        encoding="utf-8",
    )

    assert main(["--config", str(config_path), "scan", "--dry-run", "--root-id", "source"]) == 0
    dry_payload = json.loads(capsys.readouterr().out)
    assert dry_payload["files_seen"] == 1
    assert not (project / ".source_catalog").exists()

    assert main(["--config", str(config_path), "scan"]) == 0
    capsys.readouterr()
    assert main(["--config", str(config_path), "query", "--text", "report"]) == 0
    query_payload = json.loads(capsys.readouterr().out)
    assert query_payload[0]["title"] == "report"


def test_catalog_writer_lock_and_repeatable_processing_batches(tmp_path):
    module = _catalog_module()
    from company_wiki.source_catalog.lock import CatalogOperationLock

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for number in range(3):
        (source_root / f"report-{number}.txt").write_text(
            f"Source-only report number {number}.", encoding="utf-8"
        )
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("source", source_root, "directory"),),
        )
    )

    catalog.scan()
    with CatalogOperationLock(catalog.config.catalog_dir, operation="test-holder"):
        with pytest.raises(module.CatalogOperationLockedError):
            catalog.scan()

    first = catalog.normalize(limit=1)
    second = catalog.normalize(limit=1)
    assert first.completed == 1
    assert second.completed == 1
    assert catalog.status()["normalized_artifacts"] == 2

    first_summary = catalog.summarize(limit=1)
    second_summary = catalog.summarize(limit=1)
    assert first_summary.completed == 1
    assert second_summary.completed == 1
    assert catalog.status()["summary_artifacts"] == 2


def test_large_index_export_uses_bounded_bulk_queries(tmp_path, monkeypatch):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for number in range(40):
        (source_root / f"report-{number:02d}.txt").write_text(
            f"Source document {number}.", encoding="utf-8"
        )
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("source", source_root, "directory"),),
        )
    )
    catalog.scan()
    fetchall = catalog.store.fetchall
    calls = 0

    def counted(sql, params=()):
        nonlocal calls
        calls += 1
        return fetchall(sql, params)

    monkeypatch.setattr(catalog.store, "fetchall", counted)
    exported = catalog.export_indexes()

    # Bounded bulk queries: documents, entities, locations, artifacts, plus one
    # for semantic duplicate groups, plus one for sources (CW-2.28 query SHA).
    # Must stay O(1) as the catalog grows.
    assert calls == 6
    with exported["documents_csv"].open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 40
