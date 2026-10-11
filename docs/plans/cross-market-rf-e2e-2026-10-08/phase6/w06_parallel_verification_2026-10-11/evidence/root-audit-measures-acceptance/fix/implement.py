"""Systemic typed-boundary repair in the single authorized ROOT worktree."""
from pathlib import Path

path = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root/skills/revenue-forecast-audit/scripts/financial_measure_audit.py")
source = path.read_text(encoding="utf-8")
source = source.replace("from decimal import Decimal, InvalidOperation, localcontext", "from decimal import Decimal, DecimalException, InvalidOperation, localcontext")
source = source.replace("import json\n", "import json\nimport re\n", 1)
source = source.replace('COMPARE_EPSILON = Decimal("1e-9")', 'COMPARE_EPSILON = Decimal("1e-20")')

def replace_function(start, end, code):
    global source
    a = source.index("def " + start + "(")
    b = source.index("def " + end + "(", a)
    source = source[:a] + code.strip() + "\n\n\n" + source[b:]

replace_function("_parse_date", "_allowed_scales", '''
def _parse_date(value, field, diags):
    if value is None:
        return None, True
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        diags.append(_diag("invalid_date", f"{field} must be YYYY-MM-DD text"))
        return None, False
    try:
        return dt.date.fromisoformat(value), True
    except ValueError:
        diags.append(_diag("invalid_date", f"{field} must be a real YYYY-MM-DD date"))
        return None, False
''')

replace_function("_check_observation", "_compare_values", '''
def _check_observation(row, seen_ids, as_of=None):
    """Normalize once, preserving typed/provenance status for dependent relations."""
    diags = []
    states = []
    def issue(status, code, detail):
        states.append(status)
        diags.append(_diag(code, detail))

    if not isinstance(row, dict):
        return (_check("obs:<invalid>", "observation", None, "INVALID", None, None,
                       None, None, None, [_diag("not_object", "observation must be an object")]), None)
    oid = row.get("id")
    if not isinstance(oid, str) or not oid.strip():
        issue("INVALID", "missing_id", "observation id must be nonempty text")
        oid = None
    elif oid in seen_ids:
        issue("INVALID", "duplicate_id", f"duplicate observation id {oid!r}")
    else:
        seen_ids.add(oid)

    value = None
    try:
        value = numeric_audit.decimal_value(row.get("value"))
    except (ValueError, DecimalException):
        issue("INVALID", "invalid_value", "value must be an explicit finite decimal, not bool/NaN/Inf")

    scale = row.get("scale")
    if not isinstance(scale, str) or scale not in SCALES:
        issue("UNRESOLVED" if scale is None else "INVALID", "unknown_scale", "scale is missing or unsupported; do not infer")
        scale = None
    kind = row.get("measure_kind")
    if not isinstance(kind, str) or kind not in MEASURE_KINDS:
        issue("UNRESOLVED" if kind is None else "INVALID", "unknown_measure_kind", "measure_kind is missing or unsupported")
        kind = None
    cur = None
    try:
        cur = numeric_audit.currency(row.get("currency"))
    except ValueError:
        issue("INVALID", "invalid_currency", "currency must be an explicit 3-letter code or null")
    currency = CURRENCY_ALIAS.get(cur, cur) if cur else None
    if cur in CURRENCY_ALIAS:
        diags.append(_diag("currency_alias", f"{cur} treated as {currency} (documented alias)"))
    if kind in DIMENSIONLESS_KINDS and currency is not None:
        issue("INVALID", "currency_on_dimensionless", f"{kind} cannot carry currency")
    if kind in ("stock", "flow") and currency is None:
        issue("UNRESOLVED", "missing_currency", "monetary stock/flow requires explicit currency")
    if kind and scale and scale not in _allowed_scales(kind):
        issue("INVALID", "scale_kind_mismatch", f"scale {scale!r} is incompatible with {kind!r}")

    fields = {}
    for name in ("entity_key", "definition"):
        raw = row.get(name)
        if not isinstance(raw, str) or not raw.strip():
            issue("UNRESOLVED" if raw is None or raw == "" else "INVALID", "missing_" + name, name + " must be explicit nonempty text")
            fields[name] = None
        else:
            fields[name] = raw

    ps, ok1 = _parse_date(row.get("period_start"), "period_start", diags)
    pe, ok2 = _parse_date(row.get("period_end"), "period_end", diags)
    pd, ok3 = _parse_date(row.get("point_date"), "point_date", diags)
    available, ok4 = _parse_date(row.get("available_by"), "available_by", diags)
    if not all((ok1, ok2, ok3, ok4)):
        states.append("INVALID")
    window = ps is not None and pe is not None
    partial = (ps is None) != (pe is None)
    if window and pe < ps:
        issue("INVALID", "invalid_window", "period_end is before period_start")
    if partial:
        issue("UNRESOLVED", "missing_window", "both window endpoints are required; a missing endpoint is not inferred")
    if window and pd is not None:
        issue("INVALID", "ambiguous_time_anchor", "a measure cannot have both a window and a point anchor")
    if kind == "stock":
        if pd is None:
            issue("UNRESOLVED", "missing_point_date", "stock requires point_date")
        if ps is not None or pe is not None:
            issue("INVALID", "stock_with_window", "stock is a point observation, not a flow window")
    elif kind == "flow":
        if not window:
            issue("UNRESOLVED", "missing_window", "flow requires both period endpoints")
        if pd is not None:
            issue("INVALID", "flow_with_point", "flow uses a window, not point_date")
    elif kind in ("growth", "ratio", "count") and not window and pd is None:
        issue("UNRESOLVED", "missing_time_anchor", f"{kind} requires an explicit point or window")

    role = row.get("evidence_role")
    if not isinstance(role, str) or role not in EVIDENCE_ROLES:
        issue("UNRESOLVED" if role is None else "INVALID", "unknown_evidence_role", "evidence_role must be explicit")
        role = None
    source_ref = row.get("source_ref")
    has_ref = (isinstance(source_ref, dict) and all(isinstance(source_ref.get(key), str) and source_ref[key].strip()
                                                  for key in ("source_id", "locator")))
    if source_ref is not None and not isinstance(source_ref, dict):
        issue("INVALID", "invalid_source_ref", "source_ref must be an object or null")
    rationale = row.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        issue("INVALID", "invalid_rationale", "rationale must be text or null")
    if role in ("reported_fact", "management_guidance") and not has_ref:
        issue("UNRESOLVED", "missing_source_ref", f"{role} requires source_id+locator")
    if role in ("analyst_assumption", "scenario_stress") and not has_ref and not (isinstance(rationale, str) and rationale.strip()):
        issue("UNRESOLVED", "missing_rationale", "unsourced assumptions/stress require explicit rationale")
    if available is None:
        diags.append(_diag("source_availability_unknown", "available_by not supplied; source qualification is not verified"))
    elif as_of is not None and available > as_of:
        issue("UNRESOLVED", "available_after_as_of", "declared source availability is later than audit as_of_date")
    target_end = pe or pd
    if role == "reported_fact" and as_of is not None and target_end is not None and target_end > as_of:
        issue("UNRESOLVED", "future_period_declared_as_fact", "future target is not silently promoted to an actual; declare the correct role")

    abs_val = None
    if value is not None and scale is not None:
        try:
            with localcontext() as ctx:
                ctx.prec = max(60, len(value.as_tuple().digits) + 20)
                abs_val = value * SCALES[scale]
        except DecimalException:
            issue("INVALID", "unrepresentable_value", "value cannot be represented within Decimal arithmetic")
    status = "INVALID" if "INVALID" in states else "UNRESOLVED" if "UNRESOLVED" in states else "PASS"
    units = scale if kind in DIMENSIONLESS_KINDS else f"{currency} {scale}" if currency and scale else scale
    time = _time_str(ps, pe, pd)
    norm = dict(id=oid, value=value, scale=scale, currency=currency, currency_raw=cur,
                measure_kind=kind, period_start=ps, period_end=pe, point_date=pd,
                abs=abs_val, evidence_role=role, source_ref=source_ref if has_ref else None,
                rationale=rationale, available_by=available, units=units, time=time,
                usable=status == "PASS" and abs_val is not None, status=status, diagnostics=diags, **fields)
    return (_check("obs:" + (oid or "<invalid>"), "observation", None, status, None,
                   str(value) if value is not None else None, units, time,
                   source_ref if has_ref else None, diags), norm)
''')

replace_function("_compare_values", "_conversion_expected", '''
def _compare_values(expected, declared, tol, rounding):
    """Unit-aware comparison: caller values cannot inflate precision or tolerance."""
    diags = []
    exp = expected
    quantum = None
    if rounding is not None:
        places = rounding.get("places")
        basis = rounding.get("basis")
        if type(places) is not int or not -12 <= places <= 30:
            return "INVALID", expected, declared, [_diag("invalid_rounding", "places must be an integer in [-12,30], never bool/coerced text")]
        if not isinstance(basis, str) or not basis.strip():
            return "INVALID", expected, declared, [_diag("rounding_requires_basis", "rounding needs explicit display-precision basis")]
        quantum = Decimal(1).scaleb(-places)
        exp = expected.quantize(quantum)
        if declared.quantize(quantum) != declared:
            return "INVALID", exp, declared, [_diag("declared_precision_mismatch", "declared result exceeds the supplied display precision")]
    if tol is not None and tol > 0:
        if quantum is None:
            return "INVALID", exp, declared, [_diag("tolerance_requires_precision_basis", "positive absolute tolerance needs explicit display precision")]
        if tol > quantum / 2:
            return "INVALID", exp, declared, [_diag("excessive_tolerance", "tolerance exceeds half the declared display quantum")]
        if expected != 0 and tol >= abs(expected) / 2:
            return "INVALID", exp, declared, [_diag("excessive_tolerance", "tolerance would mask the true expected magnitude")]
    # No max(...,1) floor: changing units cannot create an absolute pass allowance.
    numerical_epsilon = abs(exp) * COMPARE_EPSILON
    limit = max(tol or Decimal(0), numerical_epsilon)
    difference = abs(declared - exp)
    if difference <= limit:
        return "PASS", exp, declared, diags
    return "FAIL", exp, declared, [_diag("value_mismatch", f"expected {exp} got {declared} (difference {difference})")]
''')

replace_function("_check_relation", "_overall", '''
def _time_key(norm):
    return norm["period_start"], norm["period_end"], norm["point_date"]


def _anchor(norm):
    return norm["point_date"] or norm["period_start"]


def _precision(norms):
    return max(80, sum(len(n["value"].as_tuple().digits) for n in norms if n["value"] is not None) + 30)


def _check_relation(rel, norms, as_of=None):
    """All ops share typed dependency/arity/context checks before arithmetic."""
    diags = []
    if not isinstance(rel, dict):
        return _check("rel:<invalid>", "relation", None, "INVALID", None, None, None, None, None,
                      [_diag("not_object", "relation must be an object")])
    rid, op = rel.get("relation_id"), rel.get("op")
    check_id = "rel:" + rid if isinstance(rid, str) and rid.strip() else "rel:<invalid>"
    resolved = []
    result_norm = None

    def finish(state, expected=None, actual=None, extra=()):
        row = _check(check_id, "relation", op if isinstance(op, str) else None, state,
                     str(expected) if expected is not None else None,
                     str(actual) if actual is not None else None,
                     result_norm["units"] if result_norm else None,
                     result_norm["time"] if result_norm else None,
                     result_norm["source_ref"] if result_norm else None, diags + list(extra))
        row["arithmetic_status"] = state if expected is not None else "NOT_CHECKED"
        row["input_contexts"] = [{"id": n["id"], "entity_key": n["entity_key"],
                                  "definition": n["definition"], "measure_kind": n["measure_kind"],
                                  "units": n["units"], "time": n["time"], "evidence_role": n["evidence_role"],
                                  "source_ref": n["source_ref"]} for n in resolved]
        row["result_evidence_role"] = result_norm["evidence_role"] if result_norm else None
        row["source_truth_verified"] = False
        return row

    def reject(code, detail, state="INVALID"):
        return finish(state, extra=[_diag(code, detail)])

    if not isinstance(rid, str) or not rid.strip():
        return reject("missing_relation_id", "relation_id must be nonempty text")
    if not isinstance(op, str) or op not in OPS:
        return reject("unknown_op", "unsupported operation; no eval or inferred expressions")
    ids = rel.get("inputs")
    expected_arity = 1 if op in ("scale_conversion", "fx_conversion") else 2
    if not isinstance(ids, list) or (len(ids) < 2 if op == "sum" else len(ids) != expected_arity):
        return reject("invalid_arity", "sum requires >=2 operands; conversions exactly 1; other fixed ops exactly 2")
    for iid in ids:
        if not isinstance(iid, str) or not iid.strip() or iid not in norms:
            return reject("dangling_reference", "each input must be an existing nonempty observation id")
        resolved.append(norms[iid])
    result_check, result_norm = _check_observation(rel.get("result"), set(), as_of)
    diags.extend(result_check["diagnostics"])
    dependencies = [n["status"] for n in resolved] + [result_check["status"]]
    if "INVALID" in dependencies:
        return reject("invalid_dependency", "invalid input/result context is not a computable relation")
    if "UNRESOLVED" in dependencies:
        return reject("unresolved_dependency", "missing source/unit/role/time context cannot become an arithmetic PASS", "UNRESOLVED")
    if result_norm is None or any(not n["usable"] for n in resolved + [result_norm]):
        return reject("input_not_computable", "an observation is not computable", "UNRESOLVED")
    role_rank = {"reported_fact": 0, "management_guidance": 1, "analyst_assumption": 2, "scenario_stress": 3}
    if role_rank[result_norm["evidence_role"]] < max(role_rank[n["evidence_role"]] for n in resolved):
        return reject("evidence_role_promotion", "guidance/assumption/stress inputs cannot manufacture a more factual output role", "UNRESOLVED")

    rounding, fx = rel.get("rounding"), rel.get("fx")
    if rounding is not None and not isinstance(rounding, dict):
        return reject("invalid_rounding", "rounding must be an object {places,basis}")
    if fx is not None and not isinstance(fx, dict):
        return reject("invalid_fx", "fx must be an explicit object")
    tol = None
    if rel.get("absolute_tolerance") is not None:
        try:
            tol = numeric_audit.decimal_value(rel["absolute_tolerance"])
        except (ValueError, DecimalException):
            return reject("invalid_tolerance", "absolute_tolerance must be finite Decimal")
        if tol < 0:
            return reject("negative_tolerance", "absolute_tolerance cannot be negative")
    if op != "fx_conversion" and fx is not None:
        return reject("unexpected_fx", "only an explicit fx_conversion may consume FX")

    def matching(items, fields):
        first = items[0]
        for n in items[1:]:
            for field in fields:
                if first[field] != n[field]:
                    diags.append(_diag("incompatible_context", f"observations differ on {field}"))
                    return False
        return True

    def result_time_matches(norm):
        if _time_key(result_norm) != _time_key(norm):
            diags.append(_diag("result_time_mismatch", "derived result must preserve the relevant output anchor/window"))
            return False
        return True

    def temporal_comparison(end, base, ordered):
        # Compare like temporal anchors. Flow duration differs by <=3 days for leap/calendar quarters.
        ep, bp = end["point_date"], base["point_date"]
        if (ep is None) != (bp is None):
            diags.append(_diag("incompatible_time_kind", "point and flow-window observations are not comparable"))
            return False
        if ep is None:
            days_end = (end["period_end"] - end["period_start"]).days + 1
            days_base = (base["period_end"] - base["period_start"]).days + 1
            if abs(days_end - days_base) > 3:
                diags.append(_diag("incompatible_period_duration", "quarter/year or otherwise unequal windows cannot be generic growth/difference"))
                return False
            if ordered and base["period_end"] >= end["period_start"]:
                diags.append(_diag("overlapping_or_reversed_growth_period", "growth requires base before end without overlapping flow windows"))
                return False
        if ordered and _anchor(end) <= _anchor(base):
            diags.append(_diag("reversed_growth_period", "growth requires an earlier base anchor"))
            return False
        return True

    a = resolved[0]
    if op in ("scale_conversion", "fx_conversion"):
        if not matching([a, result_norm], ("entity_key", "definition", "measure_kind")) or not result_time_matches(a):
            return finish("INVALID")
        if a["scale"] == PP_SCALE or result_norm["scale"] == PP_SCALE:
            return reject("pp_scale_conversion", "percentage_points is a difference meaning, not a growth-rate scale conversion")
        if (a["scale"] in AMOUNT_SCALES) != (result_norm["scale"] in AMOUNT_SCALES):
            return reject("result_dimension_mismatch", "amount and ratio dimensions cannot be converted")
        if op == "scale_conversion":
            if a["currency"] != result_norm["currency"]:
                return reject("silent_currency_change", "scale conversion preserves currency; explicit FX is required")
        else:
            if fx is None:
                return reject("missing_explicit_fx", "currency change requires explicit FX", "UNRESOLVED")
            if a["currency"] == result_norm["currency"] or a["currency"] is None or result_norm["currency"] is None:
                return reject("invalid_fx_dimension", "FX converts different explicit monetary currencies")
            if fx.get("from") != a["currency"] or fx.get("to") != result_norm["currency"]:
                return reject("fx_direction_mismatch", "FX from/to must match the input/result currencies")
            if not isinstance(fx.get("source"), str) or not fx["source"].strip():
                return reject("fx_source_required", "explicit FX source is required", "UNRESOLVED")
            fx_date, valid_date = _parse_date(fx.get("date"), "fx.date", diags)
            if not valid_date:
                return finish("INVALID")
            if fx_date is None:
                return reject("fx_date_required", "explicit FX date is required", "UNRESOLVED")
            if as_of is not None and fx_date > as_of:
                return reject("fx_after_as_of", "declared FX rate was not available at the audit context date", "UNRESOLVED")
            try:
                rate = numeric_audit.decimal_value(fx.get("rate"))
            except (ValueError, DecimalException):
                return reject("invalid_fx_rate", "rate must be positive finite Decimal")
            if rate <= 0:
                return reject("invalid_fx_rate", "rate must be positive")
    elif op == "sum":
        if not matching(resolved + [result_norm], ("entity_key", "definition", "currency", "measure_kind")):
            return finish("INVALID")
        if any(n["measure_kind"] != "flow" for n in resolved + [result_norm]):
            return reject("stock_not_summable", "sum concatenates compatible monetary flow windows, never stock snapshots")
        windows = sorted((n["period_start"], n["period_end"]) for n in resolved)
        for previous, following in zip(windows, windows[1:]):
            if following[0] <= previous[1]:
                return reject("overlapping_flow_double_count", "overlapping flow windows double-count periods")
            if (following[0] - previous[1]).days != 1:
                return reject("window_gap_not_zero_filled", "a flow window gap is not implicitly zero-filled", "UNRESOLVED")
        if result_norm["period_start"] != windows[0][0] or result_norm["period_end"] != windows[-1][1]:
            return reject("window_mismatch", "sum result window must equal the concatenated span", "FAIL")
    elif op == "difference":
        if not matching(resolved, ("entity_key", "definition", "currency", "measure_kind")):
            return finish("INVALID")
        if not temporal_comparison(a, resolved[1], False) or not result_time_matches(a):
            return finish("INVALID")
        if result_norm["entity_key"] != a["entity_key"]:
            return reject("result_entity_mismatch", "difference result belongs to the same entity")
        if a["measure_kind"] == "ratio":
            if result_norm["measure_kind"] != "growth" or result_norm["scale"] != PP_SCALE:
                return reject("result_dimension_mismatch", "ratio-level difference is growth in percentage_points")
        elif (result_norm["currency"] != a["currency"] or result_norm["definition"] != a["definition"] or
              result_norm["measure_kind"] != a["measure_kind"] or result_norm["scale"] not in AMOUNT_SCALES):
            return reject("result_dimension_mismatch", "amount difference preserves monetary/count kind, currency and economic line")
    elif op in ("growth_rate", "cagr"):
        if not matching(resolved, ("entity_key", "definition", "currency", "measure_kind")):
            return finish("INVALID")
        if any(n["scale"] == PP_SCALE for n in resolved):
            return reject("pp_growth_input", "percentage-point differences are not ratio levels")
        if not temporal_comparison(a, resolved[1], True) or not result_time_matches(a):
            return finish("INVALID")
        if result_norm["entity_key"] != a["entity_key"] or result_norm["measure_kind"] != "growth" or result_norm["scale"] not in RATE_SCALES:
            return reject("result_dimension_mismatch", "growth/cagr output must be a same-entity percent/decimal growth")
        if resolved[1]["abs"] <= 0:
            return reject("nonpositive_base", "zero/negative bases do not support a generic percentage growth", "UNRESOLVED")
    elif op == "share":
        if not matching(resolved, ("currency", "measure_kind")) or _time_key(a) != _time_key(resolved[1]):
            return reject("incompatible_share_context", "share numerator/denominator require matching dimension, currency and time")
        if a["measure_kind"] not in ("stock", "flow", "count"):
            return reject("invalid_share_dimension", "share must compare quantities, not existing percentage rates")
        inclusion = rel.get("scope_inclusion")
        if not isinstance(inclusion, str) or not inclusion.strip():
            return reject("scope_inclusion_required", "explicit numerator/denominator inclusion declaration is required", "UNRESOLVED")
        if result_norm["entity_key"] != a["entity_key"] or result_norm["measure_kind"] != "ratio" or result_norm["scale"] not in RATE_SCALES or not result_time_matches(a):
            return reject("result_dimension_mismatch", "share is a numerator-entity ratio at the same time")
        if resolved[1]["abs"] == 0:
            return reject("share_denominator_zero", "share denominator is zero", "UNRESOLVED")
        diags.append(_diag("scope_inclusion_not_verified", "declared inclusion is not independently source-verified"))

    try:
        with localcontext() as ctx:
            ctx.prec = _precision(resolved + [result_norm])
            if op in ("scale_conversion", "fx_conversion"):
                expected = _conversion_expected(rid, a, result_norm, fx)
            elif op == "sum":
                expected = sum((n["abs"] for n in resolved), Decimal(0)) / SCALES[result_norm["scale"]]
            elif op == "difference":
                expected = (a["abs"] - resolved[1]["abs"]) / SCALES[result_norm["scale"]]
            elif op == "growth_rate":
                expected = ((a["abs"] - resolved[1]["abs"]) / resolved[1]["abs"]) / SCALES[result_norm["scale"]]
            elif op == "cagr":
                try:
                    years = numeric_audit.decimal_value(rel.get("years"))
                except (ValueError, DecimalException):
                    return reject("invalid_years", "cagr requires explicit positive finite years")
                if years <= 0:
                    return reject("invalid_years", "cagr years must be positive")
                if a["abs"] <= 0:
                    return reject("nonpositive_end", "cagr requires a positive end", "UNRESOLVED")
                days = Decimal((_anchor(a) - _anchor(resolved[1])).days)
                if abs(days - years * Decimal("365.2425")) > Decimal(3):
                    return reject("cagr_period_mismatch", "explicit years differs from the declared anchor gap by more than three calendar days", "FAIL")
                expected = ((a["abs"] / resolved[1]["abs"]) ** (Decimal(1) / years) - Decimal(1)) / SCALES[result_norm["scale"]]
            else:  # share
                expected = (a["abs"] / resolved[1]["abs"]) / SCALES[result_norm["scale"]]
            state, exp, act, compare_diags = _compare_values(expected, result_norm["value"], tol, rounding)
        return finish(state, exp, act, compare_diags)
    except (ValueError, DecimalException):
        return reject("arithmetic_not_representable", "declared operation cannot be represented as finite Decimal arithmetic")
''')

replace_function("audit_measures", "_empty_report", '''
def audit_measures(ledger):
    """Pure typed diagnostic: malformed JSON content is a report, never a batch crash."""
    if not isinstance(ledger, dict):
        report = _empty_report(None)
        report.update(overall="INVALID", exit_code=2, diagnostics=[_diag("ledger_not_object", "ledger must be an object")])
        return report
    top_diags = []
    raw_as_of = ledger.get("as_of_date")
    as_of, as_of_valid = _parse_date(raw_as_of, "as_of_date", top_diags)
    invalid_top = not as_of_valid
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        top_diags.append(_diag("unsupported_schema", "schema_version must be financial-measure-ledger/1"))
        invalid_top = True
    if as_of is None:
        top_diags.append(_diag("missing_as_of", "explicit audit as_of_date is required; target periods are not inferred"))
        invalid_top = True
    observations, relations = ledger.get("observations"), ledger.get("relations", [])
    if not isinstance(observations, list) or not isinstance(relations, list):
        report = _empty_report(raw_as_of if isinstance(raw_as_of, str) else None)
        report.update(overall="INVALID", exit_code=2, diagnostics=top_diags + [_diag("invalid_ledger_shape", "observations and relations must be lists")])
        return report
    seen_ids, norms = set(), {}
    observation_checks = []
    for row in observations:
        check, norm = _check_observation(row, seen_ids, as_of)
        observation_checks.append(check)
        if norm is not None and isinstance(norm["id"], str):
            norms.setdefault(norm["id"], norm)
    relation_checks = []
    relation_ids = set()
    for rel in relations:
        check = _check_relation(rel, norms, as_of)
        rid = rel.get("relation_id") if isinstance(rel, dict) else None
        if isinstance(rid, str) and rid.strip():
            if rid in relation_ids:
                check["status"] = "INVALID"
                check["diagnostics"].append(_diag("duplicate_relation_id", "relation ids must be unique"))
            relation_ids.add(rid)
        relation_checks.append(check)
    if not observations:
        top_diags.append(_diag("no_observations", "zero observations cannot fabricate a coverage PASS"))
    if not relations:
        top_diags.append(_diag("relations_not_declared", "only observation checks ran; relationships NOT_CHECKED"))
    verification = ("not_declared" if not relations else "incomplete" if any(c["status"] in ("INVALID", "UNRESOLVED", "NOT_CHECKED") for c in relation_checks) else "complete")
    coverage = {"observations_declared": len(observations), "observation_denominator": len(observations),
                "relations_declared": len(relations), "relation_denominator": len(relations),
                "relation_verification": verification, "coverage_pass": False}
    overall = "INVALID" if invalid_top else _overall(observation_checks, relation_checks, coverage)
    coverage["coverage_pass"] = overall == "PASS"
    return {"schema_version": REPORT_SCHEMA, "check_kind": CHECK_KIND,
            "as_of_date": raw_as_of if isinstance(raw_as_of, str) else None,
            "source_truth_verified": False, "source_qualification_verified": False,
            "economic_reasonableness": "not_evaluated", "overall": overall,
            "exit_code": EXIT_CODES[overall], "observation_checks": observation_checks,
            "relation_checks": relation_checks, "coverage": coverage, "diagnostics": top_diags}
''')
path.write_text(source, encoding="utf-8")
print(path)
