"""Source turn identity is structural evidence, never an institutional role."""

from __future__ import annotations

from hashlib import sha256
import io
from xml.sax.saxutils import escape
import zipfile

import pytest

from company_wiki.document_normalization import (
    NormalizationLimits,
    normalize_document,
    replay_units,
)
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.source_catalog.narrative_evidence import parse_transcript_text

MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TITLE = "某公司财报交流会"
LINES = [
    "说话人1 00:00 请问新产品何时上线？",
    "说话人2 00:39 我们计划在海外渠道推出新产品。",
    "但具体计划尚未确定，可能会发生变化。",
    "说话人1 02:40 那么是否已经量产？",
    "说话人2 02:55 尚未量产，目前仍在客户验证阶段。",
]


def docx(lines, *, heading_after=None):
    paragraphs = []
    for index, text in enumerate(lines):
        props = (
            '<w:pPr><w:outlineLvl w:val="0"/></w:pPr>' if index == heading_after else ""
        )
        paragraphs.append(f"<w:p>{props}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paragraphs) + "</w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml.encode())
    return output.getvalue()


def normalized(lines=LINES, **kwargs):
    data = docx(lines, **kwargs)
    digest = sha256(data).hexdigest()
    return data, normalize_document(
        data,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        mime_type=MIME,
    )


def observation(document, title=TITLE):
    return build_observation(
        document.units,
        source_id=document.source_id,
        source_sha256=document.source_sha256,
        mime_type=MIME,
        title=title,
    )


def pipeline(document, title=TITLE):
    return understand_units(
        document.units,
        source_id=document.source_id,
        source_sha256=document.source_sha256,
        mime_type=MIME,
        title=title,
    )


def test_docx_observes_anonymous_turns_and_continuation_without_assigning_company_role():
    data, document = normalized()
    units = document.units
    turns = [unit.metadata.get("native_speaker_turn") for unit in units]
    assert all(turns), "native timestamps must reach the shared source port"
    assert {unit.source_role for unit in units} == {"unknown"}
    assert [turn["speaker"] for turn in turns] == [
        "说话人1",
        "说话人2",
        "说话人2",
        "说话人1",
        "说话人2",
    ]
    assert turns[1]["turn_id"] == turns[2]["turn_id"]
    assert turns[0]["turn_id"] != turns[3]["turn_id"]
    assert turns[1]["turn_id"] != turns[4]["turn_id"]
    assert turns[1]["timestamp"] == "00:39"
    assert [unit.raw_text for unit in units] == LINES
    assert replay_units(
        data,
        source_sha256=document.source_sha256,
        units=units,
        limits=NormalizationLimits(),
    ) == tuple(LINES)


def test_docx_heading_stops_anonymous_continuation():
    _, document = normalized([LINES[0], "公司制度", "收入表格说明"], heading_after=1)
    assert document.units[0].metadata.get("native_speaker_turn")
    assert all(
        "native_speaker_turn" not in unit.metadata for unit in document.units[1:]
    )


def test_closed_docx_source_cannot_reopen_at_an_appendix_heading():
    _, document = normalized([
        'Speaker 1 00:00 We discuss new product development.',
        'End of transcript', 'Editorial Appendix',
        'Speaker 7 01:20 Navigation placeholder with earnings keywords.'], heading_after=2)
    assert document.units[0].metadata.get('native_speaker_turn')
    assert all('native_speaker_turn' not in unit.metadata for unit in document.units[1:])


@pytest.mark.parametrize(
    "label",
    [
        "说话人1 99:99 讨论收入",
        "说话人1 00:000 讨论收入",
        "文章提到说话人1 00:00 讨论收入",
        "说话人1 收入增长",
        "营业收入 00:39 人民币100万元",
    ],
)
def test_non_native_timestamp_shapes_do_not_create_speakers(label):
    _, document = normalized([label, "其后的一般说明"])
    assert all("native_speaker_turn" not in unit.metadata for unit in document.units)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("說話人 3 01:02:03 计划尚未确定。", "說話人 3"),
        ("Speaker 7 03:14 The launch has not been approved.", "Speaker 7"),
    ],
)
def test_anonymous_labels_generalize_across_languages(label, expected):
    _, document = normalized([label])
    assert document.units[0].metadata["native_speaker_turn"]["speaker"] == expected
    assert document.units[0].source_role == "unknown"


def test_native_docx_turns_reach_pipeline_and_support_chinese_call_route():
    _, document = normalized()
    source = observation(document)
    output = pipeline(document)
    assert output["route"]["family"] == "earnings_call"
    # Structural turn association is not a Q&A answer attribution.
    assert not any(
        unit["kind"] == "qa_exchange" for unit in output["structure"]["semantic_units"]
    )
    hints = [unit["hints"] for unit in source["units"]]
    assert all(hint.get("native_speaker_turn") for hint in hints)
    assert [hint["speaker"] for hint in hints] == [
        "说话人1",
        "说话人2",
        "说话人2",
        "说话人1",
        "说话人2",
    ]


@pytest.mark.parametrize(
    "lines,title",
    [
        (["普通公司业务说明"], TITLE),
        (["说话人1 00:00 业务进展。", "说话人1 01:00 研发计划。"], TITLE),
        (["说话人1 00:00 业务进展。", "说话人 1 01:00 研发计划。"], TITLE),
        (LINES, "访谈记录"),
    ],
)
def test_title_or_unrelated_interview_does_not_prove_earnings_call(lines, title):
    _, document = normalized(lines)
    output = pipeline(document, title)
    assert output["route"]["family"] != "earnings_call"


def test_saved_docx_11_keeps_old_units_without_new_turn_metadata():
    data, current = normalized()
    old = normalize_document(
        data,
        source_id=current.source_id,
        source_sha256=current.source_sha256,
        mime_type=MIME,
        parser_version="1.1.0",
    )
    assert old.parser_version == "1.1.0"
    assert current.parser_version != old.parser_version
    assert all("native_speaker_turn" not in unit.metadata for unit in old.units)
    assert {unit.source_role for unit in old.units} == {"company_filing"}
    assert [unit.raw_text for unit in old.units] == LINES
    assert replay_units(
        data,
        source_sha256=old.source_sha256,
        units=old.units,
        limits=NormalizationLimits(),
    ) == tuple(LINES)


def test_txt_and_docx_share_native_anonymous_identity_without_role_guessing():
    text = TITLE + "\n" + "\n".join(LINES) + "\nEnd of transcript"
    digest = sha256(text.encode()).hexdigest()
    parsed = parse_transcript_text(
        text,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        language="zh",
    )
    assert len(parsed.units) == len(LINES)
    assert [unit.raw_text for unit in parsed.units] == LINES
    assert {unit.source_role for unit in parsed.units} == {"unknown"}
    turns = [unit.metadata["native_speaker_turn"] for unit in parsed.units]
    assert turns[1]["turn_id"] == turns[2]["turn_id"]
    assert turns[0]["turn_id"] != turns[3]["turn_id"]
    assert [turn["speaker"] for turn in turns] == [
        "说话人1",
        "说话人2",
        "说话人2",
        "说话人1",
        "说话人2",
    ]
    old = parse_transcript_text(
        text,
        source_id=parsed.source_id,
        source_sha256=digest,
        language="zh",
        parser_version="0.3.1",
    )
    assert not old.units and "transcript_start_missing" in old.errors


def test_anonymous_txt_respects_explicit_body_and_inline_end_control():
    text = (
        "Speaker 8 00:00 Editorial roster text.\nSpeaker 9 00:10 Editorial roster response.\n"
        "Full Conference Call Transcript\n"
        + "\n".join(LINES)
        + "\n说话人2 03:00 This concludes the call.\nWebsite Editor: invented business.\n"
    )
    digest = sha256(text.encode()).hexdigest()
    parsed = parse_transcript_text(
        text,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        language="zh",
    )
    assert parsed.units and len(parsed.units) == len(LINES) + 1
    assert not any(
        "Editorial" in unit.raw_text or "invented" in unit.raw_text
        for unit in parsed.units
    )


def test_anonymous_txt_whitespace_keeps_exact_trimmed_source_offsets():
    text = "  " + LINES[0] + "  \n\t" + LINES[1] + " \nEnd of transcript"
    digest = sha256(text.encode()).hexdigest()
    parsed = parse_transcript_text(
        text,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        language="zh",
    )
    assert [unit.raw_text for unit in parsed.units] == LINES[:2]
    lines = text.splitlines()
    for unit in parsed.units:
        c = unit.coordinates
        assert lines[c.paragraph_index][c.char_start : c.char_end] == unit.raw_text


def test_docx_table_stops_turn_even_when_table_has_no_visible_cells():
    data = docx([LINES[0], "ordinary business after table"])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml").replace(
            b"</w:p><w:p>", b"</w:p><w:tbl/><w:p>", 1
        )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml)
    data = output.getvalue()
    digest = sha256(data).hexdigest()
    document = normalize_document(
        data,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        mime_type=MIME,
    )
    assert document.units[0].metadata.get("native_speaker_turn")
    assert "native_speaker_turn" not in document.units[1].metadata


def test_docx_explicit_end_does_not_attach_footer_to_a_speaker():
    lines = [*LINES, "End of transcript", "Website Editor: invented business."]
    _, document = normalized(lines)
    assert [unit.raw_text for unit in document.units] == lines
    assert all(
        "native_speaker_turn" not in unit.metadata for unit in document.units[-2:]
    )


def test_txt_formatting_differences_do_not_manufacture_a_second_actor():
    text = "说话人1 00:00 业务进展。\n说话人 1 01:00 研发计划。\nEnd of transcript"
    digest = sha256(text.encode()).hexdigest()
    parsed = parse_transcript_text(
        text,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        language="zh",
    )
    assert not parsed.units


def test_mixed_native_and_named_txt_speakers_keep_their_own_turns():
    text = (
        "Speaker 8 00:00 Editorial roster.\nSpeaker 9 00:10 Roster response.\n"
        "Earnings Call Transcript\nCEO: We launched a new product.\n"
        + "\n".join(LINES)
        + "\nCFO: Our subscriptions are billed monthly.\nEnd of transcript"
    )
    digest = sha256(text.encode()).hexdigest()
    parsed = parse_transcript_text(
        text,
        source_id="urn:company-wiki:source:sha256:" + digest,
        source_sha256=digest,
        language="zh",
    )
    assert parsed.units and not any(
        "roster" in unit.raw_text.casefold() for unit in parsed.units
    )
    ceo = next(unit for unit in parsed.units if "We launched" in unit.raw_text)
    cfo = next(unit for unit in parsed.units if "billed monthly" in unit.raw_text)
    assert ceo.source_role == cfo.source_role == "management"
    assert (
        "native_speaker_turn" not in ceo.metadata
        and "native_speaker_turn" not in cfo.metadata
    )
    assert any(
        unit.source_role == "unknown" and LINES[2] in unit.raw_text
        for unit in parsed.units
    )


def test_distinct_sources_cannot_pool_their_single_speakers_into_a_call():
    _, first = normalized(["Speaker 1 00:00 We discuss earnings."])
    _, second = normalized(["Speaker 2 00:12 We discuss the quarter."])
    output = understand_units(
        (*first.units, *second.units),
        source_id=first.source_id,
        source_sha256=first.source_sha256,
        mime_type=MIME,
        title=TITLE,
    )
    assert output["route"]["family"] != "earnings_call"


def test_elapsed_minutes_can_exceed_fifty_nine_without_reusing_another_speaker():
    _, document = normalized(
        ["Speaker 2 00:00 Business progress.", "Speaker 3 65:12 Product update."]
    )
    assert document.units[1].metadata["native_speaker_turn"]["speaker"] == "Speaker 3"
    assert document.units[1].metadata["native_speaker_turn"]["timestamp"] == "65:12"


def test_empty_outline_heading_is_still_a_physical_turn_boundary():
    _, document = normalized([LINES[0], "", "普通说明"], heading_after=1)
    assert len(document.units) == 2
    assert "native_speaker_turn" not in document.units[-1].metadata
