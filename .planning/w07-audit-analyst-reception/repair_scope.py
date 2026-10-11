from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
target = ROOT / 'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py'
code = target.read_text(encoding='utf-8')
assert 'def _native_paths(' not in code

def replace(old, new):
    global code
    assert code.count(old) == 1, old[:120]
    code = code.replace(old, new)

replace('import json\n', 'import json\nimport math\nfrom datetime import date\n')
start = code.index('def _revenue_path_ids(')
end = code.index('\ndef _parameter_index(', start)
code = code[:start] + '''def _ids(value):
    if isinstance(value, str):
        return [value]
    return [v for v in value or [] if isinstance(v, str)]


def _native_paths(native_input, forecast):
    """Read native driver roles by segment and scenario; no model re-execution."""
    paths = {}
    for doc in (native_input, forecast):
        for seg in doc.get("segments") or []:
            if not isinstance(seg, dict):
                continue
            for scenario, body in (seg.get("scenarios") or {}).items():
                if not isinstance(body, dict):
                    continue
                ids = set()
                for value in (body.get("driver_parameter_ids") or {}).values():
                    ids.update(_ids(value))
                paths.setdefault((seg.get("name"), scenario), set()).update(ids)
    return paths


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _forecast_years(native_input, forecast):
    return {str(y) for doc in (native_input, forecast) for y in doc.get("forecast_years") or []}

''' + code[end:]
replace('    revenue_ids = _revenue_path_ids(native_input, forecast)', '    paths = _native_paths(native_input, forecast)\n    revenue_ids = set().union(*paths.values()) if paths else set()')
replace('''        linked = [p for p in parameter_ids if p in revenue_ids]
        reasons, missing = [], []''', '''        linked = [p for p in parameter_ids if p in revenue_ids]
        reasons, missing = [], []
        if any(p not in params for p in parameter_ids):
            reasons.append("driver_parameter_unresolved")''')
replace('''            if not segments or any(s not in known_segments for s in segments):
                reasons.append("driver_segment_unresolved")''', '''            if not segments or any(s not in known_segments for s in segments):
                reasons.append("driver_segment_unresolved")
            elif any(not any(set(linked) & ids for (name, _), ids in paths.items()
                             if name == segment) for segment in segments):
                reasons.append("driver_segment_path_mismatch")
            if not isinstance(start, int) or not isinstance(end, int):
                reasons.append("driver_timing_unresolved")''')
replace('def _constraint_scope(row):', 'def _constraint_scope(row, params):')
replace('''                    match = _TAIL_YEAR_RE.search(pid)
                    if match and match.group(1) not in years:
                        years.append(match.group(1))''', '''                    year = _param_year(params.get(pid), pid)
                    if year and year not in years:
                        years.append(year)''')
replace('    for i, row in enumerate(forecast.get("revenue_constraints") or []):', '    params = _parameter_index(native_input)\n    for i, row in enumerate(forecast.get("revenue_constraints") or []):')
replace('        segments, years = _constraint_scope(row)', '        segments, years = _constraint_scope(row, params)')
replace('''        segments, years = _constraint_scope(row, params)
        resolved = bool(segments) and bool(years) and all(s in known_segments
                                                          for s in segments)''', '''        segments, years = _constraint_scope(row, params)
        referenced = [pid for key in ("scenario_parameter_ids", "weight_parameter_ids")
                      for value in (row.get(key) or {}).values() for pid in _ids(value)]
        resolved = bool(segments) and bool(years) and all(s in known_segments for s in segments) \\
            and all(pid in params for pid in referenced)''')
replace('    calibrations = _calibration_index(native_input)\n    findings = []', '    calibrations = _calibration_index(native_input)\n    params = _parameter_index(native_input)\n    findings = []')
replace('''        resolved = [calibrations[cid] for cid in calibration_ids if cid in calibrations]
        if not resolved:''', '''        resolved = [calibrations[cid] for cid in calibration_ids if cid in calibrations]
        if any(cid not in calibrations for cid in calibration_ids):
            reasons.append("calibration_reference_unresolved")
        if not resolved:''')
replace('''            outputs = cal.get("scenario_output_parameter_ids") or {}
            if not cal.get("output_unit") or not outputs.get(scenario):''', '''            outputs = cal.get("scenario_output_parameter_ids") or {}
            output_ids = _ids(outputs.get(scenario))
            if cal.get("scope") != segment or not output_ids or any(
                    _param_year(params.get(pid), pid) != year for pid in output_ids):
                reasons.append("calibration_scope_not_covering")
            if any(pid not in params for pid in output_ids) or not set(output_ids).intersection(
                    entry.get("supported_parameter_ids") or []):
                reasons.append("calibration_output_unresolved")
            if not cal.get("output_unit") or not outputs.get(scenario):''')
replace('        independent = bool(fields.get("independent"))', '        independent = fields.get("independent") is True')
replace('''        if not independent:
            reasons = ["independence_unknown_not_assumed"]
        elif len(distinct) >= 2 and len(actual_sources) >= 2:''', '''        targets = {(claim_index[cid].get("target_type"), claim_index[cid].get("target_id"))
                   for cid in claim_ids if cid in claim_index}
        if not independent:
            reasons = ["independence_unknown_not_assumed"]
        elif any(cid not in claim_index for cid in claim_ids) or len(targets) != 1 \\
                or set(declared) != set(actual_sources):
            reasons = ["independence_reference_unresolved"]
        elif len(distinct) >= 2 and len(actual_sources) >= 2:''')
replace('''    if not management_ids:
        findings.append(_finding(''', '''    groups = {}
    for claim in claims:
        groups.setdefault((claim.get("target_type"), claim.get("target_id")), []).append(claim.get("claim_id"))
    for group in groups.values():
        if notes and not any(set(group).issubset(set((note.get("fields") or {}).get("claim_ids") or []))
                             for _, note in notes):
            findings.append(_finding("A08", "UNRESOLVED", ["independence_unknown_not_assumed"],
                                     claim_ids=group, detail="this claim group has no independence metadata"))
    if not management_ids:
        findings.append(_finding(''')
replace('''            if any(p not in params for p in drivers):
                reasons.append("beat_comparison_driver_unresolved")
            if not reasons:''', '''            if any(p not in params for p in drivers):
                reasons.append("beat_comparison_driver_unresolved")
            elif any(_param_year(params[p], p) != _period_year(result.get("period")) for p in drivers):
                reasons.append("beat_comparison_period_unresolved")
            try:
                baseline_date = date.fromisoformat(baseline["as_of_date"])
                result_date = date.fromisoformat(result["announced_date"])
                if baseline_date > result_date:
                    reasons.append("beat_baseline_after_result")
            except (ValueError, TypeError):
                reasons.append("beat_date_unresolved")
            if not reasons:''')
replace('''        if lower is None or upper is None:
            reasons.append("operating_range_unknown")
            missing.append("observed_range.lower/upper")''', '''        if not (_finite(lower) and _finite(upper)) or lower > upper:
            reasons.append("operating_range_unknown")
            missing.append("observed_range.lower/upper")
        if not cal.get("observed_period"):
            reasons.append("range_timing_unknown")
            missing.append("observed_period")''')
replace('''        declared.append({"segment": cal.get("scope"), "years": years, "calibration_id": cid})''', '''        if status == "OBSERVED":
            declared.append({"segment": cal.get("scope"), "years": years, "calibration_id": cid,
                             "scenarios": set((cal.get("scenario_output_parameter_ids") or {}).keys())})''')
replace('''        if lower is None or upper is None:
            reasons.append("operating_range_unknown")
            missing.append("range.lower/upper")''', '''        if not (_finite(lower) and _finite(upper)) or lower > upper:
            reasons.append("operating_range_unknown")
            missing.append("range.lower/upper")
        if not years or not segment:
            reasons.append("range_timing_unknown")
            missing.append("support_years/scope.segment")''')
replace('''        declared.append({"segment": segment, "years": years, "calibration_id": None})''', '''        if status == "OBSERVED":
            declared.append({"segment": segment, "years": years, "calibration_id": None,
                             "scenarios": set(scope.get("scenarios") or [])})''')
replace('    if declared and cells:', '    if (calibrations or notes) and cells:')
replace('''                row["segment"] == segment and year in row["years"]
                and (row["calibration_id"] is None or not calibration_ids''', '''                row["segment"] == segment and year in row["years"]
                and (not row["scenarios"] or entry.get("scenario") in row["scenarios"])
                and (row["calibration_id"] is None or not calibration_ids''')
replace('def _audit_a17(forecast, context):', 'def _audit_a17(native_input, forecast, context):')
replace('''    valid = False
    for i, statement in declarations:''', '''    valid = False
    params = _parameter_index(native_input)
    paths = _native_paths(native_input, forecast)
    years = _forecast_years(native_input, forecast)
    for i, statement in declarations:''')
replace('''        joint = bool(fields.get("joint"))
        cross = bool(fields.get("cross_exposure_declared"))''', '''        scope_ok = scope_ok and all(str(y) in years for y in scope.get("years") or []) \\
            and all((seg, sc) in paths for seg in scope.get("segments") or []
                    for sc in scope.get("scenarios") or []) \\
            and all(pid in params for pid in parameter_ids)
        joint = fields.get("joint") is True
        cross = fields.get("cross_exposure_declared") is True''')
replace('        "A17": _audit_a17(forecast, context),', '        "A17": _audit_a17(native_input, forecast, context),')
replace('''        year = _period_year((statement.get("fields") or {}).get("period"))
        if year and year not in checked:''', '''        fields = statement.get("fields") or {}
        year = _period_year(fields.get("period"))
        if year and _finite(fields.get("value")) and fields.get("unit") and year not in checked:''')
replace('''    for i, record in enumerate(records):
        for value in (record.get("years") or []) + [record.get("period")]:''', '''    for i, record in enumerate(records):
        # Native 1.1 records contain aggregate actual evidence; legacy labels alone do not.
        if record.get("record_schema_version") != "1.1" or not _finite(record.get("sum_absolute_actual")) \\
                or not _finite(record.get("observations")) or record["observations"] <= 0:
            continue
        for value in (record.get("years") or []) + [record.get("period")]:''')
target.write_text(code, encoding='utf-8', newline='\n')
print('ROOT scope repairs written; old assertions unchanged')
