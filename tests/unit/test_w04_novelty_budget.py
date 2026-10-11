"""Actual tokenizer values, bounded completeness and a pure budget contract."""
from dataclasses import fields

import pytest

from company_wiki.source_catalog.narrative_budget import BudgetItem, budget_diagnostics, select_budget_items
from company_wiki.source_catalog import narrative_semantic_coverage as coverage


def item(key, text, score):
    kwargs = dict(item_id=key, group_id=key, page_key=("page", score),
        locator=key, order_key=(score,), reasons=("new_product_commercialization_milestone",),
        score=score, is_heading=False, payload=object(), evidence_chars=len(text),
        semantic_tokens=coverage.coverage_tokens(text))
    if "coverage_signature" in {field.name for field in fields(BudgetItem)}:
        kwargs["coverage_signature"] = coverage.coverage_signature(text)
    return BudgetItem(**kwargs)


@pytest.mark.parametrize("a,b", [("300", "500"), ("2.5", "3.5"), ("85%", "95%"), ("6-8", "8-12")])
def test_actual_tokenizer_does_not_erase_standalone_numeric_facts(a, b):
    assert coverage.coverage_tokens(f"LPCVD设备累计出货{a}反应台") != coverage.coverage_tokens(f"LPCVD设备累计出货{b}反应台")


def test_budget_uses_supplied_signature_without_reading_payload_or_files(monkeypatch):
    text = "公司持续推进客户支持工作，并完善产品工艺。LPCVD设备已累计交付300反应台。"
    items = (item("old", text, 30), item("new", text.replace("300", "500"), 29),
             item("weak", "医疗设备已经交付客户。", 1))
    def blocked(*args, **kwargs):
        raise AssertionError("budget must not read files or payload")
    monkeypatch.setattr("builtins.open", blocked)
    chosen = select_budget_items(items, limit=2, policy="semantic_coverage/1")
    omitted = budget_diagnostics(items, limit=2, policy="semantic_coverage/1")
    assert {value.item_id for value in chosen} == {"old", "new"}
    assert {key for row in omitted for key in row.item_ids} == {"weak"}


def test_incomplete_bounded_signature_cannot_call_long_content_repetition():
    background = " ".join(f"word{i} phrase{i}" for i in range(600))
    old = background + " LPCVD equipment has shipped 300 reactors."
    new = background + " LPCVD equipment has shipped 500 reactors."
    items = (item("old", old, 30), item("new", new, 29),
             item("weak", "Medical equipment technical background and general service context.", 1))
    assert {v.item_id for v in select_budget_items(items, limit=2, policy="semantic_coverage/1")} == {"old", "new"}


def test_missing_subject_context_disables_redundancy_penalty():
    text = "围绕技术路线持续改进相关工艺和质量流程。累计达到300个。"
    signature = coverage.coverage_signature(text)
    assert not signature.complete
    assert not coverage.softly_repeats(signature, signature)


def test_group_signature_rejoins_cross_line_actor_and_predicate():
    signature = coverage.group_coverage_signature(["LPCVD设", "备已累计交付300反应台。"])
    assert signature.complete
    assert "lpcvd设备已累计交付300反应台" in signature.protected_sentences
    assert any(stage == "shipment" and realized for stage, _predicate, realized, _reason in signature.stage_signals)
    english = coverage.group_coverage_signature(["The equipment", "has shipped 300 reactors."])
    assert english.complete
    assert any(stage == "shipment" and realized for stage, _predicate, realized, _reason in english.stage_signals)


def test_group_signature_is_bounded_and_does_not_read_later_parts_after_truncation():
    def parts():
        yield "设备" * 5000
        raise AssertionError("truncated metadata does not need to consume unbounded content")
    signature = coverage.group_coverage_signature(parts())
    assert not signature.complete
    assert len(signature.tokens) <= 512
    assert not coverage.softly_repeats(signature, signature)
