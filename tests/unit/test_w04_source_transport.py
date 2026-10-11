"""W04 source facts and bounded projected transport; zero network/model calls."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeRef, NarrativeTransportError
from company_wiki.automation.narrative_evidence_view import NarrativeEvidenceViewReader, NarrativeEvidenceViewQuery
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.narrative_transport_cli import _dispatch
from integration.test_official_json_transport_subject import owned_state, publish, loader_for, bundle_for
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore, NarrativeArtifactStore
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import build_projection_from_refs, persist_projection
from company_wiki.automation.narrative_official_json import open_verified_projection, select_verified_projection
from company_wiki.source_contract import EvidenceSpan


def wire_bytes(value):
    return canonical_json(value).encode("utf-8") + b"\n"


def compact(subject):
    return {"schema_version": "narrative-subject-ref/1", "kind": "official_json",
            "item_key": subject.item_key, "subject_sha256": subject.subject_sha256}


def read_request(reference, **constraints):
    return NarrativeReadRequest.from_dict({
        "schema_version": "narrative-read-request/3", "narrative_ref": reference,
        "as_of_date": constraints.get("cutoff", "2026-10-08"),
        "expected_issuer": constraints.get("issuer")})


@pytest.mark.parametrize("kind,ready", [
    ("investor_relations", True), ("broker_research", True),
    ("annual_report", False), ("quarterly_report", False),
    ("semi_annual_report", False), ("investor_call_transcript", False),
])
def test_capture_capability_requires_period_only_for_periodic_sources(tmp_path, kind, ready):
    root = tmp_path / "companies" / "Acme" / "raw"
    root.mkdir(parents=True)
    raw = root / "source.pdf"
    body = b"%PDF-1.4 Our product pipeline and customer qualification expanded."
    raw.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    raw.with_name(raw.name + ".source.json").write_text(json.dumps({
        "schema_version": "1.0", "company_name": "Acme", "canonical_entity_id": "ent-acme",
        "display_name": "Acme", "market": "US", "security_id": "ACME",
        "document_kind": kind, "source_title": "Acme source",
        "published_date": "2026-09-01", "source_url": "https://example.org/source",
        "retrieved_at": "2026-10-10T00:00:00Z", "collector_name": "offline-fixture",
        "collector_version": "1", "content_sha256": digest,
    }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", (
        RootSpec("company_raw", tmp_path / "companies", "company_raw"),
    )))
    try:
        catalog.scan()
        row = catalog.reader.fetchone("SELECT d.document_id,d.primary_source_id FROM documents d "
            "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?", (digest,))
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["primary_source_id"], digest)
        candidate = reader.describe_candidate(ref)
        assert candidate["fiscal_year"] is None
        assert candidate["fiscal_period"] is None
        assert candidate["capture_ready"] is ready
        assert reader.open_version(ref, purpose="source_export").data == body
        assert reader.query_local(SourceRequest(entity="Acme", market="US", security_id="ACME",
            document_kind=kind, fiscal_year=2026, as_of_date="2026-10-08")).matches == ()
        assert asdict(ref) == candidate["source_ref"]
    finally:
        catalog.close()


def test_compact_projected_public_operations_keep_full_lineage_and_verify_once(tmp_path, monkeypatch):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        version, generation, payload = publish(state, subject, "w04-compact")
        calls = []
        transport = NarrativeTransportReader(state.artifacts, SourceVersionReader(state.catalog),
            projection_ref_resolver=loader_for(state, calls))
        request = {"schema_version": "narrative-reference-request/3", "subject_ref": compact(subject),
                   "generation_sha256": generation}
        reference_bytes, receipt = _dispatch("reference", request, transport)
        reference = json.loads(reference_bytes)
        assert set(reference) == {"schema_version", "artifact_version_id", "artifact_sha256",
                                  "byte_size", "generation_sha256", "subject_ref"}
        assert reference["schema_version"] == "narrative-ref/3"
        assert reference["subject_ref"] == compact(subject)
        assert receipt == {"schema_version": "narrative-read-receipt/3", "status": "metadata_only",
                           "narrative_ref": reference}
        assert NarrativeRef.from_dict(reference).to_dict() == reference
        parsed = read_request(reference, issuer={"provider_company_id": 1})
        opened = []
        original_open = SourceVersionReader.open_version
        def count_open(reader, source, **kwargs):
            opened.append(source.content_sha256)
            return original_open(reader, source, **kwargs)
        monkeypatch.setattr(SourceVersionReader, "open_version", count_open)
        result = transport.read(parsed)
        assert result.data == payload
        assert sorted(opened) == sorted(ref["content_sha256"] for ref in state.refs)
        assert result.receipt["schema_version"] == "narrative-read-receipt/3"
        assert set(result.receipt) == {"schema_version", "status", "narrative_ref", "as_of_date",
            "observed_at", "locator_count", "parent_count", "lineage_sha256", "selection_status",
            "quality_status", "replay_status"}
        assert result.receipt["parent_count"] == 2
        lineage = hashlib.sha256(canonical_json(subject.to_dict()).encode()).hexdigest()
        assert result.receipt["lineage_sha256"] == lineage
        assert json.loads(result.data)["subject_binding"] == subject.to_dict()
        opened.clear()
        view = NarrativeEvidenceViewReader(transport).read(parsed, NarrativeEvidenceViewQuery("evidence-list", limit=1))
        body = json.loads(view.data)
        assert body["schema_version"] == "narrative-evidence-view/3"
        assert body["parent_source_refs"] == list(subject.parent_source_refs)
        assert body["subject_binding"] == subject.to_dict()
        assert body["total"] > len(body["items"]) == 1
        assert view.receipt["schema_version"] == "narrative-evidence-read-receipt/3"
        assert view.receipt["lineage_sha256"] == lineage
        assert view.receipt["parent_count"] == 2
        assert sorted(opened) == sorted(ref["content_sha256"] for ref in state.refs)
        for wire in (request, reference, receipt, parsed.to_dict(), result.receipt, view.receipt):
            assert len(wire_bytes(wire)) <= 16384
        assert len(result.data) <= 1310720


@pytest.mark.parametrize("mutation", ["extra", "wrong_kind", "wrong_id", "bad_sha", "raw_anchor"])
def test_compact_reference_refuses_mixed_and_inconsistent_identity(mutation):
    value = {"schema_version": "narrative-ref/3", "artifact_version_id": "w04-version",
             "artifact_sha256": "a" * 64, "byte_size": 1024, "generation_sha256": "b" * 64,
             "subject_ref": {"schema_version": "narrative-subject-ref/1", "kind": "official_json",
                 "item_key": "urn:company-wiki:source-projection:sha256:" + "c" * 64,
                 "subject_sha256": "c" * 64}}
    if mutation == "extra":
        value["subject_ref"]["parent_source_refs"] = []
    elif mutation == "wrong_kind":
        value["subject_ref"]["kind"] = "raw"
    elif mutation == "wrong_id":
        value["subject_ref"]["item_key"] += "d"
    elif mutation == "bad_sha":
        value["subject_ref"]["subject_sha256"] = "C" * 64
    else:
        value["source_ref"] = {}
    with pytest.raises(ValueError):
        NarrativeRef.from_dict(value)


@contextmanager
def large_owned_state(tmp_path):
    before = tuple(tmp_path.iterdir())
    with TemporaryDirectory(prefix="w04-65-", dir=tmp_path) as temporary:
        root = Path(temporary)
        (root / "companies").mkdir()
        catalog = SourceCatalog(CatalogConfig(root, root / "catalog", (
            RootSpec("company_raw", root / "companies", "company_raw"),)))
        refs, originals = [], []
        try:
            for page in range(65):
                first, last = page * 4, min((page + 1) * 4, 257)
                body = canonical_json({"ok": True, "result": {"page": page + 1,
                    "page_size": 4, "page_count": 65, "item_total": 257,
                    "items": [{"ref": index, "org_id": index % 24 + 1,
                        "org_name": "Company " + str(index % 24 + 1),
                        "q": "When do new product qualification and overseas shipments begin?",
                        "a": "Our new product completed customer qualification and overseas shipments begin in the fourth quarter.",
                        "answered": True, "created_at": "2026-09-01 10:00:00",
                        "updated_at": "2026-09-01 10:00:00"} for index in range(first, last)]}}).encode()
                digest = hashlib.sha256(body).hexdigest()
                imported = import_official_json_source(catalog, original=body, request={
                    "schema_version": "official-source-import-request/2",
                    "request_id": "w04-page-" + str(page), "max_bytes": 1048576,
                    "content_sha256": digest, "mime_type": "application/json",
                    "document_kind": "investor_relations", "source_subject": {
                        "kind": "multi_issuer_event", "event_namespace": "w04-fixture",
                        "event_id": "65", "issuer_refs": [], "attribution_status": "partial"},
                    "capture_receipt": {"capture_method": "local_document", "tool_name": "synthetic",
                        "tool_call_id": str(page), "captured_at": "2026-10-10T00:00:00Z",
                        "response_bytes": len(body), "content_sha256": digest}})
                refs.append(imported["source_ref"])
                originals.append(body)
            projection = build_projection_from_refs(catalog, refs=refs, layout_id="official-flat-list",
                issuer={"provider_company_id": 1}, as_of_date="2026-10-08", projection_version="1.0.2")
            assert len(projection.parent_source_refs) == 65 and len(projection.records) == 257
            persist_projection(catalog, projection)
            subject = NarrativeSubject.from_projection(projection)
            view = open_verified_projection(catalog, projection_id=subject.item_key,
                expected_projection_sha256=subject.subject_sha256)
            selected = select_verified_projection(view, title="Business development Q&A")
            selected_parents = {span.source_id for span in selected.evidence_spans}
            state = SimpleNamespace(catalog=catalog, root=root,
                refs=[ref for ref in refs if ref["source_id"] in selected_parents],
                artifacts=NarrativeArtifactStore(catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir)))
            yield state, subject, refs
            files = [path for path in (root / "companies").rglob("*.json")
                     if not path.name.endswith(".source.json")]
            assert sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in files) == sorted(
                hashlib.sha256(body).hexdigest() for body in originals)
        finally:
            catalog.close()
    assert tuple(tmp_path.iterdir()) == before


def test_compact_65_parent_wire_stays_small_without_truncating_body(tmp_path, monkeypatch):
    with large_owned_state(tmp_path) as (state, subject, all_refs):
        wire = bundle_for(state, subject)
        _, generation, payload = publish(state, subject, "w04-65", wire=wire)
        assert len(wire_bytes(subject.to_dict())) > 16384
        transport = NarrativeTransportReader(state.artifacts, SourceVersionReader(state.catalog),
            projection_ref_resolver=loader_for(state, []))
        data, metadata = _dispatch("reference", {"schema_version": "narrative-reference-request/3",
            "subject_ref": compact(subject), "generation_sha256": generation}, transport)
        parsed = read_request(json.loads(data))
        calls = []
        real_open = SourceVersionReader.open_version
        def count(reader, source, **kwargs):
            calls.append(source.content_sha256)
            return real_open(reader, source, **kwargs)
        monkeypatch.setattr(SourceVersionReader, "open_version", count)
        result = transport.read(parsed)
        assert result.data == payload and len(result.data) <= 1310720
        assert sorted(calls) == sorted(ref["content_sha256"] for ref in all_refs)
        assert result.receipt["parent_count"] == 65
        assert json.loads(result.data)["subject_binding"] == subject.to_dict()
        evidence = NarrativeEvidenceViewReader(transport).read(parsed, NarrativeEvidenceViewQuery("evidence-list", limit=1))
        assert len(json.loads(evidence.data)["parent_source_refs"]) == 65
        assert json.loads(evidence.data)["subject_binding"] == subject.to_dict()
        for value in (json.loads(data), metadata, parsed.to_dict(), result.receipt, evidence.receipt):
            assert len(wire_bytes(value)) <= 16384


@pytest.mark.parametrize("mutation,reason", [
    ("issuer", "projection_issuer_mismatch"), ("asof", "projection_after_as_of"),
    ("generation", "artifact_reference_mismatch"), ("parent", "no_verified_location"),
    ("pointer", "locator_replay_failed"),
])
def test_compact_read_preserves_native_refusals(tmp_path, mutation, reason):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        wire = bundle_for(state, subject)
        if mutation == "pointer":
            original = EvidenceSpan.from_dict(wire["evidence_spans"][0])
            fields = dict(original.structured_value)
            fields["pointer"] = "/fabricated/pointer"
            forged = EvidenceSpan.create(source_id=original.source_id,
                coordinates=original.coordinates, raw_text=original.raw_text, structured_value=fields,
                parser_name=original.parser_name, parser_version=original.parser_version,
                parse_status=original.parse_status, quality_flags=original.quality_flags)
            wire["evidence_spans"][0] = forged.to_dict()
            for claim in wire["summary"]["draft"]["claims"]:
                claim["evidence_ids"] = [forged.span_id if value == original.span_id else value
                                         for value in claim["evidence_ids"]]
        _, generation, _ = publish(state, subject, "w04-" + mutation, wire=wire)
        transport = NarrativeTransportReader(state.artifacts, SourceVersionReader(state.catalog),
            projection_ref_resolver=loader_for(state, []))
        data, _ = _dispatch("reference", {"schema_version": "narrative-reference-request/3",
            "subject_ref": compact(subject), "generation_sha256": generation}, transport)
        reference = json.loads(data)
        constraints = {}
        if mutation == "issuer":
            constraints["issuer"] = {"provider_company_id": 999}
        elif mutation == "asof":
            constraints["cutoff"] = "2026-10-07"
        elif mutation == "generation":
            reference["generation_sha256"] = "f" * 64
        changed = None
        if mutation == "parent":
            changed = next(path for path in (state.root / "companies").rglob("*.json")
                           if not path.name.endswith(".source.json"))
            before = changed.read_bytes()
            changed.write_bytes(before + b" ")
        try:
            with pytest.raises(NarrativeTransportError) as failure:
                transport.read(read_request(reference, **constraints))
            assert failure.value.reason == reason
        finally:
            if changed is not None:
                changed.write_bytes(before)
