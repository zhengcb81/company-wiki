"""ZR-702: single source of truth for the schema input field
contracts (REV-01/03).

The four REQUIRED tuples below are the ONLY definition of the statically
linted field sets; ``lint_input`` imports them (it no longer carries its
own copy), and tests pin generator/validator consistency against them.
Semantics are byte-identical to the tuples previously hardcoded in
lint_input.py (pure relocation, zero behavior change).
"""

from __future__ import annotations

TOP_LEVEL_REQUIRED = (
    "schema_version",
    "company_name",
    "as_of_date",
    "currency",
    "unit",
    "fiscal_year_end",
    "base_year",
    "forecast_years",
    "sources",
    "parameters",
    "segments",
    "reported_total_revenue_parameter_id",
    "historical_revenue",
    "research_coverage",
)

CAPTURE_REQUIRED = (
    "capture_schema_version",
    "capture_method",
    "tool_name",
    "tool_call_id",
    "captured_date",
    "snapshot_sha256",
    "content_treatment",
    "prompt_injection_status",
    "host_receipt",
    "receipt_sha256",
)

CLAIM_REQUIRED = (
    "claim_id",
    "source_id",
    "target_type",
    "target_id",
    "support_type",
    "locator",
    "excerpt",
    "excerpt_sha256",
    "content_sha256",
    "capture_receipt_sha256",
    "verification_status",
)

PARAMETER_REQUIRED = (
    "parameter_id",
    "kind",
    "value",
    "unit",
    "period",
    "definition",
    "source_ids",
)

__all__ = [
    "TOP_LEVEL_REQUIRED",
    "CAPTURE_REQUIRED",
    "CLAIM_REQUIRED",
    "PARAMETER_REQUIRED",
]
