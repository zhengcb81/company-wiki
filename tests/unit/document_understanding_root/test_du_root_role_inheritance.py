"""ROOT tests: a sub-section must inherit its parent chapter's role.

This locks the defect that made the offering document's construction schedule
invisible: the chapter ``第三节 董事会关于本次募集资金使用的可行性分析`` was
correctly recognised as fundraising, but every sub-section under it
(``（一）项目基本情况``, ``（二）项目投资计划``, ``（四）项目建设周期``) named no
chapter topic of its own and stayed ``unknown``.  ``unknown`` then ranked behind
every recognised role, so the project packages built from those sub-sections were
never reached inside the evidence budget.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding.structure import build_structure  # noqa: E402


def _observation(units: list[dict]) -> dict:
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "d"},
        "metadata": {"title": "t", "mime_type": "application/pdf", "language": "zh"},
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": units,
    }


def _heading(unit_id: str, text: str, level: int, page: int, y: int) -> dict:
    return {
        "unit_id": unit_id,
        "ordinal": y,
        "locator": f"loc:{unit_id}",
        "page": page,
        "text": text,
        "kind": "heading",
        "language": "zh",
        "role": "company_filing",
        "layout": {"bbox": [60, y, 400, y + 20], "page_width": 595, "page_height": 842},
        "hints": {"heading_level": level},
    }


def _paragraph(unit_id: str, text: str, page: int, y: int) -> dict:
    return {
        "unit_id": unit_id,
        "ordinal": y,
        "locator": f"loc:{unit_id}",
        "page": page,
        "text": text,
        "kind": "paragraph",
        "language": "zh",
        "role": "company_filing",
        "layout": {"bbox": [60, y, 530, y + 40], "page_width": 595, "page_height": 842},
        "hints": {},
    }


def _document() -> dict:
    return _observation(
        [
            _heading("h1", "第三节 董事会关于本次募集资金使用的可行性分析", 1, 61, 90),
            _paragraph("p1", "本次募集资金拟投资于以下项目：", 61, 130),
            _heading("h2", "（一）项目基本情况", 3, 61, 180),
            _paragraph("p2", "本项目由公司负责实施。", 61, 210),
            _heading("h3", "（二）项目投资计划", 3, 61, 260),
            _paragraph("p3", "本项目总投资为35,300.00 万元。", 61, 290),
            _heading("h4", "（四）项目建设周期", 3, 62, 95),
            _paragraph("p4", "项目建设期两期，新建厂房为一期，老厂区改建为二期。", 62, 130),
        ]
    )


def test_subsection_inherits_the_parent_chapter_role() -> None:
    result = build_structure(_document())
    sections = {section["section_id"]: section for section in result["sections"]}
    parents = {
        section_id: section
        for section_id, section in sections.items()
        if section["section_role"] == "fundraising"
    }
    assert parents, "the fundraising chapter must be recognised"
    children = [
        section
        for section in sections.values()
        if section["parent_id"] in parents
    ]
    assert children, "the sub-sections must be children of the chapter"
    for child in children:
        assert child["section_role"] == "fundraising", (
            f"{child['section_id']} kept the unresolved role instead of inheriting"
        )
        assert "role_inherited" in child["basis"]


def test_a_positively_matched_role_is_never_overwritten_by_inheritance() -> None:
    """A sub-section that names its own topic keeps that topic."""
    observation = _document()
    observation["units"].append(_heading("h5", "（三）风险因素", 3, 61, 330))
    observation["units"].append(_paragraph("p5", "项目实施存在一定风险。", 61, 360))
    result = build_structure(observation)
    sections = {section["section_id"]: section for section in result["sections"]}
    risk = [section for section in sections.values() if section["section_role"] == "risk"]
    assert risk, "a self-named risk sub-section must keep the risk role"
    for section in risk:
        assert "role_inherited" not in section["basis"]


def test_unknown_stays_unknown_when_the_parent_is_also_unknown() -> None:
    """Inheritance must not manufacture a role out of nothing."""
    observation = _observation(
        [
            _heading("h1", "某无主题章节", 1, 1, 90),
            _heading("h2", "（一）细节", 3, 1, 130),
            _paragraph("p1", "一段正文。", 1, 160),
        ]
    )
    result = build_structure(observation)
    for section in result["sections"]:
        assert section["section_role"] == "unknown"
        assert "role_inherited" not in section["basis"]
