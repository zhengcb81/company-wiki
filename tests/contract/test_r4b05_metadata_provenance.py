"""R4 phase-B step B05 acceptance: metadata merge keeps provenance, never a whole column.

B05's design (b-design §B05): the scanner merges document metadata from several
captures of the same content-addressed document.  It must

  1. record per-field **provenance** under the reserved key ``r4_provenance``
     (``{"schema_version": "1.0", "fields": {field: {source_id, observed_at,
     value_hash}}}``) — hashes only, **never raw text fragments**;
  2. keep every OTHER key that lives in ``documents.metadata_json`` — before
     B05 the ``prefer_new`` branch replaced the whole column, which silently
     dropped receipts written by other modules (for example the
     ``prompt_injection_review`` receipt that ``resolver`` exposes as
     ``prompt_injection_status``);
  3. leave the container shape alone, so the SQL pushdown filters that read
     ``json_extract(metadata_json, '$.acquisition.fiscal_year')`` keep working.

Cases below are RED until the merge implements the reserved key; they are the
F10 landing point for the step.  Product code is NOT modified by this file.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.prompt_injection import (  # noqa: E402
    read_prompt_injection_review,
    record_prompt_injection_review,
)

BODY = b"%PDF-1.4 r4b05-provenance"
DIGEST = hashlib.sha256(BODY).hexdigest()
CANARY = "DO-NOT-STORE-THIS-RAW-FRAGMENT-7f3c1b9d4e2a"


def _sidecar(
    *,
    url: str | None = "https://sec.gov/x/2025",
    market: str | None = "US",
    security_id: str | None = "ACME",
    provider_document_id: str | None = "doc-1",
    fiscal_year: int | None = 2025,
    extra: dict | None = None,
) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "document_kind": "annual_report",
        "fiscal_year": fiscal_year,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "content_sha256": DIGEST,
    }
    if url is not None:
        payload["source_url"] = url
    if market is not None:
        payload["market"] = market
    if security_id is not None:
        payload["security_id"] = security_id
    if provider_document_id is not None:
        payload["provider_document_id"] = provider_document_id
    if extra:
        payload.update(extra)
    return payload


def _write_copy(directory: Path, sidecar: dict, name: str = "2025.pdf") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )


def _roots(*specs: tuple[str, Path, int]) -> list[RootSpec]:
    return [
        RootSpec(
            root_id,
            path,
            "company_raw" if root_id == "company_raw" else "directory",
            priority=priority,
            adapter_id=(
                "company_raw_v1" if root_id == "company_raw" else "sidecar_filing_v1"
            ),
            read_only=root_id != "company_raw",
            reusable_for_filing=True,
            canonical_write_target="companies" if root_id == "company_raw" else None,
        )
        for root_id, path, priority in specs
    ]


def _catalog(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=tuple(roots),
        )
    )


def _scan(tmp_path: Path, roots: list[RootSpec]):
    catalog = _catalog(tmp_path, roots)
    catalog.scan()
    return catalog


def _fetchone(catalog, sql: str, params: tuple = ()):
    return catalog.store.fetchone(sql, params)


def _metadata(catalog, document_id: str) -> dict:
    row = _fetchone(
        catalog, "SELECT metadata_json FROM documents WHERE document_id=?", (document_id,)
    )
    assert row is not None, document_id
    return json.loads(row["metadata_json"] or "{}")


def _sole_document_id(catalog) -> str:
    """The filing document itself — sidecars are ingested as their own sources,
    so "the first document" is not necessarily the filing."""
    rows = _fetchall(
        catalog,
        "SELECT document_id FROM documents WHERE document_kind='annual_report' "
        "ORDER BY document_id",
    )
    assert len(rows) == 1, rows
    return str(rows[0]["document_id"])


def _fetchall(catalog, sql: str, params: tuple = ()):
    return [dict(row) for row in catalog.store.fetchall(sql, params)]


def _receipt(catalog, document_id: str) -> None:
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    try:
        record_prompt_injection_review(
            con,
            document_id,
            status="not_detected",
            reviewer="r4b05-test",
            evidence_sha256="a" * 64,
            now="2026-09-12T00:00:00Z",
        )
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------------------
# The reserved key: present, hashed, schema-versioned, additive
# ---------------------------------------------------------------------------


def test_r4b05_merge_records_provenance_without_replacing_the_column(tmp_path):
    """A second capture with richer metadata (same bytes) enters through the
    ``prefer_new`` path: the new business metadata wins, but the column is
    merged — unrelated keys survive and ``r4_provenance`` records the fields."""
    companies = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(url=None, market=None, security_id=None, provider_document_id=None),
    )
    # both roots are configured up front; the second one is EMPTY for the first
    # scan and only gets its copy before the rescan below.  The second root sits
    # at the SAME priority tier, which is what lets the merge branch run.
    catalog = _catalog(
        tmp_path,
        _roots(("company_raw", companies, 10), ("dropbox_stock", dropbox, 10)),
    )
    catalog.scan()
    document_id = _sole_document_id(catalog)
    _receipt(catalog, document_id)
    stored_before = _metadata(catalog, document_id)
    assert "prompt_injection_review" in stored_before, stored_before

    # a second copy of the SAME bytes in another root, with complete identity
    _write_copy(dropbox, _sidecar(extra={"unrelated_canary": CANARY}))
    catalog.scan()

    metadata = _metadata(catalog, document_id)
    # 1. the receipt written by another module is still there (B05's core fix)
    assert "prompt_injection_review" in metadata, metadata
    receipt = read_prompt_injection_review(catalog.reader, document_id)
    assert receipt is not None and receipt["status"] == "not_detected", receipt
    # 2. the richer business metadata won
    assert metadata["acquisition"]["source_url"] == "https://sec.gov/x/2025", metadata
    # 3. the reserved provenance key exists, is versioned and covers fields
    provenance = metadata.get("r4_provenance")
    assert isinstance(provenance, dict), metadata
    assert provenance["schema_version"] == "1.0", provenance
    fields = provenance["fields"]
    assert fields, provenance
    for name, record in fields.items():
        assert set(record) == {"value", "sources", "conflicts"}, (name, record)
        assert isinstance(record["value"], str) and record["value"], record
        assert isinstance(record["sources"], list), (name, record)
        for source in record["sources"]:
            assert set(source) == {"source_id", "observed_at", "role"}, source
    # 4. hashes only: the unrelated canary text is nowhere in the provenance
    assert CANARY not in json.dumps(provenance, ensure_ascii=False)


def test_r4b05_merge_without_prefer_new_still_records_provenance(tmp_path):
    """When the stored metadata is already the richer one, the merge must keep
    it (no downgrade) and still refresh the provenance block."""
    companies = tmp_path / "companies"
    other = tmp_path / "future_lake"
    _write_copy(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(),
    )
    catalog = _catalog(
        tmp_path,
        _roots(("company_raw", companies, 10), ("future_lake", other, 10)),
    )
    catalog.scan()
    document_id = _sole_document_id(catalog)

    # a poorer copy of the same bytes lands in the SAME priority tier
    _write_copy(other, _sidecar(url=None, market=None, security_id=None))
    catalog.scan()

    metadata = _metadata(catalog, document_id)
    assert metadata["acquisition"]["source_url"] == "https://sec.gov/x/2025", metadata
    assert metadata.get("r4_provenance", {}).get("schema_version") == "1.0", metadata


# ---------------------------------------------------------------------------
# A real disagreement is kept, never resolved by priority
# ---------------------------------------------------------------------------


def test_r4b05_true_conflict_keeps_every_candidate_and_blocks_the_read_side(tmp_path):
    """Two captures of the same bytes disagree on ``title`` (different file
    names, same priority tier).  The stored value stays as the single value,
    BOTH candidates are recorded under the field, and the read contract reports
    the document as blocked instead of quietly preferring one side."""
    companies = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(),
        "acme-2025-annual.pdf",
    )
    catalog = _catalog(
        tmp_path,
        _roots(("company_raw", companies, 10), ("dropbox_stock", dropbox, 10)),
    )
    catalog.scan()
    document_id = _sole_document_id(catalog)
    stored_title = _fetchone(
        catalog, "SELECT title FROM documents WHERE document_id=?", (document_id,)
    )["title"]

    # same bytes, same tier, but the file name says something else
    _write_copy(dropbox, _sidecar(), "acme-2025-annual-restated.pdf")
    catalog.scan()

    metadata = _metadata(catalog, document_id)
    title_record = metadata["r4_provenance"]["fields"]["title"]
    assert title_record["conflicts"], title_record
    hashes = {item["value_hash"] for item in title_record["conflicts"]}
    assert len(hashes) == 2, title_record
    # the stored single value did not flip, and it is still the document title
    row = _fetchone(
        catalog, "SELECT title FROM documents WHERE document_id=?", (document_id,)
    )
    assert row["title"] == stored_title, row

    candidate = catalog.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",)
    )[0]
    assert candidate["metadata_status"] == "blocked", candidate["conflicts"]
    assert candidate["conflicts"] == ["title"], candidate["conflicts"]
    assert candidate["provenance"]["title"]["conflicts"], candidate["provenance"]


def test_r4b05_later_capture_fills_a_missing_column(tmp_path):
    """The capture_ready recovery path must survive: a column the stored row does
    NOT have yet is filled by a later capture (fill a gap, never overwrite)."""
    companies = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(fiscal_year=None),
    )
    catalog = _catalog(
        tmp_path,
        _roots(("company_raw", companies, 10), ("dropbox_stock", dropbox, 10)),
    )
    catalog.scan()
    document_id = _sole_document_id(catalog)
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute(
        "UPDATE documents SET published_date=NULL WHERE document_id=?", (document_id,)
    )
    con.commit()
    con.close()

    _write_copy(dropbox, _sidecar(), "acme-2025-annual.pdf")
    catalog.scan()

    row = _fetchone(
        catalog,
        "SELECT published_date, title FROM documents WHERE document_id=?",
        (document_id,),
    )
    assert row["published_date"] == "2026-02-20", row
    metadata = _metadata(catalog, document_id)
    assert metadata["r4_provenance"]["fields"]["published_date"]["value"], metadata


# ---------------------------------------------------------------------------
# The container shape must survive: the SQL pushdown filters depend on it
# ---------------------------------------------------------------------------


def test_r4b05_container_shape_survives_so_json_extract_still_filters(tmp_path):
    """`query_filing_candidates` pushes `fiscal_year` down with
    `json_extract(metadata_json, '$.acquisition.fiscal_year')`; the merge must
    keep that path working (and the receipt key must not disturb it)."""
    companies = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(
        companies / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(url=None, market=None, security_id=None, provider_document_id=None),
    )
    catalog = _catalog(
        tmp_path,
        _roots(("company_raw", companies, 10), ("dropbox_stock", dropbox, 10)),
    )
    catalog.scan()
    document_id = _sole_document_id(catalog)
    _receipt(catalog, document_id)

    _write_copy(dropbox, _sidecar())
    catalog.scan()

    value = _fetchone(
        catalog,
        "SELECT json_extract(metadata_json, '$.acquisition.fiscal_year') AS year "
        "FROM documents WHERE document_id=?",
        (document_id,),
    )
    assert value["year"] == 2025, value
    candidates = catalog.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",), fiscal_year=2025
    )
    assert [item["document_id"] for item in candidates] == [document_id]
    assert candidates[0]["metadata"]["acquisition"]["fiscal_year"] == 2025
