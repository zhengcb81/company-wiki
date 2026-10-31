"""Bounded actor context augments quotes without requiring entity resolution."""
import pytest

from company_wiki.resource_budget import WorkBudget


def unit(text, **kwargs):
    return {"text": text, "parent_id": "source-a", "role": "company_filing",
            "kind": "paragraph", **kwargs}


def close(target, previous=(), *, complete=True, budget=None, **options):
    from company_wiki.source_catalog.narrative_actor_context import actor_context_closure
    units = {"target": target, **{f"p{i}": v for i, v in enumerate(previous)}}
    return actor_context_closure("target", tuple(f"p{i}" for i in range(len(previous))),
        units=units, window_complete=complete, work_budget=budget or WorkBudget(100_000), **options)


@pytest.mark.parametrize("name", ["Oriole", "雨澜", "unknown-name-42"])
def test_unknown_business_context_is_original_and_not_identity(name):
    context = f"As we assess {name}’s opportunities, new orders are rising."
    result = close(unit("Beyond this, our policies increased by 12%."), [unit(context)])
    assert result["status"] == "unique"
    assert result["required_original_unit_ids"] == ("p0",)
    assert result["attribution"] == "unknown"
    assert result["declaration_refs"] == result["member_refs"] == []
    assert result["reference_kind"] == "actor_context"
    assert result["reference_refs"][0]["unit_id"] == "target"


def test_actual_geico_adjacent_paragraph_is_retained_without_brand_rule():
    previous = "As we view GEICO’s current opportunities, Tony and I feel like two hungry mosquitoes. Americans are flocking to GEICO."
    result = close(unit("Beyond this, we are gaining ground in allied lines. Our motorcycle policies increased by 23.4%."), [unit(previous)])
    assert result["required_original_unit_ids"] == ("p0",)
    assert result["attribution"] == "unknown"


@pytest.mark.parametrize("text", ["Our products include sterile tools.", "We manufacture tools.", "我们的产品包括试剂。"])
def test_first_person_without_predecessor_does_not_create_gate(text):
    result = close(unit(text), complete=False)
    assert result["status"] == "not_applicable"
    assert result["attribution"] == "unknown"
    assert not result["required_original_unit_ids"]


def test_incomplete_search_can_still_retain_observed_adjacent_context():
    result = close(unit("In this business, our orders have not yet been approved."),
                   [unit("The Juniper subsidiary is still awaiting approval.")], complete=False)
    assert result["status"] == "unique"
    assert result["required_original_unit_ids"] == ("p0",)
    assert any(x["code"] == "actor_window_incomplete" for x in result["diagnostics"])


@pytest.mark.parametrize("previous", [
    unit("Does Juniper already supply Cedar?", role="investor_question"),
    unit("Q: Does Juniper already supply Cedar?"),
    unit("Question: Juniper already supplies Cedar."),
    unit("問題：甲公司已经向乙公司供货。"),
    unit("Juniper", kind="heading"),
    unit("Juniper | 10 | 20", kind="table_row"),
    unit("Juniper operates this business.", parent_id="source-b"),
    unit("Juniper operates this business.", speaker="speaker-b"),
    unit("Juniper operates this business.", section_id="other"),
])
def test_question_table_and_observed_scope_boundaries_never_donate(previous):
    result = close(unit("Beyond this, we have not started shipments.", speaker="speaker-a", section_id="current"), [previous])
    assert result["status"] == "not_applicable"
    assert not result["required_original_unit_ids"]


def test_no_skipping_illegal_nearest_unit_to_older_body():
    result = close(unit("Beyond this, our orders increased."), [unit("Juniper operates a factory."), unit("Another question?", role="analyst")])
    assert not result["required_original_unit_ids"]


def test_switch_in_target_does_not_borrow_previous_subbusiness():
    result = close(unit("Separately, the parent company plans a factory. We expect approval next year."), [unit("The subsidiary operates a factory.")])
    assert result["status"] == "not_applicable"
    assert not result["required_original_unit_ids"]


def test_latest_body_only_keeps_switch_and_negative_condition_original():
    latest = "Separately, our new subsidiary will not operate unless approved."
    result = close(unit("In this business, we have not commenced production."), [unit("The older subsidiary is already operating."), unit(latest)])
    assert result["required_original_unit_ids"] == ("p1",)
    assert result["declaration_refs"] == []


def test_parallel_businesses_do_not_become_single_entity_identity():
    result = close(unit("Our orders increased."), [unit("Two subsidiaries, Oriole and Juniper, both serve this market.")])
    assert result["attribution"] == "unknown"
    assert result["declaration_refs"] == []


@pytest.mark.parametrize("text", ["Juniper sells tools.", "Wind capacity increased from 33 MW to 794 MW.", "The word OUR is a document title."])
def test_not_applicable_negative(text):
    result = close(unit(text), [unit("Oriole serves this market.")])
    assert result["status"] == "not_applicable"
    assert not result["required_original_unit_ids"]


def test_envelope_counts_context_and_target_without_truncation():
    result = close(unit("Beyond this, our orders increased."), [unit("x" * 100)], max_chars=80)
    assert result["status"] == "not_applicable"
    assert not result["required_original_unit_ids"]
    assert any(x["code"] == "actor_context_envelope" for x in result["diagnostics"])


def test_budget_is_actual_shared_account_and_exhaustion_partial():
    budget = WorkBudget(8)
    result = close(unit("Our orders increased."), [unit("The subsidiary serves this market.")], budget=budget)
    assert result["status"] == "partial"
    assert not result["required_original_unit_ids"]
    assert budget.exhausted


def test_success_charges_context_and_target_before_scanning():
    budget = WorkBudget(10_000)
    target, previous = "Beyond this, our orders increased.", "The subsidiary serves this market."
    close(unit(target), [unit(previous)], budget=budget)
    assert budget.used >= len(target) + len(previous)


@pytest.mark.parametrize('text', ['Our platform routes orders through partners.',
                                'We have not yet started shipments.',
                                '我们的新产品已进入客户生产验证。',
                                'Additionally, our customers have placed orders.',
                                '此外，我们已收到订单。'])
def test_first_person_or_addition_alone_does_not_require_unrelated_predecessor(text):
    result = close(unit(text), [unit('The earlier topic is unrelated.')])
    assert result['status'] == 'not_applicable'
    assert not result['required_original_unit_ids']
    assert result['attribution'] == 'unknown'


def test_chinese_explicit_backward_business_scope_keeps_its_context():
    result = close(unit('在此基础上，我们计划明年投产，仍须取得审批。'), [unit('子业务仍在筹建中。')])
    assert result['required_original_unit_ids'] == ('p0',)
    assert result['attribution'] == 'unknown'
