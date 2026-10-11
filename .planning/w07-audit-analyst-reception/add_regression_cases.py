from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
path = ROOT / 'tests/test_root_w07_analyst_scope.py'
body = path.read_text(encoding='utf-8')
assert 'class NativeReferenceRegressionTests' not in body
body += '''

class NativeReferenceRegressionTests(unittest.TestCase):
    def test_dangling_range_claims_do_not_establish_observed_reference(self):
        doc = b.make_input(calibrations=[b.calibration()])
        doc['evidence_claims'] = []
        rows = b.findings(b.run(native_input=doc), 'A13')
        self.assertFalse(any(r['status'] == 'OBSERVED' for r in rows))

    def test_error_count_without_any_actual_evidence_stays_null(self):
        forecast = b.make_forecast(accuracy_records=[{'period': 'FY2026'}, {'period': 'FY2027'}], wape=0, wape_observations=2)
        report = b.run(forecast=forecast)
        self.assertIsNone(report['actual_input_refs']['wape'])
        self.assertEqual(report['actual_input_refs']['years_checked'], [])
        self.assertEqual(b.checkpoint(report, 'A18')['status'], 'UNRESOLVED')

    def test_native_aggregate_historical_record_preserves_real_error_metric(self):
        forecast = b.make_forecast(accuracy_records=[{'record_schema_version': '1.1', 'sum_absolute_actual': 100, 'sum_absolute_error': 5, 'observations': 2, 'wape': 0.05}], wape=0.05, wape_observations=2)
        report = b.run(forecast=forecast)
        self.assertEqual(report['actual_input_refs']['wape'], 0.05)
        self.assertEqual(report['actual_input_refs']['years_checked'], [])

    def test_real_zero_actual_is_data_not_missing(self):
        report = b.run(context=b.context_doc(b.statement('actual_input', {'period': 'FY2026', 'value': 0, 'unit': 'USD million'})))
        self.assertEqual(report['actual_input_refs']['years_checked'], ['2026'])
        self.assertIsNone(report['actual_input_refs']['wape'])

    def test_claims_for_different_targets_are_not_independent_support(self):
        doc = b.make_input(claims=[b.claim('c1', 's1', target_id='a'), b.claim('c2', 's2', target_id='b')])
        context = b.context_doc(b.statement('independence_note', {'claim_ids': ['c1', 'c2'], 'source_ids': ['s1', 's2'], 'independent': True}))
        self.assertEqual(b.checkpoint(b.run(native_input=doc, context=context), 'A08')['status'], 'UNRESOLVED')

    def test_failed_cited_measure_is_a_gap_not_comparable_evidence(self):
        context = b.context_doc(b.statement('beat_claim', {'baseline': {'kind': 'consensus', 'ref': 'feed', 'as_of_date': '2026-07-01', 'period': 'FY2026', 'unit': 'USD million'}, 'result': {'period': 'FY2026', 'unit': 'USD million', 'announced_date': '2026-07-12'}, 'comparison_driver_parameter_ids': ['0_base_2026'], 'measure_check_ids': ['rel:units']}))
        measure = {'schema_version': 'financial-measure-audit/1', 'relation_checks': [{'check_id': 'rel:units', 'status': 'FAIL'}]}
        report = b.run(context=context, measure_report=measure)
        self.assertEqual(b.checkpoint(report, 'A10')['status'], 'UNRESOLVED')
        self.assertTrue(any(p['document'] == 'measure_report' for f in b.findings(report, 'A10') for p in f['pointers']))

    def test_every_finding_has_actual_reference_resolution(self):
        report = b.run(calibrations=[b.calibration()])
        for row in report['findings']:
            self.assertIn('native_evidence_refs', row)
            for ref in row['native_evidence_refs']:
                self.assertIn('resolved', ref)
                if ref['resolved']:
                    self.assertEqual(ref['document'], 'input')

    def test_currency_label_mismatch_in_conversion_is_unresolved(self):
        doc = b.make_input(calibrations=[b.calibration(output_unit='CNY million')])
        self.assertEqual(b.checkpoint(b.run(native_input=doc), 'A06')['status'], 'UNRESOLVED')

    def test_known_but_unrelated_parameter_is_not_scoped_joint_stress(self):
        doc = b.make_input()
        doc['parameters'].append(b.parameter('other-business'))
        ctx = b.context_doc(b.statement('stress_declaration', {'joint': True, 'cross_exposure_declared': True, 'parameter_ids': ['other-business'], 'scope': {'segments': ['Segment A'], 'years': [2026], 'scenarios': ['base']}}))
        self.assertEqual(b.checkpoint(b.run(native_input=doc, context=ctx), 'A17')['status'], 'UNRESOLVED')
'''
path.write_text(body, encoding='utf-8', newline='\n')

code_path = ROOT / 'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py'
code = code_path.read_text(encoding='utf-8')
old = '    return paths\n\n\ndef _finite'
new = '''    # Read the already-declared conversion input/output bridge without running its formula.
    for _, (_, cal) in _calibration_index(native_input).items():
        for scenario, output in (cal.get("scenario_output_parameter_ids") or {}).items():
            ids = paths.get((cal.get("scope"), scenario))
            if ids is not None and ids.intersection(_ids(output)):
                ids.update(_ids((cal.get("scenario_input_parameter_ids") or {}).get(scenario)))
    return paths


def _finite'''
assert code.count(old) == 1
code = code.replace(old, new)
old = '''            if any(pid not in params for pid in output_ids) or not set(output_ids).intersection(
                    entry.get("supported_parameter_ids") or []):'''
new = '''            if any(params.get(pid, {}).get("unit") != cal.get("output_unit") for pid in output_ids):
                reasons.append("conversion_unit_incomparable")
            if any(pid not in params for pid in output_ids) or not set(output_ids).intersection(
                    entry.get("supported_parameter_ids") or []):'''
assert code.count(old) == 1
code = code.replace(old, new)
old = '            and all(pid in params for pid in parameter_ids)'
new = '''            and all(pid in params and any(pid in paths.get((seg, sc), set())
                    for seg in scope.get("segments") or [] for sc in scope.get("scenarios") or [])
                    for pid in parameter_ids)'''
assert code.count(old) == 1
code_path.write_text(code.replace(old, new), encoding='utf-8', newline='\n')
print('Regression cases and declared conversion/stress role bindings added')
