"""Bounded period-label parsing for ``du4-table-bindings/1`` columns.

One label text (one ``TextRef`` span of an original unit) is parsed into facts;
the facts of a column's header path are combined only when they agree.  A bare
year never invents fiscal/as-of semantics, a fiscal year never becomes twelve
months and an undisclosed start stays ``None``.  Conflicting facts (six vs
twelve months, two years, two kinds) are reported instead of one side winning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KIND_AS_OF = "as_of"
KIND_DURATION = "duration"
KIND_FISCAL = "fiscal_year"
KIND_UNSPECIFIED = "unspecified"

_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_MONTH_DAY_EN = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?\b"
)
_MONTH_DAY_ZH = re.compile(r"(?<!\d)(\d{1,2})月(\d{1,2})日")
_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
_DURATION_EN = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"\d{1,2})\s*(?:[-–—]\s*)?months?\b",
    re.IGNORECASE,
)
_DURATION_WORD = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
_DURATION_ZH = re.compile(r"(十二|十一|十|九|八|七|六|五|四|三|二|一)(?:个|個)月")
_DURATION_ZH_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}
_FISCAL = re.compile(r"fiscal\s*year|財政年度|财政年度", re.IGNORECASE)
_AS_OF = re.compile(r"\bas\s+of\b|截至", re.IGNORECASE)
_START_EN = re.compile(
    r"\bfrom\s+(January|February|March|April|May|June|July|August|September"
    r"|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(20\d{2})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LabelFacts:
    kind: str
    months: int | None
    year: int | None
    month_day: tuple[int, int] | None
    start: str | None


def parse_label(text: str) -> LabelFacts:
    months: int | None = None
    m = _DURATION_EN.search(text)
    if m:
        token = m.group(1).lower()
        months = _DURATION_WORD.get(token) or int(token)
    if months is None:
        m = _DURATION_ZH.search(text)
        if m:
            months = _DURATION_ZH_NUM[m.group(1)]

    year: int | None = None
    ym = _YEAR.search(text)
    if ym:
        year = int(ym.group(1))

    month_day: tuple[int, int] | None = None
    dm = _MONTH_DAY_EN.search(text)
    if dm:
        month_day = (_MONTH_NUM[dm.group(1).lower()], int(dm.group(2)))
    else:
        dm = _MONTH_DAY_ZH.search(text)
        if dm:
            month_day = (int(dm.group(1)), int(dm.group(2)))

    start: str | None = None
    sm = _START_EN.search(text)
    if sm:
        start = f"{sm.group(3)}-{_MONTH_NUM[sm.group(1).lower()]:02d}-{int(sm.group(2)):02d}"

    if months is not None:
        kind = KIND_DURATION
    elif _FISCAL.search(text):
        kind = KIND_FISCAL
    elif _AS_OF.search(text):
        kind = KIND_AS_OF
    else:
        kind = KIND_UNSPECIFIED
    return LabelFacts(kind=kind, months=months, year=year, month_day=month_day, start=start)


def combine(facts: list[LabelFacts]) -> tuple[dict, bool]:
    """Combine label facts into a period dict; returns (period, conflicted)."""
    conflict = False

    def single_int(values: set[int | None]) -> int | None:
        nonlocal conflict
        live = {v for v in values if v is not None}
        if len(live) > 1:
            conflict = True
            return None
        return next(iter(live)) if live else None

    def single_day(values: set[tuple[int, int] | None]) -> tuple[int, int] | None:
        nonlocal conflict
        live = {v for v in values if v is not None}
        if len(live) > 1:
            conflict = True
            return None
        return next(iter(live)) if live else None

    def single_str(values: set[str | None]) -> str | None:
        nonlocal conflict
        live = {v for v in values if v is not None}
        if len(live) > 1:
            conflict = True
            return None
        return next(iter(live)) if live else None

    kinds = {f.kind for f in facts if f.kind != KIND_UNSPECIFIED}
    if len(kinds) > 1:
        conflict = True
        kind = KIND_UNSPECIFIED
    elif kinds:
        kind = next(iter(kinds))
    else:
        kind = KIND_UNSPECIFIED

    months = single_int({f.months for f in facts})
    year = single_int({f.year for f in facts})
    month_day = single_day({f.month_day for f in facts})
    start = single_str({f.start for f in facts})

    end: str | None = None
    if not conflict and year is not None and month_day is not None:
        end = f"{year}-{month_day[0]:02d}-{month_day[1]:02d}"

    period: dict = {
        "kind": KIND_UNSPECIFIED if conflict else kind,
        "raw_label_refs": [],  # filled by the caller with the real header refs
        "start": None if conflict else start,
        "end": None if conflict else end,
        "duration_months": (
            months if not conflict and kind == KIND_DURATION else None
        ),
        "fiscal_label": (
            str(year) if not conflict and kind == KIND_FISCAL and year is not None else None
        ),
    }
    return period, conflict
