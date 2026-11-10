"""Typed research projection; source verification and the revenue engine stay upstream.

The researcher declares observation kinds and scopes after reading originals.
These checks catch contradictory declarations, not business truth from keywords.
"""
from __future__ import annotations

import math
from collections import Counter
from contracts.constants import GROWTH_DRIVER_EVIDENCE_ROLES, SCENARIOS
from contracts.evidence import finite_number, require
from forecast.calc import collect_parameter_roles, evaluate_derived_formula
from research.native_dependencies import direct_parameter_cells, observation_binding, parameter_scopes

OBSERVATION_ROLES = {
    "historical_revenue_table": {"history_base"},
    "historical_level": {"history_base", "value_range"},
    "weak_demand": {"counterevidence", "counter_comparison"},
    "operating_mechanism": {"mechanism_direction"},
    "quantitative_reference": {"value_range", "peer_analogy"},
    "conversion": {"conversion_assumption"},
    "recognition_policy": {"recognition_policy"},
    "contrary_fact": {"counterevidence", "counter_comparison"},
}
DISPOSITIONS = {"modeled", "included", "subscope", "unmodeled", "materiality_skip", "unknown"}
TOPICS = {"management_target", "new_product_ramp", "revenue_recognition", "shared_bottleneck",
          "customer_financing", "competitive_constraint", "other"}


def _text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} is required")
    return value


def _ids(values, available, label):
    require(isinstance(values, list) and all(isinstance(x, str) for x in values), f"{label} must be IDs")
    require(len(values) == len(set(values)) and set(values) <= set(available), f"{label} unknown or duplicate IDs")
    return values


def _observations(rows, parameters, claims, drivers, data):
    driver_ids = set(drivers)
    require(isinstance(rows, list), "operating observations must be a list")
    seen = set()
    result = []
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"claim_id", "observation_kind", "scope", "period", "parameter_ids", "driver_ids", "rationale"}, "operating observation fields invalid")
        cid = row["claim_id"]
        require(cid in claims and cid not in seen, "operating observation claim unknown/duplicate")
        seen.add(cid)
        role = claims[cid].get("evidence_role")
        require(role in GROWTH_DRIVER_EVIDENCE_ROLES and role in OBSERVATION_ROLES.get(row["observation_kind"], set()), "operating observation contradicts evidence role")
        for key in ("scope", "period", "rationale"):
            _text(row[key], f"observation {key}")
        _ids(row["parameter_ids"], parameters, "observation parameter_ids")
        _ids(row["driver_ids"], driver_ids, "observation driver_ids")
        binding_status = observation_binding(row, claims[cid], data, parameters, drivers)
        result.append({**row, "role": role, "source_id": claims[cid]["source_id"], "locator": claims[cid]["locator"], "binding_status": binding_status})
    return result


def _inventory(rows, parameters, claims, driver_ids, used):
    require(isinstance(rows, list), "operating inventory must be a list")
    result = []
    seen = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"item_id", "topic", "disposition", "rationale", "claim_ids", "parameter_ids", "driver_ids", "recognition_note", "included_in"}, "operating inventory fields invalid")
        item_id = _text(row["item_id"], "inventory item_id")
        require(item_id not in seen, "duplicate inventory item")
        seen.add(item_id)
        require(row["topic"] in TOPICS and row["disposition"] in DISPOSITIONS, "inventory topic/disposition invalid")
        _text(row["rationale"], "inventory rationale")
        _text(row["recognition_note"], "inventory recognition_note")
        _ids(row["claim_ids"], claims, "inventory claim_ids")
        _ids(row["parameter_ids"], parameters, "inventory parameter_ids")
        _ids(row["driver_ids"], driver_ids, "inventory driver_ids")
        if row["disposition"] in {"modeled", "included", "subscope"}:
            require(row["claim_ids"] and row["parameter_ids"] and set(row["parameter_ids"]) <= used, "modeled inventory requires checked claims and used parameters")
        if row["disposition"] in {"included", "subscope"}:
            _text(row["included_in"], "inventory inclusion parent")
        else:
            require(row["included_in"] is None, "inventory inclusion only for included/subscope")
        result.append(dict(row))
    index = {r["item_id"]: r for r in result}
    for row in result:
        cursor = row
        visited = {row["item_id"]}
        while cursor["included_in"] is not None:
            parent = cursor["included_in"]
            require(parent in index and parent not in visited, "inventory inclusion unknown or cyclic")
            require(set(cursor["parameter_ids"]) <= set(index[parent]["parameter_ids"]), "inventory inclusion parameters must remain within parent")
            visited.add(parent)
            cursor = index[parent]
    return result


def _calibration(row, parameters, claims, observations, used, data):
    """Check one declared calibration relation against the native DAG.

    Independent observed-range endpoints prove their real parameter/unit/
    observed period and declared reference scope; they may sit outside the
    revenue DAG (an unused upper endpoint stays a legal reference). The actual
    conversions and forecast outputs must instead bind to the target business,
    scenario, period and the real native DAG; unrelated scope or period cannot
    be promoted by a textual calibration label.
    """
    fields = {"calibration_id", "status", "scope", "observed_period", "source_claim_ids", "counterevidence_claim_ids", "observed_range", "conversion_formula", "output_unit", "scenario_input_parameter_ids", "scenario_output_parameter_ids", "rationale", "limitations"}
    require(isinstance(row, dict) and set(row) == fields, "calibration fields invalid")
    for key in ("calibration_id", "scope", "observed_period", "conversion_formula", "output_unit", "rationale"):
        _text(row[key], f"calibration {key}")
    require(row["status"] in {"calibrated", "unverified", "stress"}, "calibration status invalid")
    _ids(row["source_claim_ids"], claims, "calibration source claims")
    _ids(row["counterevidence_claim_ids"], claims, "calibration counterevidence claims")
    require(all(claims[c].get("evidence_role") in {"counterevidence", "counter_comparison"} for c in row["counterevidence_claim_ids"]), "calibration counterevidence role invalid")
    require(isinstance(row["limitations"], list) and all(isinstance(x, str) and x.strip() for x in row["limitations"]), "calibration limitations must be explicit strings")
    input_map = row["scenario_input_parameter_ids"]
    output_map = row["scenario_output_parameter_ids"]
    require(isinstance(input_map, dict) and isinstance(output_map, dict) and set(input_map) == set(output_map) == set(SCENARIOS), "calibration requires all three scenario maps")
    observed = row["observed_range"]
    reasons = []
    obs_index = {o["claim_id"]: o for o in observations}
    range_claims = [claims[c] for c in row["source_claim_ids"] if claims[c].get("evidence_role") == "value_range"]
    if observed is None:
        reasons.append("observed_range_unknown")
    else:
        require(isinstance(observed, dict) and set(observed) == {"lower", "upper", "unit"}, "observed range fields invalid")
        lower = finite_number(observed["lower"], "observed lower")
        upper = finite_number(observed["upper"], "observed upper")
        require(lower <= upper, "observed range order invalid")
        _text(observed["unit"], "observed unit")
        scoped = [c for c in range_claims if c["claim_id"] in obs_index and
                  obs_index[c["claim_id"]]["scope"] == row["scope"] and
                  obs_index[c["claim_id"]]["period"] == row["observed_period"] and
                  c.get("unit") == observed["unit"] and c.get("period") == row["observed_period"]]
        endpoints = [c.get("extracted_value") for c in scoped]
        if not all(any(type(v) in (int, float) and math.isclose(v, bound, rel_tol=0, abs_tol=1e-9) for v in endpoints) for bound in (lower, upper)):
            reasons.append("range_endpoints_period_or_scope_not_supported")
    scenarios = {}
    native_business = {data.get("company_name")} | {s["name"] for s in data.get("segments", [])}
    if row["scope"] not in native_business:
        reasons.append(f"calibration_scope_not_native_business:{row['scope']}")
    for scenario in SCENARIOS:
        inputs = _ids(input_map[scenario], parameters, "calibration inputs")
        require(bool(inputs), "calibration inputs cannot be empty")
        output_id = output_map[scenario]
        require(output_id in parameters and output_id in used, "calibration output must be a used parameter")
        output = parameters[output_id]
        require(output.get("scenario") in (None, "all", scenario), "calibration output scenario mismatch")
        require(output["unit"] == row["output_unit"], "calibration output unit mismatch")
        values = [float(parameters[p]["value"]) for p in inputs]
        formula_value = evaluate_derived_formula(row["conversion_formula"], values)
        matched = math.isclose(formula_value, float(output["value"]), rel_tol=1e-9, abs_tol=1e-9)
        # Explicit unit conversion is represented by the same native formula;
        # observed input cannot silently become a different scale or TTM period.
        if observed is not None:
            if parameters[inputs[0]].get("measurement_period", parameters[inputs[0]]["period"]) != row["observed_period"]:
                reasons.append("observed_input_period_mismatch")
            if parameters[inputs[0]]["unit"] != observed["unit"]:
                reasons.append("observed_input_unit_mismatch")
            if not lower <= values[0] <= upper:
                reasons.append("scenario_reference_outside_observed_range")
        if not matched:
            reasons.append("conversion_formula_mismatch")
        if output.get("kind") != "derived_fact" or output.get("formula") != row["conversion_formula"] or output.get("input_parameter_ids") != inputs:
            reasons.append("native_derived_conversion_not_linked")
        conversion_ids = inputs[1:]
        conversion_observations = [o for o in observations if o["role"] == "conversion_assumption"]
        if any(not any(pid in o["parameter_ids"] for o in conversion_observations) for pid in conversion_ids):
            reasons.append("conversion_assumption_not_disclosed")
        # Scoped binding: an actual conversion must be carried by a bound
        # conversion observation; unbound text labels cannot promote an
        # unrelated business scope or period to supported conversions.
        for pid in conversion_ids:
            covering = [o for o in conversion_observations if pid in o["parameter_ids"]]
            if covering and not any(o["binding_status"] == "bound" for o in covering):
                unbound = covering[0]
                reasons.append(f"conversion_observation_{unbound['binding_status']}:{pid}:{unbound['claim_id']}")
            # The annual parameter period is the native applicability context;
            # measurement/claim/source dates retain their independent meaning.
            # A historical factor can be carried by a real target-period
            # derived node; no text label or self-consistent future observation
            # alone makes a direct conversion applicable to this output.
            conversion_period = parameters[pid]["period"]
            if conversion_period != output["period"]:
                claim_ids = ",".join(sorted({o["claim_id"] for o in covering}))
                reasons.append(f"conversion_output_period_mismatch:{pid}:{conversion_period}:{output_id}:{output['period']}:{claim_ids}")
        for segment, cell_scenario, cell_period in direct_parameter_cells(
            data, output_id, scope=row["scope"], scenario=scenario
        ):
            if output["period"] != cell_period:
                reasons.append(f"calibration_output_consumption_period_mismatch:{output_id}:{output['period']}:{segment}:{cell_scenario}:{cell_period}")
        # The forecast output must be consumed by the declared business scope
        # inside the real native DAG; a different company or total market is
        # not automatically the same perimeter.
        output_scopes = parameter_scopes(data, parameters, output_id)
        if row["scope"] != data.get("company_name") and row["scope"] not in output_scopes:
            reasons.append(f"calibration_output_scope_mismatch:{output_id}:{row['scope']}->{'/'.join(sorted(output_scopes))}")
        scenarios[scenario] = {"input_parameter_ids": inputs, "output_parameter_id": output_id,
                               "formula_value": formula_value, "native_value": float(output["value"]),
                               "output_unit": output["unit"], "matches_native": matched}
    reasons = sorted(set(reasons))
    status = "referenced_range" if row["status"] == "calibrated" and not reasons else "stress" if row["status"] == "stress" else "unverified"
    return {**row, "adequacy_status": status, "reasons": reasons, "scenario_conversion": scenarios}


def analyze_operating_research(data, validated):
    """Project declared scope/roles and source range to actual used formula inputs.

    Absent optional data emits nothing and cannot change legacy stable-fsum/1.
    A documented range is not proof of empirical accuracy or probability coverage.
    """
    research = data.get("operating_research")
    if research is None:
        return None
    require(isinstance(research, dict) and set(research) == {"schema_version", "inventory", "observations", "calibrations"} and research["schema_version"] == "operating-research/1", "operating research fields/schema invalid")
    parameters = validated["parameter_index"]
    claims = validated["claim_index"]
    roles = collect_parameter_roles(data, parameters)
    drivers = {d["driver_id"]: d for d in data.get("growth_driver_tree", {}).get("drivers", [])}
    driver_ids = set(drivers)
    observations = _observations(research["observations"], parameters, claims, drivers, data)
    inventory = _inventory(research["inventory"], parameters, claims, driver_ids, roles["used"])
    require(isinstance(research["calibrations"], list), "calibrations must be a list")
    calibrations = [_calibration(r, parameters, claims, observations, roles["used"], data) for r in research["calibrations"]]
    ids = [c["calibration_id"] for c in calibrations]
    require(len(ids) == len(set(ids)), "duplicate calibration ID")
    mechanisms = sorted({pid for o in observations if o["role"] == "mechanism_direction" and o["binding_status"] == "bound" for pid in o["parameter_ids"] if pid in roles["forecast"]})
    magnitude = sorted({pid for c in calibrations if c["adequacy_status"] == "referenced_range" for pid in c["scenario_output_parameter_ids"].values()})
    limitations = ["Typed observations reflect researcher declarations; source bytes/parser/locators do not prove economic direction or magnitude.",
                   "Referenced range is a documented conversion, not empirical forecast/probability calibration."]
    uncovered = sorted(roles["forecast"] - set(magnitude))
    if uncovered:
        limitations.append("Magnitude unknown/unverified for forecast parameters without a scoped referenced-range conversion.")
    unresolved = [r["item_id"] for r in inventory if r["disposition"] in {"unknown", "unmodeled"}]
    if unresolved:
        limitations.append("Operating content remains unknown/unmodeled: " + ", ".join(unresolved))
    return {"schema_version": "research-adequacy/1", "inventory": inventory, "evidence_roles": observations,
            "calibrations": calibrations, "documentary_presence": {"checked_claim_count": len(claims)},
            "mechanism_adequacy": {"supported_parameter_ids": mechanisms, "unverified_parameter_ids": sorted(roles["forecast"] - set(mechanisms))},
            "magnitude_adequacy": {"supported_parameter_ids": magnitude, "unverified_parameter_ids": uncovered, "status": "referenced_range" if magnitude else "unknown"},
            "inventory_counts": dict(sorted(Counter(r["disposition"] for r in inventory).items())),
            "limitations": limitations}
