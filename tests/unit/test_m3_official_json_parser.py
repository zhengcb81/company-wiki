"""M3-JSON structural parser: RFC 6901 pointers and exact raw byte identity.

The parser is generic: no company, ticker or page number may appear in it.
Frozen anchors come from JSON_EVIDENCE_INDEX.json (sealed run, read-only).
"""

import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.official_json_structure import (
    CWP_JSON_STRUCTURE_PARSER_VERSION,
    JsonStructureDocument,
    JsonStructureError,
    JsonStructureLimits,
    parse_json_structure,
)

import os

_REVENUE_FORECAST_AUDIT_RUN = (
    Path.home() / "Projects" / "revenue-forecast-audit"
    / "runs" / "m3-20261009T184946-cn-688012")
SEALED_RUN = Path(os.environ.get(
    "M3_SEALED_RUN", str(_REVENUE_FORECAST_AUDIT_RUN)))
SEALED_SOURCES = SEALED_RUN / "execution" / "sources"
SEALED_AVAILABLE = SEALED_SOURCES.is_dir()


def _sealed(name: str) -> bytes:
    return (SEALED_SOURCES / name).read_bytes()


# --- grammar admission ------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [b"{}", b"[]", b"null", b"42", b'"text"', b"true", b" [1, 2, 3] ", b'{"a": {}}'],
)
def test_grammar_valid_values_parse_with_kind(raw):
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    assert isinstance(doc, JsonStructureDocument)
    assert doc.root.kind in {"object", "array", "string", "number", "literal"}
    assert doc.byte_size == len(raw)
    assert doc.parser_version == CWP_JSON_STRUCTURE_PARSER_VERSION


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"", "empty_original"),
        (b"   \n\t ", "empty_original"),
        (b"{", "invalid_json_syntax"),
        (b'{"a": ', "invalid_json_syntax"),
        (b"[1, 2", "invalid_json_syntax"),
        (b"{}}", "invalid_json_syntax"),
        (b"[1,]", "invalid_json_syntax"),
        (b"01", "invalid_json_syntax"),
        (b"+1", "invalid_json_syntax"),
        (b".5", "invalid_json_syntax"),
        (b"tru", "invalid_json_syntax"),
        (b"<html><body>page</body></html>", "invalid_json_syntax"),
        (b"\xff\xfe{}", "invalid_json_encoding"),
        (b'{"a": "\xc3\x28"}', "invalid_json_encoding"),
    ],
)
def test_invalid_originals_are_named_refusals(raw, code):
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(raw, limits=JsonStructureLimits())
    assert raised.value.code == code


def test_truncated_page_is_invalid_syntax_not_empty():
    raw = _sealed("qa-latest-form-01.raw") if SEALED_AVAILABLE else b'{"a": "b"'
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(raw[:-8], limits=JsonStructureLimits())
    assert raised.value.code in {"invalid_json_syntax", "invalid_json_encoding"}


# --- pointers ---------------------------------------------------------------


def test_pointer_generation_and_lookup_with_special_keys():
    raw = json.dumps(
        {"a/b": 1, "m~n": {"中文": "值"}, "😀": [True, None, 3.5]},
        ensure_ascii=False,
    ).encode("utf-8")
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    assert doc.at_pointer("/a~1b").value == 1
    assert doc.at_pointer("/m~0n/中文").decoded == "值"
    emoji = doc.at_pointer("/😀")
    assert emoji.kind == "array"
    assert emoji.at("0").value is True
    assert emoji.at("2").value == 3.5
    assert doc.at_pointer("").pointer == ""


@pytest.mark.parametrize("bad", ["a", "/~", "/~2y", " /a"])
def test_invalid_pointer_forms_rejected(bad):
    doc = parse_json_structure(b'{"a": 1}', limits=JsonStructureLimits())
    with pytest.raises(JsonStructureError) as raised:
        doc.at_pointer(bad)
    assert raised.value.code == "invalid_json_pointer"


def test_missing_pointer_is_named_refusal():
    doc = parse_json_structure(b'{"a": [1]}', limits=JsonStructureLimits())
    with pytest.raises(JsonStructureError) as raised:
        doc.at_pointer("/b")
    assert raised.value.code == "pointer_not_found"
    with pytest.raises(JsonStructureError) as raised:
        doc.at_pointer("/a/9")
    assert raised.value.code == "pointer_not_found"


# --- exact byte identity against frozen evidence ----------------------------


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_frozen_latest_page1_anchors_match_evidence_index():
    raw = _sealed("qa-latest-form-01.raw")
    assert len(raw) == 5119
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    record = doc.at_pointer("/datas/0/records/0")
    assert record.token_range == (61, 1141)
    content = doc.at_pointer("/datas/0/records/0/content")
    assert content.token_range == (193, 458)
    assert content.encoded_body_range == (194, 457)
    assert content.encoded_token_sha256 == (
        "d076becb8e4c3800eeb7fad809c999bd44e4c1cbaeb91616d3edff4b92f122e0"
    )
    assert content.decoded_sha256 == (
        "867efb169b6d008051428057f448603cb9071fb7222e4750f906c1f086135444"
    )
    assert content.decoded_character_count == 91
    # Token slices re-decode to the same value: ranges are self-verifying.
    assert json.loads(raw[193:458]) == content.decoded == content.value


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_frozen_answer_precedes_question_and_keeps_independent_locators():
    raw = _sealed("qa-latest-form-18.raw")
    assert len(raw) == 7316
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    record = doc.at_pointer("/datas/0/records/2")
    assert record.token_range == (4653, 7267)
    answer = doc.at_pointer("/datas/0/records/2/content")
    question = doc.at_pointer("/datas/0/records/2/questionContent")
    assert answer.token_range == (5036, 5558)
    assert answer.encoded_body_range == (5037, 5557)
    assert answer.encoded_token_sha256 == (
        "700ff1dd808f4c33cd8d2b9f6fbcc24e947558b3b9737ac856121f9782a31654"
    )
    assert question.token_range == (6702, 6767)
    assert question.encoded_body_range == (6703, 6766)
    assert question.encoded_token_sha256 == (
        "1ee9a3dc4a8532a52b9ee96a7b12a7f27ca93ed30f9fce8ccb26ea0ad1a3c6f0"
    )
    # The real byte order is answer first, question later; a contiguous
    # Q+A range may never be claimed from this page.
    assert answer.token_range[1] < question.token_range[0]
    assert not (answer.token_range[0] <= question.token_range[0] < answer.token_range[1])


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_frozen_precollect_page10_question_and_answer_anchors():
    raw = _sealed("qa-precollect-form-10.raw")
    assert len(raw) == 3871
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    assert doc.at_pointer("/datas/0/records/1").token_range == (1514, 3823)
    question = doc.at_pointer("/datas/0/records/1/question")
    answer = doc.at_pointer("/datas/0/records/1/answer")
    assert question.token_range == (1672, 2862)
    assert question.encoded_token_sha256 == (
        "a4055c0a61d21401956fa08e7cafb85c562c0ef6aaec8fcd1515b8a01bd1bdd0"
    )
    assert question.decoded_character_count == 420
    assert answer.token_range == (2872, 3384)
    assert answer.encoded_token_sha256 == (
        "d87c7993c06d52a2534600bb6569a6cec494901535c489fd10e4bbbab2c2f589"
    )
    assert answer.decoded_character_count == 172


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_frozen_unanswered_question_page1_anchor():
    raw = _sealed("qa-questions-form-01.raw")
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    content = doc.at_pointer("/datas/0/records/0/content")
    assert content.token_range == (429, 645)
    assert content.encoded_body_range == (430, 644)
    assert content.decoded_sha256 == (
        "e19df33fe8e4e29649f56121a8ab832fd0addb7a68c52c6cbfae75329cc71d1a"
    )
    assert content.decoded_character_count == 74


# --- decoded string handling --------------------------------------------------


def test_decoded_string_variants_and_char_byte_separation():
    raw = (
        b'{"zh": "\xe4\xb8\xad\xe6\x96\x87", '
        b'"esc": "\\u4e2d\\u6587", '
        b'"emoji": "\\ud83d\\ude00", '
        b'"nl": "a\\nb", "q": "x\\"y", "bs": "c\\\\d", '
        b'"long": "\\u20ac\\u00a5\\ud83c\\udf7a"}'
    )
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    zh = doc.at_pointer("/zh")
    esc = doc.at_pointer("/esc")
    assert zh.decoded == esc.decoded == "中文"
    assert zh.encoded_token_sha256 != esc.encoded_token_sha256
    assert zh.decoded_sha256 == esc.decoded_sha256
    assert doc.at_pointer("/emoji").decoded == "\U0001f600"
    assert doc.at_pointer("/nl").decoded == "a\nb"
    assert doc.at_pointer("/q").decoded == 'x"y'
    assert doc.at_pointer("/bs").decoded == "c\\d"
    assert doc.at_pointer("/long").decoded == "€¥🍺"
    # Byte offsets are raw offsets: escaped and literal forms keep their own
    # exact raw byte spans.
    zh_span = doc.at_pointer("/zh")
    assert doc.raw[zh_span.encoded_body_range[0]:zh_span.encoded_body_range[1]] == "中文".encode("utf-8")
    assert raw[esc.encoded_body_range[0]:esc.encoded_body_range[1]] == b"\\u4e2d\\u6587"


def test_same_text_in_two_records_keeps_independent_locators():
    raw = json.dumps(
        {"records": [{"content": "相同文本"}, {"content": "相同文本"}]},
        ensure_ascii=False,
    ).encode("utf-8")
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    first = doc.at_pointer("/records/0/content")
    second = doc.at_pointer("/records/1/content")
    assert first.pointer != second.pointer
    assert first.token_range != second.token_range
    assert first.decoded_sha256 == second.decoded_sha256
    assert first.encoded_token_sha256 == second.encoded_token_sha256


def test_string_containing_the_word_content_is_not_special():
    raw = json.dumps({"note": "the word content appears here"}, ensure_ascii=False)
    doc = parse_json_structure(raw.encode("utf-8"), limits=JsonStructureLimits())
    assert doc.at_pointer("/note").decoded == "the word content appears here"


# --- strict refusals ----------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b'{"a": 1, "a": 2}', "duplicate_json_key"),
        (b'{"a": 1, "\\u0061": 2}', "duplicate_json_key"),
        (b'{"x": {"b": 1, "b": 2}}', "duplicate_json_key"),
        (b"[NaN]", "nonfinite_json_number"),
        (b"[Infinity]", "nonfinite_json_number"),
        (b"[-Infinity]", "nonfinite_json_number"),
        (b"[1e999]", "nonfinite_json_number"),
        (b'{"a": "\\ud800"}', "invalid_json_surrogate"),
        (b'{"a": "\\ud83d"}', "invalid_json_surrogate"),
        (b'{"a": "\\x41"}', "invalid_json_syntax"),
        (b'{"a', "invalid_json_syntax"),
        (b'{"a": "raw\ncontrol"}', "invalid_json_syntax"),
    ],
)
def test_strict_value_refusals(raw, code):
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(raw, limits=JsonStructureLimits())
    assert raised.value.code == code


def test_duplicate_key_detection_uses_decoded_keys():
    raw = b'{"\\u0061": 1, "a": 2}'
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(raw, limits=JsonStructureLimits())
    assert raised.value.code == "duplicate_json_key"


# --- budgets -------------------------------------------------------------------


def test_depth_limit_is_precise():
    limits = JsonStructureLimits(max_json_depth=3)
    parse_json_structure(b"[[[1]]]", limits=limits)
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(b"[[[[1]]]]", limits=limits)
    assert raised.value.code == "json_depth_limit_exceeded"


def test_node_limit_is_precise():
    limits = JsonStructureLimits(max_json_nodes=3)
    parse_json_structure(b"[1, 2]", limits=limits)
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(b"[1, 2, 3]", limits=limits)
    assert raised.value.code == "json_node_limit_exceeded"


def test_string_limit_is_on_encoded_body_bytes():
    limits = JsonStructureLimits(max_json_string_bytes=4)
    parse_json_structure('"abcd"'.encode(), limits=limits)
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure('"abcde"'.encode(), limits=limits)
    assert raised.value.code == "json_string_limit_exceeded"


def test_source_byte_limit_refusal():
    limits = JsonStructureLimits(max_source_bytes=8)
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(b'{"a": "123456789"}', limits=limits)
    assert raised.value.code == "json_source_limit_exceeded"


def test_deadline_refusal_is_named():
    import time

    limits = JsonStructureLimits(deadline=time.monotonic() - 1)
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(b"[1, 2, 3]", limits=limits)
    assert raised.value.code == "json_time_limit_exceeded"


def test_bom_counts_three_bytes_toward_offsets():
    raw = b"\xef\xbb\xbf" + b'{"a": 1}'
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    assert doc.has_bom is True
    # BOM occupies raw bytes 0..2; the number token starts at byte 9.
    assert doc.at_pointer("/a").token_range == (9, 10)
    second = b'{"a": 1}\xef\xbb\xbf'
    with pytest.raises(JsonStructureError) as raised:
        parse_json_structure(second, limits=JsonStructureLimits())
    assert raised.value.code == "invalid_json_syntax"


# --- locator format --------------------------------------------------------------


def test_field_locator_format_is_stable_and_escapable():
    raw = json.dumps({"a/b": "值"}, ensure_ascii=False).encode("utf-8")
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    node = doc.at_pointer("/a~1b")
    locator = node.locator()
    assert locator.startswith("cwp-json-pointer/1|")
    parts = dict(part.split("=", 1) for part in locator.split("|")[1:])
    # The pointer is UTF-8 percent-encoded so '/', '~' and non-ASCII keys
    # cannot corrupt the field layout.
    assert parts["p"] == "%2Fa~1b"
    assert parts["b"] == f"{node.token_range[0]}:{node.token_range[1]}"
    assert parts["d"] == f"0:{node.decoded_character_count}"
    assert parts["x"]


def test_decoded_substring_cuts_on_character_boundaries():
    raw = json.dumps({"t": "中文😀tail"}, ensure_ascii=False).encode("utf-8")
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    node = doc.at_pointer("/t")
    piece = node.decoded_slice(2, 4)
    assert piece == "😀t"
    with pytest.raises(JsonStructureError):
        node.decoded_slice(0, 99)
