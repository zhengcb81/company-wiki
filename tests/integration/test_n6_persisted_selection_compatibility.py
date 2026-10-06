"""Frozen 0.3.2 finals survive later selection and grouping policies.

Fixtures were published once by the actual three jobs/outbox before this test
was written. Reading never regenerates historical spans with the new selector.
Synthetic raw and a deterministic local model do not prove vendor quality.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation import narrative_select
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import (
    NarrativeReadRequest, NarrativeTransportError,
)
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactDraft, NarrativeArtifactStore,
)
from company_wiki.source_catalog import narrative_evidence
from company_wiki.source_contract import EvidenceSpan
from integration.test_narrative_runtime_e2e import _new_catalog


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "n6_main_compatibility"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _publish(artifacts, bundle: NarrativeBundle, payload: bytes, *, label: str):
    draft = NarrativeArtifactDraft(
        effect_id=f"n6-{label}", work_key=_sha(label.encode()),
        document_id=bundle.source_ref.document_id,
        source_id=bundle.source_ref.source_id,
        source_sha256=bundle.source_ref.content_sha256,
        producer_name="company_wiki.narrative_bundle",
        producer_version=bundle.versions.bundle_producer,
        policy_sha256=bundle.expected_read_policy_sha256,
        selection_status=bundle.selection.status, quality_status=bundle.quality_status,
        metadata_json=canonical_json({"bundle_schema": bundle.schema_version}),
        created_at="2026-10-06T00:00:00Z",
    )
    prepared = artifacts.prepare(draft, payload)
    return artifacts.activate(
        draft.effect_id, verified_after_hash=prepared.content_sha256,
        activated_at="2026-10-06T00:00:01Z" if label == "legacy" else "2026-10-06T00:00:02Z",
    )


@contextmanager
def _frozen_lake(tmp_path: Path, kind: str):
    baseline = tuple(sorted(path.name for path in tmp_path.iterdir()))
    root = tmp_path / "nf"
    assert not root.exists()
    root.mkdir()
    catalog = None
    try:
        fixture = json.loads((FIXTURES / f"{kind}.json").read_text(encoding="utf-8"))
        assert fixture["schema_version"] == "n6-frozen-narrative-fixture/1"
        assert fixture["provenance"]["selector_version"] == "0.3.2"
        raw = base64.b64decode(fixture["source_base64"], validate=True)
        payload = fixture["bundle_utf8"].encode("utf-8")
        assert _sha(raw) == fixture["source_sha256"]
        assert _sha(payload) == fixture["bundle_sha256"]
        bundle = NarrativeBundle.from_dict(json.loads(payload))
        assert canonical_json(bundle.to_dict()).encode() == payload
        assert bundle.versions.selector == "0.3.2" and bundle.evidence_spans
        spec = {**fixture["source_spec"], "data": raw}
        catalog, source_reader, indexed = _new_catalog(root, [spec])
        assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == 0
        assert len(indexed) == 1
        _, actual_ref = next(iter(indexed.values()))
        assert asdict(actual_ref) == bundle.source_ref.to_dict()
        artifacts = NarrativeArtifactStore(
            catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        _publish(artifacts, bundle, payload, label="legacy")
        transport = NarrativeTransportReader(artifacts, source_reader)
        reference = transport.reference(bundle.source_ref)
        request = NarrativeReadRequest.from_dict({
            "schema_version": "narrative-read-request/1",
            "narrative_ref": reference.to_dict(), "as_of_date": "2026-09-01",
            "expected_source": fixture["expected_source"],
        })
        raw_path = next((root / "companies").rglob(spec["name"]))
        yield root, raw_path, raw, payload, bundle, artifacts, transport, request
        assert raw_path.read_bytes() == raw
    finally:
        if catalog is not None:
            catalog.close()
        assert root.resolve().parent == tmp_path.resolve() and not root.is_symlink()
        shutil.rmtree(root)
        assert not root.exists()
        assert tuple(sorted(path.name for path in tmp_path.iterdir())) == baseline


def _disable_new_selection(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("reading a frozen final must not run current selection")

    for module in (narrative_evidence, narrative_select):
        monkeypatch.setattr(module, "NARRATIVE_SELECTOR_VERSION", "0.4.0")
        monkeypatch.setattr(module, "select_narrative_evidence", forbidden)
    monkeypatch.setattr(narrative_select.NarrativeSelectHandler, "_run_selector", forbidden)


def _persistent_bytes(root):
    # SQLite SHM read marks are not persistent source or artifact state.
    return {path.relative_to(root).as_posix(): _sha(path.read_bytes())
            for path in root.rglob("*") if path.is_file() and not path.name.endswith("-shm")}


@pytest.mark.parametrize("kind", ["txt", "json", "pdf"])
def test_frozen_final_reads_without_current_selection(tmp_path, monkeypatch, kind):
    (tmp_path / "keep.txt").write_bytes(b"existing independent test material")
    with _frozen_lake(tmp_path, kind) as state:
        root, _, _, payload, bundle, _, transport, request = state
        before = _persistent_bytes(root)
        _disable_new_selection(monkeypatch)
        result = transport.read(request)
        assert result.data == payload
        assert result.receipt["replay_status"] == "verified"
        assert result.receipt["locator_count"] == len(bundle.evidence_spans)
        loaded = NarrativeBundle.from_dict(json.loads(result.data))
        assert loaded.versions.selector == "0.3.2"
        assert loaded.evidence_spans == bundle.evidence_spans
        assert loaded.summary == bundle.summary
        assert _persistent_bytes(root) == before


@pytest.mark.parametrize("kind", ["txt", "json", "pdf"])
def test_old_ids_remain_pinned_after_new_group_ids_are_published(tmp_path, monkeypatch, kind):
    with _frozen_lake(tmp_path, kind) as state:
        _, _, _, payload, bundle, artifacts, transport, old_request = state
        changed = bundle.to_dict()
        replacements = {}
        new_spans = []
        for old in bundle.evidence_spans:
            structured = old.to_dict()["structured_value"]
            structured["selection_group_id"] = "n6-new-canonical-group"
            new = EvidenceSpan.create(
                source_id=old.source_id, coordinates=old.coordinates, raw_text=old.raw_text,
                structured_value=structured, parser_name=old.parser_name,
                parser_version=old.parser_version, parse_status=old.parse_status,
                quality_flags=old.quality_flags,
            )
            assert new.span_id != old.span_id
            replacements[old.span_id] = new.span_id
            new_spans.append(new.to_dict())
        changed["evidence_spans"] = new_spans
        changed["versions"]["selector"] = "0.4.0"
        for claim in changed["summary"]["draft"]["claims"]:
            claim["evidence_ids"] = [replacements[eid] for eid in claim["evidence_ids"]]
        for binding in changed["transcript_byte_bindings"]:
            binding["evidence_id"] = replacements[binding["evidence_id"]]
        newer = NarrativeBundle.from_dict(changed)
        new_payload = canonical_json(newer.to_dict()).encode()
        _publish(artifacts, newer, new_payload, label="new-group")
        new_reference = transport.reference(bundle.source_ref)
        assert new_reference.artifact_version_id != old_request.narrative_ref.artifact_version_id
        new_request = NarrativeReadRequest.from_dict({
            **old_request.to_dict(), "narrative_ref": new_reference.to_dict(),
        })
        _disable_new_selection(monkeypatch)
        assert transport.read(old_request).data == payload
        result = transport.read(new_request)
        assert result.data == new_payload
        assert result.receipt["locator_count"] == len(bundle.evidence_spans)
        assert [span["locator"] for span in new_spans] == [span.locator for span in bundle.evidence_spans]


@pytest.mark.parametrize("kind", ["txt", "json", "pdf"])
def test_selector_upgrade_still_refuses_changed_original_bytes(tmp_path, monkeypatch, kind):
    with _frozen_lake(tmp_path, kind) as state:
        _, raw_path, raw, payload, _, _, transport, request = state
        _disable_new_selection(monkeypatch)
        assert transport.read(request).data == payload
        raw_path.write_bytes(b"X" * len(raw))
        try:
            with pytest.raises(NarrativeTransportError):
                transport.read(request)
        finally:
            raw_path.write_bytes(raw)
        assert transport.read(request).data == payload
