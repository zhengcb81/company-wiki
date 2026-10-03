"""Real DAG publication, compacted restart and formal final transport."""

from __future__ import annotations

import json

import pytest

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.automation.terminal_receipts import compact_terminal_narrative_jobs
from unit.test_terminal_narrative_receipts import T3, snapshot, terminal_fixture


@pytest.mark.parametrize(
    "kind,unknown", [("txt", False), ("txt", True), ("skip", False)]
)
def test_published_dag_compacts_then_resumes_without_model_replay_and_keeps_final(
    tmp_path, kind, unknown
):
    with terminal_fixture(tmp_path, kind=kind, unknown=unknown) as state:
        raw = {
            path: path.read_bytes()
            for path in (state.root / "companies").rglob("*")
            if path.is_file()
        }
        reservations = state.ledger.reservations_for_run("terminal-run")
        if reservations:
            state.ledger.settle_output(
                run_id="terminal-run",
                attempt_id=reservations[0].attempt_id,
                output_bytes=len(state.payload),
                output_sha256=state.pin.artifact_sha256,
                settled_at=T3,
            )
        before = snapshot(state)
        calls = len(state.model.calls)
        transport = NarrativeTransportReader(state.artifacts, state.reader)
        reference = transport.reference(state.source_ref)
        manifest = state.reader.describe_version(
            state.reader.query_ref(
                reference.source_ref.document_id,
                reference.source_ref.source_id,
                reference.source_ref.content_sha256,
            )
        )
        request = NarrativeReadRequest.from_dict(
            {
                "schema_version": "narrative-read-request/1",
                "narrative_ref": reference.to_dict(),
                "as_of_date": "2026-09-01",
                "expected_source": {
                    key: manifest[key]
                    for key in (
                        "canonical_entity_id",
                        "market",
                        "security_id",
                        "document_kind",
                        "fiscal_year",
                        "fiscal_period",
                    )
                },
            }
        )
        final_before = transport.read(request)
        receipt = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.job_ids,
            final_artifact=state.pin,
            compacted_at=T3,
        )
        assert receipt.attempts_compacted == 3
        assert receipt.logical_bytes_before > receipt.logical_bytes_after
        state.scheduler.materialize_event(state.event)
        assert not state.worker.process_one()
        assert len(state.model.calls) == calls == (0 if kind == "skip" else 1)
        final_after = transport.read(request)
        assert final_after.data == final_before.data == state.payload
        assert {
            key: value for key, value in final_after.receipt.items() if key != "read_at"
        } == {
            key: value
            for key, value in final_before.receipt.items()
            if key != "read_at"
        }
        after = snapshot(state)
        for table in ("jobs", "effects", "outbox", "narrative_model_reservations"):
            assert after[table] == before[table]
        assert {path: path.read_bytes() for path in raw} == raw
        compacted = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.job_ids,
            final_artifact=state.pin,
            compacted_at=T3,
        )
        assert compacted.already_compacted
        assert snapshot(state) == after
        assert json.loads(final_after.data)["selection"]["status"] == (
            "skipped_no_narrative" if kind == "skip" else "selected"
        )
