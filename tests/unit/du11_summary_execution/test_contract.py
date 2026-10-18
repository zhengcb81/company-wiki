from __future__ import annotations
from copy import deepcopy
import pytest
from company_wiki.automation.narrative_contracts import NarrativeContractError
from company_wiki.automation.narrative_summary_execution import (
    INTERNAL_SCHEMA,
    wrap_summary,
    parse_summary_job_result,
    extract_summary_execution,
)


def test_legacy_canonical_summary_is_unchanged(materials):
    selected, summary, _ = materials
    assert parse_summary_job_result(summary.to_dict(), selected=selected) == summary
    assert extract_summary_execution(summary.to_dict()) is None


def test_mixed_usable_and_unresolved_table_card_survives_full_wrapper_and_terminal_path(materials):
    from dataclasses import replace
    from company_wiki.automation.narrative_contracts import NarrativeSummaryResult
    from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
    selected, summary, _ = materials
    selected = replace(selected, evidence_spans=(selected.evidence_spans[0],
        replace(selected.evidence_spans[1], quality_flags=("table_structure_ambiguous",))),
        reading_context={"schema_version": "du-production-reading/1", "groups": []})
    plan = compile_extractive_plan(selected)
    wire = summary.to_dict()
    wire['draft'] = plan.draft
    summary = NarrativeSummaryResult.from_dict(wire)
    value = wrap_summary(summary, plan.execution)
    assert parse_summary_job_result(value, selected=selected) == summary
    assert len(summary.draft.claims) == 1
    assert extract_summary_execution({"schema_version": "narrative-terminal-receipt/1.0",
        "execution": plan.execution, "original_result_sha256": "f" * 64}) == plan.execution
    # Another *known* reason is not interchangeable with the observed cause.
    value['execution']['tasks'][1]['reason'] = 'source_not_parsed'
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value, selected=selected)


def test_wrapper_bound_to_actual_selected_and_inner_public_wire_is_unchanged(materials):
    selected, summary, report = materials
    value = wrap_summary(summary, report)
    assert set(value) == {"schema_version", "summary", "execution"}
    assert value["schema_version"] == INTERNAL_SCHEMA == "narrative-summary-execution/1"
    assert (
        parse_summary_job_result(value, selected=selected).to_dict()
        == summary.to_dict()
    )
    assert extract_summary_execution(value) == report
    value["execution"]["tasks"][0]["priority"] = "low"
    assert report["tasks"][0]["priority"] == "high"


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(extra="body"),
        lambda r: r.update(schema_version="wrong"),
        lambda r: r.update(plan_sha256="not-sha"),
        lambda r: r["tasks"].append(deepcopy(r["tasks"][0])),
        lambda r: r["tasks"][0].update(text="source body must not enter report"),
        lambda r: r["tasks"][0].update(source_disposition="approved"),
        lambda r: r["tasks"][0].update(reason="arbitrary original-language text"),
        lambda r: r["tasks"][0].update(model_disposition="accepted"),
        lambda r: r["tasks"][0].update(priority="urgent"),
        lambda r: r.update(model_diagnostic="raw provider text"),
        lambda r: r.update(source_coverage_complete=True),
        lambda r: r.update(model_coverage_complete=True),
        lambda r: r.update(source_coverage_complete=0),
        lambda r: r["tasks"][0].update(claim_id=None),
        lambda r: r["tasks"][1].update(claim_id="t1-source"),
        lambda r: r["tasks"][0].update(reason="draft_byte_budget"),
        lambda r: r["tasks"][0].update(claim_id="missing"),
    ],
)
def test_invalid_internal_report_is_refused(materials, change):
    _, summary, report = materials
    change(report)
    with pytest.raises(NarrativeContractError):
        wrap_summary(summary, report)


@pytest.mark.parametrize(
    "field", ["plan_sha256", "task_binding_sha256", "missing_task", "unknown_task"]
)
def test_selected_binding_cannot_be_counterfeited(materials, field):
    selected, summary, report = materials
    value = wrap_summary(summary, report)
    if field == "plan_sha256":
        value["execution"][field] = "e" * 64
    elif field == "task_binding_sha256":
        value["execution"]["tasks"][0][field] = "e" * 64
    elif field == "missing_task":
        value["execution"]["tasks"].pop()
    else:
        value["execution"]["tasks"][0]["task"] = "t999"
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value, selected=selected)


def test_duplicate_must_reference_an_admitted_claim_and_true_same_source_scope(
    materials,
):
    selected, summary, report = materials
    report["tasks"][1].update(
        source_disposition="duplicate", reason="duplicate_scope", claim_id="t1-source"
    )
    report["source_coverage_complete"] = True
    value = wrap_summary(summary, report)
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value, selected=selected)
    report["tasks"][1]["claim_id"] = "no-admitted-claim"
    with pytest.raises(NarrativeContractError):
        wrap_summary(summary, report)


def test_report_byte_cap_is_measured_without_dropping_rows(materials):
    _, summary, report = materials
    report["tasks"] = [
        dict(report["tasks"][1], task="t" + str(i)) for i in range(1, 400)
    ]
    report["tasks"][0] = dict(
        report["tasks"][0],
        source_disposition="admitted",
        reason="source_card",
        claim_id="t1-source",
    )
    with pytest.raises(NarrativeContractError):
        wrap_summary(summary, report)


def test_terminal_receipt_keeps_typed_report_without_summary(materials):
    _, _, report = materials
    receipt = {
        "schema_version": "narrative-terminal-receipt/1.0",
        "execution": report,
        "original_result_sha256": "f" * 64,
    }
    assert extract_summary_execution(receipt) == report
    assert (
        extract_summary_execution({"schema_version": "narrative-terminal-receipt/1.0"})
        is None
    )
    receipt["execution"]["tasks"][0]["text"] = "hidden source prose"
    with pytest.raises(NarrativeContractError):
        extract_summary_execution(receipt)


def test_wrapper_unknown_fields_and_invalid_inner_still_refused(materials):
    _, summary, report = materials
    value = wrap_summary(summary, report)
    value["extra"] = True
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value)
    value.pop("extra")
    value["summary"]["translate"] = True
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value)


def test_unprocessed_model_rank_does_not_remove_source_admitted_cards(materials):
    selected, summary, report = materials
    for row in report["tasks"]:
        row.update(model_disposition="unprocessed", priority=None)
    value = wrap_summary(summary, report)
    assert parse_summary_job_result(value, selected=selected) == summary


def test_invalid_rank_diagnostic_requires_uniform_invalid_state(materials):
    _, summary, report = materials
    report["model_diagnostic"] = "RANK_INVALID"
    with pytest.raises(NarrativeContractError):
        wrap_summary(summary, report)
    for row in report["tasks"]:
        row.update(model_disposition="invalid", priority=None)
    assert extract_summary_execution(wrap_summary(summary, report)) == report


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(text="Unsupported replacement narrative"),
        lambda c: c.update(modality="actual"),
        lambda c: c.update(claim_type="uncertain"),
        lambda c: c.update(claim_id="arbitrary-id"),
        lambda c: c.update(evidence_ids=[]),
    ],
)
def test_selected_v5_card_exact_bytes_role_modality_and_identity_are_bound(
    materials, change
):
    selected, summary, report = materials
    value = wrap_summary(summary, report)
    change(value["summary"]["draft"]["claims"][0])
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value, selected=selected)


def test_duplicate_true_source_scope_remains_traced_without_dropping_task_row(
    materials,
):
    from dataclasses import replace
    from company_wiki.automation.models import canonical_json_hash
    from company_wiki.document_understanding.summary_tasks import (
        build_summary_task_plan,
    )

    selected, summary, report = materials
    sid = selected.evidence_spans[0].span_id
    selected = replace(
        selected,
        reading_context={
            "schema_version": "du-production-reading/1",
            "groups": [
                {
                    "group_id": "g1",
                    "kind": "paragraph_event",
                    "section_role": "business",
                    "evidence_ids": [sid],
                },
                {
                    "group_id": "g2",
                    "kind": "paragraph_event",
                    "section_role": "business",
                    "evidence_ids": [sid],
                },
            ],
        },
    )
    # The unused second source span remains a third standalone task.
    plan = build_summary_task_plan(
        selected.evidence_spans, reading_context=selected.reading_context, max_claims=4
    )
    rows = []
    for i, task in enumerate(plan.tasks):
        rows.append(
            {
                "task": task.key,
                "task_binding_sha256": canonical_json_hash(task.to_binding()),
                "source_disposition": ["admitted", "duplicate", "deferred"][i],
                "reason": ["source_card", "duplicate_scope", "draft_byte_budget"][i],
                "claim_id": "t1-source" if i < 2 else None,
                "model_disposition": "unprocessed",
                "priority": None,
            }
        )
    report.update(plan_sha256=plan.binding_sha256, tasks=rows)
    value = wrap_summary(summary, report)
    assert parse_summary_job_result(value, selected=selected) == summary
    assert len(extract_summary_execution(value)["tasks"]) == 3


def test_report_cannot_label_parsed_source_task_unsupported(materials):
    selected, summary, report = materials
    report["tasks"][1].update(
        source_disposition="unsupported", reason="source_not_parsed"
    )
    value = wrap_summary(summary, report)
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(value, selected=selected)


def test_audit_availability_does_not_materialize_deferred_source_quote(
    materials, monkeypatch
):
    from types import SimpleNamespace
    from company_wiki.automation import narrative_summary_execution as audit

    selected, summary, report = materials

    def lazy_cards(plan, known):
        return (SimpleNamespace(task=task, available=True) for task in plan.tasks)

    monkeypatch.setattr(audit, "source_cards", lazy_cards)
    assert (
        audit.parse_summary_job_result(wrap_summary(summary, report), selected=selected)
        == summary
    )


def test_v5_job_result_cannot_bypass_source_binding_by_omitting_wrapper(materials):
    from company_wiki.automation.narrative_contracts import NarrativeSummaryResult
    from company_wiki.automation.narrative_model_extractive import (
        EXTRACTIVE_PROMPT_VERSION,
    )

    selected, summary, report = materials
    wire = summary.to_dict()
    wire["model"]["prompt_version"] = EXTRACTIVE_PROMPT_VERSION
    # Public canonical summaries remain valid, including the inner wrapper wire.
    typed = NarrativeSummaryResult.from_dict(wire)
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(wire, selected=selected)
    assert (
        parse_summary_job_result(wrap_summary(typed, report), selected=selected)
        == typed
    )
