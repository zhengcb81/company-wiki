"""B.VR-ba1 dispositions that need code: F-BA1-03 / F-BA1-04 / F-BA1-06.

Three findings from the independent review of the product-fix batch each needed a change, and
each change gets a regression here:

* **F-BA1-03 (P2)** - the F-BAR-11 byte gate keyed on the PATH-owning root while the decision
  path keys on the location's `root_id`.  With NESTED roots holding the same file the two
  disagreed, so a handle the decision path elects could be refused `policy_denied`.  The gate
  now resolves the root the same way the decision path does, and `test_nested_roots_*` pins
  the case the reviewer constructed.
* **F-BA1-04 (P2)** - once adapter-declared roots ALWAYS dispatch (F-BAR-10), a root whose
  adapter is registered but unimplemented aborted the WHOLE scan (`ScannerFacadeError`),
  starving the healthy roots behind it.  The failure is per-root now, with no silent v1
  fallback.
* **F-BA1-06 (P2)** - two same-shape partial guards remained on the same two columns
  (`locations.manifest_json` catching only JSONDecodeError; an assertion's `evidence_json`
  catching only (TypeError, ValueError)), so a deeply nested value escaped.  Both go through
  the single chain, which never raises.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    SourceRequest,
    SourceResolver,
)

BODY = b"%PDF-1.4 r4ba1 dispositions"
DIGEST = hashlib.sha256(BODY).hexdigest()
DEEP = "[" * 20000 + "]" * 20000  # RecursionError on a plain json.loads


def _sidecar() -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-ba1",
        "display_name": "BA1 Co",
        "company_name": "BA1 Co",
        "market": "US",
        "security_id": "BA1",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "published_at": "2026-02-20",
        "provider": "sec",
        "provider_document_id": "ba1-1",
        "source_url": "https://sec.gov/ba1-1",
        "content_sha256": DIGEST,
    }


def _write_filing(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "2025.pdf"
    target.write_bytes(BODY)
    (directory / "2025.pdf.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8")
    return target


def _catalog(tmp_path: Path, roots: tuple[RootSpec, ...]) -> SourceCatalog:
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        reusable_root_kinds=("company_raw", "directory"),
        roots=roots,
    ))
    catalog.scan()
    return catalog


# ---------------------------------------------------------------------------
# F-BA1-03: nested roots must not make the two layers disagree
# ---------------------------------------------------------------------------


def test_nested_roots_serve_a_handle_the_decision_path_elected(tmp_path: Path) -> None:
    """The SAME file is indexed by an OUTER reusable root and an INNER denied root.

    The decision path keys on the location's `root_id`, so it elects the outer (reusable)
    location; before the fix the byte gate keyed on the PATH-owning root, which is the inner
    denied one, and refused the very handle the decision had just elected.
    """
    outer = tmp_path / "outer"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    _write_filing(inner)  # the file lives inside BOTH roots
    catalog = _catalog(tmp_path, (
        RootSpec("outer_root", outer, "directory", priority=10,
                 adapter_id="sidecar_filing_v1", read_only=True, reusable_for_filing=True),
        RootSpec("inner_root", inner, "directory", priority=20,
                 adapter_id="sidecar_filing_v1", read_only=True, reusable_for_filing=False),
    ))
    resolver = SourceResolver(catalog)
    resolution = resolver.resolve(SourceRequest(
        entity="BA1 Co", market="US", security_id="BA1", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", mode="exact",
    ))
    assert resolution.matches, resolution.debug_trace
    handle = resolution.matches[0]
    location = catalog.reader.fetchone(
        "SELECT root_id FROM locations WHERE location_id=?", (handle.canonical_location_id,))
    assert location["root_id"] == "outer_root", dict(location)
    result = resolver.read_verified_bytes(handle)
    assert result.ok is True, (result.status, result.reason, result.detail)
    assert result.data == BODY


def test_a_denied_only_file_is_still_refused(tmp_path: Path) -> None:
    """Control: when the file exists ONLY under the denied root, the gate still refuses."""
    denied = tmp_path / "denied"
    _write_filing(denied)
    reusable = tmp_path / "reusable"
    reusable.mkdir()
    catalog = _catalog(tmp_path, (
        RootSpec("reusable_root", reusable, "directory", priority=10,
                 adapter_id="sidecar_filing_v1", read_only=True, reusable_for_filing=True),
        RootSpec("denied_root", denied, "directory", priority=20,
                 adapter_id="sidecar_filing_v1", read_only=True, reusable_for_filing=False),
    ))
    resolver = SourceResolver(catalog)
    # The decision path refuses this root, so the handle is built from its own location row -
    # exactly the "caller builds its own handle" shape F-BAR-11 was about.
    from company_wiki.source_catalog.resolver import SourceHandle

    row = catalog.reader.fetchone(
        "SELECT location_id,absolute_path FROM locations WHERE root_id='denied_root'")
    handle = SourceHandle(
        schema_version="1.0", document_id=f"urn:company-wiki:document:sha256:{DIGEST}",
        source_id=f"urn:company-wiki:source:sha256:{DIGEST}", entity_ids=(),
        title="BA1 Co 2025", source_type="regulatory_filing",
        document_kind="annual_report", published_date="2026-02-20", fiscal_year=2025,
        fiscal_period=None, form_type="10-K", language="en", provider="sec",
        provider_document_id="ba1-1", https_url="https://sec.gov/ba1-1",
        canonical_location_id=row["location_id"], canonical_path=row["absolute_path"],
        content_sha256=DIGEST, snapshot_sha256=DIGEST, mime_type="application/pdf",
        byte_size=len(BODY), retrieved_at="2026-02-20T00:00:00Z", collector_name="probe",
        collector_version="1.0.0", source_status="active", duplicate_group_id="",
        exact_duplicate_location_count=0, capture_ready=True, missing_capture_fields=(),
    )
    result = resolver.read_verified_bytes(handle)
    assert result.ok is False
    assert result.reason == "policy_denied", (result.status, result.reason)
    assert result.detail == "denied_root", result.detail


# ---------------------------------------------------------------------------
# F-BA1-04: one root's adapter failure must not abort the scan
# ---------------------------------------------------------------------------


def test_an_unimplemented_adapter_is_a_per_root_failure(tmp_path: Path) -> None:
    """`generic_document_v1` is REGISTERED but has no scanner implementation."""
    bad_root_dir = tmp_path / "bad"
    bad_root_dir.mkdir()
    (bad_root_dir / "x.pdf").write_bytes(BODY)
    healthy_dir = tmp_path / "healthy"
    _write_filing(healthy_dir)
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        reusable_root_kinds=("company_raw", "directory"),
        roots=(
            RootSpec("bad_root", bad_root_dir, "directory", priority=10,
                     adapter_id="generic_document_v1", read_only=True,
                     reusable_for_filing=True),
            RootSpec("healthy_root", healthy_dir, "directory", priority=20,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
    ))
    report = catalog.scan()  # must NOT raise
    assert report.errors >= 1, report.to_dict()
    details = [item for item in report.error_details if item["root_id"] == "bad_root"]
    assert details and "scan_root_strategy" in details[0]["error"], report.error_details
    assert dict(report.strategy) == {"bad_root": "adapter", "healthy_root": "adapter"}
    # the HEALTHY root behind it was still indexed
    rows = catalog.reader.fetchall(
        "SELECT relative_path FROM locations WHERE root_id='healthy_root'")
    assert [row["relative_path"] for row in rows] == ["2025.pdf"]
    assert catalog.reader.fetchone("SELECT COUNT(*) AS n FROM roots")["n"] == 1


# ---------------------------------------------------------------------------
# F-BA1-06: the two remaining partial guards
# ---------------------------------------------------------------------------


def _deep_manifest_catalog(tmp_path: Path) -> SourceCatalog:
    healthy = tmp_path / "healthy"
    _write_filing(healthy)
    catalog = _catalog(tmp_path, (RootSpec("healthy_root", healthy, "directory", priority=10,
                                           adapter_id="sidecar_filing_v1", read_only=True,
                                           reusable_for_filing=True),))
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE locations SET manifest_json=?", (DEEP,))
    return catalog


def test_a_deeply_nested_manifest_column_does_not_escape_the_resolve(tmp_path: Path) -> None:
    """A RecursionError-raising value must degrade EXACTLY like an empty manifest.

    The old guard caught only JSONDecodeError, so a deeply nested column raised out of the read
    path.  Since an unreadable manifest legitimately means "no manifest claims to compare", the
    measurable assertion is EQUIVALENCE with the empty-manifest case - not "it still matches"
    (with no manifest there is no capture trace, so the handle is legitimately incomplete).
    """
    request = SourceRequest(
        entity="BA1 Co", market="US", security_id="BA1", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", mode="exact",
    )
    deep_catalog = _deep_manifest_catalog(tmp_path)
    deep = SourceResolver(deep_catalog).resolve(request)
    empty_catalog = _deep_manifest_catalog(tmp_path / "empty_case")
    with empty_catalog.store.transaction() as connection:
        connection.execute("UPDATE locations SET manifest_json='{}'")
    empty = SourceResolver(empty_catalog).resolve(request)
    assert (deep.status, deep.reason, len(deep.matches)) == (
        empty.status, empty.reason, len(empty.matches)), (deep.debug_trace, empty.debug_trace)


def test_a_deeply_nested_evidence_column_does_not_escape(tmp_path: Path) -> None:
    """`evidence_json` on an assertion row: (TypeError, ValueError) used to be the whole guard.

    Driven through the real helper (`_v2_assertion_metadata`) with a v1 reader, so the row is
    visible (`visibility_state='legacy'`); the assertion under test is simply that a
    RecursionError-raising value does not escape the read path.
    """
    from company_wiki.source_catalog.resolver import _v2_assertion_metadata

    empty = tmp_path / "empty"
    empty.mkdir()
    catalog = _catalog(tmp_path, (RootSpec("r", empty, "directory", priority=10,
                                           read_only=True),))
    now = "2026-01-01T00:00:00Z"
    with catalog.store.transaction() as connection:
        connection.execute(
            "INSERT INTO sources (source_id,content_sha256,byte_size,mime_type,"
            "first_seen_at) VALUES ('s1','c',1,'application/pdf',?)", (now,))
        connection.execute(
            "INSERT INTO documents (document_id,title,source_status,source_type,"
            "document_kind,metadata_priority,metadata_json,first_seen_at,last_seen_at) "
            "VALUES ('d1','BA1','active','file','annual_report',1,'{}',?,?)", (now, now))
        connection.execute(
            "INSERT INTO source_metadata_assertions (assertion_id,schema_version,source_id,"
            "document_id,content_sha256,evidence_basis,evidence_json,decision,created_at,"
            "created_by,visibility_state) VALUES ('a1','2.0','s1','d1','c','sidecar',?,"
            "'verified',?, 'probe','legacy')", (DEEP, now))
    metadata = _v2_assertion_metadata(catalog.store, "s1", reader="v1",
                                      current_epoch=None, active_cohorts=())
    # no exception, and the unreadable evidence degrades to "no evidence" rather than
    # inventing fields (the measured return is {'content_sha256': 'c', 'evidence': {}})
    assert metadata is None or metadata.get("evidence") == {}, metadata
