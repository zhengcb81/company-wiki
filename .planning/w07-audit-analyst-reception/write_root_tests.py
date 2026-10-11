from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
target = ROOT / 'tests/test_root_w07_analyst_scope.py'
assert not target.exists()
body = r'''"""Non-author composition tests: scoped evidence cannot be promoted by labels alone."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('w07_builders', Path(__file__).with_name('test_w07_analyst_risk_audit.py'))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class RootScopeTests(unittest.TestCase):
    def unresolved(self, report, checkpoint):
        self.assertEqual(b.checkpoint(report, checkpoint)['status'], 'UNRESOLVED')

    def test_driver_cannot_borrow_another_segments_path(self):
        doc = b.make_input(drivers=[b.driver(segment='Segment B')])
        doc['segments'].append({'name': 'Segment B', 'scenarios': {}})
        self.unresolved(b.run(native_input=doc), 'A02')

    def test_driver_input_roles_are_not_limited_to_direct_revenue(self):
        doc = b.make_input()
        doc['segments'][0]['scenarios']['base']['driver_parameter_ids'] = {'quantity': ['0_base_2026'], 'price': ['0_base_2027']}
        forecast = b.make_forecast(segments=copy.deepcopy(doc['segments']))
        self.assertEqual(b.checkpoint(b.run(native_input=doc, forecast=forecast), 'A02')['status'], 'OBSERVED')

    def test_missing_parameter_definition_is_not_a_resolved_driver(self):
        doc = b.make_input(parameters=[])
        self.unresolved(b.run(native_input=doc), 'A02')

    def test_constraint_period_comes_from_parameter_not_id_spelling(self):
        doc = b.make_input(parameters=[b.parameter('opaque-cap')])
        forecast = b.make_forecast(constraints=[{'segments': ['Segment A'], 'scenario_parameter_ids': {'base': ['opaque-cap']}}])
        self.assertEqual(b.checkpoint(b.run(native_input=doc, forecast=forecast), 'A05')['status'], 'OBSERVED')

    def test_supported_cell_cannot_borrow_calibration_from_another_year(self):
        support = b.make_support({'Segment A': [b.support_entry('base', 2027, 'supported', supported=['0_base_2027'], calibration_ids=['reference_bridge'])]})
        self.unresolved(b.run(calibrations=[b.calibration()], support=support), 'A06')

    def test_supported_cell_cannot_borrow_calibration_from_another_segment(self):
        support = b.make_support({'Segment B': [b.support_entry('base', 2026, 'supported', supported=['0_base_2026'], calibration_ids=['reference_bridge'])]})
        self.unresolved(b.run(calibrations=[b.calibration()], support=support), 'A06')

    def test_supported_output_must_resolve_in_opened_native_input(self):
        doc = b.make_input(calibrations=[b.calibration()])
        doc['parameters'] = []
        self.unresolved(b.run(native_input=doc), 'A06')

    def test_dangling_calibration_is_not_hidden_by_a_valid_one(self):
        support = b.make_support({'Segment A': [b.support_entry('base', 2026, 'supported', supported=['0_base_2026'], calibration_ids=['reference_bridge', 'ghost'])]})
        self.unresolved(b.run(calibrations=[b.calibration()], support=support), 'A06')

    def test_string_false_is_not_independence_evidence(self):
        ctx = b.context_doc(b.statement('independence_note', {'claim_ids': ['c1', 'c2'], 'source_ids': ['s1', 's2'], 'independent': 'false'}))
        doc = b.make_input(claims=[b.claim('c1', 's1'), b.claim('c2', 's2')])
        self.unresolved(b.run(native_input=doc, context=ctx), 'A08')

    def test_post_announcement_consensus_cannot_be_a_prior_beat_baseline(self):
        ctx = b.context_doc(b.statement('beat_claim', {'baseline': {'kind': 'consensus', 'ref': 'feed', 'as_of_date': '2026-07-13', 'period': 'FY2026', 'unit': 'USD million'}, 'result': {'period': 'FY2026', 'unit': 'USD million', 'announced_date': '2026-07-12'}, 'comparison_driver_parameter_ids': ['0_base_2026']}))
        self.unresolved(b.run(context=ctx), 'A10')

    def test_range_without_observed_period_is_not_observed(self):
        doc = b.make_input(calibrations=[b.calibration(observed_period=None)])
        rows = b.findings(b.run(native_input=doc), 'A13')
        self.assertFalse(any(r['status'] == 'OBSERVED' and r['calibration_ids'] for r in rows))

    def test_invalid_range_does_not_cover_a_supported_cell(self):
        doc = b.make_input(calibrations=[b.calibration(observed_range={'lower': None, 'upper': None})])
        rows = b.findings(b.run(native_input=doc), 'A13')
        self.assertTrue(any(r['year'] == '2026' and 'support_period_gap' in r['reasons'] for r in rows))

    def test_joint_declaration_unknown_parameter_stays_unresolved(self):
        ctx = b.context_doc(b.statement('stress_declaration', {'joint': True, 'cross_exposure_declared': True, 'parameter_ids': ['ghost'], 'scope': {'segments': ['Segment A'], 'years': [2026], 'scenarios': ['base']}}))
        self.unresolved(b.run(context=ctx), 'A17')

    def test_joint_declaration_unknown_segment_stays_unresolved(self):
        ctx = b.context_doc(b.statement('stress_declaration', {'joint': True, 'cross_exposure_declared': True, 'parameter_ids': ['0_base_2026'], 'scope': {'segments': ['Ghost'], 'years': [2026], 'scenarios': ['base']}}))
        self.unresolved(b.run(context=ctx), 'A17')

    def test_actual_period_without_numeric_value_is_not_coverage(self):
        for value in (None, 'unknown', float('nan'), True):
            with self.subTest(value=repr(value)):
                ctx = b.context_doc(b.statement('actual_input', {'period': 'FY2026', 'value': value, 'unit': 'USD million'}))
                report = b.run(context=ctx)
                self.assertEqual(report['actual_input_refs']['years_checked'], [])
                self.assertIn('2026', report['actual_input_refs']['years_unchecked'])

    def test_empty_historical_record_is_not_actual_coverage(self):
        report = b.run(forecast=b.make_forecast(accuracy_records=[{'period': 'FY2026', 'years': ['FY2026']}]))
        self.assertEqual(report['actual_input_refs']['years_checked'], [])


if __name__ == '__main__':
    unittest.main()
'''
target.write_text(body, encoding='utf-8', newline='\n')
print(target)
