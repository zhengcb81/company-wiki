"""Deterministic text, quantity and modality primitives for the oracle.

Everything here is deliberately conservative. It can prove *absence* or a
*contradiction* from an exact anchor, but it can never prove semantic
entailment — that stays ``NOT_EVALUATED`` unless an independent reviewer has
signed off (see ``checkers.semantics_entailment``).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------

_WHITESPACE = re.compile(r"[\s\u3000]+")
# Full-width/CJK punctuation and quoting variants that carry no meaning for
# substring containment.
_PUNCT_MAP = {
    "，": ",",
    "。": ".",
    "、": ",",
    "；": ";",
    "：": ":",
    "（": "(",
    "）": ")",
    "《": "<",
    "》": ">",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "％": "%",
    "　": " ",
}


def normalize_text(value: Any) -> str:
    """Fold text for containment comparison without changing its meaning."""

    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    for source, target in _PUNCT_MAP.items():
        text = text.replace(source, target)
    text = text.casefold()
    return _WHITESPACE.sub("", text)


def normalize_loose(value: Any) -> str:
    """Like :func:`normalize_text` but keeps single spaces between words.

    Word-boundary languages (English) need the spaces, so both forms are
    tried when matching a quote anchor.
    """

    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    for source, target in _PUNCT_MAP.items():
        text = text.replace(source, target)
    return _WHITESPACE.sub(" ", text.casefold()).strip()


def text_contains(haystack: str, needle: str) -> bool:
    """Return True when ``needle`` is present in ``haystack`` under either fold."""

    if not needle:
        return False
    if normalize_text(needle) in normalize_text(haystack):
        return True
    loose_needle = normalize_loose(needle)
    return bool(loose_needle) and loose_needle in normalize_loose(haystack)


def anchor_matches(anchor_text: str, haystack: str) -> bool:
    return text_contains(haystack, anchor_text)


# --------------------------------------------------------------------------
# numbers
# --------------------------------------------------------------------------

_CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}

# Chinese scale words and their multipliers.
_SCALE_WORDS: tuple[tuple[str, int], ...] = (
    ("亿元", 100_000_000),
    ("亿", 100_000_000),
    ("万元", 10_000),
    ("万", 10_000),
    ("千元", 1_000),
    ("百万元", 1_000_000),
    ("million", 1_000_000),
    ("billion", 1_000_000_000),
    ("thousand", 1_000),
)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_CN_NUMBER_RE = re.compile(r"[零〇一二两三四五六七八九十百千]+")
# A bare digit run inside a longer alphanumeric token (7,504 / 28,000 / 2024年)
# is a number; a digit run glued to a unit keeps its unit.
_DIGIT_RUN_RE = re.compile(r"\d[\d.,]*")


def _parse_arabic(raw: str) -> float | None:
    cleaned = raw.replace(",", "")
    # A dot followed by exactly 3 digits inside a grouped number is a
    # thousands separator (1.234.567), not a decimal point.
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_chinese_number(raw: str) -> float | None:
    if not raw:
        return None
    if all(char in _CN_DIGITS for char in raw):
        value = 0
        for char in raw:
            value = value * 10 + _CN_DIGITS[char]
        return float(value)
    total = 0.0
    section = 0.0
    digit: float | None = None
    for char in raw:
        if char in _CN_DIGITS:
            digit = float(_CN_DIGITS[char])
            continue
        unit = _CN_UNITS.get(char)
        if unit is None:
            return None
        section += (1.0 if digit is None else digit) * unit
        digit = None
    if digit is not None:
        section += digit
    total += section
    return total


def _spans_with_scales(text: str) -> list[tuple[float, str]]:
    """Return ``(value, unit_text)`` pairs found in ``text``."""

    found: list[tuple[float, str]] = []
    for match in _NUMBER_RE.finditer(text):
        value = _parse_arabic(match.group())
        if value is None:
            continue
        tail = text[match.end() : match.end() + 8]
        unit = ""
        for word, _multiplier in _SCALE_WORDS:
            if tail.startswith(word):
                unit = word
                break
        found.append((value, unit))
    for match in _CN_NUMBER_RE.finditer(text):
        value = _parse_chinese_number(match.group())
        if value is None:
            continue
        tail = text[match.end() : match.end() + 8]
        unit = ""
        for word, _multiplier in _SCALE_WORDS:
            if tail.startswith(word):
                unit = word
                break
        found.append((value, unit))
    return found


def scale_multiplier(unit_text: str | None) -> int:
    if not unit_text:
        return 1
    folded = unit_text.casefold()
    for word, multiplier in _SCALE_WORDS:
        if word in folded:
            return multiplier
    return 1


def quantities_from_text(text: str) -> list[tuple[float, str]]:
    return _spans_with_scales(text)


def number_present(value: Any, haystack: str) -> bool:
    """Return True when ``value`` appears in ``haystack``, at any scale.

    ``28000`` matches ``28,000万元`` and ``2.8亿元``; ``7504`` matches
    ``7,504家``. It does *not* match a bare substring such as ``750`` inside
    ``7504``.
    """

    if value is None:
        return False
    try:
        target = float(str(value).replace(",", ""))
    except ValueError:
        return text_contains(haystack, str(value))

    for raw in _DIGIT_RUN_RE.findall(haystack):
        found = _parse_arabic(raw)
        if found is None:
            continue
        if _numbers_equal(found, target):
            return True

    # Scaled CJK forms: 2.8亿 == 280,000,000.
    for match in _NUMBER_RE.finditer(haystack):
        found = _parse_arabic(match.group())
        if found is None:
            continue
        tail = haystack[match.end() : match.end() + 8]
        multiplier = 1
        for word, scale in _SCALE_WORDS:
            if tail.startswith(word):
                multiplier = scale
                break
        if multiplier != 1 and _numbers_equal(found * multiplier, target):
            return True

    for match in _CN_NUMBER_RE.finditer(haystack):
        found = _parse_chinese_number(match.group())
        if found is None:
            continue
        tail = haystack[match.end() : match.end() + 8]
        multiplier = 1
        for word, scale in _SCALE_WORDS:
            if tail.startswith(word):
                multiplier = scale
                break
        if _numbers_equal(found * multiplier, target):
            return True
    return False


def _numbers_equal(left: float, right: float) -> bool:
    return abs(left - right) <= max(abs(right) * 1e-9, 1e-9)


def quantities_from_scales(text: str) -> list[tuple[float, str]]:
    return _spans_with_scales(text)


# --------------------------------------------------------------------------
# modality / role
# --------------------------------------------------------------------------

_NEGATION_MARKERS = (
    "不",
    "未",
    "没有",
    "无",
    "非",
    "尚未",
    "not ",
    "no ",
    "never",
    "without",
    "cannot",
    "does not",
    "did not",
)

_PLAN_MARKERS = (
    "拟",
    "计划",
    "预计",
    "将",
    "拟投资",
    "规划",
    "目标",
    "预计投入",
    "plan",
    "plans to",
    "intend",
    "expects to",
    "will ",
    "target",
    "proposed",
)

_ACTUAL_MARKERS = (
    "已完成",
    "已实现",
    "已投产",
    "截至",
    "实际",
    "complet",
    "realiz",
    "actual",
    "as of",
    "was ",
    "were ",
)

_QUESTION_MARKERS = ("?", "？")
_QUESTION_VERBS = ("请问", "是否", "能否", "如何", "吗", "呢")


# Phrases where a negation marker is part of a quantity bound rather than a
# denial. "不超过35,978.71万元" caps an amount; it does not negate a fact, so
# treating it as negation would invert the meaning of a legitimate plan.
_BOUND_PHRASES = (
    "不超过",
    "不多于",
    "不少于",
    "不低于",
    "不足部分",
    "不计",
    "不适用",
    "不含",
    "no more than",
    "no less than",
    "not more than",
    "not less than",
    "not applicable",
)


def has_negation(text: str) -> bool:
    """True when the text denies or prohibits something.

    Quantity bounds such as ``不超过`` are stripped first, because they contain
    a negation character but carry the opposite meaning for fact purposes.
    """

    working = text
    for phrase in _BOUND_PHRASES:
        working = working.replace(phrase, "")
        working = working.replace(phrase.casefold(), "")
    folded = normalize_loose(working)
    if any(marker in folded for marker in _NEGATION_MARKERS):
        return True
    # CJK negation is not whitespace-delimited, so also test the compact form.
    compact = normalize_text(working)
    return any(marker in compact for marker in ("不", "未", "无", "非", "暂无", "没有"))


def has_plan_marker(text: str) -> bool:
    folded = normalize_loose(text)
    compact = normalize_text(text)
    return any(marker in folded for marker in _PLAN_MARKERS) or any(
        marker in compact for marker in ("拟", "计划", "预计", "规划")
    )


def has_actual_marker(text: str) -> bool:
    folded = normalize_loose(text)
    compact = normalize_text(text)
    return any(marker in folded for marker in _ACTUAL_MARKERS) or any(
        marker in compact for marker in ("已完成", "已实现", "已投产", "截至")
    )


def looks_like_question(text: str) -> bool:
    if any(marker in text for marker in _QUESTION_MARKERS):
        return True
    compact = normalize_text(text)
    return any(marker in compact for marker in _QUESTION_VERBS)


def modality_conflicts(declared: str, text: str) -> str | None:
    """Return a conflict code when ``declared`` contradicts the claim text."""

    if declared == "negation" and not has_negation(text):
        return "declared_negation_but_text_asserts"
    if declared in {"actual", "plan"} and has_negation(text):
        return "text_negates_but_declared_positive"
    if declared == "actual" and has_plan_marker(text) and not has_actual_marker(text):
        return "declared_actual_but_text_is_plan"
    if declared == "plan" and has_actual_marker(text) and not has_plan_marker(text):
        return "declared_plan_but_text_is_actual"
    if declared == "question" and not looks_like_question(text):
        return "declared_question_but_text_is_statement"
    return None


def unit_matches_evidence(value: Any, unit: str | None, haystack: str) -> bool:
    """True when ``value`` + ``unit`` is exactly how the evidence states it.

    ``28000 万元`` matches "28,000万元" but not a claim that rewrote the same
    magnitude as ``280000000 元``: the unit basis must not be silently
    converted, because that is where 万元/亿元 and currency errors enter.
    """

    if value is None:
        return True
    target = _coerce_number(value)
    if target is None:
        return text_contains(haystack, str(value))
    declared_multiplier = scale_multiplier(unit)

    for raw in _DIGIT_RUN_RE.findall(haystack):
        found = _parse_arabic(raw)
        if found is None:
            continue
        if not _numbers_equal(found, target):
            continue
        tail = haystack[haystack.index(raw) + len(raw) :][:8]
        evidence_unit = ""
        for word, _scale in _SCALE_WORDS:
            if tail.startswith(word):
                evidence_unit = word
                break
        if scale_multiplier(evidence_unit) == declared_multiplier:
            return True
    return False


def _coerce_number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


_ANALYST_ROLES = frozenset({"analyst_question", "analyst_statement", "operator", "editorial_summary"})


def role_is_third_party(role: str) -> bool:
    return role in _ANALYST_ROLES or role == "third_party"


# --------------------------------------------------------------------------
# quantity-basis contradiction
# --------------------------------------------------------------------------

_TOTAL_MARKERS = ("门店总数", "总数", "总店数", "合计", "总计", "累计", "总产能", "total stores", "total")
_INCREMENT_MARKERS = (
    "净新增",
    "净增",
    "新增",
    "新开",
    "净开店",
    "同比增加",
    "net addition",
    "net new",
    "newly added",
    "opened",
)
_INVESTMENT_MARKERS = ("总投资", "投资额", "拟投入", "项目投资", "capex", "investment", "capital expenditure")
_REVENUE_MARKERS = ("营业收入", "收入", "营收", "revenue", "sales", "turnover")
_GMT_MARKERS = ("gmv", "商品交易总额", "总交易额")
_PLAN_ONLY_MARKERS = ("拟", "计划", "预计", "规划", "plan", "intend", "expect")


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    folded = normalize_loose(text)
    compact = normalize_text(text)
    for marker in markers:
        candidate = marker.casefold()
        if candidate in folded:
            return True
        if candidate.replace(" ", "") in compact:
            return True
    return False


def basis_contradiction(fact_basis: str, text: str) -> str | None:
    """Return a contradiction code when ``text`` restates a fact under the wrong basis.

    Unlike a literal ``must_not_assert`` token, this catches paraphrases such
    as "净新增门店7,504家" for a store-total fact.
    """

    total_like = _has_any(text, _TOTAL_MARKERS)
    increment_like = _has_any(text, _INCREMENT_MARKERS)

    if fact_basis == "total":
        if increment_like and not total_like:
            return "total_restated_as_increment"
        if _has_any(text, _GMT_MARKERS):
            return "gmv_restated_as_revenue"
    if fact_basis == "investment":
        if _has_any(text, _REVENUE_MARKERS) and not _has_any(text, _INVESTMENT_MARKERS):
            return "investment_restated_as_revenue"
    if fact_basis == "projected_output":
        if has_actual_marker(text) and not has_plan_marker(text):
            return "plan_restated_as_actual"
    if fact_basis == "count" and _has_any(text, _GMT_MARKERS):
        return "gmv_restated_as_revenue"
    return None


def fact_basis_hint(fact_id: str, must_not_assert: Sequence[str]) -> str:
    """Infer the intended quantity basis of a gold fact from its own guard tokens."""

    joined = " ".join(must_not_assert)
    if _has_any(joined, _REVENUE_MARKERS):
        return "investment" if _has_any(fact_id, ("capex", "investment", "project")) else "count"
    if _has_any(joined, _INCREMENT_MARKERS):
        return "total"
    if _has_any(joined, _PLAN_ONLY_MARKERS):
        return "unknown"
    return "unknown"


# --------------------------------------------------------------------------
# product / project lifecycle stage
# --------------------------------------------------------------------------

# A fact anchored at an early stage must not be restated at a later one. The
# order below is the real maturity order for equipment/verification reporting:
# development < lab verification < customer verification < mass-production
# verification < certified/succeeded < mass production.
STAGE_ORDER: tuple[tuple[str, int], ...] = (
    ("正在开发", 0),
    ("研发中", 0),
    ("under development", 0),
    ("实验室验证", 1),
    ("laboratory verification", 1),
    ("晶圆验证", 2),
    ("wafer verification", 2),
    ("客户端验证", 3),
    ("customer verification", 3),
    ("量产验证", 4),
    ("mass production verification", 4),
    ("验证成功", 5),
    ("verified successfully", 5),
    ("建成投产", 6),
    ("已量产", 7),
    ("批量生产", 7),
    ("mass production", 7),
)


def stage_level(text: str) -> int | None:
    """Return the most advanced lifecycle stage mentioned, or None."""

    folded = normalize_loose(text)
    compact = normalize_text(text)
    level: int | None = None
    for marker, value in STAGE_ORDER:
        candidate = marker.casefold().replace(" ", "")
        if candidate in compact or marker.casefold() in folded:
            level = value if level is None else max(level, value)
    return level


def stage_regression(anchor_text: str, claim_text: str) -> str | None:
    """Return a code when a claim claims a later stage than its evidence.

    ``量产验证阶段`` promoted to ``已量产`` is the canonical hallucination this
    catches; the reverse (a claim being more cautious than its evidence) is not
    reported, because under-claiming is not a fabrication.
    """

    anchored = stage_level(anchor_text)
    claimed = stage_level(claim_text)
    if anchored is None or claimed is None:
        return None
    if claimed > anchored:
        return f"stage_advanced:{anchored}->{claimed}"
    return None
