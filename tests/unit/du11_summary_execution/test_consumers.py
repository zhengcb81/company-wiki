from __future__ import annotations
import sqlite3
from types import SimpleNamespace
import pytest
from company_wiki.automation.models import (
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    canonical_json,
)
from company_wiki.automation.narrative_summary_execution import wrap_summary
from company_wiki.automation.narrative_verify import _dependencies, _VerifyFailure
from company_wiki.automation.narrative_batch import _attempt_model_diagnostics
from tools.document_understanding_benchmark import (
    phase_c_failure_review_material as review,
)


def result(value, *, outcome=HandlerOutcome.SUCCEEDED):
    return HandlerResult(
        outcome=outcome,
        result=value,
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=None,
    )


def test_verify_consumes_bound_inner_summary_only(materials):
    selected, summary, execution = materials
    context = SimpleNamespace(
        dependency_results={
            "source.narrative_select": result(selected.to_dict()),
            "source.narrative_summarize": result(wrap_summary(summary, execution)),
        }
    )
    actual_selected, actual_summary = _dependencies(context)
    assert actual_selected == selected
    assert actual_summary.to_dict() == summary.to_dict()
    bad = wrap_summary(summary, execution)
    bad["execution"]["plan_sha256"] = "f" * 64
    context.dependency_results["source.narrative_summarize"] = result(bad)
    with pytest.raises(_VerifyFailure):
        _dependencies(context)


@pytest.mark.parametrize("terminal", [False, True])
def test_batch_diagnostics_reads_execution_even_without_reasoning_usage_fields(
    materials, terminal
):
    _, summary, execution = materials
    value = (
        wrap_summary(summary, execution)
        if not terminal
        else {
            "schema_version": "narrative-terminal-receipt/1.0",
            "execution": execution,
        }
    )
    attempt = SimpleNamespace(
        attempt_id="attempt", result_json=canonical_json(result(value).to_dict())
    )
    store = SimpleNamespace(list_attempts=lambda job: [attempt])
    reservation = SimpleNamespace(
        usage_status="known", input_tokens=10, output_tokens=2
    )
    observations = _attempt_model_diagnostics(
        store, {"attempt": reservation}, SimpleNamespace(job_id="job")
    )
    assert len(observations) == 1
    assert observations[0]["execution"] == execution
    assert observations[0]["usage_status"] == "known"


def test_batch_invalid_execution_is_optional_diagnostic_not_job_outcome_change(
    materials,
):
    _, summary, execution = materials
    value = wrap_summary(summary, execution)
    value["execution"]["tasks"][0]["text"] = "body"
    attempt = SimpleNamespace(
        attempt_id="attempt", result_json=canonical_json(result(value).to_dict())
    )
    observations = _attempt_model_diagnostics(
        SimpleNamespace(list_attempts=lambda job: [attempt]),
        {},
        SimpleNamespace(job_id="job"),
    )
    assert observations == [
        {"attempt_id": "attempt", "diagnostic_status": "stored_observation_unreadable"}
    ]


def test_failure_review_keeps_inner_canonical_summary_and_report_separate(
    materials, tmp_path, monkeypatch
):
    selected, summary, execution = materials
    database = tmp_path / "AUTO.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        CREATE TABLE jobs(job_id TEXT,subject_id TEXT,job_type TEXT,status TEXT);
        CREATE TABLE attempts(job_id TEXT,attempt_id TEXT,attempt_no INTEGER,outcome TEXT,error_code TEXT,result_json TEXT,finished_at TEXT);
        CREATE TABLE narrative_run_jobs(run_id TEXT,job_id TEXT);
        CREATE TABLE narrative_model_reservations(run_id TEXT,job_id TEXT,attempt_id TEXT);
        """)
        records = [
            (
                "select",
                "source.narrative_select",
                "succeeded",
                None,
                result(selected.to_dict()),
            ),
            (
                "summary",
                "source.narrative_summarize",
                "succeeded",
                None,
                result(wrap_summary(summary, execution)),
            ),
            (
                "verify",
                "source.narrative_verify",
                "terminal_failure",
                "REPLAY_INVALID",
                result({}),
            ),
        ]
        for job, kind, outcome, error, value in records:
            connection.execute(
                "INSERT INTO jobs VALUES(?,?,?,?)", (job, "doc", kind, outcome)
            )
            connection.execute(
                "INSERT INTO narrative_run_jobs VALUES(?,?)", ("run", job)
            )
            connection.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?,?,?)",
                (
                    job,
                    job + "-attempt",
                    1,
                    outcome,
                    error,
                    canonical_json(value.to_dict()),
                    "2026-10-18T00:00:00Z",
                ),
            )
        connection.execute(
            "INSERT INTO narrative_model_reservations VALUES(?,?,?)",
            ("run", "summary", "summary-attempt"),
        )
    monkeypatch.setattr(
        review,
        "NarrativeRunStore",
        lambda db: SimpleNamespace(final_generations=lambda run: {}),
    )
    before = database.read_bytes()
    material = review._native_material(database, "run")
    assert material["items"][0]["summary_result"] == summary.to_dict()
    assert material["items"][0]["execution"] == execution
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "response_bytes",
    [
        b'{"decisions":[]}',
        b'{"decisions":[{"task":"t2","priority":"high","disposition":"consider"},{"task":"t1","priority":"low","disposition":"consider"}]}',
        b'{"decisions":[{"task":"t1","priority":"high","disposition":"consider","text":"fabricated business fact"}]}',
    ],
)
def test_actual_extractive_core_report_roundtrips_bound_public_summary(
    materials, response_bytes
):
    from dataclasses import replace
    from company_wiki.automation.narrative_contracts import NarrativeSummaryResult
    from company_wiki.automation.narrative_model import NarrativeModelResponse
    from company_wiki.automation.narrative_model_extractive import (
        EXTRACTIVE_PROMPT_VERSION,
        decode_extractive_result,
    )
    from company_wiki.automation.narrative_summary_execution import (
        parse_summary_job_result,
        extract_summary_execution,
    )

    selected, summary, _ = materials
    selected = replace(
        selected,
        reading_context={"schema_version": "du-production-reading/1", "groups": []},
    )
    response = NarrativeModelResponse(
        "fixture", "fixture", EXTRACTIVE_PROMPT_VERSION, response_bytes
    )
    decoded = decode_extractive_result(response, selected=selected)
    wire = summary.to_dict()
    wire["draft"] = decoded.draft
    wire["model"]["prompt_version"] = EXTRACTIVE_PROMPT_VERSION
    typed = NarrativeSummaryResult.from_dict(wire)
    wrapped = wrap_summary(typed, decoded.execution)
    assert parse_summary_job_result(wrapped, selected=selected) == typed
    assert extract_summary_execution(wrapped) == decoded.execution
    assert {c.text for c in typed.draft.claims} == {
        s.raw_text for s in selected.evidence_spans
    }
