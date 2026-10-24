"""Independent neutral grammar checks; no company/page/amount fixture matching."""
from __future__ import annotations
import pytest
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact, reading_material_value

@pytest.mark.parametrize("text", (
    "Our order backlog is not quantified, while employee headcount was 800.",
    "Our order backlog is strong, while cash balances were $40 million.",
    "本公司未交付订单尚未披露，员工人数为800人。",
))
def test_stock_cannot_borrow_other_subject_amount(text):
    assert "operating_contract_stock" not in detect_reading_business_fact(text).topics

@pytest.mark.parametrize("text", (
    "Revenue is recognized on shipment, while payroll is allocated based on customer's location.",
    "本公司收入按发货时间确认，而差旅费按客户所在地统计。",
    "本公司收入上升，客户总部所在地按合同登记。",
))
def test_geographic_revenue_needs_its_own_allocation_relation(text):
    assert "customer_revenue_geography" not in detect_reading_business_fact(text).topics

@pytest.mark.parametrize("text", (
    "Our order backlog was $80 million, and our supplier will deliver its products in FY2028.",
    "Our order backlog was $80 million, and unrelated equity will be recognized in FY2028.",
    "Our order backlog was $80 million, but product revenue will be recognized in FY2028 under a different contract.",
    "本公司在手订单余额为80亿元，员工奖金将于2028年度确认收入。",
))
def test_conversion_does_not_borrow_new_actor_or_different_subject(text):
    fact = detect_reading_business_fact(text)
    assert "operating_contract_stock" in fact.topics
    assert "contract_revenue_conversion" not in fact.topics

@pytest.mark.parametrize("text", (
    "Our revenue from customers in the Northern market amounted to $90 million.",
    "Revenue from customers in international markets increased by 12%.",
    "Our customer revenue by geographic location was $80 million in the domestic market.",
))
def test_geography_is_not_limited_to_chinese_or_headquarters_definitions(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible
    assert "customer_revenue_geography" in fact.topics
    assert reading_material_value(fact) == "meaningful_fact"

@pytest.mark.parametrize("text", (
    "Our order backlog was $80 million, of which 50% will be recognized in FY2028.",
    "Our remaining performance obligations were $80 million, of which 50% is expected to be recognized in FY2028.",
    "本公司在手订单余额为80亿元，其中25亿元预计于2028年度确认收入。",
))
def test_same_stock_partitive_future_conversion_remains_valuable(text):
    fact = detect_reading_business_fact(text)
    assert {"operating_contract_stock", "contract_revenue_conversion"} <= set(fact.topics)
    assert reading_material_value(fact) == "meaningful_fact"

@pytest.mark.parametrize("text", (
    "Our business consists of software subscriptions and equipment service.",
    "本公司业务分为测量仪器和控制软件。",
))
def test_named_scope_not_just_generic_activity_remains_valuable(text):
    fact = detect_reading_business_fact(text)
    assert "business_scope" in fact.topics
    assert reading_material_value(fact) == "meaningful_fact"

@pytest.mark.parametrize("text", (
    "Our factories are located in three geographic markets.",
    "Our cash balances are attributed to the countries of the group's banks.",
    "Our business consists of research, development and manufacturing.",
))
def test_generic_and_non_revenue_geography_does_not_get_new_coverage(text):
    fact = detect_reading_business_fact(text)
    assert not {"customer_revenue_geography", "business_scope"} & set(fact.topics)


@pytest.mark.parametrize("text", (
    "Our order backlog was $80 million and will be delivered in FY2028.",
    "Our remaining performance obligations were $80 million, 50% of which is expected to be recognized in FY2028.",
    "Our remaining performance obligations were $80 million, with 50% expected to be recognized in FY2028.",
    "Our remaining performance obligations of $80 million are expected to be recognized in FY2028.",
    "本公司订单余额为80亿元，并将在2028年度确认收入。",
))
def test_stock_head_quantity_and_same_subject_conversion_grammar(text):
    fact = detect_reading_business_fact(text)
    assert {"operating_contract_stock", "contract_revenue_conversion"} <= set(fact.topics)


def test_relative_contract_description_does_not_change_conversion_subject():
    text = ("Our remaining performance obligations were $80 million, of which $10 million "
            "relates to contracts where the customer will deliver equipment in FY2028.")
    assert "contract_revenue_conversion" not in detect_reading_business_fact(text).topics


def test_negated_stock_amount_does_not_become_measured_stock():
    fact = detect_reading_business_fact("Our order backlog was not $80 million, but the amount has not been disclosed.")
    assert "operating_contract_stock" not in fact.topics


@pytest.mark.parametrize("text", (
    "Our remaining performance obligations are expected to be recognized over the next twelve months.",
    "We expect to recognize 50% of the remaining performance obligations over the next twelve months.",
))
def test_existing_direct_or_prefix_recognition_without_stock_amount_remains_useful(text):
    fact = detect_reading_business_fact(text)
    assert "contract_revenue_conversion" in fact.topics
    assert reading_material_value(fact) == "meaningful_fact"


def test_new_module_bytes_change_the_actual_reading_inventory(tmp_path, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.source_catalog import narrative_business_disclosures
    original = decision_inventory.import_module
    before = decision_inventory._versions()["business_algorithms"]
    changed = tmp_path / "disclosure_variant.py"
    changed.write_bytes(Path(narrative_business_disclosures.__file__).read_bytes() + b"\n# independent byte identity probe\n")
    def imported(name):
        return SimpleNamespace(__file__=str(changed)) if name == narrative_business_disclosures.__name__ else original(name)
    monkeypatch.setattr(decision_inventory, "import_module", imported)
    assert decision_inventory._versions()["business_algorithms"] != before


def test_numeric_noncarrier_tail_finishes_within_bounded_runtime():
    # Start-up/import time is excluded; this checks the parser, not machine speed.
    import os
    import subprocess
    import sys
    code = ("from company_wiki.source_catalog.narrative_business_disclosures import disclosure_relations; "
            "print('READY',flush=True); input(); "
            "print(disclosure_relations('Our order backlog was $80 million, of which '+"
            "'1'*48+' widgets will be recognized in FY2028.'),flush=True)")
    worker = subprocess.Popen([sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE":"1"})
    try:
        assert worker.stdout.readline().strip() == "READY"
        worker.stdin.write("go\n")
        worker.stdin.flush()
        try:
            stdout, stderr = worker.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            pytest.fail("Bounded source prefix triggers excessive parser backtracking")
        assert worker.returncode == 0, stderr
        assert "contract_revenue_conversion" not in stdout
    finally:
        if worker.poll() is None:
            worker.kill()
        worker.communicate()


@pytest.mark.parametrize("text", (
    "Our remaining obligations were $80 million for environmental remediation.",
    "Our remaining obligations were $80 million for pension payments.",
))
def test_non_customer_obligations_are_not_customer_contract_stock(text):
    assert "operating_contract_stock" not in detect_reading_business_fact(text).topics
