"""Phase A counterexamples for the existing public evidence-budget planner.

These tests exercise real BudgetItem objects and the production selector.  The
missing additive interface is asserted inside test bodies so the initial RED
run cannot break collection of other test packages.
"""

from __future__ import annotations

import builtins
import hashlib
from dataclasses import fields, replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from company_wiki.source_catalog import narrative_budget as budget


READING_POLICY = "reading_plan/1"
READING_FIELDS = {
    "reading_priority", "reading_topics", "required_item_ids", "is_context_only"
}


@pytest.fixture(scope="module", autouse=True)
def isolated_files_and_production_config_guard():
    """All owned scratch is temporary; production config and raw bytes stay put."""
    config = Path(__file__).resolve().parents[3] / "config" / "source_catalog.yaml"

    def snapshot(path: Path):
        return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns, path.stat().st_size

    config_before = snapshot(config) if config.is_file() else None
    with TemporaryDirectory(prefix="cw-reading-budget-", dir=Path(__file__).parent) as directory:
        root = Path(directory)
        original = root / "original.txt"
        sentinel = root / "preexisting-sentinel.bin"
        original.write_bytes(b"immutable original source fixture\n")
        sentinel.write_bytes(b"keep this preexisting byte sequence\x00\xff")
        before = {path: snapshot(path) for path in (original, sentinel)}
        try:
            yield root
        finally:
            for path, expected in before.items():
                assert snapshot(path) == expected, f"planner changed immutable fixture: {path.name}"
            if config_before is not None:
                assert snapshot(config) == config_before, "production source_catalog config changed"


def _item(
    item_id: str,
    *,
    page: int = 1,
    paragraph: int = 0,
    locator: str | None = None,
    group: str | None = None,
    text: str = "A source-owned operating statement.",
    priority: int = 2,
    topics: tuple[str, ...] = ("operations",),
    required: tuple[str, ...] = (),
    context_only: bool = False,
    reasons: tuple[str, ...] = ("specific_business_event",),
    score: int = 10,
) -> budget.BudgetItem[str]:
    missing = READING_FIELDS - {field.name for field in fields(budget.BudgetItem)}
    assert not missing, f"Phase A RED: BudgetItem lacks reading metadata: {sorted(missing)}"
    return budget.BudgetItem(
        item_id=item_id,
        group_id=group,
        page_key=("page", page),
        locator=locator or f"loc:v1/page:{page}/paragraph:{paragraph}",
        order_key=(page, paragraph),
        reasons=reasons,
        score=score,
        is_heading=False,
        payload=text,
        evidence_chars=len(text),
        reading_priority=priority,
        reading_topics=topics,
        required_item_ids=required,
        is_context_only=context_only,
    )


def _select(items, *, limit, **options):
    assert getattr(budget, "REPLAY_READING_BUDGET_POLICY", None) == READING_POLICY, (
        "Phase A RED: the additive reading_plan/1 policy is not exported"
    )
    return budget.select_budget_items(tuple(items), limit=limit, policy=READING_POLICY, **options)


def _ids(items):
    return {item.item_id for item in items}


def _shared_projects():
    header = _item("header", paragraph=0, text="Project | stage | period", context_only=True,
                   priority=1, score=1000)
    footnote = _item("footnote", paragraph=1, text="Amounts exclude tax; stages are planned.",
                     context_only=True, priority=1, score=1000)
    project_a = _item("project-a", paragraph=2, text="Alpha: qualification planned in 2–7 months.",
                      priority=1, topics=("alpha",), required=("header", "footnote"))
    project_b = _item("project-b", paragraph=3, text="Beta: qualification planned in 12–18 months.",
                      priority=1, topics=("beta",), required=("header", "footnote"))
    fallback = _item("fallback", page=9, priority=3, topics=("other",), text="Minor update.")
    return project_a, project_b, header, footnote, fallback


def test_reading_metadata_is_additive_with_neutral_defaults():
    available = {field.name: field for field in fields(budget.BudgetItem)}
    assert READING_FIELDS <= available.keys(), "Phase A RED: additive reading fields are missing"
    assert available["reading_priority"].default == 2
    assert available["reading_topics"].default == ()
    assert available["required_item_ids"].default == ()
    assert available["is_context_only"].default is False
    assert getattr(budget, "REPLAY_READING_BUDGET_POLICY", None) == READING_POLICY


def test_changing_only_the_reading_priority_changes_the_selected_scope():
    parent = _item("parent", page=1, priority=1, topics=("parent-business",))
    child = _item("child", page=2, priority=3, topics=("child-business",))
    unrelated = _item("unrelated", page=3, priority=3, topics=("other-business",))
    assert _ids(_select((parent, child, unrelated), limit=1)) == {"parent"}
    promoted = replace(child, reading_priority=1)
    demoted = replace(parent, reading_priority=3)
    assert _ids(_select((demoted, promoted, unrelated), limit=1)) == {"child"}
    assert _ids(_select((parent, child, replace(unrelated, reading_priority=4)), limit=1)) == {"parent"}


@pytest.mark.parametrize("duration", ("2–7 months", "12–18 months"))
@pytest.mark.parametrize("old_reserved_reason", (
    "downstream_center_certification_timeline", "downstream_business_extension"
))
def test_reading_priority_has_no_fixed_topic_or_four_to_nine_month_reservation(duration, old_reserved_reason):
    important = _item("important", page=2, priority=1, topics=("water-systems",),
                      text=f"Water-system customer qualification is planned in {duration}.",
                      reasons=("project_execution_timeline",), score=20)
    formerly_reserved = _item("old-special", page=1, priority=3, topics=("integration-center",),
                              text="Integration-center certification is planned in 4–9 months.",
                              reasons=(old_reserved_reason,), score=1000)
    assert _ids(_select((formerly_reserved, important), limit=1)) == {"important"}


def test_two_projects_share_context_once_in_both_span_and_character_cost():
    items = _shared_projects()
    expected = {"project-a", "project-b", "header", "footnote"}
    unique_chars = sum(item.evidence_chars for item in items if item.item_id in expected)
    selected = _select(items, limit=4, max_chars=unique_chars)
    assert _ids(selected) == expected
    assert len(selected) == len(_ids(selected)) == 4
    assert sum(item.evidence_chars for item in selected) == unique_chars
    assert {item.item_id for item in selected if not item.is_context_only} == {"project-a", "project-b"}


def test_shared_context_does_not_join_independent_projects_into_one_giant_group():
    selected = _select(_shared_projects(), limit=3)
    assert _ids(selected) == {"project-a", "header", "footnote"}
    assert len(selected) == 3


@pytest.mark.parametrize("budget_kind", ("spans", "characters"))
def test_transitive_dependency_closure_is_deferred_whole_when_it_cannot_fit(budget_kind):
    unit = _item("unit", text="Unit: thousand tonnes.", context_only=True)
    period = _item("period", text="Period: first half of 2026.", required=("unit",), context_only=True)
    anchor = _item("anchor", priority=1, text="Volume remained below plan.", required=("period",))
    fallback = _item("fallback", priority=3, text="Update.", topics=("unrelated",))
    options = {"limit": 2} if budget_kind == "spans" else {"limit": 4, "max_chars": 40}
    selected = _select((anchor, period, unit, fallback), **options)
    assert _ids(selected) == {"fallback"}


def test_group_members_and_their_dependencies_are_one_atomic_package():
    head = _item("group-head", group="one-assertion", priority=1, required=("qualification",))
    tail = _item("group-tail", paragraph=1, group="one-assertion", priority=1)
    qualification = _item("qualification", paragraph=2, context_only=True, text="Not commercially available yet.")
    fallback = _item("fallback", page=2, priority=3)
    assert _ids(_select((head, tail, qualification, fallback), limit=2)) == {"fallback"}
    assert _ids(_select((head, tail, qualification, fallback), limit=3)) == {
        "group-head", "group-tail", "qualification"
    }


def test_all_candidates_fit_still_rejects_an_incomplete_dependency_package():
    anchor = _item("anchor", priority=1, required=("missing-period",))
    assert _select((anchor,), limit=10) == ()
    rows = budget.budget_diagnostics((anchor,), limit=10, policy=READING_POLICY)
    assert rows and any("anchor" in row.item_ids for row in rows)


def test_all_candidates_fit_still_enforces_full_original_character_cost():
    caption = _item("caption", context_only=True, text="Periods and amounts are provisional.")
    anchor = _item("anchor", priority=1, text="Plant is planned, not commissioned.", required=("caption",))
    assert _select((anchor, caption), limit=10, max_chars=len(anchor.payload)) == ()
    exact = anchor.evidence_chars + caption.evidence_chars
    assert _ids(_select((anchor, caption), limit=10, max_chars=exact)) == {"anchor", "caption"}


def test_context_only_material_is_never_an_independent_value_anchor():
    context = _item("question", priority=1, score=10000, context_only=True,
                    reasons=("downstream_center_certification_timeline",),
                    text="Investor: has the project reached commercial delivery?")
    assert _select((context,), limit=10, max_chars=1000) == ()
    answer = _item("answer", page=2, priority=3, required=("question",),
                   text="Management: no, the project remains in qualification.")
    selected = _select((context, answer), limit=2)
    assert _ids(selected) == {"question", "answer"}
    assert next(item for item in selected if item.item_id == "answer").payload == answer.payload


def test_same_text_at_distinct_locators_is_not_merged_or_charged_once():
    text = "Customer qualification remains pending."
    first = _item("first", page=1, text=text, topics=("project-a",))
    second = _item("second", page=2, text=text, topics=("project-b",))
    both = _select((first, second), limit=2, max_chars=2 * len(text))
    assert _ids(both) == {"first", "second"}
    assert {item.locator for item in both} == {first.locator, second.locator}
    assert sum(item.evidence_chars for item in both) == 2 * len(text)
    one = _select((first, second), limit=2, max_chars=len(text))
    assert len(one) == 1


def test_repeated_topic_does_not_use_every_slot_before_independent_table_and_prose():
    repeated = tuple(_item(f"repeat-{index}", page=index + 1, priority=1,
                           topics=("same-product",), score=100)
                     for index in range(100))
    table = _item("supply-table", page=101, priority=1, score=20, topics=("supply",),
                  locator="loc:v1/page:101/table:0/row:1", text="Supplier lead time | 12 months")
    prose = _item("service-change", page=102, priority=1, score=20, topics=("service",),
                  text="Service coverage expanded to a new region.")
    selected = _select((*repeated, table, prose), limit=3)
    assert {"supply-table", "service-change"} <= _ids(selected)
    assert len(selected) == 3
    assert sum(item.item_id.startswith("repeat-") for item in selected) == 1


def test_reading_selection_is_stable_under_input_permutations():
    items = _shared_projects()
    expected = _select(items, limit=3)
    assert _select(tuple(reversed(items)), limit=3) == expected
    assert _select(items[::2] + items[1::2], limit=3) == expected


def test_work_budget_exhaustion_does_not_return_a_partial_dependency_package():
    contexts = tuple(_item(f"context-{index}", paragraph=index, context_only=True,
                           required=(f"context-{index + 1}",) if index < 9 else ())
                     for index in range(10))
    anchor = _item("anchor", priority=1, required=("context-0",))
    items = (anchor, *contexts)
    assert _select(items, limit=20, max_work_units=1) == ()
    rows = budget.budget_diagnostics(items, limit=20, policy=READING_POLICY, max_work_units=1)
    assert rows and "work_budget_exhausted" in {row.reason for row in rows}


def test_reading_planner_uses_only_supplied_metadata_and_original_cost(monkeypatch):
    items = _shared_projects()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("pure reading planner must not open any file")

    monkeypatch.setattr(builtins, "open", forbidden)
    assert _ids(_select(items, limit=4)) == {"project-a", "project-b", "header", "footnote"}


@pytest.mark.parametrize("policy", ("legacy", "semantic_coverage/1"))
def test_existing_policies_keep_their_historical_reserved_reason_replay(policy):
    def old_item(identifier, page, reason, score):
        return budget.BudgetItem(
            item_id=identifier, group_id=None, page_key=("page", page),
            locator=f"loc:v1/page:{page}/paragraph:0", order_key=(page, 0),
            reasons=(reason,), score=score, is_heading=False, payload=identifier,
            evidence_chars=len(identifier),
        )

    items = (
        old_item("ordinary", 1, "specific_business_event", 100),
        old_item("extension", 9, "downstream_business_extension", 1),
        old_item("risk", 2, "business_risk_or_constraint", 20),
    )
    selected = budget.select_budget_items(items, limit=2, policy=policy)
    assert tuple(item.item_id for item in selected) == ("extension", "risk")
