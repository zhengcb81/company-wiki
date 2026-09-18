"""F-BAR-10 regression: a root that DECLARES an adapter must be scanned through it.

Measured defect (R3 mutation M5, 2026-09-18): with no `runtime_policy.json` the scan fell
back to the legacy directory walk for EVERY root, including a `directory` root that declares
`adapter_id: sidecar_filing_v1`.  The walk has no idea what a sidecar is, so it indexed
`.source.json` files as documents of their own - which is exactly the shape seen in the
production catalog (the `.pdf.source` documents of F-BAR-1) and in the leaf-mount probe
(F-B08-L2-2).

The fix is at the scan site: `use_adapter = v2_scan_shadow or root.adapter_id is not None`.
These tests therefore exercise the SCAN ENTRY POINT (`SourceCatalog.scan()`), not the
facade, and they assert the reported `ScanReport.strategy` so the dispatch is checked
directly instead of being inferred from the document set.

Both directions are pinned:
  * adapter-declared root, NO snapshot -> strategy "adapter", sidecar is NOT a document;
  * plain root, NO snapshot          -> strategy "legacy", sidecar IS a document (the
    legacy behaviour is preserved for roots that declare no adapter - this half is what
    keeps the fix from silently changing the v1/v2 cutover for the production roots).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from company_wiki.source_catalog import CatalogConfig, SourceCatalog
from company_wiki.source_catalog.models import RootSpec

SIDECAR = {
    "schema_version": "1.0",
    "canonical_entity_id": "ent-r4bar10",
    "display_name": "R4BAR10 Acme",
    "market": "US",
    "security_id": "R4BAR10",
    "document_kind": "annual_report",
    "fiscal_year": 2025,
    "period_end": "2025-12-31",
    "published_at": "2026-02-20",
    "form_type": "10-K",
    "provider": "sec",
    "provider_document_id": "r4bar10-doc-1",
    "source_url": "https://www.sec.gov/Archives/edgar/data/r4bar10/2025.htm",
    "language": "en",
}
BODY = b"%PDF-1.4\n% r4bar10 adapter-declared root fixture\n"


def _write_fixture(root_dir: Path) -> None:
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / "2025-annual.pdf").write_bytes(BODY)
    import hashlib

    payload = dict(SIDECAR)
    payload["content_sha256"] = hashlib.sha256(BODY).hexdigest()
    (root_dir / "2025-annual.pdf.source.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _scan(tmp_path: Path, *, declare_adapter: bool) -> tuple[SourceCatalog, dict]:
    """Scan one root in a FRESH temp project (no activation snapshot on purpose)."""
    root_dir = tmp_path / "roots" / "r4bar10_root"
    _write_fixture(root_dir)
    root = RootSpec(
        "r4bar10_root",
        root_dir,
        "directory",
        priority=10,
        adapter_id="sidecar_filing_v1" if declare_adapter else None,
        read_only=True,
        reusable_for_filing=True,
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=(root,),
        )
    )
    report = catalog.scan()
    # No snapshot was ever written - that is the condition the defect needed.
    assert not (tmp_path / ".source_catalog" / "runtime_policy.json").exists()
    connection = sqlite3.connect(f"file:{catalog.config.database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        documents = [dict(row) for row in connection.execute(
            "SELECT title,document_kind FROM documents ORDER BY title")]
        locations = [dict(row) for row in connection.execute(
            "SELECT relative_path,role FROM locations ORDER BY relative_path")]
    finally:
        connection.close()
    return catalog, {"report": report, "documents": documents, "locations": locations}


def test_adapter_declared_root_dispatches_without_a_snapshot(tmp_path: Path) -> None:
    """The declared adapter wins over the missing activation snapshot."""
    _catalog, observed = _scan(tmp_path, declare_adapter=True)
    report = observed["report"]
    assert dict(report.strategy) == {"r4bar10_root": "adapter"}, report.strategy
    titles = [row["title"] for row in observed["documents"]]
    assert titles == ["2025-annual"], titles
    assert not [row for row in observed["documents"]
                if row["title"].endswith(".source.json")], observed["documents"]
    assert [row["relative_path"] for row in observed["locations"]] == ["2025-annual.pdf"]
    assert observed["locations"][0]["role"] == "original_primary"


def test_plain_directory_root_still_uses_the_legacy_walk(tmp_path: Path) -> None:
    """Control: the fix must NOT touch roots that declare no adapter.

    Without an adapter and without a snapshot the legacy walk is still the reader - and it
    still indexes the sidecar as a document of its own.  That is the pre-existing behaviour
    this test PINS (not endorses): if a later change makes plain roots adapter-aware too, the
    cutover semantics of the production roots change and this test is where that shows up.
    """
    _catalog, observed = _scan(tmp_path, declare_adapter=False)
    report = observed["report"]
    assert dict(report.strategy) == {"r4bar10_root": "legacy"}, report.strategy
    titles = sorted(row["title"] for row in observed["documents"])
    assert titles == ["2025-annual", "2025-annual.pdf.source"], titles
