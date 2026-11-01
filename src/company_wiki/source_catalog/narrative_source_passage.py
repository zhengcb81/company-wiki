"""Prepared source-quote capability, never an issuer/event/measurement proof.

Unknown names and business vocabularies need not match an operating predicate
inventory to remain readable narration. This uses generic declaration syntax
and existing source-purpose/abstract/accounting observations. Original text,
attribution, stage, numeric meaning and priority remain with their owners.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import re

from company_wiki.document_understanding.operating_states.assertion_roles import (
    SourceAssertionRoles, abstract_source_argument, _STATE_HEAD,
)
from company_wiki.document_understanding.structure.table_purpose import accounting_field
from company_wiki.document_understanding.source_turn_markers import (
    explicit_qa_marker, ROLE_INVESTOR, SOURCE_TURN_MARKER_PREFIX_CHARS,
)
from company_wiki.document_normalization.text_matching import matching_reading_text

from .narrative_causal_links import CAUSAL_LINK
from .narrative_business_meaning import _OBJECT
from .narrative_reporting_rules import arithmetic_presentation


SOURCE_PASSAGE_POLICY_VERSION = 'source-passage/2'
# Preparation reuses normalized clauses from the already charged assessment.
# Includes generic grammar, negative envelopes, account and cause scans, plus
# the measurement callback's normalized clause view. Metric proofs themselves
# share the assessment cache with causal and business consumers.
SOURCE_PASSAGE_SCAN_PASSES = 24


@dataclass(frozen=True)
class SourcePassageCapability:
    use: str
    reason: str
    role: str
    relevant: bool
    financial_only: bool = False


@dataclass(frozen=True)
class SourceStatementScope:
    """Transient classification view; original refs never index normalized text."""
    text: str
    roles: SourceAssertionRoles
    suppressed: bool = False
    assertion_keys: frozenset[str] = frozenset()
    business_causal_keys: frozenset[str] = frozenset()


# Finite grammatical witnesses, not products, industries or named entities.
_EN_DECLARATION = re.compile(
    r'\b(?:is|are|was|were|has|have|had|will|would|can|could|may|might)\s+\S|'
    r'\bowns\s+\S|\bfrom\s+\d[^!?;]{0,60}\bto\s+\d', re.I)
_CN_DECLARATION = re.compile(
    r'拥有|设有|包括|包含|取决于|由于|因为|'
    r'从[^。！？;；]{1,80}(?:到|至)|'
    r'(?:正在|已经|尚未|预计|计划|将会|能够|可以)[^。！？;；]{3,}|'
    r'[^。！？;；]{2,}(?:是|为)[^。！？;；]{3,}|'
    r'对[^。！？;；]{2,}(?:影响|依赖)')
_EN_QUESTION = re.compile(r'\s*(?:(?:what|when|where|why|how|whether)\b|'
                          r'(?:is|are|was|were|do|does|did|can|could|will|would)\b)', re.I)
_CN_QUESTION = re.compile(r'\s*(?:请问|請問|是否|会不会|會不會)')
_NON_ASSERTION = re.compile(
    r'^\s*(?:the\s+)?(?:模板|示例|填报|流程|程序|规则|指南|template|example|procedure|manual|'
    r'instructions?|guidelines?)\b|'
    r'^\s*(?:模板|示例|填报|流程|程序|规则|指南)(?:示例|说明|要求|规定|[:：])', re.I)
_REFERENCE_METADATA = re.compile(r'\b(?:glossary|contents|index)\b|术语表|词汇表|目录|'
                                 r'^(?:单位|币种)\s*[:：为是]|'
                                 r'^\s*(?:all\s+)?amounts?\s+in\b', re.I)
_DEPENDENT_SUBJECT = re.compile(r'^\s*(?:the\s+other|other|this|that|such|these|those)\b', re.I)
_COURTESY = re.compile(r'\s*(?:thank you|thanks|good morning|good afternoon|'
                         r'谢谢|謝謝|感谢|感謝|各位好)', re.I)
_VAGUE_OBJECTIVE = re.compile(
    r'\b(?:striv\w*|aspir\w*)\b[^。.!?]{0,90}\b(?:value|goals?|vision|success)\b|'
    r'\b(?:outstanding|strategic|best-in-class)\s+(?:goals?|aspirations?|'
    r'products?|services?|solutions?)\b|'
    r'(?:努力|愿景|目标)[^。！？]{0,35}(?:价值|发展|未来)|'
    r'(?:宏伟|远大|美好)(?:的)?(?:愿景|目标|未来)|'
    r'为股东创造[^。！？]{0,15}价值', re.I)
_SENTENCE_END = re.compile(r'[。！？;；]|[.!?](?=\s|$)')
_QUESTION_END = re.compile(r'[?？]')
_CONFIRMATION_QUESTION = re.compile(
    r'\s*(?:(?:is|was)\s+(?:that|this|it)\s+(?:correct|true|accurate)\b|'
    r'(?:please\s+)?confirm\b[^?？]{0,80}\b(?:that|this|statement)\b|'
    r'(?:请|請)?确认(?:上述|这一|该|這一|該)[^?？]{0,30}(?:属实|屬實|正确|正確))', re.I)
_METADATA_STATEMENT = re.compile(
    r'\b(?:is|are|was|were|be|been)\s+(?:[a-z-]+\s+){0,2}'
    r'(?:described|discussed|mentioned|listed|referenced)\b'
    r'[^。.!?;]{0,80}\b(?:sections?|chapters?|elsewhere|appendi\w*|glossar\w*)\b|'
    r'\b(?:is|are)\s+defined\s+as\b|'
    r'\b(?:is|are)\s+(?:a\s+)?(?:(?:generic|general|billing)\s+){0,3}definition\b', re.I)
# A causal action must bind a typed operating argument in the same clause.
# Word morphology alone (e.g. an arbitrary -ing noun) proves neither role.
_CAUSAL_PROCESS = re.compile(
    r'\b(?:change[sd]?|shift(?:ed|s)?|adjust\w*|mix|higher|lower|greater|fewer|'
    r'increas\w*|decreas\w*|improv\w*|reduc\w*|manufactur\w*|assembl\w*|'
    r'process\w*|produc(?:e|es|ed|ing|tion)|complet\w*|expand\w*)\b|'
    r'调整|調整|改变|改變|转向|轉向|推进|推進|提高|提升|下降|上升|增长|增長|减少|減少|优化|優化', re.I)
_FINANCIAL_CAUSAL_ARGUMENT = re.compile(
    r'\bfinancial\s+(?:performance|results?|condition)\b|财务(?:表现|业绩|状况)|財務(?:表現|業績|狀況)', re.I)


def statement_assertion_key(text: str) -> str:
    return matching_reading_text(text).strip(' \t\r\n.。!?？！;；')


def prepare_source_statement_scope(text: str, roles: SourceAssertionRoles, *,
        accounting_text: Callable[[str], bool] = accounting_field,
        causal_relation: Callable[[str], bool] | None = None,
        measurement_relation: Callable[[str], bool] | None = None) -> SourceStatementScope:
    """Observe every sentence once; suppress question/courtesy proof anywhere.

    The masked classification string has exactly the original length. One
    monotonic alignment filters the already prepared role proofs; normalization
    is transient and never supplies source offsets. Policy and passage share
    this observation instead of scanning/preparing assertions again.
    """
    start = 0
    segments: list[tuple[int, int, bool]] = []
    suppressed = False
    while start < len(text):
        end = _SENTENCE_END.search(text, start)
        question = (bool(end and end.group() in {'?', '？'})
                    or bool(_EN_QUESTION.match(text, start))
                    or explicit_qa_marker(text[start:start + SOURCE_TURN_MARKER_PREFIX_CHARS]) == ROLE_INVESTOR
                    or bool(_CN_QUESTION.match(text, start)))
        if question:
            end = _QUESTION_END.search(text, start)
        stop = end.end() if end else len(text)
        if question and _CONFIRMATION_QUESTION.match(text, start) and segments:
            previous_start, previous_stop, _allowed = segments[-1]
            # Explicit backward verification governs only its immediately
            # preceding proposition, not every earlier independent statement.
            segments[-1] = (previous_start, previous_stop, False)
        allowed = not (question or _COURTESY.match(text, start)
                       or _METADATA_STATEMENT.search(text, start, stop))
        segments.append((start, stop, allowed))
        suppressed |= not allowed
        start = stop
    if not suppressed and CAUSAL_LINK.search(text) is None:
        return SourceStatementScope(text, roles)
    normalized = []
    segment_ranges = []
    offset = 0
    for start, stop, allowed in segments:
        raw = text[start:stop]
        segment = matching_reading_text(raw)
        normalized.append(segment)
        segment_ranges.append((offset, offset + len(segment)))
        offset += len(segment)
    value = ''.join(normalized)
    memberships: list[list] = [[] for _ in segments]
    cursor = 0
    statement_index = 0
    for clause in roles.clauses:
        position = value.find(clause.text, cursor)
        if position < 0:
            # The supplied prepared view cannot prove a safe suffix alignment.
            return SourceStatementScope(' ' * len(text), replace(roles, clauses=(),
                bound_operating=False, bound_payload=False), True)
        cursor = position + len(clause.text)
        while (statement_index < len(segment_ranges)
               and segment_ranges[statement_index][1] <= position):
            statement_index += 1
        if (statement_index < len(segment_ranges)
                and segment_ranges[statement_index][0] <= position
                and cursor <= segment_ranges[statement_index][1]):
            memberships[statement_index].append(clause)
    masked = []
    clauses = []
    assertion_keys = set()
    causal_keys: set[str] = set()
    for (start, stop, allowed), segment, members in zip(segments, normalized, memberships):
        cause = CAUSAL_LINK.search(segment)
        if allowed and cause and accounting_text(segment):
            tail = (cause.group('embedded_cause') or segment[cause.end():]).strip()
            # Existing source-owned quantity/direction/action proof has higher
            # authority than generic quote grammar. It owns the cause's full
            # assertion/modality and must not be vetoed by a weaker noun test.
            source_cause = bool(causal_relation and causal_relation(segment))
            business_cause = source_cause or bool(tail and not accounting_text(tail)
                and not _FINANCIAL_CAUSAL_ARGUMENT.search(tail)
                and not abstract_source_argument(tail)
                and (_OBJECT.search(tail) or _STATE_HEAD.search(tail))
                and _CAUSAL_PROCESS.search(tail))
            independent = any(clause.independent_payload is True for clause in members)
            # A separately observed business measurement remains readable even
            # when its causal prelude is unproved. Keep this proof independent:
            # an amount is not evidence that the stated cause is true.
            allowed = independent or business_cause or bool(
                measurement_relation and measurement_relation(segment))
            if business_cause:
                causal_keys.update(clause.text.strip(' \t\r\n.。!?？！;；') for clause in members)
        suppressed |= not allowed
        masked.append(text[start:stop] if allowed else ' ' * (stop-start))
        if allowed:
            clauses.extend(members)
            assertion_keys.add(segment.strip(' \t\r\n.。!?？！;；'))
            assertion_keys.update(clause.text.strip(' \t\r\n.。!?？！;；') for clause in members)
    prepared_roles = (replace(roles, clauses=tuple(clauses), bound_operating=False,
                             bound_payload=False) if suppressed else roles)
    return SourceStatementScope(''.join(masked), prepared_roles, suppressed,
                                frozenset(assertion_keys), frozenset(causal_keys))


def _declarative(text: str, *, causal: bool = False) -> bool:
    """Observe a source statement, not its economic truth or event eligibility."""
    if not any(character.isalpha() for character in text):
        return False
    if (text.rstrip().endswith(('?', '？')) or _EN_QUESTION.match(text)
            or explicit_qa_marker(text) == ROLE_INVESTOR
            or text.lstrip().startswith(('请问', '請問', '是否', '会不会'))
            or _NON_ASSERTION.search(text) or _COURTESY.match(text)
            or _DEPENDENT_SUBJECT.match(text)
            or _VAGUE_OBJECTIVE.search(text) or abstract_source_argument(text)):
        return False
    return bool(causal or _CN_DECLARATION.search(text) or _EN_DECLARATION.search(text))


def prepare_source_passage(
    text: str, roles: SourceAssertionRoles, *, purpose: str, financial_only: bool,
    accounting_text: Callable[[str], bool], non_operating_purposes: frozenset[str],
    existing_use: tuple[str, str], existing_relevant: bool,
    statement_scope: SourceStatementScope | None = None,
) -> SourcePassageCapability:
    """Prepare once; two consumers share the same capability without rescanning.

    A mixed original scope stays verbatim when an independent narrative clause
    is readable. An account-result clause or an account-only causal explanation
    cannot make itself useful just by being grammatical. This never upgrades
    the existing roles, OperatingFact, numeric or issuer-state proof.
    """
    def context(reason: str, *, finance: bool = False):
        return SourcePassageCapability('context_only', reason,
            'financial_context' if finance else 'source_context', False, finance)

    if purpose == 'unassessed':
        return SourcePassageCapability('unresolved', 'source_assessment_incomplete', 'unknown', False)
    if purpose in non_operating_purposes:
        return context('non_operating_purpose')
    if _NON_ASSERTION.search(text):
        return context('source_non_assertion')
    prepared_use = statement_scope is not None
    statement_scope = (statement_scope if statement_scope is not None else
                       prepare_source_statement_scope(text, roles))
    clauses, has_prefix = statement_scope.roles.clauses, statement_scope.suppressed
    if has_prefix and not clauses:
        return context('source_non_assertion')
    if not has_prefix and roles.independent_payload is False:
        return context('source_generic_objective')
    # Preserve the established prepared capability before considering a more
    # general source-quote fallback. It may be proved by a bound relation or a
    # resource/quantity owner rather than a single local clause witness.
    if (prepared_use or not has_prefix) and existing_use[0] == 'support':
        return SourcePassageCapability('support', existing_use[1], 'source_narrative', True)
    if clauses and all(_VAGUE_OBJECTIVE.search(clause.text)
                             or abstract_source_argument(clause.text)
                             for clause in clauses):
        return context('source_generic_objective')
    if (prepared_use or not has_prefix) and existing_use[0] == 'unresolved' and existing_relevant:
        return SourcePassageCapability('unresolved', existing_use[1], 'source_narrative', True)
    readable = False
    finance_seen = financial_only
    for clause in clauses:
        text = clause.text
        if (clause.rule_purpose or clause.independent_payload is False
                or _NON_ASSERTION.search(text)
                or _VAGUE_OBJECTIVE.search(text) or _REFERENCE_METADATA.search(text)):
            continue
        # Presentation belongs to this clause. A different readable operation
        # in the unchanged quote still supplies its own support below.
        account = accounting_text(text) or arithmetic_presentation(text)
        finance_seen |= account
        # Positive role evidence already prepared by the source owner remains
        # valid. Generic readable narration below confers no such proof.
        if clause.independent_payload is True:
            readable = True
        elif not account and _declarative(text):
            readable = True
        elif account:
            if text.strip(' \t\r\n.。!?？！;；') in statement_scope.business_causal_keys:
                readable |= _declarative(text, causal=True)
    if readable:
        if roles.numeric_ambiguous and not roles.operating:
            return SourcePassageCapability('unresolved', 'source_numeric_scope_unresolved',
                                           'source_narrative', True)
        return SourcePassageCapability('support', 'source_readable_narrative',
            'mixed_narrative_context' if finance_seen else 'source_narrative', True)
    if finance_seen:
        return context('financial_only', finance=True)
    return SourcePassageCapability('unresolved', 'source_passage_incomplete', 'unknown', False)
