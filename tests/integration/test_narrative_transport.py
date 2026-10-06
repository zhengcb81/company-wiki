"""Actual raw/catalog/artifact integration for selected narrative reads."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeTransportError
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactDraft
from company_wiki.source_contract import EvidenceSpan
from support.narrative_transport_fixture import published_fixture


def test_duplicate_byte_bindings_cannot_hide_an_unbound_transcript_span(tmp_path: Path) -> None:
    data = (
        b"Full Conference Call Transcript\n"
        b"CEO: We launched a new product and expanded overseas capacity.\n\n"
        b"CTO: Our new manufacturing platform entered customer qualification.\n"
    )
    with published_fixture(tmp_path, source_spec={"data": data}) as fixture:
        payload = json.loads(fixture.payload)
        assert len(payload["evidence_spans"]) >= 2
        bindings = payload["transcript_byte_bindings"]
        payload["transcript_byte_bindings"] = [bindings[0]] * len(bindings)
        _copy_version(fixture, canonical_json(payload).encode("utf-8"))
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError) as refused:
            transport.read(_request(fixture, reference))
        assert refused.value.reason == "locator_replay_failed"


def _request(fixture, reference, **kwargs):
    return NarrativeReadRequest.from_dict(fixture.read_request(reference, **kwargs))


def _copy_version(fixture, payload: bytes, *, visible: bool = True):
    old = fixture.version
    draft = NarrativeArtifactDraft(
        effect_id="effect-second", work_key="d" * 64,
        document_id=old.document_id, source_id=old.source_id,
        source_sha256=old.source_sha256, producer_name=old.producer_name,
        producer_version=old.producer_version, policy_sha256=old.policy_sha256,
        selection_status=json.loads(payload)["selection"]["status"],
        quality_status=json.loads(payload)["quality_status"],
        metadata_json=old.metadata_json, created_at="2026-10-01T00:00:00Z",
    )
    version = fixture.artifacts.prepare(draft, payload)
    if visible:
        version = fixture.artifacts.activate(
            draft.effect_id, verified_after_hash=version.content_sha256,
            activated_at="2026-10-01T00:00:01Z",
        )
    return version


@pytest.mark.parametrize("kind", ["txt", "json", "pdf", "skip"])
def test_read_returns_exact_persisted_bytes_and_current_receipt(tmp_path: Path, kind) -> None:
    with published_fixture(tmp_path, kind=kind) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        result = transport.read(_request(fixture, reference))
        bundle = json.loads(result.data)
        assert result.data == fixture.payload
        assert result.receipt["status"] == "ok"
        assert result.receipt["narrative_ref"] == reference.to_dict()
        assert result.receipt["as_of_date"] == "2026-09-01"
        assert result.receipt["source_read_policy_sha256"] == fixture.reader.read_policy_sha256()
        assert result.receipt["selection_status"] == bundle["selection"]["status"]
        assert result.receipt["quality_status"] == bundle["quality_status"]
        assert result.receipt["locator_count"] == len(bundle["evidence_spans"])
        assert result.receipt["replay_status"] == "verified"
        assert result.receipt["manifest"]["canonical_entity_id"] == "ent-acme"
        assert str(fixture.root) not in json.dumps(result.receipt)
        if kind == "skip":
            assert result.receipt["selection_status"] == "skipped_no_narrative"
            assert result.receipt["locator_count"] == 0


def test_old_reference_reads_old_artifact_after_new_version_is_published(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        payload = json.loads(fixture.payload)
        payload["prompt_review"]["evidence_sha256"] = "e" * 64
        newer_bytes = canonical_json(payload).encode("utf-8")
        newer = _copy_version(fixture, newer_bytes)
        assert transport.reference(fixture.source_ref).artifact_version_id == newer.artifact_version_id
        assert transport.read(_request(fixture, reference)).data == fixture.payload


def test_current_reader_preserves_older_summary_above_new_generation_targets(tmp_path: Path) -> None:
    """Private short-output targets must not become public read-time gates."""
    # Every statement is backed by a distinct, replayable management paragraph.
    statements = [
        f"We launched a new product for customer segment {index} with "
        + "customer validation continuing under limited pilot availability and " * 4
        + "further rollout subject to completed validation."
        for index in range(25)
    ]
    source = ("Full Conference Call Transcript\nCEO: " + "\n".join(statements)).encode()
    with published_fixture(tmp_path, source_spec={"data": source}) as fixture:
        value = json.loads(fixture.payload)
        spans = value["evidence_spans"]
        assert len(spans) >= 25
        claims = [{
            "claim_id": f"old-{index}", "text": statement,
            "evidence_ids": [next(span["span_id"] for span in spans if span["raw_text"] == statement)],
            "claim_type": "company_statement", "modality": "actual", "needs_review": False,
        } for index, statement in enumerate(statements)]
        value["summary"]["draft"]["claims"] = claims
        value["summary"]["model"]["prompt_version"] = "1.4.0"
        value["versions"]["prompt"] = "1.4.0"
        payload = canonical_json(value).encode()
        _copy_version(fixture, payload)
        reader = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = reader.reference(fixture.source_ref)
        result = reader.read(_request(fixture, reference))
        assert result.data == payload
        assert result.receipt["replay_status"] == "verified"
        draft = NarrativeBundle.from_dict(json.loads(result.data)).summary.draft
        assert draft is not None and len(draft.claims) == 25
        assert all(len(claim.text) > 280 for claim in draft.claims)
        assert fixture.raw_path.read_bytes() == source


def test_reference_is_metadata_only_and_raw_integrity_is_checked_at_read(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        fixture.raw_path.write_bytes(b"X" * len(fixture.raw_bytes))
        try:
            transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
            reference = transport.reference(fixture.source_ref)
            with pytest.raises(NarrativeTransportError):
                transport.read(_request(fixture, reference))
        finally:
            fixture.raw_path.write_bytes(fixture.raw_bytes)


def test_same_size_artifact_tampering_is_rejected(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        path = fixture.catalog.config.catalog_dir / fixture.version.object_key
        path.write_bytes(b"X" * len(fixture.payload))
        with pytest.raises(NarrativeTransportError):
            transport.read(_request(fixture, reference))


def test_prepared_reference_is_not_discoverable_or_readable(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with fixture.catalog.store.transaction() as connection:
            connection.execute("UPDATE narrative_artifact_versions SET status='prepared'")
        with pytest.raises(NarrativeTransportError):
            transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError):
            transport.read(_request(fixture, reference))


@pytest.mark.parametrize("change", ["revoked", "primary"])
def test_revocation_and_primary_replacement_invalidate_old_references(tmp_path: Path, change) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with fixture.catalog.store.transaction() as connection:
            if change == "revoked":
                connection.execute("UPDATE documents SET source_status='withdrawn'")
            else:
                connection.execute("UPDATE documents SET primary_source_id=NULL")
        with pytest.raises(NarrativeTransportError):
            transport.read(_request(fixture, reference))


@pytest.mark.parametrize("field,value", [
    ("canonical_entity_id", "ent-wrong"), ("security_id", "OTHER"),
    ("market", "HK"), ("document_kind", "annual_report"),
    ("fiscal_year", 2025), ("fiscal_period", "Q3"),
])
def test_requested_identity_and_period_must_match_manifest(tmp_path: Path, field, value) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        payload = fixture.read_request(reference)
        payload["expected_source"][field] = value
        with pytest.raises(NarrativeTransportError):
            transport.read(NarrativeReadRequest.from_dict(payload))


def test_publication_after_cutoff_is_rejected(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError) as error:
            transport.read(_request(fixture, reference, as_of_date="2026-07-31"))
        assert error.value.reason == "source_after_as_of"


def test_later_capture_does_not_block_already_public_narrative(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        source = fixture.source_ref
        ref = fixture.reader.query_ref(
            source.document_id, source.source_id, source.content_sha256,
        )
        manifest = fixture.reader.describe_version(ref)
        assert manifest["published_date"] == "2026-08-01"
        assert str(manifest["retrieved_at"]).startswith("2026-08-02")
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        result = transport.read(_request(fixture, reference, as_of_date="2026-08-01"))
        assert result.data == fixture.payload
        assert fixture.raw_path.read_bytes() == fixture.raw_bytes


def test_unknown_publication_can_have_reference_but_not_historical_read(tmp_path: Path) -> None:
    with published_fixture(tmp_path, kind="json") as fixture:
        with fixture.catalog.store.transaction() as connection:
            connection.execute("UPDATE documents SET published_date=NULL")
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError):
            transport.read(_request(fixture, reference))


def test_generation_policy_is_lineage_and_current_read_policy_controls_read(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        old_policy = fixture.reader.read_policy_sha256()
        root = fixture.catalog.config.roots[0]
        fixture.catalog.config = replace(
            fixture.catalog.config, roots=(replace(root, priority=root.priority + 1),),
        )
        current_policy = fixture.reader.read_policy_sha256()
        assert current_policy != old_policy
        result = transport.read(_request(fixture, reference))
        assert result.receipt["source_read_policy_sha256"] == current_policy
        assert json.loads(result.data)["expected_read_policy_sha256"] == old_policy


def test_partial_and_needs_review_quality_is_preserved_by_verified_replay(tmp_path: Path) -> None:
    with published_fixture(tmp_path) as fixture:
        payload = json.loads(fixture.payload)
        payload["selection"]["status"] = "partial"
        payload["selection"]["coverage_complete"] = False
        payload["quality_status"] = "needs_review"
        checked = NarrativeBundle.from_dict(payload)
        _copy_version(fixture, canonical_json(checked.to_dict()).encode("utf-8"))
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        result = transport.read(_request(fixture, reference))
        assert result.receipt["selection_status"] == "partial"
        assert result.receipt["quality_status"] == "needs_review"
        assert result.receipt["replay_status"] == "verified"


@pytest.mark.parametrize("kind", ["txt", "json", "pdf"])
def test_resigned_semantically_valid_locator_with_fabricated_text_is_rejected(tmp_path: Path, kind) -> None:
    with published_fixture(tmp_path, kind=kind) as fixture:
        payload = json.loads(fixture.payload)
        original = EvidenceSpan.from_dict(payload["evidence_spans"][0])
        forged = EvidenceSpan.create(
            source_id=original.source_id, coordinates=original.coordinates,
            raw_text="Fabricated business claim at a real locator.",
            structured_value=original.structured_value,
            parser_name=original.parser_name, parser_version=original.parser_version,
            parse_status=original.parse_status, quality_flags=original.quality_flags,
        )
        payload["evidence_spans"][0] = forged.to_dict()
        for claim in payload["summary"]["draft"]["claims"]:
            claim["evidence_ids"] = [
                forged.span_id if evidence_id == original.span_id else evidence_id
                for evidence_id in claim["evidence_ids"]
            ]
        for binding in payload["transcript_byte_bindings"]:
            if binding["evidence_id"] == original.span_id:
                binding["evidence_id"] = forged.span_id
        # The ref, content-addressed artifact and strict wire all agree. Only
        # replay against immutable source bytes can detect this false excerpt.
        checked = NarrativeBundle.from_dict(payload)
        _copy_version(fixture, canonical_json(checked.to_dict()).encode("utf-8"))
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError) as refused:
            transport.read(_request(fixture, reference))
        assert refused.value.reason == "locator_replay_failed"


def test_json_resigned_byte_binding_drift_is_rejected(tmp_path: Path) -> None:
    with published_fixture(tmp_path, kind="json") as fixture:
        payload = json.loads(fixture.payload)
        payload["transcript_byte_bindings"][0]["source_byte_ranges"][0]["start"] += 1
        checked = NarrativeBundle.from_dict(payload)
        _copy_version(fixture, canonical_json(checked.to_dict()).encode("utf-8"))
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        with pytest.raises(NarrativeTransportError) as refused:
            transport.read(_request(fixture, reference))
        assert refused.value.reason == "locator_replay_failed"
