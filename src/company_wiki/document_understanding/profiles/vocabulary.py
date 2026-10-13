"""Frozen vocabulary for document profiles.

These enumerations are the shared language between the registry, the router and the
consumers of ``du-route/1``. They are deliberately closed sets: a route that needs a new
family or section role is a wire change owned by ROOT, not a local invention.

The vocabularies come from ``INTERFACES.md`` section 3 (families, regimes, section roles,
semantic units, dispositions) and from ``design.md`` section 4 (the classification axes).
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION_ROUTE: Final = "du-route/1"
SCHEMA_VERSION_INPUT: Final = "du-input/1"

#: Disclosure regime, i.e. which regulator's form vocabulary applies.
REGIMES: Final[tuple[str, ...]] = ("cn_exchange", "hkex", "sec", "other", "unknown")

#: Document family, orthogonal to regime, carrier and language.
FAMILIES: Final[tuple[str, ...]] = (
    "annual",
    "interim",
    "quarterly",
    "prospectus",
    "offering",
    "results_release",
    "presentation",
    "investor_qa",
    "earnings_call",
    "administrative",
    "unknown",
)

#: Route confidence. No calibrated probability is emitted without calibration.
CONFIDENCES: Final[tuple[str, ...]] = ("high", "medium", "low", "unknown")

#: What the router suggests downstream should do. Never the final skip decision.
DISPOSITIONS: Final[tuple[str, ...]] = ("read", "generic_read", "administrative_candidate")

#: Unified section roles shared by every profile.
SECTION_ROLES: Final[tuple[str, ...]] = (
    "business",
    "industry",
    "management_discussion",
    "outlook",
    "risk",
    "operating_metrics",
    "fundraising",
    "financial_notes",
    "questions",
    "administrative",
    "unknown",
)

#: Semantic unit kinds. ``design.md`` section 6 fixes exactly these six.
SEMANTIC_UNITS: Final[tuple[str, ...]] = (
    "paragraph_event",
    "qa_exchange",
    "project",
    "operating_table",
    "risk",
    "background",
)

#: Reason codes emitted by the router. Short, stable, machine-readable diagnostics.
REASON_METADATA_MATCH: Final = "METADATA_MATCH"
REASON_DECLARED_KIND_MATCH: Final = "DECLARED_KIND_MATCH"
REASON_FILENAME_MATCH: Final = "FILENAME_MATCH"
REASON_COVER_HEADING: Final = "COVER_HEADING"
REASON_TOC_STRUCTURE: Final = "TOC_STRUCTURE"
REASON_SECTION_VOCABULARY: Final = "SECTION_VOCABULARY"
REASON_QA_STRUCTURE: Final = "QA_STRUCTURE"
REASON_SPEAKER_TURNS: Final = "SPEAKER_TURNS"
REASON_SLIDE_STRUCTURE: Final = "SLIDE_STRUCTURE"
REASON_HTML_CARRIER: Final = "HTML_CARRIER"
REASON_TXT_CARRIER: Final = "TXT_CARRIER"
REASON_ADMINISTRATIVE_PURPOSE: Final = "ADMINISTRATIVE_PURPOSE"
REASON_METADATA_CONFLICT: Final = "METADATA_CONFLICT"
REASON_REGIME_CONFLICT: Final = "REGIME_CONFLICT"
REASON_DECLARED_KIND_CONFLICT: Final = "DECLARED_KIND_CONFLICT"
REASON_ALTERNATIVE_FAMILY: Final = "ALTERNATIVE_FAMILY"
REASON_NATIVE_SCAN_UNAVAILABLE: Final = "NATIVE_SCAN_UNAVAILABLE"
REASON_PARTIAL_NATIVE_SCAN: Final = "PARTIAL_NATIVE_SCAN"
REASON_OPAQUE_PAGES: Final = "OPAQUE_PAGES"
REASON_NO_READABLE_BODY: Final = "NO_READABLE_BODY"
REASON_ROUTE_PROBE_LIMIT: Final = "ROUTE_PROBE_LIMIT"
REASON_UNKNOWN_PROFILE: Final = "UNKNOWN_PROFILE"
REASON_EXTERNAL_ATTACHMENT_NOT_READ: Final = "EXTERNAL_ATTACHMENT_NOT_READ"
REASON_CHILD_RANGE_NOT_READ: Final = "CHILD_RANGE_NOT_READ"
REASON_LOW_INFORMATION: Final = "LOW_INFORMATION"

#: Default probe budget. ROOT converges these with the existing global limits.
DEFAULT_MAX_PROBE_UNITS: Final = 200
DEFAULT_MAX_PROBE_CHARS: Final = 64000
DEFAULT_MAX_CHILD_ROUTES: Final = 16

#: Bounded detail length so a diagnostic never becomes a body copy.
MAX_REASON_DETAIL_CHARS: Final = 200
