"""Projected and raw work share item identity without inventing a source."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_contracts import (
    SourceRevisionEventPayload,
    NarrativeContractError,
)
from company_wiki.automation.execution_context import (
    JobExecutionContext,
    ExecutionContextError,
)
from company_wiki.automation.models import (
    canonical_json,
    canonical_json_hash,
    make_job_key,
)
from company_wiki.source_catalog.official_json_projection import build_source_projection
from company_wiki.source_catalog.official_json_structure import parse_json_structure
from unit.test_narrative_batch_request import _request
from unit.test_automation_execution_context import _snapshot


def subject(issuer=1):
    pages = []
    for page in (1, 2):
        rows = [
            {
                "ref": page * 10 + who,
                "org_id": who,
                "org_name": "Company " + str(who),
                "q": "What is the overseas capacity expansion plan?",
                "a": "New production capacity is being expanded overseas for customer deliveries.",
                "answered": True,
                "created_at": "2026-09-01 10:00:00",
                "updated_at": "2026-09-01 10:00:00",
            }
            for who in (1, 2)
        ]
        data = json.dumps(
            {
                "ok": True,
                "result": {
                    "page": page,
                    "page_size": 2,
                    "page_count": 2,
                    "item_total": 4,
                    "items": rows,
                },
            }
        ).encode()
        pages.append(
            (hashlib.sha256(data).hexdigest(), len(data), parse_json_structure(data))
        )
    return NarrativeSubject.from_projection(
        build_source_projection(
            parent_pages=pages,
            layout_id="official-flat-list",
            issuer={"provider_company_id": issuer},
            as_of_date="2026-10-08",
        )
    )


def projected_request():
    value = _request()
    value["schema_version"] = "narrative-batch-request/2"
    ref = value.pop("sources")[0]
    value["items"] = [{"kind": "raw", "source_ref": ref}]
    for who in (1, 2):
        s = subject(who)
        value["items"].append(
            {
                "kind": "official_json",
                "projection_id": s.item_key,
                "projection_sha256": s.subject_sha256,
            }
        )
    return value


def event_payload(who=1):
    return {
        "schema_version": "source-revision-event/3.0",
        "subject_binding": subject(who).to_dict(),
        "source_metadata": {
            "source_class": "official_json",
            "title": "Business Q&A",
            "document_kind": "investor_relations",
            "language": "en",
        },
    }


def test_new_batch_keeps_shared_parent_issuers_as_distinct_compact_items():
    request = NarrativeBatchRequest.from_dict(projected_request())
    assert len(request.work_items) == 3
    assert (
        len(request.sources) == 1
    )  # Originals only, never a projection disguised as a raw ref.
    assert [item.kind for item in request.work_items] == [
        "raw",
        "official_json",
        "official_json",
    ]
    assert len({item.item_key for item in request.work_items}) == 3
    wire = request.to_dict()
    assert (
        wire["schema_version"] == "narrative-batch-request/2" and "sources" not in wire
    )
    assert "records" not in json.dumps(wire)
    assert "parent_source_refs" not in json.dumps(wire)
    assert (
        NarrativeBatchRequest.from_dict(wire).request_sha256 == request.request_sha256
    )


def test_identical_items_fold_without_merging_distinct_issuers():
    raw = projected_request()
    expected = NarrativeBatchRequest.from_dict(raw)
    raw["items"].append(deepcopy(raw["items"][1]))
    actual = NarrativeBatchRequest.from_dict(raw)
    assert len(actual.work_items) == 3 and actual.input_hash == expected.input_hash


def test_old_request_gets_common_raw_items_without_changing_public_wire():
    request = NarrativeBatchRequest.from_dict(_request())
    wire = request.to_dict()
    assert wire["schema_version"] == "narrative-batch-request/1" and "items" not in wire
    assert request.work_items[0].item_key == request.sources[0].document_id
    assert request.work_items[0].source_ref == request.sources[0]
    assert NarrativeBatchRequest.from_dict(wire).input_hash == request.input_hash


@pytest.mark.parametrize(
    "change", ["empty", "wrong_hash", "raw_conflict", "records", "unknown_kind", "path"]
)
def test_invalid_items_fail_before_any_source_or_model_operation(change, tmp_path):
    raw = projected_request()
    if change == "empty":
        raw["items"] = []
    elif change == "wrong_hash":
        raw["items"][1]["projection_sha256"] = "a" * 64
    elif change == "raw_conflict":
        other = deepcopy(raw["items"][0])
        other["source_ref"].update(
            source_id="urn:company-wiki:source:sha256:" + "b" * 64,
            content_sha256="b" * 64,
        )
        raw["items"].append(other)
    elif change == "records":
        raw["items"][1]["records"] = [{}]
    elif change == "unknown_kind":
        raw["items"][1]["kind"] = "mystery"
    else:
        raw["items"][1]["path"] = str(tmp_path / "raw.json")
    with pytest.raises(ValueError):
        NarrativeBatchRequest.from_dict(raw)


def test_projection_event_has_one_identity_and_real_anchor_without_public_fake_source():
    payload = SourceRevisionEventPayload.from_dict(event_payload())
    assert payload.subject == subject() and payload.item_key == subject().item_key
    assert payload.source_ref.to_dict() == subject().anchor_ref
    assert payload.expected_read_policy_sha256 is None
    assert payload.to_dict() == event_payload()
    assert payload.input_hash == canonical_json_hash(event_payload())
    assert (
        "source_ref" not in payload.to_dict()
        and "records" not in payload.to_dict()["subject_binding"]
    )
    assert all(
        type(page["records"]) is int
        for page in payload.to_dict()["subject_binding"]["coverage"]["pages"]
    )


def test_old_event_identity_accessor_preserves_exact_2_0_wire():
    from unit.test_automation_execution_context import _payload

    original = _payload()
    payload = SourceRevisionEventPayload.from_dict(original)
    assert payload.to_dict() == original
    assert payload.item_key == original["source_ref"]["document_id"]
    assert payload.subject.kind == "raw"


@pytest.mark.parametrize(
    "mutation", ["raw_under_3", "projection_under_2", "fake_source", "class_mismatch"]
)
def test_event_versions_cannot_relabel_raw_or_projection(mutation):
    raw = event_payload()
    if mutation == "raw_under_3":
        raw["subject_binding"] = NarrativeSubject.from_raw(
            subject().anchor_ref
        ).to_dict()
    elif mutation == "projection_under_2":
        raw["schema_version"] = "source-revision-event/2.0"
    elif mutation == "fake_source":
        raw["source_ref"] = subject().anchor_ref
    else:
        raw["source_metadata"]["source_class"] = "transcript"
    with pytest.raises(NarrativeContractError):
        SourceRevisionEventPayload.from_dict(raw)


def test_context_uses_projection_item_key_not_anchor_document():
    payload = event_payload()
    s = subject()
    snapshot = _snapshot("source.narrative_select", ())
    event = replace(
        snapshot.event,
        subject_type="narrative_subject",
        subject_id=s.item_key,
        input_hash=canonical_json_hash(payload),
        payload_json=canonical_json(payload),
    )
    job = replace(
        snapshot.job,
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        job_key=make_job_key(
            snapshot.job.job_type,
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            snapshot.job.handler_version,
        ),
    )
    ctx = JobExecutionContext.from_snapshot(
        replace(snapshot, event=event, job=job), checkpoint=lambda: None
    )
    assert ctx.source_revision.item_key == s.item_key
    assert ctx.source_revision.subject == s
    assert ctx.source_revision.source_ref.document_id != event.subject_id
    wrong_event = replace(event, subject_id=s.anchor_ref["document_id"])
    wrong_job = replace(
        job,
        subject_id=wrong_event.subject_id,
        job_key=make_job_key(
            job.job_type,
            wrong_event.subject_type,
            wrong_event.subject_id,
            wrong_event.input_hash,
            wrong_event.policy_version,
            job.handler_version,
        ),
    )
    with pytest.raises(ExecutionContextError):
        JobExecutionContext.from_snapshot(
            replace(snapshot, event=wrong_event, job=wrong_job), checkpoint=lambda: None
        )
