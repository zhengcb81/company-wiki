"""Bounded internal execution diagnostics; public summary wire stays canonical.

These receipts describe source-card execution, not a permit or semantic review.
Without a pinned selection only internal report consistency can be verified.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any

from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards
from company_wiki.source_catalog.narrative_evidence import summary_claim_type_for_roles
from .models import canonical_json, canonical_json_hash, _to_plain
from .narrative_contracts import (
    NarrativeContractError,
    NarrativeSelectResult,
    NarrativeSummaryResult,
)
from .terminal_receipt_contracts import is_terminal_receipt

INTERNAL_SCHEMA = "narrative-summary-execution/1"
ASSESSED_INTERNAL_SCHEMA = "narrative-summary-execution/2"
SUMMARY_EXECUTION_MARKERS = tuple(json.dumps(schema) for schema in (INTERNAL_SCHEMA,ASSESSED_INTERNAL_SCHEMA))
EXECUTION_SCHEMA = "source-extractive-execution/1"
EXECUTION_MAX_BYTES = 32 * 1024
_REPORT_KEYS = {
    "schema_version",
    "plan_sha256",
    "tasks",
    "source_coverage_complete",
    "model_coverage_complete",
    "model_diagnostic",
}
_TASK_KEYS = {
    "task",
    "task_binding_sha256",
    "source_disposition",
    "reason",
    "claim_id",
    "model_disposition",
    "priority",
}
_REASONS = {
    "admitted": ("source_card",),
    "duplicate": ("duplicate_scope",),
    "unsupported": ("source_not_parsed", "source_table_unresolved"),
    "deferred": ("draft_byte_budget",),
}
_MODELS = {"consider", "redundant", "unclear", "unprocessed", "invalid"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise NarrativeContractError(message)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _report(value: object) -> dict[str, Any]:
    _require(
        isinstance(value, Mapping) and set(value) == _REPORT_KEYS,
        "execution report fields are invalid",
    )
    try:
        encoded = canonical_json(_to_plain(value)).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise NarrativeContractError("execution report encoding is invalid") from exc
    _require(len(encoded) <= EXECUTION_MAX_BYTES, "execution report exceeds 32 KiB")
    # Return an owned plain value; diagnostic callers must not mutate job state.
    item = json.loads(encoded)
    _require(
        item["schema_version"] == EXECUTION_SCHEMA,
        "unsupported execution report schema",
    )
    _require(_sha(item["plan_sha256"]), "execution plan SHA is invalid")
    _require(isinstance(item["tasks"], list), "execution tasks must be an array")
    names, admitted, duplicates = set(), set(), []
    for row in item["tasks"]:
        _require(
            isinstance(row, dict) and set(row) == _TASK_KEYS,
            "execution task fields are invalid",
        )
        key = row["task"]
        _require(
            isinstance(key, str) and re.fullmatch(r"t[1-9][0-9]*", key) is not None,
            "execution task key is invalid",
        )
        _require(key not in names, "execution task keys are duplicated")
        names.add(key)
        _require(_sha(row["task_binding_sha256"]), "execution task SHA is invalid")
        disposition = row["source_disposition"]
        _require(
            isinstance(disposition, str) and disposition in _REASONS,
            "execution source disposition is invalid",
        )
        _require(
            row["reason"] in _REASONS[disposition], "execution source reason is invalid"
        )
        claim_id = row["claim_id"]
        if disposition == "admitted":
            _require(
                claim_id == key + "-source", "admitted source card identity is invalid"
            )
            _require(
                claim_id not in admitted, "admitted source card IDs are duplicated"
            )
            admitted.add(claim_id)
        elif disposition == "duplicate":
            _require(
                isinstance(claim_id, str),
                "duplicate source card requires its admitted identity",
            )
            duplicates.append(claim_id)
        else:
            _require(
                claim_id is None, "unemitted source task must not claim a source card"
            )
        model = row["model_disposition"]
        _require(
            isinstance(model, str) and model in _MODELS,
            "execution model disposition is invalid",
        )
        _require(
            row["priority"] in (None, "high", "normal", "low"),
            "execution priority is invalid",
        )
        if model in {"unprocessed", "invalid"}:
            _require(
                row["priority"] is None,
                "unprocessed execution must not invent priority",
            )
    _require(
        set(duplicates) <= admitted,
        "duplicate scope references an unknown admitted source card",
    )
    source_complete = all(
        row["source_disposition"] in {"admitted", "duplicate"} for row in item["tasks"]
    )
    model_complete = all(
        row["model_disposition"] not in {"unprocessed", "invalid"}
        for row in item["tasks"]
    )
    for key, expected in (
        ("source_coverage_complete", source_complete),
        ("model_coverage_complete", model_complete),
    ):
        _require(
            type(item[key]) is bool and item[key] == expected,
            "execution coverage differs from task dispositions",
        )
    diagnostic = item["model_diagnostic"]
    _require(
        diagnostic in (None, "RANK_INVALID", "RANK_INCOMPLETE"),
        "execution model diagnostic is invalid",
    )
    if diagnostic == "RANK_INVALID":
        _require(
            all(
                row["model_disposition"] == "invalid" and row["priority"] is None
                for row in item["tasks"]
            ),
            "invalid rank must preserve uniform invalid source order",
        )
    elif diagnostic == "RANK_INCOMPLETE":
        _require(
            any(row["model_disposition"] == "unprocessed" for row in item["tasks"])
            and all(row["model_disposition"] != "invalid" for row in item["tasks"]),
            "incomplete rank must expose unprocessed source tasks",
        )
    else:
        _require(
            model_complete,
            "unprocessed model tasks require an explicit rank diagnostic",
        )
    return item


def _bind_summary(
    summary: NarrativeSummaryResult,
    report: Mapping[str, Any],
    selected: NarrativeSelectResult | None,
) -> None:
    claims = (
        {claim.claim_id: claim for claim in summary.draft.claims}
        if summary.draft is not None
        else {}
    )
    admitted = {
        row["claim_id"]: row
        for row in report["tasks"]
        if row["source_disposition"] == "admitted"
    }
    _require(
        set(claims) == set(admitted),
        "execution admitted cards differ from canonical summary",
    )
    if selected is None:
        return
    summary.validate_against(selected)
    plan = build_summary_task_plan(
        selected.evidence_spans,
        reading_context=selected.reading_context,
        max_claims=max(1, len(selected.evidence_spans) * 2),
    )
    _require(
        report["plan_sha256"] == plan.binding_sha256,
        "execution plan differs from selected source tasks",
    )
    _require(
        [row["task"] for row in report["tasks"]] == [task.key for task in plan.tasks],
        "execution must retain every selected source task in source order",
    )
    tasks = {task.key: task for task in plan.tasks}
    known = {span.span_id: span for span in selected.evidence_spans}
    cards = {card.task.key: card for card in source_cards(plan, known)}
    for row in report["tasks"]:
        task = tasks[row["task"]]
        _require(
            row["task_binding_sha256"] == canonical_json_hash(task.to_binding()),
            "execution task differs from its selected source binding",
        )
        _require(
            (row["source_disposition"] == "unsupported")
            == (not cards[task.key].available),
            "execution availability differs from source-owned whole-card availability",
        )
        if row["source_disposition"] == "unsupported":
            _require(row["reason"] == cards[task.key].reason,
                     "execution unsupported reason differs from its source observation")
        if row["source_disposition"] == "admitted":
            claim = claims[row["claim_id"]]
            claim_type = summary_claim_type_for_roles(task.support_roles)
            _require(
                claim.evidence_ids == task.support_ids
                and claim.context_evidence_ids == task.context_ids,
                "source card evidence differs from its complete factual scope",
            )
            support_texts = [known[sid].raw_text or "" for sid in task.support_ids]
            expected_chars = sum(len(text) for text in support_texts) + len(support_texts) - 1
            _require(
                len(claim.text) == expected_chars,
                "source card bytes differ from their factual scope",
            )
            # Only materialize text already bounded by the canonical inner summary.
            _require(
                claim.text == "\n".join(support_texts),
                "source card bytes differ from their factual scope",
            )
            _require(
                claim.claim_type == claim_type
                and claim.modality
                == ("question" if claim_type == "analyst_question" else "uncertain"),
                "source card role or modality differs from its source-owned protocol",
            )
        elif row["source_disposition"] == "duplicate":
            owner = tasks[admitted[row["claim_id"]]["task"]]
            _require(
                (task.source_id, task.support_ids, task.context_ids)
                == (owner.source_id, owner.support_ids, owner.context_ids),
                "duplicate task does not share its admitted source scope",
            )


def wrap_summary(summary: NarrativeSummaryResult, execution: Mapping) -> dict[str, Any]:
    from .narrative_summary_assessment import ASSESSMENT_SCHEMA, validate_assessment_wire, validate_assessment_quality
    if execution.get('schema_version')==ASSESSMENT_SCHEMA:
        from .narrative_summary_protocols import ASSESSED_PROMPTS, scoped_protocol_for_prompt
        _require(summary.model is not None and summary.model.prompt_version in ASSESSED_PROMPTS
                 and summary.draft is not None,'assessment requires its explicit summary protocol')
        assert summary.draft is not None and summary.model is not None
        protocol = scoped_protocol_for_prompt(summary.model.prompt_version)
        try:
            report=validate_assessment_wire(execution,summary.to_dict()['draft']['claims'])
            _require(report['validator']['version']==protocol.assessor_version,'assessment protocol version mismatch')
            validate_assessment_quality(report,summary.to_dict()['draft']['claims'],summary.draft.status)
        except (ValueError,TypeError,KeyError) as exc:
            raise NarrativeContractError('invalid summary assessment wrapper') from exc
        return {'schema_version':ASSESSED_INTERNAL_SCHEMA,'summary':summary.to_dict(),'assessment':report}
    _require(
        isinstance(summary, NarrativeSummaryResult),
        "wrapper requires a canonical typed summary",
    )
    # Recheck its canonical wire cap, independently of the report's byte cap.
    typed = NarrativeSummaryResult.from_dict(summary.to_dict())
    report = _report(execution)
    _bind_summary(typed, report, None)
    return {
        "schema_version": INTERNAL_SCHEMA,
        "summary": typed.to_dict(),
        "execution": report,
    }


def parse_summary_job_result(
    value: object, *, selected: NarrativeSelectResult | None = None
) -> NarrativeSummaryResult:
    if isinstance(value,Mapping) and value.get('schema_version')==ASSESSED_INTERNAL_SCHEMA:
        from .narrative_summary_protocols import ASSESSED_PROMPTS, scoped_protocol_for_prompt
        from .narrative_summary_assessment import validate_assessment_wire, validate_assessment_material, validate_assessment_quality
        _require(set(value)=={'schema_version','summary','assessment'},'invalid assessed summary wrapper fields')
        summary=NarrativeSummaryResult.from_dict(value['summary'])
        _require(summary.model is not None and summary.model.prompt_version in ASSESSED_PROMPTS
                 and summary.draft is not None,'assessment requires its explicit summary protocol')
        assert summary.draft is not None and summary.model is not None
        protocol = scoped_protocol_for_prompt(summary.model.prompt_version)
        claims=summary.to_dict()['draft']['claims']
        try:
            if selected is None:
                report=validate_assessment_wire(value['assessment'],claims)
            else:
                summary.validate_against(selected)
                report=validate_assessment_material(value['assessment'],selected.evidence_spans,selected.reading_context,
                    claims,plan_max_claims=protocol.plan_max_claims,assessor_version=protocol.assessor_version)
            _require(report['validator']['version']==protocol.assessor_version,'assessment protocol version mismatch')
            validate_assessment_quality(report,claims,summary.draft.status)
        except (ValueError,TypeError,KeyError) as exc:
            raise NarrativeContractError('invalid assessed summary wrapper') from exc
        return summary
    if isinstance(value, Mapping) and value.get("schema_version") == INTERNAL_SCHEMA:
        _require(
            set(value) == {"schema_version", "summary", "execution"},
            "summary execution wrapper fields are invalid",
        )
        summary = NarrativeSummaryResult.from_dict(value["summary"])
        from .narrative_summary_protocols import ASSESSED_PROMPTS, scoped_protocol_for_prompt
        _require(summary.model is None or summary.model.prompt_version not in ASSESSED_PROMPTS,
                 'assessed protocol requires its assessment wrapper')
        report = _report(value["execution"])
        _bind_summary(summary, report, selected)
        return summary
    summary = NarrativeSummaryResult.from_dict(value)
    from .narrative_model_extractive import EXTRACTIVE_PROMPT_VERSION
    from .narrative_summary_protocols import ASSESSED_PROMPTS, scoped_protocol_for_prompt

    _require(
        summary.model is None
        or summary.model.prompt_version not in ({EXTRACTIVE_PROMPT_VERSION} | ASSESSED_PROMPTS),
        "source-extractive job result requires its execution wrapper",
    )
    if selected is not None:
        summary.validate_against(selected)
    return summary


def extract_summary_execution(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get('schema_version')==ASSESSED_INTERNAL_SCHEMA:
        parse_summary_job_result(value)
        from .models import _to_plain
        return _to_plain(value['assessment'])
    if value.get("schema_version") == INTERNAL_SCHEMA:
        parse_summary_job_result(value)
        return _report(value["execution"])
    if is_terminal_receipt(value) and "execution" in value:
        from .narrative_summary_assessment import ASSESSMENT_SCHEMA, validate_assessment_wire
        execution=value['execution']
        if isinstance(execution,Mapping) and execution.get('schema_version')==ASSESSMENT_SCHEMA:
            # The compact receipt intentionally discarded claims/prose. This
            # is bounded diagnostic shape/algebra, never source/semantic proof.
            try:
                return validate_assessment_wire(execution,None)
            except (ValueError,TypeError,KeyError) as exc:
                raise NarrativeContractError('invalid terminal summary assessment') from exc
        return _report(value["execution"])
    return None
