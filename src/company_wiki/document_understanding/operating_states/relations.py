"""Bounded operating-relation extraction (DU4-STATE, source-oriented only).

``detect_operating_relations`` turns one observed unit into concrete
assertion relations: an operating predicate bound to its object and actor
within a bounded window, with polarity / stage / attribution / modality kept
separately. Matching runs on the converted reading view; every returned ref
is an exact slice of the untouched original unit text. Nothing here scores
investments, decides selection, changes source roles or invents subjects.

Conventions locked by the lane's test suite:

* ``assertion_refs`` — the clause span where the predicate binds (including
  any elided native line wrap inside the original span);
* ``actor_refs`` / ``object_refs`` — subject conjuncts and product/theme NPs;
* ``predicate_refs`` — the core predicate phrase; ``qualifier_refs`` — bound
  negation / aspect / modality / restriction markers;
* unknown actors/stages stay ``"unknown"`` — never "" or a completed state.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)

from . import patterns as p
from .text_view import MatchingView, build_matching_view, split_clauses, strip_connector

OBSERVATION_SCHEMA = "du4-operating-observation/1"
RELATIONS_SCHEMA = "du4-operating-relations/1"
_REQUIRED_UNIT_FIELDS = ("text", "parent_id", "role", "kind", "locator")

_ABSENCE_CONSTRUCTIONS = frozenset(
    {
        "production_negation",
        "production_suspend",
        "production_stop",
        "production_en",
        "production_en_suspend",
        "unsuccessful_validation",
        "qualification_pending",
        "qualification_pending_en",
        "scope_cn",
        "scope_en",
        "commercialization",
        "commercialization_en",
    }
)
_VERBAL_CONSTRUCTIONS = frozenset(
    {
        "production_stop",
        "production_en_suspend",
        "qualification_result",
        "scope_cn",
        "scope_en",
        "shipment",
        "shipment_en",
        "relation_contact",
        "relation_contact_en",
        "relation_sign",
        "relation_sign_en",
        "relation_intended",
        "relation_intended_en",
    }
)
_ACTIVITY_BY_CONSTRUCTION = {
    "production_negation": "production",
    "production_suspend": "production",
    "production_stop": "production",
    "production_aspect": "production",
    "production_en": "production",
    "production_en_suspend": "production",
    "commercialization": "commercialization",
    "commercialization_en": "commercialization",
    "commercial_plan_en": "commercialization",
    "qualification_pending": "qualification",
    "qualification_result": "qualification",
    "qualification_verb": "qualification",
    "qualification_en": "qualification",
    "qualification_pending_en": "qualification",
    "approval_restricted": "qualification",
    "unsuccessful_validation": "qualification",
    "shipment": "shipment",
    "shipment_en": "shipment",
    "scope_cn": "business_scope",
    "scope_en": "business_scope",
    "relation_contact": "business_relationship",
    "relation_contact_en": "business_relationship",
    "relation_sign": "business_relationship",
    "relation_sign_en": "business_relationship",
    "relation_intended": "business_relationship",
    "relation_intended_en": "business_relationship",
    "relation_plan": "business_relationship",
    "relation_plan_en": "business_relationship",
    "uncertain": "business_scope",
    "double_negation": "production",
}
_NOT_YET = re.compile(
    r"尚未|还未|暂未|仍未|not\s+yet|remains?\s+pending|remain\s+pending|is\s+pending",
    re.IGNORECASE,
)
_NEGATIVE_QUAL = re.compile(
    r"无|無|不|未|没|沒|非|暂停|中止|停产|停止|终止|失败|未通过|"
    r"never|no\s+longer|not|suspend|halt|ceas|stop|fail|unsuccessful",
    re.IGNORECASE,
)
_OBJ_TRIM = re.compile(r"^(?:关于|關於|就|对于|對於|about|on|for|regarding|re)\s*")


@dataclass
class _Event:
    construction: str
    start: int
    end: int
    pred_span: tuple[int, int]
    qual_spans: list[tuple[int, int]] = field(default_factory=list)
    obj_spans: list[tuple[int, int]] = field(default_factory=list)
    actor_spans: list[tuple[int, int]] = field(default_factory=list)
    actor_hint: tuple[int, int] | None = None
    attribution: str = "unknown"
    activity: str = "other_operating"
    polarity: str = "positive"
    stage: str = "unknown"
    modality: str = "actual"


@dataclass
class _UnitScan:
    view: MatchingView
    name_classes: dict[str, str]
    last_topic: tuple[int, int] | None = None
    last_actors: list[tuple[int, int]] = field(default_factory=list)


# ---------------------------------------------------------------- validation


def _validate(observation: Mapping[str, Any]) -> tuple[str, dict[str, Mapping[str, Any]], list[str], str | None]:
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    if observation.get("schema_version") != OBSERVATION_SCHEMA:
        raise ValueError("unexpected observation schema_version")
    target = observation.get("unit_id")
    if not isinstance(target, str) or not target:
        raise ValueError("unit_id must be a non-empty string")
    units = observation.get("units")
    if not isinstance(units, Mapping):
        raise ValueError("units must be a mapping of unit_id to unit")
    if target not in units:
        raise ValueError("unit_id is not present in units")
    for unit_id, unit in units.items():
        if not isinstance(unit_id, str) or not isinstance(unit, Mapping):
            raise ValueError("malformed units entry")
        for key in _REQUIRED_UNIT_FIELDS:
            if key not in unit:
                raise ValueError(f"unit is missing {key}")
        if not isinstance(unit["text"], str):
            raise ValueError("unit text must be a string")
    context_ids_raw = observation.get("context_unit_ids")
    if context_ids_raw is None:
        context_ids: list[str] = []
    elif isinstance(context_ids_raw, Sequence) and not isinstance(context_ids_raw, (str, bytes)):
        context_ids = list(context_ids_raw)
        if any(not isinstance(item, str) for item in context_ids):
            raise ValueError("context_unit_ids must be strings")
        if len(set(context_ids)) != len(context_ids):
            raise ValueError("duplicate context_unit_ids")
    else:
        raise ValueError("context_unit_ids must be a sequence of strings")
    language = observation.get("language")
    if language is not None and not isinstance(language, str):
        raise ValueError("language must be a string when present")
    return target, dict(units), context_ids, language


# ---------------------------------------------------------------- name classes


def _scan_name_classes(view: MatchingView) -> dict[str, str]:
    classes: dict[str, str] = {}
    for regex, label in ((p.CUE_RELATED, "quoted_related_party"), (p.CUE_THIRD, "other")):
        for match in regex.finditer(view.text):
            name = match.group("name").strip()
            if name:
                classes.setdefault(name, label)
    return classes


# ---------------------------------------------------------------- clause guards


def _clause_guarded(clause_text: str, closing: str) -> str | None:
    if closing in ("？", "?") or p.INTERROGATIVE_MARKER.search(clause_text):
        return "interrogative"
    if p.INTERROGATIVE_PREFIX.match(clause_text):
        return "interrogative"
    for regex, name in (
        (p.DEFINITION, "definition"),
        (p.ADMIN_RECEIPT, "administrative_receipt"),
        (p.VISION, "vision"),
        (p.GENERIC_WISH, "generic_wish"),
        (p.FINANCIAL_COMPOSITION, "financial_composition"),
    ):
        if regex.search(clause_text):
            return name
    return None


# ---------------------------------------------------------------- subject/object


def _tail_np(text: str) -> str:
    """Keep the trailing noun phrase after causal/relay material."""
    best = text
    for marker in ("因", "由于", "因为", "根据", "基于", "通过", "，", "。", "、", "；", "的"):
        index = best.rfind(marker)
        if index >= 0:
            best = best[index + len(marker):]
    for marker in (" after ", " because ", " due to ", " following ", " given "):
        index = best.rfind(marker)
        if index >= 0:
            best = best[index + len(marker):]
    return best.strip()


def _obj_after(text: str) -> str:
    """Object noun phrase after a predicate: cut at the first particle/boundary."""
    for index, character in enumerate(text):
        if character in "的等，。、；;：:":
            return text[:index]
    return text


def _clean_np(text: str) -> str:
    text = _OBJ_TRIM.sub("", text.strip())
    return text.strip(" .，,、；;：:")


def _np_candidates(view: MatchingView, region: str, base: int) -> list[tuple[int, int]]:
    """Leading noun-phrase span(s) of a subject region (prefix offsets exact)."""
    leading = len(region) - len(region.lstrip())
    core = region.strip()
    if not core:
        return []
    trimmed = _OBJ_TRIM.match(core)
    if trimmed is not None:
        leading += trimmed.end()
        core = core[trimmed.end():]
    cut = None
    for regex in (p.ACTOR_CUT, p.EN_AUX_BOUNDARY, p.CN_TOPIC_BOUNDARY):
        match = regex.search(core)
        if match is not None:
            cut = match.start() if cut is None else min(cut, match.start())
    if cut is not None:
        if cut == 0:
            return []
        core = core[:cut]
    if len(core) > 24:
        match = p.EN_AUX_BOUNDARY.search(core)
        if match is not None and match.start() > 0:
            core = core[:match.start()]
    tail = p.SUBJECT_TAIL.search(core)
    if tail is not None:
        core = core[:tail.start()]
    core = core.strip()
    if not core:
        return []
    start = base + leading
    return [(start, start + len(core))]


def _split_conjuncts(view: MatchingView, span: tuple[int, int]) -> list[tuple[int, int]]:
    text = view.text[span[0]:span[1]]
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in p.CONJUNCT_SPLIT.finditer(text):
        if match.start() > cursor:
            spans.append((span[0] + cursor, span[0] + match.start()))
        cursor = match.end()
    if cursor < len(text):
        spans.append((span[0] + cursor, span[1]))
    cleaned: list[tuple[int, int]] = []
    for start, end in spans:
        piece = view.text[start:end]
        for marker in ("就", "关于", "關於", "对于", "對於"):
            index = piece.find(marker)
            if index > 0:
                piece = piece[:index]
                break
        piece = piece.strip()
        if piece:
            offset = view.text[start:end].index(piece)
            cleaned.append((start + offset, start + offset + len(piece)))
    return cleaned


def _classify_np(view: MatchingView, span: tuple[int, int],
                 name_classes: Mapping[str, str]) -> tuple[str, str]:
    """Return (role, attribution class) for one NP span."""
    text = view.text[span[0]:span[1]].strip()
    if not text:
        return "none", "unknown"
    if p.PRODUCT_SUFFIX.search(text):
        return "object", "unknown"
    if p.RELATED_PARTY.search(text):
        return "actor", "quoted_related_party"
    if p.THIRD_PARTY.search(text):
        return "actor", "other"
    if p.ISSUER_WORD.search(text):
        return "actor", "issuer"
    if text in name_classes:
        return "actor", name_classes[text]
    return "actor", "unknown"


# ---------------------------------------------------------------- event binding


def _bind_event(view: MatchingView, scan: _UnitScan, clause: tuple[int, int],
                event: _Event, previous_end: int | None) -> None:
    lower = clause[0] if previous_end is None else max(clause[0], previous_end)
    region = view.text[lower:event.start]
    stripped = region.strip()
    if stripped:
        rest, removed = strip_connector(stripped)
        region = rest if removed else stripped
    else:
        region = ""
    spans: list[tuple[int, int]] = []
    if event.actor_hint is not None:
        hint_text = view.text[event.actor_hint[0]:event.actor_hint[1]]
        spans.extend(_np_candidates(view, hint_text, event.actor_hint[0]))
    spans.extend(_np_candidates(view, region, lower))
    expanded: list[tuple[int, int]] = []
    for span in spans:
        expanded.extend(_split_conjuncts(view, span))
    spans = expanded
    actor_spans: list[tuple[int, int]] = []
    obj_spans: list[tuple[int, int]] = []
    attribution = "unknown"
    for span in spans:
        role, actor_class = _classify_np(view, span, scan.name_classes)
        if role == "object":
            obj_spans.append(span)
        elif role == "actor":
            actor_spans.append(span)
            if attribution == "unknown" and actor_class != "unknown":
                attribution = actor_class
    if not actor_spans:
        inherited = list(scan.last_actors) or (
            [scan.last_topic] if scan.last_topic is not None else []
        )
        for span in inherited:
            role, actor_class = _classify_np(view, span, scan.name_classes)
            if role == "actor":
                actor_spans.append(span)
                if attribution == "unknown" and actor_class != "unknown":
                    attribution = actor_class
            elif role == "object" and not obj_spans:
                obj_spans.append(span)
    event.actor_spans = actor_spans
    event.obj_spans = list(dict.fromkeys([*obj_spans, *event.obj_spans]))
    event.attribution = attribution
    if actor_spans:
        scan.last_actors = actor_spans


def _resolve_fields(construction: str, qual_text: str, has_condition: bool,
                    has_future: bool, has_restriction: bool) -> tuple[str, str, str]:
    """Return (polarity, stage, modality) for one bound event."""
    if construction in ("uncertain", "double_negation"):
        return "unknown", "unknown", "uncertain"
    negative = bool(_NEGATIVE_QUAL.search(qual_text)) or construction in (
        "production_suspend", "production_stop", "production_en_suspend",
    )
    polarity = "negative" if negative else "positive"
    if construction.startswith("relation_contact"):
        stage, modality = "contact_established", "actual"
    elif construction.startswith("relation_intended"):
        stage, modality = "intended_cooperation", "aspirational"
    elif has_restriction or construction == "approval_restricted":
        stage, modality = "conditional", "conditional"
    elif has_condition:
        stage, modality = "conditional", "conditional"
    elif construction == "production_suspend" or "suspend" in qual_text or "暂停" in qual_text or "中止" in qual_text:
        stage, modality = "suspended", "actual"
    elif construction == "production_stop" or "停产" in qual_text or "停止" in qual_text or "终止" in qual_text:
        stage, modality = "discontinued", "actual"
    elif _NOT_YET.search(qual_text):
        stage, modality = "not_yet", "actual"
    elif construction.startswith("relation_plan") or construction == "commercial_plan_en" or has_future:
        stage, modality = "planned", "planned"
    elif qual_text and _NEGATIVE_QUAL.search(qual_text):
        stage, modality = "current", "actual"
    elif "现" in qual_text or "目前" in qual_text or "当前" in qual_text:
        stage, modality = "current", "actual"
    elif construction in _ABSENCE_CONSTRUCTIONS:
        stage, modality = "current", "actual"
    elif qual_text or construction in ("relation_sign", "relation_sign_en"):
        stage, modality = "current", "actual"
    else:
        stage, modality = "unknown", "actual"
    return polarity, stage, modality


def _clause_events(view: MatchingView, scan: _UnitScan,
                   clause: tuple[int, int], clause_text: str) -> list[_Event]:
    candidates: list[tuple[int, int, int, re.Match[str]]] = []
    for order, (construction, regex) in enumerate(p.EVENT_PATTERNS):
        for match in regex.finditer(clause_text):
            start = clause[0] + match.start()
            end = clause[0] + match.end()
            if end > start:
                candidates.append((start, end, order, match))
    candidates.sort(key=lambda item: (item[0], item[2]))
    taken: list[tuple[int, int]] = []
    events: list[_Event] = []
    for start, end, order, match in candidates:
        if any(start < other_end and other_start < end for other_start, other_end in taken):
            continue
        construction = p.EVENT_PATTERNS[order][0]
        groups = match.groupdict()
        pred = groups.get("pred")
        if not pred:
            continue
        qual_text = " ".join(
            groups.get(key) or ""
            for key in ("qual", "qual2", "restriction", "state")
        ).strip()
        verbal = construction in _VERBAL_CONSTRUCTIONS
        has_marker = any(
            groups.get(key) for key in ("qual", "qual2", "restriction", "state", "obj_lead", "partner")
        )
        if not (has_marker or verbal):
            # Bare noun compounds ("product qualification and commercialization")
            # are list members, never assertions: a bound qualifier or a verbal
            # predicate construction is required.
            continue
        taken.append((start, end))
        pred_start = clause[0] + match.start("pred")
        pred_end = pred_start + len(pred)
        event = _Event(construction, start, end, (pred_start, pred_end))
        for key in ("qual", "qual2", "restriction", "state"):
            group = groups.get(key)
            if group:
                group_start = clause[0] + match.start(key)
                event.qual_spans.append((group_start, group_start + len(group)))
        obj_group = groups.get("obj")
        if obj_group:
            raw_start = clause[0] + match.start("obj")
            raw = obj_group
            if match.start("obj") < match.start("pred"):
                trimmed = _tail_np(_clean_np(raw))
            else:
                trimmed = _clean_np(_obj_after(raw))
            if trimmed:
                lead = raw.find(trimmed[:2]) if len(trimmed) >= 2 else -1
                obj_start = raw_start + (lead if lead >= 0 else 0)
                event.obj_spans.append((obj_start, obj_start + len(trimmed)))
                if obj_start > raw_start and obj_start <= start:
                    # Object sat before the predicate ("…滤芯产线停产"); the
                    # discarded prefix is the subject candidate ("公司因").
                    event.actor_hint = (raw_start, obj_start)
        partner = groups.get("partner")
        if partner:
            partner_start = clause[0] + match.start("partner")
            event.actor_spans.append((partner_start, partner_start + len(partner)))
        activity = _ACTIVITY_BY_CONSTRUCTION.get(construction, "other_operating")
        if construction in ("uncertain", "double_negation"):
            lowered = pred.lower()
            if "生产" in pred or "制造" in pred or "produc" in lowered or "manufactur" in lowered:
                activity = "production"
            elif "商业化" in pred or "commercial" in lowered:
                activity = "commercialization"
            elif "涉及" in pred or "参与" in pred or "involved" in lowered:
                activity = "business_scope"
        event.activity = activity
        has_condition = bool(p.CONDITIONAL.search(clause_text))
        has_future = bool(p.FUTURE_TIME.search(clause_text))
        polarity, stage, modality = _resolve_fields(
            construction, qual_text, has_condition, has_future,
            bool(groups.get("restriction")),
        )
        if construction == "qualification_result":
            if _NEGATIVE_QUAL.search(qual_text or ""):
                polarity, stage = "negative", "unknown"
            else:
                polarity, stage = "positive", "current"
        event.polarity, event.stage, event.modality = polarity, stage, modality
        _bind_event(view, scan, clause, event, events[-1].end if events else None)
        if any(
            p.ABSTRACT_OBJECT.fullmatch(view.text[span[0]:span[1]].strip())
            for span in event.obj_spans
        ):
            continue  # risk/issue language is not an operating assertion
        events.append(event)
    return events


# ---------------------------------------------------------------- assembly


def _to_ref(unit_id: str, view: MatchingView, span: tuple[int, int]) -> dict[str, Any]:
    start, end = view.to_original(span[0], span[1])
    return {"unit_id": unit_id, "char_start": start, "char_end": end}


def _relation_dict(unit_id: str, view: MatchingView, clause: tuple[int, int],
                   event: _Event, extra_quals: list[tuple[int, int]]) -> dict[str, Any]:
    return {
        "assertion_refs": [_to_ref(unit_id, view, clause)],
        "actor_refs": [_to_ref(unit_id, view, span) for span in event.actor_spans],
        "object_refs": [_to_ref(unit_id, view, span) for span in event.obj_spans],
        "predicate_refs": [_to_ref(unit_id, view, event.pred_span)],
        "qualifier_refs": [
            _to_ref(unit_id, view, span) for span in (*event.qual_spans, *extra_quals)
        ],
        "activity": event.activity,
        "polarity": event.polarity,
        "stage": event.stage,
        "attribution": event.attribution,
        "modality": event.modality,
    }


def detect_operating_relations(
    observation: Mapping[str, Any], *, work_budget: WorkBudget
) -> dict[str, Any]:
    """Extract bounded operating relations from one observed unit.

    Structural errors raise ``ValueError``; work-budget exhaustion keeps the
    relations already determined and reports ``status="partial"``. Missing or
    empty source text reports ``"unavailable"`` for the affected item without
    rejecting the rest of the document.
    """
    target, units, context_ids, _language = _validate(observation)
    used_before = work_budget.used
    relations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    exhausted = False
    contexts_used: list[str] = []

    try:
        target_view = build_matching_view(units[target]["text"])
        work_budget.charge(1)
        name_classes = _scan_name_classes(target_view)
        work_budget.charge(1)
        target_parent = units[target]["parent_id"]
        for context_id in context_ids:
            work_budget.charge(1)
            if context_id not in units:
                diagnostics.append({"code": "context_unit_missing", "unit_id": context_id})
                continue
            if units[context_id]["parent_id"] != target_parent:
                diagnostics.append({"code": "context_parent_mismatch", "unit_id": context_id})
                continue
            context_view = build_matching_view(units[context_id]["text"])
            for name, label in _scan_name_classes(context_view).items():
                name_classes.setdefault(name, label)
            contexts_used.append(context_id)

        if not target_view.text.strip():
            diagnostics.append({"code": "unit_text_unavailable", "unit_id": target})
            return {
                "schema_version": RELATIONS_SCHEMA,
                "unit_id": target,
                "relations": [],
                "diagnostics": diagnostics,
                "status": "unavailable",
                "work_used": work_budget.used - used_before,
            }

        scan = _UnitScan(target_view, name_classes)
        clauses = split_clauses(target_view)
        for clause in clauses:
            work_budget.charge(1)
            clause_text = target_view.text[clause[0]:clause[1]]
            closing = target_view.text[clause[1]:clause[1] + 1]
            if _clause_guarded(clause_text, closing):
                continue
            if p.RESTRICTION_CONTINUATION.match(clause_text) and relations:
                span = (clause[0], clause[1])
                relations[-1]["qualifier_refs"].append(_to_ref(target, target_view, span))
                continue
            events = _clause_events(target_view, scan, clause, clause_text)
            if not events:
                stripped = clause_text.strip()
                if stripped:
                    topic = _np_candidates(target_view, stripped, clause[0])
                    if topic:
                        scan.last_topic = topic[0]
                continue
            for event in events:
                work_budget.charge(1)
                # Assemble immediately: budget exhaustion keeps the relations
                # already determined instead of dropping unconverted events.
                relations.append(_relation_dict(target, target_view, clause, event, []))
    except WorkBudgetExceeded:
        exhausted = True

    relations.sort(
        key=lambda item: (
            item["assertion_refs"][0]["char_start"],
            item["predicate_refs"][0]["char_start"],
        )
    )

    status = "partial" if exhausted or diagnostics else "complete"
    if exhausted:
        diagnostics.append({"code": "work_budget_exhausted", "unit_id": target})
    return {
        "schema_version": RELATIONS_SCHEMA,
        "unit_id": target,
        "relations": relations,
        "diagnostics": diagnostics,
        "status": status,
        "work_used": work_budget.used - used_before,
    }
