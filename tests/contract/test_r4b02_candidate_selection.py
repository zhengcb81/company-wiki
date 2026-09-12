"""R4 phase-B step B02 acceptance: same-version candidate selection.

B02 makes "which copy of the requested version do we reuse" a four-segment
decision — (1) root registration/capability, (2) status and safety, (3)
locally readable bytes, (4) preference order — where segments 1-2 decide
*qualification* and segment 4 may only decide *which qualified copy is tried
first*.  Before B02 the canonical location was elected by priority alone and
the resolver then discarded it if it was unhealthy or rejected, so a document
with a perfectly good second copy could be reported as missing (and trigger a
re-download).

Acceptance covered here (see assurance/.../test-acceptance-map.md):

  L01/L02  four roots, identical bytes, one document: the canonical copy is
           elected inside the QUALIFIED set; config (root) order changes
           nothing.
  L03      withdrawal fall-through: the preferred copy disappears -> the same
           version is served from the next qualified copy, the reference
           (document id + content hash) is unchanged and no download is
           requested; all copies gone -> unavailable with no reuse.
  L04      provider-rejected (.rejections) paths are excluded BEFORE ordering,
           even when they hold the best priority and their document row was
           forced back to active.
  budget   B02 read budget/cancellation: finite candidate/byte ceilings,
           cancellation never reads a byte, and neither is ever silent.
  no-net   a candidate whose bytes are not local (cloud placeholder) is
           refused without reading it: the query path performs no network I/O.

Scope note (B02): byte-equality with the claimed ``content_sha256`` is a
PREFERENCE plus per-candidate diagnostics here, not the hard gate — the
byte-level refusal belongs to the read path (B03: serve verified bytes or fail
explicitly), and the A-side frozen fixtures (determinism / sql pushdown) build
catalogs whose files deliberately do not contain the bytes their metadata
claims, so a hard gate inside ``resolve`` would contradict those assertions.
What B02 guarantees is that a candidate is never *silently* unverified: the
selection reason and the per-candidate reasons are in the debug trace.

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import types
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    _CANDIDATE_BYTES_CAP,
    _REQUEST_MAX_BYTES,
    _REQUEST_MAX_CANDIDATES,
    _ReadBudget,
    _needs_hydration,
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)

BODY = b"%PDF-1.4 r4b02-same-version"
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


def _write_copy(directory: Path, name: str = "2025.pdf") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_SIDECAR, ensure_ascii=False), encoding="utf-8"
    )


def _three_copy_fixture(tmp_path: Path) -> dict[str, Path]:
    """The SAME bytes in three roots (company_raw p10 / dropbox p30 /
    future_lake p40), each with a complete sidecar identity."""
    companies = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    dropbox = tmp_path / "Dropbox" / "Stock"
    future = tmp_path / "future_lake"
    _write_copy(companies)
    _write_copy(dropbox)
    _write_copy(future)
    return {"companies": companies, "dropbox": dropbox, "future_lake": future}


def _roots(paths: dict[str, Path], *, companies_p: int = 10, dropbox_p: int = 30,
           future_p: int = 40) -> list[RootSpec]:
    return [
        RootSpec(
            "company_raw",
            paths["companies"].parents[3],
            "company_raw",
            priority=companies_p,
            adapter_id="company_raw_v1",
            read_only=False,
            reusable_for_filing=True,
            canonical_write_target="companies",
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
            reusable_root_kinds=("company_raw", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _force_active(catalog) -> None:
    """The scanner quarantines .rejections groups; force the document row
    back to active to construct the leak scenario (same technique as the
    fail-closed / ZR-403 suites)."""
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='active'")
    con.commit()
    con.close()


def _request() -> SourceRequest:
    return SourceRequest(
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


def _resolve(catalog, resolver: SourceResolver | None = None):
    return (resolver or SourceResolver(catalog)).resolve(_request())


def _locations(catalog) -> list[sqlite3.Row]:
    return list(
        catalog.store.fetchall(
            """SELECT location_id, root_id, relative_path, absolute_path,
                      location_status, document_id, source_id, role
               FROM locations ORDER BY root_id, location_id"""
        )
    )


# ---------------------------------------------------------------------------
# L01/L02 — canonical is elected inside the qualified set
# ---------------------------------------------------------------------------


def test_r4b02_l01_canonical_prefers_lowest_priority_qualified_copy(tmp_path):
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    handle = result.matches[0]
    assert handle.content_sha256 == DIGEST
    assert "companies" in handle.canonical_path.replace("\\", "/")
    assert handle.exact_duplicate_location_count == 2
    assert result.download_required is False


def test_r4b02_l02_root_config_order_cannot_change_the_winner(tmp_path):
    """Segment 4 ordering is a total order on (priority, root id, relative
    path, location id): permuting the root CONFIG order must not move the
    canonical copy or the document identity."""
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    paths_a = _three_copy_fixture(first)
    paths_b = _three_copy_fixture(second)
    catalog_a = _scan(first, _roots(paths_a))
    catalog_b = _scan(second, list(reversed(_roots(paths_b))))
    handle_a = _resolve(catalog_a).matches[0]
    handle_b = _resolve(catalog_b).matches[0]
    assert handle_a.canonical_location_id == handle_b.canonical_location_id
    assert Path(handle_a.canonical_path).name == Path(handle_b.canonical_path).name
    assert handle_a.document_id == handle_b.document_id
    assert handle_a.content_sha256 == handle_b.content_sha256 == DIGEST


# ---------------------------------------------------------------------------
# L03 — withdrawal fall-through (the defect B02 fixes)
# ---------------------------------------------------------------------------


def test_r4b02_l03_withdrawn_preferred_copy_falls_through_to_equivalent(tmp_path):
    """Delete the preferred copy: the SAME version must still be reused from
    the next qualified copy — same document id and same content hash, no
    download, and the canonical path moves."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    before = _resolve(catalog).matches[0]
    preferred = Path(before.canonical_path)
    assert "companies" in preferred.as_posix()
    preferred.unlink()

    after = _resolve(catalog)
    assert after.status is ResolutionStatus.REUSED_EXACT, after.debug_trace
    handle = after.matches[0]
    assert handle.document_id == before.document_id
    assert handle.content_sha256 == before.content_sha256 == DIGEST
    assert handle.canonical_path != before.canonical_path
    assert "companies" not in handle.canonical_path.replace("\\", "/")
    assert after.download_required is False
    assert any(
        "verified_candidate_rank_2" in item or "verified_candidate_rank" in item
        for item in after.debug_trace
    ), after.debug_trace


def test_r4b02_l03_all_copies_gone_is_unavailable_without_reuse(tmp_path):
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    for row in _locations(catalog):
        candidate_file = Path(row["absolute_path"])
        if row["role"] == "original_primary" and candidate_file.is_file():
            candidate_file.unlink()
    result = _resolve(catalog)
    assert result.matches == (), result.debug_trace
    assert result.status is ResolutionStatus.MISSING, result.debug_trace
    # "unavailable" for reuse: the request needs a source, and resolve itself
    # never authorizes the download (`request.allow_download` stays False).
    assert result.download_required is True
    assert result.download_allowed is False
    assert any("not_readable" in item for item in result.debug_trace), (
        result.debug_trace
    )


# ---------------------------------------------------------------------------
# L04 — safety decisions happen BEFORE ordering
# ---------------------------------------------------------------------------


def test_r4b02_l04_rejected_copy_with_best_priority_is_not_a_candidate(tmp_path):
    """The .rejections copy holds the BEST priority (p10) and the document row
    is forced active: it must be excluded by segment 2 (rank 0, reason
    rejections_path) and the healthy copy must serve the handle.  Pre-B02 the
    rejected row won the election on priority and the whole document fell
    through to MISSING."""
    company_root = tmp_path / "companies"
    rejected = company_root / "Acme" / "raw" / "financial_reports" / ".rejections"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(rejected)
    _write_copy(dropbox)
    catalog = _scan(
        tmp_path,
        [
            RootSpec(
                "company_raw",
                company_root,
                "company_raw",
                priority=10,
                adapter_id="company_raw_v1",
                read_only=False,
                reusable_for_filing=True,
                canonical_write_target="companies",
            ),
            RootSpec(
                "dropbox_stock",
                dropbox,
                "directory",
                priority=30,
                adapter_id="sidecar_filing_v1",
                read_only=True,
                reusable_for_filing=True,
            ),
        ],
    )
    _force_active(catalog)

    rejected_rows = [
        row
        for row in _locations(catalog)
        if ".rejections" in row["relative_path"].replace("\\", "/")
    ]
    assert rejected_rows, _locations(catalog)

    service = _service(catalog)
    candidates = service.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",)
    )
    assert len(candidates) == 1, candidates
    by_path = {
        item["relative_path"].replace("\\", "/"): item
        for item in candidates[0]["locations"]
    }
    rejected_key = next(key for key in by_path if ".rejections" in key)
    rejected = by_path[rejected_key]
    assert rejected["candidate_rank"] == 0, rejected
    assert rejected["exclusion_reason"] == "rejections_path", rejected
    assert rejected["is_canonical"] is False
    healthy = [item for item in candidates[0]["locations"] if item["candidate_rank"]]
    assert healthy and all(item["candidate_rank"] == 1 for item in healthy)
    assert candidates[0]["exact_duplicate_location_count"] == 0
    assert candidates[0]["exact_original_copy_count"] == len(healthy)

    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    handle = result.matches[0]
    assert ".rejections" not in handle.canonical_path.replace("\\", "/")
    assert "Stock" in handle.canonical_path.replace("\\", "/")


def test_r4b02_l04_unhealthy_copy_loses_to_healthier_lower_priority(tmp_path):
    """Same rule for a non-active copy: a retired best-priority location is
    not a candidate, so the healthy copy wins instead of the document being
    dropped."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE locations SET location_status='retired' WHERE root_id='company_raw'")
    con.commit()
    con.close()
    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert "companies" not in result.matches[0].canonical_path.replace("\\", "/")
    assert result.matches[0].exact_duplicate_location_count == 1


def _service(catalog):
    from company_wiki.source_catalog.service import SourceCatalog as Service

    return Service(catalog.config)


# ---------------------------------------------------------------------------
# B02 budget and cancellation (L06/L12)
# ---------------------------------------------------------------------------


def test_r4b02_budget_counters_bound_candidate_reads(tmp_path):
    """A one-byte ceiling stops the read BEFORE any byte is read; the request
    keeps its documented reuse decision and says so in the trace (never a
    silent unverified reuse)."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    budget = _ReadBudget(max_candidates=4, max_bytes=1)
    resolver = SourceResolver(catalog, read_budget=budget)
    result = resolver.resolve(_request())
    assert budget.bytes_read == 0, budget
    assert budget.candidates == 1, budget
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert any("budget_exceeded" in item for item in result.debug_trace), (
        result.debug_trace
    )
    assert any("unverified_bytes" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_budget_default_ceilings_are_finite(tmp_path):
    """The documented defaults stay finite and identical to the design."""
    budget = _ReadBudget()
    assert budget.max_candidates == _REQUEST_MAX_CANDIDATES == 64
    assert budget.max_bytes == _REQUEST_MAX_BYTES == 2 * 1024 * 1024 * 1024
    assert _CANDIDATE_BYTES_CAP == 256 * 1024 * 1024
    assert budget.cancelled is False and budget.bytes_read == 0


def test_r4b02_cancellation_reads_no_byte_and_returns_no_handle(tmp_path):
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    budget = _ReadBudget()
    budget.cancel()
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert budget.bytes_read == 0, budget
    assert result.matches == (), result.debug_trace
    assert any(
        "candidate_verification_cancelled" in item for item in result.debug_trace
    ), result.debug_trace


def test_r4b02_verified_copy_is_read_once_per_candidate(tmp_path):
    """A successful verification charges exactly one candidate and the size of
    the file it read — the counters are the evidence L06 asks for."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    budget = _ReadBudget(max_candidates=10, max_bytes=10 * len(BODY))
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert budget.candidates == 1, budget
    assert budget.bytes_read == len(BODY), budget


# ---------------------------------------------------------------------------
# No network in the query path (B-DR-08): placeholders are refused unread
# ---------------------------------------------------------------------------


def test_r4b02_placeholder_attributes_are_detected_without_reading():
    """`stat` reports the Windows cloud-placeholder attributes; the helper
    must read that flag (0x400000 | 0x1000) and nothing else."""
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0)) is False
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x80)) is False
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x400000)) is True
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x1000)) is True


def test_r4b02_cloud_placeholder_candidate_is_not_read(tmp_path, monkeypatch):
    """A candidate whose bytes are not local is refused as `hydration_required`
    with ZERO bytes read; the equivalent local copy serves the handle."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    placeholder = paths["companies"] / "2025.pdf"
    real_stat = Path.stat
    real_result = real_stat(placeholder)

    def stat_with_placeholder_attribute(self, *args, **kwargs):
        result = real_stat(self, *args, **kwargs)
        if Path(self) == placeholder:
            return types.SimpleNamespace(
                st_size=real_result.st_size,
                st_mode=real_result.st_mode,
                st_file_attributes=0x400000,
            )
        return result

    monkeypatch.setattr(Path, "stat", stat_with_placeholder_attribute, raising=True)
    budget = _ReadBudget()
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert budget.bytes_read == len(BODY), budget
    assert "companies" not in result.matches[0].canonical_path.replace("\\", "/")
    assert any("hydration_required" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_only_placeholder_copy_is_unavailable(tmp_path, monkeypatch):
    """No local bytes anywhere => unavailable, and the reason is named."""
    company_root = tmp_path / "companies"
    only = company_root / "Acme" / "raw" / "financial_reports" / "annual"
    _write_copy(only)
    catalog = _scan(
        tmp_path,
        [
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
        ],
    )
    placeholder = only / "2025.pdf"
    real_stat = Path.stat
    real_result = real_stat(placeholder)

    def stat_with_placeholder_attribute(self, *args, **kwargs):
        result = real_stat(self, *args, **kwargs)
        if Path(self) == placeholder:
            return types.SimpleNamespace(
                st_size=real_result.st_size,
                st_mode=real_result.st_mode,
                st_file_attributes=0x1000,
            )
        return result

    monkeypatch.setattr(Path, "stat", stat_with_placeholder_attribute, raising=True)
    budget = _ReadBudget()
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert result.matches == (), result.debug_trace
    assert budget.bytes_read == 0, budget
    assert any("hydration_required" in item for item in result.debug_trace), (
        result.debug_trace
    )


# ---------------------------------------------------------------------------
# S-7 guard: the complexity ratchet table itself is frozen
# ---------------------------------------------------------------------------


def test_r4b02_complexity_ratchet_table_is_not_edited() -> None:
    """S-7: B may not raise a ratchet ceiling.  B02 keeps the two changed
    files inside their frozen values instead of editing the table."""
    import importlib.util

    ratchet_path = Path(__file__).with_name("test_fc1204_complexity_ratchet.py")
    spec = importlib.util.spec_from_file_location("_r4b02_ratchet", ratchet_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.FROZEN_MAX["service.py"] == 45
    assert module.FROZEN_MAX["resolver.py"] == 103


def test_r4b02_no_new_source_catalog_module_was_added() -> None:
    """S-7/work-package scope: B02 changes F1+F2 only — a new product module
    would need its own work package."""
    source_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "company_wiki"
        / "source_catalog"
    )
    assert not (source_dir / "location_candidates.py").exists()
    assert not (source_dir / "candidate_selection.py").exists()
    assert os.path.isdir(source_dir)


def test_r4b02_selection_objects_are_frozen_evidence() -> None:
    """The selection type is a small frozen record (which copy + why)."""
    from company_wiki.source_catalog.resolver import _Selection

    selection = _Selection(handle=None, reason="placeholder_no_handle")
    assert selection.tried == ()
    with pytest.raises(Exception):
        selection.reason = "other"  # type: ignore[misc]
