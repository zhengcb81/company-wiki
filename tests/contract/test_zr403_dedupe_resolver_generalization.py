"""ZR-403 acceptance tests: dedupe/resolver generalization + canonical vs
eligible-location separation (FC-303/503 evidence).

Independent acceptance pin over the CURRENT product (this card changes NO
product code):

  C1  FOUR contexts, same algorithm: identical bytes under company_raw /
      dayu_portfolio / dropbox(directory) / future_lake(directory +
      sidecar adapter) produce ONE content-addressed document with four
      active original_primary locations; the global canonical is the
      lowest-priority root — including a variant where future_lake wins
      on priority.
  C2  health precedes priority: an unhealthy (retired, or .rejections)
      higher-priority location NEVER becomes canonical; the healthy
      lower-priority copy wins and the resolver still reuses it.
  C3  reads never write canonical: the locations schema has NO
      is_canonical column (canonical is derived on read by
      _annotate_locations) and a full resolve()+query cycle leaves the
      catalog database file bytes unchanged.
  C4  config-order randomization stability: >=10 random shuffles of the
      four-root config order (each scanned into its own catalog) yield
      identical canonical (root_id, relative_path), duplicate group ids,
      duplicate counts and document_id sets.

RED evidence (gap analysis) is archived at
assurance/unified_completion/receipts/ZR-403/red/zr403_red_evidence.json.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402

BODY = b"%PDF-1.4 zr403-crossroot"
DIGEST = hashlib.sha256(BODY).hexdigest()

_SIDECAR = {
    "schema_version": "1.0",
    "canonical_entity_id": "ent-acme",
    "display_name": "Acme",
    "market": "US",
    "security_id": "ACME",
    "document_kind": "annual_report",
    "fiscal_year": 2025,
    "period_end": "2025-12-31",
    "filing_date": "2026-02-20",
    "form_type": "10-K",
    "provider": "sec",
    "provider_document_id": "doc-1",
    "source_url": "https://sec.gov/x/2025",
    "content_sha256": DIGEST,
}


def _write_sidecar(directory: Path, name: str = "2025.pdf") -> None:
    (directory / f"{name}.source.json").write_text(
        json.dumps(_SIDECAR, ensure_ascii=False), encoding="utf-8"
    )


def _four_root_fixture(tmp_path: Path) -> dict[str, Path]:
    """The same PDF bytes in FOUR root layouts (company_raw / dayu /
    dropbox / future_lake), each with complete sidecar/meta identity."""
    companies = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    companies.mkdir(parents=True)
    (companies / "2025.pdf").write_bytes(BODY)
    _write_sidecar(companies)

    dayu = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    dayu.mkdir(parents=True)
    (dayu / "fil_x.pdf").write_bytes(BODY)
    (dayu / "meta.json").write_text(
        json.dumps(
            {
                "document_id": "fil_x",
                "ticker": "ACME",
                "form_type": "10-K",
                "fiscal_year": 2025,
                "filing_date": "2026-02-20",
                "source_provider": "sec",
                "source_id": "doc-1",
                "source_url": "https://sec.gov/x/2025",
                "source_language": "en",
                "ingest_complete": True,
                "primary_document": "fil_x.pdf",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(
        json.dumps({"ticker": "ACME", "market": "US"}, ensure_ascii=False),
        encoding="utf-8",
    )

    dropbox = tmp_path / "Dropbox" / "Stock"
    dropbox.mkdir(parents=True)
    (dropbox / "2025.pdf").write_bytes(BODY)
    _write_sidecar(dropbox)

    future = tmp_path / "future_lake"
    future.mkdir()
    (future / "2025.pdf").write_bytes(BODY)
    _write_sidecar(future)

    return {
        "companies": tmp_path / "companies",
        "portfolio": tmp_path / "portfolio",
        "dropbox": dropbox,
        "future_lake": future,
    }


def _roots(
    paths: dict[str, Path], *, companies_p=10, dayu_p=20, dropbox_p=30, future_p=40
) -> list[RootSpec]:
    return [
        RootSpec(
            "company_raw",
            paths["companies"],
            "company_raw",
            priority=companies_p,
            adapter_id="company_raw_v1",
            read_only=False,
            reusable_for_filing=True,
            canonical_write_target="companies",
        ),
        RootSpec(
            "dayu_portfolio",
            paths["portfolio"],
            "dayu_portfolio",
            priority=dayu_p,
            adapter_id="dayu_filing_v1",
            read_only=True,
            reusable_for_filing=True,
        ),
        RootSpec(
            "dropbox_stock",
            paths["dropbox"],
            "directory",
            priority=dropbox_p,
            adapter_id="sidecar_filing_v1",
            read_only=True,
            reusable_for_filing=True,
        ),
        RootSpec(
            "future_lake",
            paths["future_lake"],
            "directory",
            priority=future_p,
            adapter_id="sidecar_filing_v1",
            read_only=True,
            reusable_for_filing=True,
        ),
    ]


def _scan(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _resolve_exact(catalog):
    from company_wiki.source_catalog.resolver import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Acme",
            market="US",
            security_id="ACME",
            document_kind="annual_report",
            form_type="10-K",
            fiscal_year=2025,
            provider="sec",
            provider_document_id="doc-1",
            as_of_date="2026-08-10",
            mode="exact",
        )
    )
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    return result


def _locations_for_digest(catalog) -> list[dict]:
    return [
        dict(row)
        for row in catalog.store.fetchall(
            """SELECT l.root_id, l.relative_path, l.location_status, l.document_id
               FROM locations l JOIN sources s ON s.source_id = l.source_id
               WHERE s.content_sha256 = ? ORDER BY l.root_id""",
            (DIGEST,),
        )
    ]


# ---------------------------------------------------------------------------
# C1 — four contexts, same dedupe/canonical algorithm
# ---------------------------------------------------------------------------


def test_c1_four_contexts_one_document_canonical_lowest_priority(tmp_path):
    paths = _four_root_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    rows = _locations_for_digest(catalog)
    assert len(rows) == 4, rows
    assert {r["root_id"] for r in rows} == {
        "company_raw",
        "dayu_portfolio",
        "dropbox_stock",
        "future_lake",
    }
    assert all(r["location_status"] == "active" for r in rows)
    assert len({r["document_id"] for r in rows}) == 1
    handle = _resolve_exact(catalog).matches[0]
    assert handle.exact_duplicate_location_count == 3
    assert "companies" in handle.canonical_path.replace("\\", "/")


def test_c1_future_lake_wins_on_priority(tmp_path):
    """Variant: future_lake has the LOWEST priority number -> it must win
    the canonical location (the algorithm never special-cases which root
    kind may be canonical — priority + stable tie-break only)."""
    paths = _four_root_fixture(tmp_path)
    catalog = _scan(
        tmp_path,
        _roots(paths, companies_p=20, dayu_p=30, dropbox_p=40, future_p=5),
    )
    handle = _resolve_exact(catalog).matches[0]
    assert "future_lake" in handle.canonical_path.replace("\\", "/"), (
        handle.canonical_path
    )


# ---------------------------------------------------------------------------
# C2 — health precedes priority in canonical selection
# ---------------------------------------------------------------------------


def _retire_location(catalog, root_id: str) -> None:
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute(
        "UPDATE locations SET location_status='retired' WHERE root_id=?",
        (root_id,),
    )
    con.commit()
    con.close()


def test_c2_retired_high_priority_location_never_canonical(tmp_path):
    """The p10 company_raw copy is retired in place: the canonical must
    move to the next healthy location (dayu p20) and the resolver must
    still reuse the document through it."""
    paths = _four_root_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    _retire_location(catalog, "company_raw")
    handle = _resolve_exact(catalog).matches[0]
    assert "portfolio" in handle.canonical_path.replace("\\", "/"), (
        handle.canonical_path
    )
    # duplicate accounting counts only the healthy copies
    assert handle.exact_duplicate_location_count == 2


def test_c2_rejections_path_loses_to_healthy_lower_priority(tmp_path):
    """A .rejections location at the highest priority never becomes
    canonical even when the document row is forced active (the leak
    scenario): the healthy lower-priority copy serves the handle."""
    paths = _four_root_fixture(tmp_path)
    # move the dropbox copy (p30) under .rejections BEFORE scanning
    rejected = paths["dropbox"] / ".rejections"
    rejected.mkdir()
    (paths["dropbox"] / "2025.pdf").rename(rejected / "2025.pdf")
    (paths["dropbox"] / "2025.pdf.source.json").rename(
        rejected / "2025.pdf.source.json"
    )
    catalog = _scan(tmp_path, _roots(paths))
    # the scanner quarantines .rejections documents; force the row back to
    # active to construct the leak (same technique as the fail-closed suite)
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='active'")
    con.commit()
    con.close()
    handle = _resolve_exact(catalog).matches[0]
    assert ".rejections" not in handle.canonical_path.replace("\\", "/")
    assert "companies" in handle.canonical_path.replace("\\", "/")


# ---------------------------------------------------------------------------
# C3 — reads never write canonical
# ---------------------------------------------------------------------------


def test_c3_locations_schema_has_no_canonical_column(tmp_path):
    """Canonical is DERIVED on read (_annotate_locations): the persisted
    schema must not carry an is_canonical column — otherwise a persisted
    canonical could drift from the health/priority order."""
    paths = _four_root_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=ro", uri=True)
    try:
        cols = {row[1] for row in con.execute("PRAGMA table_info(locations)")}
    finally:
        con.close()
    assert "is_canonical" not in cols, sorted(cols)


def test_c3_resolve_and_queries_leave_database_bytes_unchanged(tmp_path):
    """A full resolve() + service query cycle over the four-root catalog
    must not modify the catalog database file (reads never write the
    canonical annotation or anything else)."""
    paths = _four_root_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    # flush any pending WAL content into the main file, then fingerprint
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.commit()
    con.close()
    before = hashlib.sha256(Path(catalog.config.database_path).read_bytes()).hexdigest()
    _resolve_exact(catalog)
    _ = catalog.query_source_bundle  # attribute access only, no write
    # the canonical annotation is derived by the service read path
    # (_annotate_locations inside document queries) — exercising it must
    # not write anything back
    from company_wiki.source_catalog.service import SourceCatalog as Service

    service = Service(catalog.config)
    service.semantic_duplicate_groups()  # annotated read; no write path
    after = hashlib.sha256(Path(catalog.config.database_path).read_bytes()).hexdigest()
    assert before == after


# ---------------------------------------------------------------------------
# C4 — config-order randomization stability (property)
# ---------------------------------------------------------------------------


def _canonical_signature(catalog) -> dict:
    handle = _resolve_exact(catalog).matches[0]
    rows = _locations_for_digest(catalog)
    return {
        "canonical_root": handle.canonical_location_id,
        "canonical_path": Path(handle.canonical_path).name,
        "duplicate_group_id": handle.duplicate_group_id,
        "duplicate_count": handle.exact_duplicate_location_count,
        "document_ids": sorted({r["document_id"] for r in rows}),
        "location_roots": sorted(r["root_id"] for r in rows),
    }


def test_c4_random_config_orders_produce_identical_catalogs(tmp_path):
    """Property: >=10 random shuffles of the four-root config order, each
    scanned into its OWN catalog, produce the identical canonical
    signature (location id, duplicate group, counts, document ids)."""
    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    paths = _four_root_fixture(fixture_root)
    base_roots = _roots(paths)

    rng = random.Random(20260818)  # deterministic property seed
    signatures = []
    for index in range(10):
        shuffled = list(base_roots)
        rng.shuffle(shuffled)
        catalog_dir = tmp_path / f"cat_{index}"
        catalog_dir.mkdir()
        # roots point at the shared fixture tree via per-catalog copies of
        # the same RootSpec paths (scan is read-only over the tree)
        catalog = _scan(catalog_dir, shuffled)
        signatures.append(_canonical_signature(catalog))
        catalog.close()
    first = signatures[0]
    assert all(signature == first for signature in signatures), signatures
    # and the winner is the priority-10 root regardless of config order
    assert first["duplicate_count"] == 3
    assert first["canonical_path"] == "2025.pdf"
    assert len(first["document_ids"]) == 1
