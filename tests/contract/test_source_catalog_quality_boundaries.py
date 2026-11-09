"""Exercise lookup completeness and optional acquisition diagnostics on a real catalog."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import (
    AcquisitionCoordinator,
    AcquisitionJournal,
    AdapterRegistry,
    CanonicalSourceWriter,
    SourceAcquisitionService,
    SourceReadError,
    SourceRef,
    SourceRequest,
    SourceResolver,
    SourceVersionReader,
)
from company_wiki.source_catalog.canonical_scope import HistoricalCaptureScopes, qualified_source_scope
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits, LocalReadBudget
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_source_flow import (
    import_official_source,
    recover_official_source,
)
from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord
from contract.test_official_capture_recovery import BODY, import_request, lake
from contract.test_local_request_relevance import request as local_request
from contract.test_source_catalog_acquisition import _catalog, _ExplodingAdapter, _FakeAdapter
from helpers import source_fact_fixture


def _ensure_service(catalog, tmp_path, adapter):
    staging = tmp_path / "staging"
    return SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=catalog, adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
            staging_root=staging,
        ),
        writer=CanonicalSourceWriter(catalog, staging_root=staging),
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )


def _annual_request(*, market="CN", allow_download=True):
    return SourceRequest(
        entity="Acme", market=market, document_kind="annual_report", fiscal_year=2025,
        as_of_date="2026-07-18", allow_download=allow_download,
    )


def test_alias_snapshot_replacement_updates_lookup_in_the_same_process(tmp_path):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        master = SecurityMasterStore(catalog.config.catalog_dir / "security_master")
        record = SecurityRecord(
            "Acme", "CN", "SSE", "600519", "600519", (), True, "cninfo",
            "https://www.cninfo.com.cn/", "fixture-issuer", {},
        )
        snapshot = {"retrieved_at": "2026-07-18T00:00:00Z", "sources": ("cninfo",)}
        master.write_market("CN", (record,), **snapshot)
        request = replace(_annual_request(allow_download=False), entity="New Acme Alias")
        resolver = SourceResolver(catalog)
        reader = SourceVersionReader(catalog)
        assert resolver.resolve(request).status.value == "missing"
        master.write_market("CN", (replace(record, aliases=(request.entity,)),), **snapshot)
        result = resolver.resolve(request)
        assert result.status.value == "reused_equivalent"
        local = reader.query_local(request)
        assert [match.source_id for match in local.matches] == [result.matches[0].source_id]
        master.write_market("CN", (record,), **snapshot)
        assert resolver.resolve(request).status.value == "missing"
        assert not reader.query_local(request).matches
    finally:
        catalog.close()


def test_expansion_does_not_reuse_another_issuer_through_their_shared_alias(tmp_path):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        master = SecurityMasterStore(catalog.config.catalog_dir / "security_master")
        first = SecurityRecord(
            "Issuer One", "CN", "SSE", "600519", "600519", ("Acme",), True, "cninfo",
            "https://www.cninfo.com.cn/", "issuer-one", {},
        )
        second = replace(first, canonical_name="Issuer Two", ticker="600520",
                         security_id="600520", source_record_id="issuer-two")
        master.write_market("CN", (first, second), retrieved_at="2026-07-18T00:00:00Z", sources=("cninfo",))
        resolver = SourceResolver(catalog)
        reader = SourceVersionReader(catalog)
        request = replace(_annual_request(allow_download=False), entity="Issuer Two")
        assert resolver.resolve(request).status.value == "missing"
        assert not reader.query_local(request).matches
        first_request = replace(request, entity="Issuer One")
        assert resolver.resolve(first_request).status.value == "reused_equivalent"
        assert reader.query_local(first_request).matches
    finally:
        catalog.close()


def test_ensure_reads_only_the_current_registered_root_location(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        root = catalog.config.roots[0].path
        original = next(root.rglob("*.txt"))
        stale = tmp_path / "former-root.txt"
        stale.write_bytes(original.read_bytes())
        with catalog.store.transaction() as connection:
            connection.execute("UPDATE locations SET absolute_path = ?", (str(stale),))
        touched = []
        open_path = Path.open

        def observe(path, *args, **kwargs):
            if path in {original, stale}:
                touched.append(path)
            return open_path(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", observe)
        adapter = _ExplodingAdapter()
        result = _ensure_service(catalog, tmp_path, adapter).ensure(_annual_request())
        assert result.status.value == "reused"
        assert touched and set(touched) == {original}
        assert adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


@pytest.mark.parametrize("same_issuer", [False, True], ids=["unrelated-issuers", "other-periods"])
def test_ensure_reuses_matching_raw_past_one_candidate_page(tmp_path, same_issuer):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        request = _annual_request()
        document_id = _seed_newer_candidates(catalog, same_issuer=same_issuer)
        adapter = _ExplodingAdapter()
        result = _ensure_service(catalog, tmp_path, adapter).ensure(request)
        assert result.status.value == "reused"
        assert [match.document_id for match in result.resolution.matches] == [document_id]
        assert adapter.discover_calls == adapter.fetch_calls == 0
        assert not (tmp_path / "staging").exists()
    finally:
        catalog.close()


def _seed_newer_candidates(catalog, *, same_issuer=False):
    # Add a full page of newer annual declarations before the older original.
    with catalog.store.transaction() as connection:
        original = dict(connection.execute("SELECT * FROM documents").fetchone())
        columns = tuple(original)
        placeholders = ",".join("?" for _ in columns)
        rows = []
        for i in range(1000):
            company = "Acme" if same_issuer else f"Other issuer {i}"
            values = dict(
                original, document_id=f"noise-{i:05d}", primary_source_id=None,
                title=f"{company} annual report {i}", published_date="2026-08-01",
                metadata_json=json.dumps({"acquisition": {"company_name": company, "fiscal_year": 2026}}),
            )
            rows.append(tuple(values[key] for key in columns))
        connection.executemany(
            f"INSERT INTO documents ({', '.join(columns)}) VALUES ({placeholders})", rows,
        )
    return original["document_id"]


def test_local_reconciliation_uses_indexed_raw_beyond_first_page_without_rediscovery(tmp_path):
    catalog = source_fact_fixture.lake(tmp_path)
    try:
        original = source_fact_fixture.html()
        ref, path = source_fact_fixture.imported(catalog, original, published="2026-07-30", declared_year=2022)
        _seed_newer_candidates(catalog)
        for i in range(20):
            (path.parent / f"scratch-{i}.txt").write_text("Unregistered test file", encoding="utf-8")

        result = prepare_local_source(catalog, local_request(), limits=LocalPrepareLimits(max_discovery_entries=12))
        assert result["status"] == "ready", result
        assert result["source_ref"]["source_id"] == ref.source_id
        assert result["download_events"] == 0 and path.read_bytes() == original
    finally:
        catalog.close()


def _damage_journal(journal, damage):
    if damage == "directory":
        journal.path.mkdir()
    else:
        journal.path.write_bytes(b"{invalid-json\n")


@pytest.mark.parametrize("damage", ["directory", "corrupt-tail"])
def test_ensure_returns_import_reuse_and_missing_despite_unwritable_observation(tmp_path_factory, caplog, damage):
    tmp_path = tmp_path_factory.mktemp("obs")
    catalog = _catalog(tmp_path, with_source=False)
    try:
        adapter = _FakeAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)
        _damage_journal(service.journal, damage)
        request = _annual_request(market="HK")

        first = service.ensure(request)
        assert first.status.value == "imported"
        assert first.attempt is None
        assert first.canonical_import is not None
        ref = first.canonical_import.source_ref
        assert SourceVersionReader(catalog).open_version(ref).data == b"%PDF-1.7\nsource bytes"

        second = service.ensure(request)
        assert second.status.value == "reused"
        assert second.attempt is None
        assert [match.source_id for match in second.resolution.matches] == [ref.source_id]

        missing = service.ensure(_annual_request(market="CN", allow_download=False))
        assert missing.status.value == "missing"
        assert missing.attempt is None
        assert adapter.discover_calls == adapter.fetch_calls == 1
        assert sum("acquisition_journal_unavailable" in record.message for record in caplog.records) == 3
        if damage == "corrupt-tail":
            with pytest.raises(ValueError, match="invalid acquisition journal line 1"):
                service.journal.read_all()
            assert service.journal.path.read_bytes() == b"{invalid-json\n"
    finally:
        catalog.close()


def _shared_json_request(original):
    request = import_request(original)
    del request["source"]
    return {
        **request, "schema_version": "official-source-import-request/2",
        "document_kind": "investor_relations", "mime_type": "application/json",
        "source_subject": {
            "kind": "multi_issuer_event", "event_namespace": "journal-fixture", "event_id": "1",
            "issuer_refs": [], "attribution_status": "partial",
        },
    }


@pytest.mark.parametrize("shared_json", [False, True], ids=["official-v1", "official-v2"])
def test_capture_completion_and_lost_response_replay_do_not_require_attempt_log(tmp_path, caplog, shared_json):
    with lake(tmp_path) as (_, catalog):
        journal = AcquisitionJournal(catalog.config.catalog_dir)
        journal.path.parent.mkdir(exist_ok=True)
        _damage_journal(journal, "directory")
        if shared_json:
            original = b'{"record":"A shared issuer observation"}'
            result = import_official_json_source(catalog, original=original, request=_shared_json_request(original))
        else:
            original = BODY
            result = import_official_source(catalog, original=original, request=import_request())
        ref = SourceRef(**result["source_ref"])
        assert ref.content_sha256 == hashlib.sha256(original).hexdigest()
        assert result["status"] == "imported_new"
        staging = catalog.config.catalog_dir / "staging"
        (completed,) = staging.glob("*.result.json")
        assert not list(staging.glob("*.capture.json"))
        record = json.loads(completed.read_text(encoding="utf-8"))
        assert record["journal_attempt_id"] is None
        assert "acquisition_journal_unavailable" in caplog.text

        # Old records can contain damaged auxiliary diagnostics; replay uses
        # the canonical original and completed capture's true source fields.
        record["journal_attempt_id"] = ["damaged diagnostic"]
        completed.write_text(json.dumps(record), encoding="utf-8")
        replay = recover_official_source(catalog, capture_id=record["capture_id"])
        assert replay["source_ref"] == result["source_ref"]
        assert replay["capture_receipt"] == result["capture_receipt"]
        assert replay["download_events"] == 0
        assert replay["acquisition_usage"]["response_bytes"] == 0
        assert SourceVersionReader(catalog).open_version(ref).data == original


@pytest.mark.parametrize("tampered", [False, True], ids=["verified-target", "tampered-target"])
def test_legacy_scope_streams_large_history_and_checks_the_target_attempt(tmp_path_factory, tampered):
    tmp_path = tmp_path_factory.mktemp("hist")
    catalog = _catalog(tmp_path, with_source=False)
    try:
        service = _ensure_service(catalog, tmp_path, _FakeAdapter())
        result = service.ensure(_annual_request(market="HK"))
        ref = result.canonical_import.source_ref
        # Model a pre-source-facts capture while retaining canonical original
        # bytes, request/candidate/receipt binding and the actual writer log.
        with catalog.store.transaction() as connection:
            connection.execute("DELETE FROM source_metadata_assertions WHERE source_id=?", (ref.source_id,))
        (document,) = catalog.query_filing_candidates(document_kind="annual_report", source_statuses=("active",))
        good = service.journal.path.read_bytes()
        baseline = qualified_source_scope(catalog, ref, document, historical=HistoricalCaptureScopes(
            catalog, LocalReadBudget(LocalPrepareLimits()),
        ))
        assert baseline.authority == "historical-canonical-request"

        entry = json.loads(good)
        entry["adapter_name"] = "tampered without recomputing attempt ID"
        target = json.dumps(entry).encode() + b"\n" if tampered else good
        with service.journal.path.open("wb") as stream:
            stream.write(b"{corrupt unrelated row\n")
            for _ in range(70):
                stream.write(b" " * 65536 + b"\n")
            stream.write(target)
            stream.write(b"{torn tail")

        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=8 * 1024 * 1024))
        actual = qualified_source_scope(catalog, ref, document, historical=HistoricalCaptureScopes(catalog, budget))
        assert budget.bytes_read == service.journal.path.stat().st_size
        if tampered:
            assert actual.authority == "unverified-declaration"
        else:
            assert actual == baseline and actual.facts["fiscal_year"] == 2025
        small_budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1024))
        with pytest.raises(SourceReadError, match="budget_exceeded"):
            qualified_source_scope(catalog, ref, document, historical=HistoricalCaptureScopes(catalog, small_budget))
        assert small_budget.observed_charge_bytes == 1025
        assert SourceVersionReader(catalog).open_version(ref).data == b"%PDF-1.7\nsource bytes"
    finally:
        catalog.close()
