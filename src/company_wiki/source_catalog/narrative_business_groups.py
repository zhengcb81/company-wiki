"""Bounded same-source business support groups, using the existing atomic budget.

These are selected sets of original locators, not invented continuous quotes.
No source reads, no parser imitation, no model/task state and no permission.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import re
from types import MappingProxyType

from .n6_candidate_completion import BUSINESS_CHARACTER_WINDOW, MAX_COMPLETION_UNITS, ends_sentence
from .narrative_business_policy import business_objects, business_qualification
from .narrative_business_policy import detect_business_fact
from .narrative_stage_assertions import commercialization_milestone

from .narrative_candidates import CandidateRules, EvidenceCandidate, assess_unit
from .narrative_document import NarrativeUnit
from .narrative_visual_units import is_ocr_unit, ocr_continues, ocr_identity, join_unit_text
from .narrative_group_candidates import AtomicSentenceOwner
from .narrative_pdf_groups import _bbox, _has_visual_overlap
from .n6_candidate_operating_facts import OperatingFact

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
    restored_unit_ids: frozenset[str] = frozenset()


def _order(unit: NarrativeUnit) -> tuple:
    c = unit.coordinates
    return (unit.source_id, -1 if c.page_number is None else c.page_number,
        -1 if c.paragraph_index is None else c.paragraph_index,
        -1 if c.char_start is None else c.char_start, unit.unit_id)


def _same_boundary(left: NarrativeUnit, right: NarrativeUnit, *,
    respect_native_structure: bool = False) -> bool:
    if (left.source_id, left.parser_name, left.parser_version, left.source_role, left.language) != (
        right.source_id, right.parser_name, right.parser_version, right.source_role, right.language):
        return False
    if any(left.metadata.get(key) != right.metadata.get(key) for key in _SCOPE_KEYS):
        return False
    if respect_native_structure and left.parser_name == "cwp_document_normalization":
        # Native paragraphs, headings and cells are different structural owners.
        # Table semantics stay with the table classifier, never sentence completion.
        if left.unit_kind != right.unit_kind:
            return False
        if left.unit_kind == "pptx_paragraph":
            shape = left.metadata.get("shape_path")
            if shape is None or shape != right.metadata.get("shape_path"):
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


def _barrier(unit: NarrativeUnit, rules: CandidateRules, *,
    respect_native_structure: bool = False) -> bool:
    if unit.source_role in _EXCLUDED_ROLES or unit.unit_kind == "pdf_table_row":
        return True
    if respect_native_structure and unit.parser_name == "cwp_document_normalization" and (
        unit.coordinates.table_index is not None
        or unit.unit_kind.endswith("_table_cell")
        or unit.unit_kind.endswith("_heading")
    ):
        return True  # Eligible cells/headings remain standalone initial candidates.
    text = unit.raw_text
    return bool(rules.reject_text(text) or rules.table_of_contents.search(text)
        or rules.accounting_context.search(text) or rules.heading_only.search(text))


def _relation(left: NarrativeUnit, right: NarrativeUnit, rules: CandidateRules, *,
    respect_native_structure: bool = False) -> str | None:
    if (not _same_boundary(left, right, respect_native_structure=respect_native_structure)
        or _barrier(right, rules, respect_native_structure=respect_native_structure)
        or _NEW_SUBJECT.search(right.raw_text)):
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


def _referential_pdf_event(left: NarrativeUnit, right: NarrativeUnit, rules: CandidateRules) -> bool:
    """An independently selected product can still be required event context."""
    a, b = left.coordinates, right.coordinates
    return (left.unit_kind == right.unit_kind == "pdf_text_block"
        and a.page_number == b.page_number and a.paragraph_index is not None
        and b.paragraph_index == a.paragraph_index + 1
        and _same_boundary(left, right) and not _barrier(left, rules)
        and not _barrier(right, rules) and _REFERENCE.search(right.raw_text) is not None
        and rules.high_value_event.search(right.raw_text) is not None
        and bool(business_objects(left.raw_text).intersection(business_objects(right.raw_text))))


def _group_id(members: Sequence[NarrativeUnit]) -> str:
    digest = hashlib.sha256("|".join(unit.unit_id for unit in members).encode()).hexdigest()
    return "urn:company-wiki:context-group:sha256:" + digest


def _text_size(members: Sequence[NarrativeUnit]) -> int:
    return sum(len(unit.raw_text) for unit in members) + (
        len(members) - 1 if members and members[0].language.startswith("en") else 0)


def enrich_business_groups(units: Sequence[NarrativeUnit], *,
    initial_candidates: Sequence[EvidenceCandidate], initial_group_ids: Mapping[str, str],
    rules: CandidateRules, respect_native_structure: bool = False,
    preserve_operating_context: bool = False,
    atomic_owners: Sequence[AtomicSentenceOwner] = ()) -> BusinessEnrichmentResult:
    """Complete nearby meaning; frozen older policies retain their exact ordering."""
    if preserve_operating_context:
        return _enrich_operating_context(units, initial_candidates=initial_candidates,
            initial_group_ids=initial_group_ids, rules=rules,
            respect_native_structure=respect_native_structure, atomic_owners=atomic_owners)
    native_sources = {unit.source_id for unit in units
        if respect_native_structure and unit.parser_name == "cwp_document_normalization"}
    positions = {unit.unit_id: index for index, unit in enumerate(units)}

    def context_order(unit: NarrativeUnit) -> tuple:
        if unit.source_id in native_sources:
            # Native parsers already return physical document traversal order.
            # Independent paragraph/table counters cannot reconstruct that order.
            return (unit.source_id, positions[unit.unit_id])
        return _order(unit)

    def barrier(unit: NarrativeUnit) -> bool:
        return _barrier(unit, rules, respect_native_structure=respect_native_structure)

    def relation(left: NarrativeUnit, right: NarrativeUnit) -> str | None:
        return _relation(left, right, rules, respect_native_structure=respect_native_structure)

    ordered = tuple(sorted(units, key=context_order))
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

    def extendable_singleton(unit: NarrativeUnit) -> bool:
        group = group_ids.get(unit.unit_id)
        return group is None or not any(other != unit.unit_id and value == group
            for other, value in group_ids.items())

    def add_members(members: Sequence[NarrativeUnit]) -> None:
        topics = tuple(dict.fromkeys(topic for unit in members if unit.unit_id in by_id
            for topic in by_id[unit.unit_id].topics))
        for unit in members:
            if unit.unit_id not in by_id:
                by_id[unit.unit_id] = EvidenceCandidate(unit, topics,
                    ("business_group_context", "operating_qualification"), 0)
        for left, right in zip(members, members[1:]):
            if _referential_pdf_event(left, right, rules):
                candidate = by_id[left.unit_id]
                by_id[left.unit_id] = EvidenceCandidate(candidate.unit, candidate.topics,
                    tuple(dict.fromkeys((*candidate.reasons, "adjacent_subject_context"))), candidate.score)
        if len(members) > 1:
            group = _group_id(members)
            for unit in members:
                group_ids[unit.unit_id] = group
        handled.update(unit.unit_id for unit in members)

    for index, seed in enumerate(ordered):
        if seed.unit_id not in by_id or seed.unit_id in handled or barrier(seed):
            continue
        if seed.unit_kind == "official_json_field":
            if len(seed.raw_text) > BUSINESS_CHARACTER_WINDOW:
                diagnostic("business_group_character_limit", (seed,))
            handled.add(seed.unit_id)
            continue
        reference_pair = (
            index > 0 and _referential_pdf_event(ordered[index - 1], seed, rules)
        ) or (index + 1 < len(ordered) and _referential_pdf_event(seed, ordered[index + 1], rules))
        if seed.unit_id in group_ids and (not extendable_singleton(seed) or not reference_pair):
            continue  # Multi-member project/PDF groups retain their separate semantics.
        start = index
        if index > 0:
            previous = ordered[index - 1]
            if (previous.unit_id not in handled and (previous.unit_id not in group_ids
                    or (extendable_singleton(previous) and _referential_pdf_event(previous, seed, rules)))
                and not barrier(previous)
                and relation(previous, seed) == "required"):
                start -= 1
        members = list(ordered[start:index + 1])
        if _text_size(members) > BUSINESS_CHARACTER_WINDOW:
            add_members(members)
            diagnostic("business_group_character_limit", members)
            continue
        for next_index in range(index + 1, len(ordered)):
            follower = ordered[next_index]
            if follower.unit_id in handled or (follower.unit_id in group_ids
                and not (extendable_singleton(follower)
                    and _referential_pdf_event(members[-1], follower, rules))):
                break
            relation_kind = relation(members[-1], follower)
            if relation_kind is None:
                break
            prospective = (*members, follower)
            over_units = len(prospective) > MAX_COMPLETION_UNITS
            over_text = _text_size(prospective) > BUSINESS_CHARACTER_WINDOW
            if over_units or over_text:
                if relation_kind == "required":
                    members.append(follower)
                    add_members(members)
                    diagnostic("business_group_unit_limit" if over_units else "business_group_character_limit", members)
                break
            members.append(follower)
        add_members(members)
    return BusinessEnrichmentResult(tuple(by_id[unit_id] for unit_id in sorted(by_id,
        key=lambda unit_id: context_order(by_id[unit_id].unit))), MappingProxyType(group_ids),
        frozenset(excluded), tuple(diagnostics))


# One indivisible parser paragraph may carry both operating and accounting
# statements. Keep it whole under a local bound; never raise a request/bundle cap.
_NATIVE_PARAGRAPH_LIMIT = 4 * BUSINESS_CHARACTER_WINDOW
_NUMBER = re.compile(r"\d|[一二三四五六七八九十百千万亿]+(?:个|台|套|家|万|亿)")
_OPERATING_QUANTITY = re.compile(
    r"\b(?:paid seats?|paying users?|active users?|DAU|MAU|downloads?|retention|"
    r"remaining performance obligations?|backlog|orders?|shipments?|token consumption)\b|"
    r"(?:设备|产品).{0,35}(?:累计出货|反应台|重复.{0,5}订单)|"
    r"(?:产能|生产|研发)?(?:基地|中心|总部|大楼).{0,80}(?:开工|投产|投入使用|封顶|落成)|"
    r"(?:客户|设备|产品).{0,50}(?:现场验证|重复.{0,5}订单)", re.IGNORECASE)
_SERVICE_REVENUE = re.compile(
    r"\b(?:cloud services?|(?:commercial|consumer) cloud|games?|subscriptions?|"
    r"marketing services?)\b[^。!?;]{0,90}\brevenues?\b[^。!?;]{0,100}\d", re.IGNORECASE)
_OPERATING_VALUE = re.compile(
    r"(?:[\d,.]+|[一二三四五六七八九十百千万亿]+)\s*"
    r"(?:%|％|个|台|套|家|名|人|亩|平方米|平米|万|亿|"
    r"customers?\b|units?\b|seats?\b|billion\b|million\b)", re.IGNORECASE)
_RESOURCE_OBJECT = re.compile(r"供应链|供应商|零部件|产能|算力|计算资源|"
    r"\b(?:supply|suppliers?|components?|capacity|compute|GPU)\b", re.IGNORECASE)
_RESOURCE_CONSTRAINT = re.compile(r"紧张|受限|瓶颈|短缺|缺货|不足|"
    r"影响.{0,16}(?:交期|交付|产量)|\b(?:constrain\w*|shortages?|bottlenecks?|delay\w*)\b", re.IGNORECASE)
_COMMERCIAL_RELATION = re.compile(
    r"\b(?:pay for|moneti[sz]\w* (?:via|through)|translated into (?:increased )?revenue|"
    r"favourable pricing|commercial payments?|compute constrained)\b|"
    r"(?:供应商|零部件).{0,55}(?:策略|保障|交期)|"
    r"(?:设备|产品).{0,45}(?:现场验证|量产订单)", re.IGNORECASE)
_DEFINITION = re.compile(
    r"\b(?:will include|includes?|comprises?)\b[^。!?;]{0,130}"
    r"\b(?:licensing|cloud|consulting|support businesses|subscriptions?)\b", re.IGNORECASE)
# Classification distinguishes disclosed commercial progress from a delivery
# step in a contract/workflow. An object or product name alone is not proof.
_STAGE_CN_OBJECT = r"(?:设备|产品|系统|平台|方案|服务|系列|型号|机型)"
_STAGE_EN_OBJECT = r"\b(?:products?|equipment|systems?|platforms?|services?|solutions?)\b"
_STAGE_SENTENCES = re.compile(r"[。！？!?;；\n]|\.(?:\s|$)")
_STAGE_OBJECT = re.compile(_STAGE_CN_OBJECT + "|" + _STAGE_EN_OBJECT, re.IGNORECASE)
_CONDITIONAL_STAGE = re.compile(r"^\s*(?:若|如果|一旦|当|待|但凡|if\b|once\b|when\b|upon\b|after\b|unless\b)", re.IGNORECASE)
_PLANNED_STAGE = re.compile(
    r"(?:计划|拟|预计|将|尽早)[^。；]{0,100}(?:开发|研发|推出|付运|发运|交付|样机|客户验证|生产验证|测试)|"
    r"\b(?:plan(?:s|ned)? to|intend(?:s)? to|aim(?:s)? to|will|expected to)\b"
    r"[^.!?;]{0,100}\b(?:develop|deploy|ship|dispatch|deliver|test|validation|qualification|pilot)\b",
    re.IGNORECASE)
_DELIVERY_TERMS = re.compile(
    rf"{_STAGE_CN_OBJECT}[^。；]{{0,60}}(?:交付|出货)[^。；]{{0,65}}"
    r"(?:收款|货款|付款|收入确认|确认收入|权利|风险|流程|资金|交付时间)|"
    rf"{_STAGE_EN_OBJECT}[^.!?;]{{0,60}}\b(?:deliver\w*|ship\w*)\b"
    r"[^.!?;]{0,65}\b(?:payments?|balance|ownership|risk|contract|terms|workflow)\b",
    re.IGNORECASE)
_FULL_STOP = re.compile(r"[。！？!?.]\s*[”’\"']?$")


def _classification_text(members: Sequence[NarrativeUnit]) -> str:
    # Whitespace flattening is match-only. Returned units and locators are original.
    return re.sub(r"\s+", " ", join_unit_text(members))


def _stage_match_text(text: str) -> str:
    # 已将/已经将 is completed active grammar, unlike a future 将. Match-only.
    return re.sub(r"(?:已经|已)将", "已", text)


def _commercialization_milestone(text: str) -> bool:
    return commercialization_milestone(text)


def _planned_operating_stage(text: str) -> bool:
    """Concrete future development/adoption is recallable, never completed proof."""
    for sentence in _STAGE_SENTENCES.split(text):
        if (_STAGE_OBJECT.search(sentence) and not _CONDITIONAL_STAGE.search(sentence)
            and _PLANNED_STAGE.search(_stage_match_text(sentence))):
            return True
    return False


def _operating_fact(text: str, rules: CandidateRules | None = None) -> OperatingFact:
    milestone = _commercialization_milestone(text)
    planned = _planned_operating_stage(text)
    # Current recall extends established scope/operating facts; it cannot
    # suppress valid reporting, M&A or platform metrics before evaluating them.
    old = detect_business_fact(text)
    reasons = [reason for reason in old.reasons
        if reason != "new_product_commercialization_milestone"]
    if _OPERATING_QUANTITY.search(text) and _OPERATING_VALUE.search(text):
        reasons.append("quantified_operating_status")
    if _SERVICE_REVENUE.search(text):
        reasons.append("quantified_operating_status")
    if _RESOURCE_OBJECT.search(text) and _RESOURCE_CONSTRAINT.search(text):
        reasons.append("specific_operating_constraint")
    if _COMMERCIAL_RELATION.search(text) or _DELIVERY_TERMS.search(text):
        reasons.append("operating_mechanism")
    if milestone:
        reasons.append("new_product_commercialization_milestone")
    if planned:
        reasons.append("project_plan_or_status")
    if _DEFINITION.search(text):
        reasons.append("reporting_definition_change")
    reasons = list(dict.fromkeys(reasons))
    return OperatingFact(bool(reasons), old.topics or (("core_business",) if reasons else ()),
        tuple(reasons), old.score + (3 if len(reasons) > len(old.reasons) else 0), old.financial_exempt)


def _structural_barrier(unit: NarrativeUnit, rules: CandidateRules) -> bool:
    return ((is_ocr_unit(unit) and ocr_identity(unit) is None)
        or unit.source_role in _EXCLUDED_ROLES or unit.unit_kind == "pdf_table_row"
        or unit.coordinates.table_index is not None or unit.unit_kind.endswith("_table_cell")
        or unit.unit_kind.endswith("_heading") or bool(rules.table_of_contents.search(unit.raw_text)
        or rules.accounting_context.search(unit.raw_text)))


def _physical_link(left: NarrativeUnit, right: NarrativeUnit, rules: CandidateRules) -> bool:
    if _structural_barrier(left, rules) or _structural_barrier(right, rules):
        return False
    if is_ocr_unit(left) or is_ocr_unit(right):
        return ocr_continues(left, right)
    if not _same_boundary(left, right, respect_native_structure=True):
        return False
    if left.coordinates.page_number != right.coordinates.page_number:
        return False
    if left.unit_kind != "pdf_text_block" or right.unit_kind != "pdf_text_block":
        return False  # Native HTML/DOCX paragraphs are whole structural units.
    same_block = left.metadata.get("pdf_block") is not None and (
        left.metadata.get("pdf_block") == right.metadata.get("pdf_block")
        and left.metadata.get("block_sha256") == right.metadata.get("block_sha256"))
    return same_block or _has_visual_overlap(left, right)


def _sentence_continues(left: NarrativeUnit, right: NarrativeUnit, rules: CandidateRules) -> bool:
    if (not _physical_link(left, right, rules) or _FULL_STOP.search(left.raw_text)
        or right.raw_text.startswith(("•", "▪"))):
        return False
    for paragraph, other in ((left, right), (right, left)):
        if (len(paragraph.raw_text)>BUSINESS_CHARACTER_WINDOW
            and paragraph.metadata.get("block_char_start")==0
            and paragraph.metadata.get("block_char_end")==len(paragraph.raw_text)
            and paragraph.metadata.get("pdf_block") != other.metadata.get("pdf_block")):
            return False  # Whole native paragraph is not a clipped line fragment.
    if left.raw_text.rstrip().endswith((";", "；")):
        # A semicolon is not a terminal when the same original English block
        # continues a lower-case dependent clause. It remains a clause boundary
        # before a new standalone subject/list item.
        return (left.language.startswith("en") and bool(re.match(r"^[a-z]", right.raw_text))
            and left.metadata.get("pdf_block") == right.metadata.get("pdf_block")
            and left.metadata.get("block_sha256") == right.metadata.get("block_sha256"))
    return True


def _visual_title(body: NarrativeUnit, units: Sequence[NarrativeUnit], rules: CandidateRules) -> NarrativeUnit | None:
    b = _bbox(body)
    if body.unit_kind != "pdf_text_block" or b is None or not body.raw_text.startswith(("•", "▪")):
        return None
    choices: list[tuple[float, NarrativeUnit]] = []
    for title in units:
        t = _bbox(title)
        if title.unit_id == body.unit_id or t is None or title.unit_kind != "pdf_text_block":
            continue
        if not _same_boundary(title, body, respect_native_structure=True):
            continue
        if title.coordinates.page_number != body.coordinates.page_number:
            continue
        if _structural_barrier(title, rules) or not 3 <= len(title.raw_text) <= 80:
            continue
        if re.search(r"[。.!?;；\n]|^\d+$|^[•▪]", title.raw_text):
            continue
        gap = b[1] - t[3]
        overlap = min(t[2], b[2]) - max(t[0], b[0])
        if 0 <= gap <= 24 and min(t[2]-t[0], b[2]-b[0]) > 0 and (
            overlap / min(t[2]-t[0], b[2]-b[0]) >= 0.6):
            choices.append((gap, title))
    if not choices:
        return None
    choices.sort(key=lambda pair: pair[0])
    if len(choices)>1 and abs(choices[0][0]-choices[1][0])<1:
        return None  # Ambiguous actors remain unbound, never guessed.
    return choices[0][1]


def _enrich_operating_context(units: Sequence[NarrativeUnit], *,
    initial_candidates: Sequence[EvidenceCandidate], initial_group_ids: Mapping[str, str],
    rules: CandidateRules, respect_native_structure: bool,
    atomic_owners: Sequence[AtomicSentenceOwner]) -> BusinessEnrichmentResult:
    """0.8 native business recall; explicit old policies never enter this path."""
    legacy = enrich_business_groups(units, initial_candidates=initial_candidates,
        initial_group_ids=initial_group_ids, rules=rules,
        respect_native_structure=respect_native_structure)
    by_id = {candidate.unit.unit_id: candidate for candidate in legacy.candidates}
    groups = dict(legacy.group_ids)
    excluded = set(legacy.excluded_unit_ids)
    diagnostics = list(legacy.diagnostics)
    restored: set[str] = set()
    positions = {u.unit_id: i for i, u in enumerate(units)}
    ordered = tuple(sorted(units, key=lambda u: (u.source_id, positions[u.unit_id])
        if u.parser_name == "cwp_document_normalization" else _order(u)))
    owners_by_unit: dict[str, list[int]] = {}
    for index, owner in enumerate(atomic_owners):
        for unit_id in owner.unit_ids:
            owners_by_unit.setdefault(unit_id, []).append(index)
    visual_pages: dict[tuple, list[NarrativeUnit]] = {}
    for unit in ordered:
        if unit.unit_kind == "pdf_text_block":
            key = (unit.source_id, unit.coordinates.page_number, unit.source_role, unit.language)
            visual_pages.setdefault(key, []).append(unit)
    runs: list[list[NarrativeUnit]] = []
    for unit in ordered:
        if runs and _sentence_continues(runs[-1][-1], unit, rules):
            runs[-1].append(unit)
        else:
            runs.append([unit])
    # Explicit referential qualifiers need their preceding subject, even when
    # sentence parsing splits it. Merge only the bounded native sentences.
    sentences: list[list[NarrativeUnit]] = []
    for members in runs:
        if (sentences and (_REFERENCE.search(members[0].raw_text) or re.match(
            r"^(?:若|如果|倘若|除非|但|然而|if\b|unless\b|although\b|however\b|but\b)",
            members[0].raw_text, re.IGNORECASE))
            and _physical_link(sentences[-1][-1], members[0], rules)
            and business_objects(_classification_text(sentences[-1])).intersection(
                business_objects(_classification_text(members)))
            and _text_size((*sentences[-1], *members)) <= BUSINESS_CHARACTER_WINDOW):
            sentences[-1].extend(members)
        else:
            sentences.append(members)

    def omit(reason: str, members: Sequence[NarrativeUnit]) -> None:
        excluded.update(u.unit_id for u in members)
        if len(diagnostics)<16:
            diagnostics.append(BusinessGroupDiagnostic(reason,
                tuple(u.coordinates.locator() for u in members[:MAX_COMPLETION_UNITS]),len(members)))

    for members in sentences:
        if any(groups.get(u.unit_id, "").startswith("urn:company-wiki:fundraising-context:")
            for u in members):
            continue  # Native project introduction + table is a separate atomic owner.
        if any(_structural_barrier(u, rules) for u in members):
            continue
        ids = {u.unit_id for u in members}
        owner_indices = {index for uid in ids for index in owners_by_unit.get(uid, ())}
        owners = [atomic_owners[index] for index in sorted(owner_indices)]
        if any(not set(owner.unit_ids) <= ids for owner in owners):
            # A coarse layout split may not rewrite only part of a proved owner.
            # Existing candidate/group membership stays intact.
            continue
        whole = len(members)==1 and not is_ocr_unit(members[0])
        cap = _NATIVE_PARAGRAPH_LIMIT if whole else BUSINESS_CHARACTER_WINDOW
        if (_text_size(members)>cap or any(owner.exclusion_reason for owner in owners)):
            omit("business_group_character_limit", members)
            continue  # Do not assemble/classify an unbounded original sentence.
        text = _classification_text(members)
        fact = _operating_fact(text, rules)
        if not fact.eligible:
            continue
        assessment = assess_unit(replace(members[0], raw_text=text), replace(rules,
            operating_facts=lambda _text: fact, reject_text=lambda _text: False))
        assessed = assessment.candidate
        topics = tuple(dict.fromkeys((*rules.topics(text), *fact.topics)))
        reasons = tuple(dict.fromkeys(("business_narrative_signal", *fact.reasons,
            *(assessed.reasons if assessed is not None else ()),
            *(("business_group_context", "operating_qualification") if len(members)>1 else ()))))
        for unit in members:
            old = by_id.get(unit.unit_id)
            by_id[unit.unit_id] = EvidenceCandidate(unit, topics,
                tuple(dict.fromkeys((*old.reasons, *reasons))) if old else reasons,
                max(old.score if old else 0, assessed.score if assessed is not None else fact.score + len(topics)))
        title = _visual_title(members[0], visual_pages.get((members[0].source_id,
            members[0].coordinates.page_number, members[0].source_role, members[0].language), ()),
            rules) if len(members)==1 else None
        if title is not None and _text_size((title,*members))<=BUSINESS_CHARACTER_WINDOW:
            by_id[title.unit_id] = EvidenceCandidate(title, topics,
                ("adjacent_subject_context", "business_group_context"), fact.score)
            members = [title,*members]
        # Rebuild these operating sentence owners only. Unrelated prior members
        # retain their original group; project/table groups were never traversed.
        for unit in members:
            excluded.discard(unit.unit_id)
            restored.add(unit.unit_id)
        if len(members)>1:
            group = _group_id(members)
            for unit in members:
                groups[unit.unit_id] = group
        elif (len(members[0].raw_text)>BUSINESS_CHARACTER_WINDOW
            or (members[0].unit_kind == "pdf_text_block"
                and members[0].raw_text.startswith(("•", "▪")))):
            groups.pop(members[0].unit_id,None)
    return BusinessEnrichmentResult(tuple(by_id[u.unit_id] for u in ordered if u.unit_id in by_id),
        MappingProxyType(groups),frozenset(excluded),tuple(diagnostics),frozenset(restored))


__all__ = ["BusinessGroupDiagnostic", "BusinessEnrichmentResult", "enrich_business_groups"]
