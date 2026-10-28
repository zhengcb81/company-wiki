"""Quote observation preserves tokens and citation scope in verified ranges.

Synthetic canonical EvidenceSpan carriers only: no native extraction or source
ingress proof is fabricated here. The source owner supplies that prerequisite.
"""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256
from tools.document_understanding_benchmark.closed_group_support import score_claim_facts, score_facts


SOURCE = source_id_for_sha256("d" * 64)


def _range(text, *, page=7, source=SOURCE, role="company_filing", native=True):
    return EvidenceSpan.create(
        source_id=source,
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=0,
                                        char_start=0, char_end=len(text)),
        raw_text=text,
        structured_value={"source_role": role,
                          "unit_kind": "pdf_native_range" if native else "pdf_text_block"},
        parser_name="native_pdf_range_parser" if native else "selective_narrative_parser",
        parser_version="0.1.0", parse_status="parsed", quality_flags=(),
    )


def _fact(quote, *, page=7, source=None, role="company_filing"):
    anchor = {"page": page, "exact_quote": quote}
    if source is not None:
        anchor["source_id"] = source
    return {"id": "neutral-business-quantity", "role": role, "any_support_sets": [[anchor]]}


def _supported(row, quote, **kwargs):
    return score_facts([_fact(quote, **kwargs)], evidence_spans=[row],
                       reading_context=None, source_id=SOURCE)[0]["supported"]


@pytest.mark.parametrize(("left", "right"), [
    ("收入为2,345.6", "百万元。"),
    ("收入為2,345.6", "百萬元。"),
    ("公司研发人员为", "560人。"),
    ("截至2024", "年末。"),
    ("计划在下半年", "送样验证。"),
    ("设备尚未完成验证，", "不能投入量产。"),
    ("设备完成了验证", "，仍需认证。"),
])
@pytest.mark.parametrize("break_text", ["\n", "\r\n", " \n  "])
def test_actual_native_line_break_keeps_cjk_quantity_and_qualifier(left, right, break_text):
    row = _range(left + break_text + right)
    before = deepcopy(row.to_dict())
    assert _supported(row, left + right)
    assert row.to_dict() == before


@pytest.mark.parametrize(("raw", "invented"), [
    ("收入为2,345.6 百万元。", "收入为2,345.6百万元。"),
    ("公司研发人员为 560人。", "公司研发人员为560人。"),
    ("公司研 发投入增加。", "公司研发投入增加。"),
    ("总额为12\n34万元。", "总额为1234万元。"),
    ("总额为12.\n34万元。", "总额为12.34万元。"),
    ("总额为12\n.34万元。", "总额为12.34万元。"),
    ("总额为1,\n234万元。", "总额为1,234万元。"),
    ("总额为1\n,234万元。", "总额为1,234万元。"),
    ("We provide owner\nship services.", "We provide ownership services."),
    ("The sub scribers increased.", "The subscribers increased."),
    ("产品名为Alpha\n设备。", "产品名为Alpha设备。"),
    ("数量为2,345.6\n\n百万元。", "数量为2,345.6百万元。"),
])
def test_spacing_observation_cannot_invent_tokens_or_remove_inline_spaces(raw, invented):
    assert not _supported(_range(raw), invented)


@pytest.mark.parametrize("raw", [
    "收入为2,345.6 百万元。", "公司研发人员为 560人。", "公司研 发投入增加。",
    "We provide owner\nship services.", "数量为2,345.6\n\n百万元。",
])
def test_the_original_intentional_spaced_quote_still_matches(raw):
    assert _supported(_range(raw), raw)


@pytest.mark.parametrize("violation", ["page", "source", "anchor_source", "role", "parser"])
def test_quantity_wrap_does_not_bypass_source_page_role_or_range_owner(violation):
    raw, quote = "收入为2,345.6\n百万元。", "收入为2,345.6百万元。"
    args, fact_args = {}, {}
    if violation == "page":
        args["page"] = 8
    elif violation == "source":
        args["source"] = source_id_for_sha256("e" * 64)
    elif violation == "anchor_source":
        fact_args["source"] = source_id_for_sha256("e" * 64)
    elif violation == "role":
        args["role"] = "management"
    else:
        args["native"] = False
    assert not _supported(_range(raw, **args), quote, **fact_args)


def _fragment(text, index):
    return EvidenceSpan.create(
        source_id=SOURCE,
        coordinates=EvidenceCoordinates(page_number=7, paragraph_index=index),
        raw_text=text,
        structured_value={"source_role": "company_filing", "unit_kind": "pdf_text_block",
                          "selection_reasons": ["reading_plan"], "pdf_block": index},
        parser_name="selective_narrative_parser", parser_version="1.0.0",
        parse_status="parsed", quality_flags=(),
    )


def test_partial_factual_citation_cannot_borrow_a_numeric_unit_from_context():
    rows = [_fragment("研发人员为", 0), _fragment("560人。", 1)]
    ids = [row.span_id for row in rows]
    digest = sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    context = {"schema_version": "du-production-reading/1", "groups": [{
        "group_id": "urn:company-wiki:reading-group:sha256:" + digest,
        "kind": "native_continuity", "evidence_ids": ids,
    }]}
    check = {**_fact("研发人员为560人。"), "claim_id": "quantity"}
    full = {"claim_id": "quantity", "evidence_ids": ids, "context_evidence_ids": []}
    partial = {**full, "evidence_ids": ids[:1], "context_evidence_ids": ids[1:]}
    args = {"evidence_spans": rows, "reading_context": context, "source_id": SOURCE}
    assert score_claim_facts([check], claims=[full], **args)[0]["supported"]
    result = score_claim_facts([check], claims=[partial], **args)[0]
    assert not result["supported"] and result["selected_source_support_present"]


def test_two_native_ranges_without_closed_membership_cannot_supply_a_complete_quote():
    rows = [_range("收入为2,345.6"), _range("百万元。")]
    assert not score_facts([_fact("收入为2,345.6百万元。")],
                           evidence_spans=rows, reading_context=None, source_id=SOURCE)[0]["supported"]
