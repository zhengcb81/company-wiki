"""Reported fiscal years for public source selection and manifests."""
from __future__ import annotations

from collections.abc import Mapping
import re
from unicodedata import normalize


_YEAR = r"(?<!\d)(?P<year>19\d{2}|20\d{2}|21\d{2})(?!\d)"
_DATE_OR_RANGE_SUFFIX = re.compile(
    r"\s*(?:(?:[-/.–—]|&|and\b|至|到)\s*\d{1,4}\b|年\s*\d{1,2}\s*月)", re.IGNORECASE,
)
_RANGE_PREFIX = re.compile(r"\d{2,4}\s*(?:[-/.–—]|&|and\b|至|到)\s*\Z", re.IGNORECASE)
_REPORT_LABELS = {
    "annual_report": r"(?:annual\s+report\b|年度(?:報告|报告)|年[報报](?:告)?)",
    "semi_annual_report": r"(?:(?:semi[\s-]*annual|half[\s-]*year(?:ly)?|interim)\s+report\b|(?:半年度?|中期)(?:報告|报告))",
    "quarterly_report": r"(?:quarterly\s+report\b|(?:第?[一二三四1-4]季度?|季度)(?:報告|报告))",
}
_TITLE_YEAR_PATTERNS = {
    kind: (
        re.compile(rf"{_YEAR}\s*(?:年\s*)?(?:[-–—:]\s*)?{label}", re.IGNORECASE),
        re.compile(
            rf"{label}\s*[:–—-]?\s*(?:for\s+(?:the\s+)?)?(?:fiscal\s+year\s+|FY\s*)?{_YEAR}", re.IGNORECASE,
        ),
    )
    for kind, label in _REPORT_LABELS.items()
}


def reported_fiscal_year(document_kind: str, metadata: Mapping[str, object]) -> int | None:
    """Use the captured fiscal year or one unambiguous year in the disclosure title."""
    if "fiscal_year" in metadata:
        value = metadata["fiscal_year"]
        if not isinstance(value, bool) and isinstance(value, (int, str)):
            match = re.fullmatch(_YEAR, str(value).strip())
            if match is not None:
                return int(match["year"])
        return None

    source_title = metadata.get("source_title")
    if not isinstance(source_title, str):
        return None
    title = normalize("NFKC", source_title)
    matches = {
        int(match["year"])
        for pattern in _TITLE_YEAR_PATTERNS.get(document_kind, ())
        for match in pattern.finditer(title)
        if _RANGE_PREFIX.search(title[:match.start("year")]) is None
        and _DATE_OR_RANGE_SUFFIX.match(title, match.end("year")) is None
    }
    return next(iter(matches)) if len(matches) == 1 else None
