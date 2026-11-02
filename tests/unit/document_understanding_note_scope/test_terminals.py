"""A source sentence cannot become a heading just by closing its quotation."""
from hashlib import sha256

import pytest

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding.observation_adapter import _heading_level
from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import is_heading
from company_wiki.source_contract import source_id_for_sha256
from .fixtures import Row, observation, run_pipeline, snapshot, source


@pytest.mark.parametrize("owner", ["adapter", "layout"])
@pytest.mark.parametrize("prefix", ["3、", "一、"])
@pytest.mark.parametrize("wrapper", ["", "”", '\")', "）", "】", "』", "》"])
def test_numbered_complete_prose_is_not_heading_after_closing_wrappers(owner, prefix, wrapper):
    text = prefix + "甲方承担上述承诺的一切损失。" + wrapper
    parsed, _owned = source((Row("prose", text),))
    before = snapshot(parsed)
    if owner == "adapter":
        assert _heading_level(text, parsed.units[0].metadata) is None
    else:
        wire = observation(parsed)["units"][0]
        assert is_heading(ObservationUnit(wire, 0)) is False
    assert snapshot(parsed) == before


@pytest.mark.parametrize("text", ["3、经营进展", "一、海外业务", "1.2 主营业务（2026）"])
def test_real_numbered_business_heading_retains_original_identity(text):
    parsed, owned = source((Row("heading", text), Row("body", "公司完成检测平台升级。")))
    result, _contexts = run_pipeline(parsed)
    section = next(section for section in result["structure"]["sections"]
                   if owned["body"].unit_id in section["body_unit_ids"])
    assert owned["heading"].unit_id in section["heading_unit_ids"]
    assert parsed.units[0].coordinates.locator() == owned["heading"].coordinates.locator()


def test_actual_html_heading_hint_has_priority_over_sentence_punctuation():
    raw = '<html><body><h2>一、业务说明。”</h2><p>公司完成检测平台升级。</p></body></html>'.encode()
    digest = sha256(raw).hexdigest()
    normalized = normalize_document(raw, source_id=source_id_for_sha256(digest),
                                    source_sha256=digest, mime_type="text/html")
    parsed = normalized.structure
    heading = next(unit for unit in parsed.units if unit.unit_kind == "html_heading")
    body = next(unit for unit in parsed.units if unit.unit_kind == "html_paragraph")
    assert heading.metadata["heading_level"] == 2  # emitted by the real HTML normalizer
    result, _contexts = run_pipeline(parsed)
    section = next(section for section in result["structure"]["sections"]
                   if body.unit_id in section["body_unit_ids"])
    assert heading.unit_id in section["heading_unit_ids"]
