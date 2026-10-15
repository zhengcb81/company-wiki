"""Phase A core: the retained real IR answer must yield three independent relations.

This is the semantic RED node: the m41 first answer is a real saved
parse/select observation (see fixtures/manifest.json for its SHA). The three
assertions — issuer production denial, quoted-shareholder contact, and the
cooperation hope — are checked separately on actor, stage, modality and exact
original-text refs. The old predicate's ``eligible=False`` result is the
baseline observation, not an expectation here.
"""

from __future__ import annotations

import copy
import json

from helpers import (
    REAL_ANSWER,
    REAL_MANIFEST,
    REAL_OBSERVATION,
    REAL_QUESTION,
    REAL_SHAREHOLDER,
    RELATIONS_SCHEMA,
    assert_refs_valid,
    load_real_units,
    make_observation,
    ref_texts,
    run,
)


def _answer_observation(units, *, with_context: bool = True):
    context = [REAL_QUESTION, REAL_SHAREHOLDER] if with_context else None
    return make_observation(units, target=REAL_ANSWER, context_unit_ids=context, language="zh")


def test_retained_fixture_matches_its_manifest() -> None:
    from hashlib import sha256

    manifest = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
    entry = next(item for item in manifest if item["path"] == "cn-ir-observation.json")
    payload = REAL_OBSERVATION.read_bytes()
    assert len(payload) == entry["bytes"]
    assert sha256(payload).hexdigest() == entry["sha256"]
    assert entry["kind"] == "retained_real_observation"


def test_real_first_answer_yields_three_independent_relations() -> None:
    """The semantic RED core: three separate assertions, not one eligible bit."""
    units = load_real_units()
    result, _ = run(_answer_observation(units))

    assert result["schema_version"] == RELATIONS_SCHEMA
    assert result["status"] == "complete"
    assert_refs_valid(units, result)
    relations = result["relations"]
    assert len(relations) == 3, result
    first, second, third = relations

    # 1) issuer: 公司现无生产 VC（碳酸亚乙烯酯） — current production denial.
    assert first["activity"] == "production"
    assert first["polarity"] == "negative"
    assert first["stage"] == "current"
    assert first["attribution"] == "issuer"
    assert first["modality"] == "actual"
    assert ref_texts(units, first, "actor_refs") == ["公司"]
    assert ref_texts(units, first, "object_refs") == ["VC（碳酸亚乙烯酯）"]
    assert ref_texts(units, first, "predicate_refs") == ["生产"]
    assert ref_texts(units, first, "qualifier_refs") == ["现无"]
    assert ref_texts(units, first, "assertion_refs") == [
        "公司现无生产 VC（碳酸亚乙烯酯）的情况"
    ]

    # 2) quoted related party: 中国节能与宁德时代已经建立了联系.
    assert second["activity"] == "business_relationship"
    assert second["polarity"] == "positive"
    assert second["stage"] == "contact_established"
    assert second["attribution"] == "quoted_related_party"
    assert second["modality"] == "actual"
    assert ref_texts(units, second, "actor_refs") == ["中国节能", "宁德时代"]
    assert ref_texts(units, second, "object_refs") == []
    assert ref_texts(units, second, "predicate_refs") == ["建立了联系"]
    assert ref_texts(units, second, "qualifier_refs") == ["已经"]
    assert ref_texts(units, second, "assertion_refs") == [
        "中国节能与宁德时代已经建立了联系"
    ]
    # The contact must not be re-attributed to the issuer.
    assert "公司" not in ref_texts(units, second, "actor_refs")

    # 3) same attributed actors: 并希望建立业务协同与合作 — aspiration only.
    assert third["activity"] == "business_relationship"
    assert third["stage"] == "intended_cooperation"
    assert third["modality"] == "aspirational"
    assert third["attribution"] == "quoted_related_party"
    assert ref_texts(units, third, "actor_refs") == ["中国节能", "宁德时代"]
    assert ref_texts(units, third, "object_refs") == ["业务协同与合作"]
    assert ref_texts(units, third, "predicate_refs") == ["建立"]
    assert ref_texts(units, third, "qualifier_refs") == ["希望"]
    # The assertion ref keeps the native line wrap of the original unit.
    assert ref_texts(units, third, "assertion_refs") == ["并希望建立\n业务协同与合作"]

    # Fact scope: hope is not a contract, order, shipment or revenue.
    for relation in relations:
        assert relation["activity"] != "shipment"
    assert third["modality"] != "actual"
    assert second["stage"] != "current"


def test_real_question_procurement_stays_question_context() -> None:
    units = load_real_units()
    observation = make_observation(units, target=REAL_QUESTION, language="zh")
    result, _ = run(observation)
    assert_refs_valid(units, result)
    assert result["relations"] == [], result
    # The 采购 premise must not surface as any realized relation either way.
    assert result["status"] in {"complete", "partial"}


def test_real_shareholder_increase_is_not_an_operating_fact() -> None:
    units = load_real_units()
    observation = make_observation(units, target=REAL_SHAREHOLDER, language="zh")
    result, _ = run(observation)
    assert_refs_valid(units, result)
    assert result["relations"] == [], result


def test_real_refs_are_original_offsets_not_normalized_view() -> None:
    units = load_real_units()
    result, _ = run(_answer_observation(units))
    text = units[REAL_ANSWER]["text"]
    # Offsets index the original unit, including its embedded newlines.
    for relation in result["relations"]:
        for field in ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs"):
            for ref in relation[field]:
                assert ref["unit_id"] == REAL_ANSWER
                sliced = text[ref["char_start"] : ref["char_end"]]
                assert sliced
    wrapped = [ref for relation in result["relations"] for ref in relation["assertion_refs"]]
    assert any("\n" in text[ref["char_start"] : ref["char_end"]] for ref in wrapped)


def test_real_relations_do_not_depend_on_context_units() -> None:
    units = load_real_units()
    with_context, _ = run(_answer_observation(units))
    without_context, _ = run(_answer_observation(units, with_context=False))
    assert with_context["relations"] == without_context["relations"]


def test_real_observation_input_is_unchanged() -> None:
    units = load_real_units()
    observation = _answer_observation(units)
    before = copy.deepcopy(observation)
    run(observation)
    assert observation == before
