"""Pure source revenue outlooks and explicit local premise references.

This owner observes words, never forecasts values or changes source locators.
The reading policy projects a reason/purpose; the source session separately
requires real native adjacency before it can publish a dependency edge.
"""
from __future__ import annotations

import re

from company_wiki.document_normalization.text_matching import matching_reading_text

from .narrative_predicate_state import observe_metric_predicate

_REVENUE = re.compile(r"收入|营收|營收|\b(?:revenues?|net\s+sales)\b", re.I)
_ISSUER_SUBJECT = re.compile(r"\s*(?:we|(?:the|this|our)\s+(?:company|group)|"
                             r"本公司|公司|本集团|本集團|集团|集團|我们|我們)\s*", re.I)
_YEAR_ONLY_PREFIX = re.compile(r"\s*(?:(?:19|20)\d{2}(?:年度?|年)?\s*)?", re.I)
_EXPLICIT_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_ISSUER_METRIC = re.compile(r"^\s*(?:our\b|(?:the|this)\s+(?:company|group)['’]s\b|"
                            r"(?:本公司|公司|本集团|本集團|集团|集團)(?:的)?)", re.I)
_PERIOD_ISSUER_AFTER_EXPECTED = re.compile(
    r"\s*(?:(?:19|20)\d{2}(?:年度?|年)\s*)?"
    r"(?:本公司|本集团|本集團|公司|集团|集團|我们|我們)"
    r"(?:的)?(?:整体|總體|总体|全年|年度)?\s*", re.I)
_UNIT = r"(?:[%％]|percent\b|亿元|億元|万元|萬元|亿|億|万|萬|元|港元|美元|"
_UNIT += r"billion\b|million\b|thousand\b|dollars?\b|USD\b|HKD\b|CNY\b|RMB\b)"
_CURRENCY = r"(?:USD\b|HKD\b|CNY\b|RMB\b|GBP\b|EUR\b|人民币|人民幣|港币|港幣|美元|[$€£¥])"
_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_RANGE = r"(?:\s*(?:to|through|and|至|到|[-–—~～])\s*(?:" + _CURRENCY + r"\s*)?" + _NUMBER + r")?"
_VALUE = re.compile(r"(?:" + _CURRENCY + r"\s*" + _NUMBER + _RANGE + r"(?:\s*" + _UNIT + r")?|"
                    + _NUMBER + _RANGE + r"\s*" + _UNIT + r")", re.I)
_OTHER_METRIC = re.compile(r"利润|利潤|成本|税|稅|\b(?:profit|margin|costs?|tax|expenses?)\b", re.I)
_SENTENCE = re.compile(r"[。！？;；!?]|(?<=[a-zA-Z])\.(?:\s+|$)")
_REFERENCE = re.compile(
    r"^\s*(?P<reference>the\s+above|the\s+following|aforementioned|this|that|above|following|"
    r"上述|该|該|此|以下|下述|下列)\s*"
    r"(?:(?:提及|所述|提到)的?\s*)?"
    r"(?:(?P<scope>[^。！？;；.!?]{0,65}?)(?:收入|营收|營收|经营业绩|業績|\brevenues?\b)\s*)?"
    r"(?:指引|展望|预期|預期|预测|預測|目标|目標|\b(?:outlook|guidance|forecast|target)\b)", re.I)
_PREMISE = re.compile(
    r"^\s*(?:(?:assumes?|requires?|depends?\s+(?:on|upon))\b|"
    r"(?:(?:is|are)\s+)?(?:based\s+on|conditional\s+on|subject\s+to)\b|"
    r"假设|假設|假定|基于|基於|取决于|取決於|以[^。！？;；.!?]+(?:为前提|為前提|为基础|為基礎))", re.I)
_GENERIC_SCOPE = re.compile(
    r"\b(?:our|the|business|segment|annual|full.year|fiscal|FY)\b|"
    r"业务|業務|分部|全年|经营|經營|业绩|業績|(?:19|20)\d{2}年?|\s+", re.I)
_FOLLOWING = frozenset({"the following", "following", "以下", "下述", "下列"})


def revenue_guidance(text: str, *, issuer_only: bool = False) -> bool:
    """Observe a future revenue amount/range/rate within its own assertion.

    A cue after an already stated actual amount cannot retroactively turn that
    amount into a forecast. Numbers require a literal currency/unit, not years.
    """
    value = matching_reading_text(text)
    for clause in _SENTENCE.split(value):
        for revenue in _REVENUE.finditer(clause):
            tail = clause[revenue.end():]
            amount = _VALUE.search(tail[:160])
            if amount is None or _OTHER_METRIC.search(tail[:amount.start()]):
                continue
            state = observe_metric_predicate(clause, revenue.start(), revenue.end() + amount.end())
            if not state.forward_outlook:
                continue
            if issuer_only:
                local = clause[state.scope_start:revenue.start()]
                if state.cue_start is not None and state.cue_start < revenue.start():
                    before_cue = clause[state.scope_start:state.cue_start]
                    if not _ISSUER_SUBJECT.fullmatch(before_cue):
                        if not _YEAR_ONLY_PREFIX.fullmatch(before_cue):
                            continue
                        # Chinese filings often put the forecast marker and
                        # fiscal year before the issuer: "预计2026年公司整体收入".
                        # Require that the cue has no other subject, and that
                        # the bounded text after it names the issuer before
                        # this revenue metric.
                        after_cue = (clause[state.cue_end:revenue.start()]
                                     if state.cue_end is not None else "")
                        if not _PERIOD_ISSUER_AFTER_EXPECTED.fullmatch(after_cue):
                            continue
                else:
                    owner = _ISSUER_METRIC.match(local)
                    if owner is None or re.search(r"['’]s\b|的", local[owner.end():]):
                        continue
            return True
    return False


def revenue_guidance_premise(forecast: str, premise: str, *, follows: bool) -> bool:
    """A source-authored explicit reference, not a nearby conditional sentence."""
    value = matching_reading_text(premise)
    reference = _REFERENCE.match(value)
    if reference is None or not _PREMISE.match(value[reference.end():]):
        return False
    forward = reference.group("reference").casefold() in _FOLLOWING
    if forward == follows or not revenue_guidance(forecast, issuer_only=True):
        return False
    scope = reference.group("scope") or ""
    reference_years = set(_EXPLICIT_YEAR.findall(scope))
    forecast_years = set(_EXPLICIT_YEAR.findall(matching_reading_text(forecast)))
    # A year-qualified reference is a source-level link to that exact outlook.
    # If the nearby forecast has a different or ambiguous set of years, leave
    # the dependency unproved instead of attaching an adjacent assertion.
    if reference_years and (len(reference_years) != 1 or forecast_years != reference_years):
        return False
    scope = _GENERIC_SCOPE.sub("", scope).casefold()
    if scope and scope not in _GENERIC_SCOPE.sub("", matching_reading_text(forecast)).casefold():
        return False
    return True


def is_explicit_backward_revenue_guidance_premise(premise: str) -> bool:
    """Cheaply identify a premise that explicitly points to prior guidance."""
    value = matching_reading_text(premise)
    reference = _REFERENCE.match(value)
    if reference is None or not _PREMISE.match(value[reference.end():]):
        return False
    return reference.group("reference").casefold() not in _FOLLOWING
