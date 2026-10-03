"""Terminal compaction is scoped, recoverable and preserves publication facts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import json
import sqlite3
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import (
    HandlerResult,
    JobStatus,
    canonical_json,
    canonical_json_hash,
    make_job_key,
)
from company_wiki.automation.narrative_contracts import SourceRefValue
from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller
from company_wiki.automation.narrative_projection import NarrativeEffectDispatcher
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.narrative_runtime import (
    NarrativeRuntimeDependencies,
    register_narrative_handlers,
)
from company_wiki.automation.terminal_receipt_contracts import FinalArtifactPin
from company_wiki.automation.terminal_receipts import compact_terminal_narrative_jobs
from company_wiki.automation.store import (
    IntegrityViolationError,
    TerminalResultCompactedError,
)
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactError,
    NarrativeArtifactStore,
)
from integration.test_narrative_runtime_e2e import (
    T0,
    T1,
    _drain,
    _event,
    _new_catalog,
    _pdf_bytes,
    _runtime,
)
from support.narrative_model_fixture import ReplayNarrativeModel


T2 = "2026-09-28T22:02:00Z"
T3 = "2026-09-28T22:03:00Z"


class MeteredReplayModel(ReplayNarrativeModel):
    model_id = "fixture-v1"
    max_output_tokens = 50

    def __init__(self, *, unknown=False):
        super().__init__()
        self.unknown = unknown

    def request_bytes(self, request):
        return request.data_json.encode("utf-8")

    def generate(self, request):
        response = super().generate(request)
        return replace(
            response,
            input_tokens=None if self.unknown else 31,
            output_tokens=None if self.unknown else 11,
        )


@contextmanager
def terminal_fixture(tmp_path, *, kind="txt", unknown=False):
    root = tmp_path / "terminal"
    root.mkdir()
    data = (
        _pdf_bytes("This policy describes meeting administration procedures.")
        if kind == "skip"
        else b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity.\n"
    )
    source = dict(
        name="source.pdf" if kind == "skip" else "source.txt",
        data=data,
        title="投资者关系管理办法（2025年8月）.pdf"
        if kind == "skip"
        else "ACME update",
        document_kind="ir_policy" if kind == "skip" else "investor_call_transcript",
        sidecar_overrides={"fiscal_period": "FY" if kind == "skip" else "Q2"},
    )
    catalog, reader, indexed = _new_catalog(root, [source])
    try:
        _, ref = next(iter(indexed.values()))
        model = MeteredReplayModel(unknown=unknown)
        auto, scheduler, worker = _runtime(root, reader, model)
        event = _event(reader, ref, event_id="terminal-event")
        auto.put_event(event)
        scheduler.materialize_event(event)
        jobs = auto.list_jobs()
        job_ids = tuple(job.job_id for job in jobs)
        ledger = NarrativeRunStore(auto.db_path)
        ledger.create_run(
            run_id="terminal-run",
            input_hash=canonical_json_hash(list(job_ids)),
            job_ids=job_ids,
            model_id=model.model_id,
            prompt_version=NARRATIVE_PROMPT_VERSION,
            pricing_version="fixture-price",
            input_micro_usd_per_million_tokens=1_000_000,
            output_micro_usd_per_million_tokens=2_000_000,
            max_tokens=1_000_000,
            max_micro_usd=2_000_000,
            max_output_bytes=4 * 1024 * 1024,
            created_at=T0,
        )
        # Register the real metering boundary before any attempt is executed.
        register_narrative_handlers(
            worker._executor,
            NarrativeRuntimeDependencies(
                reader=reader,
                model=model,
                model_caller=BudgetedNarrativeCaller(
                    store=ledger, run_id="terminal-run", model=model, clock=lambda: T1
                ),
            ),
        )
        assert _drain(worker, scheduler) == 3
        artifacts = NarrativeArtifactStore(
            catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir)
        )
        dispatcher = NarrativeEffectDispatcher(auto, artifacts, allowed_job_ids=job_ids)
        assert (
            dispatcher.dispatch_next(
                worker_id="terminal-projector",
                now=T2,
                lease_until=T3,
                expected_generation=auto.read_runtime_gate().control_generation,
            ).status
            == "visible"
        )
        version, payload = artifacts.read_visible(
            document_id=ref.document_id,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
        )
        pin = FinalArtifactPin(
            version.effect_id,
            version.artifact_version_id,
            version.content_sha256,
            version.byte_size,
            ref.document_id,
            ref.source_id,
            ref.content_sha256,
        )
        yield SimpleNamespace(
            root=root,
            catalog=catalog,
            reader=reader,
            auto=auto,
            scheduler=scheduler,
            worker=worker,
            event=event,
            ledger=ledger,
            jobs=jobs,
            job_ids=job_ids,
            model=model,
            artifacts=artifacts,
            version=version,
            payload=payload,
            pin=pin,
            source_ref=SourceRefValue.from_dict(
                {
                    "schema_version": ref.schema_version,
                    "document_id": ref.document_id,
                    "source_id": ref.source_id,
                    "content_sha256": ref.content_sha256,
                    "byte_size": ref.byte_size,
                    "mime_type": ref.mime_type,
                }
            ),
        )
    finally:
        catalog.close()


def snapshot(state):
    connection = state.auto._connect()
    try:
        return {
            table: [
                tuple(row)
                for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")
            ]
            for table in (
                "jobs",
                "attempts",
                "effects",
                "outbox",
                "narrative_model_reservations",
            )
        }
    finally:
        connection.close()


@pytest.mark.parametrize(
    "fault",
    [
        "active",
        "retry",
        "unfinished",
        "unacked",
        "effect_hash",
        "wrong_final",
        "outside",
        "run_pin",
        "missing_edge",
    ],
)
def test_ineligible_dag_or_pin_never_changes_any_rows(tmp_path, fault):
    with terminal_fixture(tmp_path) as state:
        by_type = {job.job_type: job for job in state.jobs}
        select_id = by_type["source.narrative_select"].job_id
        verify_id = by_type["source.narrative_verify"].job_id
        pin = state.pin

        def damage(connection):
            if fault in {"active", "retry"}:
                connection.execute(
                    "UPDATE jobs SET status=? WHERE job_id=?",
                    ("running" if fault == "active" else "retry_wait", select_id),
                )
            elif fault == "unfinished":
                connection.execute(
                    "UPDATE attempts SET finished_at=NULL WHERE job_id=?", (select_id,)
                )
            elif fault == "unacked":
                connection.execute(
                    "UPDATE outbox SET status='pending' WHERE effect_id=?",
                    (pin.effect_id,),
                )
            elif fault == "effect_hash":
                connection.execute(
                    "UPDATE effects SET actual_after_hash=? WHERE effect_id=?",
                    ("f" * 64, pin.effect_id),
                )
            elif fault == "run_pin":
                connection.execute(
                    "UPDATE narrative_run_jobs SET input_hash=? WHERE job_id=?",
                    ("f" * 64, select_id),
                )
            elif fault == "missing_edge":
                connection.execute(
                    "DELETE FROM job_dependencies WHERE job_id=? AND depends_on_job_id=?",
                    (verify_id, select_id),
                )

        if fault == "outside":
            old = by_type["source.narrative_verify"]
            outside = replace(
                old,
                job_id="outside-job",
                policy_version="outside-policy",
                job_key=make_job_key(
                    old.job_type,
                    old.subject_type,
                    old.subject_id,
                    old.input_hash,
                    "outside-policy",
                    old.handler_version,
                ),
                status=JobStatus.READY,
            )
            state.auto.put_job(outside)
            state.auto.add_job_dependency(outside.job_id, select_id)
        elif fault == "wrong_final":
            pin = replace(pin, artifact_sha256="f" * 64)
        else:
            state.auto._write_transaction(damage)
        before = snapshot(state)
        with pytest.raises(IntegrityViolationError):
            state.auto.compact_terminal_narrative_jobs(
                job_ids=state.job_ids, final_artifact=pin, compacted_at=T3
            )
        assert snapshot(state) == before


@pytest.mark.parametrize(
    "fault", ["prepared", "withdrawn", "tampered", "changed_before_commit"]
)
def test_catalog_proof_is_exact_visible_and_rechecked_before_compaction(
    tmp_path, monkeypatch, fault
):
    with terminal_fixture(tmp_path) as state:
        if fault in {"prepared", "withdrawn"}:
            with state.catalog.store.transaction() as connection:
                connection.execute(
                    "UPDATE narrative_artifact_versions SET status='prepared'"
                    if fault == "prepared"
                    else "UPDATE documents SET source_status='withdrawn'"
                )
        elif fault == "tampered":
            (state.catalog.config.catalog_dir / state.version.object_key).write_bytes(
                b"X" * len(state.payload)
            )
        else:
            original_read = state.artifacts.read_exact

            def change_after_read(**kwargs):
                result = original_read(**kwargs)
                with state.catalog.store.transaction() as connection:
                    connection.execute("UPDATE documents SET source_status='withdrawn'")
                return result

            monkeypatch.setattr(state.artifacts, "read_exact", change_after_read)
        before = snapshot(state)
        with pytest.raises(NarrativeArtifactError):
            compact_terminal_narrative_jobs(
                state.auto,
                state.artifacts,
                job_ids=state.job_ids,
                final_artifact=state.pin,
                compacted_at=T3,
            )
        assert snapshot(state) == before


def test_empty_scope_and_exact_repeat_are_readonly_and_compacted_body_is_named(
    tmp_path, monkeypatch
):
    with terminal_fixture(tmp_path, unknown=True) as state:
        first = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.job_ids,
            final_artifact=state.pin,
            compacted_at=T3,
        )
        assert first.attempts_compacted == 3
        assert first.logical_bytes_before > first.logical_bytes_after
        before = snapshot(state)

        def unexpected_write(*args, **kwargs):
            raise AssertionError("readonly empty/repeat entered a write transaction")

        monkeypatch.setattr(state.auto, "_write_transaction", unexpected_write)
        assert (
            state.auto.compact_terminal_narrative_jobs(
                job_ids=(), final_artifact=state.pin, compacted_at=T3
            ).attempts_compacted
            == 0
        )
        repeat = state.auto.compact_terminal_narrative_jobs(
            job_ids=state.job_ids, final_artifact=state.pin, compacted_at=T3
        )
        assert repeat.already_compacted and repeat.attempts_compacted == 0
        with pytest.raises(TerminalResultCompactedError):
            state.auto.result_for_effect(state.pin.effect_id)
        assert snapshot(state) == before
        for job in state.jobs:
            value = json.loads(state.auto.list_attempts(job.job_id)[-1].result_json)
            result = HandlerResult.from_dict(value)
            assert result.result["schema_version"] == "narrative-terminal-receipt/1.0"
            assert (
                result.result["final_artifact"]["artifact_version_id"]
                == state.pin.artifact_version_id
            )
            assert len(canonical_json(value).encode("utf-8")) < 8192


@pytest.mark.parametrize(
    "job_ids", [None, ("one",), ("one", "one", "two"), ("", "two", "three")]
)
def test_scope_requires_exact_three_distinct_ids(tmp_path, job_ids):
    from company_wiki.automation.store import AutomationStore

    auto = AutomationStore(tmp_path / "scope.db")
    pin = FinalArtifactPin(
        "effect", "artifact", "a" * 64, 1, "document", "source", "b" * 64
    )
    with pytest.raises((TypeError, ValueError)):
        auto.compact_terminal_narrative_jobs(
            job_ids=job_ids, final_artifact=pin, compacted_at=T3
        )


def test_sqlite_abort_mid_compaction_rolls_back_all_bodies_then_resume_succeeds(
    tmp_path,
):
    with terminal_fixture(tmp_path) as state:
        second_job = sorted(state.job_ids)[1].replace("'", "''")
        state.auto._write_transaction(
            lambda connection: connection.execute(
                "CREATE TRIGGER fail_terminal_compaction BEFORE UPDATE OF result_json ON attempts "
                f"WHEN OLD.job_id='{second_job}' BEGIN SELECT RAISE(ABORT,'injected compact crash'); END"
            )
        )
        before = snapshot(state)
        with pytest.raises(sqlite3.IntegrityError, match="injected compact crash"):
            compact_terminal_narrative_jobs(
                state.auto,
                state.artifacts,
                job_ids=state.job_ids,
                final_artifact=state.pin,
                compacted_at=T3,
            )
        assert snapshot(state) == before
        state.auto._write_transaction(
            lambda connection: connection.execute(
                "DROP TRIGGER fail_terminal_compaction"
            )
        )
        resumed = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.job_ids,
            final_artifact=state.pin,
            compacted_at=T3,
        )
        assert resumed.attempts_compacted == 3
        assert (
            state.artifacts.visible_version_for_effect(
                state.pin.effect_id
            ).content_sha256
            == state.pin.artifact_sha256
        )


def test_gate_generation_cas_precedes_same_state_and_keeps_other_owner_enabled(
    tmp_path,
):
    from company_wiki.automation.models import RuntimeState
    from company_wiki.automation.store import AutomationStore, ConcurrentUpdateError

    auto = AutomationStore(tmp_path / "gate.db")
    initial = auto.read_runtime_gate()
    enabled = auto.set_runtime_gate(
        RuntimeState.ENABLED,
        updated_at=T1,
        expected_generation=initial.control_generation,
    )
    for desired in (RuntimeState.ENABLED, RuntimeState.PAUSED):
        with pytest.raises(ConcurrentUpdateError):
            auto.set_runtime_gate(
                desired, updated_at=T2, expected_generation=initial.control_generation
            )
    assert auto.read_runtime_gate() == enabled
    assert (
        auto.set_runtime_gate(
            RuntimeState.ENABLED,
            updated_at=T2,
            expected_generation=enabled.control_generation,
        )
        == enabled
    )


def test_obsolete_generation_is_reaped_before_lease_expiry_only_in_scope_and_keeps_unknown_hold(
    tmp_path,
):
    from company_wiki.automation.models import (
        HandlerMetrics,
        HandlerOutcome,
        RuntimeState,
    )
    from company_wiki.automation.store import RuntimeGenerationError
    from unit.test_narrative_run_store import (
        setup_run,
        claim,
        reserve,
        T1 as NOW,
        T9 as LATER,
    )

    _, auto, ledger, generation, inside, outside = setup_run(tmp_path)
    a = claim(auto, generation, inside)
    b = claim(auto, generation, outside)
    held = reserve(ledger, a).record
    ledger.settle_model_usage(
        run_id="run-one",
        attempt_id=a.attempt.attempt_id,
        usage=None,
        response_sha256=None,
        error_code="MODEL_TIMEOUT",
        settled_at=NOW,
    )
    paused = auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=NOW)
    assert auto.reap_expired_attempts(now=NOW, allowed_job_ids=(inside.job_id,)) == (
        a.attempt.attempt_id,
    )
    reaped = auto.list_attempts(inside.job_id)[-1]
    assert reaped.error_code == "RUNTIME_GENERATION_CHANGED"
    assert reaped.finished_at == NOW < a.attempt.lease_until
    assert auto.list_attempts(outside.job_id) == (b.attempt,)
    current = auto.set_runtime_gate(
        RuntimeState.ENABLED,
        updated_at=NOW,
        expected_generation=paused.control_generation,
    )
    with pytest.raises(RuntimeGenerationError):
        auto.finish_attempt(
            attempt_id=a.attempt.attempt_id,
            lease_token=a.attempt.lease_token,
            runtime_generation=generation,
            finished_at=NOW,
            result=HandlerResult(
                HandlerOutcome.SUCCEEDED, {}, (), (), HandlerMetrics(0, 0, 0), None
            ),
        )
    assert auto.promote_ready_jobs(now=NOW, allowed_job_ids=(inside.job_id,)) == (
        inside.job_id,
    )
    reclaimed = auto.claim_next_ready(
        worker_id="new-owner",
        attempt_id="new-attempt",
        lease_token="new-token",
        now=NOW,
        lease_until=LATER,
        expected_generation=current.control_generation,
        allowed_job_ids=(inside.job_id,),
    )
    assert reclaimed.job.job_id == inside.job_id
    reservation = ledger.get_reservation("run-one", held.attempt_id)
    assert reservation.usage_status == "unknown"
    assert reservation.charged_tokens == held.reserved_tokens
    assert len(ledger.reservations_for_run("run-one")) == 1
