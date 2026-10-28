"""Numeric/CJK quote observation at proven fragment edges, not source repair."""
from hashlib import sha256
import json

import pytest

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256
from tools.document_understanding_benchmark.closed_group_support import score_facts


SOURCE = source_id_for_sha256("a" * 64)


def _span(text, index, *, block, start=0, page=3, role="company_filing",
          source=SOURCE, kind="pdf_text_block", table=None, row=None):
    return EvidenceSpan.create(
        source_id=source,
        coordinates=EvidenceCoordinates(
            page_number=page, paragraph_index=index if table is None else None,
            table_index=table, row_index=row,
        ),
        raw_text=text,
        structured_value={
            "source_role": role, "unit_kind": kind,
            "selection_reasons": ["reading_plan"], "pdf_block": block,
            "block_sha256": sha256(str(block).encode()).hexdigest(),
            "block_char_start": start, "block_char_end": start + len(text),
        },
        parser_name="selective_narrative_parser", parser_version="1.0.0",
        parse_status="parsed", quality_flags=(),
    )


def _context(groups, *, kind="native_continuity"):
    result = []
    for rows in groups:
        ids = [span.span_id for span in rows]
        digest = sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
        result.append({
            "group_id": "urn:company-wiki:reading-group:sha256:" + digest,
            "kind": kind, "section_role": "business", "evidence_ids": ids,
        })
    return {"schema_version": "du-production-reading/1", "groups": result}


def _supports(quote, rows, context):
    facts = [{"id": "neutral-quantity", "any_support_sets": [[{
        "exact_quote": quote, "location_kind": "document",
    }]]}]
    return score_facts(
        facts, evidence_spans=rows, reading_context=context, source_id=SOURCE,
    )[0]["supported"]


@pytest.mark.parametrize("kind", ["native_continuity", "background"])
@pytest.mark.parametrize(("left", "right", "quote"), [
    ("公司研发人员为", "560人。", "公司研发人员为560人。"),
    ("收入为2,345.6", "百万元。", "收入为2,345.6百万元。"),
    ("截至2024", "年末。", "截至2024年末。"),
    ("研究团队增至", "320人。", "研究团队增至320人。"),
])
def test_proven_numeric_cjk_fragment_edge_preserves_quantity(left, right, quote, kind):
    same_block = kind == "background"
    rows = [_span(left, 0, block=4), _span(
        right, 1, block=4 if same_block else 5, start=len(left) if same_block else 0,
    )]
    before = [span.to_dict() for span in rows]
    assert _supports(quote, rows, _context([rows], kind=kind))
    assert [span.to_dict() for span in rows] == before


@pytest.mark.parametrize(("left", "right", "invented"), [
    ("总额为12", "34万元。", "总额为1234万元。"),
    ("总额为12.", "34万元。", "总额为12.34万元。"),
    ("总额为12", ".34万元。", "总额为12.34万元。"),
    ("总额为1,", "234万元。", "总额为1,234万元。"),
    ("总额为1", ",234万元。", "总额为1,234万元。"),
    ("The sub", "scribers increased.", "The subscribers increased."),
    ("公司收入为2 345.6", "百万元。", "公司收入为2345.6百万元。"),
    ("公司收入为2. 345", "百万元。", "公司收入为2.345百万元。"),
    ("公司收入为", "2 345.6百万元。", "公司收入为2345.6百万元。"),
    ("公司研 发投入为", "300万元。", "公司研发投入为300万元。"),
])
def test_fragment_edge_cannot_merge_tokens_or_delete_internal_spaces(left, right, invented):
    rows = [_span(left, 0, block=4), _span(right, 1, block=5)]
    assert not _supports(invented, rows, _context([rows]))


@pytest.mark.parametrize("break_kind", [
    "page", "paragraph_gap", "block_reversed", "role", "source", "table_row", "unproven_group",
])
def test_numeric_cjk_join_cannot_bypass_existing_continuity(break_kind):
    left = _span("公司研发人数为", 0, block=4)
    kwargs = {"block": 5}
    index = 1
    group_kind = "native_continuity"
    if break_kind == "page":
        kwargs["page"] = 4
    elif break_kind == "paragraph_gap":
        index = 2
    elif break_kind == "block_reversed":
        kwargs["block"] = 3
    elif break_kind == "role":
        kwargs["role"] = "management"
    elif break_kind == "source":
        kwargs["source"] = source_id_for_sha256("b" * 64)
    elif break_kind == "table_row":
        kwargs.update(kind="pdf_table_row", table=1, row=2)
    elif break_kind == "unproven_group":
        group_kind = "background"
    rows = [left, _span("560人。", index, **kwargs)]
    assert not _supports("公司研发人数为560人。", rows, _context([rows], kind=group_kind))


def test_number_from_another_subject_group_cannot_complete_a_claim():
    # The source owner separates subjects into distinct closed groups. The
    # oracle must not flatten those groups even if all spans share one page.
    rows = [
        _span("公司甲预计研发人数为", 0, block=4),
        _span("公司乙研发人数为", 1, block=5),
        _span("560人。", 2, block=6),
    ]
    context = _context([[rows[0]], rows[1:]])
    assert not _supports("公司甲预计研发人数为560人。", rows, context)


def test_distant_same_block_char_ranges_cannot_join_numeric_cjk():
    left = "公司收入为2,345.6"
    rows = [_span(left, 0, block=4), _span("百万元。", 1, block=4, start=len(left) + 8)]
    assert not _supports("公司收入为2,345.6百万元。", rows, _context([rows], kind="background"))
