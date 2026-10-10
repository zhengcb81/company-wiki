"""Projection transport wire and immutable-locator requirements, before implementation."""

from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_official_json import (
    VerifiedProjectionView,
    select_verified_projection,
)
from company_wiki.automation.narrative_transport_contracts import (
    NarrativeRef,
    NarrativeReadRequest,
    parse_reference_request,
)
from company_wiki.automation import narrative_transport_contracts as contracts
from company_wiki.automation import narrative_replay as replay
from company_wiki.source_contract import EvidenceSpan
from unit.test_official_json_narrative_adapter import source_export


def view_fixture():
    _, value = source_export()
    return VerifiedProjectionView(json.dumps(value, ensure_ascii=False))


def reference_wire():
    return {
        "schema_version": "narrative-ref/2",
        "artifact_version_id": "projection-version-1",
        "artifact_sha256": "a" * 64,
        "byte_size": 1024,
        "subject_binding": view_fixture().subject.to_dict(),
        "generation_sha256": "b" * 64,
    }


def read_wire():
    return {
        "schema_version": "narrative-read-request/2",
        "narrative_ref": reference_wire(),
        "as_of_date": "2026-10-08",
        "expected_issuer": {"provider_company_id": 1},
    }


def test_ref2_and_read2_exact_round_trip_and_detached_subject():
    value = reference_wire()
    reference = NarrativeRef.from_dict(value)
    assert reference.to_dict() == value
    assert reference.source_ref is None
    assert reference.subject == view_fixture().subject
    value["subject_binding"]["issuer"]["provider_company_id"] = 999
    assert reference.subject.issuer["provider_company_id"] == 1
    detached = reference.to_dict()
    detached["subject_binding"]["coverage"]["pagination_complete"] = False
    assert reference.to_dict() == reference_wire()
    assert NarrativeReadRequest.from_dict(read_wire()).to_dict() == read_wire()


@pytest.mark.parametrize(
    "change",
    [
        "source_ref",
        "missing_generation",
        "bad_generation",
        "raw_subject",
        "size_bool",
        "extra",
        "old_schema",
    ],
)
def test_ref2_rejects_mixed_or_inconsistent_wire(change):
    value = reference_wire()
    if change == "source_ref":
        value["source_ref"] = view_fixture().subject.anchor_ref
    elif change == "missing_generation":
        value.pop("generation_sha256")
    elif change == "bad_generation":
        value["generation_sha256"] = "ABC"
    elif change == "raw_subject":
        from company_wiki.narrative_subject import NarrativeSubject

        value["subject_binding"] = NarrativeSubject.from_raw(
            view_fixture().subject.anchor_ref
        ).to_dict()
    elif change == "size_bool":
        value["byte_size"] = True
    elif change == "extra":
        value["authorization"] = "not-a-transport-field"
    else:
        value["schema_version"] = "narrative-ref/1"
    with pytest.raises(ValueError):
        NarrativeRef.from_dict(value)


@pytest.mark.parametrize(
    "issuer",
    [
        None,
        {"provider_company_id": 1},
        {"provider_company_id": "1"},
        {"market": "CN", "security_id": "688012"},
    ],
)
def test_read2_supports_explicit_issuer_partial_constraints(issuer):
    value = read_wire()
    value["expected_issuer"] = issuer
    assert NarrativeReadRequest.from_dict(value).to_dict() == value


@pytest.mark.parametrize(
    "change",
    [
        "expected_source",
        "fiscal",
        "unknown_issuer",
        "boolean_id",
        "null_id",
        "invalid_date",
        "missing_date",
        "raw_ref",
    ],
)
def test_read2_cannot_fall_back_to_raw_identity_or_invalid_cutoff(change):
    value = read_wire()
    if change == "expected_source":
        value["expected_source"] = {}
    elif change == "fiscal":
        value["expected_issuer"] = {"fiscal_year": 2026}
    elif change == "unknown_issuer":
        value["expected_issuer"] = {"provider": "fake"}
    elif change == "boolean_id":
        value["expected_issuer"] = {"provider_company_id": True}
    elif change == "null_id":
        value["expected_issuer"] = {"provider_company_id": None}
    elif change == "invalid_date":
        value["as_of_date"] = "2026-02-30"
    elif change == "missing_date":
        value.pop("as_of_date")
    else:
        value["narrative_ref"] = {
            "schema_version": "narrative-ref/1",
            "artifact_version_id": "raw-version",
            "artifact_sha256": "a" * 64,
            "byte_size": 1024,
            "source_ref": view_fixture().subject.anchor_ref,
        }
    with pytest.raises(ValueError):
        NarrativeReadRequest.from_dict(value)


def test_reference2_parser_requires_exact_subject_generation_and_keeps_old_parser():
    view = view_fixture()
    wire = {
        "schema_version": "narrative-reference-request/2",
        "subject_binding": view.subject.to_dict(),
        "generation_sha256": "b" * 64,
    }
    subject, generation = contracts.parse_projected_reference_request(wire)
    assert subject == view.subject and generation == "b" * 64
    with pytest.raises(ValueError):
        parse_reference_request(wire)
    with pytest.raises(ValueError):
        contracts.parse_projected_reference_request(
            {**wire, "source_ref": view.subject.anchor_ref}
        )
    with pytest.raises(ValueError):
        contracts.parse_projected_reference_request(
            {**wire, "generation_sha256": "bad"}
        )


def test_projected_replay_accepts_only_selector_annotations():
    view = view_fixture()
    package = select_verified_projection(view, title="Business development Q&A")
    selected = SimpleNamespace(
        subject=view.subject, evidence_spans=package.evidence_spans
    )
    assert replay.replay_verified_projection(view, selected) == len(
        package.evidence_spans
    )


@pytest.mark.parametrize(
    "field",
    [
        "parent_content_sha256",
        "pointer",
        "token_range",
        "encoded_token_sha256",
        "role",
        "source_role",
        "language",
        "original_role",
        "raw_text",
        "coordinates",
        "parser",
        "text_sha256",
        "unit_kind",
        "unknown_metadata",
        "missing_metadata",
    ],
)
def test_resigned_locator_mutations_are_refused_even_with_valid_span_hash(field):
    view = view_fixture()
    package = select_verified_projection(view, title="Business development Q&A")
    original = package.evidence_spans[0]
    metadata = deepcopy(original.to_dict()["structured_value"])
    raw_text, coordinates, parser = (
        original.raw_text,
        original.coordinates,
        original.parser_name,
    )
    if field == "raw_text":
        raw_text = "Fabricated growth."
    elif field == "coordinates":
        from dataclasses import replace

        coordinates = replace(coordinates, paragraph_index=999)
    elif field == "parser":
        parser = "invented"
    elif field == "unknown_metadata":
        metadata["fabricated_source_fact"] = True
    elif field == "missing_metadata":
        metadata.pop("record_times")
    elif field == "token_range":
        metadata[field] = [1, 2]
    elif field in {"encoded_token_sha256", "parent_content_sha256", "text_sha256"}:
        metadata[field] = "f" * 64
    else:
        metadata[field] = "invented"
    forged = EvidenceSpan.create(
        source_id=original.source_id,
        coordinates=coordinates,
        raw_text=raw_text,
        structured_value=metadata,
        parser_name=parser,
        parser_version=original.parser_version,
        parse_status=original.parse_status,
        quality_flags=original.quality_flags,
    )
    selected = SimpleNamespace(subject=view.subject, evidence_spans=(forged,))
    with pytest.raises(replay.NarrativeReplayError):
        replay.replay_verified_projection(view, selected)


def test_projected_replay_requires_whole_subject_not_only_projection_hash():
    from company_wiki.narrative_subject import NarrativeSubject

    view = view_fixture()
    wire = view.subject.to_dict()
    wire["issuer"]["provider_company_id"] = 999
    selected = SimpleNamespace(
        subject=NarrativeSubject.from_dict(wire), evidence_spans=view.evidence_spans
    )
    with pytest.raises(replay.NarrativeReplayError):
        replay.replay_verified_projection(view, selected)


def test_legacy_ref_subject_does_not_add_any_ref2_fields():
    from company_wiki.narrative_subject import NarrativeSubject

    raw = view_fixture().subject.anchor_ref
    wire = {
        "schema_version": "narrative-ref/1",
        "artifact_version_id": "raw-version",
        "artifact_sha256": hashlib.sha256(b"legacy").hexdigest(),
        "byte_size": 100,
        "source_ref": raw,
    }
    reference = NarrativeRef.from_dict(wire)
    assert reference.subject == NarrativeSubject.from_raw(raw)
    assert reference.to_dict() == wire
