"""Phase A generalization: 32 reference statements, 16 extended counterexamples
and fresh-name holdouts.

The 32 rows are the reference design's synthetic specification list; the
expected boolean means "at least one concrete operating relation is bound"
(or none at all). Richer stage/modality/attribution checks live in the
targeted and extended cases below. These are specifications, not a market
recall score; the real saved paragraph is reported separately in
test_a_real_observation.py.
"""

from __future__ import annotations

import pytest

from helpers import ref_texts, run_text, signature

# case_id, text, specified relation presence (reference design spec).
SYNTHETIC_CASES = [
    ("cn_current_production_denial", "公司现无生产 QJ-11 的情况。", True),
    ("cn_wrapped_current_denial", "本公司现无生\n产椿石添加剂的情况。", True),
    ("cn_traditional_denial", "本公司目前並未生產梧石添加劑。", True),
    ("en_current_manufacture_denial", "We do not currently manufacture Novalon.", True),
    ("en_named_actor_denial", "Arbor Ltd. does not manufacture Novalon filters.", True),
    ("cn_no_business_involvement", "公司目前未涉及星纤存储业务。", True),
    ("en_no_business_involvement", "The company is not involved in storage services.", True),
    ("cn_not_commercialized", "青梧设备仍在研发阶段，尚未商业化。", True),
    (
        "en_not_commercialized",
        "The platform remains a research prototype and is not available for commercial sale.",
        True,
    ),
    ("cn_suspend_production", "子公司因客户验证未通过暂停滤芯生产。", True),
    (
        "en_suspend_production",
        "Unrelated supplier Dusk suspended production of its filters after unsuccessful validation.",
        True,
    ),
    ("cn_parent_pending_qualification", "母公司青梧尚未取得客户对其膜产品的认证。", True),
    (
        "en_parent_pending_qualification",
        "Our parent Rowan has not obtained customer qualification for its membrane.",
        True,
    ),
    (
        "en_restricted_approval",
        "Third-party Mica is approved only for pilot use; production qualification remains pending.",
        True,
    ),
    ("cn_contact_intention", "公司与谷石就涂覆设备进行了技术接洽，并希望开展合作。", True),
    (
        "en_contact_intention",
        "We held technical discussions with Vale about coating equipment and hope to cooperate.",
        True,
    ),
    (
        "cn_parent_contact_intention",
        "控股股东青梧与暮石已建立联系，并希望开展涂覆设备业务合作。",
        True,
    ),
    (
        "en_parent_contact_intention",
        "Our controlling shareholder Rowan has contacted Vale about coating equipment and hopes to cooperate.",
        True,
    ),
    (
        "en_concrete_conditional_plan",
        "We plan to commercialize Product N next year if customer qualification is obtained.",
        True,
    ),
    ("cn_positive_control", "公司新产品完成客户验证，第四季度开始批量交付。", True),
    ("cn_definition", "商业化是指产品形成销售的过程。", False),
    (
        "en_owned_glossary",
        "Our glossary: product qualification is defined as approval before commercialization.",
        False,
    ),
    ("cn_admin_negative", "本次调研未收到有关平台商业化的股东提问。", False),
    (
        "en_admin_negative",
        "No shareholder questions were received about commercializing the platform.",
        False,
    ),
    ("cn_financial_total", "公司产品分部包括营业收入10亿元、利润2亿元。", False),
    (
        "en_financial_total",
        "Our products segment comprises revenue of $100 million and profit of $20 million.",
        False,
    ),
    ("cn_bare_nouns", "产品认证与商业化。", False),
    ("en_bare_nouns", "Product qualification and commercialization.", False),
    ("cn_generic_hope", "我们期待产品商业化与客户导入一切顺利。", False),
    (
        "en_generic_hope",
        "We expect product commercialization and customer adoption to go well.",
        False,
    ),
    ("cn_polite_cooperation", "感谢您的关注，希望未来保持沟通与合作。", False),
    (
        "en_polite_cooperation",
        "Thank you for your interest; we look forward to continued communication and cooperation.",
        False,
    ),
]


@pytest.mark.parametrize(
    ("case_id", "text", "expected"), SYNTHETIC_CASES, ids=[row[0] for row in SYNTHETIC_CASES]
)
def test_synthetic_relation_presence(case_id: str, text: str, expected: bool) -> None:
    result, units, _ = run_text(text)
    present = bool(result["relations"])
    assert present is expected, (case_id, result)
    if expected:
        assert result["status"] == "complete"


# ---------------------------------------------------------------- targeted state checks


def test_current_production_denial_shape() -> None:
    result, units, _ = run_text("公司现无生产 QJ-11 的情况。")
    relation = result["relations"][0]
    assert relation["activity"] == "production"
    assert relation["polarity"] == "negative"
    assert relation["stage"] == "current"
    assert relation["attribution"] == "issuer"
    assert relation["modality"] == "actual"
    assert ref_texts(units, relation, "object_refs") == ["QJ-11"]
    assert ref_texts(units, relation, "qualifier_refs") == ["现无"]


def test_wrapped_denial_ref_is_original_span() -> None:
    result, units, _ = run_text("本公司现无生\n产椿石添加剂的情况。")
    relation = result["relations"][0]
    assert ref_texts(units, relation, "assertion_refs") == [
        "本公司现无生\n产椿石添加剂的情况"
    ]
    assert ref_texts(units, relation, "object_refs") == ["椿石添加剂"]


def test_traditional_denial_refs_are_original_characters() -> None:
    result, units, _ = run_text("本公司目前並未生產梧石添加劑。")
    relation = result["relations"][0]
    assert relation["polarity"] == "negative"
    assert relation["stage"] == "current"
    assert ref_texts(units, relation, "predicate_refs") == ["生產"]
    assert ref_texts(units, relation, "object_refs") == ["梧石添加劑"]
    assert ref_texts(units, relation, "qualifier_refs") == ["目前並未"]


def test_en_manufacture_denial_shape() -> None:
    result, units, _ = run_text("We do not currently manufacture Novalon.")
    relation = result["relations"][0]
    assert relation["activity"] == "production"
    assert relation["polarity"] == "negative"
    assert relation["stage"] == "current"
    assert ref_texts(units, relation, "object_refs") == ["Novalon"]
    assert ref_texts(units, relation, "predicate_refs") == ["manufacture"]
    assert ref_texts(units, relation, "qualifier_refs") == ["do not currently"]


def test_suspended_production_keeps_suspended_stage() -> None:
    result, units, _ = run_text("子公司因客户验证未通过暂停滤芯生产。")
    stages = {relation["stage"] for relation in result["relations"]}
    assert "suspended" in stages
    production = [
        relation for relation in result["relations"] if relation["activity"] == "production"
    ]
    assert production and production[0]["stage"] == "suspended"
    assert production[0]["polarity"] == "negative"


def test_not_yet_commercialization_borrows_topic_object() -> None:
    result, units, _ = run_text("青梧设备仍在研发阶段，尚未商业化。")
    relation = result["relations"][0]
    assert relation["activity"] == "commercialization"
    assert relation["polarity"] == "negative"
    assert relation["stage"] == "not_yet"
    assert ref_texts(units, relation, "object_refs") == ["青梧设备"]
    assert ref_texts(units, relation, "qualifier_refs") == ["尚未"]


def test_parent_pending_qualification_is_related_party_not_issuer() -> None:
    result, units, _ = run_text("母公司青梧尚未取得客户对其膜产品的认证。")
    relation = result["relations"][0]
    assert relation["activity"] == "qualification"
    assert relation["polarity"] == "negative"
    assert relation["stage"] == "not_yet"
    assert relation["attribution"] == "quoted_related_party"
    assert ref_texts(units, relation, "object_refs") == ["膜产品"]


def test_pilot_only_approval_is_not_full_qualification() -> None:
    result, units, _ = run_text(
        "Third-party Mica is approved only for pilot use; production qualification remains pending."
    )
    for relation in result["relations"]:
        assert not (
            relation["activity"] == "qualification"
            and relation["polarity"] == "positive"
            and relation["stage"] == "current"
        )
    stages = {relation["stage"] for relation in result["relations"]}
    assert "conditional" in stages
    assert "not_yet" in stages


def test_contact_and_hope_are_distinct_relations() -> None:
    result, _, _ = run_text("公司与谷石就涂覆设备进行了技术接洽，并希望开展合作。")
    stages = [relation["stage"] for relation in result["relations"]]
    assert "contact_established" in stages
    assert "intended_cooperation" in stages
    for relation in result["relations"]:
        assert relation["modality"] != "actual" or relation["stage"] == "contact_established"


def test_conditional_plan_stays_conditional() -> None:
    result, _, _ = run_text(
        "We plan to commercialize Product N next year if customer qualification is obtained."
    )
    commercial = [
        relation for relation in result["relations"] if relation["activity"] == "commercialization"
    ]
    assert commercial
    for relation in commercial:
        assert relation["modality"] in {"planned", "conditional"}
        assert relation["modality"] != "actual"
        assert relation["stage"] in {"planned", "conditional"}


# ---------------------------------------------------------------- extended counterexamples


def test_ext_double_negation_is_uncertain_not_inverted() -> None:
    result, _, _ = run_text("并非没有生产 QJ-11。")
    assert len(result["relations"]) == 1, result
    relation = result["relations"][0]
    assert relation["activity"] == "production"
    assert relation["modality"] == "uncertain"
    assert relation["polarity"] == "unknown"


def test_ext_not_cancelled_proves_nothing_and_cancelled_differs() -> None:
    kept, _, _ = run_text("该项目未取消。")
    assert kept["relations"] == [], kept
    started, _, _ = run_text("该项目已投产。")
    assert started["relations"], started
    assert started["relations"][0]["polarity"] == "positive"


def test_ext_not_a_bottleneck_is_not_production_absence() -> None:
    bottleneck, _, _ = run_text("该产线不是生产瓶颈。")
    assert bottleneck["relations"] == [], bottleneck
    halted, _, _ = run_text("公司暂停该产线生产。")
    relation = halted["relations"][0]
    assert relation["activity"] == "production"
    assert relation["stage"] == "suspended"
    assert relation["polarity"] == "negative"


def test_ext_pilot_only_use_is_not_certification_success() -> None:
    result, units, _ = run_text("该产线非批量生产，仅用于试用。")
    for relation in result["relations"]:
        assert not (
            relation["activity"] == "qualification"
            and relation["polarity"] == "positive"
            and relation["modality"] == "actual"
        )
    assert result["relations"], result
    relation = result["relations"][0]
    assert relation["polarity"] == "negative"
    qualifiers = ref_texts(units, relation, "qualifier_refs")
    assert "非批量" in qualifiers
    assert "仅用于试用" in qualifiers


def test_ext_admin_notification_negation_is_not_uncommercialized() -> None:
    result, _, _ = run_text("公司未收到有关产品商业化的通知。")
    assert result["relations"] == [], result


def test_ext_actor_kinds_never_swap() -> None:
    cases = {
        "issuer": ("公司暂停生产 VC。", "issuer", "公司"),
        "shareholder": ("控股股东青梧暂停生产 VC。", "quoted_related_party", "控股股东青梧"),
        "subsidiary": ("子公司青梧暂停生产 VC。", "quoted_related_party", "子公司青梧"),
        "counterparty": ("供应商暮石暂停生产 VC。", "other", "供应商暮石"),
    }
    seen = {}
    for label, (text, expected_attribution, expected_actor) in cases.items():
        result, units, _ = run_text(text)
        assert result["relations"], (label, result)
        relation = result["relations"][0]
        assert relation["attribution"] == expected_attribution, (label, relation)
        assert ref_texts(units, relation, "actor_refs") == [expected_actor], (label, relation)
        seen[label] = relation["attribution"]
    assert seen["issuer"] != seen["shareholder"]
    assert seen["issuer"] != seen["counterparty"]
    assert seen["counterparty"] != seen["subsidiary"]


def test_ext_cross_parent_context_never_chains() -> None:
    text = "青梧与暮石已建立联系。"
    cue = "公司控股股东青梧信息。"
    chained, units, _ = run_text(text, context=[(cue, "p9")])
    assert chained["relations"], chained
    assert chained["relations"][0]["attribution"] == "unknown"
    assert any(
        diagnostic.get("code") == "context_parent_mismatch"
        for diagnostic in chained["diagnostics"]
    )
    same_parent, _, _ = run_text(text, context=[(cue, "p1")])
    assert same_parent["relations"][0]["attribution"] == "quoted_related_party"
    assert same_parent["status"] == "complete"


def test_ext_question_premise_is_not_a_disclosed_relation() -> None:
    result, _, _ = run_text(
        "Could you confirm whether we can secure volume procurement of VC?",
        role="investor_question",
    )
    assert result["relations"] == [], result


def test_ext_financial_composition_borrows_no_product_predicate() -> None:
    result, _, _ = run_text("产品分部由营业收入和利润构成。")
    assert result["relations"] == [], result


def test_ext_production_cause_survives_financial_words() -> None:
    result, _, _ = run_text("公司因滤芯产线停产导致营收下降。")
    assert result["relations"], result
    relation = result["relations"][0]
    assert relation["activity"] == "production"
    assert relation["stage"] == "discontinued"
    assert relation["polarity"] == "negative"


def test_ext_courtesy_plus_real_denial_stays_useful() -> None:
    result, _, _ = run_text("感谢您对公司的关注，公司现无生产 VC。")
    assert len(result["relations"]) == 1, result
    assert result["relations"][0]["activity"] == "production"


def test_ext_vision_statement_is_not_an_operating_assertion() -> None:
    result, _, _ = run_text("公司致力于成为行业领先的平台型企业。")
    assert result["relations"] == [], result


def test_ext_bare_negation_and_declines_say_nothing() -> None:
    for text in ("没有。", "不便评论。", "We have nothing further to disclose."):
        result, _, _ = run_text(text)
        assert result["relations"] == [], (text, result)


def test_ext_undeterminable_scope_is_uncertain() -> None:
    result, _, _ = run_text("公司目前无法确定是否涉及该储能业务。")
    assert len(result["relations"]) == 1, result
    relation = result["relations"][0]
    assert relation["activity"] == "business_scope"
    assert relation["modality"] == "uncertain"
    assert relation["polarity"] == "unknown"


def test_ext_relationship_stages_are_five_distinct_states() -> None:
    expectations = {
        "公司与谷石已建立联系。": ("business_relationship", "contact_established", "actual"),
        "公司计划与谷石开展业务合作。": ("business_relationship", "planned", "planned"),
        "公司希望与谷石开展业务协同与合作。": (
            "business_relationship",
            "intended_cooperation",
            "aspirational",
        ),
        "公司与谷石已签署采购合同。": ("business_relationship", "current", "actual"),
        "公司已向谷石发货涂覆设备。": ("shipment", "current", "actual"),
    }
    seen = set()
    for text, expected in expectations.items():
        result, _, _ = run_text(text)
        assert result["relations"], (text, result)
        got = signature(result["relations"][0])
        assert got == expected, (text, got)
        seen.add(got)
    assert len(seen) == len(expectations)


def test_ext_body_relations_are_role_independent() -> None:
    text = "公司现无生产 VC。"
    as_management, units_management, _ = run_text(text, role="management")
    as_question, units_question, _ = run_text(text, role="investor_question")
    assert as_management["relations"] == as_question["relations"]
    assert units_management["u1"]["role"] == "management"
    assert units_question["u1"]["role"] == "investor_question"


# ---------------------------------------------------------------- holdout (fresh names)

HOLDOUT_CASES = [
    (
        "holdout_cn_fresh_company_product",
        "寰宇新材目前没有生产 ZX-9 添加剂。",
        ("production", "negative", "current"),
        ["ZX-9 添加剂"],
    ),
    (
        "holdout_en_fresh_names",
        "Halcyon Meridian does not currently produce Tessellate resin.",
        ("production", "negative", "current"),
        ["Tessellate resin"],
    ),
    (
        "holdout_traditional_fresh_names",
        "臺廠光宇精密目前尚未量產氫能模組。",
        ("production", "negative", "not_yet"),
        ["氫能模組"],
    ),
    (
        "holdout_wrapped_fresh_names",
        "星环新材现无生\n产 TL-3溶剂的情况。",
        ("production", "negative", "current"),
        ["TL-3溶剂"],
    ),
]


@pytest.mark.parametrize(
    ("case_id", "text", "expected", "objects"),
    HOLDOUT_CASES,
    ids=[row[0] for row in HOLDOUT_CASES],
)
def test_holdout_unseen_names(case_id, text, expected, objects) -> None:
    result, units, _ = run_text(text)
    assert result["relations"], (case_id, result)
    relation = result["relations"][0]
    assert (relation["activity"], relation["polarity"], relation["stage"]) == expected
    assert ref_texts(units, relation, "object_refs") == objects
    assert result["status"] == "complete"
