"""Extracted from revenue_core.py during the R9 split (behavior-locked by tests/test_golden_behavior_lock.py)."""

from __future__ import annotations

import math
import re
from typing import Any

import copy

from contracts.constants import (
    GROWTH_DRIVER_COUNTEREVIDENCE_STATUSES,
    GROWTH_DRIVER_INFERENCE_DISTANCES,
    GROWTH_DRIVER_PERSISTENCE,
    GROWTH_DRIVER_TREE_STATUSES,
    MECHANISM_EVIDENCE_ROLES,
    MECHANISM_ROLE_SCHEMA_VERSIONS,
)
from contracts.evidence import (
    finite_number,
    require,
    validate_claim_ids,
)
from forecast.calc import (
    _string_list,
    base_forecast_parameter_ids,
    base_segment_parameter_ids,
)


def _validate_growth_driver_attribution(
    driver_id: str,
    attribution: Any,
    available_segments: set[str],
    attribution_totals: dict[str, float],
) -> tuple[set[str], list[dict[str, Any]]]:
    require(
        isinstance(attribution, list) and attribution,
        f"{driver_id}.segment_attribution must be a non-empty list",
    )
    seen_segments: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for position, item in enumerate(attribution):
        require(
            isinstance(item, dict),
            f"{driver_id}.segment_attribution[{position}] must be an object",
        )
        segment_name = item.get("segment_name")
        require(
            segment_name in available_segments,
            f"unknown growth driver segment: {segment_name}",
        )
        require(
            segment_name not in seen_segments,
            f"duplicate segment attribution in {driver_id}: {segment_name}",
        )
        seen_segments.add(segment_name)
        weight = finite_number(
            item.get("weight"), f"{driver_id}.segment_attribution[{position}].weight"
        )
        require(
            -1 <= weight <= 1 and weight != 0,
            f"growth driver attribution weight must be in [-1, 1] excluding zero: {driver_id}/{segment_name}",
        )
        attribution_totals[segment_name] += weight
        normalized.append({"segment_name": segment_name, "weight": weight})
    return seen_segments, normalized


def _validate_growth_driver_parameters(
    driver_id: str,
    parameter_ids: Any,
    parameter_index: dict[str, dict[str, Any]],
    base_parameter_ids: set[str],
    parameters_by_segment: dict[str, set[str]],
    attributed_segments: set[str],
) -> list[str]:
    require(
        isinstance(parameter_ids, list) and parameter_ids,
        f"{driver_id}.parameter_ids must be a non-empty list",
    )
    require(
        len(parameter_ids) == len(set(parameter_ids)),
        f"{driver_id}.parameter_ids contains duplicates",
    )
    for parameter_id in parameter_ids:
        require(
            parameter_id in parameter_index,
            f"unknown growth driver parameter_id: {parameter_id}",
        )
        require(
            parameter_id in base_parameter_ids,
            f"growth driver parameter_id is not used by the base forecast: {parameter_id}",
        )
        require(
            parameter_index[parameter_id].get("scenario") in (None, "all", "base"),
            f"growth driver parameter is not a base/shared assumption: {parameter_id}",
        )
        require(
            any(
                parameter_id in parameters_by_segment[segment_name]
                for segment_name in attributed_segments
            ),
            f"growth driver parameter does not affect an attributed segment: {driver_id}/{parameter_id}",
        )
    return list(parameter_ids)


def _validate_growth_driver_evidence(
    driver_id: str,
    evidence_nodes: Any,
    counterevidence_status: str,
    evidence_ids: set[str],
    source_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
    *,
    role_aware: bool = False,
) -> tuple[list[dict[str, Any]], list[str], list[str], str, str | None]:
    require(
        isinstance(evidence_nodes, list) and evidence_nodes,
        f"{driver_id}.evidence_nodes must be a non-empty list",
    )
    require(
        len(evidence_nodes) <= 10, f"{driver_id}.evidence_nodes cannot exceed 10 items"
    )
    normalized_nodes: list[dict[str, Any]] = []
    for position, node in enumerate(evidence_nodes):
        require(
            isinstance(node, dict),
            f"{driver_id}.evidence_nodes[{position}] must be an object",
        )
        evidence_id = node.get("evidence_id")
        require(
            isinstance(evidence_id, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]+", evidence_id),
            f"{driver_id}.evidence_id must be a stable identifier",
        )
        require(
            evidence_id not in evidence_ids,
            f"duplicate growth driver evidence_id: {evidence_id}",
        )
        evidence_ids.add(evidence_id)
        evidence_type = node.get("evidence_type")
        require(
            isinstance(evidence_type, str) and evidence_type.strip(),
            f"{evidence_id}.evidence_type is required",
        )
        inference_distance = node.get("inference_distance")
        require(
            inference_distance in GROWTH_DRIVER_INFERENCE_DISTANCES,
            f"unsupported inference_distance for {evidence_id}: {inference_distance}",
        )
        conclusion = node.get("conclusion")
        require(
            isinstance(conclusion, str) and conclusion.strip(),
            f"{evidence_id}.conclusion is required",
        )
        claims = validate_claim_ids(
            node.get("claim_ids"),
            claim_index,
            "growth_driver",
            evidence_id,
            f"{driver_id}.evidence_nodes[{position}]",
            "rationale_support",
        )
        node_source_ids = list(dict.fromkeys(claim["source_id"] for claim in claims))
        require(
            set(node_source_ids) <= set(source_index),
            f"unknown source in growth driver evidence: {evidence_id}",
        )
        normalized_nodes.append(
            {
                "evidence_id": evidence_id,
                "evidence_type": evidence_type.strip(),
                "inference_distance": inference_distance,
                "conclusion": conclusion.strip(),
                "claim_ids": list(node["claim_ids"]),
                "source_ids": node_source_ids,
            }
        )
    supporting_nodes = [
        node for node in normalized_nodes if node["inference_distance"] != "contrary"
    ]
    require(
        supporting_nodes,
        f"{driver_id} requires at least one non-contrary evidence node",
    )
    if counterevidence_status == "found":
        require(
            any(node["inference_distance"] == "contrary" for node in normalized_nodes),
            f"{driver_id} found counterevidence requires a contrary evidence node",
        )
    # The same checked excerpt cannot serve as both support and counterevidence.
    excerpt_distances: dict[str, set[str]] = {}
    for node in normalized_nodes:
        for claim_id in node["claim_ids"]:
            excerpt_sha = claim_index.get(claim_id, {}).get("excerpt_sha256")
            if excerpt_sha:
                excerpt_distances.setdefault(excerpt_sha, set()).add(
                    node["inference_distance"]
                )
    dual_use = [
        claim_index[next(cid for cid in node["claim_ids"]
                         if claim_index.get(cid, {}).get("excerpt_sha256") == sha)]["claim_id"]
        for sha in excerpt_distances
        if "contrary" in excerpt_distances[sha] and len(excerpt_distances[sha]) > 1
        for node in normalized_nodes
        if any(claim_index.get(cid, {}).get("excerpt_sha256") == sha for cid in node["claim_ids"])
    ]
    require(
        not dual_use,
        f"{driver_id}: the same excerpt cannot support and contradict (claims: {', '.join(sorted(set(dual_use)))})",
    )
    # A peer analogy is a reference class, never the company's own mechanism:
    # peer-based nodes are disclosed but excluded from triangulation.
    def _is_peer_based(node: dict[str, Any]) -> bool:
        return any(
            claim_index.get(claim_id, {}).get("evidence_role") == "peer_analogy"
            for claim_id in node["claim_ids"]
        )

    def _is_mechanism_support(node: dict[str, Any]) -> bool:
        return any(
            claim_index.get(claim_id, {}).get("evidence_role")
            in MECHANISM_EVIDENCE_ROLES
            for claim_id in node["claim_ids"]
        )

    peer_nodes = [node for node in supporting_nodes if _is_peer_based(node)]
    # M3-FLOW (schema 3.9): triangulation of a future-mechanism driver counts
    # only nodes asserting the operating mechanism itself. History bases,
    # financing background, value ranges, conversions, recognition policies,
    # unroled excerpts and comparisons stay disclosed but cannot combine into
    # "triangulated". Legacy schemas keep the peer-only exclusion so already
    # published triangulated results are never silently re-judged.
    if role_aware:
        core_nodes = [
            node
            for node in supporting_nodes
            if _is_mechanism_support(node)
        ]
    else:
        core_nodes = [node for node in supporting_nodes if not _is_peer_based(node)]
    evidence_types = list(
        dict.fromkeys(node["evidence_type"] for node in core_nodes)
    )
    if role_aware:
        # Independence belongs to the eligible mechanism claims, not the
        # enclosing node. Mixed history/peer claims remain disclosed but
        # their source IDs cannot fabricate a second mechanism source.
        evidence_source_ids = list(
            dict.fromkeys(
                claim_index[claim_id]["source_id"]
                for node in core_nodes
                for claim_id in node["claim_ids"]
                if claim_index[claim_id].get("evidence_role")
                in MECHANISM_EVIDENCE_ROLES
            )
        )
    else:
        evidence_source_ids = list(
            dict.fromkeys(
                source_id for node in core_nodes for source_id in node["source_ids"]
            )
        )
    evidence_status = (
        "triangulated"
        if len(evidence_types) >= 2 and len(evidence_source_ids) >= 2
        else "limited"
    )
    peer_note = None
    excluded_supporting = [
        node
        for node in supporting_nodes
        if node not in core_nodes and node not in peer_nodes
    ]
    if not core_nodes:
        if role_aware:
            peer_note = (
                f"Growth driver {driver_id} has no future-mechanism evidence: "
                "every supporting node relies on history, financing, unroled or "
                "peer-analogy claims, which cannot prove the modeled growth mechanism"
            )
        elif peer_nodes:
            peer_note = (
                f"Growth driver {driver_id} relies on peer-analogy evidence only; company-mechanism evidence is missing"
            )
    elif peer_nodes or (role_aware and excluded_supporting):
        detail = "peer-analogy evidence is disclosed but excluded from triangulation"
        if role_aware and excluded_supporting:
            detail = (
                "non-mechanism evidence (history_base, financing background, "
                "value_range, conversion, recognition_policy, unroled excerpts) "
                "is disclosed but excluded from mechanism triangulation"
            )
        peer_note = f"Growth driver {driver_id}: {detail}"
    return normalized_nodes, evidence_types, evidence_source_ids, evidence_status, peer_note


def _validate_growth_driver_record(
    driver: Any,
    position: int,
    data: dict[str, Any],
    parameter_index: dict[str, dict[str, Any]],
    source_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    prefix = f"growth_driver_tree.drivers[{position}]"
    require(isinstance(driver, dict), f"{prefix} must be an object")
    driver_id = driver.get("driver_id")
    require(
        isinstance(driver_id, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", driver_id),
        f"{prefix}.driver_id must be a stable identifier",
    )
    require(
        driver_id not in context["driver_ids"],
        f"duplicate growth driver_id: {driver_id}",
    )
    context["driver_ids"].add(driver_id)
    for field in (
        "title",
        "thesis",
        "persistence_rationale",
        "counterevidence_rationale",
    ):
        require(
            isinstance(driver.get(field), str) and driver[field].strip(),
            f"{driver_id}.{field} is required",
        )
    causal_chain = _string_list(
        driver.get("causal_chain"), f"{driver_id}.causal_chain", 2, 8
    )
    leading_indicators = _string_list(
        driver.get("leading_indicators"), f"{driver_id}.leading_indicators", 1, 8
    )
    falsifiers = _string_list(driver.get("falsifiers"), f"{driver_id}.falsifiers", 1, 8)
    attributed_segments, normalized_attribution = _validate_growth_driver_attribution(
        driver_id,
        driver.get("segment_attribution"),
        context["available_segments"],
        context["attribution_totals"],
    )
    parameter_ids = _validate_growth_driver_parameters(
        driver_id,
        driver.get("parameter_ids"),
        parameter_index,
        context["base_parameter_ids"],
        context["parameters_by_segment"],
        attributed_segments,
    )
    horizon = driver.get("horizon")
    require(isinstance(horizon, dict), f"{driver_id}.horizon must be an object")
    start_year, end_year = horizon.get("start_year"), horizon.get("end_year")
    require(
        isinstance(start_year, int) and isinstance(end_year, int),
        f"{driver_id}.horizon years must be integers",
    )
    require(
        data["forecast_years"][0]
        <= start_year
        <= end_year
        <= data["forecast_years"][-1],
        f"{driver_id}.horizon must fall inside forecast_years",
    )
    persistence = driver.get("persistence")
    require(
        persistence in GROWTH_DRIVER_PERSISTENCE,
        f"unsupported persistence for {driver_id}: {persistence}",
    )
    counterevidence_status = driver.get("counterevidence_status")
    require(
        counterevidence_status in GROWTH_DRIVER_COUNTEREVIDENCE_STATUSES,
        f"unsupported counterevidence_status for {driver_id}: {counterevidence_status}",
    )
    normalized_nodes, evidence_types, evidence_source_ids, evidence_status, peer_note = (
        _validate_growth_driver_evidence(
            driver_id,
            driver.get("evidence_nodes"),
            counterevidence_status,
            context["evidence_ids"],
            source_index,
            claim_index,
            role_aware=data.get("schema_version") in MECHANISM_ROLE_SCHEMA_VERSIONS,
        )
    )
    if peer_note:
        context["limitations"].append(peer_note)
    if counterevidence_status == "data_gap":
        context["gap_messages"].append(
            f"growth_driver:{driver_id}: counterevidence search is incomplete"
        )
    if evidence_status == "limited":
        context["limitations"].append(
            f"Growth driver {driver_id} is not triangulated across two evidence types and sources"
        )
    return {
        "driver_id": driver_id,
        "title": driver["title"].strip(),
        "thesis": driver["thesis"].strip(),
        "causal_chain": causal_chain,
        "parameter_ids": parameter_ids,
        "segment_attribution": normalized_attribution,
        "horizon": {"start_year": start_year, "end_year": end_year},
        "persistence": persistence,
        "persistence_rationale": driver["persistence_rationale"].strip(),
        "evidence_nodes": normalized_nodes,
        "evidence_types": evidence_types,
        "evidence_source_ids": evidence_source_ids,
        "evidence_status": evidence_status,
        "leading_indicators": leading_indicators,
        "falsifiers": falsifiers,
        "counterevidence_status": counterevidence_status,
        "counterevidence_rationale": driver["counterevidence_rationale"].strip(),
    }


def validate_growth_driver_tree(
    data: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    parameter_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate a generic causal tree that explains the modeled base-case revenue path."""
    tree = data.get("growth_driver_tree")
    require(isinstance(tree, dict), "growth_driver_tree must be an object")
    status = tree.get("status")
    require(
        status in GROWTH_DRIVER_TREE_STATUSES,
        f"unsupported growth_driver_tree status: {status}",
    )
    drivers = tree.get("drivers")
    require(isinstance(drivers, list), "growth_driver_tree.drivers must be a list")
    if status == "data_gap":
        require(not drivers, "growth_driver_tree data_gap cannot contain drivers")
        rationale = tree.get("rationale")
        require(
            isinstance(rationale, str) and rationale.strip(),
            "growth_driver_tree data_gap requires rationale",
        )
        return {
            "status": status,
            "rationale": rationale.strip(),
            "drivers": [],
            "gap_messages": [f"growth_driver_tree: {rationale.strip()}"],
            "limitations": ["No auditable revenue growth-driver tree is available"],
        }

    require(
        1 <= len(drivers) <= 10,
        "growth_driver_tree modeled status requires 1-10 drivers",
    )
    segment_names = [
        segment.get("name")
        for segment in data.get("segments", [])
        if isinstance(segment, dict)
    ]
    require(
        all(isinstance(name, str) and name.strip() for name in segment_names),
        "growth_driver_tree requires valid segment names",
    )
    available_segments = set(segment_names)
    base_parameter_ids = base_forecast_parameter_ids(data, parameter_index)
    parameters_by_segment = base_segment_parameter_ids(data, parameter_index)
    require(
        base_parameter_ids,
        "growth_driver_tree modeled status requires a base forecast path",
    )
    context: dict[str, Any] = {
        "available_segments": available_segments,
        "base_parameter_ids": base_parameter_ids,
        "parameters_by_segment": parameters_by_segment,
        "attribution_totals": {name: 0.0 for name in segment_names},
        "driver_ids": set(),
        "evidence_ids": set(),
        "limitations": [],
        "gap_messages": [],
    }
    normalized_drivers = [
        _validate_growth_driver_record(
            driver, position, data, parameter_index, source_index, claim_index, context
        )
        for position, driver in enumerate(drivers)
    ]
    for segment_name, total in context["attribution_totals"].items():
        require(
            math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9),
            f"growth driver attribution weights must sum to 1 for segment {segment_name}; got {total}",
        )
    return {
        "status": status,
        "drivers": normalized_drivers,
        "gap_messages": context["gap_messages"],
        "limitations": context["limitations"],
    }


def calculate_growth_driver_analysis(
    validated: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Rank causal revenue drivers by reconciled base-case terminal revenue increment."""
    tree = validated["growth_driver_tree"]
    base_contribution = result["consolidated_forecast"]["base"][
        "incremental_contribution"
    ]
    segment_increments = {
        item["name"]: float(item["terminal_incremental_revenue"])
        for item in base_contribution["segments"]
    }
    if tree["status"] == "data_gap":
        return {
            "status": "data_gap",
            "rationale": tree["rationale"],
            "top_drivers": [],
            "headwinds": [],
            "drivers": [],
            "unattributed_company_adjustments": float(base_contribution["adjustments"]),
            "reconciliation": {
                "driver_attributed_segment_increment": 0.0,
                "segment_increment_total": sum(segment_increments.values()),
                "unattributed_company_adjustments": float(
                    base_contribution["adjustments"]
                ),
                "company_increment_total": float(base_contribution["total"]),
                "difference": float(base_contribution["adjustments"])
                - float(base_contribution["total"]),
            },
        }

    output_drivers: list[dict[str, Any]] = []
    for driver in tree["drivers"]:
        by_segment = [
            {
                "segment_name": item["segment_name"],
                "weight": item["weight"],
                "terminal_incremental_revenue": segment_increments[item["segment_name"]]
                * item["weight"],
            }
            for item in driver["segment_attribution"]
        ]
        impact = sum(item["terminal_incremental_revenue"] for item in by_segment)
        output = copy.deepcopy(driver)
        output["terminal_increment_by_segment"] = by_segment
        output["estimated_base_terminal_increment"] = impact
        output_drivers.append(output)

    positive_total = sum(
        max(0.0, driver["estimated_base_terminal_increment"])
        for driver in output_drivers
    )
    for driver in output_drivers:
        driver["share_of_positive_driver_increment"] = (
            None
            if positive_total == 0
            else max(0.0, driver["estimated_base_terminal_increment"]) / positive_total
        )

    def summary(driver: dict[str, Any]) -> dict[str, Any]:
        return {
            "driver_id": driver["driver_id"],
            "title": driver["title"],
            "thesis": driver["thesis"],
            "estimated_base_terminal_increment": driver[
                "estimated_base_terminal_increment"
            ],
            "share_of_positive_driver_increment": driver[
                "share_of_positive_driver_increment"
            ],
            "segment_names": [
                item["segment_name"] for item in driver["segment_attribution"]
            ],
            "causal_chain": list(driver["causal_chain"]),
            "evidence_status": driver["evidence_status"],
            "leading_indicators": list(driver["leading_indicators"]),
            "falsifiers": list(driver["falsifiers"]),
        }

    positive = sorted(
        (
            driver
            for driver in output_drivers
            if driver["estimated_base_terminal_increment"] > 0
        ),
        key=lambda driver: (
            -driver["estimated_base_terminal_increment"],
            driver["driver_id"],
        ),
    )
    negative = sorted(
        (
            driver
            for driver in output_drivers
            if driver["estimated_base_terminal_increment"] < 0
        ),
        key=lambda driver: (
            driver["estimated_base_terminal_increment"],
            driver["driver_id"],
        ),
    )
    top_drivers = [
        dict(summary(driver), rank=rank)
        for rank, driver in enumerate(positive[:5], start=1)
    ]
    headwinds = [
        dict(summary(driver), rank=rank)
        for rank, driver in enumerate(negative[:5], start=1)
    ]
    attributed = sum(
        driver["estimated_base_terminal_increment"] for driver in output_drivers
    )
    segment_total = sum(segment_increments.values())
    require(
        math.isclose(attributed, segment_total, rel_tol=1e-9, abs_tol=1e-9),
        "growth driver attribution does not reconcile to segment increment",
    )
    adjustments = float(base_contribution["adjustments"])
    company_total = float(base_contribution["total"])
    return {
        "status": "modeled",
        "top_drivers": top_drivers,
        "headwinds": headwinds,
        "drivers": output_drivers,
        "unattributed_company_adjustments": adjustments,
        "reconciliation": {
            "driver_attributed_segment_increment": attributed,
            "segment_increment_total": segment_total,
            "unattributed_company_adjustments": adjustments,
            "company_increment_total": company_total,
            "difference": attributed + adjustments - company_total,
        },
    }
