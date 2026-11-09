"""Acquisition consumes one owner-verified original within a reuse decision."""

from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from company_wiki.source_catalog import SourceReadError, SourceResolver, SourceVersionReader
from company_wiki.source_catalog import acquisition_service as service_module
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from contract.test_local_request_relevance import request as sec_request
from contract.test_source_catalog_acquisition import _catalog, _ExplodingAdapter, _FakeAdapter
from contract.test_source_catalog_quality_boundaries import _annual_request, _ensure_service
from helpers import source_fact_fixture


_MULTI_CHUNK_ORIGINAL = b"A report original with multiple chunks\n" * 65_536


def _register_annual(catalog, *, market="CN", provider="cninfo", accession="1"):
    folder = catalog.config.roots[0].path / "Acme"
    folder.mkdir(parents=True, exist_ok=True)
    original = folder / "2026-03-20_Acme_2025_annual_report.txt"
    original.write_bytes(_MULTI_CHUNK_ORIGINAL)
    original.with_name(original.name + ".source.json").write_text(json.dumps({
        "company_name": "Acme", "source_title": "Acme 2025 Annual Report", "document_kind": "annual_report",
        "market": market, "provider": provider, "provider_document_id": accession,
        "form_type": "annual_report", "fiscal_year": 2025, "fiscal_period": "FY", "language": "en",
        "filing_date": "2026-03-20", "source_url": "https://issuer.example/annual-2025",
    }), encoding="utf-8")
    catalog.scan()
    return original


def _observe_original_reads(monkeypatch, original, *, observe=lambda: True, after_read=None):
    actual_open = Path.open
    reads = []

    class Stream:
        def __init__(self, stream):
            self.stream = stream
            self.sizes = []

        def __enter__(self):
            self.stream.__enter__()
            return self

        def read(self, size=-1):
            value = self.stream.read(size)
            if value:
                self.sizes.append(len(value))
            return value

        def __exit__(self, *exc):
            result = self.stream.__exit__(*exc)
            reads.append(tuple(self.sizes))
            if after_read is not None:
                after_read(len(reads))
            return result

    def track(path, *args, **kwargs):
        stream = actual_open(path, *args, **kwargs)
        mode = args[0] if args else kwargs.get("mode", "r")
        return Stream(stream) if path == original and mode == "rb" and observe() else stream

    monkeypatch.setattr(Path, "open", track)
    return reads


def test_exact_local_reuse_streams_once_per_request(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)
        reads = _observe_original_reads(monkeypatch, original)
        for number in (1, 2):
            result = service.ensure(_annual_request())
            assert result.status.value == "reused"
            assert len(reads) == number
            assert len(reads[-1]) > 1 and sum(reads[-1]) == len(_MULTI_CHUNK_ORIGINAL)
        assert adapter.discover_calls == adapter.fetch_calls == 0
        assert "verified_reuse" not in result.acquisition.to_dict()
    finally:
        catalog.close()


def test_after_discovery_reuse_verifies_current_bytes_once_under_target_lock(tmp_path_factory, monkeypatch):
    tmp_path = tmp_path_factory.mktemp("late")
    catalog = _catalog(tmp_path, with_source=False)
    try:
        inside_target_lock = False
        mutex = service_module._acquisition_mutex

        @contextmanager
        def track_lock(*args, **kwargs):
            nonlocal inside_target_lock
            with mutex(*args, **kwargs):
                inside_target_lock = True
                try:
                    yield
                finally:
                    inside_target_lock = False

        monkeypatch.setattr(service_module, "_acquisition_mutex", track_lock)

        class LocalArrival(_FakeAdapter):
            def discover(self, request):
                candidates = super().discover(request)
                original = _register_annual(catalog, market="HK", provider="hkex", accession="12345")
                self.raw_reads = _observe_original_reads(monkeypatch, original, observe=lambda: inside_target_lock)
                return candidates

        adapter = LocalArrival()
        service = _ensure_service(catalog, tmp_path, adapter)
        result = service.ensure(_annual_request(market="HK"))
        assert result.status.value == "reused" and result.acquisition.reason.endswith("after_discovery")
        assert adapter.discover_calls == 1 and adapter.fetch_calls == 0
        assert len(adapter.raw_reads) == 1
        assert len(adapter.raw_reads[0]) > 1 and sum(adapter.raw_reads[0]) == len(_MULTI_CHUNK_ORIGINAL)
    finally:
        catalog.close()


def test_changed_mtime_during_candidate_read_cannot_become_successful_reuse(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)

        def move_mtime(first_read):
            if first_read == 1:
                status = original.stat()
                os.utime(original, ns=(status.st_atime_ns, status.st_mtime_ns + 2_000_000_000))

        _observe_original_reads(monkeypatch, original, after_read=move_mtime)
        with pytest.raises(SourceReadError, match="changed_during_read"):
            service.ensure(_annual_request())
        assert adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_changed_same_size_bytes_after_previous_request_cannot_reuse_legacy_claim(tmp_path):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)
        request = _annual_request()
        assert service.ensure(request).status.value == "reused"
        original.write_bytes(b"X" + _MULTI_CHUNK_ORIGINAL[1:])

        compatibility = SourceResolver(catalog).resolve(request)
        assert compatibility.status.value == "reused_equivalent"
        assert any("unverified_content_sha256_mismatch" in step for step in compatibility.debug_trace)
        with pytest.raises(SourceReadError, match="content_sha256_mismatch"):
            service.ensure(request)
        assert adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_public_operations_do_not_accept_or_publish_request_local_proof(tmp_path):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        service = _ensure_service(catalog, tmp_path, _ExplodingAdapter())
        request = _annual_request()
        first = service.ensure(request)
        assert first.status.value == "reused"
        public_selection = service.coordinator.select(request)
        previous = getattr(first.acquisition, "verified_reuse", None)
        original.write_bytes(b"X" + _MULTI_CHUNK_ORIGINAL[1:])

        with pytest.raises(TypeError, match="_verified_reuse"):
            prepare_local_source(catalog, request, _verified_reuse=previous)
        ordinary = prepare_local_source(catalog, request)
        assert ordinary["status"] == "unavailable" and ordinary["blocks_download"]
        assert ordinary["reason"] == "no_verified_location"
        assert not hasattr(first.acquisition, "verified_reuse")
        assert not hasattr(public_selection, "verified_reuse")
    finally:
        catalog.close()


def test_as_of_cutoff_does_not_allow_future_original(tmp_path):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        _register_annual(catalog)
        request = replace(_annual_request(allow_download=False), as_of_date="2026-02-10")
        result = _ensure_service(catalog, tmp_path, _ExplodingAdapter()).ensure(request)
        assert result.status.value == "missing" and not result.resolution.matches
    finally:
        catalog.close()


@pytest.mark.parametrize("constraint", [
    {"allowed_document_kinds": ("quarterly_report",)},
    {"allowed_statuses": ("retired",)},
    {"max_file_size": len(_MULTI_CHUNK_ORIGINAL) - 1},
])
def test_current_root_admission_refuses_before_reading_original(tmp_path, monkeypatch, constraint):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        root, = catalog.config.roots
        catalog.config = replace(catalog.config, roots=(replace(root, **constraint),))
        reads = _observe_original_reads(monkeypatch, original)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)

        with pytest.raises(SourceReadError, match="root_admission_denied"):
            service.ensure(_annual_request())
        assert reads == [] and adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_stale_absolute_location_is_ignored_and_outside_relative_location_refuses(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        outside = catalog.config.project_root / "not-in-an-original-root.txt"
        outside.write_bytes(_MULTI_CHUNK_ORIGINAL)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)
        with catalog.store.transaction() as connection:
            connection.execute("UPDATE locations SET absolute_path=? WHERE role='original_primary'", (str(outside),))
        original_reads = _observe_original_reads(monkeypatch, original)
        outside_reads = _observe_original_reads(monkeypatch, outside)
        assert service.ensure(_annual_request()).status.value == "reused"
        assert len(original_reads) == 1 and outside_reads == []

        with catalog.store.transaction() as connection:
            connection.execute("UPDATE locations SET relative_path=? WHERE role='original_primary'", ("../" + outside.name,))
        with pytest.raises(SourceReadError, match="invalid_relative_path"):
            service.ensure(_annual_request())
        assert len(original_reads) == 1 and outside_reads == []
        assert adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_legacy_handle_projects_location_actually_verified_after_same_id_rebind(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        moved = original.with_name("same-original-new-location.txt")
        moved.write_bytes(_MULTI_CHUNK_ORIGINAL)
        verify = SourceVersionReader.verify_reusable_version

        def rebind(reader, ref, **kwargs):
            root = catalog.config.roots[0].path
            with catalog.store.transaction() as connection:
                connection.execute(
                    "UPDATE locations SET absolute_path=?, relative_path=? "
                    "WHERE document_id=? AND role='original_primary'",
                    (str(moved), moved.relative_to(root).as_posix(), ref.document_id),
                )
            original.write_bytes(b"X" + _MULTI_CHUNK_ORIGINAL[1:])
            return verify(reader, ref, **kwargs)

        monkeypatch.setattr(SourceVersionReader, "verify_reusable_version", rebind)
        old_reads = _observe_original_reads(monkeypatch, original)
        current_reads = _observe_original_reads(monkeypatch, moved)
        adapter = _ExplodingAdapter()
        result = _ensure_service(catalog, tmp_path, adapter).ensure(_annual_request())
        assert result.status.value == "reused"
        assert Path(result.resolution.matches[0].canonical_path) == moved
        assert old_reads == [] and len(current_reads) == 1
        assert sum(current_reads[0]) == len(_MULTI_CHUNK_ORIGINAL)
        assert adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


@pytest.mark.parametrize("change", ["size", "role"])
def test_later_request_rechecks_registered_size_and_original_role(tmp_path, monkeypatch, change):
    catalog = _catalog(tmp_path, with_source=False)
    try:
        original = _register_annual(catalog)
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)
        request = _annual_request()
        assert service.ensure(request).status.value == "reused"
        if change == "size":
            original.write_bytes(_MULTI_CHUNK_ORIGINAL + b"extra")
        else:
            with catalog.store.transaction() as connection:
                connection.execute("UPDATE locations SET role='metadata' WHERE role='original_primary'")

        reads = _observe_original_reads(monkeypatch, original)
        if change == "size":
            with pytest.raises(SourceReadError, match="byte_size_mismatch"):
                service.ensure(request)
        else:
            result = service.ensure(request)
            assert result.status.value == "missing" and result.acquisition.local_preparation["blocks_download"]
            assert result.acquisition.reason == "root_admission_denied"
        assert reads == [] and adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_sec_original_rejects_conflicting_issuer_even_when_index_claims_match(tmp_path):
    catalog = source_fact_fixture.lake(tmp_path)
    try:
        body = source_fact_fixture.html(cik="99999")
        ref, original = source_fact_fixture.imported(catalog, body, published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        catalog.record_source_facts(ref=ref, facts=facts, evidence=source_fact_fixture.evidence(ref, facts))
        adapter = _ExplodingAdapter()
        service = _ensure_service(catalog, tmp_path, adapter)

        with pytest.raises(SourceReadError, match="primary_issuer_conflict"):
            service.ensure(sec_request(allow_download=True))
        assert original.read_bytes() == body and adapter.discover_calls == adapter.fetch_calls == 0
    finally:
        catalog.close()


def test_sec_primary_bytes_can_complete_incomplete_listing_sidecar_identity(tmp_path):
    catalog = source_fact_fixture.lake(tmp_path)
    try:
        body = source_fact_fixture.html(cik="12345")
        ref, original = source_fact_fixture.imported(
            catalog, body, published="2026-07-30", declared_year=2026
        )
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        catalog.record_source_facts(
            ref=ref, facts=facts, evidence=source_fact_fixture.evidence(ref, facts)
        )

        row = catalog.reader.fetchone(
            "SELECT metadata_json FROM documents WHERE document_id=?", (ref.document_id,)
        )
        metadata = json.loads(row["metadata_json"])
        metadata["acquisition"].pop("market", None)
        metadata["acquisition"].pop("security_id", None)
        metadata["acquisition"]["candidate"].pop("market", None)
        with catalog.store.transaction() as connection:
            connection.execute(
                "UPDATE documents SET metadata_json=? WHERE document_id=?",
                (json.dumps(metadata), ref.document_id),
            )

        prepared = prepare_local_source(catalog, sec_request())

        assert prepared["status"] == "ready", prepared
        assert prepared["source_ref"]["content_sha256"] == ref.content_sha256
        assert original.read_bytes() == body
        assert prepared["download_events"] == 0
    finally:
        catalog.close()


@pytest.mark.parametrize("changed", [False, True])
def test_latest_provider_boundary_reverifies_only_after_discovery(tmp_path_factory, monkeypatch, changed):
    tmp_path = tmp_path_factory.mktemp("latest")
    catalog = _catalog(tmp_path, with_source=False)
    try:
        class ChangeAtDiscovery(_FakeAdapter):
            original = None
            discovery_returned = False

            def discover(self, request):
                if self.original is None:
                    return super().discover(request)
                self.discover_calls += 1
                if changed:
                    self.original.write_bytes(b"X" + original_body[1:])
                self.discovery_returned = True
                return ()

        adapter = ChangeAtDiscovery()
        service = _ensure_service(catalog, tmp_path, adapter)
        request = replace(_annual_request(market="HK"), security_id="01234")
        imported = service.ensure(request)
        assert imported.status.value == "imported"
        adapter.original = Path(imported.canonical_import.canonical_path)
        original_body = adapter.original.read_bytes()
        before = _observe_original_reads(monkeypatch, adapter.original, observe=lambda: not adapter.discovery_returned)
        after = _observe_original_reads(monkeypatch, adapter.original, observe=lambda: adapter.discovery_returned)

        latest = replace(request, mode="latest_as_of")
        if changed:
            with pytest.raises(SourceReadError, match="content_sha256_mismatch"):
                service.ensure(latest)
        else:
            reused = service.ensure(latest)
            assert reused.status.value == "reused"
            assert reused.acquisition.reason == "local_source_latest_as_of_provider_metadata"
        assert before == after == [(len(original_body),)]
        assert adapter.discover_calls == 2 and adapter.fetch_calls == 1
    finally:
        catalog.close()
