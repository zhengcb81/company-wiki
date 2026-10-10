"""Public production mixed-item batch CLI, spawned workers and real HTTP E2E.

Synthetic originals and a loopback-only model keep this independent of vendor
availability. Assertions cover actual runner/store/source/transport boundaries.
"""

from collections import Counter
import json

import pytest

from company_wiki.automation.models import JobStatus
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from support.official_json_batch_fixture import (
    invoke_batch,
    invoke_read,
    official_batch_state,
    request_for,
)
from support import official_json_batch_fixture as fixtures


official_json_loopback_model = fixtures.official_json_loopback_model


def items_by_key(receipt):
    assert "documents" not in receipt
    assert len({item["item_key"] for item in receipt["items"]}) == len(receipt["items"])
    return {item["item_key"]: item for item in receipt["items"]}


def assert_paid(receipt, count):
    assert receipt["budget"] == {
        "tokens": 92 * count,
        "estimated_micro_usd": 111 * count,
        "unknown_reservations": 0,
        "unsettled_reservations": 0,
    }


def assert_terminal_jobs(state, run_id, expected_keys):
    store = AutomationStore(state.automation_db)
    run = NarrativeRunStore(state.automation_db).get_run(run_id)
    assert run is not None
    jobs = store.list_jobs(job_ids=run.job_ids)
    assert len(jobs) == 3 * len(expected_keys)
    by_item = {key: [] for key in expected_keys}
    for job in jobs:
        assert job.subject_id in by_item and job.status is JobStatus.SUCCEEDED
        by_item[job.subject_id].append(job)
        attempts = store.list_attempts(job.job_id)
        assert len(attempts) == 1, (
            "the successful attempt must be durably retained once"
        )
        result = json.loads(attempts[0].result_json)["result"]
        projected = job.subject_id.startswith("urn:company-wiki:source-projection:")
        assert result["schema_version"] == (
            "narrative-terminal-receipt/2.0"
            if projected
            else "narrative-terminal-receipt/1.0"
        )
        pin = result["final_artifact"]
        if projected:
            assert pin["subject_binding"]["item_key"] == job.subject_id
            assert len(pin["generation_sha256"]) == 64
            assert "document_id" not in pin and "source_id" not in pin
        else:
            assert pin["document_id"] == job.subject_id
        assert "evidence_spans" not in result and "summary" not in result
        assert len(attempts[0].result_json.encode()) < 16384
    for item_jobs in by_item.values():
        assert {job.job_type for job in item_jobs} == {
            "source.narrative_select",
            "source.narrative_summarize",
            "source.narrative_verify",
        }


def assert_actual_public_reads(state, receipt):
    by_key = items_by_key(receipt)
    expected = {s.item_key for s in state.subjects} | {state.raw_ref["document_id"]}
    assert set(by_key) == expected
    for subject in state.subjects:
        item = by_key[subject.item_key]
        assert (
            item["kind"] == "official_json"
            and item["status"] == "completed"
            and item["errors"] == []
        )
        ref = item["artifact_ref"]
        assert (
            ref["schema_version"] == "narrative-ref/2"
            and ref["subject_binding"] == subject.to_dict()
        )
        assert (
            "source_ref" not in ref
            and "effect_id" not in ref
            and "content_sha256" not in ref
        )
        wire, read_receipt = invoke_read(state, ref, issuer=subject.issuer)
        bundle = NarrativeBundle.from_dict(wire)
        assert (
            bundle.subject == subject
            and bundle.schema_version == "narrative-bundle/3.0"
        )
        language = "zh" if subject.issuer["provider_company_id"] == 1 else "en"
        assert (
            bundle.source_metadata.language == language
            and bundle.summary.draft.language == language
        )
        assert bundle.summary.translate is False
        assert set(span.source_id for span in bundle.evidence_spans) == {
            ref["source_id"] for ref in state.parent_refs
        }
        assert {
            span.structured_value["source_role"] for span in bundle.evidence_spans
        } == {"management", "investor_question"}
        assert all(
            span.structured_value["provider_record_id"] % 100
            == subject.issuer["provider_company_id"]
            for span in bundle.evidence_spans
        )
        assert all(
            "provider_translation" not in span.structured_value["role"]
            for span in bundle.evidence_spans
        )
        assert all(
            "Provider translation" not in span.raw_text
            for span in bundle.evidence_spans
        )
        assert (
            read_receipt["subject_binding"] == subject.to_dict()
            and read_receipt["replay_status"] == "verified"
        )
    raw = by_key[state.raw_ref["document_id"]]
    assert raw["kind"] == "raw" and raw["status"] == "completed"
    assert raw["artifact_ref"]["schema_version"] == "narrative-ref/1"
    wire, read_receipt = invoke_read(state, raw["artifact_ref"])
    bundle = NarrativeBundle.from_dict(wire)
    assert (
        bundle.schema_version == "narrative-bundle/2.0"
        and bundle.source_ref.to_dict() == state.raw_ref
    )
    assert read_receipt["replay_status"] == "verified"


def test_public_mixed_batch_has_real_three_job_flow_resume_reuse_refresh_and_restores_originals(
    tmp_path, official_json_loopback_model
):
    server = official_json_loopback_model
    with official_batch_state(tmp_path) as state:
        path = request_for(state, server.endpoint, "mixed-first")
        process, first = invoke_batch(state, path, "mixed-first")
        assert process.returncode == 0 and first["status"] == "completed", (
            first,
            process.stderr,
        )
        assert server.errors == [] and len(server.requests) == 3
        identity_keys = [
            data["subject"]["subject_id"]
            if "subject" in data
            else data["source"]["source_id"]
            for data in server.requests
        ]
        assert Counter(identity_keys) == Counter(
            {
                state.subjects[0].item_key: 1,
                state.subjects[1].item_key: 1,
                state.raw_ref["source_id"]: 1,
            }
        )
        assert_paid(first, 3)
        keys = set(items_by_key(first))
        assert_terminal_jobs(state, "mixed-first", keys)
        assert_actual_public_reads(state, first)
        resumed_process, resumed = invoke_batch(state, path, "mixed-first")
        assert resumed_process.returncode == 0 and resumed["status"] == "completed"
        assert (
            resumed["items"] == first["items"] and resumed["budget"] == first["budget"]
        )
        assert len(server.requests) == 3
        assert_terminal_jobs(state, "mixed-first", keys)
        reuse_path = request_for(state, server.endpoint, "mixed-reuse")
        reused_process, reused = invoke_batch(state, reuse_path, "mixed-reuse")
        assert reused_process.returncode == 0 and reused["status"] == "completed"
        assert len(server.requests) == 3 and server.errors == []
        assert_paid(reused, 0)
        assert {
            key: item["artifact_ref"] for key, item in items_by_key(reused).items()
        } == {key: item["artifact_ref"] for key, item in items_by_key(first).items()}
        assert_terminal_jobs(state, "mixed-reuse", set())
        refresh_path = request_for(
            state, server.endpoint, "mixed-refresh", refresh=True
        )
        refresh_process, refreshed = invoke_batch(state, refresh_path, "mixed-refresh")
        assert refresh_process.returncode == 0 and refreshed["status"] == "completed"
        assert len(server.requests) == 6 and server.errors == []
        assert_paid(refreshed, 3)
        assert_terminal_jobs(state, "mixed-refresh", keys)
        assert all(
            items_by_key(refreshed)[key]["artifact_ref"]["artifact_version_id"]
            != items_by_key(first)[key]["artifact_ref"]["artifact_version_id"]
            for key in keys
        )
        assert_actual_public_reads(state, refreshed)
        assert {p: p.read_bytes() for p in state.originals} == state.originals


@pytest.mark.parametrize(
    "change", ["second_parent_bytes", "second_parent_inactive", "wrong_projection_sha"]
)
def test_public_batch_preparation_refuses_invalid_parent_or_projection_before_any_paid_call(
    tmp_path, official_json_loopback_model, change
):
    server = official_json_loopback_model
    with official_batch_state(tmp_path) as state:
        items = None
        target = None
        if change == "second_parent_bytes":
            target = next(
                p
                for p in state.originals
                if p.suffix == ".json"
                and not p.name.endswith(".source.json")
                and fixtures.sha(p.read_bytes())
                == state.parent_refs[1]["content_sha256"]
            )
            target.write_bytes(b"X" * len(state.originals[target]))
        elif change == "second_parent_inactive":
            with state.catalog.store.transaction() as connection:
                connection.execute(
                    "UPDATE documents SET source_status='retired' WHERE document_id=?",
                    (state.parent_refs[1]["document_id"],),
                )
        else:
            items = [
                {
                    "kind": "official_json",
                    "projection_id": "urn:company-wiki:source-projection:sha256:"
                    + "f" * 64,
                    "projection_sha256": "f" * 64,
                }
            ]
        try:
            path = request_for(state, server.endpoint, "invalid-" + change, items=items)
            process, result = invoke_batch(state, path, "invalid-" + change)
            assert process.returncode != 0 and result["status"] != "completed"
            assert result["items"] and all(
                item["artifact_ref"] is None for item in result["items"]
            )
            assert_paid(result, 0)
            assert server.requests == [] and server.errors == []
            assert not state.automation_db.exists(), (
                "source preparation must fail before AUTO materialization"
            )
        finally:
            if target is not None:
                target.write_bytes(state.originals[target])


def test_mixed_batch_only_missing_items_pay_and_keeps_preexisting_projection_pin(
    tmp_path, official_json_loopback_model
):
    server = official_json_loopback_model
    with official_batch_state(tmp_path) as state:
        a, b = state.subjects
        only_a = [
            {
                "kind": "official_json",
                "projection_id": a.item_key,
                "projection_sha256": a.subject_sha256,
            }
        ]
        first_path = request_for(
            state, server.endpoint, "only-projection-a", items=only_a
        )
        first_process, first = invoke_batch(state, first_path, "only-projection-a")
        assert first_process.returncode == 0 and first["status"] == "completed", first
        assert len(server.requests) == 1 and server.errors == []
        assert_paid(first, 1)
        assert_terminal_jobs(state, "only-projection-a", {a.item_key})
        saved_ref = items_by_key(first)[a.item_key]["artifact_ref"]
        mixed_path = request_for(state, server.endpoint, "partial-reuse-mixed")
        mixed_process, mixed = invoke_batch(state, mixed_path, "partial-reuse-mixed")
        assert mixed_process.returncode == 0 and mixed["status"] == "completed", mixed
        assert len(server.requests) == 3 and server.errors == []
        assert_paid(mixed, 2)
        assert items_by_key(mixed)[a.item_key]["artifact_ref"] == saved_ref
        assert_terminal_jobs(
            state, "partial-reuse-mixed", {b.item_key, state.raw_ref["document_id"]}
        )
        keys = [
            data["subject"]["subject_id"]
            if "subject" in data
            else data["source"]["source_id"]
            for data in server.requests
        ]
        assert Counter(keys) == Counter(
            {a.item_key: 1, b.item_key: 1, state.raw_ref["source_id"]: 1}
        )
        assert_actual_public_reads(state, mixed)
