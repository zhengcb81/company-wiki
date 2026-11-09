"""Contract for the public, pathless document browse (G-CWP-01).

Focused coverage required by the owner extension card:

- cross document kinds / multi-version documents under one entity;
- fixed-snapshot pagination and deterministic sorting (cursor + snapshot_id);
- same file name with different bytes stays distinct;
- same document_id with two sources/hashes yields distinct version keys and
  each reopens to exactly its own complete SourceRef;
- storage-root migration keeps the same SourceRef resolvable by the owner
  reader and keeps the pinned snapshot valid;
- no catalog (unavailable) and partially unresolvable versions (partial);
- zero physical-path leakage in any response, cursor or snapshot token.
"""

from __future__ import annotations

import base64
from contextlib import closing
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.public_document_browser import (  # noqa: E402
    BROWSE_REQUEST_SCHEMA,
    REOPEN_REQUEST_SCHEMA,
    PublicBrowseError,
    PublicDocumentBrowser,
    document_version_id,
)
from company_wiki.source_catalog.source_reader import (  # noqa: E402
    SourceVersionReader,
)


ENT = "ent-acme"
ENT_BETA = "ent-beta"

ANNUAL = b"%PDF-1.4 acme annual report 2025"
INTERIM = b"%PDF-1.4 acme interim report 2025H1"
PROSPECTUS = b"%PDF-1.4 acme ipo prospectus"
IR_NOTE = b"# investor relations note\nacme ir material"
NEWS = b"acme wins order"
ANNUAL_BETA = b"%PDF-1.4 beta annual report 2025"
FILING_PRIMARY = b"%PDF-1.4 dayu filing original"
FILING_AMENDED = b"%PDF-1.4 dayu filing amended content v2"
SAME_NAME_OTHER_BYTES = b"%PDF-1.4 same name, different bytes"

SOURCES = {
    "annual": ANNUAL,
    "interim": INTERIM,
    "prospectus": PROSPECTUS,
    "ir": IR_NOTE,
    "news": NEWS,
    "beta": ANNUAL_BETA,
    "primary": FILING_PRIMARY,
    "amended": FILING_AMENDED,
    "same_name": SAME_NAME_OTHER_BYTES,
}


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sidecar(*, entity: str = ENT, kind: str, fiscal_year: int | None,
             provider_id: str, filing_date: str = "2026-03-01",
             sha: str | None = None, language: str = "zh",
             market: str = "CN") -> dict:
    result = {
        "schema_version": "1.0",
        "canonical_entity_id": entity,
        "display_name": "Acme" if entity == ENT else "Beta",
        "market": market,
        "security_id": "600000",
        "document_kind": kind,
        "filing_date": filing_date,
        "form_type": "FY",
        "provider": "test",
        "provider_document_id": provider_id,
        "language": language,
    }
    if fiscal_year is not None:
        result["fiscal_year"] = fiscal_year
        result["period_end"] = f"{fiscal_year}-12-31"
    if sha is not None:
        result["content_sha256"] = sha
    return result


def _write_doc(directory: Path, name: str, body: bytes, sidecar: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(body)
    (directory / f"{name}.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8",
    )
    return path


def _write_tree(tmp_path: Path) -> None:
    companies = tmp_path / "companies"
    _write_doc(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        "2025.pdf", ANNUAL,
        _sidecar(kind="annual_report", fiscal_year=2025, provider_id="acme-ar25",
                 filing_date="2026-03-28"),
    )
    _write_doc(
        companies / "Acme" / "raw" / "financial_reports" / "interim",
        "2025H1.pdf", INTERIM,
        _sidecar(kind="semi_annual_report", fiscal_year=2025,
                 provider_id="acme-h125", filing_date="2025-08-30"),
    )
    _write_doc(
        companies / "Acme" / "raw" / "prospectus",
        "ipo.pdf", PROSPECTUS,
        _sidecar(kind="prospectus", fiscal_year=None, provider_id="acme-ipo",
                 filing_date="2021-01-20"),
    )
    _write_doc(
        companies / "Acme" / "raw" / "ir",
        "note.md", IR_NOTE,
        _sidecar(kind="investor_relations", fiscal_year=None,
                 provider_id="acme-ir-1", filing_date="2026-04-01"),
    )
    _write_doc(
        companies / "Acme" / "raw" / "news",
        "order.md", NEWS,
        _sidecar(kind="news", fiscal_year=None, provider_id="acme-news-1",
                 filing_date="2026-04-02", language="en", market="CN"),
    )
    _write_doc(
        companies / "Beta" / "raw" / "financial_reports" / "annual",
        "2025.pdf", ANNUAL_BETA,
        _sidecar(kind="annual_report", fiscal_year=2025, provider_id="beta-ar25",
                 filing_date="2026-03-28", entity=ENT_BETA),
    )
    # Same file NAME, different bytes in a second root.
    _write_doc(
        tmp_path / "dropbox" / "Stock",
        "2025.pdf", SAME_NAME_OTHER_BYTES,
        _sidecar(kind="annual_report", fiscal_year=2025, provider_id="acme-ar25",
                 filing_date="2026-03-28"),
    )
    # dayu portfolio group: one logical filing, two byte versions.
    filing_dir = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    filing_dir.mkdir(parents=True)
    (filing_dir / "fil_x.pdf").write_bytes(FILING_PRIMARY)
    (filing_dir / "fil_x_amended.pdf").write_bytes(FILING_AMENDED)
    (filing_dir / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": "ACME", "form_type": "FY",
        "canonical_entity_id": ENT, "display_name": "Acme", "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2024, "filing_date": "2025-03-30",
        "source_provider": "dayu", "source_id": "fil_x",
        "source_language": "en",
        "ingest_complete": True, "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(
        json.dumps({"ticker": "ACME", "market": "CN"}), encoding="utf-8",
    )


def _roots(tmp_path: Path) -> tuple[RootSpec, ...]:
    return (
        RootSpec("company_raw", tmp_path / "companies", "company_raw",
                 priority=10, adapter_id="company_raw_v1", read_only=False,
                 reusable_for_filing=True, canonical_write_target="companies"),
        RootSpec("dayu_portfolio", tmp_path / "portfolio", "dayu_portfolio",
                 priority=20, adapter_id="dayu_filing_v1", read_only=True,
                 reusable_for_filing=True),
        RootSpec("dropbox_stock", tmp_path / "dropbox" / "Stock", "directory",
                 priority=30, adapter_id="sidecar_filing_v1", read_only=True,
                 reusable_for_filing=True),
    )


def _config(tmp_path: Path, roots: tuple[RootSpec, ...]) -> CatalogConfig:
    return CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=roots,
        reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
    )


def _build(tmp_path: Path) -> SourceCatalog:
    _write_tree(tmp_path)
    catalog = SourceCatalog(_config(tmp_path, _roots(tmp_path)))
    catalog.scan()
    return catalog


def _browse(browser: PublicDocumentBrowser, **overrides) -> dict:
    request = {
        "schema_version": BROWSE_REQUEST_SCHEMA,
        "canonical_entity_id": ENT,
        "market": None,
        "document_kinds": None,
        "fiscal_years": None,
        "language": None,
        "source_statuses": None,
        "limit": None,
        "cursor": None,
        "snapshot_id": None,
    }
    request.update(overrides)
    return browser.browse(request)


def _iter_pages(browser: PublicDocumentBrowser, first: dict, limit: int = 2):
    page = first
    while True:
        yield page
        if page["page"]["next_cursor"] is None:
            return
        page = _browse(browser, limit=limit, cursor=page["page"]["next_cursor"])


# --- happy path: cross-kind, pathless, complete SourceRefs -------------------


def test_browse_covers_all_document_kinds_with_complete_source_refs(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser)
    assert result["state"] == "available"
    kinds = {item["document_kind"] for item in result["items"]}
    assert kinds == {
        "annual_report", "semi_annual_report", "prospectus",
        "investor_relations", "news",
    }
    # dayu multi-version: both byte versions of one logical filing present,
    # current first (content-addressed document id from the primary sha)
    annual_items = [i for i in result["items"]
                    if i["document_kind"] == "annual_report"]
    dayu_docs = [i for i in annual_items
                 if i["document_id"].endswith(_sha(FILING_PRIMARY))]
    assert len(dayu_docs) == 2
    assert {i["is_current_version"] for i in dayu_docs} == {True, False}
    assert dayu_docs[0]["is_current_version"] is True
    for item in result["items"]:
        ref = item["source_ref"]
        assert ref["schema_version"] == "2.0"
        assert ref["document_id"] == item["document_id"]
        assert ref["content_sha256"] == _sha(
            SOURCES[_body_key(item)])
        assert ref["byte_size"] == len(SOURCES[_body_key(item)])
        assert ref["mime_type"]
    # facets count the filtered snapshot exactly
    total = result["page"]["total"]
    assert sum(result["facets"]["document_kind"].values()) == total
    assert result["facets"]["document_kind"]["annual_report"] == len(annual_items)
    catalog.close()


def _body_key(item: dict) -> str:
    return {
        _sha(ANNUAL): "annual", _sha(INTERIM): "interim",
        _sha(PROSPECTUS): "prospectus", _sha(IR_NOTE): "ir",
        _sha(NEWS): "news", _sha(ANNUAL_BETA): "beta",
        _sha(FILING_PRIMARY): "primary", _sha(FILING_AMENDED): "amended",
        _sha(SAME_NAME_OTHER_BYTES): "same_name",
    }[item["source_ref"]["content_sha256"]]


def test_entity_scope_excludes_other_companies_and_matches_both_channels(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser)
    assert all(i["source_ref"]["content_sha256"] != _sha(ANNUAL_BETA)
               for i in result["items"])
    # path-derived entity key (scanner: ticker:ACME) resolves a subset of
    # the same cabinet; the dropbox document only declares the metadata
    # channel, so the two channels legitimately differ by that doc.
    by_path_key = _browse(browser, canonical_entity_id="ticker:ACME")
    assert by_path_key["state"] == "available"
    assert {i["document_version_id"] for i in by_path_key["items"]} < \
        {i["document_version_id"] for i in result["items"]}
    dayu_current = next(
        i for i in by_path_key["items"]
        if i["document_id"].endswith(_sha(FILING_PRIMARY))
        and i["is_current_version"])
    assert dayu_current["source_ref"]["content_sha256"] == _sha(FILING_PRIMARY)
    beta = _browse(browser, canonical_entity_id=ENT_BETA)
    assert beta["state"] == "available"
    assert {i["source_ref"]["content_sha256"] for i in beta["items"]} == \
        {_sha(ANNUAL_BETA)}
    catalog.close()


# --- stable version identity: same document, different bytes -----------------


def test_same_document_id_dual_sources_get_distinct_version_ids_and_reopen(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser, document_kinds=["annual_report"],
                     fiscal_years=[2024])
    items = result["items"]
    assert len(items) == 2
    assert {i["document_id"] for i in items} == {items[0]["document_id"]}
    version_ids = {i["document_version_id"] for i in items}
    assert len(version_ids) == 2
    shas = {i["source_ref"]["content_sha256"] for i in items}
    assert shas == {_sha(FILING_PRIMARY), _sha(FILING_AMENDED)}
    # deterministic token == hash of the complete triple
    for item in items:
        assert item["document_version_id"] == document_version_id(
            item["document_id"], item["source_ref"]["source_id"],
            item["source_ref"]["content_sha256"],
        )
    # exact reopen per frozen version
    for item in items:
        reopened = browser.reopen_document_version({
            "schema_version": REOPEN_REQUEST_SCHEMA,
            "document_version_id": item["document_version_id"],
        })
        assert reopened["state"] == "available"
        assert reopened["document"]["source_ref"] == item["source_ref"]
        assert reopened["document"]["document_id"] == item["document_id"]
    unknown = browser.reopen_document_version(
        "cwpdv1-" + "A" * 43)
    assert unknown["state"] == "not_found"
    catalog.close()


def test_same_name_different_bytes_stays_distinct(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser, document_kinds=["annual_report"],
                     fiscal_years=[2025])
    shas = [i["source_ref"]["content_sha256"] for i in result["items"]]
    assert _sha(ANNUAL) in shas
    assert _sha(SAME_NAME_OTHER_BYTES) in shas
    ids = {i["document_id"] for i in result["items"]}
    assert len(ids) == len(result["items"])  # content-addressed documents
    assert _sha(ANNUAL_BETA) not in shas
    catalog.close()


# --- fixed snapshot pagination and deterministic ordering --------------------


def test_snapshot_pagination_is_exact_stable_and_sorted(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser, limit=3)
    assert first["page"]["total_status"] == "exact"
    collected = []
    snapshot_ids = set()
    for page in _iter_pages(browser, first, limit=3):
        snapshot_ids.add(page["page"]["snapshot_id"])
        assert page["catalog_revision"] == first["catalog_revision"]
        collected.extend(page["items"])
    assert len(collected) == first["page"]["total"]
    assert len(snapshot_ids) == 1
    # deterministic order: kind ascending groups the cabinet
    kinds = [i["document_kind"] for i in collected]
    assert kinds == sorted(kinds)
    # within one document the current version precedes historical ones
    by_doc: dict[str, list[dict]] = {}
    for item in collected:
        by_doc.setdefault(item["document_id"], []).append(item)
    for items in by_doc.values():
        if len(items) > 1:
            assert items[0]["is_current_version"] is True
            assert items[1]["is_current_version"] is False
    # replay with an explicit snapshot id serves the same page again
    replay = _browse(browser, limit=3, snapshot_id=first["page"]["snapshot_id"])
    assert [i["document_version_id"] for i in replay["items"]] == \
        [i["document_version_id"] for i in first["items"]]
    assert replay["page"]["snapshot_id"] == first["page"]["snapshot_id"]
    catalog.close()


def test_stale_snapshot_is_reported_never_mixed(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser, limit=2)
    cursor = first["page"]["next_cursor"]
    assert cursor is not None
    # catalog content changes between pages (a new document is indexed)
    _write_doc(
        tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "quarterly",
        "2026Q1.pdf", b"%PDF-1.4 acme quarterly 2026Q1",
        _sidecar(kind="quarterly_report", fiscal_year=2026,
                 provider_id="acme-q1-26"),
    )
    catalog.scan()
    second = _browse(browser, limit=2, cursor=cursor)
    assert second["state"] == "stale"
    assert "catalog_revision_changed" in second["reason_codes"]
    assert second["items"] == []
    assert second["catalog_revision"] != first["catalog_revision"]
    # the fresh snapshot restarts pagination coherently
    restart = _browse(browser, limit=2,
                      snapshot_id=second["page"]["snapshot_id"])
    assert restart["state"] in {"available", "partial"}
    assert restart["page"]["total"] == first["page"]["total"] + 1
    catalog.close()


def test_filter_conflicts_and_bad_tokens_are_rejected(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser, limit=2)
    with pytest.raises(PublicBrowseError):
        _browse(browser, cursor=first["page"]["next_cursor"],
                document_kinds=["news"])  # conflicts with pinned snapshot
    with pytest.raises(PublicBrowseError):
        _browse(browser, snapshot_id=first["page"]["snapshot_id"],
                canonical_entity_id="company-name:Acme")
    with pytest.raises(PublicBrowseError):
        _browse(browser, cursor="not-a-valid-token")
    with pytest.raises(PublicBrowseError):
        _browse(browser, limit=0)
    with pytest.raises(PublicBrowseError):
        _browse(browser, market="x" * 500)
    with pytest.raises(PublicBrowseError):
        browser.browse({"schema_version": BROWSE_REQUEST_SCHEMA})
    # F-01 (review): a null canonical entity is a blocked request, never an
    # internal crash (CLI must emit the blocked envelope with exit 2).
    with pytest.raises(PublicBrowseError):
        _browse(browser, canonical_entity_id=None)
    catalog.close()


def test_snapshot_filter_replay_is_order_insensitive_and_empty_list_is_unset(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser, document_kinds=["annual_report", "news"], limit=3)
    assert first["state"] == "available"
    # F-02 (review): re-sending the same filter SET in a different order is
    # a replay, not a conflict.
    replay = _browse(browser, limit=3,
                     document_kinds=["news", "annual_report"],
                     snapshot_id=first["page"]["snapshot_id"])
    assert [i["document_version_id"] for i in replay["items"]] == \
        [i["document_version_id"] for i in first["items"]]
    # F-04 (review): an empty filter list means "no filter" — same cabinet as
    # an absent filter, on fresh and replayed pages alike.
    unfiltered = _browse(browser, document_kinds=[], limit=3)
    assert unfiltered["page"]["total"] == _browse(browser, limit=3)["page"]["total"]
    catalog.close()


def test_forged_cursor_offset_beyond_total_reports_empty(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser, document_kinds=["news"], limit=3)
    assert first["page"]["total"] == 1
    import base64
    import json as _json
    forged = base64.urlsafe_b64encode(_json.dumps({
        "v": 1, "snapshot": first["page"]["snapshot_id"], "offset": 999999,
    }).encode("utf-8")).decode("ascii").rstrip("=")
    # F-03 (review): a past-the-end offset is reported honestly as an empty
    # page, not as a silently "available" zero-item slice.
    page = _browse(browser, cursor=forged)
    assert page["items"] == []
    assert page["state"] == "empty"
    assert "page_offset_beyond_total" in page["reason_codes"]
    assert page["page"]["next_cursor"] is None
    catalog.close()


# --- migration, missing roots, unavailable, empty ----------------------------


def test_root_migration_keeps_source_ref_resolvable_and_snapshot_valid(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    first = _browse(browser)  # full first page keeps the pinned snapshot
    ref = next(i["source_ref"] for i in first["items"]
               if i["processing_state"] == "active"
               and i["source_ref"]["content_sha256"] == _sha(ANNUAL))
    old_revision = first["catalog_revision"]
    catalog.close()
    # migrate the storage tree: new directory, same root ids
    migrated = tmp_path / "migrated"
    migrated.mkdir()
    (tmp_path / "companies").rename(migrated / "companies")
    roots2 = (
        RootSpec("company_raw", migrated / "companies", "company_raw",
                 priority=10, adapter_id="company_raw_v1", read_only=False,
                 reusable_for_filing=True, canonical_write_target="companies"),
        RootSpec("dayu_portfolio", tmp_path / "portfolio", "dayu_portfolio",
                 priority=20, adapter_id="dayu_filing_v1", read_only=True,
                 reusable_for_filing=True),
        RootSpec("dropbox_stock", tmp_path / "dropbox" / "Stock", "directory",
                 priority=30, adapter_id="sidecar_filing_v1", read_only=True,
                 reusable_for_filing=True),
    )
    catalog2 = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=roots2,
        reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
    ))
    browser2 = PublicDocumentBrowser(catalog2)
    again = _browse(browser2, limit=2,
                    snapshot_id=first["page"]["snapshot_id"])
    # catalog content is unchanged by a path move: the pinned snapshot holds
    assert again["state"] in {"available", "partial"}
    assert again["catalog_revision"] == old_revision
    # the owner reader resolves the very same SourceRef from the new root
    reader = SourceVersionReader(catalog2)
    receipt = reader.verify_version(_as_ref(ref), purpose="source_export")
    assert receipt.content_sha256 == ref["content_sha256"]
    catalog2.close()


def _as_ref(ref: dict):
    from company_wiki.source_catalog.source_reader import SourceRef
    return SourceRef(**ref)


def test_missing_root_in_config_yields_partial_state(tmp_path):
    catalog = _build(tmp_path)
    catalog.close()
    reduced = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(
            RootSpec("company_raw", tmp_path / "companies", "company_raw",
                     priority=10, adapter_id="company_raw_v1", read_only=False,
                     reusable_for_filing=True, canonical_write_target="companies"),
        ),
        reusable_root_kinds=("company_raw",),
    ))
    browser = PublicDocumentBrowser(reduced)
    result = _browse(browser)
    assert result["page"]["total"] > 0
    assert any(i["storage_state"] == "not_resolvable" for i in result["items"])
    assert result["state"] == "partial"
    assert "some_versions_not_resolvable" in result["reason_codes"]
    reduced.close()


def test_filters_empty_result_is_reported_as_empty(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser, fiscal_years=[1999])
    assert result["state"] == "empty"
    assert result["items"] == []
    assert result["reason_codes"] == ["no_documents_match_filters"]
    assert result["page"]["total"] == 0
    assert result["facets"] == {name: {} for name in (
        "document_kind", "language", "source_status", "market", "fiscal_year")}
    catalog.close()


def _run_cli(config_path: Path, payload: dict | str,
             cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    data = (json.dumps(payload) if isinstance(payload, dict)
            else payload).encode("utf-8")
    return subprocess.run(
        [sys.executable, "-B",
         "-m", "company_wiki.source_catalog.public_document_browser_cli",
         "--config", str(config_path)],
        input=data, capture_output=True, cwd=str(cwd), env=env,
    )


def _write_cli_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "reusable_root_kinds": ["company_raw", "dayu_portfolio", "directory"],
        "roots": [
            {"root_id": "company_raw", "kind": "company_raw",
             "path": str(tmp_path / "companies"), "priority": 10},
            {"root_id": "dayu_portfolio", "kind": "dayu_portfolio",
             "path": str(tmp_path / "portfolio"), "priority": 20},
            {"root_id": "dropbox_stock", "kind": "directory",
             "path": str(tmp_path / "dropbox" / "Stock"), "priority": 30},
        ],
    }), encoding="utf-8")
    return config_path


def test_missing_catalog_is_unavailable_via_cli(tmp_path):
    empty_root = tmp_path / "none"
    empty_root.mkdir()
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".missing_catalog"),
        "reusable_root_kinds": ["company_raw"],
        "roots": [{
            "root_id": "company_raw", "kind": "company_raw",
            "path": str(empty_root), "priority": 10,
        }],
    }), encoding="utf-8")
    request = json.dumps({
        "schema_version": BROWSE_REQUEST_SCHEMA,
        "canonical_entity_id": ENT,
        "market": None, "document_kinds": None, "fiscal_years": None,
        "language": None, "source_statuses": None,
        "limit": None, "cursor": None, "snapshot_id": None,
    })
    proc = _run_cli(config_path, request, tmp_path)
    assert proc.returncode == 2
    error = json.loads(proc.stderr.decode("utf-8").splitlines()[-1])
    assert error["state"] == "unavailable"


# --- CLI end-to-end and zero path leakage ------------------------------------


def test_cli_browse_and_reopen_roundtrip(tmp_path):
    catalog = _build(tmp_path)
    catalog.close()
    config_path = _write_cli_config(tmp_path)

    def run(payload: dict | str) -> subprocess.CompletedProcess:
        return _run_cli(config_path, payload, tmp_path)

    browse_request = {
        "schema_version": BROWSE_REQUEST_SCHEMA,
        "canonical_entity_id": ENT,
        "market": None, "document_kinds": None, "fiscal_years": None,
        "language": None, "source_statuses": None,
        "limit": 4, "cursor": None, "snapshot_id": None,
    }
    proc = run(browse_request)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.decode("utf-8"))
    assert result["state"] in {"available", "partial"}
    assert result["page"]["total"] >= 8

    reopen_request = {
        "schema_version": REOPEN_REQUEST_SCHEMA,
        "document_version_id": result["items"][0]["document_version_id"],
    }
    proc = run(reopen_request)
    assert proc.returncode == 0, proc.stderr
    reopened = json.loads(proc.stdout.decode("utf-8"))
    assert reopened["state"] == "available"
    assert reopened["document"]["source_ref"] == result["items"][0]["source_ref"]

    bad = dict(browse_request, limit=0)
    proc = run(bad)
    assert proc.returncode == 2
    assert json.loads(proc.stderr.decode("utf-8").splitlines()[-1])["state"] \
        == "blocked"

    # F-01 (review RED): a null canonical entity is a blocked request with
    # the error envelope — never an internal traceback with exit 1.
    proc = run(dict(browse_request, canonical_entity_id=None))
    assert proc.returncode == 2, proc.stderr
    assert json.loads(proc.stderr.decode("utf-8").splitlines()[-1]) == {
        "schema_version": "company-wiki-public-document-browse/1",
        "state": "blocked",
        "reason": "invalid_canonical_entity_id",
    }

    # duplicate JSON keys are rejected
    proc = _run_cli(
        config_path,
        json.dumps(browse_request)[:-1] + ',"limit":4,"limit":4}',
        tmp_path,
    )
    assert proc.returncode == 2
    assert json.loads(proc.stderr.decode("utf-8").splitlines()[-1])["state"] \
        == "blocked"
    _assert_no_path_leak(json.dumps(result) + json.dumps(reopened), tmp_path)


@pytest.mark.parametrize(
    ("entry", "reason"),
    [("request", "invalid_request"), ("snapshot", "invalid_snapshot_id")],
)
def test_cli_reports_json_decoder_stack_failure_without_traceback(tmp_path, entry, reason):
    catalog = _build(tmp_path)
    catalog.close()
    config_path = _write_cli_config(tmp_path)
    nested = "[" * 3_000 + "0" + "]" * 3_000
    if entry == "request":
        request = '{"schema_version":"' + BROWSE_REQUEST_SCHEMA + '","nested":' + nested + "}"
    else:
        token = base64.urlsafe_b64encode(('{"v":1,"nested":' + nested + "}").encode())
        request = {
            "schema_version": BROWSE_REQUEST_SCHEMA,
            "canonical_entity_id": ENT,
            "market": None, "document_kinds": None, "fiscal_years": None,
            "language": None, "source_statuses": None, "limit": None, "cursor": None,
            "snapshot_id": token.decode().rstrip("="),
        }

    proc = _run_cli(config_path, request, tmp_path)
    assert proc.returncode == 2, proc.stderr
    assert proc.stdout == b""
    assert json.loads(proc.stderr) == {
        "schema_version": "company-wiki-public-document-browse/1",
        "state": "blocked",
        "reason": reason,
    }
    _assert_no_path_leak(proc.stderr.decode(), tmp_path)


def test_invalid_catalog_locator_does_not_advertise_resolvable_original(tmp_path):
    with closing(_build(tmp_path)) as catalog:
        browser = PublicDocumentBrowser(catalog)
        original_sha = _sha(ANNUAL)
        before = next(item for item in _browse(browser)["items"]
                      if item["source_ref"]["content_sha256"] == original_sha)
        assert before["storage_state"] == "resolvable"
        ref = before["source_ref"]
        with catalog.store.transaction() as connection:
            connection.execute(
                "UPDATE locations SET relative_path=? WHERE document_id=? AND source_id=?",
                ("../escape.pdf", ref["document_id"], ref["source_id"]),
            )
        result = _browse(browser)
        after = next(item for item in result["items"] if item["source_ref"] == ref)
        assert result["state"] == "partial"
        assert after["storage_state"] == "not_resolvable"
        assert browser.reopen_document_version(before["document_version_id"])["document"] == after
        _assert_no_path_leak(json.dumps(after), tmp_path)


def _assert_no_path_leak(payload: str, tmp_path: Path) -> None:
    for marker in (
        str(tmp_path), str(tmp_path.resolve()), "relative_path",
        "absolute_path", "catalog.sqlite3", "source_catalog.yaml",
    ):
        assert marker not in payload, marker


def test_browse_response_never_leaks_paths_or_locations(tmp_path):
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser, limit=2)
    payload = json.dumps(result, ensure_ascii=True)
    for marker in (
        str(tmp_path), str(tmp_path.resolve()), "relative_path",
        "absolute_path", ".source_catalog", "catalog.sqlite3",
        "companies", "portfolio", "dropbox", os.sep if os.sep != "/" else "never",
    ):
        assert marker not in payload, marker
    for item in result["items"]:
        version_id = item["document_version_id"]
        assert "/" not in version_id and "\\" not in version_id
        assert version_id.startswith("cwpdv1-")
        assert version_id.isascii()
    # cursors and snapshot tokens carry no path either
    page2 = _browse(browser, limit=1)
    tokens = json.dumps([
        result["page"]["snapshot_id"], page2["page"]["snapshot_id"],
        page2["page"]["next_cursor"],
    ])
    for marker in (str(tmp_path), str(tmp_path.resolve()), os.sep, "companies"):
        assert marker not in tokens, marker
    catalog.close()
