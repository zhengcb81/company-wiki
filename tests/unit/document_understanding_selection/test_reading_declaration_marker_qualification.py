"""List syntax is a prefix, never a new subject or a license to drop a restriction."""
import pytest

from company_wiki.document_understanding.operating_states.text_view import strip_connector
from unit.document_understanding_selection.test_reading_local_qualification import (
    LEFT, NEGATIVE, case,
)


@pytest.mark.parametrize("prefix", ["- ", "• ", "● ", "▪ ", "i. ", "ii) ", "(1) ", "（2） "])
def test_observed_list_marker_is_offset_preserving_prefix(prefix):
    text = prefix + "however more text"
    rest, offset = strip_connector(text)
    assert rest == "more text"
    assert text[offset:] == rest
    assert offset == len(prefix + "however ")


@pytest.mark.parametrize("prefix", ["- ", "• ", "● ", "▪ ", "i. ", "ii) ", "(1) ", "（2） "])
def test_explicit_restriction_in_observed_list_keeps_real_dependency(prefix):
    texts = [prefix + LEFT, prefix + NEGATIVE]
    parsed, result, session = case(texts)
    dependencies = session.local_qualification_dependencies(result["adjacency_edges"])
    assert dependencies == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}
    assert [unit.raw_text for unit in parsed.units] == texts
    for unit in parsed.units:
        for relation in session.relations(unit.unit_id)["relations"]:
            for field in ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs"):
                for ref in relation[field]:
                    original = next(item for item in parsed.units if item.unit_id == ref["unit_id"])
                    assert 0 <= ref["char_start"] < ref["char_end"] <= len(original.raw_text)


@pytest.mark.parametrize("text", ["-5 devices", "-this device", "i.device", "ivory devices", "(1)device", "（2）设备", "x + ", "0.2 devices"])
def test_arithmetic_and_words_without_a_list_delimiter_are_not_stripped(text):
    assert strip_connector(text) == (text, 0)


@pytest.mark.parametrize("prefix", ["- 供应商表示，", "• 其他公司称：", "- 5 + ", "i. 独立新主语 "])
def test_list_marker_does_not_remove_an_intervening_business_subject(prefix):
    parsed, result, session = case([LEFT, prefix + NEGATIVE])
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}
    assert parsed.units[1].raw_text == prefix + NEGATIVE


@pytest.mark.parametrize("prefix", ["II. ", "IV) "])
@pytest.mark.parametrize("exercise", ["prefix", "dependency"])
def test_uppercase_roman_is_the_same_delimited_list_grammar(prefix, exercise):
    if exercise == "prefix":
        text = prefix + "however more text"
        rest, offset = strip_connector(text)
        assert rest == "more text" and text[offset:] == rest
    else:
        parsed, result, session = case([prefix + LEFT, prefix + NEGATIVE])
        assert session.local_qualification_dependencies(result["adjacency_edges"]) == {
            parsed.units[0].unit_id: (parsed.units[1].unit_id,)
        }
