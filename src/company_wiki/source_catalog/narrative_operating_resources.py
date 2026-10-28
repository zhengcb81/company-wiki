"""Finite source resource observations for the production reading projection.

These are uses of unchanged prose, not extracted financial accounts, issuer
identity, or achieved operating milestones. Legacy text selectors never call
this observer. Predicate modality/time has exactly one existing owner.
"""
from __future__ import annotations

import re
from itertools import chain

from .narrative_business_meaning import _CLAUSES, _GENERIC_DEFINITION
from .narrative_predicate_state import (
    PredicateObservation, prepare_predicate_context,
)
from .narrative_source_purpose import NON_OPERATING_PURPOSES, source_purpose


# One call per already bounded source owner, charged before projection. This
# covers clause construction, the fixed recognizer passes and predicate scans;
# there is no per-match rescan of the entire original document.
RESOURCE_READING_SCAN_PASSES = 18
_RESEARCH = r"(?:技术)?研发|研究开发|\b(?:R\s*&\s*D|research(?:\s+and\s+development)?)\b"
_WORKFORCE = (
    r"(?:(?:研发|研究|技术|软件)(?:中心|实验室)?(?:的)?(?:员工|人员|团队)|"
    r"(?:软件|研发|技术)?工程师)(?:总数|数量|人数)?|"
    r"\b(?:(?:R\s*&\s*D|research(?:\s+and\s+development)?|development|"
    r"software|engineering|technical)\s+)(?:(?:cent(?:er|re)|laboratory)\s+)?"
    r"(?:staff|team|personnel|employees|engineers|researchers)\b"
)
_NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"
_PERSONS = r"(?:人|名|\b(?:people|persons?|employees|staff|engineers|researchers)\b)"
_COUNT = re.compile(
    r"(?P<metric>" + _WORKFORCE + r")\s*(?:\b(?:headcount|count|number)\s+)?"
    r"(?:[（(][^()（）;；。!?]{0,96}[)）]\s*)?"
    r"(?:(?:已经|已|总计|合计|达到|达|为|超过|约为|超|逾|增加至|提升至)|"
    r"\b(?:has|have|had|already|now|currently|numbered|numbers?|totaled|totalled|"
    r"totals?|was|were|is|are|reached|reach|of|to|over|approximately|about|nearly)\b|\s)*"
    r"(?P<quantity>" + _NUMBER + r")\s*(?:万|thousand\s+)?(?P<unit>" + _PERSONS + r")", re.I)
_EMPLOYED = re.compile(
    r"\b(?:employed|employs?|employing)\s+(?P<quantity>" + _NUMBER + r")\s+"
    r"(?P<metric>(?:software|research|development|technical)\s+(?:engineers|staff|personnel))\b", re.I)
_CURRENCY = r"(?:人民币|港币|美元|USD|RMB|CNY|HKD|US\$|[$¥€£])"
_MONEY = (r"(?:" + _CURRENCY + r"\s*" + _NUMBER +
          r"\s*(?:百万元|千万元|亿元|万元|元|billion\b|million\b|thousand\b)?|" +
          _NUMBER + r"\s*(?:百万元|千万元|亿元|万元|元|(?:million|billion|thousand)\s+dollars\b))")
_INVESTED = re.compile(
    r"(?P<action>投入|投资|\b(?:invested|invests?|investing|allocated|allocates?|allocating|spent)\b)"
    r"\s*(?:了|为|约|approximately\s+|about\s+)?(?P<quantity>" + _MONEY + r")\s*"
    r"(?:用于|用作|进行|于|到|\b(?:in|into|on|to|for)\b)\s*(?:技术)?"
    r"(?P<resource>" + _RESEARCH + r")", re.I)
_RESEARCH_ALLOCATION = re.compile(
    r"(?P<resource>" + _RESEARCH + r")\s*(?:投入|投资|\binvestment\b)\s*"
    r"(?:为|达|达到|约为|\b(?:was|were|is|of|totaled|totalled)\b)\s*"
    r"(?P<quantity>" + _MONEY + r")", re.I)
_RESOURCE_ACTION = re.compile(
    r"(?:投入|投资)(?:更多(?:的)?资源(?:于|到)?|更多)?\s*(?:技术)?(?:研发|研究开发)|"
    r"\b(?:invest(?:s|ed|ing)?\s+(?:(?:more|further)\s+)?(?:in|into)|"
    r"allocat(?:e|es|ed|ing)\s+(?:(?:more|additional|our)\s+)?"
    r"(?:resources|capital|funding)\s+(?:to|for))\s+(?:our\s+)?(?:" + _RESEARCH + r")|"
    r"(?:提升|加强|扩充|建设)(?:我们的)?(?:人工智能|AI|云计算|研发|技术研发)能力|"
    r"\b(?:enhance|enhancing|strengthen|strengthening|build|building)\s+"
    r"(?:our\s+)?(?:AI|artificial intelligence|research|cloud computing)\s+capabilities\b", re.I)
_ACTOR = re.compile(r"本公司|公司|本集团|集团|我们|\b(?:we|our|the\s+(?:company|group))\b", re.I)
_CONTINUATION = re.compile(
    r"^\s*(?:(?:并且|并|且|同时|不断|持续|继续|全面|进一步|积极)\s*|"
    r"\b(?:and|also|continuously|further|continue|continuing)\s+)*$", re.I)
_QUESTION_OR_EXAMPLE = re.compile(r"[?？]|请问|例如|示例|是指|定义为|\b(?:for example|e\.g\.|defined as|will\s+you)\b", re.I)


def _projection(state: PredicateObservation, actual: str) -> str | None:
    if state.observed:
        return actual
    if state.forward_outlook:
        return "operating_plan"
    return None


def operating_resource_relations(text: str) -> tuple[str, ...]:
    """Observe only closed resource predicates in the caller's matching view.

    The number, units, roles and qualifiers remain in the original source;
    nothing here converts a value or assigns a resource to an inferred issuer.
    A plan frame may govern a subsequent coordinated action, but never a new
    subject, a standalone quantity, or a separate source sentence.
    """
    reasons: list[str] = []
    sentence_start = 0
    for boundary in chain(_CLAUSES.finditer(text), (None,)):
        sentence_end = boundary.start() if boundary is not None else len(text)
        sentence = text[sentence_start:sentence_end]
        sentence_start = boundary.end() if boundary is not None else len(text)
        # Retain the question terminator until classification. Splitting it
        # away first would turn an analyst question into a company's plan.
        if boundary is not None and any(char in boundary.group() for char in "?？"):
            continue
        inherited: PredicateObservation | None = None
        context = prepare_predicate_context(sentence)
        matching = context.modality_view()
        for start, cursor in context.assertion_spans:
            part = sentence[start:cursor]
            if not part.strip():
                continue
            if (_QUESTION_OR_EXAMPLE.search(part) or _GENERIC_DEFINITION.search(part)
                    or source_purpose(part) in NON_OPERATING_PURPOSES):
                inherited = None
                continue
            actor = _ACTOR.search(part)
            action = _RESOURCE_ACTION.search(part)
            coordinated = bool(action and _CONTINUATION.fullmatch(part[:action.start()]))
            frame = context.observe(start, cursor)
            if actor is not None:
                inherited = frame if frame.forward_outlook else None
            elif not coordinated:
                inherited = None
            # A fixed number of complete subject/predicate patterns is checked
            # once per assertion. An irrelevant first noun cannot donate money
            # or a manual/identifier number through an unbounded gap.
            for pattern, actual in ((_COUNT, "operating_resource_stock"),
                                    (_EMPLOYED, "operating_resource_stock"),
                                    (_INVESTED, "operating_resource_allocation"),
                                    (_RESEARCH_ALLOCATION, "operating_resource_allocation")):
                match = pattern.search(matching[start:cursor] if pattern is _COUNT else part)
                if match is None:
                    continue
                state = context.observe(start + match.start(), start + match.end())
                reason = _projection(state, actual)
                if reason is not None:
                    reasons.append(reason)
            if action is not None:
                state = context.observe(start + action.start(), start + action.end())
                # Only a direct same-actor continuation may inherit a plan.
                # Explicit negative/uncertain/referenced predicates win first.
                if coordinated and state.observed and inherited is not None:
                    state = inherited
                if (actor is not None or coordinated and inherited is not None) and state.forward_outlook:
                    reasons.append("operating_plan")
    return tuple(dict.fromkeys(reasons))
