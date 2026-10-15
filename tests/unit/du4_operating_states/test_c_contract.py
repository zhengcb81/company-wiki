"""Phase B contract: schema, budget, immutability, offsets and determinism.

No API, config, AUTO run, original reopen or production write happens here;
budgets are fresh local ``WorkBudget`` instances and fixtures live in the
lane's own test directory only.
"""

from __future__ import annotations

import copy
import json

import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.operating_states import detect_operating_relations

from .helpers import (
    REF_FIELDS,
    make_observation,
    make_unit,
    run,
    run_text,
)


def _units(*texts: str, parent_id: str = "p1") -> dict[str, dict]:
    return {
        f"u{index}": make_unit(text, unit_id=f"u{index}", parent_id=parent_id)
        for index, text in enumerate(texts)
    }


def test_wrong_schema_version_raises_value_error() -> None:
    units = _units("公司现无生产 VC。")
    observation = make_observation(
        units, target="u0", schema_version="du4-operating-observation/2"
    )
    with pytest.raises(ValueError):
        run(observation)


def test_missing_target_unit_raises_value_error() -> None:
    units = _units("公司现无生产 VC。")
    observation = make_observation(units, target="missing")
    with pytest.raises(ValueError):
        run(observation)


def test_units_as_sequence_raises_value_error() -> None:
    observation = {
        "schema_version": "du4-operating-observation/1",
        "unit_id": "u0",
        "units": [{"unit_id": "u0", "text": "x"}],
    }
    with pytest.raises(ValueError):
        run(observation)


def test_unit_missing_required_fields_raises_value_error() -> None:
    units = {"u0": {"text": "公司现无生产 VC。"}}
    observation = make_observation(units, target="u0")
    with pytest.raises(ValueError):
        run(observation)


def test_duplicate_context_ids_raise_value_error() -> None:
    units = _units("公司现无生产 VC。", "同上。")
    observation = make_observation(
        units, target="u0", context_unit_ids=["u1", "u1"]
    )
    with pytest.raises(ValueError):
        run(observation)


def test_non_string_context_ids_raise_value_error() -> None:
    units = _units("公司现无生产 VC。", "同上。")
    observation = make_observation(units, target="u0", context_unit_ids=["u1"])
    observation["context_unit_ids"] = [3]
    with pytest.raises(ValueError):
        run(observation)


def test_enum_values_are_contract_legal() -> None:
    texts = [
        "公司现无生产 VC。",
        "子公司暂停滤芯生产。",
        "青梧设备尚未商业化。",
        "公司与谷石已建立联系。",
        "公司希望与谷石开展合作。",
        "并非没有生产 QJ-11。",
        "公司目前无法确定是否涉及该储能业务。",
        "Arbor Ltd. does not manufacture Novalon filters.",
    ]
    for text in texts:
        result, _, _ = run_text(text)
        for relation in result["relations"]:
            assert relation["activity"] in {
                "production", "commercialization", "qualification", "shipment",
                "capacity", "business_scope", "business_relationship", "other_operating",
            }, (text, relation)
            assert relation["polarity"] in {"positive", "negative", "unknown"}
            assert relation["stage"] in {
                "current", "not_yet", "suspended", "discontinued", "planned",
                "conditional", "contact_established", "intended_cooperation", "unknown",
            }
            assert relation["attribution"] in {
                "issuer", "quoted_related_party", "other", "unknown",
            }
            assert relation["modality"] in {
                "actual", "planned", "conditional", "aspirational", "uncertain",
            }


def test_missing_context_unit_is_partial_not_rejection() -> None:
    units = _units("公司现无生产 VC。")
    observation = make_observation(units, target="u0", context_unit_ids=["gone"])
    result, _ = run(observation)
    assert result["status"] == "partial"
    assert result["relations"], result
    assert any(
        diagnostic.get("code") == "context_unit_missing" for diagnostic in result["diagnostics"]
    )


def test_zero_budget_returns_partial_with_zero_work() -> None:
    units = _units("公司现无生产 VC。")
    observation = make_observation(units, target="u0")
    budget = WorkBudget(0)
    result = detect_operating_relations(observation, work_budget=budget)
    assert result["status"] == "partial"
    assert result["relations"] == []
    assert result["work_used"] == 0
    assert budget.exhausted
    assert any(
        diagnostic.get("code") == "work_budget_exhausted" for diagnostic in result["diagnostics"]
    )


def test_partial_budget_keeps_determined_results() -> None:
    text = "公司现无生产 VC。子公司暂停滤芯生产。青梧设备尚未商业化。"
    units = _units(text)
    observation = make_observation(units, target="u0")
    generous = detect_operating_relations(observation, work_budget=WorkBudget(100000))
    full = [json.dumps(relation, sort_keys=True) for relation in generous["relations"]]
    assert len(full) == 3
    seen_non_empty = False
    # Work now includes actual character preparation and regex scans. Sample
    # the real caller range, rather than assuming one charge per relation.
    total_work = generous['work_used']
    limits = sorted(set(range(0, total_work, max(1, total_work // 32))) | {total_work})
    for limit in limits:
        budget = WorkBudget(limit)
        result = detect_operating_relations(observation, work_budget=budget)
        kept = [json.dumps(relation, sort_keys=True) for relation in result["relations"]]
        assert result["work_used"] == budget.used
        if result["status"] == "partial":
            assert budget.exhausted
        # Exhaustion keeps exactly a prefix of the full relations, never drops
        # already-determined ones and never invents extras.
        assert kept == full[: len(kept)]
        if kept:
            seen_non_empty = True
    assert seen_non_empty


def test_work_used_is_the_caller_budget_delta() -> None:
    units = _units("公司现无生产 VC。")
    observation = make_observation(units, target="u0")
    result, budget = run(observation)
    assert result["work_used"] == budget.used
    assert budget.used >= 1


def test_input_is_never_modified() -> None:
    units = _units("公司现无生产 VC。", "公司与谷石已建立联系。")
    observation = make_observation(
        units, target="u0", context_unit_ids=["u1"], language="zh"
    )
    before = copy.deepcopy(observation)
    run(observation)
    assert observation == before


def test_output_is_json_serializable_and_source_oriented() -> None:
    result, _, _ = run_text("公司现无生产 VC。")
    payload = json.dumps(result, ensure_ascii=False)
    assert "du4-operating-relations/1" in payload
    for relation in result["relations"]:
        assert set(relation) >= {
            "assertion_refs",
            "actor_refs",
            "object_refs",
            "predicate_refs",
            "qualifier_refs",
            "activity",
            "polarity",
            "stage",
            "attribution",
            "modality",
        }
        for field in REF_FIELDS:
            for ref in relation[field]:
                assert set(ref) == {"unit_id", "char_start", "char_end"}


def test_unknown_fields_are_never_empty_strings_or_complete() -> None:
    result, _, _ = run_text("Arbor Ltd. does not manufacture Novalon filters.")
    relation = result["relations"][0]
    assert relation["attribution"] == "unknown"
    for field in ("activity", "polarity", "stage", "attribution", "modality"):
        assert relation[field] not in ("", None)
    # Budget truncation is reported, never laundered into "complete".
    truncated, _, _ = run_text("公司现无生产 VC。", max_work_units=1)
    assert truncated["status"] == "partial"


def test_results_are_deterministic() -> None:
    text = "公司现无生产 VC（碳酸亚乙烯酯）的情况，控股股东青梧与暮石已建立联系，并希望建立业务协同与合作。"
    first, _, _ = run_text(text)
    second, _, _ = run_text(text)
    assert first == second


def test_script_and_wrap_variants_share_semantics_but_not_spans() -> None:
    variants = [
        "公司现无生产 QJ-11。",
        "公司現無生產 QJ-11。",
        "公司现无生\n产 QJ-11。",
    ]
    slices = []
    for text in variants:
        result, units, _ = run_text(text)
        assert result["relations"], (text, result)
        relation = result["relations"][0]
        assert (relation["activity"], relation["polarity"], relation["stage"]) == (
            "production",
            "negative",
            "current",
        )
        slices.append(
            units["u1"]["text"][relation["assertion_refs"][0]["char_start"] :
                               relation["assertion_refs"][0]["char_end"]]
        )
    assert len(set(slices)) == 3


def test_long_clause_binds_only_bounded_relations() -> None:
    far = "公司现无生产" + "化" * 2000 + "QJ-11"
    result, units, _ = run_text(far)
    # assertion_refs is the clause evidence span by convention; the binding
    # itself is only in the component refs, which must not reach the far noun.
    for relation in result["relations"]:
        for field in REF_FIELDS:
            if field == "assertion_refs":
                continue
            for ref_text in (
                units["u1"]["text"][ref["char_start"] : ref["char_end"]]
                for ref in relation[field]
            ):
                assert "QJ-11" not in ref_text
    near = "公司现无生产QJ-11。"
    near_result, near_units, _ = run_text(near)
    relation = near_result["relations"][0]
    assert "QJ-11" in (
        near_units["u1"]["text"][
            relation["object_refs"][0]["char_start"] : relation["object_refs"][0]["char_end"]
        ]
    )


def test_empty_target_text_is_unavailable_not_complete() -> None:
    result, _, _ = run_text("   \n ")
    assert result["status"] == "unavailable"
    assert result["relations"] == []
    assert any(
        diagnostic.get("code") == "unit_text_unavailable" for diagnostic in result["diagnostics"]
    )


def test_language_hint_is_accepted_for_any_script() -> None:
    for language in ("zh", "en", None):
        result, _, _ = run_text("公司现无生产 VC。", language=language)
        assert result["relations"], language
