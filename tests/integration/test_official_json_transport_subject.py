"""Real dual-page imports, exact subject artifacts and source-verified transport.

Owned TEMP is restored. All bundles are constructed locally without model/provider
calls; this tests transport/source responsibility, not summarization quality.
"""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_official_json import (
    open_verified_projection,
    select_verified_projection,
)
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import (
    NarrativeReadRequest,
    NarrativeRef,
    NarrativeTransportError,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactDraft,
    NarrativeArtifactStore,
)
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs,
    persist_projection,
)
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_contract import EvidenceSpan

T0 = "2026-10-10T00:00:00Z"
T1 = "2026-10-10T00:00:01Z"


def encoded(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


@contextmanager
def owned_state(tmp_path):
    before = tuple(tmp_path.iterdir())
    with TemporaryDirectory(prefix="subject-artifacts-", dir=tmp_path) as name:
        root = Path(name)
        (root / "companies").mkdir()
        catalog = SourceCatalog(
            CatalogConfig(
                project_root=root,
                catalog_dir=root / "catalog",
                roots=(RootSpec("company_raw", root / "companies", "company_raw"),),
            )
        )
        refs, original = [], []
        try:
            for page in (1, 2):
                body = encoded(
                    {
                        "ok": True,
                        "result": {
                            "page": page,
                            "page_size": 2,
                            "page_count": 2,
                            "item_total": 4,
                            "items": [
                                {
                                    "ref": page * 10 + company,
                                    "org_id": company,
                                    "org_name": "Company " + str(company),
                                    "q": "When do new product qualification and overseas shipments begin?",
                                    "a": "Our new product has completed customer qualification and overseas shipments begin in the fourth quarter.",
                                    "answered": True,
                                    "created_at": "2026-09-01 10:00:00",
                                    "updated_at": "2026-09-01 10:00:00",
                                }
                                for company in (1, 2)
                            ],
                        },
                    }
                )
                request = {
                    "schema_version": "official-source-import-request/2",
                    "request_id": "subject-page-" + str(page),
                    "max_bytes": 1048576,
                    "content_sha256": digest(body),
                    "mime_type": "application/json",
                    "document_kind": "investor_relations",
                    "source_subject": {
                        "kind": "multi_issuer_event",
                        "event_namespace": "fixture",
                        "event_id": "901",
                        "issuer_refs": [],
                        "attribution_status": "partial",
                    },
                    "capture_receipt": {
                        "capture_method": "local_document",
                        "tool_name": "synthetic",
                        "tool_call_id": "page-" + str(page),
                        "captured_at": T0,
                        "response_bytes": len(body),
                        "content_sha256": digest(body),
                    },
                }
                result = import_official_json_source(
                    catalog, original=body, request=request
                )
                refs.append(result["source_ref"])
                original.append(body)
            projections = tuple(
                build_projection_from_refs(
                    catalog,
                    refs=refs,
                    layout_id="official-flat-list",
                    issuer={"provider_company_id": company},
                    as_of_date="2026-10-08",
                )
                for company in (1, 2)
            )
            for projection in projections:
                persist_projection(catalog, projection)
            subjects = tuple(
                NarrativeSubject.from_projection(projection)
                for projection in projections
            )
            with catalog.store.transaction() as connection:
                initial_documents = tuple(
                    row[0]
                    for row in connection.execute(
                        "SELECT document_id FROM documents ORDER BY document_id"
                    )
                )
                initial_sources = tuple(
                    row[0]
                    for row in connection.execute(
                        "SELECT source_id FROM sources ORDER BY source_id"
                    )
                )
            # Public import also registers provenance sidecars as sources. Compare
            # actual initial keys, not a guessed one-source-per-raw-file count.
            assert len(initial_documents) == 2
            objects = LocalNarrativeObjectStore(catalog.config.catalog_dir)
            artifacts = NarrativeArtifactStore(catalog.store, objects)
            state = SimpleNamespace(
                root=root,
                catalog=catalog,
                refs=refs,
                original=original,
                subjects=subjects,
                artifacts=artifacts,
                objects=objects,
            )
            yield state
            files = [
                p
                for p in (root / "companies").rglob("*.json")
                if not p.name.endswith(".source.json")
            ]
            assert len(files) == 2
            assert sorted(digest(p.read_bytes()) for p in files) == sorted(
                digest(b) for b in original
            )
            with catalog.store.transaction() as connection:
                assert (
                    tuple(
                        row[0]
                        for row in connection.execute(
                            "SELECT document_id FROM documents ORDER BY document_id"
                        )
                    )
                    == initial_documents
                )
                assert (
                    tuple(
                        row[0]
                        for row in connection.execute(
                            "SELECT source_id FROM sources ORDER BY source_id"
                        )
                    )
                    == initial_sources
                )
        finally:
            catalog.close()
    assert tuple(tmp_path.iterdir()) == before


def loader_for(state, calls):
    def load(subject):
        calls.append(subject)
        return open_verified_projection(
            state.catalog,
            projection_id=subject.item_key,
            expected_projection_sha256=subject.subject_sha256,
        )

    return load


def bundle_for(state, subject):
    view = loader_for(state, [])(subject)
    package = select_verified_projection(view, title="Business development Q&A")
    spans = package.evidence_spans
    assert spans and {span.source_id for span in spans} == {
        ref["source_id"] for ref in state.refs
    }
    answer = next(
        span
        for span in spans
        if span.structured_value["source_role"] in {"management", "company_filing"}
    )
    prompt_review = {
        "status": "not_reviewed",
        "source_sha256": None,
        "evidence_sha256": None,
        "policy_hash": None,
        "reviewed_at": None,
    }
    wire = {
        "schema_version": "narrative-bundle/3.0",
        "subject_binding": subject.to_dict(),
        "source_metadata": {
            "source_class": "official_json",
            "title": "Business development Q&A",
            "document_kind": "investor_relations",
            "language": view.language,
        },
        "quality_status": "verified",
        "selection": {
            "status": package.status,
            "coverage_complete": package.coverage_complete,
            "source_units": package.source_units,
            "candidate_count": package.candidate_count,
            "selected_count": len(spans),
            "omitted_candidate_count": package.omitted_candidate_count,
            "dropped_financial_count": package.dropped_financial_count,
            "pages_total": 2,
            "pages_read": 2,
            "lines_total": len(view.evidence_spans),
            "tables_total": 0,
            "tables_scanned": 0,
        },
        "evidence_spans": [span.to_dict() for span in spans],
        "summary": {
            "status": "completed",
            "translate": False,
            "draft": {
                "subject_id": subject.item_key,
                "subject_sha256": subject.subject_sha256,
                "language": view.language,
                "status": "draft",
                "claims": [
                    {
                        "claim_id": "business-update",
                        "text": answer.raw_text,
                        "evidence_ids": [answer.span_id],
                        "claim_type": "company_statement",
                        "modality": "planned",
                        "needs_review": False,
                    }
                ],
            },
            "model": {
                "adapter_id": "synthetic-local-model",
                "model_id": "synthetic-local",
                "prompt_version": "official-json/1.0.0",
                "response_sha256": "a" * 64,
            },
        },
        "prompt_review": prompt_review,
        "versions": {
            "parser": spans[0].parser_version,
            "selector": "1.0.0",
            "material": None,
            "model": "synthetic-local",
            "prompt": "official-json/1.0.0",
            "bundle_producer": "1.0.0",
        },
        "replay": {"required": True, "locator_count": len(spans)},
    }
    return NarrativeBundle.from_dict(wire).to_dict()


def publish(state, subject, label, wire=None, *, generation=None):
    wire = bundle_for(state, subject) if wire is None else wire
    payload = encoded(wire)
    generation = (
        digest((label + "-generation").encode()) if generation is None else generation
    )
    anchor = subject.anchor_ref
    draft = NarrativeArtifactDraft(
        effect_id=label,
        work_key=digest(label.encode()),
        document_id=anchor["document_id"],
        source_id=anchor["source_id"],
        source_sha256=anchor["content_sha256"],
        producer_name="fixture.narrative",
        producer_version="3.0",
        policy_sha256=digest(b"policy"),
        selection_status=wire.get("selection", {}).get("status", "selected"),
        quality_status=wire.get("quality_status", "verified"),
        metadata_json=encoded(
            {"subject_binding": subject.to_dict(), "generation_sha256": generation}
        ).decode(),
        created_at=T0,
    )
    prepared = state.artifacts.prepare(draft, payload)
    visible = state.artifacts.activate(
        label, verified_after_hash=prepared.content_sha256, activated_at=T1
    )
    return visible, generation, payload


def request(reference, *, issuer=None, cutoff="2026-10-08"):
    return NarrativeReadRequest.from_dict(
        {
            "schema_version": "narrative-read-request/2",
            "narrative_ref": reference.to_dict(),
            "as_of_date": cutoff,
            "expected_issuer": issuer,
        }
    )


def test_shared_anchor_exact_subject_generation_and_one_verified_export(
    tmp_path, monkeypatch
):
    with owned_state(tmp_path) as state:
        a, b = state.subjects
        va, ga, pa = publish(state, a, "a-one")
        va2, ga2, pa2 = publish(state, a, "a-two")
        vb, gb, pb = publish(state, b, "b-one")
        assert va.document_id == vb.document_id
        raw = NarrativeSubject.from_raw(state.refs[0])
        vr, _, _ = publish(state, raw, "legacy-raw", {"fixture": "old raw"})
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        opened = []
        real_open = SourceVersionReader.open_version

        def count_open(reader, source, **kwargs):
            opened.append(source.content_sha256)
            return real_open(reader, source, **kwargs)

        monkeypatch.setattr(SourceVersionReader, "open_version", count_open)
        ra = transport.reference_subject(a, generation_sha256=ga)
        rb = transport.reference_subject(b, generation_sha256=gb)
        assert calls == opened == [], "references observe SQL metadata only"
        assert ra.artifact_version_id == va.artifact_version_id
        assert rb.artifact_version_id == vb.artifact_version_id
        assert (
            transport.reference(
                NarrativeRef.from_dict(
                    {
                        "schema_version": "narrative-ref/1",
                        "artifact_version_id": "unused",
                        "artifact_sha256": "a" * 64,
                        "byte_size": 100,
                        "source_ref": raw.anchor_ref,
                    }
                ).source_ref
            ).artifact_version_id
            == vr.artifact_version_id
        )
        result = transport.read(request(ra, issuer={"provider_company_id": 1}))
        assert result.data == pa and calls == [a]
        assert opened == [ref["content_sha256"] for ref in state.refs]
        receipt = result.receipt
        assert set(receipt) == {
            "schema_version",
            "status",
            "narrative_ref",
            "subject_binding",
            "parent_source_refs",
            "as_of_date",
            "observed_at",
            "locator_count",
            "selection_status",
            "quality_status",
            "replay_status",
        }
        assert receipt["schema_version"] == "narrative-read-receipt/2"
        assert receipt["subject_binding"] == a.to_dict() and receipt[
            "parent_source_refs"
        ] == list(a.parent_source_refs)
        assert receipt["replay_status"] == "verified" and receipt[
            "locator_count"
        ] == len(json.loads(pa)["evidence_spans"])
        assert "manifest" not in receipt and "source_read_policy_sha256" not in receipt
        assert transport.read(request(rb, issuer={"provider_company_id": 2})).data == pb
        assert (
            transport.read(
                request(transport.reference_subject(a, generation_sha256=ga2))
            ).data
            == pa2
        )
        assert transport.read(request(ra, cutoff=None)).data == pa
        assert transport.read(request(ra, cutoff="2026-10-09")).data == pa
        assert va2.artifact_version_id != va.artifact_version_id


@pytest.mark.parametrize(
    "bad",
    ["issuer", "cutoff", "generation", "binding", "artifact_hash", "artifact_size"],
)
def test_wrong_read_context_refuses_without_reopening_source(tmp_path, bad):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        _, generation, _ = publish(state, a, "context")
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        wire = request(reference).to_dict()
        if bad == "issuer":
            wire["expected_issuer"] = {"provider_company_id": 2}
        elif bad == "cutoff":
            wire["as_of_date"] = "2026-10-07"
        elif bad == "generation":
            wire["narrative_ref"]["generation_sha256"] = "f" * 64
        elif bad == "binding":
            wire["narrative_ref"]["subject_binding"]["issuer"][
                "provider_company_id"
            ] = 2
        elif bad == "artifact_hash":
            wire["narrative_ref"]["artifact_sha256"] = "f" * 64
        else:
            wire["narrative_ref"]["byte_size"] += 1
        with pytest.raises(NarrativeTransportError):
            transport.read(NarrativeReadRequest.from_dict(wire))
        assert calls == []


@pytest.mark.parametrize("change", ["bytes", "status", "primary"])
def test_second_parent_is_revalidated_by_owning_layers(tmp_path, change):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        _, generation, _ = publish(state, a, "second-parent")
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        target = next(
            p
            for p in (state.root / "companies").rglob("*.json")
            if not p.name.endswith(".source.json")
            and p.read_bytes() == state.original[1]
        )
        try:
            if change == "bytes":
                target.write_bytes(state.original[1].replace(b"fourth", b"fifth", 1))
            else:
                with state.catalog.store.transaction() as connection:
                    if change == "status":
                        connection.execute(
                            "UPDATE documents SET source_status='retired' WHERE document_id=?",
                            (state.refs[1]["document_id"],),
                        )
                    else:
                        connection.execute(
                            "UPDATE documents SET primary_source_id=NULL WHERE document_id=?",
                            (state.refs[1]["document_id"],),
                        )
            with pytest.raises(NarrativeTransportError):
                transport.read(request(reference))
            assert len(calls) == (1 if change == "bytes" else 0)
        finally:
            if change == "bytes":
                target.write_bytes(state.original[1])


def test_artifact_corruption_is_not_a_cache_miss_or_a_source_read(tmp_path):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        version, generation, payload = publish(state, a, "corrupt")
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        target = state.catalog.config.catalog_dir / version.object_key
        target.write_bytes(b"X" * len(payload))
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(request(reference))
        assert error.value.reason == "narrative_artifact_corrupt" and calls == []


@pytest.mark.parametrize(
    "change", ["raw_text", "encoded_token_sha256", "coordinates", "parser"]
)
def test_resigned_artifact_can_never_fabricate_verified_native_field(tmp_path, change):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        wire = bundle_for(state, a)
        original = EvidenceSpan.from_dict(wire["evidence_spans"][0])
        metadata = deepcopy(original.to_dict()["structured_value"])
        text = original.raw_text
        coordinates = original.coordinates
        parser = original.parser_name
        if change == "raw_text":
            text = "Fabricated product revenue growth."
            metadata["text_sha256"] = digest(text.encode())
        elif change == "encoded_token_sha256":
            metadata[change] = "f" * 64
        elif change == "coordinates":
            from dataclasses import replace

            coordinates = replace(coordinates, paragraph_index=999)
        else:
            parser = "invented"
        forged = EvidenceSpan.create(
            source_id=original.source_id,
            coordinates=coordinates,
            raw_text=text,
            structured_value=metadata,
            parser_name=parser,
            parser_version=original.parser_version,
            parse_status=original.parse_status,
            quality_flags=original.quality_flags,
        )
        wire["evidence_spans"][0] = forged.to_dict()
        for claim in wire["summary"]["draft"]["claims"]:
            claim["evidence_ids"] = [
                forged.span_id if x == original.span_id else x
                for x in claim["evidence_ids"]
            ]
        wire = NarrativeBundle.from_dict(wire).to_dict()
        _, generation, _ = publish(state, a, "forged-" + change, wire)
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(request(reference))
        assert error.value.reason == "locator_replay_failed" and calls == [a]


def test_missing_or_wrong_loader_refuses_without_faking_anchor_projection(tmp_path):
    with owned_state(tmp_path) as state:
        a, b = state.subjects
        _, generation, _ = publish(state, a, "wrong-loader")
        transport = NarrativeTransportReader(
            state.artifacts, SourceVersionReader(state.catalog)
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(request(reference))
        assert error.value.reason == "projection_loader_unavailable"
        other = loader_for(state, [])(b)
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=lambda subject: other,
        )
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(request(reference))
        assert error.value.reason == "projection_identity_mismatch"


def test_wrong_subject_generation_discovery_never_uses_anchor_latest(tmp_path):
    with owned_state(tmp_path) as state:
        a, b = state.subjects
        _, generation, _ = publish(state, a, "only-a")
        transport = NarrativeTransportReader(
            state.artifacts, SourceVersionReader(state.catalog)
        )
        for subject, gen in [(b, generation), (a, "f" * 64)]:
            with pytest.raises(NarrativeTransportError) as error:
                transport.reference_subject(subject, generation_sha256=gen)
            assert error.value.reason == "narrative_artifact_not_visible"


@pytest.mark.parametrize("change", ["language", "generation_parser"])
def test_resigned_artifact_cannot_misstate_verified_projection_metadata(
    tmp_path, change
):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        wire = bundle_for(state, a)
        if change == "language":
            wire["source_metadata"]["language"] = "zh"
            wire["summary"]["draft"]["language"] = "zh"
        else:
            wire["versions"]["parser"] = "999.0.0"
        wire = NarrativeBundle.from_dict(wire).to_dict()
        _, generation, _ = publish(state, a, "metadata-" + change, wire)
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        reference = transport.reference_subject(a, generation_sha256=generation)
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(request(reference))
        assert error.value.reason == "locator_replay_failed" and calls == [a]
