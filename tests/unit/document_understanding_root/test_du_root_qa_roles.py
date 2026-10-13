"""ROOT contract: the Q&A dual-role-set decision (DU-S-ADAPT-5).

The production parser emits every Q&A page twice: as flat ``qa_text_shadow`` fragments (the
page's text layer) and as structured ``investor_question``/``management`` units that carry
the speaker and turn. The plan required ROOT to decide which set to keep, and the decision
is only defensible if it is stated and locked.

ROOT decision:

* both copies stay in the observation -- the structure lane needs them to pair a question
  with its answer, and deleting either side would make coverage look better than it is;
* the shadow copy is not *selectable* evidence -- it duplicates the structured copy, so
  selecting from it double-counts a sentence and loses the speaker attribution.

This is the same rule production selection already applies (``qa_text_shadow`` appears in
``narrative_candidates._EXCLUDED_ROLES``), so the new layer agrees with the existing one
instead of inventing a second convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding.observation_adapter import (  # noqa: E402
    QA_SHADOW_HINT,
    QA_SHADOW_ROLE,
    QA_STRUCTURED_ROLES,
    build_observation,
    is_selectable,
    selectable_unit_ids,
)


class _Coords:
    def __init__(self, page=1):
        self.page_number = page
        self.row_index = None
        self.table_index = None
        self.column_index = None


class _Unit:
    def __init__(self, unit_id, text, *, role, metadata=None, kind="pdf_text_block"):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = kind
        self.source_role = role
        self.language = "zh"
        self.coordinates = _Coords()
        self.metadata = dict(metadata or {})


def _qa_page_units():
    """The two role sets the parser really emits for one Q&A page."""
    return [
        _Unit("s1", "问：公司目前产能利用率是多少？", role=QA_SHADOW_ROLE),
        _Unit("s2", "答：公司2022年整体产能利用率64.68%。", role=QA_SHADOW_ROLE),
        _Unit(
            "q1",
            "问：公司目前产能利用率是多少？",
            role="investor_question",
            metadata={"qa_state": "question", "qa_group_id": "g1"},
        ),
        _Unit(
            "a1",
            "答：公司2022年整体产能利用率64.68%。",
            role="management",
            metadata={"qa_state": "answer", "qa_group_id": "g1"},
        ),
    ]


def test_production_convention_still_excludes_the_shadow_role():
    """The decision must agree with the existing production selector, not invent a rule."""
    from company_wiki.source_catalog.narrative_candidates import _EXCLUDED_ROLES

    assert QA_SHADOW_ROLE in _EXCLUDED_ROLES


def test_both_copies_reach_the_observation():
    """Neither side may be deleted: the structure lane needs both to pair Q and A."""
    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    roles = [unit["role"] for unit in observation["units"]]
    assert roles.count(QA_SHADOW_ROLE) == 2
    assert "investor_question" in roles
    assert "management" in roles


def test_shadow_units_are_marked_on_the_wire():
    """A consumer must not have to know the parser's internal role name."""
    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    shadow = [u for u in observation["units"] if u["role"] == QA_SHADOW_ROLE]
    assert shadow, "the sample must contain shadow units"
    for unit in shadow:
        assert unit["hints"].get(QA_SHADOW_HINT) is True


def test_structured_units_are_not_marked_as_shadow():
    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    for unit in observation["units"]:
        if unit["role"] in QA_STRUCTURED_ROLES:
            assert unit["hints"].get(QA_SHADOW_HINT) is not True


def test_shadow_is_not_selectable_but_structured_is():
    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    by_id = {unit["unit_id"]: unit for unit in observation["units"]}
    assert is_selectable(by_id["s1"]) is False
    assert is_selectable(by_id["q1"]) is True
    assert is_selectable(by_id["a1"]) is True


def test_selectable_ids_exclude_the_shadow_copy_only():
    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    assert set(selectable_unit_ids(observation)) == {"q1", "a1"}


def test_shadow_units_stay_visible_to_the_structure_lane():
    """Excluding from selection is not deletion: structure must still see every unit."""
    from company_wiki.document_understanding.structure import build_structure

    observation = build_observation(
        _qa_page_units(), source_id="s", source_sha256="d", language="zh"
    )
    structure = build_structure(observation)
    members: set[str] = set()
    for semantic in structure["semantic_units"]:
        members.update(semantic["member_unit_ids"])
    covered = members | set(structure["coverage"].get("unassigned_unit_ids", ()))
    assert {"s1", "s2", "q1", "a1"} <= covered, (
        "the structure lane must not drop either Q&A copy"
    )


def test_a_page_without_qa_markers_marks_nothing():
    units = [_Unit("u1", "公司持续保持市场领先地位。", role="company_filing")]
    observation = build_observation(units, source_id="s", source_sha256="d", language="zh")
    assert all(unit["hints"].get(QA_SHADOW_HINT) is not True for unit in observation["units"])
    assert selectable_unit_ids(observation) == ["u1"]
