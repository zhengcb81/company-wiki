"""Reception data regressions; explicit fixtures, never NL entailment inference."""
from helpers import load_record, load_case, load_json, INDEX_PATH


def test_qualitative_assertions_never_require_numeric_slots():
    for record_id in ("facet_customer_orders", "facet_capacity_projects", "semantic_capacity_project"):
        for rule in load_record(record_id)["required_context"]:
            if rule["required_when"] != "quantity_emitted":
                assert not ({"quantity", "unit", "denominator"} & set(rule["slots"])), (record_id, rule)


def test_ir_optional_numeric_fact_has_full_original_numeric_support():
    case = load_case("real_cn_ir_premise_denial")
    fact = next(f for f in case["expectations"]["facts"] if f["id"] == "f5")
    assert fact["importance"] == "correctness_if_emitted"
    units = {u["unit_id"]: u for u in case["observation"]["units"]}
    for group in fact["any_support_sets"]:
        quotes = " ".join(units[uid]["anchor"]["exact_quote"] for uid in group)
        for original_number in ("37.17", "2.84", "10.15", "亿元"):
            assert original_number in quotes


def test_stage_alternative_support_does_not_claim_absent_order_information():
    fact = load_case("syn_stage_ladder")["expectations"]["facts"][0]
    assert all("u1" in group for group in fact["any_support_sets"])


def test_capacity_actual_and_plan_are_explicit_in_synthetic_original():
    case = load_case("syn_capacity_project")
    assert "一期已于2026年6月建成" in case["observation"]["units"][0]["text"]
    assert "二期" in case["observation"]["units"][0]["text"]
    assert "预计2027年12月建成" in case["observation"]["units"][0]["text"]


def test_store_fact_never_forces_optional_gmv():
    case = load_case("real_hk_annual_store_network")
    store = next(f for f in case["expectations"]["facts"] if f["id"] == "f1")
    assert all("GMV" not in keep for keep in store["must_preserve"])
    optional = next(f for f in case["expectations"]["facts"] if f["id"] == "f4")
    assert optional["importance"] == "correctness_if_emitted"


def test_denial_is_not_missing_a_nonexistent_commercialisation_stage():
    case = load_case("real_cn_ir_premise_denial")
    assert case["candidate_claim"]["modality"] == "denial"
    assert "stage" not in case["expected_missing_slots"]
    assert "stage" in case["not_applicable_slots"]


def test_consumer_customer_segment_does_not_prove_consumption_billing():
    row = next(r for r in load_json(INDEX_PATH)["coverage"] if r["mechanism"] == "consumption")
    assert row["evidence_status"] == "missing"
    assert row["case_ids"] == []
    assert row["gaps"]


def test_real_fixture_text_has_explicit_provenance_and_is_never_runtime_raw():
    from helpers import EXPECTED_CASE_IDS
    for cid in EXPECTED_CASE_IDS:
        case = load_case(cid)
        if case["kind"] != "real_excerpt":
            continue
        for unit in case["observation"]["units"]:
            assert unit["text_status"] in {"original_excerpt", "explanatory_reconstruction"}
            assert unit["text_source"]
            assert unit["runtime_raw"] is False


def test_qualitative_cooperation_has_a_legal_no_amount_case():
    case = load_case("syn_qualitative_cooperation")
    assert case["candidate_claim"]["quantity"] is None
    assert case["candidate_claim"]["unit"] is None
    assert not ({"quantity", "unit"} & set(case["expected_missing_slots"]))
    assert case["expectations"]["facts"][0]["importance"] == "required_business"


def test_conditional_self_funding_has_a_legal_no_amount_case():
    case = load_case("syn_qualitative_funding")
    assert case["candidate_claim"]["quantity"] is None
    assert case["candidate_claim"]["unit"] is None
    assert not ({"quantity", "unit"} & set(case["expected_missing_slots"]))
    assert case["candidate_claim"]["condition"]


def test_construction_schedule_does_not_claim_first_phase_already_completed():
    case = load_case("real_cn_equity_capacity_phasing")
    kept = case["expectations"]["facts"][0]["must_preserve"]
    assert not any("一期三个时点为已发生" in value for value in kept)
    assert any("不额外证明均已完成" in value for value in kept)


def test_replacement_capacity_has_its_own_original_scope_support():
    case = load_case("real_cn_equity_capacity_phasing")
    fact = next(f for f in case["expectations"]["facts"] if f["id"] == "f2")
    assert all("u3p" in group for group in fact["any_support_sets"])
    source_unit = next(u for u in case["observation"]["units"] if u["unit_id"] == "u3p")
    assert "替换" in source_unit["anchor"]["exact_quote"]
