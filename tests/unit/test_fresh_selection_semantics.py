"""General selection contracts from fresh audit failures; originals stay exact."""

import hashlib

import pytest

from company_wiki.source_catalog.narrative_document import NarrativeParseResult
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def select(lines, *, language="zh", limit=96, ocr=False):
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    sid = source_id_for_sha256(digest)
    units = []
    for i, text in enumerate(lines):
        metadata = {"pdf_block": 1, "bbox": [70, 100 + i * 12, 500, 112 + i * 12]}
        if ocr:
            metadata = {"coordinate_space": "image_pixels", "media_sha256": "a" * 64,
                        "ocr_fingerprint": "b" * 64, "shape_path": [1], "ocr_line_index": i,
                        "ocr_confidence": 0.99, "image_width": 1000, "image_height": 1000,
                        "ocr_box": [70, 100 + i * 12, 500, 112 + i * 12], "slide_id": "slide7"}
        units.append(_make_unit(source_id=sid, parser_version="1.0.0",
                                coordinates=EvidenceCoordinates(page_number=7 if ocr else 41,
                                                                paragraph_index=i),
                                raw_text=text, unit_kind="pptx_image_ocr_line" if ocr else "pdf_text_block",
                                source_role="company_filing", language=language, metadata=metadata))
    parsed = NarrativeParseResult(sid, digest, language, tuple(units), page_count=41,
                                  pages_read=41, line_count=len(units))
    result = select_narrative_evidence(parsed, title="Another issuer annual report",
                                       existing_kind="annual_report", max_selected=limit)
    return result, units


@pytest.mark.parametrize("simplified,traditional", [
    ("公司新产品已通过客户验证，并已进入海外市场量产。",
     "公司新產品已通過客戶驗證，並已進入海外市場量產。"),
    ("本年度海外业务持续增长，新客户已经完成产品验证。",
     "本年度海外業務持續增長，新客戶已經完成產品驗證。"),
    ("公司生产线产能利用率提升至85%，新产线已投入使用。",
     "公司生產線產能利用率提升至85%，新產線已投入使用。"),
])
def test_native_scripts_have_equivalent_recall_but_keep_original_text(simplified, traditional):
    left, _ = select([simplified])
    right, originals = select([traditional])
    assert len(left.evidence_spans) == len(right.evidence_spans) == 1
    assert left.evidence_spans[0].structured_value["topics"] == right.evidence_spans[0].structured_value["topics"]
    span = right.evidence_spans[0]
    assert span.raw_text == traditional
    assert span.coordinates == originals[0].coordinates
    assert span.structured_value["text_sha256"] == originals[0].text_sha256


@pytest.mark.parametrize("text", [
    "本年度本土市場遊戲的日活躍用戶增長18%，國際市場付費用戶增加。",
    "報告期內廣告曝光次數同比上升，平均廣告價格增長帶動營銷服務發展。",
    "During the quarter, advertising impressions increased 12% and average ad pricing rose 5%.",
])
def test_operating_metrics_are_business_narrative_without_industrial_keywords(text):
    package, units = select([text], language="en" if text.startswith("During") else "zh")
    assert len(package.evidence_spans) == 1
    assert package.evidence_spans[0].raw_text == units[0].raw_text


def test_product_subject_repeat_order_and_quantity_are_one_atomic_statement():
    lines = [
        "公司总部位于上海市浦东新区。",
        "公司在新产品开发方面取得了显著成效，近两年新开发出十多种导体和介质薄膜设备，目前",
        "已有多款新型设备产品进入市场，其中部分设备已获得重复性订单，LPCVD设备累计出货量突破",
        "三百个反应台，其他多个关键薄膜沉积设备研发项目正在顺利推进；",
        "公司EPI设备已顺利进入客户端量产验证阶段。",
    ]
    package, _ = select(lines)
    spans = {span.coordinates.paragraph_index: span for span in package.evidence_spans}
    assert {1, 2, 3} <= set(spans)
    assert 0 not in spans
    assert len({spans[i].structured_value.get("selection_group_id") for i in (1, 2, 3)}) == 1
    assert spans[1].structured_value.get("selection_group_id") is not None
    capped, _ = select(lines, limit=2)
    retained = {span.coordinates.paragraph_index for span in capped.evidence_spans}
    assert not (retained & {1, 2, 3})  # A small quota must omit the whole statement.


def test_ocr_short_segment_owner_stays_with_its_predicate_and_tail():
    lines = ["Agents and Infra", "Revenue grew 30%, driven by the new platform", "and higher customer adoption."]
    package, _ = select(lines, language="en", ocr=True)
    assert {span.coordinates.paragraph_index for span in package.evidence_spans} == {0, 1, 2}
    assert len({span.structured_value.get("selection_group_id") for span in package.evidence_spans}) == 1


def test_governance_keyword_boilerplate_does_not_spend_business_quota():
    lines = ["公司本年度完成新产品客户验证，并已在海外产线实现量产。",
             "公司持续加强反舞弊管理，提升员工培训水平，完善公司治理与内部控制制度。"]
    package, _ = select(lines)
    assert {span.coordinates.paragraph_index for span in package.evidence_spans} == {0}


def test_specific_supply_chain_risk_keeps_its_conditional_body():
    lines = ["3、上游供应链产能紧张的风险",
             "公司科学管理供应厂商，对关键零部件供应商采取多厂商策略保障及时供应。",
             "若未来上游供应链产能紧张形势延续，将对公司设备交期产生影响。"]
    package, _ = select(lines)
    assert any("若未来" in span.raw_text for span in package.evidence_spans)


@pytest.mark.parametrize("text", [
    "Supply constraints delayed deliveries to customers by six weeks.",
    "Production capacity decreased 20% following an unexpected factory closure.",
    "Customer orders declined 20% and our backlog fell by five million units.",
])
def test_english_negative_operating_disclosures_are_material_business_evidence(text):
    package, _ = select([text], language="en")
    assert [span.raw_text for span in package.evidence_spans] == [text]


@pytest.mark.parametrize("lines", [
    ["The board training on ad pricing increased awareness of internal anti-fraud policies."],
    ["Advertising impressions were stable!", "Our fraud-awareness training increased completion rates."],
])
def test_metric_words_in_training_or_a_finished_previous_sentence_are_not_operating_growth(lines):
    package, _ = select(lines, language="en")
    assert package.evidence_spans == ()


@pytest.mark.parametrize("ocr", [False, True])
def test_fragment_count_does_not_split_a_bounded_sentence_from_its_cancellation_condition(ocr):
    lines = ["公司新产品", "已经完成客户验证，", "未来将进入量产阶段，", "本项目还需要",
             "补充设备安装，", "完成场地建设，", "办理生产许可，", "落实上游供应，",
             "以上安排尚未经董事会批准且可能取消。"]
    full, _ = select(lines, ocr=ocr)
    assert {span.coordinates.paragraph_index for span in full.evidence_spans} == set(range(9))
    assert len({span.structured_value.get("selection_group_id") for span in full.evidence_spans}) == 1
    for limit in (1, 7, 8):
        capped, _ = select(lines, limit=limit, ocr=ocr)
        assert capped.evidence_spans == ()
        assert capped.omitted_candidate_count == 9
        assert capped.status == "partial"


def test_finished_previous_product_description_is_not_borrowed_as_the_next_event_subject():
    lines = ["公司新产品技术采用独立架构，不涉及本年度的业务进展。",
             "公司已签订海外客户的供货合同。"]
    package, _ = select(lines)
    assert {span.coordinates.paragraph_index for span in package.evidence_spans} == {1}


@pytest.mark.parametrize("lines,language", [
    (["董事会关于广告价格的培训提升了员工的反舞弊意识。"], "zh"),
    (["Revenue grew 30%!", "Our anti-fraud training was driven by higher customer adoption of the new policy."], "en"),
])
def test_operating_subject_and_cause_cannot_be_borrowed_from_training_or_another_sentence(lines, language):
    package, _ = select(lines, language=language)
    assert package.evidence_spans == ()


@pytest.mark.parametrize("ocr", [False, True])
def test_a_statement_over_the_character_cap_is_omitted_instead_of_published_without_its_conditions(ocr):
    lines = ["公司新产品", "已经完成客户验证，", "未来将进入量产阶段，", "本项目还需要",
             "补充设备安装细节，" + "有关项目具体实施安排及前置条件，" * 100,
             "完成场地建设，", "办理生产许可，", "落实上游供应，",
             "以上安排尚未经董事会批准且可能取消。"]
    package, _ = select(lines, ocr=ocr)
    assert package.evidence_spans == ()
    assert package.omitted_candidate_count > 0
    assert package.status == "partial"
