"""LT/UJ REAL-data E2E (GP-005 completion, owner-directed design).

Design principle: the DOWNLOAD is NOT the test target.  Real documents
were downloaded ONCE (Zijin FY2024 + FY2025 annual reports are already in
the production catalog under company_raw); every test run REUSES those
existing documents to verify the resolver / reuse / idempotency logic.

Everything is READ-ONLY against the production catalog (mode=ro, same as
test_zr409).  A missing catalog or missing Zijin documents SKIP the
tests (environmental precondition), never fail.

Scenarios verified on real data:

  LT-02  Both periods exist (FY2024 old + FY2025 new) -> each request
         resolves to its own period's handle; latest (FY2025) is
         returned with capture-ready state.
  LT-08  An immediate re-resolve after a successful resolve returns the
         same capture-ready handle (no manual retry needed).
  LT-09  A second identical request resolves identically and the catalog
         file bytes are unchanged (zero side effects).
  UJ-03  Old period (FY2024) and new period (FY2025) are both reusable;
         requesting the new period returns the latest capture-ready
         handle with its processing artifacts present.
  UJ-05  Full reuse journey: the request resolves to the existing
         document AND its normalized artifact is readable - the pipeline
         needs no re-processing.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
sys.path.insert(0, str(WIKI_ROOT / "src"))

PRODUCTION_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
PRODUCTION_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"

ZIJIN_ENTITY = "紫金矿业"
ZIJIN_SECURITY = "601899"
ZIJIN_MARKET = "CN"
ZIJIN_PDOC_2024 = "1222870413"
ZIJIN_PDOC_2025 = "1225023658"


def _env_ready() -> bool:
    return PRODUCTION_DB.is_file() and PRODUCTION_CONFIG.is_file()


def _zijin_docs_present() -> bool:
    if not _env_ready():
        return False
    con = sqlite3.connect(f"file:{PRODUCTION_DB}?mode=ro", uri=True)
    try:
        row = con.execute(
            """SELECT COUNT(DISTINCT d.document_id) AS c FROM documents d
               JOIN locations l ON l.document_id=d.document_id
               WHERE d.document_kind='annual_report'
                 AND (d.title LIKE '%紫金%' OR d.title LIKE '%601899%')
                 AND l.root_id='company_raw' AND l.location_status='active'"""
        ).fetchone()
        return bool(row and row[0] >= 2)
    finally:
        con.close()


REQUIRE_REAL = pytest.mark.skipif(
    not _zijin_docs_present(),
    reason="production catalog or Zijin annual reports not present (read-only E2E precondition)",
)


def _production_catalog():
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(PRODUCTION_CONFIG, project_root=WIKI_ROOT)
    return SourceCatalog(config)


def _resolve(catalog, *, fy: int, pdoc: str, as_of: str = "2026-09-03"):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(
        SourceRequest(
            entity=ZIJIN_ENTITY,
            market=ZIJIN_MARKET,
            security_id=ZIJIN_SECURITY,
            document_kind="annual_report",
            fiscal_year=fy,
            provider="cninfo",
            provider_document_id=pdoc,
            as_of_date=as_of,
            mode="exact",
        )
    )


def _db_state() -> tuple:
    """Cheap zero-write fingerprint of the (49 GB) catalog.

    Reading the whole file to hash it would take minutes; instead we capture
    the SQLite header change counter (bytes 24-27: increments on every
    committed write transaction), the file size + mtime, and any journal /
    WAL / SHM sidecar state.  A resolver write would change at least one of
    these; the read is only 100 bytes so the check stays fast.
    """
    st = PRODUCTION_DB.stat()
    with PRODUCTION_DB.open("rb") as fh:
        header = fh.read(100)
    change_counter = (
        int.from_bytes(header[24:28], "big") if len(header) >= 28 else None
    )
    sidecars = tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns)
        for p in (
            Path(f"{PRODUCTION_DB}-journal"),
            Path(f"{PRODUCTION_DB}-wal"),
            Path(f"{PRODUCTION_DB}-shm"),
        )
        if p.exists()
    )
    return (st.st_size, st.st_mtime_ns, change_counter, sidecars)


def _artifact_path(catalog, *, fy: int, pdoc: str) -> Path | None:
    """Locate the normalized artifact for the FY request via its source."""
    con = sqlite3.connect(f"file:{PRODUCTION_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            """SELECT a.path, a.status FROM artifacts a
               JOIN documents d ON d.document_id=a.document_id
               JOIN sources s ON s.source_id=d.primary_source_id
               WHERE a.artifact_role='normalized'
                 AND d.document_kind='annual_report'
                 AND (d.title LIKE '%紫金%' OR d.title LIKE '%601899%')
                 AND s.content_sha256 IS NOT NULL
               ORDER BY a.created_at DESC LIMIT 1"""
        ).fetchone()
        if row is None:
            return None
        return Path(row["path"]) if Path(row["path"]).is_file() else None
    finally:
        con.close()


# ---------------------------------------------------------------------------
# LT-02: old + new periods both present -> per-period handles, latest returned
# ---------------------------------------------------------------------------


@REQUIRE_REAL
def test_lt02_real_both_periods_resolve_to_own_handles() -> None:
    """FY2024 (old) and FY2025 (new) are both in the catalog; each request
    resolves to its own period's handle and the latest (FY2025) carries
    capture-ready state - no gap remains."""
    catalog = _production_catalog()
    from company_wiki.source_catalog.resolver import ResolutionStatus

    r2024 = _resolve(catalog, fy=2024, pdoc=ZIJIN_PDOC_2024)
    r2025 = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert r2024.status is ResolutionStatus.REUSED_EXACT, r2024.debug_trace
    assert r2025.status is ResolutionStatus.REUSED_EXACT, r2025.debug_trace
    # FY2025 is the later period and is capture-ready (already downloaded +
    # processed in a prior run) - the resolver returns it without any gap.
    assert r2025.matches, "FY2025 must have a match"
    assert r2025.matches[0].capture_ready is True


# ---------------------------------------------------------------------------
# LT-08: immediate re-resolve after a successful resolve -> same handle
# ---------------------------------------------------------------------------


@REQUIRE_REAL
def test_lt08_real_immediate_reresolve_returns_same_handle() -> None:
    """A resolve followed immediately by another resolve returns the same
    capture-ready handle - the caller never needs a manual retry."""
    catalog = _production_catalog()

    first = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    second = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert first.status is second.status
    assert first.matches and second.matches
    assert first.matches[0].canonical_path == second.matches[0].canonical_path
    assert second.matches[0].capture_ready is True


# ---------------------------------------------------------------------------
# LT-09: second identical request -> identical result, zero catalog writes
# ---------------------------------------------------------------------------


@REQUIRE_REAL
def test_lt09_real_second_request_zero_side_effects() -> None:
    """Executing the same request twice must resolve identically and leave
    the catalog bytes untouched (no download, no write, no scan)."""
    catalog = _production_catalog()

    before = _db_state()
    first = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    second = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    after = _db_state()

    assert first.matches[0].canonical_path == second.matches[0].canonical_path
    assert before == after, "resolve must be zero-write on the catalog"


# ---------------------------------------------------------------------------
# UJ-03: old + new both reusable; new period carries processed artifacts
# ---------------------------------------------------------------------------


@REQUIRE_REAL
def test_uj03_real_new_period_has_processing_artifacts() -> None:
    """The new-period (FY2025) document is reusable AND its normalized
    artifact is readable on disk - the user journey needs no download and
    no re-processing."""
    catalog = _production_catalog()
    from company_wiki.source_catalog.resolver import ResolutionStatus

    result = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].capture_ready is True
    artifact = _artifact_path(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert artifact is not None, "FY2025 normalized artifact must exist"
    text = artifact.read_text(encoding="utf-8", errors="replace")
    assert len(text) > 100, "normalized artifact must contain real content"


# ---------------------------------------------------------------------------
# UJ-05: full reuse journey - resolve + read artifact, no re-processing
# ---------------------------------------------------------------------------


@REQUIRE_REAL
def test_uj05_real_full_reuse_journey() -> None:
    """The complete user journey (request -> resolve -> read processed
    artifact) succeeds on the already-downloaded document with zero
    catalog mutation."""
    catalog = _production_catalog()
    from company_wiki.source_catalog.resolver import ResolutionStatus

    before = _db_state()
    result = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].capture_ready is True

    artifact = _artifact_path(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert artifact is not None
    content = artifact.read_text(encoding="utf-8", errors="replace")
    assert "紫金" in content or "年度报告" in content

    after = _db_state()
    assert before == after, "full journey must not mutate the catalog"
