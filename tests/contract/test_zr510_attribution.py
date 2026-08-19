"""ZR-510 acceptance tests: multi-entity chunk attribution (misattribution
= 0, BR-06/07).

  C1  attribute_document attributes each chunk to the entity its text
      actually names: single entity / mixed / unattributed (honest).
  C2  Changjiang-shaped document: the 紫金 chunk attributes to 紫金, the
      陕西 chunk to 陕西, the entity-less chunk to unattributed — no chunk
      carries a non-local entity (misattribution == 0).
  C3  normalize wiring: multi-entity documents get the frontmatter
      `chunk_attribution` key; single-entity documents stay without it;
      ZR-501..509 fields coexist.
  C4  determinism + zero hardcoding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.attribution import attribute_document  # noqa: E402
from company_wiki.source_catalog.normalizer import (  # noqa: E402
    _Normalized,
    _frontmatter,
)
from company_wiki.source_catalog.section_chunk_fact import (  # noqa: E402
    chunk_spans,
    detect_sections,
)

CHANGJIANG_TEXT = """一、紫金矿业分析

紫金矿业集团股份有限公司的资源禀赋与资本开支情况良好。

二、陕西煤业分析

陕西煤业股份有限公司的成本曲线具有竞争力。

三、风险提示

本报告仅供内部参考，不构成投资建议。
"""


def _chunks(text: str) -> list[list[int]]:
    sections = detect_sections(text)
    return chunk_spans(len([line for line in text.splitlines() if line.strip()]), sections)


# ---------------------------------------------------------------------------
# C1 — per-chunk attribution
# ---------------------------------------------------------------------------


def test_c1_single_entity_chunk_attributes_to_entity():
    text = "紫金矿业集团股份有限公司2025年经营数据\n\n其他内容"
    chunks = [[0, 1], [1, 2]]
    result = attribute_document(
        text, chunks, ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    assert result[0]["attribution"] == "紫金矿业集团股份有限公司"
    assert result[1]["attribution"] == "unattributed"


def test_c1_mixed_chunk():
    text = "紫金矿业集团股份有限公司与陕西煤业股份有限公司对比"
    result = attribute_document(
        text, [[0, 1]], ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    assert result[0]["attribution"] == "mixed"


def test_c1_unattributed_chunk():
    text = "本报告仅供内部参考，不构成投资建议。"
    result = attribute_document(text, [[0, 1]], ["紫金矿业集团股份有限公司"])
    assert result[0]["attribution"] == "unattributed"
    assert result[0]["entities"] == []


# ---------------------------------------------------------------------------
# C2 — Changjiang-shaped document, misattribution == 0
# ---------------------------------------------------------------------------


def test_c2_changjiang_shape_has_zero_misattribution():
    chunks = _chunks(CHANGJIANG_TEXT)
    candidates = [
        "紫金矿业集团股份有限公司",
        "陕西煤业股份有限公司",
    ]
    result = attribute_document(CHANGJIANG_TEXT, chunks, candidates)
    by_entity: dict[str, list[int]] = {}
    for item in result:
        by_entity.setdefault(item["attribution"], []).append(item["chunk_index"])
    assert "紫金矿业集团股份有限公司" in by_entity
    assert "陕西煤业股份有限公司" in by_entity
    assert "unattributed" in by_entity
    # misattribution == 0: every attributed chunk's entity actually appears
    # in that chunk's own text
    for item in result:
        if item["attribution"] not in ("mixed", "unattributed"):
            assert item["attribution"] in item["entities"] or any(
                item["attribution"] in phrase or phrase in item["attribution"]
                for phrase in item["entities"]
            )


def test_c2_unattributed_chunk_carries_no_entity():
    chunks = _chunks(CHANGJIANG_TEXT)
    result = attribute_document(
        CHANGJIANG_TEXT, chunks, ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    risk = next(item for item in result if item["chunk_index"] == 3)
    assert risk["attribution"] == "unattributed"
    assert risk["entities"] == []


# ---------------------------------------------------------------------------
# C3 — normalize wiring
# ---------------------------------------------------------------------------


def _doc() -> dict:
    return {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": "紫金矿业VS陕西煤业，矿企两大模式之辩",
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
        "metadata_json": {
            "acquisition": {
                "publisher": "长江证券",
                "canonical_entity_id": "紫金矿业集团股份有限公司",
            }
        },
    }


def _norm(body: str) -> _Normalized:
    return _Normalized(
        body=body,
        parser_results=(),
        parser_name="pdf_page_aware_core",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
        error=None,
        page_count=2,
        first_page_text=body.splitlines()[0] if body else None,
    )


def test_c3_multi_entity_document_gets_chunk_attribution():
    import yaml

    payload = yaml.safe_load(_frontmatter(_doc(), _norm(CHANGJIANG_TEXT)).split("---\n", 2)[1])
    assert payload["detected_entities"]["verdict"] == "multi_entity"
    assert "chunk_attribution" in payload
    # chunk semantics (ZR-506): sections + 1 leading range
    assert len(payload["chunk_attribution"]) == payload["document_structure"]["chunk_count"] == 4
    assert payload["page_count"] == 2           # ZR-501
    assert "homepage_identity" in payload        # ZR-502
    assert "document_structure" in payload       # ZR-506


def test_c3_single_entity_document_has_no_chunk_attribution():
    import yaml

    payload = yaml.safe_load(
        _frontmatter(_doc(), _norm("紫金矿业集团股份有限公司2025年年度报告")).split("---\n", 2)[1]
    )
    assert payload["detected_entities"]["verdict"] == "single"
    assert "chunk_attribution" not in payload


# ---------------------------------------------------------------------------
# C4 — determinism + zero hardcoding
# ---------------------------------------------------------------------------


def test_c4_deterministic():
    first = attribute_document(
        CHANGJIANG_TEXT, _chunks(CHANGJIANG_TEXT), ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    second = attribute_document(
        CHANGJIANG_TEXT, _chunks(CHANGJIANG_TEXT), ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    assert first == second


def test_c4_zero_hardcoded_names_in_product_module():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "company_wiki"
        / "source_catalog"
        / "attribution.py"
    ).read_text(encoding="utf-8")
    for name in ("紫金矿业", "陕西煤业"):
        assert name not in source


def test_c4_locator_bearing_body_offsets_stay_aligned():
    """REV-002 fix: production bodies carry '## Page N' and
    '<!-- locator: ... -->' lines — the content-line universe used by
    chunk offsets must match attribute_document's slicing exactly."""
    body = (
        "## Page 1\n\n"
        "<!-- locator: loc:v1/page:1/paragraph:0 -->\n\n"
        "一、紫金矿业分析\n\n"
        "<!-- locator: loc:v1/page:1/paragraph:1 -->\n\n"
        "紫金矿业集团股份有限公司的资源禀赋良好。\n\n"
        "## Page 2\n\n"
        "<!-- locator: loc:v1/page:2/paragraph:0 -->\n\n"
        "二、陕西煤业分析\n\n"
        "<!-- locator: loc:v1/page:2/paragraph:1 -->\n\n"
        "陕西煤业股份有限公司的成本曲线有竞争力。\n\n"
        "三、风险提示\n\n"
        "本报告仅供内部参考。\n"
    )
    from company_wiki.source_catalog.section_chunk_fact import (  # noqa: F811
        chunk_spans,
        content_line_count,
        detect_sections,
    )

    sections = detect_sections(body)
    chunks = chunk_spans(content_line_count(body), sections)
    result = attribute_document(
        body, chunks, ["紫金矿业集团股份有限公司", "陕西煤业股份有限公司"]
    )
    by_index = {item["chunk_index"]: item for item in result}
    # chunk 1 = 一、紫金矿业分析 section content; chunk 2 = 二、陕西煤业分析
    assert by_index[1]["attribution"] == "紫金矿业集团股份有限公司"
    assert by_index[2]["attribution"] == "陕西煤业股份有限公司"
    assert by_index[3]["attribution"] == "unattributed"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
