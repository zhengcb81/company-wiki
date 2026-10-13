"""Frozen wire schemas and validation for the document-understanding benchmark.

These schemas are the benchmark's public data contract (INTERFACES.md §5):

- ``du-gold/1``      — independently authored ground truth, one JSON object per
  sample, bound to one original by ``source_sha256``.
- ``du-observed/1``  — what one observation entry point actually produced,
  including its real entry point/version/counters.
- ``du-evaluation/1``— the oracle result: PASS / FAIL / PARTIAL / UNAVAILABLE
  plus per-check rows, metrics, not_evaluated rows and execution facts.

The module is deliberately dependency-free: it must not import
``company_wiki`` so that the measurement cannot be shaped by the system it
measures. Everything is plain JSON-serializable ``Mapping`` data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

GOLD_SCHEMA_VERSION = "du-gold/1"
OBSERVED_SCHEMA_VERSION = "du-observed/1"
EVALUATION_SCHEMA_VERSION = "du-evaluation/1"

# check statuses
PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
UNAVAILABLE = "UNAVAILABLE"
NOT_EVALUATED = "NOT_EVALUATED"

CHECK_STATUSES = frozenset({PASS, FAIL, PARTIAL, UNAVAILABLE, NOT_EVALUATED})
OVERALL_STATUSES = frozenset({PASS, FAIL, PARTIAL, UNAVAILABLE})

# fact importance
CRITICAL = "critical"
NORMAL = "normal"
IMPORTANCES = frozenset({CRITICAL, NORMAL})

# gold scope
DEVELOPMENT = "development"
HOLDOUT = "holdout"
SCOPES = frozenset({DEVELOPMENT, HOLDOUT})

# fact scope: which layer of the pipeline is answerable for the fact.
#   narrative     - business content the evidence selection is responsible for
#   document_meta - front matter, provenance, carrier or period facts that a
#                   metadata/front-end layer owns rather than the selector
# Splitting these keeps a recall denominator interpretable: mixing them would
# blame the selector for facts it was never scoped to carry.
NARRATIVE = "narrative"
DOCUMENT_META = "document_meta"
FACT_SCOPES = frozenset({NARRATIVE, DOCUMENT_META})

REQUIRED_BUSINESS = "required_business"
DISPOSITION_CONTEXT = "disposition_context"
CORRECTNESS_IF_EMITTED = "correctness_if_emitted"
TARGET_KINDS = frozenset({REQUIRED_BUSINESS, DISPOSITION_CONTEXT, CORRECTNESS_IF_EMITTED})

# claim modality: who is speaking and whether it happened
MODALITY_VALUES = frozenset(
    {
        "actual",  # happened / is true in the reporting period
        "plan",  # forward-looking intention or target
        "negation",  # explicitly denied
        "question",  # posed by a questioner, not asserted by the company
        "third_party",  # analyst/media/research-house assertion
        "conditional",  # contingent on a precondition
        "unknown",
    }
)

# claim role: whose voice the statement belongs to
ROLE_VALUES = frozenset(
    {
        "company_filing",
        "company_statement",
        "management_answer",
        "management_prepared",
        "analyst_question",
        "analyst_statement",
        "editorial_summary",
        "operator",
        "third_party",
        "unknown",
    }
)

# quantity basis: what a number counts
QUANTITY_BASIS_VALUES = frozenset(
    {
        "total",  # cumulative stock at a point in time
        "incremental",  # net change / new additions over a period
        "period_flow",  # revenue, profit, GMV earned during a period
        "investment",  # capex / project investment amount
        "capacity_total",
        "capacity_new",
        "projected_output",  # a plan number, not realised
        "count",
        "ratio",
        "unknown",
    }
)

# evaluation dimensions
DIMENSION_ROUTE = "route_type"
DIMENSION_RECALL = "critical_fact_recall"
DIMENSION_CONTEXT = "context_completeness"
DIMENSION_REPLAY = "citation_replay"
DIMENSION_BASIS = "role_modality_quantity"
DIMENSION_BILINGUAL = "bilingual_redundancy"
DIMENSION_DERIVED = "derived_space"
DIMENSION_RESOURCE = "time_resource"
DIMENSION_INTEGRITY = "observation_integrity"

DIMENSIONS = (
    DIMENSION_ROUTE,
    DIMENSION_RECALL,
    DIMENSION_CONTEXT,
    DIMENSION_REPLAY,
    DIMENSION_BASIS,
    DIMENSION_BILINGUAL,
    DIMENSION_DERIVED,
    DIMENSION_RESOURCE,
    DIMENSION_INTEGRITY,
)

# Coverage/native_scan enum shared with du-input/1.
NATIVE_SCAN_VALUES = frozenset({"complete", "partial", "unavailable"})

# Character blocks that appear in broken CID font mappings and essentially never
# in legitimate prose of any language. Shared by the observer, which measures
# legibility over everything the parser read, and the checker, which judges it.
#
# Chosen from a measured control rather than guessed: seven real originals were
# scored on the share of characters in these blocks. Clean Chinese filings
# measured 0.000%-0.076% (worst case a 136k-character traditional-Chinese annual
# report); a genuinely garbled 415-page PDF measured 2.663%.
UNUSABLE_BLOCKS: tuple[tuple[int, int], ...] = (
    (0x2E80, 0x2EFF),  # CJK radicals supplement
    (0x2F00, 0x2FDF),  # Kangxi radicals
    (0x31C0, 0x31EF),  # CJK strokes
    (0x2400, 0x243F),  # control pictures
    (0xE000, 0xF8FF),  # private use area
    (0x4DC0, 0x4DFF),  # Yijing hexagram symbols
    (0x2500, 0x257F),  # box drawing
)
MAX_UNUSABLE_BLOCK_RATIO = 0.005
MIN_LEGIBILITY_CHARS = 200


class BenchmarkSchemaError(ValueError):
    """A record violates the frozen wire schema."""


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkSchemaError(f"{what} must be a mapping")
    return value


def _require_text(value: Any, what: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise BenchmarkSchemaError(f"{what} must be a string")
    if not allow_empty and not value:
        raise BenchmarkSchemaError(f"{what} must be non-empty")
    return value


def _require_sha256(value: Any, what: str) -> str:
    text = _require_text(value, what)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise BenchmarkSchemaError(f"{what} must be a lowercase SHA-256 hex digest")
    return text


def _optional_text(value: Any, what: str) -> str | None:
    """Optional text: ``None`` and ``""`` both mean "not supplied".

    Field absence is ``unknown`` in this contract, never a review trigger, so an
    empty optional string is normalized to ``None`` rather than rejected.
    """

    if value is None:
        return None
    if isinstance(value, str) and not value:
        return None
    return _require_text(value, what)


def _require_sequence(value: Any, what: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise BenchmarkSchemaError(f"{what} must be an array")
    return value


def _optional_sequence(value: Any, what: str) -> Sequence[Any]:
    if value is None:
        return ()
    return _require_sequence(value, what)


def _require_enum(value: Any, allowed: frozenset[str], what: str) -> str:
    text = _require_text(value, what)
    if text not in allowed:
        raise BenchmarkSchemaError(f"{what} must be one of {sorted(allowed)}")
    return text
