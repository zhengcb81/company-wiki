"""Install focused public-contract tests before implementation in the ROOT leaf only."""
from pathlib import Path

leaf = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root")
(leaf / "tests/test_financial_measure_typed_contract.py").write_text('''"""Behavior of typed arithmetic, not source truth or forecast quality."""
import copy
import unittest
from test_financial_measure_audit import module, obs, flow, rel, res, ledger, status

def conversion(**result_updates):
    result = flow("converted", "12", scale="亿")
    result.update(result_updates)
    return ledger([flow("revenue", "1.2", scale="billion")],
                  [rel("sc", "scale_conversion", ["revenue"], result)])

def growth(end_value="120", base_value="100"):
    return ledger([flow("end", end_value), flow("base", base_value, start="2023-01-01", end="2023-12-31")],
                  [rel("g", "growth_rate", ["end", "base"],
                       res("growth", "20", "percent", None, "growth", period_start="2024-01-01", period_end="2024-12-31"))])

class TypedMeasureContractTests(unittest.TestCase):
    def test_each_conversion_output_context_field_is_checked(self):
        for field, value in (("entity_key", "other"), ("definition", "cash_balance"),
                             ("period_start", "2023-01-01"), ("period_end", "2025-12-31")):
            with self.subTest(field=field):
                self.assertNotEqual(module.audit_measures(conversion(**{field: value}))["overall"], "PASS")

    def test_amount_difference_cannot_change_output_currency(self):
        data = growth()
        data["relations"] = [rel("d", "difference", ["end", "base"], flow("change", "20", currency="CNY"))]
        self.assertEqual(module.audit_measures(data)["overall"], "INVALID")

    def test_growth_result_must_be_growth_kind_and_end_time(self):
        for changes in ({"measure_kind": "ratio"}, {"period_start": "2023-01-01", "period_end": "2023-12-31"}):
            with self.subTest(changes=changes):
                data = growth()
                data["relations"][0]["result"].update(changes)
                self.assertNotEqual(module.audit_measures(data)["overall"], "PASS")

    def test_positive_base_can_fall_to_zero_or_negative(self):
        for end, rate in (("0", "-100"), ("-20", "-120")):
            with self.subTest(end=end):
                data = growth(end)
                data["relations"][0]["result"]["value"] = rate
                self.assertEqual(module.audit_measures(data)["overall"], "PASS")

    def test_all_fixed_ops_enforce_exact_arity(self):
        for op in ("scale_conversion", "fx_conversion", "difference", "growth_rate", "cagr", "share"):
            for count in (0, 3):
                with self.subTest(op=op, count=count):
                    data = conversion()
                    data["relations"][0].update(op=op, inputs=["revenue"] * count)
                    self.assertEqual(module.audit_measures(data)["overall"], "INVALID")

    def test_structurally_invalid_dependency_cannot_have_pass_relation(self):
        data = conversion()
        data["observations"][0]["definition"] = []
        report = module.audit_measures(data)
        self.assertEqual(report["overall"], "INVALID")
        self.assertNotEqual(report["relation_checks"][0]["status"], "PASS")

    def test_guidance_and_assumptions_are_not_promoted_to_actual(self):
        for role in ("management_guidance", "analyst_assumption", "scenario_stress"):
            with self.subTest(role=role):
                data = conversion()
                data["observations"][0]["evidence_role"] = role
                self.assertNotEqual(module.audit_measures(data)["overall"], "PASS")

    def test_future_guidance_and_explicit_assumption_keep_their_roles(self):
        for role in ("management_guidance", "analyst_assumption"):
            with self.subTest(role=role):
                data = conversion()
                for item in [data["observations"][0], data["relations"][0]["result"]]:
                    item.update(evidence_role=role, period_start="2027-01-01", period_end="2027-12-31")
                    if role == "analyst_assumption":
                        item.update(source_ref=None, rationale="explicit model scenario; not a fact")
                self.assertEqual(module.audit_measures(data)["overall"], "PASS")

    def test_declared_source_availability_after_asof_is_unresolved(self):
        data = conversion()
        data["observations"][0]["available_by"] = "2026-10-12"
        self.assertEqual(module.audit_measures(data)["overall"], "UNRESOLVED")

    def test_future_reported_fact_is_not_silently_actual(self):
        data = conversion()
        for item in [data["observations"][0], data["relations"][0]["result"]]:
            item.update(period_start="2027-01-01", period_end="2027-12-31")
        self.assertEqual(module.audit_measures(data)["overall"], "UNRESOLVED")

    def test_malformed_json_field_shapes_are_diagnostics_not_batch_crashes(self):
        for target, field in (("observation", "id"), ("observation", "scale"),
                              ("observation", "measure_kind"), ("observation", "evidence_role"),
                              ("relation", "op"), ("relation", "relation_id")):
            with self.subTest(target=target, field=field):
                data = conversion()
                item = data["observations"][0] if target == "observation" else data["relations"][0]
                item[field] = {"unexpected": "object"}
                self.assertEqual(module.audit_measures(data)["overall"], "INVALID")

    def test_duplicate_relation_ids_are_invalid(self):
        data = conversion()
        data["relations"].append(copy.deepcopy(data["relations"][0]))
        self.assertEqual(module.audit_measures(data)["overall"], "INVALID")

    def test_daytime_malformed_or_contradictory_anchors_are_diagnosed(self):
        for changes in ({"period_start": "20240101"}, {"point_date": "2024-12-31"},
                        {"available_by": "nonsense"}):
            with self.subTest(changes=changes):
                data = conversion()
                data["observations"][0].update(changes)
                self.assertEqual(module.audit_measures(data)["overall"], "INVALID")

    def test_rounding_uses_integer_places_and_explicit_display_precision(self):
        for places in (True, 2.4, "2"):
            with self.subTest(places=places):
                data = conversion()
                data["relations"][0]["rounding"] = {"places": places, "basis": "displayed to two decimals"}
                self.assertEqual(module.audit_measures(data)["overall"], "INVALID")
        data = conversion()
        data["relations"][0]["rounding"] = {"places": 2, "basis": "displayed to two decimals"}
        self.assertEqual(module.audit_measures(data)["overall"], "PASS")

    def test_relative_precision_has_no_one_unit_absolute_floor(self):
        data = conversion()
        data["observations"][0].update(value="0.0000000000000000001", scale="unit")
        data["relations"][0]["result"].update(value="0.0000000001", scale="unit")
        self.assertEqual(module.audit_measures(data)["overall"], "FAIL")

    def test_cagr_declared_two_point_six_years_for_three_years_fails(self):
        data = growth("133.1")
        data["observations"][1].update(period_start="2021-01-01", period_end="2021-12-31")
        data["relations"][0].update(op="cagr", years="2.6")
        data["relations"][0]["result"]["value"] = "11.5"
        self.assertNotEqual(module.audit_measures(data)["overall"], "PASS")
        self.assertTrue(any(d["code"] == "cagr_period_mismatch" for d in module.audit_measures(data)["relation_checks"][0]["diagnostics"]))

    def test_complete_declared_coverage_is_not_a_pass_when_values_fail(self):
        data = conversion()
        data["relations"][0]["result"]["value"] = "1200"
        self.assertFalse(module.audit_measures(data)["coverage"]["coverage_pass"])

if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")
