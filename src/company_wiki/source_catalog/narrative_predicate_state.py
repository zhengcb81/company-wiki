"""One transient metric-assertion owner for source modality and measured time.

Quantity/rate and revenue-outlook projections consume this same observation.
Offsets refer only to the caller's bounded classification text, never original
source coordinates. No values, periods, actors or evidence are manufactured.
"""
from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left, bisect_right
from heapq import merge
import re
from typing import Literal, cast

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
    r"(?P<negative>尚未|未能|没有|沒有|并未|並未|并非|並非|不曾|不是|不明|暂无|暫無|并无|並無|"
    r"不(?=计划|計劃|拟|擬|打算)|\bno\s+(?:(?:current|immediate|present)\s+)?plans?\b|"
    r"\b(?:not|never|unknown|don't|doesn't|didn't|can't|cannot|isn't|aren't|wasn't|weren't)\b)|"
    r"(?P<uncertain>是否|可能|\b(?:may|might|could|would|whether|uncertain|unclear)\b)|"
    r"(?P<expected>预计|预期|预测|有望|展望|指引|"
    r"\b(?:expects?|expected|expecting|anticipat\w*|forecast\w*|"
    r"project(?:s|ed|ing)?|predict\w*|estimat\w*|outlook|guidance)\b)|"
    r"(?P<planned>计划|計劃|拟|擬|目标|目標|力争|力爭|(?<!已)(?<!已经)(?<!已經)[将將]|"
    r"\b(?:plans?|planned|aim(?:s|ed|ing)?|targets?|hopes?|seeks?|will)\b)", re.I)
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
_INFINITIVE_PREFIX = re.compile(
    r"\bto\s+(?:(?:further|significantly|substantially)\s+)?"
    r"(?:[a-z]+\s+(?:(?:the|our|their|its|total|active|paid|licensed|new|average)\s+)*)?$", re.I)
_ACTUAL_INFINITIVE_CONTROL = re.compile(
    r"\b(?:continued?|continues?|began|begins?|started|starts?|managed|manages?)\s+to\s+"
    r"(?:[a-z]+\s+)?(?:(?:the|our|their|its|total|active|paid|new|average)\s+)*$", re.I)
_PREPOSITION_TO = re.compile(r"\b(?:due|owing|attributable|related|according|pursuant|subject|exposed)\s+to\s*$", re.I)
_PURPOSE_CHANGE = re.compile(r"\bto\s+(?:(?:further|significantly|substantially)\s+)?"
    r"(?P<verb>improve|increase|decrease|grow|reduce|expand|raise|lower|boost|cut|enhance|strengthen)\b", re.I)


def purpose_infinitive(text: str, target_start: int, scope_start: int = 0) -> bool:
    """Bounded local purpose/control syntax, never a new modality word list."""
    prefix = text[max(scope_start, target_start-80):target_start]
    return bool(_INFINITIVE_PREFIX.search(prefix) and not _ACTUAL_INFINITIVE_CONTROL.search(prefix)
                and not _PREPOSITION_TO.search(prefix))
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


# These contextual recognizers are derived from the same grammar, not a second
# modality vocabulary. Each scans an assertion once during preparation.
_COMPARATIVE_PAST = re.compile(
    "(?:" + _COMPARISON.pattern.replace("$", "") + ")(?=" + _PAST_PERIOD.pattern + ")", re.I)
_NOMINAL_PROJECT_PAIR = re.compile(
    "(?:" + _NOMINAL_PROJECT.pattern.replace("$", "") + r")(?=\bprojects?\b)", re.I)
_PROJECT_NOUN_PAIR = re.compile(
    r"\bprojects?\b(?=" + _PROJECT_NOUN_PREDICATE.pattern.removeprefix("^") + ")", re.I)
_PROJECT_VERBAL_PAIR = re.compile(
    r"\bprojects?\b(?=" + _PROJECT_VERBAL_COMPLEMENT.pattern.removeprefix("^") + ")", re.I)
_WILL_DISCLOSURE = re.compile(
    r"\bwill\b(?:" + _DISCLOSURE_ACTION.pattern.replace("^", "") + ")", re.I)
_REFERENCE_PHRASE = re.compile(_REFERENCED_VALUE.pattern.removesuffix("$"), re.I)
_SPACE = re.compile(r"\s+")


class _Tokens:
    """An ordered modal index; a query inspects at most six neighbors."""

    def __init__(self, pairs=()):
        self.pairs = tuple(pairs)
        self.starts = tuple(a for a, _ in self.pairs)
        self.ends = tuple(b for _, b in self.pairs)

    def candidates(self, mode, start, end, stop, lower=0, upper=None):
        upper = min(len(self.pairs) if upper is None else upper,
                    bisect_left(self.starts, stop))
        if lower >= upper:
            return []
        indices = {lower, upper - 1}
        for positions, point in ((self.starts, start), (self.ends, end)):
            near = bisect_left(positions, point, lower, upper)
            indices.update(i for i in (near - 1, near) if lower <= i < upper)
        return [(mode, *self.pairs[i]) for i in sorted(indices)]


class _Assertion:
    """Prepared local grammar, independent of the number of metric queries."""

    def __init__(self, text, left, right, *, future_frame=False, leading_condition=False):
        self.left, self.right = left, right
        local = text[left:right]
        self.purpose_cues = tuple((left+m.start(), left+m.start('verb'))
            for m in _PURPOSE_CHANGE.finditer(local)
            if purpose_infinitive(text, left+m.start('verb'), left))
        self.purpose_starts = tuple(end for _, end in self.purpose_cues)
        markers = tuple(_MODAL.finditer(local))
        future = bool(_FUTURE_PERIOD.search(local) or future_frame)
        past_markers = tuple(_PAST_PERIOD.finditer(local))
        comparative = {m.end() for m in _COMPARATIVE_PAST.finditer(local)} if past_markers else set()
        past = any(m.start() not in comparative for m in past_markers)
        self.period: Period = ("past" if past else "future" if future else
                       "current" if _CURRENT_PERIOD.search(local) else "unspecified")
        self.prior_completion = bool(any(m.lastgroup == "expected" for m in markers)
                                     and _PRIOR_COMPLETION.search(local))
        has_project = any(m.group().casefold() in {"project", "projects"} for m in markers)
        nominal, verbal = set(), set()
        if has_project:
            nominal = {m.end() for m in _NOMINAL_PROJECT_PAIR.finditer(local)}
            nominal.update(m.start() for m in _PROJECT_NOUN_PAIR.finditer(local))
            verbal = {m.start() for m in _PROJECT_VERBAL_PAIR.finditer(local)}
        disclosure = ({m.start(): left + m.end() for m in _WILL_DISCLOSURE.finditer(local)}
                      if any(m.group().casefold() == "will" for m in markers) else {})
        groups: dict[str, list[tuple[int, int]]] = {}
        self.mask_spans = []
        self.conditions = []
        self.leading_condition = leading_condition
        self.non_assumption_condition = False
        self.assumption_condition = False
        self.disclosure_ends = []
        for marker in markers:
            a, b = left + marker.start(), left + marker.end()
            # Every _MODAL alternative is named; successful matches cannot
            # have an absent group name. This cast does not alter matching.
            mode = cast(str, marker.lastgroup)
            word = marker.group().casefold()
            if word in {"project", "projects"}:
                if marker.start() in nominal:
                    continue
                mode = "verbal_project" if marker.start() in verbal else "project"
            elif mode == "planned" and word == "will" and marker.start() in disclosure:
                mode = "will_disclose"
                self.disclosure_ends.append(disclosure[marker.start()])
            if mode == "conditional":
                self.conditions.append(a)
                if word.startswith("assumption"):
                    self.assumption_condition = True
                else:
                    self.non_assumption_condition = True
            else:
                self.mask_spans.append((a, b))
            groups.setdefault(mode, []).append((a, b))
        self.tokens = {mode: _Tokens(pairs) for mode, pairs in groups.items()}
        references: list[tuple[int, int]] = []
        for phrase in _REFERENCE_PHRASE.finditer(local):
            references.extend((left + phrase.start() + gap.start() + 1,
                               left + phrase.start() + gap.end())
                              for gap in _SPACE.finditer(phrase.group()))
        self.references = tuple(references)
        self.reference_starts = tuple(a for a, _ in references)

    def observe(self, start, end):
        left, right = self.left, self.right
        period: Period = self.period
        condition_index = bisect_left(self.conditions, end)
        stop = self.conditions[condition_index] if condition_index < len(self.conditions) else right
        has_condition = bool(self.conditions or self.leading_condition)
        for mode in ("negative", "uncertain"):
            index = self.tokens.get(mode)
            if index and index.starts[0] < stop:
                a, b = index.pairs[0]
                return PredicateObservation(left, right, mode, period, a, b, has_condition)
        ref = bisect_right(self.reference_starts, start) - 1
        if ref >= 0 and start <= self.references[ref][1]:
            return PredicateObservation(left, right, "referenced", period, has_condition=has_condition)
        candidates = []
        for mode, index in self.tokens.items():
            if mode == "conditional":
                continue
            if mode in {"project", "verbal_project"}:
                # A project token overlapping the metric is not its forecast
                # predicate. The same token can still govern another metric.
                before = bisect_right(index.ends, start)
                after = bisect_left(index.starts, end)
                candidates.extend(index.candidates("expected", start, end, stop, upper=before))
                candidates.extend(index.candidates("expected", start, end, stop, lower=after))
                if mode == "verbal_project":
                    candidates.extend(index.candidates("referenced", start, end, stop, before, after))
            elif mode == "will_disclose":
                disclosed = bisect_right(self.disclosure_ends, start)
                candidates.extend(index.candidates("referenced", start, end, stop, upper=disclosed))
                candidates.extend(index.candidates("planned", start, end, stop, lower=disclosed))
            else:
                candidates.extend(index.candidates(mode, start, end, stop))
        if candidates:
            outer = [m for m in candidates if m[0] in {"expected", "planned"} and m[1] < start]
            mode, a, b = (min(outer, key=lambda m: m[1]) if outer else
                          min(candidates, key=lambda m: (min(abs(m[1]-start), abs(m[2]-end)), m[1])))
            if period != "future" and mode == "expected" and self.prior_completion:
                period = "past"
            return PredicateObservation(left, right, mode, period, a, b, has_condition)
        if has_condition:
            return PredicateObservation(left, right, "conditional", period, has_condition=True)
        purpose = bisect_right(self.purpose_starts, start)-1
        if purpose >= 0:
            a, b = self.purpose_cues[purpose]
            return PredicateObservation(left, right, "planned", period, a, b)
        return PredicateObservation(left, right, "actual", period)


class PreparedPredicateContext:
    """One bounded source view with reusable assertion and modal indexes.

    Construction scans disjoint assertions, not the source prefix per metric.
    Queries inside a prepared assertion use binary searches and a fixed number
    of modal neighbors. No regex runs again, even for many hits in one clause.
    """

    def __init__(self, text):
        self.text = text
        sentences = tuple((m.start(), m.end()) for m in _SENTENCE.finditer(text))
        assertions = tuple((m.start(), m.end()) for m in _BOUNDARY.finditer(text))
        self.boundaries = tuple(merge(sentences, assertions))
        self.starts = tuple(a for a, _ in self.boundaries)
        self.ends = tuple(sorted(b for _, b in self.boundaries))
        sentence_ends = (0, *(b for _, b in sentences))
        sentence_starts = (*(a for a, _ in sentences), len(text))
        frames = {}
        hypotheses = {}
        for left, right in zip(sentence_ends, sentence_starts):
            sentence = text[left:right]
            frame = _FUTURE_FRAME.match(sentence)
            frames[left] = left + frame.end() if frame else None
            hypotheses[left] = tuple(left + m.end() for m in _LEADING_HYPOTHESIS.finditer(sentence))
        spans = []
        left = 0
        for a, b in self.boundaries:
            if a > left:
                spans.append((left, a))
            left = max(left, b)
        if left < len(text):
            spans.append((left, len(text)))
        self.assertion_spans = tuple(spans)
        self._assertions = {}
        sentence_left = None
        non_assumption = assumption = False
        for left, right in spans:
            current = sentence_ends[bisect_right(sentence_ends, left) - 1]
            if current != sentence_left:
                non_assumption = assumption = False
                sentence_left = current
            frame_end = frames[current]
            leading = non_assumption or assumption and bool(
                hypotheses[current] and hypotheses[current][0] <= left)
            prepared = _Assertion(text, left, right,
                                  future_frame=frame_end is not None and frame_end <= left,
                                  leading_condition=leading)
            self._assertions[left, right] = prepared
            non_assumption |= prepared.non_assumption_condition
            assumption |= prepared.assumption_condition

    def scope(self, start, end):
        left_index = bisect_right(self.ends, start) - 1
        right_index = bisect_left(self.starts, end)
        return (self.ends[left_index] if left_index >= 0 else 0,
                self.starts[right_index] if right_index < len(self.starts) else len(self.text))

    def observe(self, start, end):
        if not 0 <= start < end <= len(self.text):
            raise ValueError("metric target is outside classification text")
        scope = self.scope(start, end)
        prepared = self._assertions.get(scope)
        if prepared is None:
            # Public callers can explicitly bind a target spanning delimiters.
            # Preserve that behavior; production repeated queries are bounded
            # by assertion_spans and never enter this compatibility fallback.
            left, right = scope
            first = next((v for (a, _), v in self._assertions.items() if a == left), None)
            prepared = _Assertion(self.text, left, right,
                                  leading_condition=bool(first and first.leading_condition),
                                  future_frame=bool(first and first.period == "future"))
            self._assertions[scope] = prepared
        return prepared.observe(start, end)

    def modality_view(self):
        """Equal-length grammar view; never changes source text or evidence.

        Resource binders can bridge auxiliaries without copying this owner's
        vocabulary. Interpretation still uses original offsets and modality.
        """
        chars = list(self.text)
        for prepared in self._assertions.values():
            for left, right in prepared.mask_spans:
                chars[left:right] = " " * (right - left)
        return "".join(chars)


def prepare_predicate_context(text: str) -> PreparedPredicateContext:
    return PreparedPredicateContext(text)


def predicate_scope(text: str, start: int, end: int) -> tuple[int, int]:
    """Bound the target assertion, not a bag of predicates in one sentence."""
    # The single-target compatibility API retains its inexpensive boundary-only
    # behavior. Multi-target owners prepare one context instead.
    left, right = 0, len(text)
    for delimiter in merge(_SENTENCE.finditer(text), _BOUNDARY.finditer(text), key=lambda m: m.start()):
        if delimiter.end() <= start:
            left = max(left, delimiter.end())
        elif delimiter.start() >= end:
            right = min(right, delimiter.start())
    return left, right


def split_predicate_assertions(text: str) -> tuple[str, ...]:
    """Reuse assertion grammar; preserve numeric commas and coordinated nouns."""
    return tuple(part for part in _BOUNDARY.split(text) if part.strip())


def observe_metric_predicate(text: str, start: int, end: int) -> PredicateObservation:
    """Compatibility entry point for a single source metric observation."""
    if not 0 <= start < end <= len(text):
        raise ValueError("metric target is outside classification text")
    left, right = predicate_scope(text, start, end)
    sentence_start = max((m.end() for m in _SENTENCE.finditer(text[:left])), default=0)
    prior = text[sentence_start:left]
    leading = any(m.lastgroup == "conditional" and (
        not m.group().casefold().startswith("assumption") or _LEADING_HYPOTHESIS.search(prior))
        for m in _MODAL.finditer(prior))
    return _Assertion(text, left, right, future_frame=bool(_FUTURE_FRAME.match(prior)),
                      leading_condition=leading).observe(start, end)
