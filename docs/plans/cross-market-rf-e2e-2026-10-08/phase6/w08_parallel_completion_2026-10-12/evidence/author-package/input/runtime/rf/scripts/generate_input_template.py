"""Emit a schema input skeleton pre-filled with correct field names.

The emitted ``schema_version`` is taken from
``contracts.constants.FORECAST_SCHEMA_VERSION`` (single source of truth).

The 688785 exercise showed ~65% of input-build failures are field-name / shape
mistakes the author could never infer from docs alone. This generator emits a
structurally consistent skeleton (correct keys, a strict 9-key capture, wired
parameter/claim/source references, the nine research dimensions and six
management categories) so the author fills in *values*, not field names.

Every hash is a ``0``x64 placeholder marked for recompute; the intended workflow
is: edit values/excerpts -> ``lint_input.py`` (pre-flight) -> ``fix_hashes.py``
(recompute hashes) -> ``revenue_forecast.py --validate-only``.

CLI mirrors ``revenue_forecast.py`` conventions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from revenue_core import (  # noqa: E402
    FORECAST_SCHEMA_VERSION,
    MANAGEMENT_COMMUNICATION_CATEGORIES,
    RESEARCH_DIMENSIONS,
    MONETARY_DIMENSIONS,
)
from contracts.constants import (  # noqa: E402
    OPT_IN_SCHEMA_VERSION,
    SUPPORTED_FORECAST_SCHEMA_VERSIONS,
)
from model_registry import MODEL_REGISTRY
from model_extensions import EXTENSION_OPENING_BALANCES

PLACEHOLDER_HASH = "0" * 64


def build_template(
    name: str,
    base_year: int,
    forecast_years: list[int],
    currency: str,
    unit: str,
    segment_names: list[str],
    segment_models: dict[str, str] | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Build a schema skeleton with FIXME placeholders and consistent references."""
    base_year = int(base_year)
    forecast_years = sorted({int(year) for year in forecast_years})
    segment_models = segment_models or {}
    if set(segment_models) - set(segment_names):
        raise ValueError("segment_models contains an unknown segment")
    if any(model not in MODEL_REGISTRY for model in segment_models.values()):
        raise ValueError("segment_models contains an unknown revenue model")
    # M3-FLOW: opt-in schema choice. The default stays the canonical 3.7; 3.8
    # adds operating_units and 3.9 adds typed dated period flows plus the
    # role-aware mechanism triangulation. The skeleton stays annual-basis —
    # a dated flow is authored per parameter, never defaulted (no fabricated
    # start dates).
    if schema_version is None:
        schema_version = FORECAST_SCHEMA_VERSION
    if schema_version not in SUPPORTED_FORECAST_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported schema_version {schema_version!r}; choose one of "
            f"{sorted(SUPPORTED_FORECAST_SCHEMA_VERSIONS)}"
        )
    if schema_version == OPT_IN_SCHEMA_VERSION:
        operating_units: list[dict[str, Any]] | None = []
    else:
        operating_units = None
    as_of = f"{base_year + 1}-06-30"
    source_id = "src_primary_filing"
    monetary_unit = f"{currency} {unit}"

    source: dict[str, Any] = {
        "source_id": source_id,
        "source_type": "exchange_filing",
        "title": "FIXME: filing title",
        "publisher": "FIXME: filing publisher or exchange",
        "url": "https://FIXME.invalid/replace-with-real-filing-url",
        "published_date": f"{base_year + 1}-03-01",
        "accessed_date": as_of,
        "page_or_section": "FIXME: revenue note page or section",
        "capture": {
            "capture_schema_version": "1.0",
            "capture_method": "browser_open",
            "tool_name": "FIXME: capture tool name",
            "tool_call_id": "FIXME: capture tool call id",
            "captured_date": as_of,
            "snapshot_sha256": PLACEHOLDER_HASH,
            "content_treatment": "untrusted_data_only",
            "prompt_injection_status": "not_detected",
            "host_receipt": {
                "host_receipt_schema_version": "1.0",
                "issuer": "FIXME: host issuer",
                "environment": "FIXME: host environment",
                "tool_name": "FIXME: capture tool name",
                "action": "capture_open",
                "event_sha256": PLACEHOLDER_HASH,
                "timestamp": as_of,
                "receipt_sha256": PLACEHOLDER_HASH,
            },
            "receipt_sha256": PLACEHOLDER_HASH,
        },
    }

    parameters: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []

    def add_parameter(
        parameter_id: str,
        kind: str,
        value: float,
        period: str,
        dimension: str = "revenue",
        scenario: str | None = None,
        rationale: str | None = None,
    ) -> str:
        parameters.append(
            {
                "parameter_id": parameter_id,
                "kind": kind,
                "value": value,
                "unit": monetary_unit if dimension in {"revenue", "backlog", "monetary_balance"}
                else "ratio" if dimension == "ratio" else f"FIXME: {dimension} unit",
                "period": period,
                "definition": f"FIXME: define {parameter_id}",
                "dimension": dimension,
                "time_basis": "annual",
                "source_ids": [source_id],
                "scenario": scenario,
                "rationale": rationale,
                "claim_ids": [f"claim_{parameter_id}"],
            }
        )
        if dimension in MONETARY_DIMENSIONS:
            parameters[-1].update(currency=currency, scale=unit)
        claims.append(
            {
                "claim_id": f"claim_{parameter_id}",
                "source_id": source_id,
                "target_type": "parameter",
                "target_id": parameter_id,
                "support_type": "rationale_support",
                "research_role_status": "unclassified",
                "locator": "FIXME: locator within the source",
                "excerpt": f"FIXME: checked excerpt supporting {parameter_id}.",
                "excerpt_sha256": PLACEHOLDER_HASH,
                "content_sha256": PLACEHOLDER_HASH,
                "capture_receipt_sha256": PLACEHOLDER_HASH,
                "verification_status": "opened_and_checked",
                "verified_by": "FIXME: research agent",
                "verified_date": as_of,
            }
        )
        return parameter_id

    reported_id = "reported_total"
    add_parameter(
        reported_id,
        "reported_fact",
        0.0,
        f"FY{base_year}",
        rationale="FIXME: reported total revenue",
    )

    segment_base_ids: list[str] = []
    for segment in segment_names:
        slug = segment.lower().replace(" ", "_")
        base_pid = f"{slug}_base"
        add_parameter(
            base_pid,
            "reported_fact",
            0.0,
            f"FY{base_year}",
            rationale=f"FIXME: {segment} base revenue",
        )
        segment_base_ids.append(base_pid)

    segments: list[dict[str, Any]] = []
    for segment, base_pid in zip(segment_names, segment_base_ids):
        slug = segment.lower().replace(" ", "_")
        model = segment_models.get(segment, "direct_revenue")
        spec = MODEL_REGISTRY[model]
        scenarios: dict[str, Any] = {}
        for scenario in ("low", "base", "high"):
            driver_ids = {driver: [
                add_parameter(
                    f"{slug}_{driver}_{scenario}_{year}",
                    "analyst_assumption",
                    0.0,
                    f"FY{year}",
                    dimension=spec.dimensions[driver],
                    scenario=scenario,
                    rationale=f"FIXME: {segment} {scenario} {driver} for FY{year}",
                )
                for year in forecast_years
            ] for driver in spec.required}
            scenarios[scenario] = {
                "model": model,
                "driver_parameter_ids": driver_ids,
                "rationale": f"FIXME: {segment} {scenario} revenue path rationale",
            }
        segments.append(
            {
                "name": segment,
                "base_revenue_parameter_id": base_pid,
                "recognition": {
                    "mode": "modeled_as_recognized",
                    "timing": "point_in_time",
                    "trigger": "FIXME: recognition trigger",
                    "presentation": "gross",
                },
                "scenarios": scenarios,
            }
        )
        opening = dict(EXTENSION_OPENING_BALANCES)
        opening.update({
            "project_backlog": ("base_backlog_parameter_id", "opening_backlog", "backlog"),
            "delivery_pipeline": ("base_orders_parameter_id", "opening_orders", "quantity"),
        })
        if model in opening:
            field, driver, dimension = opening[model]
            segments[-1][field] = add_parameter(
                f"{slug}_base_{driver}", "reported_fact", 0.0,
                f"FY{base_year}", dimension=dimension,
                rationale=f"FIXME: source-linked opening {driver}",
            )

    historical: list[dict[str, Any]] = []
    for year in (base_year - 1, base_year):
        claim_id = f"claim_history_{year}"
        claims.append(
            {
                "claim_id": claim_id,
                "source_id": source_id,
                "target_type": "historical_revenue",
                "target_id": f"historical_revenue:{year}",
                "support_type": "exact_value",
                "evidence_role": "history_base",
                "locator": "FIXME: historical revenue locator",
                "excerpt": f"FIXME: checked excerpt for FY{year} revenue.",
                "excerpt_sha256": PLACEHOLDER_HASH,
                "content_sha256": PLACEHOLDER_HASH,
                "capture_receipt_sha256": PLACEHOLDER_HASH,
                "verification_status": "opened_and_checked",
                "verified_by": "FIXME: research agent",
                "verified_date": as_of,
            }
        )
        historical.append(
            {
                "year": year,
                "value": 0.0,
                "source_ids": [source_id],
                "claim_ids": [claim_id],
            }
        )

    research = [
        {
            "dimension": dimension,
            "status": "data_gap",
            "conclusion": f"FIXME: {dimension} conclusion",
            "revenue_mechanism": f"FIXME: {dimension} revenue mechanism",
            "rationale": f"FIXME: why {dimension} remains a data gap, or set status=modeled_driver and map parameters",
        }
        for dimension in RESEARCH_DIMENSIONS
    ]
    management = [
        {
            "category": category,
            "status": "not_checked",
            "source_ids": [],
            "checked_date": as_of,
            "conclusion": f"FIXME: {category} review conclusion",
            "material_revenue_target_ids": [],
        }
        for category in MANAGEMENT_COMMUNICATION_CATEGORIES
    ]

    document: dict[str, Any] = {
        "_comment": (
            f"Schema {schema_version} skeleton. Replace every FIXME value, then run: "
            "lint_input.py <file>  ->  fix_hashes.py <file>  ->  "
            "revenue_forecast.py <file> --validate-only."
            + (
                "  Schema 3.9 note: date half/quarter-year flows with "
                "time_basis=period_flow plus period_start/period_end inside the "
                "fiscal window, and give growth-driver claims an evidence_role; "
                "history/financing/peer rows stay disclosed but no longer "
                "triangulate the mechanism."
                if schema_version == "3.9"
                else ""
            )
            + (
                "  Schema 3.10 note: any real dated window is expressible with "
                "time_basis=period_flow plus period_start/period_end "
                "(period_start <= period_end) inside the fiscal window — e.g. a "
                "post-control contribution 2026-05-31..2026-06-30. Amounts belong "
                "only to their window (no implicit annualization); compose a full "
                "year only through actual input windows and their derived lineage. "
                "Rationale may explain independent scopes, a residual subtraction or "
                "a real pre-control perimeter gap; it never moves known dates or "
                "adds the same economic flow twice. Stock/rate alone is not revenue."
                if schema_version == "3.10"
                else ""
            )
        ),
        "schema_version": schema_version,
        "company_name": name,
        "as_of_date": as_of,
        "currency": currency,
        "unit": unit,
        "fiscal_year_end": "12-31",
        "base_year": base_year,
        "forecast_years": forecast_years,
        "sources": [source],
        "parameters": parameters,
        "evidence_claims": claims,
        "segments": segments,
        "reported_total_revenue_parameter_id": reported_id,
        "base_adjustment_parameter_ids": [],
        "historical_revenue": historical,
        "research_coverage": research,
        "management_communication_coverage": management,
        "growth_driver_tree": {
            "status": "data_gap",
            "drivers": [],
            "rationale": "FIXME: build a causal driver tree, or keep status=data_gap",
        },
    }
    if operating_units is not None:
        document["operating_units"] = operating_units
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True, help="company name")
    parser.add_argument(
        "--base-year", type=int, required=True, help="base fiscal year (e.g. 2025)"
    )
    parser.add_argument(
        "--forecast-years",
        type=int,
        nargs="+",
        required=True,
        help="forecast years (e.g. 2026 2027)",
    )
    parser.add_argument("--currency", default="USD", help="currency code (default USD)")
    parser.add_argument(
        "--unit", default="million", help="monetary unit (default million)"
    )
    parser.add_argument(
        "--segments", nargs="+", required=True, help="segment display names"
    )
    parser.add_argument(
        "--output", type=Path, help="write skeleton here (default stdout)"
    )
    parser.add_argument("--segment-model", action="append", default=[], metavar="SEGMENT=MODEL",
                        help="select a registered revenue model for a segment; repeat for multiple segments")
    parser.add_argument(
        "--schema",
        default=None,
        metavar="VERSION",
        help="opt-in schema version (default 3.7; 3.8 adds operating_units, 3.9 adds dated period flows and role-aware triangulation, 3.10 adds arbitrary real dated windows for consolidated contributions)",
    )
    args = parser.parse_args(argv)

    model_map = {}
    for selection in args.segment_model:
        segment, separator, model = selection.partition("=")
        if not separator or segment not in args.segments or model not in MODEL_REGISTRY or segment in model_map:
            parser.error("--segment-model requires a unique declared SEGMENT=registered_model")
        model_map[segment] = model
    try:
        data = build_template(
            args.name,
            args.base_year,
            args.forecast_years,
            args.currency,
            args.unit,
            args.segments,
            model_map,
            args.schema,
        )
    except ValueError as exc:
        parser.error(str(exc))
        raise AssertionError("unreachable")  # parser.error exits
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
