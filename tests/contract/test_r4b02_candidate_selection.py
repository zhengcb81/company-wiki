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

Scope note (B02, rev5): the serving rule is exactly two clauses, and the cases
below pin both:

  1. **a verified copy always wins** — the first candidate whose bytes really
     are the requested version is served, whatever its rank (so withdrawing or
     corrupting the preferred copy still yields the same version from another
     copy);
  2. only when NO candidate verifies may ONE row be served on the catalog's
     claim: the legacy ``is_canonical`` row among the qualified candidates of
     the document's own version.  It is never silent (the reason is
     ``unverified_<status>_on_pre_b02_canonical`` and the per-candidate reasons
     are in the debug trace).

Clause 2 is NOT equivalent to what pre-B02 served.  The authoritative list of
the deliberate differences — (a) ``.rejections`` matched as a path SEGMENT
instead of a substring (wider on names such as ``my.rejections_backup``),
(b) the election restricted to the document's own source group (conditionally;
stricter), (c) the row must additionally pass the local probe, so a cloud
placeholder is refused where pre-B02 only checked ``is_file()`` (stricter) — is
maintained in ONE place and must not be restated here:

  revenue-forecast/assurance/runs/2026-09-11_r4-phase-b/evidence/
      b02-implementation.md   section 3  (decision S-10)

A-side frozen fixtures (determinism / sql pushdown) build catalogs whose files
deliberately do not contain the bytes their metadata claims, which is why
clause 2 exists at all; clause 1 is a strict improvement over pre-B02.

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
    healthy = [item for item in candidates[0]["locations"] if item["candidate_rank"]]
    assert healthy and all(item["candidate_rank"] == 1 for item in healthy)
    # The LEGACY annotation contract is deliberately unchanged (B-VR02-02/-03):
    # the rejected copy is still part of the duplicate/cleanup view, so the
    # planner keeps offering it for reclaiming and no consumer loses its
    # invariant that every group has a canonical.
    assert candidates[0]["exact_original_copy_count"] == 2
    assert candidates[0]["exact_duplicate_location_count"] == 1
    assert rejected["is_canonical"] is True

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
    keeps the pre-B02 trust level for the PREFERRED copy and says so in the
    trace (never a silent unverified reuse)."""
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
    assert any(
        "unverified_budget_exceeded_on_pre_b02_canonical" in item
        for item in result.debug_trace
    ), result.debug_trace


def test_r4b02_verified_copy_wins_over_the_claim_trusted_one(tmp_path):
    """B-VR02R2-01 (P2): when the pre-B02 canonical's bytes have drifted but
    another copy of the SAME version still verifies, the verified copy must be
    served — the claim-trusted fallback may not short-circuit the walk."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    preferred = _resolve(catalog).matches[0]
    drifted = Path(preferred.canonical_path)
    assert "companies" in drifted.as_posix()
    drifted.write_bytes(BODY + b"# drifted after ingest")

    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    handle = result.matches[0]
    assert Path(handle.canonical_path) != drifted
    assert "companies" not in handle.canonical_path.replace("\\", "/")
    assert handle.content_sha256 == DIGEST
    assert any(
        item.startswith("2025: verified_candidate_rank_2:") for item in result.debug_trace
    ), result.debug_trace


def test_r4b02_rejected_best_priority_plus_drifted_copy_is_unavailable(tmp_path):
    """B-VR02R2-02 (P2): the pre-B02 canonical is the provider-rejected row, so
    pre-B02 answered MISSING.  With the surviving qualified copy's bytes
    drifted, rev2 may not answer with that copy either — the claim-trusted
    fallback is anchored to the row pre-B02 would have served."""
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
    (dropbox / "2025.pdf").write_bytes(BODY + b"# drifted after ingest")

    result = _resolve(catalog)
    assert result.matches == (), result.debug_trace
    assert result.status is ResolutionStatus.MISSING, result.debug_trace
    assert not any("unverified" in item for item in result.debug_trace), (
        result.debug_trace
    )
    assert any("content_sha256_mismatch" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_mid_read_cancellation_returns_no_handle(tmp_path, monkeypatch):
    """B-VR02R2-03 (P3): cancelling while the digest is being read must still
    revoke the answer."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    from company_wiki.source_catalog import resolver as resolver_module

    budget = _ReadBudget()
    real_sha256_of_file = resolver_module._sha256_of_file

    def cancel_then_hash(path):
        budget.cancel()
        return real_sha256_of_file(path)

    monkeypatch.setattr(resolver_module, "_sha256_of_file", cancel_then_hash)
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert budget.cancelled is True
    assert result.matches == (), result.debug_trace
    assert any(
        "candidate_verification_cancelled" in item for item in result.debug_trace
    ), result.debug_trace


def test_r4b02_other_source_group_is_never_served(tmp_path):
    """B-VR02R2-04 (P3): the candidate set is restricted to the document's own
    source entry.  A foreign source group attached to the same document must
    never be served — not even when every own copy is unusable."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    first = _resolve(catalog)
    assert first.status is ResolutionStatus.REUSED_EXACT, first.debug_trace
    own_source = first.matches[0].source_id
    foreign_source = "urn:company-wiki:source:sha256:" + "f" * 64

    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute(
        "INSERT OR IGNORE INTO sources(source_id,content_sha256,byte_size,mime_type,"
        "first_seen_at) VALUES(?,?,?,?,?)",
        (foreign_source, "f" * 64, len(BODY), "application/pdf", "2025-01-01"),
    )
    con.execute(
        "UPDATE locations SET source_id=? WHERE root_id='future_lake'", (foreign_source,)
    )
    con.commit()
    con.close()
    assert own_source != foreign_source

    # every own-source copy disappears; only the foreign group's copy is left
    for row in _locations(catalog):
        candidate_file = Path(row["absolute_path"])
        if row["role"] == "original_primary" and candidate_file.is_file():
            candidate_file.unlink()
    foreign = paths["future_lake"] / "2025.pdf"
    foreign.write_bytes(BODY)

    after = _resolve(catalog)
    assert after.matches == (), after.debug_trace
    assert after.status is ResolutionStatus.MISSING, after.debug_trace


def test_r4b02_injected_budget_is_per_request(tmp_path):
    """B-VR02-04: the ceilings are PER REQUEST.  Reusing one injected budget
    (or one resolver) must not silently un-verify the next request."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    budget = _ReadBudget(max_candidates=4, max_bytes=4 * len(BODY))
    resolver = SourceResolver(catalog, read_budget=budget)

    first = resolver.resolve(_request())
    assert first.status is ResolutionStatus.REUSED_EXACT, first.debug_trace
    assert budget.bytes_read == len(BODY), budget
    assert not any("unverified" in item for item in first.debug_trace)

    second = resolver.resolve(_request())
    assert second.status is ResolutionStatus.REUSED_EXACT, second.debug_trace
    assert budget.candidates == 1, budget
    assert budget.bytes_read == len(BODY), budget
    assert not any("unverified" in item for item in second.debug_trace), (
        second.debug_trace
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
# B-VR02-01/-02/-03 regressions: a non-preferred copy is never served
# unverified, and the legacy annotation contract is untouched
# ---------------------------------------------------------------------------


def test_r4b02_different_bytes_copy_is_never_served_as_the_same_version(tmp_path):
    """B-VR02-01 (P1): withdraw the preferred copy AND the third copy, then
    rewrite the surviving copy with DIFFERENT bytes.  The bytes are provably
    not the requested version, so the answer must be unavailable (no reuse, no
    download authorization) — exactly what pre-B02 did.  Serving it would be
    the "take another revision" that L03 forbids."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    before = _resolve(catalog).matches[0]
    preferred = Path(before.canonical_path)
    assert "companies" in preferred.as_posix()
    preferred.unlink()
    third = paths["future_lake"] / "2025.pdf"
    third.unlink()
    survivor = paths["dropbox"] / "2025.pdf"
    survivor.write_bytes(BODY + b"# a different revision")

    result = _resolve(catalog)
    assert result.matches == (), result.debug_trace
    assert result.status is ResolutionStatus.MISSING, result.debug_trace
    assert result.download_required is True
    assert not any("unverified" in item for item in result.debug_trace), (
        result.debug_trace
    )
    assert any("content_sha256_mismatch" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_rejected_only_document_still_lists_for_cleanup(tmp_path):
    """B-VR02-02 (P1): two provider-rejected copies of one document (the
    scanner's own layout) must not break the duplicate-cleanup listing.  The
    legacy annotation contract keeps electing a canonical over the group's
    active originals, so `list_groups()` cannot hit StopIteration."""
    from company_wiki.source_catalog.duplicate_cleanup import DuplicateCleanupService

    company_root = tmp_path / "companies"
    rejected_a = company_root / "Acme" / "raw" / "financial_reports" / ".rejections" / "123"
    rejected_b = company_root / "Acme" / "raw" / "financial_reports" / ".rejections" / "456"
    _write_copy(rejected_a)
    _write_copy(rejected_b)
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
    _force_active(catalog)

    service = _service(catalog)
    candidates = service.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",)
    )
    assert len(candidates) == 1, candidates
    assert all(item["candidate_rank"] == 0 for item in candidates[0]["locations"])
    assert [item for item in candidates[0]["locations"] if item["is_canonical"]]

    groups = DuplicateCleanupService(catalog).list_groups()
    assert groups["total_groups"] >= 1, groups
    assert groups["total_reclaimable_copies"] >= 1, groups
    assert all(group["copy_count"] >= 2 for group in groups["groups"]), groups

    # and no reuse: a rejected path is never a reusable candidate (L04)
    result = _resolve(catalog)
    assert result.matches == (), result.debug_trace
    assert any("rejections_path" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_rejected_copy_stays_reclaimable_next_to_healthy_copies(tmp_path):
    """B-VR02-03 (P2): with a rejected copy at the BEST priority plus two
    healthy copies, the cleanup planner must still offer the rejected copy
    (the operator's reclaim target) — pre-B02 it offered three copies."""
    from company_wiki.source_catalog.duplicate_cleanup import DuplicateCleanupService

    company_root = tmp_path / "companies"
    rejected = company_root / "Acme" / "raw" / "financial_reports" / ".rejections"
    dropbox = tmp_path / "Dropbox" / "Stock"
    future = tmp_path / "future_lake"
    _write_copy(rejected)
    _write_copy(dropbox)
    _write_copy(future)
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
            RootSpec(
                "future_lake",
                future,
                "directory",
                priority=40,
                adapter_id="sidecar_filing_v1",
                read_only=True,
                reusable_for_filing=True,
            ),
        ],
    )
    _force_active(catalog)

    groups = DuplicateCleanupService(catalog).list_groups()
    # pre-B02 measurement (B-VR02-03): 3 reclaimable copies over 2 groups, and
    # the rejected copy is one of the rows the planner knows about.
    assert groups["total_groups"] == 2, groups
    assert groups["total_reclaimable_copies"] == 3, groups
    listed_paths = [
        item["relative_path"]
        for group in groups["groups"]
        for item in (group["canonical"], *group["duplicates"])
    ]
    assert any(
        ".rejections" in path.replace("\\", "/") for path in listed_paths
    ), listed_paths


# ---------------------------------------------------------------------------
# B-VR02-04/-05/-07 regressions: budget reset, unambiguous reasons, matching
# ---------------------------------------------------------------------------


def test_r4b02_selection_reason_names_the_source_group(tmp_path):
    """B-VR02-05: a bare rank is ambiguous, and `tried` must be emitted
    whenever it is non-empty."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    trace = list(result.debug_trace)
    assert "2025: matched" in trace
    # the ordinary case (preferred copy, nothing tried) keeps the legacy shape
    assert not any("verified_candidate_rank" in item for item in trace), trace

    preferred = Path(result.matches[0].canonical_path)
    preferred.unlink()
    fallthrough = _resolve(catalog)
    trace = list(fallthrough.debug_trace)
    assert any(
        item.startswith("2025: verified_candidate_rank_2:") for item in trace
    ), trace
    assert any("2025: candidate " in item for item in trace), trace


def test_r4b02_rejections_is_matched_as_a_path_segment() -> None:
    """B-VR02-07: a substring match disqualified unrelated names."""
    from company_wiki.source_catalog.service import _location_exclusion_reason

    def location(relative_path: str) -> dict:
        return {
            "role": "original_primary",
            "location_status": "active",
            "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
            "relative_path": relative_path,
        }

    assert _location_exclusion_reason(location("annual/my.rejections_backup/2025.pdf")) == ""
    assert (
        _location_exclusion_reason(location("annual/my.rejections_backup/2025.pdf"))
        != "rejections_path"
    )
    assert (
        _location_exclusion_reason(location("Acme/raw/.rejections/2025.pdf"))
        == "rejections_path"
    )
    assert (
        _location_exclusion_reason(location(r"Acme\raw\.rejections\2025.pdf"))
        == "rejections_path"
    )


def test_r4b02_recall_on_open_placeholders_are_detected() -> None:
    """B-VR02-07: RECALL_ON_OPEN (0x40000) also hydrates on open."""
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x40000)) is True
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x400000)) is True
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x1000)) is True
    assert _needs_hydration(types.SimpleNamespace(st_file_attributes=0x20)) is False


def test_r4b02_cancel_during_the_last_candidate_read(tmp_path, monkeypatch):
    """B-VR02R3-02 (P3): cancelling while the LAST candidate's digest is being
    read must also revoke the answer — the end-of-walk guard is load-bearing,
    not dead code (all copies drifted, so the walk ends with an anchor in
    hand and the cancellation is the only thing standing between the caller
    and an unverified handle)."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    from company_wiki.source_catalog import resolver as resolver_module

    for name in ("companies", "dropbox", "future_lake"):
        (paths[name] / "2025.pdf").write_bytes(BODY + b"# drifted")
    budget = _ReadBudget()
    real_sha256_of_file = resolver_module._sha256_of_file
    seen: list[str] = []

    def cancel_on_last(path):
        seen.append(str(path))
        digest = real_sha256_of_file(path)
        if len(seen) == 3:
            budget.cancel()
        return digest

    monkeypatch.setattr(resolver_module, "_sha256_of_file", cancel_on_last)
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert len(seen) == 3, seen
    assert budget.cancelled is True
    assert result.matches == (), result.debug_trace
    assert any(
        "candidate_verification_cancelled" in item for item in result.debug_trace
    ), result.debug_trace


def test_r4b02_claim_reason_names_the_anchor_failure(tmp_path):
    """B-VR02R3-06 (P3): the reason must say why the claim-trusted row failed,
    not why the walk stopped (a later candidate can stop on budget)."""
    paths = _three_copy_fixture(tmp_path)
    catalog = _scan(tmp_path, _roots(paths))
    for name in ("companies", "dropbox"):
        (paths[name] / "2025.pdf").write_bytes(BODY + b"# drifted")
    budget = _ReadBudget(max_candidates=2, max_bytes=64 * len(BODY))
    result = SourceResolver(catalog, read_budget=budget).resolve(_request())
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert any(
        "unverified_content_sha256_mismatch_on_pre_b02_canonical" in item
        for item in result.debug_trace
    ), result.debug_trace
    assert any("budget_exceeded" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b02_documented_difference_from_pre_b02_is_pinned(tmp_path):
    """S-10 difference #1, pinned so nobody "restores" it silently: pre-B02
    matched `.rejections` as a SUBSTRING, so a copy under
    `my.rejections_backup/` was refused; rev3 follows the adapters' SEGMENT
    convention, so that copy is a normal candidate.  With its bytes drifted it
    is served on the catalog's claim (rule 2) and the trace says so."""
    root = tmp_path / "future_lake"
    _write_copy(root / "my.rejections_backup")
    catalog = _scan(
        tmp_path,
        [
            RootSpec(
                "future_lake",
                root,
                "directory",
                priority=40,
                adapter_id="sidecar_filing_v1",
                read_only=True,
                reusable_for_filing=True,
            )
        ],
    )
    (root / "my.rejections_backup" / "2025.pdf").write_bytes(BODY + b"# drifted")

    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert any(
        "unverified_content_sha256_mismatch_on_pre_b02_canonical" in item
        for item in result.debug_trace
    ), result.debug_trace
    assert "my.rejections_backup" in result.matches[0].canonical_path


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
