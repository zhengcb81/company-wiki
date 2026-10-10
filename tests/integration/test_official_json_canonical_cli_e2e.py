"""Explicit canonical producer version through public CLI and AUTO boundaries.

Only independent owned TEMP originals and loopback HTTP are used. Historical
producer1.0.1/default behavior remains observable, not silently reinterpreted.
"""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation.models import JobStatus
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.official_json_projection import projection_from_dict
from support import official_json_batch_fixture as fixtures
from support.official_json_batch_fixture import (
    encoded,
    invoke_batch,
    invoke_read,
    official_batch_state,
    request_for,
    subprocess_env,
)


official_json_loopback_model = fixtures.official_json_loopback_model
ABSENT = object()


def official(state, operation, request):
    path = state.root / (
        "canonical-" + operation + "-" + str(len(state.calls)) + ".json"
    )
    path.write_bytes(encoded(request))
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-B",
        "-m",
        "company_wiki.source_catalog.cli",
        "official",
        "--config",
        str(state.config_path),
        "--project-root",
        str(state.root),
        "--operation",
        operation,
        "--request",
        str(path),
    ]
    process = subprocess.run(
        command, cwd=state.root, env=subprocess_env(), capture_output=True, timeout=30
    )
    assert fixtures.KEY.encode() not in process.stdout + process.stderr
    state.calls.append({"operation": operation, "exit_code": process.returncode})
    return process


def project(state, refs, *, version=ABSENT):
    request = {
        "schema_version": "official-json-projection-request/1",
        "parent_source_refs": list(refs),
        "layout_id": "official-paged-qa",
        "issuer": {"provider_company_id": 1},
        "as_of_date": "2026-10-08",
        "persist": True,
    }
    if version is not ABSENT:
        request["projection_version"] = version
    process = official(state, "project", request)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["schema_version"] == "official-json-projection-result/1"
    assert result["selected_records"] == 2
    return process.stdout, result["projection"]


def published_item(result, subject):
    assert (
        result["schema_version"] == "narrative-batch-result/2"
        and result["status"] == "completed"
    )
    assert len(result["items"]) == 1 and "documents" not in result
    item = result["items"][0]
    assert item["item_key"] == subject.item_key and item["kind"] == "official_json"
    assert item["status"] == "completed" and item["errors"] == []
    assert item["artifact_ref"]["schema_version"] == "narrative-ref/2"
    assert item["artifact_ref"]["subject_binding"] == subject.to_dict()
    return item["artifact_ref"]


def test_explicit_canonical_cli_persists_replays_publishes_and_reversed_rebuild_reuses(
    tmp_path,
    official_json_loopback_model,
):
    server = official_json_loopback_model
    with official_batch_state(tmp_path) as state:
        forward_bytes, forward = project(state, state.parent_refs, version="1.0.2")
        assert forward["adapter"]["parser"] == "cwp_official_json/1.0.2", (
            "the public CLI must pass the explicit projection_version to its producer"
        )
        assert forward["adapter"]["structure_parser_version"] == "1.0.1"
        reverse_bytes, reverse = project(
            state, reversed(state.parent_refs), version="1.0.2"
        )
        assert reverse_bytes == forward_bytes
        assert reverse["projection_id"] == forward["projection_id"]
        assert reverse["projection_sha256"] == forward["projection_sha256"]
        for operation, schema in (
            ("replay", "official-json-replay-request/1"),
            ("export", "source-projection-export-request/1"),
        ):
            reopened = official(
                state,
                operation,
                {"schema_version": schema, "projection_id": forward["projection_id"]},
            )
            assert reopened.returncode == 0, reopened.stderr
            wire = json.loads(reopened.stdout)
            if operation == "replay":
                assert (
                    wire["projection_id"] == forward["projection_id"]
                    and wire["verified_records"] == 2
                )
                assert {row["parent_content_sha256"] for row in wire["records"]} == {
                    ref["content_sha256"] for ref in state.parent_refs
                }
            else:
                assert wire["projection"] == forward
                assert (
                    wire["counts"]["source_refs"] == 2
                    and wire["counts"]["selected_records"] == 2
                )
                assert wire["evidence_spans"] and all(
                    span["parser_name"] == "cwp_official_json"
                    and span["parser_version"] == "1.0.2"
                    for span in wire["evidence_spans"]
                )
        subject = NarrativeSubject.from_projection(projection_from_dict(forward))
        items = [
            {
                "kind": "official_json",
                "projection_id": subject.item_key,
                "projection_sha256": subject.subject_sha256,
            }
        ]
        first_path = request_for(state, server.endpoint, "canonical-first", items=items)
        process, first = invoke_batch(state, first_path, "canonical-first")
        assert process.returncode == 0, first
        reference = published_item(first, subject)
        assert len(server.requests) == 1 and server.errors == []
        assert server.requests[0]["schema_version"] == "narrative-model-request/2"
        assert server.requests[0]["subject"]["subject_id"] == subject.item_key
        assert first["budget"] == {
            "tokens": 92,
            "estimated_micro_usd": 111,
            "unknown_reservations": 0,
            "unsettled_reservations": 0,
        }
        run = NarrativeRunStore(state.automation_db).get_run("canonical-first")
        assert run is not None
        store = AutomationStore(state.automation_db)
        jobs = store.list_jobs(job_ids=run.job_ids)
        assert len(jobs) == 3 and all(job.status is JobStatus.SUCCEEDED for job in jobs)
        assert {job.job_type for job in jobs} == {
            "source.narrative_select",
            "source.narrative_summarize",
            "source.narrative_verify",
        }
        for job in jobs:
            attempts = store.list_attempts(job.job_id)
            assert len(attempts) == 1
            terminal = json.loads(attempts[0].result_json)["result"]
            assert terminal["schema_version"] == "narrative-terminal-receipt/2.0"
            assert terminal["final_artifact"]["subject_binding"] == subject.to_dict()
        read_wire, receipt = invoke_read(state, reference, issuer=subject.issuer)
        bundle = NarrativeBundle.from_dict(read_wire)
        assert bundle.subject == subject and bundle.versions.parser == "1.0.2"
        assert (
            bundle.subject.to_dict()["adapter"]["structure_parser_version"] == "1.0.1"
        )
        assert bundle.evidence_spans and all(
            span.parser_name == "cwp_official_json" and span.parser_version == "1.0.2"
            for span in bundle.evidence_spans
        )
        assert {span.source_id for span in bundle.evidence_spans} == {
            ref["source_id"] for ref in state.parent_refs
        }
        assert (
            receipt["replay_status"] == "verified"
            and receipt["subject_binding"] == subject.to_dict()
        )
        repeat_bytes, repeated = project(
            state, reversed(state.parent_refs), version="1.0.2"
        )
        assert repeat_bytes == forward_bytes and repeated == forward
        reuse_subject = NarrativeSubject.from_projection(projection_from_dict(repeated))
        reuse_items = [
            {
                "kind": "official_json",
                "projection_id": reuse_subject.item_key,
                "projection_sha256": reuse_subject.subject_sha256,
            }
        ]
        reuse_path = request_for(
            state, server.endpoint, "canonical-reordered-reuse", items=reuse_items
        )
        reuse_process, reused = invoke_batch(
            state, reuse_path, "canonical-reordered-reuse"
        )
        assert reuse_process.returncode == 0, reused
        assert published_item(reused, reuse_subject) == reference
        assert len(server.requests) == 1 and server.errors == []
        assert reused["budget"] == {
            "tokens": 0,
            "estimated_micro_usd": 0,
            "unknown_reservations": 0,
            "unsettled_reservations": 0,
        }
        reuse_run = NarrativeRunStore(state.automation_db).get_run(
            "canonical-reordered-reuse"
        )
        assert reuse_run is not None and reuse_run.job_ids == ()
        assert {path: path.read_bytes() for path in state.originals} == state.originals


def test_public_default_and_explicit_legacy_keep_historical_page_order(tmp_path):
    with official_batch_state(tmp_path) as state:
        default_forward_bytes, default_forward = project(state, state.parent_refs)
        explicit_forward_bytes, explicit_forward = project(
            state, state.parent_refs, version="1.0.1"
        )
        default_reverse_bytes, default_reverse = project(
            state, reversed(state.parent_refs)
        )
        explicit_reverse_bytes, explicit_reverse = project(
            state, reversed(state.parent_refs), version="1.0.1"
        )
        assert default_forward_bytes == explicit_forward_bytes
        assert default_reverse_bytes == explicit_reverse_bytes
        assert default_forward["projection_id"] != default_reverse["projection_id"]
        assert (
            explicit_forward["adapter"]["parser"]
            == explicit_reverse["adapter"]["parser"]
            == "cwp_official_json/1.0.1"
        )
        assert explicit_forward["parent_source_refs"] == list(state.parent_refs)
        assert explicit_reverse["parent_source_refs"] == list(
            reversed(state.parent_refs)
        )
        assert default_forward["projection_id"] == state.subjects[0].item_key
        assert not state.automation_db.exists()


@pytest.mark.parametrize(
    "projection_version",
    [
        pytest.param("9.9.9", id="unsupported"),
        pytest.param([], id="list"),
        pytest.param({}, id="dict"),
        pytest.param(None, id="null"),
    ],
)
def test_public_project_refuses_unsupported_version_without_persisting_or_processing(
    tmp_path,
    projection_version,
):
    with official_batch_state(tmp_path) as state:
        catalog_dir = Path(state.catalog.config.catalog_dir)
        before = {path: path.read_bytes() for path in catalog_dir.rglob("*.json")}
        process = official(
            state,
            "project",
            {
                "schema_version": "official-json-projection-request/1",
                "parent_source_refs": list(state.parent_refs),
                "layout_id": "official-paged-qa",
                "issuer": {"provider_company_id": 1},
                "as_of_date": "2026-10-08",
                "persist": True,
                "projection_version": projection_version,
            },
        )
        assert process.returncode == 2 and process.stdout == b""
        assert b"Traceback" not in process.stderr and b"TypeError" not in process.stderr
        failure = json.loads(process.stderr)
        assert (
            failure["schema_version"] == "official-source-failure/1"
            and failure["status"] == "failed"
        )
        assert str(state.root).encode() not in process.stderr
        assert {
            path: path.read_bytes() for path in catalog_dir.rglob("*.json")
        } == before
        assert not state.automation_db.exists()
