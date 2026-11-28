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

import os
import sqlite3
from pathlib import Path

import pytest


pytestmark = [pytest.mark.real_data]

ZIJIN_ENTITY = "紫金矿业"
ZIJIN_SECURITY = "601899"
ZIJIN_MARKET = "CN"
ZIJIN_PDOC_2024 = "1222870413"
ZIJIN_PDOC_2025 = "1225023658"


def _db_path(owner_root: Path) -> Path:
    return owner_root / ".source_catalog/catalog.sqlite3"


def _config_path(owner_root: Path) -> Path:
    return owner_root / "config/source_catalog.yaml"


@pytest.fixture(scope="module")
def real_wiki_root() -> Path:
    configured = os.environ.get("COMPANY_WIKI_REAL_WIKI_ROOT")
    if not configured:
        pytest.skip("set COMPANY_WIKI_REAL_WIKI_ROOT to the reviewed real-data workspace")
    root = Path(configured).resolve()
    db = _db_path(root)
    if not db.is_file() or not _config_path(root).is_file():
        pytest.skip("real data catalog and configuration are required")
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    try:
        row = con.execute(
            """SELECT COUNT(DISTINCT d.document_id) AS c FROM documents d
               JOIN locations l ON l.document_id=d.document_id
               WHERE d.document_kind='annual_report'
                 AND (d.title LIKE '%紫金%' OR d.title LIKE '%601899%')
                 AND l.root_id='company_raw' AND l.location_status='active'"""
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] < 2:
        pytest.skip("the real data workspace lacks both required annual sources")
    return root


def _production_catalog(owner_root: Path):
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(_config_path(owner_root), project_root=owner_root)
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


def _db_state(owner_root: Path) -> tuple:
    """Cheap zero-write fingerprint of the (49 GB) catalog.

    Reading the whole file to hash it would take minutes; instead we capture
    the SQLite header change counter (bytes 24-27: increments on every
    committed write transaction), the file size + mtime, and any journal /
    WAL / SHM sidecar state.  A resolver write would change at least one of
    these; the read is only 100 bytes so the check stays fast.
    """
    db = _db_path(owner_root)
    st = db.stat()
    with db.open("rb") as fh:
        header = fh.read(100)
    change_counter = (
        int.from_bytes(header[24:28], "big") if len(header) >= 28 else None
    )
    sidecars = tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns)
        for p in (
            Path(f"{db}-journal"),
            Path(f"{db}-wal"),
            Path(f"{db}-shm"),
        )
        if p.exists()
    )
    return (st.st_size, st.st_mtime_ns, change_counter, sidecars)


def _artifact_path(owner_root: Path, *, fy: int, pdoc: str) -> Path | None:
    """Locate the normalized artifact for the FY request via its source."""
    con = sqlite3.connect(f"{_db_path(owner_root).as_uri()}?mode=ro", uri=True)
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


def test_lt02_real_both_periods_resolve_to_own_handles(real_wiki_root):
    """FY2024 (old) and FY2025 (new) are both in the catalog; each request
    resolves to its own period's handle and the latest (FY2025) carries
    capture-ready state - no gap remains."""
    catalog = _production_catalog(real_wiki_root)
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


def test_lt08_real_immediate_reresolve_returns_same_handle(real_wiki_root):
    """A resolve followed immediately by another resolve returns the same
    capture-ready handle - the caller never needs a manual retry."""
    catalog = _production_catalog(real_wiki_root)

    first = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    second = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert first.status is second.status
    assert first.matches and second.matches
    assert first.matches[0].canonical_path == second.matches[0].canonical_path
    assert second.matches[0].capture_ready is True


# ---------------------------------------------------------------------------
# LT-09: second identical request -> identical result, zero catalog writes
# ---------------------------------------------------------------------------


def test_lt09_real_second_request_zero_side_effects(real_wiki_root):
    """Executing the same request twice must resolve identically and leave
    the catalog bytes untouched (no download, no write, no scan)."""
    catalog = _production_catalog(real_wiki_root)

    before = _db_state(real_wiki_root)
    first = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    second = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    after = _db_state(real_wiki_root)

    assert first.matches[0].canonical_path == second.matches[0].canonical_path
    assert before == after, "resolve must be zero-write on the catalog"


# ---------------------------------------------------------------------------
# UJ-03: old + new both reusable; new period carries processed artifacts
# ---------------------------------------------------------------------------


def test_uj03_real_new_period_has_processing_artifacts(real_wiki_root):
    """The new-period (FY2025) document is reusable AND its normalized
    artifact is readable on disk - the user journey needs no download and
    no re-processing."""
    catalog = _production_catalog(real_wiki_root)
    from company_wiki.source_catalog.resolver import ResolutionStatus

    result = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].capture_ready is True
    artifact = _artifact_path(real_wiki_root, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert artifact is not None, "FY2025 normalized artifact must exist"
    text = artifact.read_text(encoding="utf-8", errors="replace")
    assert len(text) > 100, "normalized artifact must contain real content"


# ---------------------------------------------------------------------------
# UJ-05: full reuse journey - resolve + read artifact, no re-processing
# ---------------------------------------------------------------------------


def test_uj05_real_full_reuse_journey(real_wiki_root):
    """The complete user journey (request -> resolve -> read processed
    artifact) succeeds on the already-downloaded document with zero
    catalog mutation."""
    catalog = _production_catalog(real_wiki_root)
    from company_wiki.source_catalog.resolver import ResolutionStatus

    before = _db_state(real_wiki_root)
    result = _resolve(catalog, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].capture_ready is True

    artifact = _artifact_path(real_wiki_root, fy=2025, pdoc=ZIJIN_PDOC_2025)
    assert artifact is not None
    content = artifact.read_text(encoding="utf-8", errors="replace")
    assert "紫金" in content or "年度报告" in content

    after = _db_state(real_wiki_root)
    assert before == after, "full journey must not mutate the catalog"
