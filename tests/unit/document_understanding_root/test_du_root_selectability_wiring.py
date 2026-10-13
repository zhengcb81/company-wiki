"""ROOT: the selectability decision must be APPLIED, not merely declared.

A regression lock for a defect found by auditing this layer's own work: the Q&A shadow
marking existed, and ``is_selectable`` existed, but **nothing consumed either**. That is the
same "no-op integration" failure this layer exists to remove -- a decision that looks
implemented because it has tests, while the code paths that matter never consult it.

Two consumers were affected, both reachable on a real Q&A original:

1. ``selection_bridge.dependency_closure`` may *add* a shadow unit back as required context
   or as negation protection, even though selection deliberately excluded it. The shadow
   duplicates the structured answer, so the negation would then appear twice.
2. ``summary_input.build_summary_input`` materialised shadow members into the model-facing
   evidence, handing the model both copies of every answer and wasting budget on the
   duplicate.

The rule the tests below enforce: a non-selectable unit is never *added* by this layer and
never *sent* to a model, but it is never *removed* from the observation or from a package's
membership either -- the structure lane still needs both copies to pair questions with
answers.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import (  # noqa: E402
    build_summary_input,
    understand_units,
)
from company_wiki.document_understanding.observation_adapter import (  # noqa: E402
    QA_SHADOW_ROLE,
)
from company_wiki.document_understanding.selection_bridge import (  # noqa: E402
    dependency_closure,
)


class _Coords:
    def __init__(self, page=1):
        self.page_number = page
        self.row_index = None
        self.table_index = None
        self.column_index = None


class _Unit:
    def __init__(self, unit_id, text, *, role, page=1, metadata=None):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = "pdf_text_block"
        self.source_role = role
        self.language = "zh"
        self.coordinates = _Coords(page)
        self.metadata = {"source_locator": f"loc:v1/page:{page}/paragraph:{unit_id}"}
        if metadata:
            self.metadata.update(metadata)


def _negated_qa_page():
    """A Q&A page where the answer contains a real negation (the 万润 '不生产VC' shape).

    Both copies of the negated answer are present, exactly as the parser emits them.
    """
    answer = "答：您好，公司现无生产VC（碳酸亚乙烯酯）的情况。"
    question = "问：公司有没有VC的带量采购业务？"
    return [
        _Unit("s_q", question, role=QA_SHADOW_ROLE, page=3),
        _Unit("s_a", answer, role=QA_SHADOW_ROLE, page=3),
        _Unit(
            "q1",
            question,
            role="investor_question",
            page=3,
            metadata={"qa_state": "question", "qa_group_id": "g1"},
        ),
        _Unit(
            "a1",
            answer,
            role="management",
            page=3,
            metadata={"qa_state": "answer", "qa_group_id": "g1"},
        ),
    ]


def _pipeline():
    return understand_units(
        _negated_qa_page(),
        source_id="s",
        source_sha256="d",
        title="投资者关系活动记录表",
        declared_kind="investor_relations",
        language="zh",
    )


# --- consumer 1: the selection bridge must not re-add a shadow unit --------------------
#
# These test the bridge's *contract* with an explicit packages fixture rather than relying
# on whatever shape the structure lane happens to produce, so the contract is pinned even
# if the upstream grouping changes.


def _mixed_packages():
    """A package that mixes structured roles with the shadow copy of the same answer.

    This is the real shape: the structure lane groups by section, so a Q&A package holds
    both the structured question/answer and the text-layer duplicates.
    """
    return {
        "schema_version": "du-packages/1",
        "packages": [
            {
                "package_id": "m1",
                "kind": "qa_exchange",
                "section_role": "questions",
                "section_ids": [],
                "member_unit_ids": ["q1", "a1", "s_q", "s_a"],
                "anchor_unit_ids": ["q1"],
                "required_context_unit_ids": ["a1", "s_a"],
                "completeness": "complete",
                "diagnostics": [],
                "truncated": False,
                "priority": 3,
                "first_ordinal": 0,
            }
        ],
    }


def _mixed_texts():
    return {
        "q1": "问：公司有没有VC的带量采购业务？",
        "a1": "答：您好，公司现无生产VC（碳酸亚乙烯酯）的情况。",
        "s_q": "问：公司有没有VC的带量采购业务？",
        "s_a": "答：您好，公司现无生产VC（碳酸亚乙烯酯）的情况。",
    }


def test_dependency_closure_does_not_add_a_shadow_unit_as_context():
    """A shadow unit must not come back in through required context."""
    observation = _pipeline()["observation"]
    by_id = {u["unit_id"]: u for u in observation["units"]}

    closure = dependency_closure(["q1"], _mixed_packages(), _mixed_texts())
    added_roles = [by_id[unit_id].get("role") for unit_id in closure["added_unit_ids"]]
    assert QA_SHADOW_ROLE not in added_roles, (
        f"the closure added a non-selectable shadow unit: {closure['added_unit_ids']}"
    )


def test_dependency_closure_does_not_add_a_shadow_unit_for_negation():
    """Negation protection must not reintroduce the duplicate answer.

    ``s_a`` carries the real negation, so a closure that ignores selectability will pull it
    in and the model then sees the same "无生产" statement twice.
    """
    observation = _pipeline()["observation"]
    by_id = {u["unit_id"]: u for u in observation["units"]}

    closure = dependency_closure(["q1"], _mixed_packages(), _mixed_texts())
    for unit_id in closure["added_unit_ids"]:
        assert by_id[unit_id].get("role") != QA_SHADOW_ROLE, (
            "negation protection pulled in the shadow copy of the answer"
        )


def test_dependency_closure_still_protects_the_negation_through_a_selectable_unit():
    """Skipping the shadow must not lose negation protection altogether."""
    closure = dependency_closure(["q1"], _mixed_packages(), _mixed_texts())
    assert "a1" in closure["added_unit_ids"], (
        "the structured answer carries the same negation and must still be protected"
    )


def test_dependency_closure_reports_that_it_withheld_a_unit():
    """A withheld unit is stated, so the gap is visible rather than silent."""
    closure = dependency_closure(["q1"], _mixed_packages(), _mixed_texts())
    codes = {item["code"] for item in closure["diagnostics"]}
    assert "NOT_SELECTABLE_WITHHELD" in codes


def test_dependency_closure_still_never_removes_what_the_caller_selected():
    """The bridge's original contract is unchanged: it only ever adds."""
    closure = dependency_closure(["s_a"], _mixed_packages(), _mixed_texts())
    assert "s_a" in closure["selected_unit_ids"]


# --- consumer 2: the summary request must not send a shadow unit ------------------------


def test_summary_input_excludes_shadow_members_from_evidence():
    """The model must not receive both copies of the same answer."""
    request = build_summary_input(_pipeline())
    roles = [
        member["role"]
        for package in request["evidence_packages"]
        for member in package["members"]
    ]
    assert QA_SHADOW_ROLE not in roles, "a shadow unit was sent as evidence"


def test_summary_input_reports_what_it_excluded():
    """An exclusion must be stated, so it cannot be mistaken for absent content."""
    request = build_summary_input(_pipeline())
    assert request.get("excluded", {}).get("not_selectable", 0) > 0, (
        "the request must report how many units it withheld as duplicates"
    )


def test_summary_input_keeps_the_structured_answer():
    """Excluding the duplicate must not lose the answer itself."""
    request = build_summary_input(_pipeline())
    texts = [
        member["text"]
        for package in request["evidence_packages"]
        for member in package["members"]
    ]
    assert any("无生产VC" in text for text in texts), "the real answer must survive"


def test_a_package_of_only_shadow_units_is_deferred_not_silently_empty():
    """If nothing selectable remains, say so instead of emitting an empty package."""
    result = _pipeline()
    tampered = {
        **result,
        "packages": {
            **result["packages"],
            "packages": [
                {
                    "package_id": "shadow-only",
                    "kind": "qa_exchange",
                    "section_role": "questions",
                    "section_ids": [],
                    "member_unit_ids": ["s_q", "s_a"],
                    "anchor_unit_ids": ["s_a"],
                    "required_context_unit_ids": ["s_a"],
                    "completeness": "complete",
                    "diagnostics": [],
                    "truncated": False,
                    "priority": 3,
                    "first_ordinal": 0,
                }
            ],
        },
    }
    request = build_summary_input(tampered)
    assert request["evidence_packages"] == []
    reasons = {item["reason"] for item in request["deferred"]}
    assert "NOT_SELECTABLE" in reasons


# --- and the whole chain still works ---------------------------------------------------


def test_the_whole_chain_still_produces_usable_evidence():
    request = build_summary_input(_pipeline())
    assert request["evidence_packages"], "the Q&A page must still yield evidence"
    assert request["budget"]["chars_used"] > 0
    assert request["profile_id"] == "investor_qa"
