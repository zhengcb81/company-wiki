"""Subject catalog identity over real imported shared pages, with owned cleanup.

This tests durable artifact/state relationships. Source bytes and projection
semantics are verified by the actual importer/projection port in setup, not by
re-parsing them inside artifact storage. No provider or model is called.
"""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactConflictError, NarrativeArtifactDraft,
    NarrativeArtifactNotVisibleError, NarrativeArtifactStore, NarrativeSourceNotCurrentError,
)
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import build_projection_from_refs
from company_wiki.source_catalog.service import SourceCatalog

T0 = "2026-10-10T00:00:00Z"
T1 = "2026-10-10T00:00:01Z"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


@contextmanager
def owned_state(tmp_path):
    before = tuple(tmp_path.iterdir())
    with TemporaryDirectory(prefix="subject-artifacts-", dir=tmp_path) as name:
        root = Path(name)
        (root / "companies").mkdir()
        catalog = SourceCatalog(CatalogConfig(project_root=root, catalog_dir=root / "catalog",
            roots=(RootSpec("company_raw", root / "companies", "company_raw"),)))
        refs, original = [], []
        try:
            for page in (1, 2):
                body = encoded({"ok": True, "result": {"page": page, "page_size": 2,
                    "page_count": 2, "item_total": 4, "items": [
                    {"ref": page * 10 + company, "org_id": company, "org_name": "Company " + str(company),
                     "q": "New business delivery?", "a": "Q4 delivery", "answered": True,
                     "created_at": "2026-09-01 10:00:00", "updated_at": "2026-09-01 10:00:00"}
                    for company in (1, 2)]}})
                request = {"schema_version": "official-source-import-request/2",
                    "request_id": "subject-page-" + str(page), "max_bytes": 1048576,
                    "content_sha256": digest(body), "mime_type": "application/json",
                    "document_kind": "investor_relations", "source_subject": {
                        "kind": "multi_issuer_event", "event_namespace": "fixture",
                        "event_id": "901", "issuer_refs": [], "attribution_status": "partial"},
                    "capture_receipt": {"capture_method": "local_document", "tool_name": "synthetic",
                        "tool_call_id": "page-" + str(page), "captured_at": T0,
                        "response_bytes": len(body), "content_sha256": digest(body)}}
                result = import_official_json_source(catalog, original=body, request=request)
                refs.append(result["source_ref"])
                original.append(body)
            subjects = tuple(NarrativeSubject.from_projection(build_projection_from_refs(catalog,
                refs=refs, layout_id="official-flat-list", issuer={"provider_company_id": company},
                as_of_date="2026-10-08")) for company in (1, 2))
            with catalog.store.transaction() as connection:
                initial_documents = tuple(row[0] for row in connection.execute("SELECT document_id FROM documents ORDER BY document_id"))
                initial_sources = tuple(row[0] for row in connection.execute("SELECT source_id FROM sources ORDER BY source_id"))
            # Public import also registers provenance sidecars as sources. Compare
            # actual initial keys, not a guessed one-source-per-raw-file count.
            assert len(initial_documents) == 2
            objects = LocalNarrativeObjectStore(catalog.config.catalog_dir)
            artifacts = NarrativeArtifactStore(catalog.store, objects)
            state = SimpleNamespace(root=root, catalog=catalog, refs=refs, original=original,
                subjects=subjects, artifacts=artifacts, objects=objects)
            yield state
            files = [p for p in (root / "companies").rglob("*.json") if not p.name.endswith(".source.json")]
            assert len(files) == 2
            assert sorted(digest(p.read_bytes()) for p in files) == sorted(digest(b) for b in original)
            with catalog.store.transaction() as connection:
                assert tuple(row[0] for row in connection.execute("SELECT document_id FROM documents ORDER BY document_id")) == initial_documents
                assert tuple(row[0] for row in connection.execute("SELECT source_id FROM sources ORDER BY source_id")) == initial_sources
        finally:
            catalog.close()
    assert tuple(tmp_path.iterdir()) == before


def draft_for(state, subject, label, *, metadata_override=None):
    anchor = subject.anchor_ref
    generation = digest((label + "-generation").encode())
    metadata = {"generation_sha256": generation, "subject_binding": subject.to_dict()}
    if metadata_override is not None:
        metadata = metadata_override
    draft = NarrativeArtifactDraft(effect_id=label, work_key=digest(label.encode()),
        document_id=anchor["document_id"], source_id=anchor["source_id"], source_sha256=anchor["content_sha256"],
        producer_name="fixture.narrative", producer_version="3.0", policy_sha256=digest(b"policy"),
        selection_status="selected", quality_status="verified", metadata_json=encoded(metadata).decode(), created_at=T0)
    return draft, generation


def publish(state, subject, label, *, metadata_override=None):
    draft, generation = draft_for(state, subject, label, metadata_override=metadata_override)
    payload = encoded({"subject_binding": subject.to_dict(), "label": label})
    version = state.artifacts.prepare(draft, payload)
    visible = state.artifacts.activate(draft.effect_id, verified_after_hash=version.content_sha256, activated_at=T1)
    return visible, generation, payload


@contextmanager
def readers(state):
    reader = NarrativeArtifactStore.for_reading(state.catalog.config.database_path, state.objects)
    try:
        yield (state.artifacts, reader)
    finally:
        reader.close()


@pytest.mark.parametrize("raw_binding", ["missing", "null", "raw"])
def test_shared_projection_versions_never_pollute_legacy_raw_reads(tmp_path, raw_binding):
    with owned_state(tmp_path) as state:
        raw = NarrativeSubject.from_raw(state.refs[0])
        label = "raw"
        generation = digest((label + "-generation").encode())
        metadata = {"generation_sha256": generation}
        if raw_binding != "missing":
            metadata["subject_binding"] = None if raw_binding == "null" else raw.to_dict()
        old, _, old_payload = publish(state, raw, label, metadata_override=metadata)
        a, _, _ = publish(state, state.subjects[0], "project-a",
            metadata_override={"subject_binding": state.subjects[0].to_dict(), "generation_sha256": generation})
        publish(state, state.subjects[1], "project-b")
        anchor = raw.anchor_ref
        kwargs = dict(document_id=anchor["document_id"], source_id=anchor["source_id"],
            source_sha256=anchor["content_sha256"])
        with readers(state) as accessors:
            for accessor in accessors:
                assert accessor.latest_visible_version(**kwargs).artifact_version_id == old.artifact_version_id
                assert accessor.read_exact(artifact_version_id=old.artifact_version_id, **kwargs)[1] == old_payload
                with pytest.raises(NarrativeArtifactNotVisibleError):
                    accessor.read_exact(artifact_version_id=a.artifact_version_id, **kwargs)
            assert accessors[1].visible_generation_candidates(generation_sha256=generation, **kwargs) == (old,)
        assert state.artifacts.read_visible(**kwargs)[1] == old_payload


def test_exact_subject_and_generation_survive_reopen_without_fake_sources(tmp_path):
    with owned_state(tmp_path) as state:
        a, b = state.subjects
        va, ga, pa = publish(state, a, "a-generation-one")
        va2, ga2, _ = publish(state, a, "a-generation-two")
        vb, gb, pb = publish(state, b, "b-generation-one")
        assert va.document_id == vb.document_id == a.anchor_ref["document_id"]
        assert va.source_id == vb.source_id == a.anchor_ref["source_id"]
        with readers(state) as accessors:
            for accessor in accessors:
                assert accessor.visible_subject_generation_candidates(subject=a, generation_sha256=ga) == (va,)
                assert accessor.visible_subject_generation_candidates(subject=a, generation_sha256=ga2) == (va2,)
                assert accessor.visible_subject_generation_candidates(subject=b, generation_sha256=gb) == (vb,)
                assert accessor.visible_subject_generation_candidates(subject=b, generation_sha256=ga) == ()
                assert accessor.read_current_subject(artifact_version_id=va.artifact_version_id,
                    subject=a, generation_sha256=ga, expected_sha256=va.content_sha256, expected_size=va.byte_size) == (va, pa)
                assert accessor.read_current_subject(artifact_version_id=vb.artifact_version_id,
                    subject=b, generation_sha256=gb) == (vb, pb)
                for subject, generation in [(b, ga), (a, ga2)]:
                    with pytest.raises(NarrativeArtifactConflictError):
                        accessor.read_current_subject(artifact_version_id=va.artifact_version_id,
                            subject=subject, generation_sha256=generation)
                with pytest.raises(NarrativeArtifactConflictError):
                    accessor.read_current_subject(artifact_version_id=va.artifact_version_id,
                        subject=a, generation_sha256=ga, expected_sha256="f" * 64)


def change_second_parent(state, mutation):
    second = state.refs[1]
    with state.catalog.store.transaction() as connection:
        if mutation == "status":
            connection.execute("UPDATE documents SET source_status='retired' WHERE document_id=?", (second["document_id"],))
        elif mutation == "primary":
            connection.execute("UPDATE documents SET primary_source_id=? WHERE document_id=?",
                (state.refs[0]["source_id"], second["document_id"]))
        else:
            connection.execute("UPDATE sources SET content_sha256=? WHERE source_id=?", ("f" * 64, second["source_id"]))


@pytest.mark.parametrize("stage", ["prepare", "activate", "read", "candidate", "effect"])
@pytest.mark.parametrize("mutation", ["status", "primary", "catalog_sha"])
def test_nonanchor_parent_change_rejects_every_state_boundary(tmp_path, stage, mutation):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        draft, generation = draft_for(state, a, "second-parent")
        payload = encoded({"subject_binding": a.to_dict()})
        version = None
        if stage != "prepare":
            version = state.artifacts.prepare(draft, payload)
        if stage not in {"prepare", "activate"}:
            state.artifacts.activate(draft.effect_id, verified_after_hash=version.content_sha256, activated_at=T1)
        change_second_parent(state, mutation)
        if stage == "prepare":
            with pytest.raises(NarrativeSourceNotCurrentError):
                state.artifacts.prepare(draft, payload)
            assert not list((state.root / "catalog" / "objects").rglob("*.json"))
        elif stage == "activate":
            with pytest.raises(NarrativeSourceNotCurrentError):
                state.artifacts.activate(draft.effect_id, verified_after_hash=version.content_sha256, activated_at=T1)
        else:
            with readers(state) as accessors:
                for accessor in accessors:
                    with pytest.raises(NarrativeSourceNotCurrentError):
                        if stage == "read":
                            accessor.read_current_subject(artifact_version_id=version.artifact_version_id,
                                subject=a, generation_sha256=generation)
                        elif stage == "candidate":
                            accessor.visible_subject_generation_candidates(subject=a, generation_sha256=generation)
                        else:
                            accessor.visible_version_for_effect(draft.effect_id)


@pytest.mark.parametrize("reader_kind", ["store", "readonly"])
def test_parent_change_during_artifact_open_is_rechecked(tmp_path, monkeypatch, reader_kind):
    with owned_state(tmp_path) as state:
        a = state.subjects[0]
        version, generation, _ = publish(state, a, "race")
        original_read = state.objects.read
        def changing_read(*args, **kwargs):
            data = original_read(*args, **kwargs)
            change_second_parent(state, "status")
            return data
        monkeypatch.setattr(state.objects, "read", changing_read)
        with readers(state) as accessors:
            accessor = accessors[0 if reader_kind == "store" else 1]
            with pytest.raises(NarrativeSourceNotCurrentError):
                accessor.read_current_subject(artifact_version_id=version.artifact_version_id,
                    subject=a, generation_sha256=generation)


@pytest.mark.parametrize("damage", ["anchor", "binding", "generation"])
def test_inconsistent_subject_draft_is_typed_and_never_written(tmp_path, damage):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        draft, _ = draft_for(state, subject, "invalid")
        if damage == "anchor":
            second = state.refs[1]
            draft = replace(draft, document_id=second["document_id"], source_id=second["source_id"], source_sha256=second["content_sha256"])
        else:
            metadata = json.loads(draft.metadata_json)
            if damage == "binding":
                metadata["subject_binding"]["item_key"] = "urn:invalid"
            else:
                metadata["generation_sha256"] = "no-hash"
            draft = replace(draft, metadata_json=encoded(metadata).decode())
        with pytest.raises(NarrativeArtifactConflictError):
            state.artifacts.prepare(draft, b'{}')
        assert not list((state.root / "catalog" / "objects").rglob("*.json"))


@pytest.mark.parametrize("field", ["issuer", "as_of_date", "adapter", "coverage", "parent_source_refs"])
def test_matching_id_and_hash_do_not_hide_a_changed_subject_context(tmp_path, field):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        version, generation, _ = publish(state, subject, "context")
        wire = subject.to_dict()
        if field == "issuer":
            wire["issuer"]["provider_company_id"] = 999
        elif field == "as_of_date":
            wire[field] = "2026-10-09"
        elif field == "adapter":
            wire[field]["layout_fingerprint"] = "f" * 64
        elif field == "coverage":
            wire[field]["pagination_complete"] = False
        else:
            wire[field][1] = wire[field][0]
        changed = NarrativeSubject.from_dict(wire)
        assert changed.item_key == subject.item_key and changed.subject_sha256 == subject.subject_sha256
        with readers(state) as accessors:
            for accessor in accessors:
                with pytest.raises(NarrativeArtifactConflictError):
                    accessor.visible_subject_generation_candidates(subject=changed, generation_sha256=generation)
                with pytest.raises(NarrativeArtifactConflictError):
                    accessor.read_current_subject(artifact_version_id=version.artifact_version_id,
                        subject=changed, generation_sha256=generation)
