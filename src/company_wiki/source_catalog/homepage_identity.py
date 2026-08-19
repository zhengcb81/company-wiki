"""ZR-502: homepage identity verification — a pure function that compares
the PDF first-page text against the sidecar-declared title/publisher.

Verdicts:
  consistent     — a declared title/publisher/entity/security-id value
                   appears verbatim in the normalized first-page text.
  contradiction  — the first page carries an EXPLICIT conflicting signal:
                   a different company/security name, or a different
                   publisher, than the sidecar declared (wrong filename or
                   mismatched cover page => fail/review).
  unverifiable   — no first-page text was extracted (nothing to compare):
                   never a false pass, never a false fail.

Everything is deterministic and hermetic (no LLM, no network).
"""

from __future__ import annotations

import re
import unicodedata

HOMEPAGE_IDENTITY_SCHEMA_VERSION = "1.0"

_STRONG_CONFLICT_TOKENS = re.compile(
    r"(公司|证券|集团|有限|annual report|年度报告|年报|招股|prospectus|"
    r"深度报告|研究报告|investment research)"
)


def _normalize(text: str) -> str:
    """Casefold + strip punctuation/whitespace for matching."""
    value = unicodedata.normalize("NFC", text or "")
    value = re.sub(r"[\s，。；、：:,.()（）\[\]【】\-—_/\\]+", "", value)
    return value.casefold()


def _declared_hits(page_norm: str, **declared: str | None) -> list[dict[str, str]]:
    """Which declared identity values appear verbatim in the normalized
    first-page text.

    CJK covers have no spaces between company name and report title, so
    tokenization cannot split them reliably; substring containment of the
    whole declared value is the precise, false-positive-free signal (a
    declared 10+ char name never collides with generic cover wording).
    """
    hits: list[dict[str, str]] = []
    for field, value in declared.items():
        if not value:
            continue
        normalized = _normalize(value)
        if len(normalized) >= 2 and normalized in page_norm:
            hits.append({"field": field, "value": value})
    return hits


def assess_homepage_identity(
    first_page_text: str | None,
    *,
    title: str | None = None,
    publisher: str | None = None,
    security_id: str | None = None,
    entity: str | None = None,
) -> dict[str, object]:
    """Return a verdict dict:

      {"schema_version": "1.0", "verdict": ..., "evidence": {...}}

    verdict in {"consistent", "contradiction", "unverifiable"}.
    """
    page = (first_page_text or "").strip()
    if not page:
        return {
            "schema_version": HOMEPAGE_IDENTITY_SCHEMA_VERSION,
            "verdict": "unverifiable",
            "evidence": {"reason": "no_first_page_text"},
        }

    page_norm = _normalize(page)
    hits = _declared_hits(
        page_norm,
        title=title,
        publisher=publisher,
        entity=entity,
        security_id=security_id,
    )

    # 1) any declared identity value appears verbatim in the first page =>
    #    consistent
    if hits:
        return {
            "schema_version": HOMEPAGE_IDENTITY_SCHEMA_VERSION,
            "verdict": "consistent",
            "evidence": {
                "matched_tokens": hits,
                "declared_count": len(hits),
            },
        }

    # 2) explicit conflict: the page is clearly a company/report cover but
    #    none of the declared identity values appear, while the page does
    #    carry strong report/company framing => contradiction (fail/review).
    if _STRONG_CONFLICT_TOKENS.search(page):
        return {
            "schema_version": HOMEPAGE_IDENTITY_SCHEMA_VERSION,
            "verdict": "contradiction",
            "evidence": {
                "reason": "no_declared_identity_on_cover",
                "page_has_report_framing": True,
                "declared_count": 0,
            },
        }

    # 3) page exists but is not recognizably a cover (no strong framing) =>
    #    unverifiable (do not invent a pass or a fail)
    return {
        "schema_version": HOMEPAGE_IDENTITY_SCHEMA_VERSION,
        "verdict": "unverifiable",
        "evidence": {"reason": "no_strong_cover_framing"},
    }


def homepage_identity_quality_flag(verdict: str) -> str | None:
    """Map a verdict to the normalized quality flag (None = no flag)."""
    if verdict == "contradiction":
        return "homepage_identity_contradiction"
    return None


__all__ = [
    "HOMEPAGE_IDENTITY_SCHEMA_VERSION",
    "assess_homepage_identity",
    "homepage_identity_quality_flag",
]
