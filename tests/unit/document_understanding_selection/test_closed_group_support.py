"""Eight independent pure fixtures for canonical, already validated selections."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256
from tools.document_understanding_benchmark.closed_group_support import score_facts

SOURCE = source_id_for_sha256("a"*64)


def test_one_verified_native_range_preserves_cjk_wrap_and_future_qualifier():
    # Explicit synthetic carrier; actual original-byte replay has separate tests.
    row = EvidenceSpan.create(source_id=SOURCE,
        coordinates=EvidenceCoordinates(page_number=3, paragraph_index=0, char_start=0, char_end=28),
        raw_text="公司将通\n过合作开发产品。\n下半年将送样验证。",
        structured_value={"source_role": "company_filing", "unit_kind": "pdf_native_range"},
        parser_name="native_pdf_range_parser", parser_version="0.1.0", parse_status="parsed", quality_flags=())
    facts = [{"id": "planned", "role": "company_filing", "any_support_sets": [[{
        "page": 3, "exact_quote": "公司将通过合作开发产品。下半年将送样验证。"}]]}]
    assert score_facts(facts, evidence_spans=[row], reading_context=None, source_id=SOURCE)[0]["supported"]


def test_native_range_whitespace_cannot_create_an_english_word():
    row = EvidenceSpan.create(source_id=SOURCE,
        coordinates=EvidenceCoordinates(page_number=3, char_start=0, char_end=20),
        raw_text="We provide owner\nship services.",
        structured_value={"source_role": "company_filing", "unit_kind": "pdf_native_range"},
        parser_name="native_pdf_range_parser", parser_version="0.1.0", parse_status="parsed", quality_flags=())
    facts = [{"id": "word", "any_support_sets": [[{"page": 3, "exact_quote": "ownership"}]]}]
    assert not score_facts(facts, evidence_spans=[row], reading_context=None, source_id=SOURCE)[0]["supported"]


def span(text, index, *, page=3, block=None, role="company_filing", kind="pdf_text_block",
         reason="reading_context", source=SOURCE, start=0, language="zh", heading=None):
    metadata = {"source_role": role, "unit_kind": kind, "language": language,
        "selection_reasons": [reason], "pdf_block": index if block is None else block,
        "block_sha256": sha256(str(index if block is None else block).encode()).hexdigest(),
        "block_char_start": start, "block_char_end": start+len(text)}
    if heading is not None:
        metadata["heading_level"] = heading
    return EvidenceSpan.create(source_id=source, coordinates=EvidenceCoordinates(page_number=page,
        paragraph_index=index), raw_text=text, structured_value=metadata,
        parser_name="selective_narrative_parser", parser_version="1.0.0",
        parse_status="parsed", quality_flags=())


def context(rows, *, kind="native_continuity", groups=None):
    members = groups or [rows]
    values = []
    for group in members:
        ids = [s.span_id for s in group]
        digest = sha256(json.dumps(ids,separators=(",",":")).encode()).hexdigest()
        values.append({"group_id":"urn:company-wiki:reading-group:sha256:"+digest,
                       "kind":kind,"section_role":"business","evidence_ids":ids})
    return {"schema_version":"du-production-reading/1", "groups":values}


def fact(quote, *, page=3, location_kind=None, role="company_filing", extra=()):
    anchor = {"exact_quote":quote,"page":page}
    if location_kind:
        anchor["location_kind"] = location_kind
    return {"id":"controlled-fact","role":role,
            "any_support_sets":[[anchor,*extra]]}


def supports(f, rows, ctx):
    return score_facts([f], evidence_spans=rows, reading_context=ctx, source_id=SOURCE)[0]["supported"]


def test_cjk_closed_body_wraps_with_prefix_heading_supports_original_quote():
    rows = [span("主要业务",0,page=2,heading=1),
            span("公司新产品进入客户生产验",1,reason="reading_plan"),span("证，尚未量产。",2)]
    before = [s.to_dict() for s in rows]
    assert supports(fact("公司新产品进入客户生产验证，尚未量产。"),rows,context(rows))
    assert not supports(fact("主要业务公司新产品"),rows,context(rows))
    assert [s.to_dict() for s in rows] == before
    # Actual closed production window can contain a completed observation and
    # its subsequent plan/qualifier. The oracle must not re-route that grammar.
    rows = [span("项目开发已取得进展。",0,reason="reading_plan"),
            span("下半年计划根据客户反馈开展验证。",1)]
    quote = "项目开发已取得进展。下半年计划根据客户反馈开展验证。"
    assert supports(fact(quote),rows,context(rows))
    assert not supports(fact(quote),rows,context(rows,kind="background"))
    # Native block ids may count an image/non-text block between body fragments.
    # The actual paragraph order and validated closed group remain authoritative.
    rows = [span("该设备已进入客户生产验",0,block=4,reason="reading_plan"),
            span("证，尚未量产。",1,block=7)]
    assert supports(fact("该设备已进入客户生产验证，尚未量产。"),rows,context(rows))
    assert not supports(fact("该设备已进入客户生产验证，尚未量产。"),rows,context(rows,kind="background"))


def test_document_location_is_a_real_page_free_html_anchor_not_a_page_bypass():
    rows = [span("We provide subscription services.",0,page=None,kind="html_paragraph",
                 reason="reading_plan",language="en")]
    assert supports(fact("We provide subscription services.",page=1,location_kind="document"),rows,None)
    assert not supports(fact("We provide subscription services.",page=1),rows,None)
    foreign = [span("We provide subscription services.",0,page=None,kind="html_paragraph",
                    source=source_id_for_sha256("b"*64),language="en")]
    assert not supports(fact("We provide subscription services.",location_kind="document"),foreign,None)


def test_non_continuity_groups_cannot_create_cross_block_quotes_but_keep_same_group_and():
    rows = [span("设备已进入客户",0,reason="reading_plan"),span("验证，尚未量产。",1)]
    ctx = context(rows,kind="background")
    assert not supports(fact("设备已进入客户验证，尚未量产。"),rows,ctx)
    assert supports(fact("设备已进入客户",extra=({"exact_quote":"验证，尚未量产。","page":3},)),rows,ctx)
    same = [span("设备已进入客户",0,block=2,reason="reading_plan"),
            span("验证，尚未量产。",1,block=2,start=len("设备已进入客户"))]
    assert supports(fact("设备已进入客户验证，尚未量产。"),same,context(same,kind="background"))


def test_separate_closed_groups_on_one_page_cannot_satisfy_one_and_support_set():
    rows = [span("新设备已开展客户验证。",0,reason="reading_plan"),
            span("另一设备尚未量产。",1,reason="reading_plan")]
    ctx = context(rows,kind="background",groups=[[rows[0]],[rows[1]]])
    assert not supports(fact("新设备已开展客户验证。",extra=({"exact_quote":"另一设备尚未量产。","page":3},)),rows,ctx)


def test_english_boundaries_never_create_a_word_and_whitespace_is_not_deleted():
    rows = [span("The number of sub",0,reason="reading_plan",language="en"),
            span("scribers increased.",1,language="en")]
    assert not supports(fact("The number of subscribers increased."),rows,context(rows))
    rows = [span("Subscription",0,reason="reading_plan",language="en"),
            span("growth accelerated.",1,language="en")]
    assert supports(fact("Subscription growth accelerated."),rows,context(rows))
    assert not supports(fact("Subscriptiongrowth accelerated."),rows,context(rows))


def test_typed_heading_question_and_table_boundaries_cannot_be_spliced():
    for kind, role, heading in (("pdf_text_block","company_filing",1),
                                ("pdf_text_block","investor_question",None),
                                ("pdf_table_row","company_filing",None)):
        rows = [span("公司新产品进入客户",0,reason="reading_plan"),
                span("验证阶段",1,kind=kind,role=role,heading=heading),span("并获得重复订单。",2)]
        assert not supports(fact("公司新产品进入客户验证阶段并获得重复订单。"),rows,context(rows))


def test_source_page_role_and_original_order_remain_exact():
    rows = [span("公司新产品进入客户",0,reason="reading_plan"),span("验证，尚未量产。",1,page=4)]
    assert not supports(fact("公司新产品进入客户验证，尚未量产。"),rows,context(rows))
    rows = [span("公司新产品进入客户",0,reason="reading_plan",role="management"),
            span("验证，尚未量产。",1,role="management")]
    assert not supports(fact("公司新产品进入客户验证，尚未量产。"),rows,context(rows))
    assert supports(fact("公司新产品进入客户验证，尚未量产。",role="management"),rows,context(rows))
    ctx = context(rows)
    ctx["groups"][0]["evidence_ids"].reverse()
    with pytest.raises(ValueError,match="order|group"):
        supports(fact("公司新产品进入客户验证，尚未量产。",role="management"),rows,ctx)


def test_declared_kind_is_not_ingress_proof_and_window_bounds_are_enforced():
    rows = [span("公司新产品进入客户",0,reason="reading_plan"),span("验证，尚未量产。",1)]
    with pytest.raises(TypeError,match="EvidenceSpan|typed"):
        supports(fact("公司新产品进入客户验证，尚未量产。"),[s.to_dict() for s in rows],context(rows))
    missing = deepcopy(context(rows))
    missing["groups"][0]["evidence_ids"].append("absent")
    with pytest.raises(ValueError,match="group|reference"):
        supports(fact("company"),rows,missing)
    too_many = [span("研发片段",i,block=0,start=i*4,reason="reading_plan" if i==0 else "reading_context")
                for i in range(8)]+[span("正在开展客户验证。",8,block=0,start=32)]
    with pytest.raises(ValueError,match="bound|window"):
        supports(fact("研发片段"),too_many,context(too_many))
