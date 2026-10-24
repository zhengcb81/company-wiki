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
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)

from . import patterns as p
from .product_reference import (find_product_deictic, head_class,
                                is_generic_reference, product_head_suffix, scan_product_declarations)
from .text_view import (MatchingText, MatchingView, build_matching_view,
                        build_prepared_matching_view, prepare_matching_text,
                        split_clauses, strip_connector)

OBSERVATION_SCHEMA = "du4-operating-observation/1"
RELATIONS_SCHEMA = "du4-operating-relations/1"
REFERENCE_SCHEMA = "du11-reference-closure/1"
_QUESTION_ROLES = frozenset({"investor_question", "analyst_question", "question",
                             "operator_question", "qa_question"})
_NON_DONATING_KINDS = frozenset({"heading", "table_row", "table_header", "table_caption",
                                 "question", "footer", "header"})
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
    "production_stop_action": "production",
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
    r"尚未|还未|暂未|仍未|仍需|尚需|还需|有待|尚待|not\s+yet|remains?\s+pending|remain\s+pending|is\s+pending",
    re.IGNORECASE,
)
_NEGATIVE_QUAL = re.compile(
    r"无|無|不|未|没|沒|非|暂停|中止|停产|停止|终止|失败|未通过|"
    r"never|no\s+longer|not|suspend|halt|ceas|stop|fail|unsuccessful",
    re.IGNORECASE,
)
_OBJ_TRIM = re.compile(r"^(?:关于|關於|就|对于|對於|about|on|for|regarding|re)\s*")
_STATEMENT_LEAD = re.compile(r"^\s*(?:(?:报告期内|本期|目前|同时|此外)[，,\s]*)?")
_NONPREDICATE_BOUNDARIES = frozenset({"and", "but", "or", "yet", "so", "then", "also",
                                        "still", "just", "not", "never"})


def _subject_predicate_boundary(text: str, start: int = 0) -> re.Match[str] | None:
    """First real predicate boundary; conjunctions do not erase subject NPs."""
    return next((match for match in p.EN_AUX_BOUNDARY.finditer(text, start)
                 if match.group().casefold() not in _NONPREDICATE_BOUNDARIES), None)


def independent_statement_start(text: str) -> bool:
    """Conservative source boundary using the existing script and NP grammar.

    A possessive NP alone (``our customers`` after ``deliver to``) supplies no
    independent assertion. A product NP followed by an observed auxiliary or
    predicate is a fresh clause. This decides a boundary, never event truth.
    """
    prepared = _STATEMENT_LEAD.sub("", prepare_matching_text(text).text, count=1)
    issuer = p.ISSUER_WORD.match(prepared)
    if issuer is None:
        return False
    if issuer.group().casefold() != "our":
        return True
    boundary = _subject_predicate_boundary(prepared, issuer.end())
    if boundary is None:
        return False
    subject = prepared[issuer.end():boundary.start()].strip()
    if re.search(r"[,;.!?]", subject):
        return False
    # A later predicate belongs to the predicate/object region, not to a
    # successively longer subject. Decide once at the first real boundary.
    return product_head_suffix(subject) is not None


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
    embedded_actor: tuple[int, int] | None = None


@dataclass
class _UnitScan:
    view: MatchingView
    name_classes: dict[str, str]
    last_topic: tuple[int, int] | None = None
    last_actors: list[tuple[int, int]] = field(default_factory=list)


# ---------------------------------------------------------------- validation


def _validate(observation: Mapping[str, Any]) -> tuple[str, Mapping[str, Any], Sequence, str | None]:
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
    context_ids_raw = observation.get("context_unit_ids")
    context_ids: Sequence
    if context_ids_raw is None:
        context_ids = []
    elif isinstance(context_ids_raw, Sequence) and not isinstance(context_ids_raw, (str, bytes)):
        context_ids = context_ids_raw
    else:
        raise ValueError("context_unit_ids must be a sequence of strings")
    language = observation.get("language")
    if language is not None and not isinstance(language, str):
        raise ValueError("language must be a string when present")
    return target, units, context_ids, language


def _unit(units, key, budget):
    budget.charge(1)
    value = units[key]
    if not isinstance(value, Mapping):
        raise ValueError("malformed units entry")
    for field_name in _REQUIRED_UNIT_FIELDS:
        if field_name not in value:
            raise ValueError(f"unit is missing {field_name}")
    if not isinstance(value['text'], str):
        raise ValueError("unit text must be a string")
    return value


def _view_and_names(unit, budget, text: MatchingText | None = None):
    # Reserve character work before constructing the offset map or scanning
    # names. Unreferenced units and arbitrary metadata are never copied.
    budget.charge(len(unit['text']))
    view = build_matching_view(unit['text']) if text is None else build_prepared_matching_view(text)
    budget.charge(2 * len(view.text))
    return view, _scan_name_classes(view)


def _predicate_expression(pattern: str, group: str) -> str | None:
    """Read an existing named predicate, without inventing a second lexicon."""
    marker = "(?P<" + group + ">"
    if pattern.count(marker) != 1 or "[]" in pattern or "[[" in pattern:
        return None
    start = pattern.find(marker)
    if start < 0:
        return None
    start += len(marker)
    depth, escaped, char_class = 1, False, False
    for index in range(start, len(pattern)):
        char = pattern[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "[" and not char_class:
            char_class = True
        elif char == "]" and char_class:
            char_class = False
        elif not char_class:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return pattern[start:index]
    return None


@lru_cache(maxsize=1)
def _predicate_gate(entries):
    """A conservative necessary condition derived from the actual grammar.

    Every emitted relation must capture its predicate. Removing its surrounding
    assertion grammar only widens matching. Context-sensitive captures, external
    backrefs or future unsupported flags disable this optimization entirely;
    they never become absence. The original rules still decide all semantics.
    """
    expressions = []
    for construction, regex in entries:
        if regex.flags & ~(re.I | re.U) or re.search(r"\(\?[aiLmsux-]", regex.pattern):
            return None
        group = "qual" if construction == "shipment_en" and "pred" not in regex.groupindex else "pred"
        expression = _predicate_expression(regex.pattern, group)
        if expression is None or any(token in expression for token in
                ("(?=", "(?!", "(?<", "(?P", "^", "$", "\\A", "\\Z", "\\z")):
            return None
        if re.search(r"\(\?(?!:)", expression):
            return None
        if re.search(r"\\[1-9]", expression):
            return None
        expressions.append("(?i:" + expression + ")" if regex.flags & re.I else "(?:" + expression + ")")
    try:
        return re.compile("|".join(dict.fromkeys(expressions)))
    except re.error:
        return None


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
    if p.CONDITION_ONLY.fullmatch(core):
        return []
    trimmed = _OBJ_TRIM.match(core)
    if trimmed is not None:
        leading += trimmed.end()
        core = core[trimmed.end():]
    cut = None
    for regex in (p.ACTOR_CUT, p.EN_AUX_BOUNDARY, p.CN_TOPIC_BOUNDARY):
        match = (_subject_predicate_boundary(core) if regex is p.EN_AUX_BOUNDARY
                 else regex.search(core))
        if match is not None:
            cut = match.start() if cut is None else min(cut, match.start())
    if cut is not None:
        if cut == 0:
            return []
        core = core[:cut]
    if len(core) > 24:
        match = _subject_predicate_boundary(core)
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
    product = product_head_suffix(text)
    if product:
        prefix = text[:product[0]]
        for marker, attribution in ((p.THIRD_PARTY, "other"), (p.RELATED_PARTY, "quoted_related_party")):
            party = marker.search(prefix)
            if party and p.POSSESSIVE_LINK.match(prefix[party.end():]):
                return "object", attribution
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
    leading = len(region) - len(region.lstrip())
    stripped = region.strip()
    lower += leading
    if stripped:
        rest, removed = strip_connector(stripped)
        region = rest if removed else stripped
        lower += removed
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
            if attribution == "unknown" and actor_class != "unknown":
                attribution = actor_class
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
    # An elided continuation may inherit the already bound object, separately
    # from its issuer actor. A new explicit subject blocks that inheritance.
    if not spans and not obj_spans and scan.last_topic is not None:
        role, _actor = _classify_np(view, scan.last_topic, scan.name_classes)
        if role == "object":
            obj_spans.append(scan.last_topic)
    event.actor_spans = actor_spans
    event.obj_spans = list(dict.fromkeys([*obj_spans, *event.obj_spans]))
    event.attribution = attribution
    if event.obj_spans:
        scan.last_topic = event.obj_spans[0]
    elif spans:
        scan.last_topic = None
    if actor_spans:
        scan.last_actors = actor_spans


def _resolve_fields(construction: str, qual_text: str, has_condition: bool,
                    has_future: bool, has_restriction: bool) -> tuple[str, str, str]:
    """Return (polarity, stage, modality) for one bound event."""
    if (construction in ("uncertain", "double_negation")
            or len(list(p.NEGATION_TOKENS.finditer(qual_text))) > 1):
        return "unknown", "unknown", "uncertain"
    negative = bool(_NEGATIVE_QUAL.search(qual_text)) or construction in (
        "production_suspend", "production_stop", "production_stop_action", "production_en_suspend",
    )
    polarity = "negative" if negative else "positive"
    if construction.startswith("relation_intended") or p.ASPIRATIONAL_QUAL.search(qual_text):
        stage, modality = "intended_cooperation", "aspirational"
    elif has_restriction or construction == "approval_restricted":
        stage, modality = "conditional", "conditional"
    elif has_condition or p.HYPOTHETICAL_QUAL.search(qual_text):
        stage, modality = "conditional", "conditional"
    elif (construction.startswith("relation_plan") or construction == "commercial_plan_en"
          or p.PLANNED_QUAL.search(qual_text) or has_future):
        stage, modality = "planned", "planned"
    elif construction == "production_suspend" or "suspend" in qual_text or "暂停" in qual_text or "中止" in qual_text:
        stage, modality = "suspended", "actual"
    elif construction == "production_stop" or "停产" in qual_text or "停止" in qual_text or "终止" in qual_text:
        stage, modality = "discontinued", "actual"
    elif _NOT_YET.search(qual_text):
        stage, modality = "not_yet", "actual"
    elif qual_text and _NEGATIVE_QUAL.search(qual_text):
        stage, modality = "current", "actual"
    elif construction.startswith("relation_contact"):
        stage, modality = "contact_established", "actual"
    elif "现" in qual_text or "目前" in qual_text or "当前" in qual_text:
        stage, modality = "current", "actual"
    elif construction in _ABSENCE_CONSTRUCTIONS:
        stage, modality = "current", "actual"
    elif qual_text or construction in ("relation_sign", "relation_sign_en"):
        stage, modality = "current", "actual"
    else:
        stage, modality = "unknown", "actual"
    return polarity, stage, modality


def _predicate_modifiers(view, clause, pred_start, previous_main_end, embedded_ranges, budget):
    """Read one bounded assertion scope, with conservative bridge handling."""
    lower = max(clause[0], previous_main_end if previous_main_end is not None else clause[0], pred_start-64)
    prefix = view.text[lower:pred_start]
    budget.charge(len(prefix))
    breaks = list(p.MODIFIER_SCOPE_BREAK.finditer(prefix))
    if breaks:
        lower += breaks[-1].end()
        prefix = view.text[lower:pred_start]
    # Both marker positions and prior embedded ranges are ordered. One sweep
    # avoids rewalking every previous event for each later assertion.
    ranges = iter(embedded_ranges)
    active = next(ranges, None)
    markers = []
    for marker in p.MODIFIER_TOKENS.finditer(prefix):
        budget.charge(1)
        position = lower+marker.start()
        while active is not None and active[1] <= position:
            budget.charge(1)
            active = next(ranges, None)
        if active is None or position < active[0]:
            markers.append(marker)
    selected: list[re.Match[str]] = []
    right = len(prefix)
    unresolved = False
    for marker in reversed(markers):
        gap = prefix[marker.end():right]
        if not p.MODIFIER_BRIDGE.fullmatch(gap):
            # A discovered nonlocal operator cannot prove a completed event.
            # Do not guess across an unparsed argument or another assertion.
            if not selected:
                unresolved = True
                selected.append(marker)
            break
        selected.append(marker)
        right = marker.start()
    if not selected:
        return '', None, unresolved
    left = min(m.start() for m in selected)
    end = max(m.end() for m in selected)
    return prefix[left:end], (lower+left,lower+end), unresolved


def _clause_events(view: MatchingView, scan: _UnitScan,
                   clause: tuple[int, int], clause_text: str, budget: WorkBudget) -> list[_Event]:
    candidates: list[tuple[int, int, int, re.Match[str]]] = []
    for order, (construction, regex) in enumerate(p.EVENT_PATTERNS):
        budget.charge(len(clause_text))
        for match in regex.finditer(clause_text):
            budget.charge(1)
            start = clause[0] + match.start()
            end = clause[0] + match.end()
            if end > start:
                candidates.append((start, end, order, match))
    budget.charge(len(candidates) * max(1, len(candidates).bit_length()))
    candidates.sort(key=lambda item: (item[0], item[2]))
    taken_end = -1
    events: list[_Event] = []
    last_main_end = None
    embedded_ranges: deque[tuple[int, int]] = deque()
    for start, end, order, match in candidates:
        budget.charge(1)
        if start < taken_end:
            continue
        construction = p.EVENT_PATTERNS[order][0]
        groups = match.groupdict()
        # The existing English shipment grammar binds its verbal phrase in
        # ``qual`` (shipped / delivered / suspend shipments). It is both an
        # aspect/state cue and the actual source predicate, not a noun list.
        pred_key = "qual" if construction == "shipment_en" and not groups.get("pred") else "pred"
        pred = groups.get(pred_key)
        if not pred:
            continue
        pred_start = clause[0] + match.start(pred_key)
        # Bind a contiguous modifier suffix to every predicate family. Missing
        # optional regex groups cannot turn a denial or plan into completion.
        while embedded_ranges and embedded_ranges[0][1] <= pred_start-64:
            budget.charge(1)
            embedded_ranges.popleft()
        extra_qual, modifier_span, unresolved = _predicate_modifiers(
            view, clause, pred_start, last_main_end, embedded_ranges, budget)
        # A family grammar can explicitly bind its own object between modifier
        # and predicate (e.g. pending customer qualification). Keep that proof;
        # generic conservative fallback only covers otherwise unbound scope.
        if groups.get('qual') or groups.get('qual2'):
            unresolved = False
        qual_text = " ".join(
            groups.get(key) or ""
            for key in ("qual", "qual2", "restriction", "state")
        ).strip()
        if extra_qual:
            # The generic scope supersedes narrower family capture. Repeating
            # the same 'not' twice would invent a double negation.
            qual_text = extra_qual + ' ' + (groups.get('restriction') or '') + ' ' + (groups.get('state') or '')
        verbal = construction in _VERBAL_CONSTRUCTIONS
        has_marker = bool(extra_qual) or any(
            groups.get(key) for key in ("qual", "qual2", "restriction", "state", "obj_lead", "partner")
        )
        if not (has_marker or verbal):
            # Bare noun compounds ("product qualification and commercialization")
            # are list members, never assertions: a bound qualifier or a verbal
            # predicate construction is required.
            continue
        taken_end = end
        if modifier_span:
            start = min(start, modifier_span[0])
        pred_end = pred_start + len(pred)
        event = _Event(construction, start, end, (pred_start, pred_end))
        if modifier_span:
            event.qual_spans.append(modifier_span)
        for key in ("qual", "qual2", "restriction", "state"):
            group = groups.get(key)
            if group:
                group_start = clause[0] + match.start(key)
                group_end = group_start+len(group)
                if not modifier_span or not (modifier_span[0] <= group_start and group_end <= modifier_span[1]):
                    event.qual_spans.append((group_start, group_end))
        event.qual_spans = list(dict.fromkeys(event.qual_spans))
        obj_group = groups.get("obj")
        if obj_group:
            raw_start = clause[0] + match.start("obj")
            raw = obj_group
            if match.start("obj") < match.start(pred_key):
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
        if unresolved:
            polarity, stage, modality = 'unknown', 'unknown', 'uncertain'
        if construction == "qualification_result" and modality == 'actual':
            if _NEGATIVE_QUAL.search(qual_text or ""):
                polarity, stage = "negative", "unknown"
            else:
                polarity, stage = "positive", "current"
        event.polarity, event.stage, event.modality = polarity, stage, modality
        # A nominal relative clause modifies its actual party, not the main
        # clause's issuer. It must not replace the main assertion's actor or
        # donate its negation to a following contract/shipment predicate.
        relative = p.ATTRIBUTIVE_PARTY.match(view.text[event.end:min(clause[1],event.end+24)])
        if relative and activity == 'qualification':
            actor = (event.end+relative.start('actor'),event.end+relative.end('actor'))
            event.embedded_actor = actor
            event.actor_spans = [actor]
            _role, event.attribution = _classify_np(view, actor, scan.name_classes)
            event.end = actor[1]
            embedded_ranges.append((event.start,event.end))
        else:
            _bind_event(view, scan, clause, event, last_main_end)
            last_main_end = event.end
        if any(
            p.ABSTRACT_OBJECT.fullmatch(view.text[span[0]:span[1]].strip())
            for span in event.obj_spans
        ):
            continue  # risk/issue language is not an operating assertion
        # A predicate embedded in a nominalised/reported proposition is not
        # an asserted operating state. Keep exact source refs and honest unknown
        # fields, rather than inverting its internal negation into event truth.
        tail = view.text[pred_end:clause[1]]
        budget.charge(len(tail))
        reported = p.REPORTED_PROPOSITION_TAIL.search(tail)
        if reported is not None:
            event.polarity = event.stage = "unknown"
            event.modality = "uncertain"
            event.qual_spans.append((pred_end + reported.start(), pred_end + reported.end()))
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


class OperatingRelationSession:
    """One immutable source map and one caller-owned work balance.

    Preparation is cached by source unit identity, never by text. Cached names
    are copied before context names are merged, so another scope cannot alter
    a later target's attribution. No unreferenced unit is read or copied.
    """

    def __init__(self, units: Mapping[str, Any], *, work_budget: WorkBudget):
        self.units = units
        self.work_budget = work_budget
        self._units: dict[str, Any] = {}
        self._texts: dict[str, MatchingText] = {}
        self._views: dict[str, tuple[MatchingView, dict[str, str]]] = {}
        self._results: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
        self._references: dict[tuple[str, tuple[str, ...], bool], dict[str, Any]] = {}

    def unit(self, uid: str):
        if uid not in self._units:
            self._units[uid] = _unit(self.units, uid, self.work_budget)
        return self._units[uid]

    def prepared(self, uid: str):
        if uid not in self._views:
            self._views[uid] = _view_and_names(self.unit(uid), self.work_budget, self.matching_text(uid))
        view, names = self._views[uid]
        return view, dict(names)

    def matching_text(self, uid: str):
        if uid not in self._texts:
            unit = self.unit(uid)
            self.work_budget.charge(len(unit["text"]))
            self._texts[uid] = prepare_matching_text(unit["text"])
        return self._texts[uid]

    def detect(self, unit_id: str, context_unit_ids: tuple[str, ...] = ()):
        key = (unit_id, context_unit_ids)
        if key not in self._results:
            self._results[key] = _detect_operating_relations({
                "schema_version": OBSERVATION_SCHEMA, "unit_id": unit_id,
                "units": self.units, "context_unit_ids": context_unit_ids,
            }, work_budget=self.work_budget, prepared=self)
        return self._results[key]

    def reference_closure(self, unit_id: str, predecessor_unit_ids: tuple[str, ...] = (), *,
                          window_complete: bool = True) -> dict[str, Any]:
        """Bounded product-reference closure over permitted source predecessors.

        Legacy detect() is unchanged. This additive operation also runs for
        descriptive material without an operating predicate: a product deictic
        needs one actual named declaration inside the permitted, source-ordered,
        same-parent predecessors. Two competing families stay ambiguous; a
        truncated or exhausted search is partial, never an inferred absence.
        """
        key = (unit_id, tuple(predecessor_unit_ids), bool(window_complete))
        if key not in self._references:
            self._references[key] = self._reference_closure(unit_id, key[1], key[2])
        return self._references[key]

    def _reference_closure(self, target: str, predecessors: tuple[str, ...],
                           window_complete: bool) -> dict[str, Any]:
        used_before = self.work_budget.used
        diagnostics: list[dict[str, Any]] = []

        def result(status: str, *, references=(), declarations=(), members=(),
                   required=(), attribution="issuer") -> dict[str, Any]:
            return {"schema_version": REFERENCE_SCHEMA, "unit_id": target,
                    "status": status, "reference_refs": list(references),
                    "declaration_refs": list(declarations), "member_refs": list(members),
                    "required_original_unit_ids": tuple(required),
                    "attribution": attribution, "diagnostics": diagnostics,
                    "work_used": self.work_budget.used - used_before}

        target_unit = self.unit(target)
        target_parent = target_unit["parent_id"]
        if not isinstance(predecessors, tuple):
            raise ValueError("predecessor_unit_ids must be a tuple of unit ids")
        if len(set(predecessors)) != len(predecessors):
            raise ValueError("duplicate predecessor_unit_ids")
        for predecessor in predecessors:
            if not isinstance(predecessor, str):
                raise ValueError("predecessor_unit_ids must be strings")
            if predecessor not in self._units and predecessor not in self.units:
                raise ValueError(f"unknown predecessor unit: {predecessor}")
            if self.unit(predecessor)["parent_id"] != target_parent:
                raise ValueError("predecessor parent mismatch")
        raw_target = target_unit["text"]
        deictics = find_product_deictic(raw_target)
        family_deictics = [item for item in deictics
                           if item.family and not is_generic_reference(raw_target, item.span)]
        if not family_deictics:
            return result("not_applicable")
        deictic_heads = {head_class(item.head) for item in family_deictics}

        def compatible(declaration) -> bool:
            # A series/device reference is closed only by its own head class;
            # a generic "these products" may accept any product declaration.
            return "product" in deictic_heads or declaration.head in deictic_heads
        # Only a family reference (该系列/上述/这些/these products) carries the
        # cross-window identity claim. A singular demonstrative keeps the
        # legacy admission path: it is not this operation's dependency.
        if not family_deictics:
            return result("not_applicable")
        # Refs stay in original characters: detection never runs on a
        # normalised view whose offsets differ from the source bytes.
        references = [{"unit_id": target, "char_start": item.span[0],
                       "char_end": item.span[1]} for item in deictics]
        # A declaration strictly before the reference inside the same material
        # already closes it. A forward declaration does not, and two internal
        # families are ambiguous instead of silently preferred.
        internal_scan = scan_product_declarations(raw_target)
        if internal_scan.clipped:
            diagnostics.append({"code": "antecedent_window_clipped", "unit_id": target})
            return result("partial")
        internal = [declaration for declaration in internal_scan.declarations
                    if declaration.span[0] < family_deictics[0].span[0]
                    and declaration.attribution == "issuer" and compatible(declaration)]
        if internal:
            internal_families = {declaration.family for declaration in internal}
            if len(internal_families) > 1:
                diagnostics.append({"code": "antecedent_ambiguous", "unit_id": target,
                                    "family_count": len(internal_families)})
                return result("ambiguous", references=references)
            return result("not_applicable")
        if not window_complete:
            diagnostics.append({"code": "antecedent_window_incomplete", "unit_id": target})
            return result("partial")
        families: dict[str, list[tuple[str, Any]]] = {}
        clipped_any = False
        try:
            self.work_budget.charge(len(predecessors) + 1)
            for predecessor in predecessors:
                unit = self.unit(predecessor)
                if unit["role"] in _QUESTION_ROLES or unit["kind"] in _NON_DONATING_KINDS:
                    continue
                text = unit["text"]
                self.work_budget.charge(len(text))
                if text.rstrip().endswith(("？", "?")) and "请问" in text:
                    continue
                scan = scan_product_declarations(text)
                if scan.clipped:
                    clipped_any = True
                for declaration in scan.declarations:
                    if declaration.attribution != "issuer" or not compatible(declaration):
                        continue
                    families.setdefault(declaration.family, []).append((predecessor, declaration))
        except WorkBudgetExceeded:
            diagnostics.append({"code": "work_budget_exhausted", "unit_id": target})
            return result("partial", references=references)
        if clipped_any:
            diagnostics.append({"code": "antecedent_window_clipped", "unit_id": target})
            return result("partial", references=references)
        if not families:
            diagnostics.append({"code": "antecedent_missing", "unit_id": target})
            return result("missing", references=references)
        if len(families) > 1:
            diagnostics.append({"code": "antecedent_ambiguous", "unit_id": target,
                                "family_count": len(families)})
            return result("ambiguous", references=references)
        _family, entries = next(iter(families.items()))
        nearest = entries[-1]
        declarations = [{"unit_id": unit_id, "char_start": declaration.span[0],
                         "char_end": declaration.span[1]}
                        for unit_id, declaration in entries]
        member_refs = [{"unit_id": nearest[0], "char_start": start, "char_end": end}
                       for start, end in nearest[1].members]
        required = tuple(dict.fromkeys(unit_id for unit_id, _ in entries))
        attribution = "issuer"
        if any(self.unit(unit_id)["role"] not in {"company_filing", "issuer", "management",
                                                  "management_discussion"}
               for unit_id, _ in entries):
            attribution = "unknown"
        return result("collective" if any(item[1].collective for item in entries) else "unique",
                      references=references, declarations=declarations,
                      members=member_refs, required=required, attribution=attribution)


def detect_operating_relations(
    observation: Mapping[str, Any], *, work_budget: WorkBudget
) -> dict[str, Any]:
    return _detect_operating_relations(observation, work_budget=work_budget)


_FRONTED_CONDITION = re.compile(r"^\s*(?:如果|若|一旦|假如|\bif\b|\bunless\b)", re.I)
_CONTRAST_BOUNDARY = re.compile(r"^\s*(?:但是|然而|不过|但|\bhowever\b|\bbut\b|\bnevertheless\b)", re.I)
_SENTENCE_END = re.compile(r"[。！？!?；;]|\.(?:\s|$)")


def _detect_operating_relations(
    observation: Mapping[str, Any], *, work_budget: WorkBudget,
    prepared: OperatingRelationSession | None = None,
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
        if prepared is None:
            prepared = OperatingRelationSession(units, work_budget=work_budget)
        target_unit = prepared.unit(target)
        target_text = prepared.matching_text(target)
        target_parent = target_unit["parent_id"]
        seen_contexts: set[str] = set()
        for index in range(len(context_ids)):
            work_budget.charge(1)
            context_id = context_ids[index]
            if not isinstance(context_id, str):
                raise ValueError("context_unit_ids must be strings")
            if context_id in seen_contexts:
                raise ValueError("duplicate context_unit_ids")
            seen_contexts.add(context_id)
            if context_id not in units:
                diagnostics.append({"code": "context_unit_missing", "unit_id": context_id})
                continue
            context_unit = prepared.unit(context_id)
            if context_unit["parent_id"] != target_parent:
                diagnostics.append({"code": "context_parent_mismatch", "unit_id": context_id})
                continue
            contexts_used.append(context_id)

        if not target_text.text.strip():
            diagnostics.append({"code": "unit_text_unavailable", "unit_id": target})
            return {
                "schema_version": RELATIONS_SCHEMA,
                "unit_id": target,
                "relations": [],
                "diagnostics": diagnostics,
                "status": "unavailable",
                "work_used": work_budget.used - used_before,
            }

        work_budget.charge(len(target_text.text))
        gate = _predicate_gate(p.EVENT_PATTERNS)
        if gate is not None and not gate.search(target_text.text):
            return {"schema_version": RELATIONS_SCHEMA, "unit_id": target,
                "relations": [], "diagnostics": diagnostics,
                "status": "partial" if diagnostics else "complete",
                "work_used": work_budget.used - used_before}
        # Only an actual possible predicate needs offset maps and contextual
        # name attribution. Normalized source characters were prepared once.
        target_view, name_classes = prepared.prepared(target)
        for context_id in contexts_used:
            _context_view, context_names = prepared.prepared(context_id)
            for name, label in context_names.items():
                name_classes.setdefault(name, label)
        scan = _UnitScan(target_view, name_classes)
        work_budget.charge(len(target_view.text))
        clauses = split_clauses(target_view)
        condition_scope = None
        preceding_end = 0
        for clause in clauses:
            work_budget.charge(1 + 8 * (clause[1] - clause[0]))
            clause_text = target_view.text[clause[0]:clause[1]]
            if (_SENTENCE_END.search(target_view.text[preceding_end:clause[0]])
                    or _CONTRAST_BOUNDARY.match(clause_text)):
                condition_scope = None
            if _FRONTED_CONDITION.match(clause_text):
                condition_scope = clause
            preceding_end = clause[1]
            closing = target_view.text[clause[1]:clause[1] + 1]
            if _clause_guarded(clause_text, closing):
                continue
            if p.RESTRICTION_CONTINUATION.match(clause_text) and relations:
                span = (clause[0], clause[1])
                relations[-1]["qualifier_refs"].append(_to_ref(target, target_view, span))
                continue
            events = (_clause_events(target_view, scan, clause, clause_text, work_budget)
                      if gate is None or gate.search(clause_text) else [])
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
                extra_quals = []
                if condition_scope is not None:
                    event.stage = event.modality = "conditional"
                    if condition_scope != clause:
                        extra_quals.append(condition_scope)
                relations.append(_relation_dict(target, target_view, clause, event, extra_quals))
    except WorkBudgetExceeded:
        exhausted = True

    # Clauses and their non-overlapping events are already in source order.

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
