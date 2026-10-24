"""Original statement/value boundaries, independent of issuer or gold vocabulary."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_routing import DocumentRoute
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def fixture(texts, *, same_block=True, language="zh", heading=False):
    source = source_id_for_sha256("e" * 64)
    original = "\n".join(texts)
    units, wires, start = [], [], 0
    for index, text in enumerate(texts):
        block = 0 if same_block else index
        box = [90, 100 + 20 * block, 550, 112 + 20 * block]
        layout = {"bbox": box, "page_width": 600, "page_height": 800,
                  "coordinate_frame": "dict", "rotation": 0, "column": 0}
        fonts = [{"char_start": 0, "char_end": len(text), "font_size": 12,
                  "font_weight": "regular", "coordinate_frame": "dict",
                  "source": "pdf_native_single_textpage", "char_alignment": "exact"}]
        metadata = {"pdf_block": block, "block_sha256": sha256(original.encode()).hexdigest(),
                    "block_char_start": start if same_block else 0,
                    "block_char_end": (start if same_block else 0) + len(text),
                    "reading_layout": {"layout": layout, "upstream_hints": {"font_runs": fonts}}}
        unit = _make_unit(source_id=source, parser_version="1.0.0",
                          coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
                          raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
                          language=language, metadata=metadata)
        units.append(unit)
        wires.append({"unit_id": unit.unit_id, "ordinal": index, "page": 1, "text": text,
                      "kind": "heading" if heading and index == 0 else "paragraph",
                      "role": "company_filing", "language": language, "layout": layout,
                      "hints": {"source_id": source, "font_runs": fonts}})
        start += len(text) + 1
    ids = [unit.unit_id for unit in units]
    body = ids[1:] if heading else ids
    pipeline = {"observation": {"units": wires},
                "reading_plan": {"unit_profiles": {uid: {"reading_profile_key": "root",
                                                         "section_role": "business", "priority": 2}
                                                   for uid in ids}},
                "structure": {"sections": [{"section_id": "business", "parent_id": None,
                                              "heading_unit_ids": ids[:1] if heading else [],
                                              "body_unit_ids": body}]},
                "packages": {"packages": [{"package_id": "body", "kind": "background",
                                             "member_unit_ids": body, "anchor_unit_ids": body[:1],
                                             "required_context_unit_ids": body[:1]}]}}
    return DocumentStructure(source, "e" * 64, language, tuple(units), page_count=1,
                             pages_read=1, mime_type="application/pdf"), pipeline


def select(parsed, candidates, metadata, *, limit=96):
    return finalize_selection(parsed, DocumentRoute("semi_annual_report", limit, False), candidates,
                              group_ids={}, heading_pattern=reading._NEVER_HEADING,
                              dropped_financial_count=0, budget_policy=reading.READING_BUDGET_POLICY,
                              reading_metadata=metadata, max_chars=48000)


@pytest.mark.parametrize("language,texts", [
    ("zh", ["公司已交付专用设备至客户开展生产验证。", "公司新增制造基地已经投入运行。"]),
    ("en", ["Our company delivered equipment to customers for production qualification.",
            "Our company opened a new manufacturing facility for customers."]),
])
def test_independent_complete_statements_are_not_one_atomic_business_claim(language, texts):
    parsed, pipeline = fixture(texts, language=language)
    before = deepcopy(pipeline)
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    ids = [unit.unit_id for unit in parsed.units]
    assert complete and not withheld
    assert [package["member_unit_ids"] for package in packages] == [[uid] for uid in ids]
    assert all(not metadata[uid]["context_only"] for uid in ids)
    assert all(metadata[uid]["required"] == () for uid in ids)
    assert len(select(parsed, candidates, metadata, limit=1).evidence_spans) == 1
    assert pipeline == before
    assert [unit.raw_text for unit in parsed.units] == texts


@pytest.mark.parametrize("qualifier", [
    "但公司尚未完成产线认证，不代表已经形成批量销售。",
    "该设备仍需完成认证，预计明年进入量产。",
    "报告期内样机继续验证，并获得重复订单。",
    "下半年将根据客户反馈安排开发，预计随后进行认证。",
])
def test_sentence_terminator_does_not_drop_reference_negation_or_forward_condition(qualifier):
    parsed, pipeline = fixture(["公司已交付设备样机至客户开展生产验证。", qualifier])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    ids = {unit.unit_id for unit in parsed.units}
    assert complete and not withheld and len(packages) == 1
    assert set(packages[0]["member_unit_ids"]) == ids
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    full = select(parsed, candidates, metadata, limit=2)
    assert [span.raw_text for span in full.evidence_spans] == [unit.raw_text for unit in parsed.units]


@pytest.mark.parametrize("qualification", [
    "公司尚未完成产线认证，不代表已经形成批量销售。",
    "公司计划在下一期开展客户认证，量产仍取决于认证结果。",
])
def test_preceding_qualification_cannot_be_detached_from_later_positive_statement(qualification):
    parsed, pipeline = fixture([qualification, "公司已交付专用设备至客户开展生产验证。"])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(packages) == 1
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    assert len(select(parsed, candidates, metadata, limit=2).evidence_spans) == 2


@pytest.mark.parametrize("order", [("table", "description"), ("description", "table")])
def test_weaker_package_does_not_overwrite_source_owned_table_fact_value(order):
    parsed, pipeline = fixture(["Device A | 15", "Product shipments | 2026 | thousand units"], same_block=False,
                               language="en")
    uid, header = [unit.unit_id for unit in parsed.units]
    packages = {
        "table": {"package_id": "operating-row", "kind": "operating_table",
                  "member_unit_ids": [uid, header], "anchor_unit_ids": [uid],
                  "required_context_unit_ids": [header]},
        "description": {"package_id": "description", "kind": "project",
                        "member_unit_ids": [uid], "anchor_unit_ids": [uid],
                        "required_context_unit_ids": []},
    }
    pipeline["packages"]["packages"] = [packages[key] for key in order]
    candidates, metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    assert metadata[uid]["value_band"] == "meaningful_fact"
    assert metadata[uid]["topics"] == (), "a weaker section description cannot claim factual novelty"
    assert not metadata[uid]["context_only"]
    assert metadata[uid]["required"] == (header,)
    full = select(parsed, candidates, metadata, limit=2)
    assert len(full.evidence_spans) == 2
    assert len({span.span_id for span in full.evidence_spans}) == 2


def test_real_wrapped_statement_is_still_complete_and_costs_every_original_fragment():
    parsed, pipeline = fixture(["报告期内，公司将开展客户生产验", "证，并保留未完成认证的条件。"])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(packages) == 1
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    full = select(parsed, candidates, metadata, limit=2)
    assert [span.raw_text for span in full.evidence_spans] == [unit.raw_text for unit in parsed.units]
    assert [span.coordinates for span in full.evidence_spans] == [unit.coordinates for unit in parsed.units]
    assert reading.READING_BUDGET_POLICY == "reading_plan/3"
    assert reading.MAX_READING_CHARS == 48000


@pytest.mark.parametrize("language,texts,expected", [
    ("mixed", ["公司产品将通", "过合作研", "发提高效率。"], "公司产品将通过合作研发提高效率。"),
    ("mixed", ["公司已交付设备。", "但尚未完成验", "证，预计明年量产。"],
        "公司已交付设备。但尚未完成验证，预计明年量产。"),
    ("zh", ["Our company introduced owner", "ship services for customers."],
        "Our company introduced owner ship services for customers."),
    ("mixed", ["Our company introduced cloud", "services for customers."],
        "Our company introduced cloud services for customers."),
    ("zh", ["公司已交付产能为12", "3万件的设备，额定电压12", "V，仍需客户认证。"],
        "公司已交付产能为12 3万件的设备，额定电压12 V，仍需客户认证。"),
])
def test_linguistic_boundary_depends_on_actual_characters_not_declared_language(language, texts, expected):
    parsed, pipeline = fixture(texts, language=language)
    before = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert expected in seen
    assert len(packages) == 1 and packages[0]["kind"] == "native_continuity"
    assert packages[0]["member_unit_ids"] == [unit.unit_id for unit in parsed.units]
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == before


def test_wrong_zh_label_cannot_create_eligible_english_product_word():
    texts = ["Our company launched prod", "ucts."]
    parsed, pipeline = fixture(texts, language="zh")
    assert reading.detect_reading_business_fact("Our company launched products.").eligible
    assert not reading.detect_reading_business_fact("Our company launched prod ucts.").eligible
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(
        parsed, pipeline, reading.detect_reading_business_fact)
    assert all(package["kind"] != "native_continuity" for package in packages)
    assert [unit.raw_text for unit in parsed.units] == texts


def test_statement_split_and_window_fact_share_the_same_cjk_boundary_rule():
    texts = ["公司已交付专用设备至客户开展生产验", "证。",
             "公司新增制造基地已经投入运", "行。"]
    parsed, pipeline = fixture(texts, language="mixed")
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert [package["member_unit_ids"] for package in packages] == [
        [unit.unit_id for unit in parsed.units[:2]], [unit.unit_id for unit in parsed.units[2:]]]
    assert "公司已交付专用设备至客户开展生产验证。" in seen
    assert "公司新增制造基地已经投入运行。" in seen
    assert not any("验 证" in text or "运 行" in text for text in seen)


def test_different_native_sources_never_share_a_linguistic_view_even_with_two_language_labels():
    parsed, pipeline = fixture(["公司产品将通", "过合作研发提高效率。"], language="mixed")
    last = parsed.units[-1]
    source = source_id_for_sha256("f" * 64)
    changed = _make_unit(source_id=source, parser_version=last.parser_version,
        coordinates=last.coordinates, raw_text=last.raw_text, unit_kind=last.unit_kind,
        source_role=last.source_role, language="zh", metadata=last.metadata)
    parsed = replace(parsed, units=(parsed.units[0], changed))
    old = last.unit_id
    pipeline["observation"]["units"][-1].update(unit_id=changed.unit_id, language="zh")
    pipeline["observation"]["units"][-1]["hints"]["source_id"] = source
    profiles = pipeline["reading_plan"]["unit_profiles"]
    profiles[changed.unit_id] = profiles.pop(old)
    pipeline["structure"]["sections"][0]["body_unit_ids"][-1] = changed.unit_id
    pipeline["packages"]["packages"][0]["member_unit_ids"][-1] = changed.unit_id
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert "公司产品将通过合作研发提高效率。" not in seen
    assert all(package["kind"] != "native_continuity" for package in packages)


# W08 source quantity/purpose regressions use the real native source owner.
@pytest.mark.parametrize("text", [
    "研发制造服务本期实现收入126.4亿元，同比增长18.6%；本期新增项目560个，期末项目总数2480个，其中临床后期项目64个。",
    "截至报告期末，公司反应釜总容积达到2400kL。",
    "公司的专门服务业务本期客户数为172家，分子项目数量为2390个。",
    "技术服务业务本期实现收入人民币26.5亿元，同比增长16.2%。",
])
def test_w08_operating_quantity_is_not_merely_a_section_description(text):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    parsed, pipeline = source_fixture([(text,)])
    before = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    assert len(candidates) == 1
    assert metadata[candidates[0].unit.unit_id]["value_band"] == "meaningful_fact"
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == before


@pytest.mark.parametrize("reverse", [False, True])
def test_w08_accounting_template_cannot_win_an_equal_priority_one_span_budget(reverse):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture, selected
    operating = "服务业务本期客户数为172家，项目总数为2390个。"
    accounting = "当金融负债的现时义务全部或部分已经解除时，公司终止确认该金融负债或已解除义务部分。"
    texts = [operating, accounting]
    if reverse:
        texts.reverse()
    parsed, pipeline = source_fixture([(text,) for text in texts])
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    result = selected(parsed, pipeline, candidates, metadata, limit=1)
    assert complete and not withheld
    assert [span.raw_text for span in result.evidence_spans] == [operating]
    assert reading.MAX_READING_CHARS == 48000 and reading.READING_BUDGET_POLICY == "reading_plan/3"


def test_w08_accounting_derecognition_is_read_no_business_without_hiding_real_note_events():
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    accounting = "当金融负债的现时义务全部或部分已经解除时，公司终止确认该金融负债或已解除义务部分。"
    parsed, pipeline = source_fixture([(accounting,)])
    candidates, _, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and not candidates and not packages
    real = "公司新增生产线已经投入运行，但仍需完成客户认证。"
    parsed, pipeline = source_fixture([(accounting,), (real,)])
    candidates, _, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    assert [candidate.unit.raw_text for candidate in candidates] == [real]


@pytest.mark.parametrize("text", [
    "客户贷款账面余额为172万元。",
    "项目账面价值为2390万元。",
    "客户数是一项定义，示例数字为172。",
    "客户服务中心项目总投资为300万元。",
    "The customer loan carrying amount was 172 million.",
    "A glossary mentions customers. Total assets were 172 million.",
])
def test_w08_unrelated_financial_values_and_definition_numbers_are_not_operating_stock(text):
    fact = reading.detect_reading_business_fact(text)
    assert not fact.eligible


def test_w08_imports_resolve_to_the_owned_source_tree():
    from pathlib import Path
    from company_wiki.source_catalog import narrative_business_policy, narrative_source_purpose
    root = Path(__file__).resolve().parents[3] / "src"
    assert all(Path(module.__file__).resolve().is_relative_to(root)
               for module in (reading, narrative_business_policy, narrative_source_purpose))


@pytest.mark.parametrize("text", [
    "项目1在本节作介绍，具体内容另述。",
    "客户2号账户的余额为172万元。",
    "項目8在本節作介紹，具體內容另述。",
    "客戶3號帳戶的餘額為2390萬元。",
    "Project 7 is discussed in another section.",
    "Customer 6 account balance was USD 2390 million.",
    "客户数量为172万元。",
    "项目2026年度介绍将在下文继续。",
])
def test_w08_metric_identifiers_and_financial_amounts_are_not_operating_counts(text):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    fact = reading.detect_reading_business_fact(text)
    parsed, pipeline = source_fixture([(text,)])
    candidates, metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert not fact.eligible and not fact.financial_exempt
    assert complete and not withheld
    assert all(metadata[candidate.unit.unit_id]["value_band"] != "meaningful_fact"
               for candidate in candidates)


@pytest.mark.parametrize("text", [
    "期末项目总数2480个，其中临床后期项目64个。",
    "本期新增项目560个。",
    "公司的客户数为172家。",
    "本期客戶數量達到2390家。",
    "截至期末反应釜总容积达到2400kL。",
    "Our customers numbered 172 during the year.",
    "Our projects totaled 560 at year end.",
    "Our active customers were 2390 at year end.",
])
def test_w08_source_quantity_requires_a_measurement_predicate_or_count_unit(text):
    fact = reading.detect_reading_business_fact(text)
    assert fact.eligible and "operating_quantity" in fact.reasons
    assert fact.purpose == "operating_metric"


@pytest.mark.parametrize("text", [
    "Our Diagnostics services revenue increased to USD 26.5 million during the year.",
    "Our Technical services revenue declined to USD 9 million during the year.",
    "New product revenue exceeds 30%.",
    "New product revenue represented 35% of segment revenue.",
    "公司的新产品收入占比提升至超30%。",
    "本公司新產品收入佔比達到35%。",
    "本公司技術服務業務收入增至人民幣26.5億元。",
])
def test_w08_absolute_business_revenue_and_share_are_native_facts_without_an_event_prefix(text):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    fact = reading.detect_reading_business_fact(text)
    parsed, pipeline = source_fixture([(text,)])
    before = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    candidates, metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert fact.eligible and "business_revenue_measure" in fact.reasons
    assert fact.purpose == "operating_metric"
    assert complete and not withheld and len(candidates) == 1
    assert metadata[candidates[0].unit.unit_id]["value_band"] == "meaningful_fact"
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == before


@pytest.mark.parametrize("text", [
    "Total revenue increased to USD 26.5 million during the year.",
    "Our product philosophy is important, revenue was USD 26.5 million.",
    "Our services revenue grew 15% driven by happy customers and product philosophy.",
    "New product revenue is expected to exceed 30% if customer qualification succeeds.",
])
def test_w08_unbound_revenue_growth_and_unrealized_share_are_not_observed_amounts(text):
    fact = reading.detect_reading_business_fact(text)
    assert "business_revenue_measure" not in fact.reasons


@pytest.mark.parametrize("text", [
    "Our product philosophy is important and revenue was USD 26.5 million.",
    "Our services are valued by customers and revenue was USD 26.5 million.",
    "产品在本节介绍，另一个客户的收入达到26.5亿元。",
    "公司产品的理念很重要而收入达到26.5亿元。",
    "Our customer service phone number is 172.",
])
def test_w08_measurement_subject_cannot_borrow_a_different_clause_predicate(text):
    fact = reading.detect_reading_business_fact(text)
    assert "business_revenue_measure" not in fact.reasons
    assert "operating_quantity" not in fact.reasons


@pytest.mark.parametrize("text", [
    "Our services revenue increased due to project 7 described elsewhere.",
    "Our services revenue increased due to customer 6 account balance.",
    "公司服务收入增长主要由项目1的介绍带动。",
])
def test_w08_causal_driver_does_not_bypass_quantity_identifier_rejection(text):
    fact = reading.detect_reading_business_fact(text)
    assert "operating_causal_driver" not in fact.reasons
    assert "product_operating_driver" not in fact.reasons


@pytest.mark.parametrize("text", [
    "Our service revenue grew with 62 million paid subscribers.",
    "Our services revenue increased due to 172 new customers.",
    "Our services revenue increased due to projects totaling 560 at year end.",
])
def test_w08_true_quantity_driver_and_stock_share_measurement_semantics(text):
    fact = reading.detect_reading_business_fact(text)
    assert fact.eligible
    assert {"operating_quantity", "operating_causal_driver", "product_operating_driver"} & set(fact.reasons)


@pytest.mark.parametrize("text", [
    "Our services revenue increased due to project 7 growth described elsewhere.",
    "Our services revenue increased due to an increase in customer 6 account balance.",
    "公司服务收入增长主要由项目1的介绍增加带动。",
    "Our services revenue increased due to higher customer loan balances.",
    "Our services revenue increased due to customer account balance growth.",
    "公司服务收入增长主要由于客户账户余额增加。",
    "公司服务收入增长主要由客户2号账户的余额增加带动。",
    "Our services revenue increased due to higher project 15 amortization.",
])
def test_w08_directional_driver_requires_the_operating_metric_itself_as_subject(text):
    fact = reading.detect_reading_business_fact(text)
    assert not {"operating_quantity", "operating_causal_driver", "product_operating_driver"} & set(fact.reasons)


@pytest.mark.parametrize("text", [
    "Our active customer count totaled 560 at year end.",
    "Our total project count stood at 240 during the year.",
    "Our active customer count was 560 at year end.",
    "Our total project number stood at 240 during the year.",
])
def test_w08_count_labels_and_stock_predicates_are_one_quantity_relation(text):
    fact = reading.detect_reading_business_fact(text)
    assert "operating_quantity" in fact.reasons
    assert fact.purpose == "operating_metric"


@pytest.mark.parametrize("text", [
    "Our services revenue increased due to 253 new customers.",
    "Our services revenue increased due to higher active customer count.",
    "Our services revenue increased due to customer count growth.",
    "Our services revenue increased due to growth in active customers.",
    "Our services revenue increased due to projects totaling 560 at year end.",
    "Our services revenue increased due to lower pricing.",
    "Our services revenue increased due to usage increasing.",
    "Our services revenue increased due to higher capacity utilization.",
    "Our services revenue increased due to improved product mix.",
    "平台服务收入增长主要由客户使用量增长带动。",
    "平台服务收入增长主要由客户数增加带动。",
])
def test_w08_quantity_and_directional_causal_consumers_require_their_own_relations(text):
    fact = reading.detect_reading_business_fact(text)
    assert {"operating_causal_driver", "product_operating_driver"} <= set(fact.reasons)


@pytest.mark.parametrize("text", [
    "New service revenue exceeded 30% of revenue.",
    "New product revenue exceeds 30%.",
    "Our Diagnostics services revenue increased to USD 26.5 million.",
])
def test_w08_present_and_past_absolute_revenue_thresholds_are_native_facts(text):
    fact = reading.detect_reading_business_fact(text)
    assert "business_revenue_measure" in fact.reasons


# W08 measure grammar uses bounded source subjects, including native wrapping.
@pytest.mark.parametrize("text", [
    "新分子业务持续发力，2025 年收入占比进一\n步提升至超30%，在核酸类、偶联类、多特异性抗体类、多肽类等领域保持领先地位。",
    "新分子业务持续贡献增长，2025 年收入占比进一步提升至超30%，核酸类、偶联抗体类、\n多肽类等领域新客户快速增长。",
    "新平台业务本年度收入占比进一步提升至超过41%。",
    "新平台業務持續貢獻增長，2024 年收入佔比進一步提升至逾41%。",
    "技术服务持续增长，报告期内收入占比已提升至约37%。",
    "Our hosting services revenue share further increased to over 37% this year.",
    "Our hosting services revenue share increased further to more than 47% this year.",
    "新平台业务收入占比同比进一步提升至超过41%。",
    "Our hosting services continued to expand, and their revenue share further increased to over 37% this year.",
    "The new product gained traction, its revenue now represents 41% of segment revenue.",
])
def test_w08_scoped_revenue_modifiers_and_single_comma_subject_continuity(text):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    fact = reading.detect_reading_business_fact(text)
    assert "business_revenue_measure" in fact.reasons
    parsed, pipeline = source_fixture([(text,)])
    before = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    candidates, metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(candidates) == 1
    assert metadata[candidates[0].unit.unit_id]["value_band"] == "meaningful_fact"
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == before


@pytest.mark.parametrize("text", [
    "新平台业务持续增长，另一个客户收入占比进一步提升至41%。",
    "新平台业务持续增长，公司总收入占比进一步提升至41%。",
    "产品理念很重要，2024 年收入占比进一步提升至41%。",
    "新平台业务持续增长，行业需求增加，2024 年收入占比进一步提升至41%。",
    "新平台业务持续增长。2024 年收入占比进一步提升至41%。",
    "假设新平台业务收入占比进一步提升至41%。",
    "如果新平台业务收入占比进一步提升至41%，公司将受益。",
    "新平台业务预计收入占比进一步提升至41%。",
    "新平台业务收入占比尚未提升至41%。",
    "新平台业务收入占比不明，2024 年公司总收入为41亿元。",
    "Total revenue now represents 41% of the prior year's assets.",
    "Our services continued to grow, another company's revenue now represents 41% of sales.",
    "Our services continued to grow, and total revenue now represents 41% of sales.",
    "Our product philosophy is important, its revenue now represents 41% of sales.",
    "Our services continued to grow, customer demand improved, and their revenue now represents 41% of sales.",
    "If our service revenue share further increased to 41%, profits would improve.",
    "Our service revenue share is expected to further increase to 41%.",
    "Our service revenue share has not increased to 41%.",
    "Definition: service revenue share increased to 41%.",
    "新平台业务收入2024年度介绍将在下文继续。",
    "Our service revenue 2024 is discussed in the glossary.",
    "Our service revenue 41 is an unidentified field.",
])
def test_w08_revenue_continuity_cannot_cross_new_actors_states_or_unknown_clauses(text):
    fact = reading.detect_reading_business_fact(text)
    assert "business_revenue_measure" not in fact.reasons


@pytest.mark.parametrize("text", [
    "新客户快速增长。",
    "客户数量同比增加。",
    "本期客戶數量持續增長。",
    "Our customer count rapidly increased.",
    "Our active users continued to grow.",
    "Our services revenue increased due to customer count rapidly increasing.",
    "平台服务收入增长主要由客户数量同比增加带动。",
])
def test_w08_directional_measure_modifiers_use_the_same_source_relation_owner(text):
    from company_wiki.source_catalog import narrative_business_policy as policy
    interpreted = policy._reading_text(text)
    relations = tuple(relation for clause in policy._reading_clauses(interpreted)
                      for relation in policy._source_measure_relations(clause))
    assert any(kind == "direction" for kind, _start, _end in relations)
    fact = reading.detect_reading_business_fact(text)
    assert fact.eligible
    assert {"operating_metric_change", "operating_causal_driver", "product_operating_driver"} & set(fact.reasons)


@pytest.mark.parametrize("text", [
    "客户2024年快速增长。",
    "客户2号账户余额持续增加。",
    "客户数量为41万元。",
    "客户收入快速增长。",
    "项目8的摊销持续增加。",
    "Customer 8 account balances rapidly increased.",
    "Customer loan balances continued to grow.",
    "Our services revenue increased due to customer 8 account growth.",
    "Our services revenue increased due to rapidly growing customer loan balances.",
    "假设客户数量快速增长。",
    "客户数量预计持续增长。",
    "客户数量增长情况不明。",
    "If customer count rapidly increased, profits would improve.",
    "Customer count is expected to rapidly increase.",
])
def test_w08_directional_modifiers_do_not_turn_ids_or_financial_balances_into_metrics(text):
    fact = reading.detect_reading_business_fact(text)
    assert not {"operating_quantity", "operating_metric_change", "operating_causal_driver", "product_operating_driver"} & set(fact.reasons)


@pytest.mark.parametrize("text", [
    "假设客户数量为731家。",
    "如果客户数量达到731家，公司将受益。",
    "客户数量是否达到731家尚不明。",
    "If our customer count reached 731 customers, margins would improve.",
    "We may have 619 customers next year.",
    "We do not have 619 customers.",
    "Whether we have 619 customers is unknown.",
    "Our service revenue grew due to an assumption that we have 619 customers.",
    "平台服务收入增长主要由于假设客户数量达到731家。",
    "Our service revenue grew due to product philosophy remaining unchanged while total revenue grew.",
    "平台服务收入增长主要由于产品理念保持不变而公司总收入增长。",
])
def test_w08_unknown_quantity_and_unbound_nested_growth_cannot_bypass_measure_owner(text):
    from company_wiki.source_catalog import narrative_business_policy as policy
    forbidden = {"operating_quantity", "operating_metric_change", "business_revenue_measure",
                 "operating_causal_driver", "product_operating_driver"}
    for clause in policy._reading_clauses(policy._reading_text(text)):
        assert not policy._source_measure_relations(clause)
    assert not policy._measured_driver(policy._reading_text(text))
    description = policy.detect_reading_business_fact(text)
    projected, _financial = policy.assess_reading_business_fact(text, {"relations": []})
    assert not forbidden & set(description.reasons)
    assert not forbidden & set(projected.reasons)


@pytest.mark.parametrize("text", [
    "公司客户数量达到731家，后续计划扩展服务范围。",
    "Our customer count reached 731 customers, and we plan to expand services.",
    "预计明年拓展产品，但本期客户数量达到731家。",
    "We may expand services next year, our current customer count reached 731 customers.",
])
def test_w08_independent_future_information_cannot_erase_current_observed_quantity(text):
    fact = reading.detect_reading_business_fact(text)
    assert "operating_quantity" in fact.reasons


@pytest.mark.parametrize("text", [
    "公司计划拓展客户，预计客户数量达到731家。",
    "客户数量尚未达到731家，仍需完成产品认证。",
    "Our company plans to expand services, customer count is expected to reach 731 customers.",
])
def test_w08_forward_and_constrained_source_descriptions_remain_readable_without_observed_metrics(text):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog import narrative_business_policy as policy
    observed = {"operating_quantity", "operating_metric_change", "business_revenue_measure",
                "operating_causal_driver", "product_operating_driver"}
    fact = reading.detect_reading_business_fact(text)
    assert not observed & set(fact.reasons)
    parsed, pipeline = source_fixture([(text,)])
    candidates, _metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and candidates
    assert [candidate.unit.raw_text for candidate in candidates] == [text]
    assert not policy._source_measure_relations(policy._reading_text(text))
