"""Construct an illustrative dated delay using the existing native formula DAG.

No engine model or capacity policy is added. Quarter amounts and cancellation
fractions are explicit caller assumptions, not inferred from annual totals.
"""
from __future__ import annotations
from copy import deepcopy
import re
from contracts.constants import SCENARIOS
from contracts.evidence import finite_number, require
from forecast.calc import evaluate_derived_formula


def build_quarter_delay_bridge(data, *, segment_name, from_period, to_period,
                               deferred_parameter_ids, catch_up_parameter_ids,
                               prefix, rationale):
    match_from = re.fullmatch(r"FY([0-9]{4})Q([1-4])", from_period)
    match_to = re.fullmatch(r"FY([0-9]{4})Q([1-4])", to_period)
    require(match_from is not None and match_to is not None, "delay periods must be fiscal quarters")
    first_year, first_quarter = map(int, match_from.groups())
    next_year, next_quarter = map(int, match_to.groups())
    require(first_quarter == 4 and next_quarter == 1 and next_year == first_year + 1,
            "annual delay bridge requires a one-quarter Q4 to next-Q1 shift")
    require(isinstance(rationale, str) and bool(rationale.strip()), "delay rationale required")
    require(isinstance(prefix, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]+", prefix)), "delay prefix invalid")
    require(set(deferred_parameter_ids) == set(catch_up_parameter_ids) == set(SCENARIOS), "delay needs all scenarios")
    out = deepcopy(data)
    years = out["forecast_years"]
    require(first_year in years and next_year in years, "delay needs both annual periods in horizon")
    index = {p["parameter_id"]: p for p in out["parameters"]}
    segment = next((s for s in out["segments"] if s["name"] == segment_name), None)
    require(segment is not None, "delay segment unknown")
    changes = {}
    for scenario in SCENARIOS:
        spec = segment["scenarios"][scenario]
        require(spec["model"] == "direct_revenue" and segment["recognition"]["mode"] == "modeled_as_recognized",
                "this aggregate bridge requires direct recognized revenue; choose an activity-specific bridge otherwise")
        require(deferred_parameter_ids[scenario] in index and catch_up_parameter_ids[scenario] in index, "delay parameter missing")
        deferred = index[deferred_parameter_ids[scenario]]
        fraction = index[catch_up_parameter_ids[scenario]]
        require(deferred["dimension"] == "revenue" and deferred.get("measurement_period") == from_period and deferred["period"] == f"FY{first_year}", "deferred amount must be explicit revenue for the source quarter")
        require(fraction["dimension"] == "ratio" and fraction["period"] == f"FY{next_year}", "catch-up fraction period/dimension mismatch")
        for p in (deferred, fraction):
            require(p.get("scenario") in (None, "all", scenario), "delay scenario mismatch")
        delay_amount = finite_number(deferred["value"], "deferred value")
        catch_up = finite_number(fraction["value"], "catch-up fraction")
        require(delay_amount >= 0 and 0 <= catch_up <= 1, "delay/cancellation bounds invalid")
        emitted = []
        for year, formula, extra_ids in ((first_year, "x0-x1", [deferred["parameter_id"]]),
                                         (next_year, "x0+x1*x2", [deferred["parameter_id"], fraction["parameter_id"]])):
            offset = years.index(year)
            old_id = spec["driver_parameter_ids"]["revenue"][offset]
            old = index[old_id]
            require(old["unit"] == deferred["unit"] and old.get("currency") == deferred.get("currency") and old.get("scale") == deferred.get("scale"), "delay unit/currency/scale mismatch")
            if year == first_year:
                require(delay_amount <= float(old["value"]), "delay cannot exceed current recognized amount")
            pid = f"{prefix}_{scenario}_{year}"
            require(pid not in index, "delay output parameter already exists")
            p = deepcopy(old)
            inputs = [old_id, *extra_ids]
            p.update(parameter_id=pid, kind="derived_fact", formula=formula, input_parameter_ids=inputs,
                     value=evaluate_derived_formula(formula, [float(index[i]["value"]) for i in inputs]),
                     definition=f"{segment_name} dated delay bridge {scenario} FY{year}",
                     rationale=rationale, claim_ids=[], source_ids=sorted({sid for i in inputs for sid in index[i].get("source_ids", [])}))
            p.pop("measurement_period", None)
            out["parameters"].append(p)
            index[pid] = p
            spec["driver_parameter_ids"]["revenue"][offset] = pid
            emitted.append({"parameter_id": pid, "formula": formula, "input_parameter_ids": inputs,
                            "value": p["value"], "unit": p["unit"]})
        changes[scenario] = {"deferred": delay_amount, "catch_up": delay_amount * catch_up,
                             "canceled": delay_amount * (1 - catch_up), "emitted": emitted}
    return out, {"schema_version": "dated-delay-bridge/1", "status": "illustrative_stress",
                 "segment_name": segment_name, "from_period": from_period, "to_period": to_period,
                 "delay_quarters": 1, "rationale": rationale, "scenarios": changes,
                 "limitations": ["Not a calibrated Low; existing scenario order and shared constraints still apply.",
                                 "Annual model cannot resolve an in-year quarterly delay; no x4 or annual sorting."]}
