"""Collect-all static pre-flight linter for schema inputs.

Unlike the engine's own validators (which fail fast on the first violation),
this linter accumulates **every** structural / reference / hash / aggregate
finding it can detect without running the forecast, so an author can fix several
problems per round-trip. It is a pre-flight only — the engine remains
authoritative for semantic checks this linter does not replicate.

Hash checks reuse ``fix_hashes.find_hash_drift`` (which itself reuses the
engine's ``canonical_sha256`` / ``text_sha256``), guaranteeing byte-for-byte
agreement with the engine.

CLI mirrors ``revenue_forecast.py``: positional input path, exit 0 when clean /
exit 2 when any finding is reported.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fix_hashes
from schema_fields import (  # ZR-702: single source of truth (REV-01/03)
    CAPTURE_REQUIRED,
    CLAIM_REQUIRED,
    PARAMETER_REQUIRED,
    TOP_LEVEL_REQUIRED,
)


def _finding(category: str, path: str, message: str) -> dict[str, str]:
    return {"category": category, "path": path, "message": message}


def _check_top_level(data: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _finding("top_level_shape", key, f"missing required top-level field: {key}")
        for key in TOP_LEVEL_REQUIRED
        if key not in data
    ]


def _check_capture_shape(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for source in data.get("sources", []):
        if not isinstance(source, dict):
            continue
        sid = source.get("source_id", "<unknown>")
        capture = source.get("capture")
        if not isinstance(capture, dict):
            findings.append(
                _finding(
                    "capture_shape",
                    f"sources.{sid}.capture",
                    f"source {sid} is missing a capture object",
                )
            )
            continue
        if set(capture) != set(CAPTURE_REQUIRED):
            findings.append(
                _finding(
                    "capture_shape",
                    f"sources.{sid}.capture",
                    f"source {sid} capture must have exactly the required fields; "
                    f"missing={sorted(set(CAPTURE_REQUIRED) - set(capture))} "
                    f"unexpected={sorted(set(capture) - set(CAPTURE_REQUIRED))}",
                )
            )
    return findings


def _check_claim_shape(claims: list[Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("claim_id", "<unknown>")
        for key in CLAIM_REQUIRED:
            if key not in claim:
                findings.append(
                    _finding(
                        "claim_shape",
                        f"evidence_claims.{cid}",
                        f"claim {cid} is missing required field: {key}",
                    )
                )
    return findings


def _check_parameter_shape(parameters: list[Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        pid = parameter.get("parameter_id", "<unknown>")
        for key in PARAMETER_REQUIRED:
            if key not in parameter:
                findings.append(
                    _finding(
                        "parameter_shape",
                        f"parameters.{pid}",
                        f"parameter {pid} is missing required field: {key}",
                    )
                )
    return findings


def _check_references(
    data: dict[str, Any],
    source_ids: set[str],
    claim_index: dict[str, dict[str, Any]],
    parameter_index: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for parameter in data.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        pid = parameter.get("parameter_id", "<unknown>")
        for sid in parameter.get("source_ids", []):
            if sid not in source_ids:
                findings.append(
                    _finding(
                        "reference",
                        f"parameters.{pid}.source_ids",
                        f"parameter {pid} references unknown source {sid}",
                    )
                )
        for cid in parameter.get("claim_ids", []):
            if cid not in claim_index:
                findings.append(
                    _finding(
                        "reference",
                        f"parameters.{pid}.claim_ids",
                        f"parameter {pid} references unknown claim {cid}",
                    )
                )
            else:
                claim = claim_index[cid]
                if (
                    claim.get("target_type") != "parameter"
                    or claim.get("target_id") != pid
                ):
                    findings.append(
                        _finding(
                            "reference",
                            f"parameters.{pid}.claim_ids",
                            f"claim {cid} does not support parameter {pid}",
                        )
                    )
    for record in data.get("historical_revenue", []):
        if not isinstance(record, dict):
            continue
        year = record.get("year")
        for cid in record.get("claim_ids", []):
            if cid not in claim_index:
                findings.append(
                    _finding(
                        "reference",
                        f"historical_revenue.{year}.claim_ids",
                        f"historical revenue {year} references unknown claim {cid}",
                    )
                )
            elif claim_index[cid].get("target_id") != f"historical_revenue:{year}":
                findings.append(
                    _finding(
                        "reference",
                        f"historical_revenue.{year}.claim_ids",
                        f"claim {cid} does not support historical_revenue:{year}",
                    )
                )
    for pid in data.get("base_adjustment_parameter_ids", []):
        if pid not in parameter_index:
            findings.append(
                _finding(
                    "reference",
                    "base_adjustment_parameter_ids",
                    f"unknown base adjustment parameter {pid}",
                )
            )
    return findings


def _check_hashes(data: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _finding(
            "hash",
            entry["path"],
            f"{entry['kind']} hash drift: expected {entry['expected']}",
        )
        for entry in fix_hashes.find_hash_drift(data)
    ]


_DIGIT_RE = re.compile(r"\d[\d,.]*")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")


def _conclusion_digit_tokens(text: str) -> list[str]:
    """Extract figure tokens from text, skipping years / dates / identifiers.

    Heuristic-only exclusions: ISO dates (2026-05-13), bare four-digit years,
    ``FY``-prefixed years, tokens glued to an ASCII letter (Qwen3.6, Model5,
    YoY9.5%), and date expressions such as 6月底 / 7月初 / 6月18日 (a short token
    followed by a date-context character). What remains is treated as a factual
    figure.

    Known trade-offs (warn-only, false-negative direction is safe): a bare
    four-digit quantity (``用戶5000萬``) or a version number glued to a letter
    (``YoY9.5%``) is skipped and will not be reported.
    """
    text = _ISO_DATE_RE.sub(" ", text)
    tokens: list[str] = []
    for match in _DIGIT_RE.finditer(text):
        token = match.group(0)
        if re.fullmatch(r"\d{4}", token):
            continue  # bare four-digit year
        if text[max(0, match.start() - 2) : match.start()].upper() == "FY":
            continue  # FY-prefixed year
        if (
            match.start() > 0
            and text[match.start() - 1].isascii()
            and text[match.start() - 1].isalpha()
        ):
            continue  # identifier suffix (Qwen3.6, Model5)
        if match.end() < len(text) and text[match.end()] in "月日旬底初末中":
            continue  # date expression (6月底 / 7月初 / 6月18日)
        if (
            match.end() + 1 < len(text)
            and text[match.end()] == "-"
            and text[match.end() + 1].isascii()
            and text[match.end() + 1].isalpha()
        ):
            continue  # form / identifier number (SEC 6-K)
        tokens.append(token)
    return tokens


def _token_numeric_value(token: str) -> float | None:
    """Numeric value of a token, or None when it is not a plain number.

    Tokens like ``1.2.3`` or ``2026.06.18`` pass the digit regex but are not
    floats; the heuristics must never raise (lint contract: "never raises").
    """
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def _figure_values(text: str) -> set[float]:
    """Numeric values of the figure tokens in ``text`` (commas stripped)."""
    values: set[float] = set()
    for token in _conclusion_digit_tokens(text):
        value = _token_numeric_value(token)
        if value is not None:
            values.add(value)
    return values


def _bound_claim_ids(
    record: dict[str, Any],
    data: dict[str, Any],
    parameter_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> set[str]:
    """Claims traceable from a coverage record (via parameters, sources, targets)."""
    bound: set[str] = set()
    pids = set(record.get("parameter_ids") or [])
    sids = set(record.get("source_ids") or [])
    for cid, claim in claim_index.items():
        if not isinstance(claim, dict):
            continue
        if claim.get("source_id") in sids:
            bound.add(cid)
        if claim.get("target_type") == "parameter" and claim.get("target_id") in pids:
            bound.add(cid)
    for pid in pids:
        bound.update(parameter_index.get(pid, {}).get("claim_ids") or [])
    for tid in record.get("material_revenue_target_ids") or []:
        for target in data.get("management_targets") or []:
            if isinstance(target, dict) and target.get("target_id") == tid:
                bound.update(target.get("claim_ids") or [])
    return bound


def _check_conclusion_facts(
    data: dict[str, Any],
    parameter_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Heuristic: conclusion figures without claim backing.

    Every digit token in a coverage conclusion should be traceable to a claim whose
    excerpt contains it. Warns (never blocks) when a token has no backing, so an
    author can decide to downgrade the statement or add a sourced claim.

    Matching is exact numeric-value equality against bound claim excerpts; unit
    normalization (亿 vs billion) is intentionally out of scope — a conclusion
    citing ``3,800億`` next to an English excerpt ``RMB 380 billion`` is reported
    and the author reconciles it.
    """
    findings: list[dict[str, str]] = []
    records: list[tuple[dict[str, Any], str, str]] = []
    for record in data.get("research_coverage", []):
        if isinstance(record, dict):
            records.append(
                (record, "research_coverage", record.get("dimension", "<unknown>"))
            )
    for record in data.get("management_communication_coverage", []):
        if isinstance(record, dict):
            records.append(
                (
                    record,
                    "management_communication_coverage",
                    record.get("category", "<unknown>"),
                )
            )
    for record, section, name in records:
        conclusion = record.get("conclusion")
        if not isinstance(conclusion, str):
            continue
        tokens = _conclusion_digit_tokens(conclusion)
        if not tokens:
            continue
        bound = _bound_claim_ids(record, data, parameter_index, claim_index)
        backed_values: set[float] = set()
        for cid in bound:
            excerpt = (
                claim_index[cid].get("excerpt", "")
                if isinstance(claim_index[cid], dict)
                else ""
            )
            backed_values |= _figure_values(excerpt)
        uncovered = []
        for token in tokens:
            value = _token_numeric_value(token)
            if value is not None and value not in backed_values:
                uncovered.append(token)
        if uncovered:
            findings.append(
                _finding(
                    "conclusion-facts",
                    f"{section}.{name}",
                    f"結論含數字但無 claim 背書: {', '.join(uncovered)}",
                )
            )
    return findings


def _period_year(period: Any) -> int | None:
    """First four-digit year inside a period string (FY2028, FY2026-FY2028)."""
    if not isinstance(period, str):
        return None
    match = re.search(r"\d{4}", period)
    return int(match.group(0)) if match else None


def _collect_absolute_level_parameter_ids(data: dict[str, Any]) -> set[str]:
    """Parameter IDs that are absolute-level drivers (no propagation across years).

    usage_platform eligible_activity / monetization_rate, forecast adjustments
    and recognition progress parameters set a level per year; shocking an
    earlier year does not propagate to the terminal year. direct_growth
    growth_rate is compound (propagating) and therefore excluded.

    Scope note (warn-only, false-negative direction is safe): other rowwise
    models (direct_revenue, unit_sales, capacity_utilization, ...) are also
    non-propagating but are not collected here; a missed warning is harmless
    compared to a false one. recognition progress in ``lagged_activity`` with
    carry-in may still propagate — accepted imprecision of the heuristic.
    """
    ids: set[str] = set()
    for segment in data.get("segments", []):
        if not isinstance(segment, dict):
            continue
        for scenario in segment.get("scenarios", {}).values():
            if (
                not isinstance(scenario, dict)
                or scenario.get("model") != "usage_platform"
            ):
                continue
            drivers = scenario.get("driver_parameter_ids") or {}
            ids.update(drivers.get("eligible_activity") or [])
            ids.update(drivers.get("monetization_rate") or [])
        recognition = segment.get("recognition")
        if isinstance(recognition, dict):
            for ids_list in (recognition.get("progress_parameter_ids") or {}).values():
                ids.update(ids_list)
    for adjustment in data.get("forecast_adjustments", []):
        if isinstance(adjustment, dict):
            for ids_list in (adjustment.get("scenario_parameter_ids") or {}).values():
                ids.update(ids_list)
    return ids


def _check_sensitivity_propagation(
    data: dict[str, Any],
    parameter_index: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Warn when a sensitivity shocks an absolute-level driver before the terminal year.

    The engine recomputes correctly — a zero terminal impact is the correct result —
    but such a sensitivity carries no information for the terminal year (A11 lesson).
    Opt-in heuristic only.
    """
    forecast_years = data.get("forecast_years", [])
    if not forecast_years:
        return []
    terminal_year = max(forecast_years)
    absolute_level_ids = _collect_absolute_level_parameter_ids(data)
    findings: list[dict[str, str]] = []
    for test in data.get("sensitivity_tests", []):
        if not isinstance(test, dict):
            continue
        pid = test.get("parameter_id")
        parameter = parameter_index.get(pid)
        if not isinstance(parameter, dict):
            continue
        year = _period_year(parameter.get("period"))
        if year is None or year >= terminal_year:
            continue
        if pid in absolute_level_ids:
            findings.append(
                _finding(
                    "sensitivity-propagation",
                    f"sensitivity_tests.{pid}",
                    f"絕對水平型參數 {pid}（{parameter.get('period')}）早於終期 {terminal_year}：終期影響可能為 0，建議選用終期參數",
                )
            )
    return findings


def _check_aggregates(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    tree = data.get("growth_driver_tree")
    if isinstance(tree, dict):
        weights: dict[Any, float] = {}
        for driver in tree.get("drivers", []):
            if not isinstance(driver, dict):
                continue
            for attr in driver.get("segment_attribution", []):
                if not isinstance(attr, dict):
                    continue
                name = attr.get("segment_name")
                weight = attr.get("weight")
                if isinstance(weight, (int, float)) and not isinstance(weight, bool):
                    weights[name] = weights.get(name, 0.0) + weight
        for name, total in weights.items():
            if abs(total - 1.0) > 1e-9:
                findings.append(
                    _finding(
                        "aggregate",
                        f"growth_driver_tree.{name}",
                        f"attribution weights for segment {name} sum to {total}, expected 1.0",
                    )
                )
    coverage = data.get("research_coverage")
    if isinstance(coverage, list):
        dims = [
            record.get("dimension") for record in coverage if isinstance(record, dict)
        ]
        if len(dims) < 9:
            findings.append(
                _finding(
                    "aggregate",
                    "research_coverage",
                    f"research_coverage has {len(dims)} dimensions, expected at least 9",
                )
            )
        if len(dims) != len(set(dims)):
            findings.append(
                _finding(
                    "aggregate",
                    "research_coverage",
                    "research_coverage has duplicate dimension names",
                )
            )
    return findings


def lint(
    data: dict[str, Any],
    check_conclusion_facts: bool = False,
    check_sensitivity_propagation: bool = False,
) -> list[dict[str, str]]:
    """Return all detectable pre-flight findings; never raises.

    ``check_conclusion_facts`` warns when a coverage conclusion contains digits
    without any claim backing; ``check_sensitivity_propagation`` warns when a
    sensitivity shocks an absolute-level driver before the terminal year. Both
    are opt-in heuristics, off by default so existing behavior is unchanged.
    """
    if not isinstance(data, dict):
        return [_finding("top_level_shape", "", "input document must be a JSON object")]
    source_ids = {
        source.get("source_id")
        for source in data.get("sources", [])
        if isinstance(source, dict)
    }
    claims = data.get("evidence_claims", [])
    claim_index = {
        claim.get("claim_id"): claim for claim in claims if isinstance(claim, dict)
    }
    parameters = data.get("parameters", [])
    parameter_index = {
        parameter.get("parameter_id"): parameter
        for parameter in parameters
        if isinstance(parameter, dict)
    }
    findings: list[dict[str, str]] = []
    findings += _check_top_level(data)
    findings += _check_capture_shape(data)
    findings += _check_claim_shape(claims)
    findings += _check_parameter_shape(parameters)
    findings += _check_references(data, source_ids, claim_index, parameter_index)
    findings += _check_hashes(data)
    findings += _check_aggregates(data)
    if check_conclusion_facts:
        findings += _check_conclusion_facts(data, parameter_index, claim_index)
    if check_sensitivity_propagation:
        findings += _check_sensitivity_propagation(data, parameter_index)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="input JSON path (see contracts.constants.FORECAST_SCHEMA_VERSION)")
    parser.add_argument(
        "--check-conclusion-facts",
        action="store_true",
        help="warn when a coverage conclusion contains digits with no claim backing (heuristic, opt-in)",
    )
    parser.add_argument(
        "--check-sensitivity-propagation",
        action="store_true",
        help="warn when a sensitivity shocks an absolute-level driver before the terminal year (heuristic, opt-in)",
    )
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings = lint(
        data,
        check_conclusion_facts=args.check_conclusion_facts,
        check_sensitivity_propagation=args.check_sensitivity_propagation,
    )
    if not findings:
        print("ok: no findings")
        return 0
    for finding in findings:
        print(f"[{finding['category']}] {finding['path']}: {finding['message']}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
