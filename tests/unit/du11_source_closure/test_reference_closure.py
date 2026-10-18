"""B2 bounded product-reference closure: grammar, engine and envelope.

Pure unit contracts. No parser, PDF, provider or model is involved. The
declaration is evidence, never a second fact or a permission to select.
"""
import pytest

from company_wiki.document_understanding.layout_hints.contract import (
    DEFAULT_LIMITS, WorkBudget,
)
from company_wiki.document_understanding.operating_states.product_reference import (
    find_product_declarations, find_product_deictic,
)
from company_wiki.document_understanding.operating_states.relations import (
    OperatingRelationSession,
)

CN_DECLARATION = (
    "公司推出Preforma Uniflash系列金属硅化物集成系统，包含SA/SU、SPTi、ALDTiNM三类产品。"
)
CN_TARGET = "该系列产品已交付多个先进客户。"
EN_DECLARATION = (
    "The Company launched the Preforma Uniflash series, including SA/SU, SPTi and ALDTiNM."
)
EN_TARGET = "These products have been delivered to multiple customers."
TW_TARGET = "該系列產品已交付多個客戶。"


def unit(text, *, parent="source-a", role="company_filing", kind="text_block"):
    return {"text": text, "parent_id": parent, "role": role, "kind": kind,
            "locator": {"page_number": 1, "paragraph_index": 0}}


def session(units):
    return OperatingRelationSession(units,
        work_budget=WorkBudget(DEFAULT_LIMITS["max_work_units"]))


# ------------------------------------------------------------------ grammar


def test_chinese_product_deictic_is_found_with_its_exact_span():
    found = find_product_deictic(CN_TARGET)
    assert len(found) == 1
    assert CN_TARGET[found[0].span[0]:found[0].span[1]] == "该系列产品"
    assert found[0].family is True


def test_company_and_generic_pronouns_are_not_product_references():
    assert not find_product_deictic("该公司已交付产品。")
    assert not find_product_deictic("其中包含多项技术指标。")
    assert not find_product_deictic("本期营业收入同比增长。")


def test_traditional_and_english_deictics_are_recognized():
    assert len(find_product_deictic(TW_TARGET)) == 1
    assert len(find_product_deictic(EN_TARGET)) == 1


def test_named_declaration_is_one_family_with_its_collective_members():
    found = find_product_declarations(CN_DECLARATION)
    assert len(found) == 1
    declaration = found[0]
    assert "preforma" in declaration.family.casefold()
    assert declaration.collective is True
    assert len(declaration.members) == 3
    assert [CN_DECLARATION[a:b] for a, b in declaration.members] == ["SA/SU", "SPTi", "ALDTiNM"]
    assert CN_DECLARATION[declaration.span[0]:declaration.span[1]].startswith("Preforma")


def test_generic_appositive_is_not_a_named_declaration():
    assert not find_product_declarations("公司推出金属硅化物集成系统，已进入客户验证。")


def test_english_declaration_is_named_and_collective():
    found = find_product_declarations(EN_DECLARATION)
    assert len(found) == 1 and found[0].collective is True


# ------------------------------------------------------------------- engine


def test_unique_deictic_resolves_to_its_predecessor_declaration():
    engine = session({"d": unit(CN_DECLARATION), "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] in {"unique", "collective"}
    assert result["required_original_unit_ids"] == ("d",)
    assert result["declaration_refs"]
    ref = result["declaration_refs"][0]
    assert ref["unit_id"] == "d"
    assert CN_DECLARATION[ref["char_start"]:ref["char_end"]].startswith("Preforma")


def test_deictic_closed_inside_its_own_package_is_not_applicable():
    engine = session({"t": unit(CN_DECLARATION + CN_TARGET)})
    result = engine.reference_closure("t", (), window_complete=True)
    assert result["status"] == "not_applicable"
    assert result["required_original_unit_ids"] == ()


def test_two_competing_series_are_ambiguous_not_nearest_wins():
    engine = session({"d1": unit(CN_DECLARATION),
                      "d2": unit("公司同时推出Alpha系列刻蚀设备，已交付客户。"),
                      "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d1", "d2"), window_complete=True)
    assert result["status"] == "ambiguous"
    assert not result["declaration_refs"]


def test_absent_declaration_is_missing():
    engine = session({"d": unit("公司上半年营业收入同比增长百分之十。"), "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] == "missing"
    assert result["required_original_unit_ids"] == ()


def test_incomplete_window_is_partial_and_never_unique():
    engine = session({"d": unit(CN_DECLARATION), "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=False)
    assert result["status"] == "partial"
    assert not result["declaration_refs"]


def test_singular_product_deictic_keeps_legacy_admission():
    engine = session({"d": unit(CN_DECLARATION),
                      "t": unit("该设备仍需完成认证，预计明年进入量产。")})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] == "not_applicable"
    assert result["required_original_unit_ids"] == ()


def test_target_without_a_product_deictic_is_not_applicable():
    engine = session({"d": unit(CN_DECLARATION),
                      "t": unit("公司向客户交付样机开展生产验证，尚未获准量产。")})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] == "not_applicable"
    assert result["required_original_unit_ids"] == ()


def test_a_question_cannot_donate_the_issuer_declaration():
    engine = session({"d": unit("请问该系列产品是否已经交付客户？", role="investor_question"),
                      "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] == "missing"


def test_cross_parent_predecessor_is_rejected():
    engine = session({"d": unit(CN_DECLARATION, parent="source-b"), "t": unit(CN_TARGET)})
    with pytest.raises(ValueError):
        engine.reference_closure("t", ("d",), window_complete=True)


def test_cache_separates_completeness_and_predecessor_order():
    engine = session({"d": unit(CN_DECLARATION), "t": unit(CN_TARGET)})
    complete = engine.reference_closure("t", ("d",), window_complete=True)
    incomplete = engine.reference_closure("t", ("d",), window_complete=False)
    assert complete is not incomplete
    assert incomplete["status"] == "partial"


def test_closure_is_cached_by_target_and_exact_predecessor_scope():
    engine = session({"d": unit(CN_DECLARATION), "t": unit(CN_TARGET)})
    first = engine.reference_closure("t", ("d",), window_complete=True)
    again = engine.reference_closure("t", ("d",), window_complete=True)
    assert again is first
    changed = engine.reference_closure("t", (), window_complete=True)
    assert changed["status"] == "missing"



def test_forward_declaration_does_not_close_the_reference():
    engine = session({"t": unit(CN_TARGET + "公司同时推出Alpha系列刻蚀设备。")})
    result = engine.reference_closure("t", (), window_complete=True)
    assert result["status"] == "missing"


def test_two_internal_families_before_the_deictic_are_ambiguous():
    engine = session({"t": unit(
        "公司推出Alpha系列设备。公司推出Beta系列设备。该系列产品已交付。")})
    result = engine.reference_closure("t", (), window_complete=True)
    assert result["status"] == "ambiguous"


def test_declaration_refs_use_original_offsets_across_a_line_wrap():
    text = "公司持续投入研发\n公司推出Preforma Uniflash系列设备。"
    engine = session({"d": unit(text), "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    ref = result["declaration_refs"][0]
    assert text[ref["char_start"]:ref["char_end"]] == "Preforma Uniflash系列"
    assert result["required_original_unit_ids"] == ("d",)



def test_collective_members_are_not_borrowed_from_an_unrelated_clause():
    declarations = find_product_declarations(
        "公司客户包括华为、小米。公司推出X系列产品，已实现量产。")
    assert len(declarations) == 1
    assert declarations[0].collective is False



def test_a_customer_statement_cannot_donate_the_issuer_declaration():
    engine = session({"d": unit("客户推出Alpha系列设备，已开始量产。"), "t": unit(CN_TARGET)})
    result = engine.reference_closure("t", ("d",), window_complete=True)
    assert result["status"] == "missing"
