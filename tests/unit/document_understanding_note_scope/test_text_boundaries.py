"""Terminal observation preserves source text and does not eat trailing prose."""
import pytest

from company_wiki.document_understanding.text_boundaries import (
    ends_complete_sentence,
    terminal_punctuation,
)

from .fixtures import Row, run_pipeline, source


@pytest.mark.parametrize(("text", "expected"), (
    ("3、承担上述损失。”,", None),
    ("3、承担上述损失。”  ）  】\n", "。"),
    ("The service is available.\") ]\n", "."),
    ("Do we intend to expand?』", "?"),
    ("是否扩展？）", "？"),
    ("继续建设！】", "！"),
    ("Available!\"", "!"),
    ("范围已经披露；』", "；"),
    ("It is available;»", ";"),
    ("1.2 主营业务（2026）", None),
    ("甲方称“已完成。”但仍需验收", None),
    ("报告期内：", None),
    ("收入增长，", None),
    ("已完成。（", None),
    (" \n )】\"", None),
    ("", None),
))
def test_observe_only_the_terminal_before_closing_wrappers(text, expected):
    original = text
    assert terminal_punctuation(text) == expected
    assert ends_complete_sentence(text) is (expected is not None)
    assert text == original


@pytest.mark.parametrize("prefix", ("3、", "一、"))
@pytest.mark.parametrize("wrapper", ("”", '")', "】", "』"))
def test_actual_layout_pipeline_cannot_reintroduce_numbered_complete_prose(prefix, wrapper):
    parsed, owned = source((
        Row("prose", prefix + "主体承担上述事项的一切损失。" + wrapper),
        Row("body", "公司完成检测平台升级。"),
    ))
    result, _contexts = run_pipeline(parsed)
    heading_ids = {uid for section in result["structure"]["sections"]
                   for uid in section["heading_unit_ids"]}
    assert owned["prose"].unit_id not in heading_ids
