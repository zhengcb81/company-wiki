"""ZR-503: multi-entity attribution guard — a pure function that detects
whether a document's text names more than one company, so a single-entity
consumer never silently attributes multi-entity content (e.g. a broker
comparison report) to one issuer.

Verdicts:
  single        — every company-name phrase on the text relates to the
                  declared entity (or there is exactly one phrase).
  multi_entity  — at least two distinct company-name phrases with one
                  unrelated to the declared entity (or the declared entity
                  is absent and several phrases exist) => attribution is
                  needed; a fail-closed review signal, never a silent
                  single-entity attribution.
  unverifiable  — no company-name phrase found (nothing to attribute):
                  never a fabricated pass or fail.

Hermetic and deterministic (regex only).  Company-name phrase extraction is
an approximation (suffix-anchored CJK runs; leading noise words possible)
— it is deliberately NOT a name registry, so zero company names are
hardcoded.  Single-entity identity *contradiction* (one phrase that differs
from the declared entity) is out of scope here: ZR-502 homepage identity
verification owns that signal.
"""

from __future__ import annotations

import re
import unicodedata

ENTITY_DETECTION_SCHEMA_VERSION = "1.0"

# Suffix-anchored company-name phrases.  Greedy subject (backtracking to the
# longest subject that ends right before a suffix) + longest-suffix-first
# alternation keeps a full company name as ONE phrase instead of splitting
# it at a short suffix (e.g. "...集团公司" + "股份有限公司").
_COMPANY_SUFFIX = re.compile(
    r"[\u4e00-\u9fff]{2,12}"
    r"(?:股份有限公司|有限责任公司|有限公司|集团公司|集团)"
)


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFC", text or "")
    value = re.sub(r"[\s，。；、：:,.()（）\[\]【】\-—_/\\]+", "", value)
    return value.casefold()


def _company_phrases(text: str) -> list[str]:
    """Suffix-anchored company-name phrases, normalized and de-duplicated
    (first-seen order)."""
    seen: dict[str, None] = {}
    for match in _COMPANY_SUFFIX.finditer(_normalize(text)):
        phrase = match.group(0)
        if phrase not in seen:
            seen[phrase] = None
    return list(seen)


def _split_related(phrases: list[str], declared_norm: str) -> list[str]:
    """Phrases unrelated to the declared entity (empty = all related)."""
    related = {
        phrase
        for phrase in phrases
        if declared_norm and (declared_norm in phrase or phrase in declared_norm)
    }
    return [phrase for phrase in phrases if phrase not in related]


def _classify(phrases: list[str], declared_norm: str) -> tuple[str, list[str]]:
    """verdict + unrelated phrases for a non-empty phrase set."""
    others = _split_related(phrases, declared_norm)
    if len(phrases) >= 2 and (others or not declared_norm):
        return "multi_entity", others
    return "single", others


def detect_entities(
    text: str | None,
    *,
    declared_entity: str | None = None,
    declared_security_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    """Return a verdict dict:

      {"schema_version": "1.0", "verdict": ..., "evidence": {...}}

    verdict in {"single", "multi_entity", "unverifiable"}.
    """
    phrases = _company_phrases(text or "")
    if not phrases:
        return {
            "schema_version": ENTITY_DETECTION_SCHEMA_VERSION,
            "verdict": "unverifiable",
            "evidence": {
                "reason": "no_company_name_phrases",
                "declared_entity": declared_entity,
                "declared_security_ids_count": len(declared_security_ids),
            },
        }
    verdict, others = _classify(phrases, _normalize(declared_entity or ""))
    return {
        "schema_version": ENTITY_DETECTION_SCHEMA_VERSION,
        "verdict": verdict,
        "evidence": {
            "company_phrases": phrases,
            "others_unrelated_to_declared": others,
            "declared_entity": declared_entity,
            "declared_security_ids_count": len(declared_security_ids),
        },
    }


def multi_entity_quality_flag(verdict: str) -> str | None:
    """Map a verdict to the normalized quality flag (None = no flag)."""
    if verdict == "multi_entity":
        return "multi_entity_attribution_needed"
    return None


__all__ = [
    "ENTITY_DETECTION_SCHEMA_VERSION",
    "detect_entities",
    "multi_entity_quality_flag",
]
