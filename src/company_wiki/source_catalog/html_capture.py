"""ZR-509: official announcement/news HTML capture identity gate — pure
functions that extract title / entity candidates / period from an HTML
page and validate them against the declared entity BEFORE any capture,
so an unrelated or entity-less page is never captured as an official
announcement (fail-closed).

  parse_html_identity(html_text)      -> {"schema_version", "title",
                                         "entities", "period"}
  validate_html_capture(identity, declared_entity)
                                      -> {"schema_version", "verdict",
                                         "reason"}

verdict in {"ok", "missing_title", "no_entity", "entity_mismatch",
"invalid_period"}.  Hermetic (regex only; zero hardcoded names).
"""

from __future__ import annotations

import re
import unicodedata

HTML_CAPTURE_SCHEMA_VERSION = "1.0"

_TITLE_RE = re.compile(
    r"<(?:title|h1)[^>]*>(.*?)</(?:title|h1)>", re.IGNORECASE | re.DOTALL
)
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_SUFFIX = re.compile(
    r"[\u4e00-\u9fff]{2,12}"
    r"(?:股份有限公司|有限责任公司|有限公司|集团公司|集团)"
)
_PERIOD_CN = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_PERIOD_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_PERIOD_YEAR = re.compile(r"(\d{4})\s*年")


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _strip_tags(value: str) -> str:
    return _TAG_RE.sub("", value)


def _extract_title(source: str) -> str | None:
    for match in _TITLE_RE.finditer(source):
        candidate = _text(_strip_tags(match.group(1)))
        if candidate:
            return candidate
    return None


def _extract_entities(body: str) -> list[str]:
    entities: list[str] = []
    for match in _ENTITY_SUFFIX.finditer(body):
        phrase = match.group(0)
        if phrase not in entities:
            entities.append(phrase)
    return entities


def _extract_period(body: str) -> str | None:
    for match in (_PERIOD_CN.search(body), _PERIOD_ISO.search(body)):
        if match:
            year, month, day = (int(match.group(i)) for i in (1, 2, 3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    year_match = _PERIOD_YEAR.search(body)
    if year_match:
        return year_match.group(1)
    return None


def parse_html_identity(html_text: str | None) -> dict[str, object]:
    """Extract title (first <title> or <h1>), entity candidates
    (suffix-anchored company phrases, first-seen order) and period (first
    CN/ISO date or bare year)."""
    source = html_text or ""
    body = _strip_tags(source)
    return {
        "schema_version": HTML_CAPTURE_SCHEMA_VERSION,
        "title": _extract_title(source),
        "entities": _extract_entities(body),
        "period": _extract_period(body),
    }


def _entity_matches(declared: str, entities: list[str]) -> bool:
    declared_norm = unicodedata.normalize("NFC", declared or "").casefold()
    if not declared_norm:
        return True
    for phrase in entities:
        phrase_norm = unicodedata.normalize("NFC", phrase).casefold()
        if declared_norm in phrase_norm or phrase_norm in declared_norm:
            return True
    return False


def _period_verdict(period: object) -> str | None:
    if period is not None and not re.fullmatch(
        r"\d{4}(-\d{2}-\d{2})?", str(period)
    ):
        return "invalid_period"
    return None


def validate_html_capture(
    identity: dict[str, object],
    *,
    declared_entity: str | None = None,
) -> dict[str, object]:
    """Identity gate: title required, >=1 entity required (fail-closed for
    entity-less pages), entity must relate to the declared one when
    provided; the period must parse when present."""
    title = identity.get("title")
    if not title:
        return {"schema_version": HTML_CAPTURE_SCHEMA_VERSION,
                "verdict": "missing_title",
                "reason": "no title or h1 element with text"}
    entities = [item for item in identity.get("entities") or [] if item]
    if not entities:
        return {"schema_version": HTML_CAPTURE_SCHEMA_VERSION,
                "verdict": "no_entity",
                "reason": "no company-name phrase on the page"}
    if not _entity_matches(declared_entity or "", entities):
        return {"schema_version": HTML_CAPTURE_SCHEMA_VERSION,
                "verdict": "entity_mismatch",
                "reason": "declared entity not found among page entities"}
    verdict = _period_verdict(identity.get("period"))
    if verdict is not None:
        return {"schema_version": HTML_CAPTURE_SCHEMA_VERSION,
                "verdict": verdict,
                "reason": "period does not parse"}
    return {"schema_version": HTML_CAPTURE_SCHEMA_VERSION,
            "verdict": "ok",
            "reason": None}


__all__ = [
    "HTML_CAPTURE_SCHEMA_VERSION",
    "parse_html_identity",
    "validate_html_capture",
]
