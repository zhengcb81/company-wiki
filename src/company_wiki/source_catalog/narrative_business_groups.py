"""Bounded same-source business support groups, using the existing atomic budget.

These are selected sets of original locators, not invented continuous quotes.
No source reads, no parser imitation, no model/task state and no permission.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import re
from types import MappingProxyType

from .n6_candidate_completion import BUSINESS_CHARACTER_WINDOW, MAX_COMPLETION_UNITS, ends_sentence
from .narrative_business_policy import business_objects, business_qualification
from .narrative_candidates import CandidateRules, EvidenceCandidate
from .narrative_document import NarrativeUnit
from .narrative_visual_units import is_ocr_unit

_EXCLUDED_ROLES = frozenset({"analyst", "investor_question", "operator", "editorial", "qa_text_shadow"})
_SCOPE_KEYS = ("qa_group_id", "qa_parent_id", "qa_question_number", "speaker", "speaker_title", "section",
    "parent_content_sha256", "projection_id", "record_pointer", "official_record_group_id")
_REFERENCE = re.compile(r"^\s*(?:该(?:系列|设备|产品)|这些|上述|其中|其(?:中)?|"
    r"(?:(?:and\s+)?(?:so\s+)?)?(?:this|these|it|they)\b|then you have\b)", re.IGNORECASE)
_QUALIFIED_FOLLOWER = re.compile(r"^\s*(?:but\b|however\b|yet\b|unless\b|"
    r"only if\b|not just\b|但|不过|然而|由于|只有|短期|突发)", re.IGNORECASE)
_CONTINUATION = re.compile(r"^\s*(?:and\b|so\b|then\b|all of these\b|"
    r"you need\b|并|同时|以及|因此)", re.IGNORECASE)
_NEW_SUBJECT = re.compile(r"\b(?:the other thing|another business|different product)\b|"
    r"另一(?:产品|业务|公司)|此外.{0,12}(?:另一|新业务)", re.IGNORECASE)
_NAMED_PRODUCT = re.compile(r"\b([A-Z][A-Za-z0-9-]*)\s+(?:product|equipment|production line)\b")


@dataclass(frozen=True)
class BusinessGroupDiagnostic:
    reason: str
    locators: tuple[str, ...]
    unit_count: int


@dataclass(frozen=True)
class BusinessEnrichmentResult:
    candidates: tuple[EvidenceCandidate, ...]
    group_ids: Mapping[str, str]
    excluded_unit_ids: frozenset[str]
    diagnostics: tuple[BusinessGroupDiagnostic, ...]


def _order(unit: NarrativeUnit) -> tuple:
    c = unit.coordinates
    return (unit.source_id, -1 if c.page_number is None else c.page_number,
        -1 if c.paragraph_index is None else c.paragraph_index,
        -1 if c.char_start is None else c.char_start, unit.unit_id)


def _same_boundary(left: NarrativeUnit, right: NarrativeUnit) -> bool:
    if (left.source_id, left.parser_name, left.parser_version, left.source_role, left.language) != (
        right.source_id, right.parser_name, right.parser_version, right.source_role, right.language):
        return False
    if any(left.metadata.get(key) != right.metadata.get(key) for key in _SCOPE_KEYS):
        return False
    # Native JSON currently exposes whole fields, never synthetic char fragments.
    if left.unit_kind == "official_json_field" or right.unit_kind == "official_json_field":
        return False
    if is_ocr_unit(left) or is_ocr_unit(right):
        return False  # source-owned OCR completion remains in its existing layer.
    a, b = left.coordinates.page_number, right.coordinates.page_number
    if a != b:
        if (left.unit_kind != "pdf_text_block" or right.unit_kind != "pdf_text_block"
            or a is None or b != a + 1):
            return False
        if not business_objects(left.raw_text).intersection(business_objects(right.raw_text)):
            return False
        if not (_REFERENCE.search(right.raw_text) or _QUALIFIED_FOLLOWER.search(right.raw_text)
            or not ends_sentence(left.raw_text)):
            return False
    left_names = set(_NAMED_PRODUCT.findall(left.raw_text))
    right_names = set(_NAMED_PRODUCT.findall(right.raw_text))
    return not (left_names and right_names and left_names.isdisjoint(right_names))


def _barrier(unit: NarrativeUnit, rules: CandidateRules) -> bool:
    if unit.source_role in _EXCLUDED_ROLES or unit.unit_kind == "pdf_table_row":
        return True
    text = unit.raw_text
    return bool(rules.reject_text(text) or rules.table_of_contents.search(text)
        or rules.accounting_context.search(text) or rules.heading_only.search(text))


def _relation(left: NarrativeUnit, right: NarrativeUnit, rules: CandidateRules) -> str | None:
    if not _same_boundary(left, right) or _barrier(right, rules) or _NEW_SUBJECT.search(right.raw_text):
        return None
    if not ends_sentence(left.raw_text):
        return "required"
    if business_qualification(left.raw_text) and rules.operating_facts(right.raw_text).eligible:
        return "required"
    common = business_objects(left.raw_text).intersection(business_objects(right.raw_text))
    qualified = business_qualification(right.raw_text)
    if _QUALIFIED_FOLLOWER.search(right.raw_text) and (common or qualified):
        return "required"
    if (_REFERENCE.search(right.raw_text) and (common or qualified)) or qualified:
        return "required"
    if common and _CONTINUATION.search(right.raw_text) and rules.operating_facts(right.raw_text).eligible:
        return "related"
    return None


def _group_id(members: Sequence[NarrativeUnit]) -> str:
    digest = hashlib.sha256("|".join(unit.unit_id for unit in members).encode()).hexdigest()
    return "urn:company-wiki:context-group:sha256:" + digest


def _text_size(members: Sequence[NarrativeUnit]) -> int:
    return sum(len(unit.raw_text) for unit in members) + (
        len(members) - 1 if members and members[0].language.startswith("en") else 0)


def enrich_business_groups(units: Sequence[NarrativeUnit], *,
    initial_candidates: Sequence[EvidenceCandidate], initial_group_ids: Mapping[str, str],
    rules: CandidateRules) -> BusinessEnrichmentResult:
    """Complete only nearby specific meaning and expose bounded omission diagnostics."""
    ordered = tuple(sorted(units, key=_order))
    by_id = {candidate.unit.unit_id: candidate for candidate in initial_candidates}
    group_ids = dict(initial_group_ids)
    excluded: set[str] = set()
    diagnostics: list[BusinessGroupDiagnostic] = []
    handled: set[str] = set()

    def diagnostic(reason: str, members: Sequence[NarrativeUnit]) -> None:
        excluded.update(unit.unit_id for unit in members)
        if len(diagnostics) < 16:
            diagnostics.append(BusinessGroupDiagnostic(reason,
                tuple(unit.coordinates.locator() for unit in members[:MAX_COMPLETION_UNITS]), len(members)))

    def add_members(members: Sequence[NarrativeUnit]) -> None:
        topics = tuple(dict.fromkeys(topic for unit in members if unit.unit_id in by_id
            for topic in by_id[unit.unit_id].topics))
        for unit in members:
            if unit.unit_id not in by_id:
                by_id[unit.unit_id] = EvidenceCandidate(unit, topics,
                    ("business_group_context", "operating_qualification"), 0)
        if len(members) > 1:
            group = _group_id(members)
            for unit in members:
                group_ids[unit.unit_id] = group
        handled.update(unit.unit_id for unit in members)

    for index, seed in enumerate(ordered):
        if seed.unit_id not in by_id or seed.unit_id in handled or _barrier(seed, rules):
            continue
        if seed.unit_kind == "official_json_field":
            if len(seed.raw_text) > BUSINESS_CHARACTER_WINDOW:
                diagnostic("business_group_character_limit", (seed,))
            handled.add(seed.unit_id)
            continue
        if seed.unit_id in group_ids:
            continue  # Existing project/PDF groups retain their separate semantics.
        start = index
        if index > 0:
            previous = ordered[index - 1]
            if (previous.unit_id not in handled and previous.unit_id not in group_ids
                and not _barrier(previous, rules)
                and _relation(previous, seed, rules) == "required"):
                start -= 1
        members = list(ordered[start:index + 1])
        if _text_size(members) > BUSINESS_CHARACTER_WINDOW:
            add_members(members)
            diagnostic("business_group_character_limit", members)
            continue
        for next_index in range(index + 1, len(ordered)):
            follower = ordered[next_index]
            if follower.unit_id in handled or follower.unit_id in group_ids:
                break
            relation = _relation(members[-1], follower, rules)
            if relation is None:
                break
            prospective = (*members, follower)
            over_units = len(prospective) > MAX_COMPLETION_UNITS
            over_text = _text_size(prospective) > BUSINESS_CHARACTER_WINDOW
            if over_units or over_text:
                if relation == "required":
                    members.append(follower)
                    add_members(members)
                    diagnostic("business_group_unit_limit" if over_units else "business_group_character_limit", members)
                break
            members.append(follower)
        add_members(members)
    return BusinessEnrichmentResult(tuple(by_id[unit_id] for unit_id in sorted(by_id,
        key=lambda unit_id: _order(by_id[unit_id].unit))), MappingProxyType(group_ids),
        frozenset(excluded), tuple(diagnostics))


__all__ = ["BusinessGroupDiagnostic", "BusinessEnrichmentResult", "enrich_business_groups"]
