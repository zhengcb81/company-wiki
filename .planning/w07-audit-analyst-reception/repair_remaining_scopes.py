from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
path = ROOT / 'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py'
code = path.read_text(encoding='utf-8')
def rep(old, new):
    global code
    assert code.count(old) == 1, old[:100]
    code = code.replace(old, new)
rep('    return _id_year(fallback_id)', '    return None  # Opaque ID spelling is never a substitute for the actual period.')
rep('''    for doc in (native_input, forecast):
        for seg in doc.get("segments") or []:
            if not isinstance(seg, dict):''', '''    for doc in (forecast,):
        for seg in doc.get("segments") or []:
            if not isinstance(seg, dict):''')
rep('''            for pid in linked:
                year = _param_year(params.get(pid), pid)
                if year and isinstance(start, int)''', '''            for pid in linked:
                year = _param_year(params.get(pid), pid)
                if not year:
                    reasons.append("driver_timing_unresolved")
                if year and isinstance(start, int)''')
rep('''        resolved = bool(segments) and bool(years) and all(s in known_segments
                                                          for s in segments)''', '''        resolved = bool(segments) and bool(years) and all(s in known_segments for s in segments) \\
            and all(year in _forecast_years(native_input, forecast) for year in years)''')
rep('''    known_claims = {c.get("claim_id") for c in native_input.get("evidence_claims") or [] if isinstance(c, dict)}''', '''    known_claims = {c.get("claim_id") for c in native_input.get("evidence_claims") or [] if isinstance(c, dict)}
    params = _parameter_index(native_input)
    paths = _native_paths(native_input, {"segments": native_input.get("segments") or []})''')
rep('''        years = _calibration_support_years(native_input, cal)
        reasons, missing = [], []''', '''        years = _calibration_support_years(native_input, cal)
        reasons, missing = [], []
        output_ids = [pid for value in (cal.get("scenario_output_parameter_ids") or {}).values() for pid in _ids(value)]
        if not output_ids or any(pid not in params or not _param_year(params.get(pid)) for pid in output_ids) \\
                or not any(name == cal.get("scope") and set(output_ids).intersection(ids)
                           for (name, _), ids in paths.items()):
            reasons.append("range_scope_unresolved")
            missing.append("native range output/scope")''')
rep('''        if not years or not segment:
            reasons.append("range_timing_unknown")''', '''        if segment not in _segment_names(native_input, {}):
            reasons.append("range_scope_unresolved")
        if not years or not segment:
            reasons.append("range_timing_unknown")''')
rep('''        joint = fields.get("joint") is True''', '''        # A native calibration can bind a historical input to a forecast output year.
        def applies(pid):
            if _param_year(params.get(pid)) in {str(y) for y in scope.get("years") or []}:
                return True
            for _, (_, cal) in _calibration_index(native_input).items():
                if cal.get("scope") not in scope.get("segments") or []:
                    continue
                for sc in scope.get("scenarios") or []:
                    if pid in _ids((cal.get("scenario_input_parameter_ids") or {}).get(sc)):
                        outputs = _ids((cal.get("scenario_output_parameter_ids") or {}).get(sc))
                        if any(_param_year(params.get(out)) in {str(y) for y in scope.get("years") or []} for out in outputs):
                            return True
            return False
        scope_ok = scope_ok and all(applies(pid) for pid in parameter_ids)
        joint = fields.get("joint") is True''')
# Parentheses are intentional: do not make 'or []' part of the boolean condition.
code = code.replace('if cal.get("scope") not in scope.get("segments") or []:', 'if cal.get("scope") not in (scope.get("segments") or []):')
path.write_text(code, encoding='utf-8', newline='\n')

tests = ROOT / 'tests/test_w07_analyst_risk_audit.py'
body = tests.read_text(encoding='utf-8')
old = '''        known = {c["claim_id"] for c in document["evidence_claims"]}'''
new = '''        defined = {p["parameter_id"] for p in document["parameters"]}
        for cal in document["operating_research"]["calibrations"]:
            for value in (cal.get("scenario_output_parameter_ids") or {}).values():
                for pid in value if isinstance(value, list) else [value]:
                    if pid not in defined:
                        document["parameters"].append(parameter(pid, period="FY2026"))
                        defined.add(pid)
        known = {c["claim_id"] for c in document["evidence_claims"]}'''
assert body.count(old) == 1
tests.write_text(body.replace(old, new), encoding='utf-8', newline='\n')

tests = ROOT / 'tests/test_root_w07_analyst_scope.py'
body = tests.read_text(encoding='utf-8')
body += '''

class FinalScopeRegressionTests(unittest.TestCase):
    def test_input_path_is_not_proof_of_executed_forecast_path(self):
        self.assertEqual(b.checkpoint(b.run(forecast=b.make_forecast(segments=[])), 'A02')['status'], 'UNRESOLVED')

    def test_parameter_name_does_not_supply_missing_period(self):
        doc = b.make_input()
        for p in doc['parameters']:
            p.pop('period')
        self.assertEqual(b.checkpoint(b.run(native_input=doc), 'A02')['status'], 'UNRESOLVED')

    def test_range_unknown_segment_cannot_be_observed(self):
        report = b.run(calibrations=[b.calibration(scope='Ghost')], support=b.make_support({}))
        self.assertEqual(b.checkpoint(report, 'A13')['status'], 'UNRESOLVED')

    def test_range_unresolved_outputs_cannot_be_observed(self):
        doc = b.make_input(calibrations=[b.calibration(scenario_outputs={'base':'ghost_2026'})])
        doc['parameters'] = [p for p in doc['parameters'] if p['parameter_id'] != 'ghost_2026']
        self.assertEqual(b.checkpoint(b.run(native_input=doc, support=b.make_support({})), 'A13')['status'], 'UNRESOLVED')

    def test_stress_parameter_year_does_not_borrow_other_years_scope(self):
        ctx = b.context_doc(b.statement('stress_declaration', {'joint': True, 'cross_exposure_declared': True, 'parameter_ids': ['0_base_2027'], 'scope': {'segments':['Segment A'], 'years':[2026], 'scenarios':['base']}}))
        self.assertEqual(b.checkpoint(b.run(context=ctx), 'A17')['status'], 'UNRESOLVED')

    def test_constraint_unknown_year_remains_unresolved(self):
        ctx = b.context_doc(b.statement('constraint_note', {'scope':{'segments':['Segment A'], 'years':[2099]}}))
        self.assertEqual(b.checkpoint(b.run(context=ctx), 'A05')['status'], 'UNRESOLVED')
'''
tests.write_text(body, encoding='utf-8', newline='\n')
print('Final review scope residuals repaired and explicit regression cases added')
