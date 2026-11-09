"""Bounded original actor context; retention is not entity resolution.

The source owner supplies ordered predecessor IDs. This helper may add the
nearest body as meaning context for first-person text. It never declares that
``we`` denotes the issuer, a subsidiary, or an entity inferred from a name.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
from company_wiki.document_understanding.source_turn_markers import (
    ROLE_INVESTOR, explicit_qa_marker, observed_source_turn,
)
from .narrative_pdf_turns import printed_turn_is_context

ACTOR_CONTEXT_FEATURE_VERSION = "source-actor-context/1"
ACTOR_CONTEXT_SCAN_PASSES = 5
MAX_ACTOR_CONTEXT_UNITS = 8
MAX_ACTOR_CONTEXT_CHARS = 2048

_FIRST_PERSON = re.compile(
    r"\bwe\b|\bour\s+(?!(?:is|are|was|were|means)\b)[\w-]+|我们|我們", re.I)
_BACKREFERENCE = re.compile(
    r'^\s*(?:beyond\s+this\b|building\s+on\s+(?:this|that)\b|'
    r'(?:in|for)\s+(?:this|that)\s+(?:business|operation)\b|'
    r'在此基[础礎]上|基[于於]上述|就[此該该](?:[业業][务務]|[经經][营營])|'
    r'[对對]此[业業][务務])', re.I)
_QUESTION = re.compile(r"^\s*(?:请问|請問)")
_LOCAL_FRAME = re.compile(
    r"^\s*(?:(?:separately|however|in contrast)\s*[,;:]?\s*)?"
    r"(?:the\s+(?:parent\s+company|subsidiary|business\s+unit)\b|"
    r"(?:at|within)\s+[^,\n]{1,100},)|"
    r"^\s*(?:另外[，,]?|另行[，,]?)?(?:母公司|该子公司|該子公司|本公司)|"
    r"^\s*在[^，,\n]{1,80}(?:子公司|部门|部門|业务|業務)[，,]", re.I)
_NON_BODY_ROLES = frozenset({"analyst", "analyst_question", "investor_question",
    "question", "qa_question", "operator", "operator_question", "qa_text_shadow"})
_NON_BODY_KINDS = frozenset({"heading", "header", "footer", "table", "table_row",
    "table_header", "table_caption", "question", "cell", "table_cell"})


def _field(unit: Any, key: str, default: Any = None) -> Any:
    return unit.get(key, default) if isinstance(unit, Mapping) else getattr(unit, key, default)


def _text(unit: Any) -> str:
    return str(_field(unit, "text", _field(unit, "raw_text", "")) or "")


def _source(unit: Any) -> Any:
    return _field(unit, "parent_id", _field(unit, "source_id"))


def _scope(unit: Any, *keys: str) -> Any:
    metadata = _field(unit, "metadata", {}) or {}
    for key in keys:
        value = _field(unit, key)
        if value is None and isinstance(metadata, Mapping):
            value = metadata.get(key)
        if value is not None:
            return value
    return None


def _turn(unit: Any) -> tuple[str | None, str | None]:
    metadata = _field(unit, 'metadata', {}) or {}
    hints = dict(metadata) if isinstance(metadata, Mapping) else {}
    for key in ('speaker', 'turn_id', 'native_speaker_turn'):
        value = _field(unit, key)
        if value is not None:
            hints[key] = value
    return observed_source_turn(hints)


def _body(unit: Any, text: str) -> bool:
    role = _field(unit, "role", _field(unit, "source_role"))
    kind = _field(unit, "kind", _field(unit, "unit_kind"))
    coordinates = _field(unit, "coordinates", _field(unit, "locator"))
    return bool(text and role not in _NON_BODY_ROLES and kind not in _NON_BODY_KINDS
        and not printed_turn_is_context(unit)
        and _field(coordinates, "table_index") is None
        and explicit_qa_marker(text) != ROLE_INVESTOR
        and not _QUESTION.search(text) and not text.rstrip().endswith(("?", "？")))


def actor_context_closure(
    target_unit_id: str,
    predecessor_unit_ids: tuple[str, ...],
    *,
    units: Mapping[str, Any],
    window_complete: bool,
    work_budget: WorkBudget,
    max_units: int = MAX_ACTOR_CONTEXT_UNITS,
    max_chars: int = MAX_ACTOR_CONTEXT_CHARS,
) -> dict[str, Any]:
    """Retain one observed adjacent body without resolving first-person identity.

    ``unique`` describes the retained context dependency, not a unique actor.
    An incomplete search can still retain its observed nearest predecessor;
    it cannot establish absence or identity. No predecessor, an explicit scope
    switch, or an unsafe neighbour remains nonblocking ``not_applicable`` with
    unknown attribution. Only actual shared work exhaustion returns partial.
    The helper never skips an unsafe neighbour to borrow an older business.
    """
    if not isinstance(predecessor_unit_ids, tuple) or type(window_complete) is not bool:
        raise ValueError("actor context requires a source-owned tuple window")
    if type(max_units) is not int or not 1 <= max_units <= MAX_ACTOR_CONTEXT_UNITS:
        raise ValueError("actor max_units must tighten the source bound")
    if type(max_chars) is not int or not 1 <= max_chars <= MAX_ACTOR_CONTEXT_CHARS:
        raise ValueError("actor max_chars must tighten the source bound")
    if target_unit_id not in units:
        raise ValueError("actor target is not an observed unit")
    used_before = work_budget.used
    diagnostics: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    def result(status: str = "not_applicable", required: tuple[str, ...] = ()) -> dict[str, Any]:
        return {"schema_version": "du11-reference-closure/1", "unit_id": target_unit_id,
            "status": status, "reference_refs": references, "declaration_refs": [],
            "member_refs": [], "required_original_unit_ids": required,
            "attribution": "unknown", "reference_kind": "actor_context",
            "diagnostics": diagnostics, "work_used": work_budget.used - used_before}

    def diagnostic(code: str) -> None:
        diagnostics.append({"code": code, "unit_id": target_unit_id})

    try:
        work_budget.charge(1 + 2 * len(predecessor_unit_ids))
        if len(predecessor_unit_ids) > max_units:
            diagnostic("actor_window_bound")
            return result()
        if (len(set(predecessor_unit_ids)) != len(predecessor_unit_ids)
                or target_unit_id in predecessor_unit_ids
                or any(uid not in units for uid in predecessor_unit_ids)):
            raise ValueError("actor window contains invalid original IDs")
        target = units[target_unit_id]
        text = _text(target)
        if len(text) > max_chars:
            diagnostic("actor_context_envelope")
            return result()
        work_budget.charge(ACTOR_CONTEXT_SCAN_PASSES * len(text) + 1)
        if not _body(target, text):
            return result()
        matches = tuple(_FIRST_PERSON.finditer(text))
        if not matches:
            return result()
        references.extend({"unit_id": target_unit_id,
            "char_start": match.start(), "char_end": match.end()} for match in matches)
        diagnostic("actor_identity_not_inferred")
        if _LOCAL_FRAME.search(text):
            diagnostic("actor_explicit_local_frame")
            return result()
        # First person alone is not a cross-paragraph dependency. Requiring
        # arbitrary preceding prose would consume selection slots and could
        # displace an otherwise complete source fact. A real backward cue is
        # needed before making adjacent source context mandatory.
        if not _BACKREFERENCE.match(text):
            diagnostic('actor_no_explicit_backreference')
            return result()
        if not window_complete:
            diagnostic("actor_window_incomplete")
        if not predecessor_unit_ids:
            diagnostic("actor_no_adjacent_body")
            return result()
        previous_id = predecessor_unit_ids[-1]
        previous = units[previous_id]
        previous_text = _text(previous)
        if len(text) + len(previous_text) > max_chars:
            diagnostic("actor_context_envelope")
            return result()
        work_budget.charge(ACTOR_CONTEXT_SCAN_PASSES * len(previous_text) + 1)
        same_source = _source(target) is not None and _source(target) == _source(previous)
        same_scope = all(left is None or right is None or left == right
            for left, right in (
                *zip(_turn(target), _turn(previous)),
                (_scope(target, 'speaker_id'), _scope(previous, 'speaker_id')),
                (_scope(target, "section_id", "section_key"), _scope(previous, "section_id", "section_key")),
                (_scope(target, "order_window_id"), _scope(previous, "order_window_id"))))
        if not same_source or not same_scope or not _body(previous, previous_text):
            diagnostic("actor_adjacent_context_boundary")
            return result()
        diagnostic("actor_context_only")
        return result("unique", (previous_id,))
    except WorkBudgetExceeded:
        diagnostic("actor_work_budget_exhausted")
        return result("partial")
