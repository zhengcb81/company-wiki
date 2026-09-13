"""R4 phase-B step B04 acceptance: references survive a move.

B04's design rule (§B04): the *reference* to a filing is
``document_id`` + ``content_sha256`` (+ a locator hint); the absolute path and
the ``location_id`` are DIAGNOSTICS.  Moving a file produces a NEW location row
and marks the old one ``missing``, and resolution re-locates the same version
inside the qualified candidate set — so an existing reference keeps working
without re-downloading and without silently switching to another revision.

Acceptance covered here:

  L07  move within one root (+ rescan) -> the same version is still served:
       same document id / source id / content hash, no download requested,
       while the locator (relative path and location id) changed and the old
       location row is marked ``missing``.
  L07b locator layering: ``location_id`` is a pure function of
       ``(root_id, relative_path)`` (a locator hint), which is why it must not
       be treated as the reference.
  L03  negative: when every copy of the requested version is gone the answer is
       unavailable (no reuse), and a readable OTHER revision of the same period
       is not substituted for it.
  GAP  ``scanner.py``'s location upsert re-points the row when the same
       relative path now holds a different revision: the superseded revision
       loses its locator.  That file is outside this step's allowed set, so the
       behaviour is PINNED here and registered as a finding instead of fixed.

Matrix items: L03, L07 (phase-B acceptance map, reverse-coverage
section; step B04 claims these, and the cases below are what exercises them).

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)
from company_wiki.source_catalog.scanner import _location_id  # noqa: E402

BODY = b"%PDF-1.4 r4b04-reference-stability"
DIGEST = hashlib.sha256(BODY).hexdigest()
OTHER_BODY = b"%PDF-1.4 r4b04-other-revision"
OTHER_DIGEST = hashlib.sha256(OTHER_BODY).hexdigest()


def _sidecar(*, digest: str = DIGEST, provider_document_id: str = "doc-1") -> dict:
    return {
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
        "provider_document_id": provider_document_id,
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": digest,
    }


def _write_copy(
    directory: Path,
    name: str = "2025.pdf",
    *,
    body: bytes = BODY,
    digest: str = DIGEST,
    provider_document_id: str = "doc-1",
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(body)
    (directory / f"{name}.source.json").write_text(
        json.dumps(
            _sidecar(digest=digest, provider_document_id=provider_document_id),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _roots(company_root: Path) -> list[RootSpec]:
    return [
        RootSpec(
            "company_raw",
            company_root,
            "company_raw",
            priority=10,
            adapter_id="company_raw_v1",
            read_only=False,
            reusable_for_filing=True,
            canonical_write_target="companies",
        )
    ]


def _scan(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _request(*, provider_document_id: str = "doc-1") -> SourceRequest:
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id=provider_document_id,
        as_of_date="2026-08-10",
        mode="exact",
    )


def _resolve(catalog, *, provider_document_id: str = "doc-1"):
    return SourceResolver(catalog).resolve(
        _request(provider_document_id=provider_document_id)
    )


def _rows(catalog, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return [dict(row) for row in catalog.store.fetchall(sql, params)]


# ---------------------------------------------------------------------------
# L07 — a move must not break the reference
# ---------------------------------------------------------------------------


def test_r4b04_move_within_root_keeps_the_reference(tmp_path):
    """Move the file (both the PDF and its sidecar) to a new relative path,
    rescan, and require the SAME version to be served: same document id, same
    source id, same content hash, no download — with a different locator."""
    root = tmp_path / "companies"
    old_dir = root / "Acme" / "raw" / "financial_reports" / "annual"
    _write_copy(old_dir)
    catalog = _scan(tmp_path, _roots(root))

    before = _resolve(catalog)
    assert before.status is ResolutionStatus.REUSED_EXACT, before.debug_trace
    handle_before = before.matches[0]
    old_location = handle_before.canonical_location_id

    # the move: same root, same bytes, new relative path; the scanner marks the
    # old row `missing` on the next run
    new_dir = root / "Acme" / "raw" / "financial_reports" / "annual" / "renamed"
    new_dir.mkdir(parents=True, exist_ok=True)
    for name in ("2025.pdf", "2025.pdf.source.json"):
        (old_dir / name).rename(new_dir / name)
    catalog.scan()

    moved_rows = _rows(
        catalog,
        "SELECT relative_path, location_status, absolute_path FROM locations "
        "WHERE document_id=? ORDER BY relative_path",
        (handle_before.document_id,),
    )
    statuses = {row["relative_path"].replace("\\", "/"): row["location_status"]
                for row in moved_rows}
    assert statuses.get("Acme/raw/financial_reports/annual/2025.pdf") == "missing", statuses
    assert statuses.get("Acme/raw/financial_reports/annual/renamed/2025.pdf") == "active", statuses

    after = _resolve(catalog)
    assert after.status is ResolutionStatus.REUSED_EXACT, after.debug_trace
    handle_after = after.matches[0]
    # the reference is unchanged …
    assert handle_after.document_id == handle_before.document_id
    assert handle_after.source_id == handle_before.source_id
    assert handle_after.content_sha256 == handle_before.content_sha256 == DIGEST
    assert after.download_required is False
    # … while the locator (diagnostic) moved
    assert handle_after.canonical_location_id != old_location
    assert "renamed" in handle_after.canonical_path.replace("\\", "/")


def test_r4b04_location_id_is_a_pure_function_of_the_locator(tmp_path):
    """Layering (L07b): ``location_id`` derives from ``(root_id, relative_path)``
    — it is a locator hint, not the reference.  The stable identity is the
    document id plus the content hash, which is what a move preserves."""
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _scan(tmp_path, _roots(root))

    rows = _rows(
        catalog,
        "SELECT location_id, root_id, relative_path FROM locations "
        "WHERE root_id='company_raw' ORDER BY relative_path",
    )
    assert rows
    for row in rows:
        assert row["location_id"] == _location_id(row["root_id"], row["relative_path"])

    handle = _resolve(catalog).matches[0]
    assert handle.canonical_location_id in {row["location_id"] for row in rows}
    assert handle.document_id != handle.canonical_location_id
    assert handle.content_sha256 == DIGEST


# ---------------------------------------------------------------------------
# L03 — nothing of this version left: unavailable, and no other revision
# ---------------------------------------------------------------------------


def test_r4b04_version_gone_is_unavailable_not_the_other_revision(tmp_path):
    """Delete every copy of the requested version while a readable OTHER
    revision of the same period sits in the same tree: the answer must be
    unavailable with no match — a different revision is not a substitute."""
    root = tmp_path / "companies"
    annual = root / "Acme" / "raw" / "financial_reports" / "annual"
    _write_copy(annual)
    other_dir = root / "Acme" / "raw" / "financial_reports" / "annual" / "other"
    _write_copy(
        other_dir,
        "2025.pdf",
        body=OTHER_BODY,
        digest=OTHER_DIGEST,
        provider_document_id="doc-2",
    )
    catalog = _scan(tmp_path, _roots(root))

    first = _resolve(catalog)
    assert first.status is ResolutionStatus.REUSED_EXACT, first.debug_trace
    assert first.matches[0].content_sha256 == DIGEST

    for name in ("2025.pdf", "2025.pdf.source.json"):
        (annual / name).unlink()
    catalog.scan()

    after = _resolve(catalog)
    assert after.matches == (), after.debug_trace
    assert after.status is ResolutionStatus.MISSING, after.debug_trace
    # the other revision exists and is readable, but it is not this version
    other_rows = _rows(
        catalog,
        "SELECT location_status FROM locations WHERE relative_path LIKE ?",
        ("%other%",),
    )
    assert other_rows and any(row["location_status"] == "active" for row in other_rows), other_rows
    assert not any(
        OTHER_DIGEST == match.content_sha256 for match in after.matches
    ), after.matches


# ---------------------------------------------------------------------------
# GAP — the scanner's location upsert, pinned and registered (out of scope)
# ---------------------------------------------------------------------------


def test_r4b04_same_path_new_revision_repoints_the_location_row(tmp_path):
    """PINNED BEHAVIOUR (finding F-B04-1): overwriting the same relative path
    with a different revision re-points that location row to the new document
    (``scanner.py`` ON CONFLICT), so the superseded revision loses its locator
    and its reference can no longer be dereferenced.  ``scanner.py`` is outside
    this step's allowed set (file-scope F3 = metadata merge only), so this test
    documents the current behaviour rather than asserting a fix."""
    root = tmp_path / "companies"
    annual = root / "Acme" / "raw" / "financial_reports" / "annual"
    _write_copy(annual)
    catalog = _scan(tmp_path, _roots(root))

    superseded = _resolve(catalog)
    assert superseded.status is ResolutionStatus.REUSED_EXACT, superseded.debug_trace
    superseded_document = superseded.matches[0].document_id
    superseded_sha = superseded.matches[0].content_sha256

    # same path, new bytes, sidecar updated to the new revision
    _write_copy(
        annual,
        "2025.pdf",
        body=OTHER_BODY,
        digest=OTHER_DIGEST,
        provider_document_id="doc-2",
    )
    catalog.scan()

    row = _rows(
        catalog,
        "SELECT document_id, source_id, location_status FROM locations "
        "WHERE relative_path=?",
        ("Acme/raw/financial_reports/annual/2025.pdf",),
    )
    assert len(row) == 1, row
    assert row[0]["document_id"] != superseded_document, row
    assert row[0]["location_status"] == "active", row

    # the superseded revision now has no active location at all …
    superseded_locations = _rows(
        catalog,
        "SELECT location_status FROM locations WHERE document_id=?",
        (superseded_document,),
    )
    assert not any(
        item["location_status"] == "active" for item in superseded_locations
    ), superseded_locations

    # … so its reference can no longer be dereferenced, while the new revision
    # resolves normally
    gone = _resolve(catalog, provider_document_id="doc-1")
    assert gone.matches == (), gone.debug_trace
    assert gone.status is ResolutionStatus.MISSING, gone.debug_trace
    assert any(
        "no_canonical_active_location" in item for item in gone.debug_trace
    ), gone.debug_trace
    assert superseded_sha == DIGEST
    fresh = _resolve(catalog, provider_document_id="doc-2")
    assert fresh.status is ResolutionStatus.REUSED_EXACT, fresh.debug_trace
    assert fresh.matches[0].content_sha256 == OTHER_DIGEST
