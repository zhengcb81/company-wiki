"""Contract for the first path-independent catalog read slice.

The caller supplies stable source identity and never a raw path.  Existing
resolver handles may remain for legacy callers but cannot be the v2 input.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.policy_2x import export_policy_2x  # noqa: E402
from company_wiki.source_catalog.runtime_policy import build_snapshot  # noqa: E402
from company_wiki.source_catalog.resolver import SourceRequest  # noqa: E402
from company_wiki.source_catalog.source_reader import (  # noqa: E402
    SourceReadError,
    SourceVersionReader,
)

BODY = b"%PDF-1.4 path-independent-source-version"
SHA = hashlib.sha256(BODY).hexdigest()
OTHER = b"%PDF-1.4 a different filing revision"
OTHER_SHA = hashlib.sha256(OTHER).hexdigest()


def test_v2_reader_is_available_from_the_public_catalog_package():
    import company_wiki.source_catalog as catalog_api

    assert catalog_api.SourceVersionReader is SourceVersionReader
    assert catalog_api.SourceReadError is SourceReadError


def _sidecar(*, sha: str = SHA, provider_id: str = "doc-1",
             source_url: str | None = "https://sec.gov/x/2025",
             capture_trace: bool = True,
             fiscal_year: int | None = 2025,
             period_end: str | None = "2025-12-31",
             filing_date: str = "2026-02-20") -> dict:
    result = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "filing_date": filing_date,
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": provider_id,
        "content_sha256": sha,
    }
    if fiscal_year is not None:
        result["fiscal_year"] = fiscal_year
    if period_end is not None:
        result["period_end"] = period_end
    if source_url is not None:
        result["source_url"] = source_url
    if capture_trace:
        result.update({
            "retrieved_at": "2026-02-21T00:00:00Z",
            "collector_name": "sec_edgar",
            "collector_version": "1.0",
        })
    return result


def _write(directory: Path, *, name: str = "2025.pdf", body: bytes = BODY,
           sha: str = SHA, provider_id: str = "doc-1",
           source_url: str | None = "https://sec.gov/x/2025",
           capture_trace: bool = True,
           fiscal_year: int | None = 2025,
           period_end: str | None = "2025-12-31",
           filing_date: str = "2026-02-20") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(body)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_sidecar(sha=sha, provider_id=provider_id,
                            source_url=source_url, capture_trace=capture_trace,
                            fiscal_year=fiscal_year, period_end=period_end,
                            filing_date=filing_date)),
        encoding="utf-8",
    )
    return path


def _fixture(tmp_path: Path, *, three_roots: bool = False,
             source_url: str | None = "https://sec.gov/x/2025",
             capture_trace: bool = True,
             fiscal_year: int | None = 2025,
             period_end: str | None = "2025-12-31",
             name: str = "2025.pdf"):
    companies = tmp_path / "companies"
    first = _write(companies / "Acme" / "raw" / "financial_reports" / "annual",
                   name=name, period_end=period_end,
                   source_url=source_url, capture_trace=capture_trace,
                   fiscal_year=fiscal_year)
    roots = [
        RootSpec("company_raw", companies, "company_raw", priority=10,
                 adapter_id="company_raw_v1", read_only=False,
                 reusable_for_filing=True, canonical_write_target="companies"),
    ]
    paths = [first]
    if three_roots:
        for root_id, directory, priority in (
            ("dropbox_stock", tmp_path / "Dropbox" / "Stock", 20),
            ("future_lake", tmp_path / "future_lake", 30),
        ):
            paths.append(_write(directory, name=name, period_end=period_end,
                                source_url=source_url,
                                capture_trace=capture_trace,
                                fiscal_year=fiscal_year))
            roots.append(
                RootSpec(root_id, directory, "directory", priority=priority,
                         adapter_id="sidecar_filing_v1", read_only=True,
                         reusable_for_filing=True)
            )
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=tuple(roots),
        reusable_root_kinds=("company_raw", "directory"),
    )
    catalog = SourceCatalog(config)
    catalog.scan()
    row = catalog.reader.fetchone(
        """SELECT d.document_id, d.primary_source_id AS source_id,
                  s.content_sha256
           FROM documents d JOIN sources s
             ON s.source_id=d.primary_source_id
           WHERE d.source_status='active' AND s.content_sha256=?""",
        (SHA,),
    )
    assert row is not None
    return catalog, tuple(paths), tuple(roots), dict(row)


@pytest.mark.parametrize("visibility,decision,assertion_sha", [
    ("active", "verified", SHA), ("legacy", "verified", SHA),
    ("shadow", "verified", SHA), ("active", "rejected", SHA),
    ("active", "verified", OTHER_SHA), ("legacy", "verified", OTHER_SHA),
])
def test_steady_policy_keeps_activated_facts_and_legacy_capture_without_canary(
    tmp_path, visibility, decision, assertion_sha,
):
    catalog, paths, _, ids = _fixture(tmp_path)
    try:
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
        with catalog.store.transaction() as conn:
            row = conn.execute("SELECT metadata_json FROM documents WHERE document_id=?",
                               (ref.document_id,)).fetchone()
            metadata = json.loads(row[0])
            metadata["acquisition"]["source_title"] = "Explicit captured title"
            conn.execute("UPDATE documents SET metadata_json=? WHERE document_id=?",
                         (json.dumps(metadata), ref.document_id))
            conn.execute("""INSERT INTO source_metadata_assertions
                (assertion_id,source_id,document_id,content_sha256,evidence_basis,evidence_json,
                 decision,created_at,created_by,schema_version,visibility_state,activation_epoch,cohort,
                 market,security_id,fiscal_year,period_end,language)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("steady-a", ref.source_id, ref.document_id, assertion_sha, "verified_bytes", "{}", decision,
                 "2026-10-07T00:00:00Z", "test", "2.0", visibility, "old-canary", "old-cohort",
                 "US", "ACME", 2024, "2024-12-31", "en"))
        snapshot = build_snapshot({"schema_version": "2.0", "mode": "steady",
            "policy_hash": export_policy_2x(catalog.config)[0], "updated_at": "2026-10-07T00:00:00Z"})
        (catalog.config.catalog_dir / "runtime_policy.json").write_text(json.dumps(snapshot), encoding="utf-8")
        manifest = reader.describe_version(ref)
        assert manifest["title"] == "Explicit captured title"
        accepted = visibility in {"active", "legacy"} and decision == "verified" and assertion_sha == SHA
        assert manifest["fiscal_year"] == (2024 if accepted else 2025)
        assert manifest["period_end"] == ("2024-12-31" if accepted else "2025-12-31")
        assert manifest["language"] == ("en" if accepted else None)
        assert manifest["source_url"] == "https://sec.gov/x/2025"
        assert reader.open_version(ref, purpose="preview").data == BODY
        paths[0].write_bytes(OTHER)
        with pytest.raises(SourceReadError):
            reader.open_version(ref, purpose="preview")
    finally:
        catalog.close()


def test_exact_ref_contains_no_location_and_delivers_verified_bytes(tmp_path):
    catalog, paths, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    serialized = asdict(ref)
    assert serialized["document_id"] == ids["document_id"]
    assert serialized["source_id"] == ids["source_id"]
    assert serialized["content_sha256"] == SHA
    assert not any("path" in key or "root" in key or "location" in key
                   for key in serialized)
    assert str(tmp_path) not in repr(serialized)

    opened = reader.open_version(ref, purpose="filing_reuse")
    assert opened.data == BODY == paths[0].read_bytes()
    assert opened.content_sha256 == SHA
    assert opened.document_id == ids["document_id"]
    assert opened.source_id == ids["source_id"]
    assert opened.policy_sha256 == export_policy_2x(catalog.config)[0]


def test_narrative_derivation_open_and_verify_return_bound_review_snapshot(
    tmp_path,
):
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )

    catalog, _, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    policy_hash = export_policy_2x(catalog.config)[0]
    with catalog.store.transaction() as connection:
        record_prompt_injection_review(
            connection,
            ref.document_id,
            status="not_detected",
            reviewer="e4-reader-contract",
            evidence_sha256=SHA,
            evidence_payload=BODY,
            now="2026-09-28T16:00:00Z",
            source_sha256=SHA,
            policy_hash=policy_hash,
        )
    read_policy_sha256 = reader.read_policy_sha256()

    opened = reader.open_version(
        ref,
        purpose="narrative_derivation",
        expected_read_policy_sha256=read_policy_sha256,
    )
    verified = reader.verify_version(
        ref,
        purpose="narrative_derivation",
        expected_read_policy_sha256=read_policy_sha256,
    )

    assert opened.data == BODY
    assert opened.review is not None
    assert opened.review.status == "not_detected"
    assert opened.review.source_sha256 == SHA
    assert opened.review.policy_hash == policy_hash
    assert verified.review == opened.review
    assert str(tmp_path) not in repr(asdict(opened))
    assert str(tmp_path) not in repr(asdict(verified))
    assert not any("path" in key or "root" in key for key in asdict(verified))

    with pytest.raises(SourceReadError) as purpose_error:
        reader.open_version(ref, purpose="unknown-purpose")
    assert purpose_error.value.reason == "unsupported_purpose"
    current_read = reader.open_version(ref, purpose="narrative_derivation",
                                       expected_read_policy_sha256="0" * 64)
    assert current_read.data == BODY
    assert current_read.source_read_policy_sha256 != "0" * 64


def test_wrong_identity_hash_and_retirement_fail_before_open(tmp_path, monkeypatch):
    catalog, _, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)

    real_open = Path.open

    def no_pdf_open(path, *args, **kwargs):
        if path.suffix.lower() == ".pdf":
            raise AssertionError("a refused request opened source bytes")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_pdf_open)
    with pytest.raises(SourceReadError):
        reader.query_ref(ids["document_id"], ids["source_id"], OTHER_SHA)
    with pytest.raises(SourceReadError):
        reader.query_ref(ids["document_id"], "urn:wrong-source", SHA)
    with pytest.raises(SourceReadError):
        reader.query_ref("urn:wrong-document", ids["source_id"], SHA)

    connection = sqlite3.connect(catalog.config.database_path)
    connection.execute(
        "UPDATE documents SET source_status='retired' WHERE document_id=?",
        (ids["document_id"],),
    )
    connection.commit()
    connection.close()
    with pytest.raises(SourceReadError) as error:
        reader.open_version(ref, purpose="filing_reuse")
    assert error.value.status == "blocked"


def test_same_version_fallback_survives_corruption_and_root_move(tmp_path):
    catalog, paths, roots, ids = _fixture(tmp_path, three_roots=True)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )

    paths[0].unlink()
    assert SourceVersionReader(catalog).open_version(
        ref, purpose="filing_reuse"
    ).data == BODY

    paths[0].write_bytes(bytes(reversed(BODY)))
    assert SourceVersionReader(catalog).open_version(
        ref, purpose="filing_reuse"
    ).data == BODY

    paths[2].unlink()
    moved_root = tmp_path / "relocated_dropbox"
    roots[1].path.rename(moved_root)
    relocated = SourceCatalog(
        replace(catalog.config, roots=(roots[0], replace(roots[1], path=moved_root),
                                       roots[2]))
    )
    # The catalog retains the old absolute_path. The reader must derive the
    # current internal path from root_id + relative_path, without a rescan.
    assert SourceVersionReader(relocated).open_version(
        ref, purpose="filing_reuse"
    ).data == BODY


def test_streaming_verify_version_uses_same_fallback_and_pathless_receipt(tmp_path):
    catalog, paths, _, ids = _fixture(tmp_path, three_roots=True)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    paths[0].write_bytes(bytes(reversed(BODY)))
    reader = SourceVersionReader(catalog)
    receipt = reader.verify_version(ref, purpose="filing_reuse")
    assert receipt.content_sha256 == SHA
    assert receipt.byte_size == len(BODY)
    assert receipt.policy_sha256 == export_policy_2x(catalog.config)[0]
    assert not any(
        name in asdict(receipt)
        for name in ("data", "path", "root_id", "location_id")
    )
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY

    for path in paths[1:]:
        path.write_bytes(bytes(reversed(BODY)))
    with pytest.raises(SourceReadError) as error:
        reader.verify_version(ref, purpose="filing_reuse")
    assert error.value.reason == "no_verified_location"


def test_other_version_never_substitutes_and_policy_is_rechecked(tmp_path, monkeypatch):
    catalog, paths, roots, ids = _fixture(tmp_path, three_roots=True)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )

    denied = SourceCatalog(
        replace(catalog.config, roots=tuple(
            replace(root, allowed_statuses=("quarantined",)) for root in roots
        ))
    )
    real_open = Path.open

    def no_pdf_open(path, *args, **kwargs):
        if path.suffix.lower() == ".pdf":
            raise AssertionError("revoked policy opened source bytes")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_pdf_open)
    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(denied).open_version(ref, purpose="filing_reuse")
    assert error.value.status == "blocked"
    monkeypatch.undo()

    _write(roots[0].path / "Acme" / "raw" / "financial_reports" / "annual",
           name="other.pdf", body=OTHER, sha=OTHER_SHA, provider_id="doc-2")
    catalog.scan()
    for path in paths:
        path.write_bytes(bytes(reversed(BODY)))
    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(catalog).open_version(ref, purpose="filing_reuse")
    assert error.value.status == "unavailable"


def test_malformed_indexed_locator_is_a_named_refusal(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    connection = sqlite3.connect(catalog.config.database_path)
    connection.execute(
        "UPDATE locations SET relative_path=? "
        "WHERE document_id=? AND role='original_primary'",
        ("bad" + chr(0) + ".pdf", ids["document_id"]),
    )
    connection.commit()
    connection.close()

    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(catalog).open_version(ref, purpose="filing_reuse")
    assert error.value.status == "unavailable"
    assert error.value.reason == "no_verified_location"


def test_missing_catalog_is_a_pathless_named_refusal(tmp_path):
    root = RootSpec(
        "company_raw", tmp_path / "companies", "company_raw",
        adapter_id="company_raw_v1", read_only=False,
        reusable_for_filing=True, canonical_write_target="companies",
    )
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / "absent_catalog",
        roots=(root,),
    ))
    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(catalog).query_ref(
            "urn:document", "urn:source", SHA
        )
    assert error.value.status == "unavailable"
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize(
    ("source_url", "capture_trace"),
    [(None, True), ("http://sec.gov/x/2025", True), ("https://sec.gov/x/2025", False)],
)
def test_filing_reuse_verifies_raw_despite_sparse_capture_metadata(
    tmp_path, monkeypatch, source_url, capture_trace
):
    catalog, _, _, ids = _fixture(
        tmp_path, source_url=source_url, capture_trace=capture_trace
    )
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    if not capture_trace:
        # The filesystem scanner records its own collection trace even when
        # the sidecar omits one.  Remove the indexed trace to model an actual
        # incomplete catalog claim, not merely a sparse input sidecar.
        connection = sqlite3.connect(catalog.config.database_path)
        rows = connection.execute(
            "SELECT location_id, manifest_json FROM locations "
            "WHERE document_id=? AND role='original_primary'",
            (ids["document_id"],),
        ).fetchall()
        for location_id, raw_manifest in rows:
            manifest = json.loads(raw_manifest)
            for field in ("retrieved_at", "collector_name", "collector_version"):
                manifest.pop(field, None)
            connection.execute(
                "UPDATE locations SET manifest_json=? WHERE location_id=?",
                (json.dumps(manifest), location_id),
            )
        connection.commit()
        connection.close()
    reader = SourceVersionReader(catalog)
    candidate = reader.describe_candidate(ref)
    assert candidate['capture_ready'] is False
    opened = reader.open_version(ref, purpose='filing_reuse')
    assert opened.data == BODY
    assert opened.content_sha256 == SHA
    assert reader.verify_version(ref, purpose='filing_reuse').byte_size == len(BODY)
    # Relaxing descriptive metadata must not bypass the actual byte check.
    for path in catalog.config.roots[0].path.rglob('*.pdf'):
        path.write_bytes(OTHER)
    with pytest.raises(SourceReadError) as error:
        reader.open_version(ref, purpose='filing_reuse')
    assert error.value.reason == 'no_verified_location'



@pytest.mark.parametrize(
    ("missing_url", "reusable_flag_off"),
    [(True, False), (False, True)],
)
def test_query_local_and_preview_are_separate_from_formal_filing_reuse(
    tmp_path, missing_url, reusable_flag_off
):
    catalog, _, roots, ids = _fixture(
        tmp_path, source_url=None if missing_url else "https://sec.gov/x/2025"
    )
    if reusable_flag_off:
        catalog = SourceCatalog(replace(
            catalog.config,
            roots=(replace(roots[0], reusable_for_filing=False),),
        ))
    request = SourceRequest(
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
    reader = SourceVersionReader(catalog)
    result = reader.query_local(request)
    assert result.status == "found"
    assert len(result.matches) == 1
    ref = result.matches[0]
    assert ref.document_id == ids["document_id"]
    assert ref.source_id == ids["source_id"]
    assert ref.content_sha256 == SHA
    assert "path" not in repr(asdict(ref)).lower()
    assert reader.open_version(ref, purpose="preview").data == BODY
    # Capture completeness and the old reusable flag are diagnostics;
    # the same SourceRef still controls the exact verified raw bytes.
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY



def test_sparse_candidate_preserves_known_capture_observations(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    with catalog.store.transaction() as connection:
        rows = connection.execute(
            "SELECT location_id, manifest_json FROM locations WHERE document_id=?",
            (ids["document_id"],),
        ).fetchall()
        for location_id, raw_manifest in rows:
            manifest = json.loads(raw_manifest)
            manifest["retrieved_at"] = "2026-02-21T00:00:00Z"
            manifest["collector_name"] = "sec_edgar"
            manifest.pop("collector_version", None)
            connection.execute(
                "UPDATE locations SET manifest_json=? WHERE location_id=?",
                (json.dumps(manifest), location_id),
            )
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    candidate = reader.describe_candidate(ref)
    assert candidate["retrieved_at"] == "2026-02-21T00:00:00Z"
    assert candidate["collector_name"] == "sec_edgar"
    assert candidate["collector_version"] is None
    assert candidate["capture_ready"] is False
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY


def test_query_local_keeps_legacy_year_from_title_and_respects_as_of(tmp_path):
    catalog, _, roots, ids = _fixture(tmp_path, fiscal_year=None)
    reader = SourceVersionReader(catalog)
    request = SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    )
    result = reader.query_local(request)
    assert result.status == "found"
    assert result.matches[0].document_id == ids["document_id"]

    future = reader.query_local(replace(request, as_of_date="2026-01-01"))
    assert future.matches == ()
    assert future.status == "not_found"


def test_as_of_cutoff_applies_before_candidate_limit(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    connection = sqlite3.connect(catalog.config.database_path)
    connection.executemany(
        """INSERT INTO documents(
               document_id, primary_source_id, title, source_type,
               document_kind, published_date, source_status,
               metadata_priority, metadata_json, first_seen_at, last_seen_at
           ) VALUES (?, NULL, ?, 'filing', 'annual_report', '2026-12-31',
                     'active', 10, '{}', '2026-12-31', '2026-12-31')""",
        ((f"urn:future:{index}", f"future-{index}") for index in range(1001)),
    )
    connection.commit()
    connection.close()
    request = SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    )
    result = SourceVersionReader(catalog).query_local(request)
    assert result.status == "found"
    assert result.matches[0].document_id == ids["document_id"]


def test_local_query_does_not_silently_miss_match_after_first_page(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    connection = sqlite3.connect(catalog.config.database_path)
    connection.executemany(
        """INSERT INTO documents(
               document_id, primary_source_id, title, source_type,
               document_kind, published_date, source_status,
               metadata_priority, metadata_json, first_seen_at, last_seen_at
           ) VALUES (?, NULL, ?, 'filing', 'annual_report', '2026-02-20',
                     'active', 10, '{}', '2026-02-20', '2026-02-20')""",
        ((f"urn:decoy:{index}", f"000-decoy-{index:04d}")
         for index in range(1001)),
    )
    connection.commit()
    connection.close()
    request = SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    )
    result = SourceVersionReader(catalog).query_local(request)
    assert result.status == "found"
    assert result.matches[0].document_id == ids["document_id"]


def test_disputed_auxiliary_capture_is_diagnostic_for_verified_filing_read(tmp_path, monkeypatch):
    catalog, _, _, ids = _fixture(tmp_path)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    connection = sqlite3.connect(catalog.config.database_path)
    row = connection.execute(
        "SELECT metadata_json FROM documents WHERE document_id=?",
        (ids["document_id"],),
    ).fetchone()
    metadata = json.loads(row[0])
    fields = metadata.setdefault("r4_provenance", {}).setdefault("fields", {})
    fields["acquisition.source_url"] = {
        "value": "disputed",
        "sources": [],
        "conflicts": [{"source_id": "urn:conflicting-capture", "value": "other"}],
    }
    connection.execute(
        "UPDATE documents SET metadata_json=? WHERE document_id=?",
        (json.dumps(metadata), ids["document_id"]),
    )
    connection.commit()
    connection.close()
    reader = SourceVersionReader(catalog)
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY
    assert reader.describe_version(ref)["source_url"] is None
    assert reader.metadata_diagnostics(ref)["conflicted_fields"] == ["acquisition.source_url"]


def test_pending_remediation_is_diagnostic_and_does_not_block_verified_reuse(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    connection = sqlite3.connect(catalog.config.database_path)
    connection.execute(
        "INSERT INTO remediation_proposals "
        "(proposal_id, source_id, document_id, content_sha256, proposal_json, "
        "policy_hash, proposed_by, created_at, status) "
        "VALUES (?, ?, ?, ?, '{}', ?, 'test', '2026-09-27T00:00:00Z', 'proposed')",
        ("proposal-1", ids["source_id"], ids["document_id"], SHA, "0" * 64),
    )
    connection.commit()
    connection.close()
    request = SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    )
    assert reader.query_local(request).matches == (ref,)
    for purpose in ("filing_reuse", "source_export", "narrative_derivation"):
        assert reader.open_version(ref, purpose=purpose).data == BODY


def test_exact_filing_read_does_not_require_period_but_period_query_does(
    tmp_path, monkeypatch
):
    catalog, _, _, ids = _fixture(
        tmp_path, fiscal_year=None, period_end=None, name="report.pdf"
    )
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    reader = SourceVersionReader(catalog)
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY
    assert reader.describe_version(ref)["fiscal_year"] is None
    request = SourceRequest(entity="Acme", document_kind="annual_report",
                            fiscal_year=2025, as_of_date="2026-10-08")
    assert reader.query_local(request).matches == ()


@pytest.mark.parametrize(
    "root_policy",
    (
        {"allowed_document_kinds": ("quarterly_report",)},
        {"max_file_size": len(BODY) - 1},
    ),
)
def test_current_root_admission_policy_applies_before_any_source_open(
    tmp_path, monkeypatch, root_policy
):
    catalog, _, roots, ids = _fixture(tmp_path)
    ref = SourceVersionReader(catalog).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    restricted = SourceCatalog(replace(
        catalog.config, roots=(replace(roots[0], **root_policy),)
    ))
    real_open = Path.open

    def no_pdf_open(path, *args, **kwargs):
        if path.suffix.lower() == ".pdf":
            raise AssertionError("revoked root admission opened source bytes")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_pdf_open)
    for purpose in ("preview", "filing_reuse", "narrative_derivation"):
        with pytest.raises(SourceReadError) as error:
            SourceVersionReader(restricted).open_version(ref, purpose=purpose)
        assert error.value.status == "blocked"


def test_v2_runtime_snapshot_closes_legacy_metadata_bridge_for_query_and_reuse(
    tmp_path, monkeypatch
):
    catalog, _, _, ids = _fixture(tmp_path)
    policy_hash = export_policy_2x(catalog.config)[0]
    snapshot = build_snapshot({
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        "current_epoch": "epoch-1",
        "active_cohorts": ["cohort-a"],
        "policy_hash": policy_hash,
        "updated_at": "2026-09-27T00:00:00Z",
    })
    (catalog.config.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    reader = SourceVersionReader(catalog, runtime_policy=snapshot)
    request = SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="doc-1",
        as_of_date="2026-09-27", mode="exact",
    )
    assert reader.query_local(request).status == "not_found"
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    manifest = reader.describe_version(ref)
    assert manifest["document_id"] == ref.document_id
    assert manifest["source_id"] == ref.source_id
    assert manifest["content_sha256"] == ref.content_sha256
    assert manifest["byte_size"] == ref.byte_size
    for field in (
        "title", "source_url", "retrieved_at", "collector_name",
        "collector_version", "canonical_entity_id", "display_name", "market",
        "security_id", "fiscal_year", "fiscal_period", "period_end",
        "form_type", "provider", "provider_document_id", "language",
    ):
        assert manifest[field] is None
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY
    modern = SourceVersionReader(catalog)
    assert modern.query_local(request).status == "found"
    assert modern.describe_version(ref)["fiscal_year"] == 2025


def test_source_export_falls_back_to_same_sha_copy_regardless_of_root_label(tmp_path):
    catalog, paths, roots, ids = _fixture(tmp_path, three_roots=True)
    restricted = SourceCatalog(replace(
        catalog.config,
        roots=(
            roots[0],
            replace(roots[1], privacy_class="private_user"),
            replace(roots[2], privacy_class="private_user"),
        ),
    ))
    ref = SourceVersionReader(restricted).query_ref(
        ids["document_id"], ids["source_id"], SHA
    )
    paths[0].write_bytes(bytes(reversed(BODY)))
    reader = SourceVersionReader(restricted)
    assert reader.open_version(ref, purpose="preview").data == BODY
    assert reader.open_version(ref, purpose="source_export").data == BODY


def test_same_sha_disputed_period_blocks_period_selection_not_raw_read(tmp_path):
    catalog, paths, _, ids = _fixture(tmp_path, three_roots=True)
    sidecar_path = paths[1].parent / f"{paths[1].name}.source.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["source_url"] = "https://sec.gov/other-filing"
    sidecar["provider_document_id"] = "other-doc"
    sidecar["fiscal_year"] = 2024
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    catalog.scan()

    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)
    manifest = reader.describe_version(ref)
    assert manifest["source_url"] is None and manifest["fiscal_year"] is None
    assert manifest["provider_document_id"] is None
    assert reader.open_version(ref, purpose="filing_reuse").data == BODY
    request = SourceRequest(entity="Acme", document_kind="annual_report", fiscal_year=2025,
                            as_of_date="2026-10-08")
    assert reader.query_local(request).matches == ()


def test_review_store_failure_is_diagnostic_and_verified_bytes_remain_usable(
    tmp_path, monkeypatch,
):
    from company_wiki.source_catalog.prompt_injection import (
        PromptInjectionReviewError,
    )
    import company_wiki.source_catalog.source_reader as reader_module

    catalog, paths, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], SHA)

    def fail_review(*_args):
        raise PromptInjectionReviewError("database is locked")

    monkeypatch.setattr(reader_module, "read_prompt_injection_review", fail_review)
    candidate = reader.describe_candidate(ref)
    assert candidate["capture_ready"] is True
    assert candidate["prompt_injection_status"] == "not_reviewed"
    opened = reader.open_version(ref, purpose="filing_reuse")
    assert opened.data == BODY
    assert opened.review is not None
    assert opened.review.status == "not_reviewed"

    paths[0].write_bytes(b"X" * len(BODY))
    assert reader.describe_candidate(ref)["capture_ready"] is True
    with pytest.raises(SourceReadError) as error:
        reader.open_version(ref, purpose="filing_reuse")
    assert error.value.reason == "no_verified_location"
