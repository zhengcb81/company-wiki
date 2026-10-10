"""Real isolated JSON import -> durable outbox publication -> terminal compaction.

Only TEMP fixture originals and SQLite files exist. No model/provider calls.
"""

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.narrative_subject import NarrativeSubject, publication_target
from company_wiki.automation.models import (
    Event,
    Job,
    JobStatus,
    RiskClass,
    RuntimeState,
    Effect,
    EffectStatus,
    HandlerResult,
    HandlerOutcome,
    HandlerMetrics,
    canonical_json,
    canonical_json_hash,
    make_job_key,
    make_effect_key,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeBundle,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_generation import projection_generation_manifest
from company_wiki.automation.narrative_official_json import open_verified_projection
from company_wiki.automation.narrative_projection import (
    NarrativeEffectDispatcher,
    NarrativeBundleReader,
)
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore, IntegrityViolationError
from company_wiki.automation.terminal_receipt_contracts import (
    FinalArtifactPin,
    is_terminal_receipt,
)
from company_wiki.automation.terminal_receipts import compact_terminal_narrative_jobs
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactNotVisibleError,
    NarrativeArtifactConflictError,
)
from company_wiki.source_contract import EvidenceSpan
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs,
    persist_projection,
)
from integration.test_official_json_subject_artifacts import owned_state, digest

T0 = "2026-10-10T00:00:00Z"
T1 = "2026-10-10T00:01:00Z"
T2 = "2026-10-10T00:02:00Z"
T3 = "2026-10-10T00:03:00Z"
T9 = "2026-10-10T00:09:00Z"


def bundle_for(view, *, tamper=False):
    spans = view.evidence_spans
    if tamper:
        old = spans[0]
        changed = EvidenceSpan.create(
            source_id=old.source_id,
            coordinates=old.coordinates,
            raw_text="Invented expansion overseas",
            structured_value=old.structured_value,
            parser_name=old.parser_name,
            parser_version=old.parser_version,
            parse_status=old.parse_status,
            quality_flags=old.quality_flags,
        )
        spans = (changed,) + spans[1:]
    count = len(spans)
    selected = NarrativeSelectResult.from_dict(
        {
            "schema_version": "narrative-select-result/3.0",
            "subject_binding": view.subject.to_dict(),
            "source_metadata": {
                "source_class": "official_json",
                "title": "Official JSON records",
                "document_kind": "investor_relations",
                "language": view.language or "unknown",
            },
            "parser": {"name": "cwp_official_json", "version": "1.0.1"},
            "selector": {"name": "narrative-selector", "version": "1.3.0"},
            "selection": {
                "status": "selected",
                "coverage_complete": view.coverage_complete,
                "source_units": count,
                "candidate_count": count,
                "selected_count": count,
                "omitted_candidate_count": 0,
                "dropped_financial_count": 0,
                "pages_total": 0,
                "pages_read": 0,
                "lines_total": 0,
                "tables_total": 0,
                "tables_scanned": 0,
            },
            "evidence_spans": [span.to_dict() for span in spans],
            "prompt_review": {
                "status": "not_reviewed",
                "source_sha256": None,
                "evidence_sha256": None,
                "policy_hash": None,
                "reviewed_at": None,
            },
            "summary_scope": "selected_evidence_only",
        }
    )
    answer = next(
        span for span in spans if span.structured_value["source_role"] == "management"
    )
    summary = NarrativeSummaryResult.from_dict(
        {
            "schema_version": "narrative-summary-result/3.0",
            "subject_binding": view.subject.to_dict(),
            "language": view.language,
            "translate": False,
            "status": "completed",
            "draft": {
                "subject_id": view.subject.item_key,
                "subject_sha256": view.subject.subject_sha256,
                "language": view.language,
                "claims": [
                    {
                        "claim_id": "delivery",
                        "text": "Company expects Q4 delivery.",
                        "evidence_ids": [answer.span_id],
                        "claim_type": "company_statement",
                        "modality": "planned",
                        "needs_review": False,
                    }
                ],
                "status": "draft",
            },
            "model": {
                "adapter_id": "fixture",
                "model_id": "fixture-v1",
                "prompt_version": "official-json/1.0.0",
                "response_sha256": hashlib.sha256(
                    b"fixture-model-response"
                ).hexdigest(),
            },
            "prompt_review": selected.prompt_review.to_dict(),
        }
    )
    summary.validate_against(selected)
    wire = selected.to_dict()
    for key in ("parser", "selector", "summary_scope"):
        wire.pop(key)
    wire.update(
        schema_version="narrative-bundle/3.0",
        quality_status="verified",
        summary={
            key: summary.to_dict()[key]
            for key in ("status", "translate", "draft", "model")
        },
        versions={
            "parser": "1.0.1",
            "selector": "1.3.0",
            "material": None,
            "model": "fixture-v1",
            "prompt": "official-json/1.0.0",
            "bundle_producer": "3.0.0",
        },
        replay={"required": True, "locator_count": count},
    )
    bundle = NarrativeBundle.from_dict(wire)
    bundle.validate_against(selected, summary)
    return selected, summary, bundle


def install_dag(state, *, subject=None, tamper=False, label="a", run_prompt_version=None, bound_prompt=None):
    subject = subject or state.subjects[0]
    projection = build_projection_from_refs(
        state.catalog,
        refs=state.refs,
        layout_id=subject.to_dict()["adapter"]["layout_id"],
        issuer=subject.issuer,
        as_of_date=subject.as_of_date,
    )
    assert NarrativeSubject.from_projection(projection) == subject
    persist_projection(state.catalog, projection)
    view = open_verified_projection(
        state.catalog,
        projection_id=subject.item_key,
        expected_projection_sha256=subject.subject_sha256,
    )
    selected, summary, bundle = bundle_for(view, tamper=tamper)
    request = SimpleNamespace(
        profile="P1",
        model_options={
            "model_id": "fixture-v1",
            "endpoint": "https://example.invalid/v1/chat/completions",
            "max_output_tokens": 1200,
        },
    )
    manifest = projection_generation_manifest(
        request,
        subject,
        language=view.language,
        execution_versions={
            "selector": "1.3.0",
            "adapter": "openai-compatible-http/1",
            "prompt": "official-json/1.0.0",
            "model_request_schema": "narrative-model-request/2",
        },
        bundle_producer="3.0.0",
        narrative_adapter_version="1.0.1",
    )
    generation = canonical_json_hash(manifest)
    wire = {
        "schema_version": "source-revision-event/3.0",
        "subject_binding": subject.to_dict(),
        "source_metadata": selected.source_metadata.to_dict(),
    }
    parsed = SourceRevisionEventPayload.from_dict(wire)
    event = Event(
        "event-" + label,
        "source.revision_registered",
        "narrative_subject",
        subject.item_key,
        parsed.input_hash,
        canonical_json(wire),
        "narrative-fixture-" + label,
        T0,
        T0,
    )
    state.auto.put_event(event)
    jobs = []
    for kind in ("select", "summarize", "verify"):
        jobtype = "source.narrative_" + kind
        job = Job(
            job_id="job-" + label + "-" + kind,
            job_key=make_job_key(
                jobtype,
                event.subject_type,
                event.subject_id,
                event.input_hash,
                event.policy_version,
                "3.0.0",
            ),
            job_type=jobtype,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            input_hash=event.input_hash,
            policy_version=event.policy_version,
            handler_version="3.0.0",
            risk_class=RiskClass.LOW,
            status=JobStatus.READY,
            priority=0,
            not_before=T0,
            max_attempts=3,
            created_from_event_id=event.event_id,
            created_at=T0,
            updated_at=T0,
            last_error_code=None,
            last_error_detail=None,
        )
        state.auto.put_job(job)
        jobs.append(job)
    for child, parent in ((1, 0), (2, 0), (2, 1)):
        state.auto.add_job_dependency(jobs[child].job_id, jobs[parent].job_id)
    job_ids = tuple(job.job_id for job in jobs)
    ledger = NarrativeRunStore(state.auto.db_path)
    ledger.create_run(
        run_id="run-" + label,
        input_hash=canonical_json_hash(list(job_ids)),
        job_ids=job_ids,
        model_id="fixture-v1",
        prompt_version=run_prompt_version or "official-json/1.0.0",
        binding_json=canonical_json({"job_prompt_versions": {
            jobs[1].job_id: bound_prompt or "official-json/1.0.0"
        }}) if run_prompt_version is not None else None,
        pricing_version="fixture",
        input_micro_usd_per_million_tokens=1,
        output_micro_usd_per_million_tokens=1,
        max_tokens=10000,
        max_micro_usd=10000,
        max_output_bytes=4000000,
        created_at=T0,
    )
    target = publication_target(subject, generation)
    bundle_sha = canonical_json_hash(bundle.to_dict())
    key = make_effect_key(
        "narrative_bundle.publish",
        target,
        canonical_json_hash(
            {"verification_job_id": jobs[2].job_id, "bundle_sha256": bundle_sha}
        ),
        "3.0.0",
    )
    effect = Effect(
        "eff-" + key[:32],
        key,
        jobs[2].job_id,
        "narrative_bundle.publish",
        target,
        None,
        bundle_sha,
        None,
        EffectStatus.PENDING,
        T1,
        None,
    )
    for index, result in enumerate(
        (selected.to_dict(), summary.to_dict(), bundle.to_dict())
    ):
        lease = state.auto.claim_next_ready(
            worker_id="fixture",
            attempt_id="attempt-" + jobs[index].job_id,
            lease_token="lease-" + jobs[index].job_id,
            now=T1,
            lease_until=T9,
            expected_generation=state.runtime_generation,
            allowed_job_ids=(jobs[index].job_id,),
        )
        assert lease is not None
        state.auto.finish_attempt(
            attempt_id=lease.attempt.attempt_id,
            lease_token=lease.attempt.lease_token,
            runtime_generation=state.runtime_generation,
            finished_at=T1,
            result=HandlerResult(
                HandlerOutcome.SUCCEEDED,
                result,
                (),
                (effect,) if index == 2 else (),
                HandlerMetrics(17, 0.001, 3) if index == 1 else HandlerMetrics(0, 0, 0),
                None,
            ),
        )
    return SimpleNamespace(
        subject=subject,
        view=view,
        bundle=bundle,
        manifest=manifest,
        generation=generation,
        event=event,
        job_ids=job_ids,
        effect=effect,
        ledger=ledger,
    )


@contextmanager
def publication_state(tmp_path, *, subject_two=False, tamper=False, run_prompt_version=None, bound_prompt=None):
    with owned_state(tmp_path) as state:
        state.auto = AutomationStore(state.root / "auto.db")
        state.runtime_generation = state.auto.set_runtime_gate(
            RuntimeState.ENABLED, updated_at=T0
        ).control_generation
        state.item = install_dag(state, tamper=tamper, run_prompt_version=run_prompt_version, bound_prompt=bound_prompt)
        if subject_two:
            state.other = install_dag(state, subject=state.subjects[1], label="b")
        state.loads = []

        def loader(subject):
            state.loads.append(subject.item_key)
            return open_verified_projection(
                state.catalog,
                projection_id=subject.item_key,
                expected_projection_sha256=subject.subject_sha256,
            )

        state.loader = loader
        yield state


def dispatcher(state, item=None, **options):
    item = item or state.item
    values = {
        "allowed_job_ids": item.job_ids,
        "generation_manifests": {item.subject.item_key: item.manifest},
        "projection_loader": state.loader,
    }
    values.update(options)
    return NarrativeEffectDispatcher(state.auto, state.artifacts, **values)


def dispatch(state, worker=None):
    return (worker or dispatcher(state)).dispatch_next(
        worker_id="projector",
        now=T2,
        lease_until=T9,
        expected_generation=state.runtime_generation,
    )


def pin_for(state, item=None):
    item = item or state.item
    version = state.artifacts.visible_version_for_effect(item.effect.effect_id)
    anchor = item.subject.anchor_ref
    return FinalArtifactPin(
        version.effect_id,
        version.artifact_version_id,
        version.content_sha256,
        version.byte_size,
        anchor["document_id"],
        anchor["source_id"],
        anchor["content_sha256"],
        subject_binding=item.subject,
        generation_sha256=item.generation,
    )


def body_snapshot(state):
    conn = state.auto._connect()
    try:
        return tuple(
            tuple(row)
            for row in conn.execute(
                "SELECT attempt_id,result_json FROM attempts ORDER BY attempt_id"
            )
        )
    finally:
        conn.close()


def test_raw_seven_positional_pin_wire_stays_identical():
    pin = FinalArtifactPin("e", "a", "a" * 64, 12, "d", "s", "b" * 64)
    assert pin.to_dict() == {
        "effect_id": "e",
        "artifact_version_id": "a",
        "artifact_sha256": "a" * 64,
        "byte_size": 12,
        "document_id": "d",
        "source_id": "s",
        "source_sha256": "b" * 64,
    }


def test_projection_pin_has_subject_and_generation_without_anchor_identity():
    from unit.test_official_json_model_subject import binding

    subject = NarrativeSubject.from_dict(binding())
    anchor = subject.anchor_ref
    pin = FinalArtifactPin(
        "e",
        "a",
        "a" * 64,
        12,
        anchor["document_id"],
        anchor["source_id"],
        anchor["content_sha256"],
        subject_binding=subject,
        generation_sha256="f" * 64,
    )
    assert set(pin.to_dict()) == {
        "effect_id",
        "artifact_version_id",
        "artifact_sha256",
        "byte_size",
        "subject_binding",
        "generation_sha256",
    }
    assert pin.to_dict()["subject_binding"] == subject.to_dict()
    with pytest.raises(ValueError):
        replace(pin, generation_sha256=None)
    with pytest.raises(ValueError):
        replace(pin, source_sha256="e" * 64)
    assert is_terminal_receipt({"schema_version": "narrative-terminal-receipt/2.0"})


def test_publish_subject_generation_and_read_uses_one_fresh_view_per_operation(
    tmp_path,
):
    with publication_state(tmp_path) as state:
        result = dispatch(state)
        assert result.status == "visible" and state.loads == [
            state.item.subject.item_key
        ]
        version = state.artifacts.visible_version_for_effect(
            state.item.effect.effect_id
        )
        metadata = json.loads(version.metadata_json)
        assert metadata["subject_binding"] == state.item.subject.to_dict()
        assert metadata["generation_manifest"] == state.item.manifest
        assert (
            metadata["generation_sha256"]
            == state.item.generation
            == version.policy_sha256
        )
        reader = NarrativeBundleReader(state.artifacts, projection_loader=state.loader)
        read = reader.read_subject(
            subject=state.item.subject, generation_sha256=state.item.generation
        )
        assert read.bundle.subject == state.item.subject and read.artifact == version
        assert state.loads == [state.item.subject.item_key] * 2
        anchor = state.item.subject.anchor_ref
        with pytest.raises(NarrativeArtifactNotVisibleError):
            reader.read(
                document_id=anchor["document_id"],
                source_id=anchor["source_id"],
                source_sha256=anchor["content_sha256"],
            )


@pytest.mark.parametrize("error", ["missing", "wrong_subject"])
def test_generation_manifest_must_bind_complete_subject_before_any_object_write(
    tmp_path, error
):
    with publication_state(tmp_path, subject_two=True) as state:
        manifests = (
            {}
            if error == "missing"
            else {state.item.subject.item_key: state.other.manifest}
        )
        result = dispatch(state, dispatcher(state, generation_manifests=manifests))
        assert result.status == "failed"
        assert state.artifacts.prepared_effects() == () and state.loads == []


def test_two_issuers_sharing_exact_parents_publish_and_compact_independently(tmp_path):
    with publication_state(tmp_path, subject_two=True) as state:
        assert state.item.subject.anchor_ref == state.other.subject.anchor_ref
        assert dispatch(state).status == "visible"
        assert dispatch(state, dispatcher(state, state.other)).status == "visible"
        assert state.item.effect.target != state.other.effect.target
        before = {
            job: state.auto.list_attempts(job)[-1].result_json
            for job in state.other.job_ids
        }
        pin = pin_for(state)
        compact = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.item.job_ids,
            final_artifact=pin,
            compacted_at=T3,
            projection_loader=state.loader,
        )
        assert (
            compact.attempts_compacted == 3
            and compact.logical_bytes_after < compact.logical_bytes_before
        )
        for job in state.item.job_ids:
            value = json.loads(state.auto.list_attempts(job)[-1].result_json)
            assert value["result"]["schema_version"] == "narrative-terminal-receipt/2.0"
            assert value["result"]["final_artifact"] == pin.to_dict()
        assert {
            job: state.auto.list_attempts(job)[-1].result_json
            for job in state.other.job_ids
        } == before
        again = compact_terminal_narrative_jobs(
            state.auto,
            state.artifacts,
            job_ids=state.item.job_ids,
            final_artifact=pin,
            compacted_at=T3,
            projection_loader=state.loader,
        )
        assert again.already_compacted and again.attempts_compacted == 0


def test_ack_committed_then_crash_reconciles_without_reclaiming_or_model_work(
    tmp_path, monkeypatch
):
    with publication_state(tmp_path) as state:
        worker = dispatcher(state)
        actual = state.auto.ack_outbox

        def crash_after_ack(**values):
            actual(**values)
            raise RuntimeError("fixture crash after ACK")

        monkeypatch.setattr(state.auto, "ack_outbox", crash_after_ack)
        result = dispatch(state, worker)
        assert result.status == "activation_pending" and state.loads == []
        before = body_snapshot(state)
        assert worker.reconcile_prepared(activated_at=T3) == (
            state.item.effect.effect_id,
        )
        assert (
            state.loads == [state.item.subject.item_key]
            and body_snapshot(state) == before
        )
        assert worker.reconcile_prepared(activated_at=T3) == ()


def test_wrong_current_projection_blocks_visibility_then_fresh_reconcile_recovers(
    tmp_path,
):
    with publication_state(tmp_path, subject_two=True) as state:

        def wrong(subject):
            return state.other.view

        worker = dispatcher(state, projection_loader=wrong)
        assert dispatch(state, worker).status == "activation_pending"
        with pytest.raises(NarrativeArtifactNotVisibleError):
            state.artifacts.visible_version_for_effect(state.item.effect.effect_id)
        worker = dispatcher(state)
        assert worker.reconcile_prepared(activated_at=T3) == (
            state.item.effect.effect_id,
        )
        assert state.loads == [state.item.subject.item_key]


def test_stale_or_tampered_selected_field_cannot_become_visible(tmp_path):
    with publication_state(tmp_path, tamper=True) as state:
        worker = dispatcher(state)
        assert dispatch(state, worker).status == "activation_pending"
        assert worker.reconcile_prepared(activated_at=T3) == ()
        with pytest.raises(NarrativeArtifactNotVisibleError):
            state.artifacts.visible_version_for_effect(state.item.effect.effect_id)


def test_nonanchor_original_byte_corruption_blocks_reconcile_and_read(tmp_path):
    with publication_state(tmp_path) as state:
        assert dispatch(state).status == "visible"
        reader = NarrativeBundleReader(state.artifacts, projection_loader=state.loader)
        second = state.refs[1]["content_sha256"]
        path = next(
            p
            for p in (state.root / "companies").rglob("*.json")
            if not p.name.endswith(".source.json") and digest(p.read_bytes()) == second
        )
        original = path.read_bytes()
        try:
            path.write_bytes(original + b" ")
            with pytest.raises((ValueError, RuntimeError)):
                reader.read_subject(
                    subject=state.item.subject, generation_sha256=state.item.generation
                )
            before = body_snapshot(state)
            with pytest.raises((ValueError, RuntimeError)):
                compact_terminal_narrative_jobs(
                    state.auto,
                    state.artifacts,
                    job_ids=state.item.job_ids,
                    final_artifact=pin_for(state),
                    compacted_at=T3,
                    projection_loader=state.loader,
                )
            assert body_snapshot(state) == before
        finally:
            path.write_bytes(original)


@pytest.mark.parametrize(
    "fault", ["subject", "generation", "job_subject", "unfinished"]
)
def test_compaction_rejects_wrong_subject_generation_or_nonterminal_dag_without_writes(
    tmp_path, fault
):
    with publication_state(tmp_path, subject_two=True) as state:
        assert dispatch(state).status == "visible"
        pin = pin_for(state)
        if fault == "subject":
            pin = replace(pin, subject_binding=state.other.subject)
        elif fault == "generation":
            pin = replace(pin, generation_sha256="f" * 64)
        else:

            def damage(conn):
                if fault == "job_subject":
                    job = state.auto.get_job(state.item.job_ids[0])
                    wrong_subject = state.item.subject.anchor_ref["document_id"]
                    wrong_key = make_job_key(
                        job.job_type,
                        job.subject_type,
                        wrong_subject,
                        job.input_hash,
                        job.policy_version,
                        job.handler_version,
                    )
                    conn.execute(
                        "UPDATE jobs SET subject_id=?,job_key=? WHERE job_id=?",
                        (wrong_subject, wrong_key, job.job_id),
                    )
                else:
                    conn.execute(
                        "UPDATE jobs SET status='running' WHERE job_id=?",
                        (state.item.job_ids[0],),
                    )

            state.auto._write_transaction(damage)
        before = body_snapshot(state)
        with pytest.raises(IntegrityViolationError):
            state.auto.compact_terminal_narrative_jobs(
                job_ids=state.item.job_ids, final_artifact=pin, compacted_at=T3
            )
        assert body_snapshot(state) == before


def test_exact_generation_reader_rejects_wrong_artifact_generation(tmp_path):
    with publication_state(tmp_path) as state:
        assert dispatch(state).status == "visible"
        pin = pin_for(state)
        reader = NarrativeBundleReader(state.artifacts, projection_loader=state.loader)
        with pytest.raises(NarrativeArtifactConflictError):
            reader.read_subject(
                subject=state.item.subject,
                generation_sha256="f" * 64,
                artifact_version_id=pin.artifact_version_id,
            )


def test_terminal_compaction_uses_same_actual_job_prompt_as_mixed_run_ledger(tmp_path):
    with publication_state(tmp_path, run_prompt_version="1.7.0") as state:
        assert dispatch(state).status == "visible"
        result = compact_terminal_narrative_jobs(state.auto, state.artifacts,
            job_ids=state.item.job_ids, final_artifact=pin_for(state), compacted_at=T3,
            projection_loader=state.loader)
        assert result.attempts_compacted == 3
        for job in state.item.job_ids:
            value = json.loads(state.auto.list_attempts(job)[-1].result_json)
            assert value["result"]["schema_version"] == "narrative-terminal-receipt/2.0"
        summary = state.auto.list_attempts(state.item.job_ids[1])[-1]
        metrics = json.loads(summary.result_json)["metrics"]
        assert metrics["tokens"] == 17 and metrics["cost_usd"] == 0.001


def test_terminal_compaction_wrong_frozen_job_prompt_does_not_destroy_results(tmp_path):
    with publication_state(tmp_path, run_prompt_version="1.7.0", bound_prompt="different-prompt") as state:
        assert dispatch(state).status == "visible"
        before = body_snapshot(state)
        with pytest.raises(IntegrityViolationError, match="model/prompt"):
            compact_terminal_narrative_jobs(state.auto, state.artifacts,
                job_ids=state.item.job_ids, final_artifact=pin_for(state), compacted_at=T3,
                projection_loader=state.loader)
        assert body_snapshot(state) == before
