"""Deterministic text-shape evidence for layout hints.

These helpers only classify *shape* (numbers, years, period/unit lines,
caption/footnote markers, heading numbering).  They contain no company names,
no page-number lists and no numeric whitelists.
"""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")

NUMBER_RE = re.compile(r"^[+\-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?$|^\d+(?:\.\d+)?%?$|^[—–-]$")
YEAR_RE = re.compile(r"^(?:19|20)\d{2}\s*年?$")
DATE_RE = re.compile(
    r"^(?:19|20)\d{2}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?$|^(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}$"
)
PERIOD_RE = re.compile(
    r"(截至|截止|止财政年度|止年度|as of|year ended|for the .{0,24}ended)",
    re.IGNORECASE,
)
UNIT_LINE_RE = re.compile(r"^\(?\s*(?:单位|金額單位|金额单位|除特别注明外|units?)\s*[:：]", re.IGNORECASE)
CAPTION_TITLE_RE = re.compile(
    r"^\s*(?:表|图|附表|附图|table|figure|exhibit)\s*[0-9A-Za-z一二三四五六七八九十\-]*",
    re.IGNORECASE,
)
FOOTNOTE_RE = re.compile(
    r"^\s*(?:注|註)\s*[0-9]*\s*[:：]?|^\s*[*＊†‡※]|\[\d+\]|^\s*(?:资料来源|資料來源|来源|source)\s*[:：]?",
    re.IGNORECASE,
)

_HEADING_NUMBERED = (
    (re.compile(r"^第[一二三四五六七八九十百零0-9]+[章节部篇]"), 1),
    (re.compile(r"^[一二三四五六七八九十]+[、．.]"), 1),
    (re.compile(r"^[（(][一二三四五六七八九十0-9]+[）)]"), 2),
    (re.compile(r"^\d+\.\d+\.\d+(?:\s|[、.．])?"), 3),
    (re.compile(r"^\d+\.\d+(?:\s|[、.．])?"), 2),
    (re.compile(r"^\d+[、．.](?!\d)"), 2),
    (re.compile(r"^[A-Z][、．.]"), 2),
)

TERMINAL_PUNCTUATION = "。．.；;！!？?：:"


def normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def normalized_key(text: str) -> str:
    return normalize_ws(text).casefold()


def is_numeric_text(text: str) -> bool:
    return bool(NUMBER_RE.match(normalize_ws(text)))


def is_year_text(text: str) -> bool:
    return bool(YEAR_RE.match(normalize_ws(text)))


def is_date_text(text: str) -> bool:
    return bool(DATE_RE.match(normalize_ws(text)))


def has_quantity_token(text: str) -> bool:
    """True when any whitespace token is a plain quantity (not a year/date)."""
    for token in normalize_ws(text).split(" "):
        token = token.strip("()（）[]【】:：，,")
        if not token:
            continue
        if is_year_text(token) or is_date_text(token):
            continue
        if is_numeric_text(token):
            return True
    return False


def is_period_text(text: str) -> bool:
    value = normalize_ws(text)
    return len(value) <= 40 and bool(PERIOD_RE.search(value))


def is_unit_line(text: str) -> bool:
    return bool(UNIT_LINE_RE.match(normalize_ws(text)))


def is_caption_title(text: str) -> bool:
    value = normalize_ws(text)
    return len(value) <= 60 and bool(CAPTION_TITLE_RE.match(value))


def is_footnote_text(text: str) -> bool:
    return bool(FOOTNOTE_RE.match(normalize_ws(text)))


def is_figure_caption(text: str) -> bool:
    value = normalize_ws(text)
    return bool(re.match(r"^\s*(?:图|figure)\s*[0-9A-Za-z一二三四五六七八九十\-]*", value, re.IGNORECASE))


def has_terminal_punctuation(text: str) -> bool:
    value = normalize_ws(text)
    return bool(value) and value[-1] in TERMINAL_PUNCTUATION


def heading_number_level(text: str) -> int | None:
    value = normalize_ws(text)
    for pattern, level in _HEADING_NUMBERED:
        if pattern.match(value):
            return level
    return None


def is_plain_sentence(text: str) -> bool:
    value = normalize_ws(text)
    return len(value) >= 12 and has_terminal_punctuation(value)
