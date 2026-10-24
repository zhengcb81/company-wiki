"""One transient metric-assertion owner for source modality and measured time.

Quantity/rate and revenue-outlook projections consume this same observation.
Offsets refer only to the caller's bounded classification text, never original
source coordinates. No values, periods, actors or evidence are manufactured.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

Mode = Literal["actual", "expected", "planned", "conditional", "negative", "uncertain", "referenced"]
Period = Literal["past", "current", "future", "unspecified"]

# Independent assertion boundaries preserve numeric commas and coordinated
# noun phrases (e.g. research and development). A separate actor after and/but
# or an explicit while/whereas clause cannot donate its predicate to a metric.
_SENTENCE = re.compile(r"[。！？;；!?]|(?<=[.!?])\s+")
_BOUNDARY = re.compile(
    r"(?<!\d)[,，]|[,，](?!\d)|\b(?:while|whereas)\b|"
    r"\b(?:and|but|yet)\s+(?=(?:we|our|their|they|it|the|this|that)\b)|"
    r"但是|但(?=本?公司|集团|我们)|而(?=本?公司|本?集团|收入|营收)|"
    r"并且(?=本?公司|本?集团|我们)", re.I)

# The single vocabulary describes predicate modality for every metric owner.
# Consumers must not maintain their own expect/anticipate/goal/negative lists.
_MODAL = re.compile(
    r"(?P<conditional>假设|假定|假如|如果|若(?!干)|\b(?:if|unless|assuming)\b|"
    r"\bassumptions?\s+(?:that|of)\b)|"
    r"(?P<negative>尚未|未能|没有|并未|不曾|不是|不明|"
    r"\b(?:not|never|unknown|don't|doesn't|didn't|can't|cannot|isn't|aren't|wasn't|weren't)\b)|"
    r"(?P<uncertain>是否|可能|\b(?:may|might|could|would|whether|uncertain|unclear)\b)|"
    r"(?P<expected>预计|预期|预测|有望|展望|指引|"
    r"\b(?:expects?|expected|expecting|anticipat\w*|forecast\w*|"
    r"project(?:s|ed|ing)?|predict\w*|estimat\w*|outlook|guidance)\b)|"
    r"(?P<planned>计划|拟|目标|力争|(?<!已)(?<!已经)将|"
    r"\b(?:plans?|planned|aims?|targets?|hopes?|seeks?|will)\b)", re.I)
_FUTURE_PERIOD = re.compile(
    r"未来|明年|下一(?:年(?:度)?|季度|月)|"
    r"\b(?:future|next|upcoming)\s+(?:year|quarter|month|period|years|quarters|months|periods)\b|"
    r"\b(?:tomorrow|thereafter)\b", re.I)
_FUTURE_FRAME = re.compile(
    r"^\s*(?:明年(?:度)?|下一(?:年(?:度)?|季度|月)|"
    r"未来(?:(?:\d+|[一二三四五六七八九十]+)?(?:年|季度|月))?|"
    r"(?:next|upcoming)\s+(?:year|quarter|month))\s*[,，]", re.I)
_PAST_PERIOD = re.compile(
    r"去年|上年(?:度)?|上(?:一)?季度|上(?:个)?月|上期|此前|之前|前期|"
    r"\b(?:last|previous|prior|preceding|past)\s+(?:year|quarter|month|period)\b", re.I)
_COMPARISON = re.compile(
    r"(?:compared\s+(?:with|to)|relative\s+to|versus|than)\s+(?:the\s+)?$|(?:较|比)\s*$", re.I)
_CURRENT_PERIOD = re.compile(r"本期|报告期|本年度|\b(?:currently|reporting\s+period|this\s+(?:year|quarter|month))\b", re.I)
_PRIOR_COMPLETION = re.compile(r"\bto\s+have\s+\w+\b", re.I)
_DISCLOSURE_ACTION = re.compile(
    r"^\s*(?:(?:to|be)\s+)?(?:announce|report|publish|disclose|release|present)\b|"
    r"^\s*(?:公布|披露|发布|公告)", re.I)
_NOMINAL_PROJECT = re.compile(
    r"\b(?:our|the|this|that|a|an|new|its|their|total)\s+"
    r"(?:[a-z]+(?:ed|ing|est)\s+){0,4}$|"
    r"\b\d[\d,.]*\s+(?:(?:thousand|million|billion)\s+)?$", re.I)
_PROJECT_NOUN_PREDICATE = re.compile(
    r"^\s+(?:(?:has|have|had)\s+)?"
    r"(?:[a-z]+ed|stood|stands|grew|grown|rose|risen|fell|fallen|"
    r"is|are|was|were|has|have|had|total(?:s|ing|ling|ed|led)?)\s+"
    r"(?:(?:at|to|from|by)\s+)?(?=\d)", re.I)
_PROJECT_VERBAL_COMPLEMENT = re.compile(r"^\s*(?:that\b|\d)", re.I)
_LEADING_HYPOTHESIS = re.compile(
    r"(?:^|[,，])\s*(?:on|under|given|based\s+on)\s+(?:(?:an?|the)\s+)?"
    r"assumptions?\s+(?:that|of)\b", re.I)
_REFERENCED_VALUE = re.compile(r"\b(?:below|above|versus|against)\s+(?:(?:the|our|its|previous|prior)\s+)*$", re.I)


@dataclass(frozen=True)
class PredicateObservation:
    scope_start: int
    scope_end: int
    modality: Mode
    period: Period
    cue_start: int | None = None
    cue_end: int | None = None
    has_condition: bool = False

    @property
    def observed(self) -> bool:
        return self.modality == "actual" and self.period != "future" and not self.has_condition

    @property
    def forward_outlook(self) -> bool:
        return (self.modality in {"expected", "planned"} and self.period != "past"
                or self.modality == "actual" and self.period == "future")


def predicate_scope(text: str, start: int, end: int) -> tuple[int, int]:
    """Bound the target assertion, not a bag of predicates in one sentence."""
    left, right = 0, len(text)
    for delimiter in (*_SENTENCE.finditer(text), *_BOUNDARY.finditer(text)):
        if delimiter.end() <= start:
            left = max(left, delimiter.end())
        elif delimiter.start() >= end:
            right = min(right, delimiter.start())
    return left, right


def observe_metric_predicate(text: str, start: int, end: int) -> PredicateObservation:
    """Describe this metric's predicate and period in one bounded source view."""
    if not 0 <= start < end <= len(text):
        raise ValueError("metric target is outside classification text")
    left, right = predicate_scope(text, start, end)
    local = text[left:right]
    sentence_start = max((m.end() for m in _SENTENCE.finditer(text[:left])), default=0)
    prior = text[sentence_start:left]
    future = bool(_FUTURE_PERIOD.search(local) or _FUTURE_FRAME.match(prior))
    past = any(not _COMPARISON.search(local[:m.start()]) for m in _PAST_PERIOD.finditer(local))
    period: Period = ("past" if past else "future" if future else
                      "current" if _CURRENT_PERIOD.search(local) else "unspecified")
    modal: list[tuple[Mode, int, int]] = []
    for marker in _MODAL.finditer(local):
        a, b = left + marker.start(), left + marker.end()
        kind = marker.lastgroup
        assert kind is not None
        if marker.group().casefold() in {"project", "projects"}:
            # A quantified/possessed project or a project with its own stock/
            # change predicate is the measured noun, not a forecast verb.
            # The source's grammar supplies this distinction, not its issuer
            # or a list of example sentences.
            if (_NOMINAL_PROJECT.search(text[left:a])
                    or _PROJECT_NOUN_PREDICATE.match(text[b:right])):
                continue
            if a < end and start < b:
                # The metric's own noun cannot be its governing forecast
                # verb. Conversely "we project 619 customers" contains a
                # verbal complement: that project token is not a measured
                # project stock at all, even though a lexical metric matcher
                # can see it. The separate customer target still observes
                # the actual preceding forecast predicate below.
                if _PROJECT_VERBAL_COMPLEMENT.match(text[b:right]):
                    modal.append(("referenced", a, b))
                continue
        if kind == "planned" and marker.group().casefold() == "will" and a < start:
            if _DISCLOSURE_ACTION.match(text[b:start]):
                modal.append(("referenced", a, b))
                continue
        # Named groups correspond to the closed internal Mode vocabulary.
        mode: Mode
        if kind == "conditional":
            mode = "conditional"
        elif kind == "negative":
            mode = "negative"
        elif kind == "uncertain":
            mode = "uncertain"
        elif kind == "planned":
            mode = "planned"
        else:
            mode = "expected"
        modal.append((mode, a, b))
    # A condition qualifies the metric assertion. It does not replace a real
    # expectation with an actual fact, or let a customer's negative predicate
    # inside the condition negate the issuer's outer forecast predicate.
    leading_condition = next((m for m in _MODAL.finditer(prior)
        if m.lastgroup == "conditional" and (
            not m.group().casefold().startswith("assumption")
            or _LEADING_HYPOTHESIS.search(prior))), None)
    conditions = [m for m in modal if m[0] == "conditional"]
    has_condition = bool(conditions or leading_condition)
    condition_start = min((m[1] for m in conditions if m[1] >= end), default=right)
    governing = [m for m in modal if m[1] < condition_start and m[0] != "conditional"]
    for mode in ("negative", "uncertain"):
        chosen = next((m for m in governing if m[0] == mode), None)
        if chosen is not None:
            return PredicateObservation(left, right, chosen[0], period, chosen[1], chosen[2], has_condition)
    if _REFERENCED_VALUE.search(text[left:start]):
        return PredicateObservation(left, right, "referenced", period, has_condition=has_condition)
    if governing:
        # An outer expectation keeps the assertion's actor when its target
        # also carries an inner future auxiliary (expect revenue will ...).
        # Separate subjects/actions have already ended the assertion above.
        outer = [m for m in governing if m[0] in {"expected", "planned"} and m[1] < start]
        mode, a, b = (min(outer, key=lambda m: m[1]) if outer else
                      min(governing, key=lambda m: min(abs(m[1]-start), abs(m[2]-end))))
        if period != "future" and mode == "expected" and _PRIOR_COMPLETION.search(local):
            period = "past"
        return PredicateObservation(left, right, mode, period, a, b, has_condition)
    if has_condition:
        return PredicateObservation(left, right, "conditional", period, has_condition=True)
    return PredicateObservation(left, right, "actual", period)
