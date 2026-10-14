"""Behavior contracts for the new production ReadingPlan selection path.

These tests use canonical source units and the public selector.  The DU port is
replaced only where a precise scope priority or dependency graph is needed;
format routing, canonical EvidenceSpan creation and the real budget still run.
Legacy selection remains independently replayable until the default switch.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.source_catalog import narrative_evidence as selector
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


SOURCE_SHA = "a" * 64
SOURCE_ID = source_id_for_sha256(SOURCE_SHA)
NEW_VERSION = "0.9.0"


@pytest.fixture(scope="module", autouse=True)
def isolated_originals_and_config_guard():
    """Restore owned temporary material even when a RED assertion fails."""
    config = Path(__file__).resolve().parents[3] / "config" / "source_catalog.yaml"

    def snapshot(path):
        return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns, path.stat().st_size

    config_before = snapshot(config) if config.is_file() else None
    with TemporaryDirectory(prefix="cw-reading-production-", dir=Path(__file__).parent) as directory:
        root = Path(directory)
        original = root / "original.txt"
        sentinel = root / "preexisting-sentinel.bin"
        original.write_bytes(b"immutable original document fixture\n")
        sentinel.write_bytes(b"retain preexisting byte sequence\x00\xff")
        before = {path: snapshot(path) for path in (original, sentinel)}
        try:
            yield root
        finally:
            for path, expected in before.items():
                assert snapshot(path) == expected, f"original fixture changed: {path.name}"
            if config_before is not None:
                assert snapshot(config) == config_before, "production source config changed"


def _unit(text, *, page=1, paragraph=0, kind="pdf_text_block", role="company_filing", language="en"):
    return selector._make_unit(
        source_id=SOURCE_ID,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language=language,
        metadata={},
    )


def _document(*units, opaque=(), language="en"):
    pages = max((unit.coordinates.page_number or 1 for unit in units), default=1)
    return DocumentStructure(
        source_id=SOURCE_ID,
        source_sha256=SOURCE_SHA,
        language=language,
        units=tuple(units),
        page_count=pages,
        pages_read=pages - len(opaque),
        opaque_pages=tuple(opaque),
    )


def _select(parsed, *, limit=96, title="Annual report", existing_kind="annual_report", version=NEW_VERSION):
    return selector.select_narrative_evidence(
        parsed,
        title=title,
        existing_kind=existing_kind,
        max_selected=limit,
        selector_version=version,
    )


def _texts(package):
    return {span.raw_text for span in package.evidence_spans}


def _reading_port():
    assert importlib.util.find_spec("company_wiki.source_catalog.narrative_reading") is not None, (
        "Phase A RED: the production ReadingPlan adapter has not been connected"
    )
    return importlib.import_module("company_wiki.source_catalog.narrative_reading")


def _package(package_id, anchor, *, context=(), kind="paragraph_event"):
    return {
        "package_id": package_id,
        "kind": kind,
        "section_ids": [],
        "section_role": "business",
        "member_unit_ids": [anchor.unit_id, *(unit.unit_id for unit in context)],
        "anchor_unit_ids": [anchor.unit_id],
        "required_context_unit_ids": [unit.unit_id for unit in context],
        "completeness": "complete",
        # This is an intentionally stale orchestration hint. Selection must use
        # the actual scope's ReadingPlan, not start another package ranker.
        "priority": 2,
        "first_ordinal": 0,
        "truncated": False,
        "diagnostics": [],
    }


def _patch_reading(monkeypatch, parsed, *, packages=None, priorities=None):
    """Return a real DU shape with only the assigned test seam changed."""
    pipeline = understand_units(
        parsed.units,
        source_id=parsed.source_id,
        source_sha256=parsed.source_sha256,
        title="Annual report",
        declared_kind="annual_report",
        language=parsed.language,
        native_scan="complete" if parsed.coverage_complete else "partial",
        opaque_pages=parsed.opaque_pages,
    )
    if packages is not None:
        pipeline["packages"]["packages"] = deepcopy(packages)
        pipeline["packages"]["package_count"] = len(packages)
        pipeline["packages"]["coverage"]["complete"] = parsed.coverage_complete
        pipeline["structure"]["semantic_units"] = [
            {"semantic_id": row["package_id"], **deepcopy(row)} for row in packages
        ]
    for uid, priority in (priorities or {}).items():
        # The map is source-unit scoped, including child scopes. No source text
        # or package ordering changes when this policy priority changes.
        profile = pipeline["reading_plan"]["unit_profiles"][uid]
        profile.update(priority=priority, section_role="business", family="annual")
    calls = []

    def supplied(actual_units, **kwargs):
        assert tuple(unit.unit_id for unit in actual_units) == tuple(unit.unit_id for unit in parsed.units)
        assert kwargs["source_id"] == parsed.source_id
        assert kwargs["source_sha256"] == parsed.source_sha256
        calls.append(tuple(unit.unit_id for unit in actual_units))
        return deepcopy(pipeline)

    monkeypatch.setattr(_reading_port(), "understand_units", supplied)
    return pipeline, calls


def _groups(package):
    context = getattr(package, "reading_context", None)
    assert isinstance(context, dict), "production evidence must carry compact final reading context"
    groups = context.get("groups")
    assert isinstance(groups, list), "reading groups must reference selected canonical span IDs"
    selected_ids = {span.span_id for span in package.evidence_spans}
    assert all(isinstance(row.get("evidence_ids"), list) and row["evidence_ids"] for row in groups)
    assert all(set(row["evidence_ids"]) <= selected_ids for row in groups)
    assert {sid for row in groups for sid in row["evidence_ids"]} == selected_ids
    return context, groups


def _shared_projects():
    header = _unit("Project | stage | qualification period", page=1)
    footnote = _unit("The stated periods are plans, not completed delivery dates.", page=1, paragraph=1)
    first = _unit("Alpha water treatment project is in customer qualification; the planned period is 2–7 months.",
                  page=2)
    second = _unit("Beta recycling project is in customer qualification; the planned period is 12–18 months.",
                   page=3)
    return header, footnote, first, second


def test_new_production_path_does_not_invoke_legacy_topic_admission(monkeypatch):
    def prohibited(*_args, **_kwargs):
        raise AssertionError("0.9.0 invoked a historical topic admission/window rule")

    monkeypatch.setattr(selector, "_base_candidates", prohibited)
    monkeypatch.setattr(selector, "_pdf_context_groups", prohibited)
    monkeypatch.setattr(selector, "_minimal_matching_unit_windows", prohibited)
    unit = _unit("Our water-treatment service expanded to a second operating region.")
    selected = _select(_document(unit))
    assert unit.raw_text in _texts(selected)
    assert selected.source_id == SOURCE_ID
    assert selected.source_sha256 == SOURCE_SHA


@pytest.mark.parametrize("duration", ("2–7个月", "12–18个月"))
def test_general_project_qualification_period_is_selected_without_four_to_nine_month_rule(duration):
    unit = _unit(f"公司新建水处理产线目前正在进行客户认证，预计客户认证需{duration}，尚未开始商业交付。", language="zh")
    selected = _select(_document(unit, language="zh"), title="首次公开发行招股说明书.pdf", existing_kind="prospectus")
    assert _texts(selected) == {unit.raw_text}
    assert selected.evidence_spans[0].raw_text.endswith("尚未开始商业交付。")


def test_actual_source_scope_priority_changes_production_selection(monkeypatch):
    first = _unit("Our water-treatment service expanded to a second operating region.", page=1)
    child = _unit("Our recycling service expanded to a third operating region.", page=2)
    document = _document(first, child)
    packages = [_package("first-scope", first), _package("child-scope", child)]
    pipeline, calls = _patch_reading(monkeypatch, document, packages=packages,
                                    priorities={first.unit_id: 1, child.unit_id: 3})
    before = _select(document, limit=1)
    assert _texts(before) == {first.raw_text}
    pipeline["reading_plan"]["unit_profiles"][first.unit_id]["priority"] = 3
    pipeline["reading_plan"]["unit_profiles"][child.unit_id]["priority"] = 1
    after = _select(document, limit=1)
    assert _texts(after) == {child.raw_text}
    assert len(calls) == 2, "each public selection runs the shared engine once"


def test_fixed_topic_and_four_to_nine_month_text_get_no_reserved_slot(monkeypatch):
    historical = _unit("公司集成中心的客户认证周期预计为4–9个月。", page=1, language="zh")
    important = _unit("公司新建水处理产线进入客户认证，预计认证需12–18个月，尚未商业交付。", page=2, language="zh")
    document = _document(historical, important, language="zh")
    _patch_reading(monkeypatch, document,
                   packages=[_package("old-topic", historical), _package("important", important)],
                   priorities={historical.unit_id: 3, important.unit_id: 1})
    assert _texts(_select(document, limit=1)) == {important.raw_text}


def test_two_projects_share_context_once_and_keep_two_independent_groups(monkeypatch):
    header, footnote, first, second = _shared_projects()
    document = _document(header, footnote, first, second)
    rows = [_package("alpha", first, context=(header, footnote), kind="project"),
            _package("beta", second, context=(header, footnote), kind="project")]
    _patch_reading(monkeypatch, document, packages=rows,
                   priorities={first.unit_id: 1, second.unit_id: 1})
    selected = _select(document, limit=4)
    assert _texts(selected) == {unit.raw_text for unit in document.units}
    assert len(selected.evidence_spans) == 4
    assert selected.selected_text_bytes == sum(len(unit.raw_text.encode()) for unit in document.units)
    context, groups = _groups(selected)
    assert len(groups) == 2
    assert all(len(row["evidence_ids"]) == 3 for row in groups)
    by_text = {span.raw_text: span.span_id for span in selected.evidence_spans}
    assert set(groups[0]["evidence_ids"]) & set(groups[1]["evidence_ids"]) == {
        by_text[header.raw_text], by_text[footnote.raw_text]
    }
    assert selected.candidate_count >= len(selected.evidence_spans)
    assert selected.omitted_candidate_count == selected.candidate_count - len(selected.evidence_spans)
    encoded = json.dumps(context, ensure_ascii=False, sort_keys=True)
    assert all(unit.raw_text not in encoded for unit in document.units), "compact policy/group context must not duplicate raw text"


def test_shared_context_does_not_force_both_projects_into_a_giant_budget_group(monkeypatch):
    header, footnote, first, second = _shared_projects()
    document = _document(header, footnote, first, second)
    _patch_reading(monkeypatch, document,
                   packages=[_package("alpha", first, context=(header, footnote), kind="project"),
                             _package("beta", second, context=(header, footnote), kind="project")],
                   priorities={first.unit_id: 1, second.unit_id: 2})
    selected = _select(document, limit=3)
    assert _texts(selected) == {header.raw_text, footnote.raw_text, first.raw_text}
    _, groups = _groups(selected)
    assert len(groups) == 1
    assert len(groups[0]["evidence_ids"]) == 3
    assert selected.status == "partial"


def test_shared_original_context_is_charged_once_under_production_character_limit(monkeypatch):
    _, footnote, first, second = _shared_projects()
    header = _unit("Unit and reporting period: " + "auxiliary qualification context " * 900)
    document = _document(header, footnote, first, second)
    _patch_reading(monkeypatch, document,
                   packages=[_package("alpha", first, context=(header, footnote), kind="project"),
                             _package("beta", second, context=(header, footnote), kind="project")],
                   priorities={first.unit_id: 1, second.unit_id: 1})
    unique_chars = sum(len(unit.raw_text) for unit in document.units)
    # The production bound is 48,000 characters. This graph fits only if the
    # original shared header is charged once; two package materialisations do not.
    assert unique_chars < 48000 < unique_chars + len(header.raw_text)
    selected = _select(document, limit=4)
    assert len(selected.evidence_spans) == 4
    assert sum(len(span.raw_text) for span in selected.evidence_spans) == unique_chars
    _, groups = _groups(selected)
    assert len(groups) == 2


def test_unaffordable_required_context_defers_the_complete_project(monkeypatch):
    header, footnote, first, second = _shared_projects()
    document = _document(header, footnote, first, second)
    _patch_reading(monkeypatch, document,
                   packages=[_package("alpha", first, context=(header, footnote), kind="project")],
                   priorities={first.unit_id: 1})
    selected = _select(document, limit=2)
    assert not selected.evidence_spans, "an anchor without its mandatory header/qualification is a different claim"
    assert selected.status == "partial"
    assert selected.omitted_candidate_count > 0


def test_same_text_at_different_original_locators_stays_distinct(monkeypatch):
    text = "Customer qualification remains pending and commercial delivery has not started."
    first = _unit(text, page=1)
    second = _unit(text, page=2)
    document = _document(first, second)
    _patch_reading(monkeypatch, document,
                   packages=[_package("first-project", first), _package("second-project", second)],
                   priorities={first.unit_id: 1, second.unit_id: 1})
    selected = _select(document, limit=2)
    assert len(selected.evidence_spans) == 2
    assert len({span.span_id for span in selected.evidence_spans}) == 2
    assert {span.locator for span in selected.evidence_spans} == {unit.coordinates.locator() for unit in document.units}
    assert selected.selected_text_bytes == 2 * len(text.encode())
    _, groups = _groups(selected)
    assert len(groups) == 2


def test_readable_financial_only_quarter_allows_zero_derived_material():
    unit = _unit("营业收入：100万元；营业成本：70万元；每股收益：0.25元。", language="zh")
    selected = _select(_document(unit, language="zh"), title="2026年第一季度报告.pdf", existing_kind="quarterly_report")
    assert selected.status == "skipped_no_narrative"
    assert selected.coverage_complete is True
    assert not selected.evidence_spans
    assert selected.dropped_financial_count == 1


def test_unread_page_cannot_be_reported_as_financial_only_skip():
    unit = _unit("营业收入：100万元；营业成本：70万元；每股收益：0.25元。", page=2, language="zh")
    selected = _select(_document(unit, opaque=(1,), language="zh"),
                       title="2026年第一季度报告.pdf", existing_kind="quarterly_report")
    assert not selected.evidence_spans
    assert selected.coverage_complete is False
    assert selected.status in {"partial", "needs_review", "blocked"}


def test_business_change_in_financial_note_is_not_dropped_as_finance():
    unit = _unit("营业收入附注：由于海外经销渠道首次开始商业运营，公司新增两个交付地区；新渠道仍在客户认证中。", language="zh")
    selected = _select(_document(unit, language="zh"), title="2026年第一季度报告.pdf", existing_kind="quarterly_report")
    assert unit.raw_text in _texts(selected)
    assert selected.dropped_financial_count == 0


def test_investor_question_stays_context_and_negative_management_answer_keeps_its_role(monkeypatch):
    question = _unit("Investor: Has the recycling plant started commercial delivery?", role="investor_question")
    answer = _unit("Management: No. The plant remains in customer qualification; delivery has not started.",
                   paragraph=1, role="management")
    document = _document(question, answer)
    _patch_reading(monkeypatch, document,
                   packages=[_package("qa-one", answer, context=(question,), kind="qa_exchange")],
                   priorities={answer.unit_id: 1, question.unit_id: 1})
    selected = _select(document, limit=2, title="Investor call transcript", existing_kind="earnings_call_transcript")
    assert _texts(selected) == {question.raw_text, answer.raw_text}
    roles = {span.raw_text: span.structured_value["source_role"] for span in selected.evidence_spans}
    assert roles[question.raw_text] == "investor_question"
    assert roles[answer.raw_text] == "management"
    too_small = _select(document, limit=1, title="Investor call transcript", existing_kind="earnings_call_transcript")
    assert not too_small.evidence_spans
    assert too_small.status == "partial"


def test_selected_spans_preserve_original_coordinates_parser_and_text():
    unit = _unit("The service launch is planned for the next reporting period, not completed.", page=4, paragraph=7)
    before = replace(unit)
    selected = _select(_document(unit))
    assert _texts(selected) == {before.raw_text}
    span = selected.evidence_spans[0]
    assert span.coordinates == before.coordinates
    assert span.locator == before.coordinates.locator()
    assert (span.parser_name, span.parser_version) == (before.parser_name, before.parser_version)
    assert unit == before


def test_legacy_default_is_still_explicitly_replayable_before_rollout():
    unit = _unit("公司新产品已获得客户认证，报告期内开始批量交付。", language="zh")
    document = _document(unit, language="zh")
    default = selector.select_narrative_evidence(document, title="2025年年度报告.pdf")
    replay = _select(document, title="2025年年度报告.pdf", version="0.8.0")
    assert selector.NARRATIVE_SELECTOR_VERSION == "0.8.0"
    assert default == replay


def test_operating_qualification_footnote_is_context_not_a_sibling_project_anchor(monkeypatch):
    header, _, first, second = _shared_projects()
    qualification = _unit("Customer qualification remains pending and commercial delivery has not started.",
                          page=1, paragraph=1)
    document = _document(header, qualification, first, second)
    _patch_reading(monkeypatch, document,
                   packages=[_package("alpha", first, context=(header, qualification), kind="project"),
                             _package("beta", second, context=(header, qualification), kind="project")],
                   priorities={first.unit_id: 1, second.unit_id: 2})
    selected = _select(document, limit=3)
    assert _texts(selected) == {header.raw_text, qualification.raw_text, first.raw_text}, (
        "A required footnote with operating words must not become an anchor or connect sibling projects"
    )
    _, groups = _groups(selected)
    assert len(groups) == 1


@pytest.mark.parametrize("problem", ("missing_context", "truncated"))
def test_unusable_project_remains_in_deferred_accounting_alongside_a_complete_project(monkeypatch, problem):
    first = _unit("Our water-treatment service expanded to a second operating region.", page=1)
    second = _unit("Our recycling service expanded to a third operating region.", page=2)
    document = _document(first, second)
    broken = _package("unusable-project", second, kind="project")
    if problem == "missing_context":
        broken["required_context_unit_ids"] = ["urn:company-wiki:narrative-unit:sha256:" + "f" * 64]
    else:
        broken["truncated"] = True
    _patch_reading(monkeypatch, document,
                   packages=[_package("complete-project", first), broken],
                   priorities={first.unit_id: 1, second.unit_id: 1})
    selected = _select(document)
    assert _texts(selected) == {first.raw_text}
    assert selected.status == "partial", "An unprocessed project must not disappear into a fully selected result"
    assert selected.candidate_count >= 2
    assert selected.omitted_candidate_count >= 1
    assert any(row.get("package_id") == "unusable-project"
               for row in selected.reading_context["deferred"])


def test_real_structure_work_budget_stop_cannot_certify_financial_only_skip(monkeypatch):
    first = _unit("营业收入：100万元；营业成本：70万元；每股收益：0.25元。", language="zh")
    second = _unit("现金流量：40万元；净利润：30万元。", page=2, language="zh")
    document = _document(first, second, language="zh")
    observed = []

    def limited(actual_units, **kwargs):
        result = understand_units(actual_units, **kwargs, limits={"max_units": 1, "max_work_units": 1})
        observed.append(result)
        return result

    monkeypatch.setattr(_reading_port(), "understand_units", limited)
    selected = _select(document, title="2026年第一季度报告.pdf", existing_kind="quarterly_report")
    assert any(row.get("code") == "WORK_BUDGET_EXCEEDED" for row in observed[0]["diagnostics"])
    assert selected.status in {"partial", "needs_review", "blocked"}
    assert selected.coverage_complete is False


def test_large_actual_candidate_pool_keeps_all_three_important_late_scopes(monkeypatch):
    # This is a supplied ReadingPlan seam, not a parser/layout acceptance test.
    # All 20,000 canonical originals and actual per-unit policies are presented;
    # a bounded planner must first compare the complete candidate population.
    count = 20000
    units = tuple(_unit(f"Our product {index} service expanded to a new operating region during the reporting period.",
                        page=1 + index // 25, paragraph=index % 25) for index in range(count))
    document = _document(*units)
    pipeline = understand_units(units[:1], source_id=SOURCE_ID, source_sha256=SOURCE_SHA,
                               title="Annual report", language="en")
    pipeline["observation"] = build_observation(units, source_id=SOURCE_ID, source_sha256=SOURCE_SHA,
                                               title="Annual report", language="en")
    base = pipeline["reading_plan"]["unit_profiles"][units[0].unit_id]
    pipeline["reading_plan"]["unit_profiles"] = {
        unit.unit_id: {**base, "section_role": "business", "priority": 1 if index >= count - 3 else 3}
        for index, unit in enumerate(units)
    }
    rows = [_package(str(index), unit) for index, unit in enumerate(units)]
    pipeline["packages"].update(packages=rows, package_count=count)
    pipeline["structure"]["coverage"].update(complete=True, deferred_unit_ids=[], unassigned_unit_ids=[])
    pipeline["diagnostics"] = []
    monkeypatch.setattr(_reading_port(), "understand_units", lambda *_args, **_kwargs: pipeline)
    selected = _select(document, limit=3)
    assert _texts(selected) == {unit.raw_text for unit in units[-3:]}, (
        "Work spent comparing low-priority candidates must not prevent important actual late scopes from fitting"
    )
    assert selected.candidate_count == count
    assert selected.omitted_candidate_count == count - 3
    assert selected.status == "partial"
    assert len(json.dumps(selected.reading_context, ensure_ascii=False).encode()) < 64000, (
        "Deferred diagnostics must use bounded examples and exact totals, not persist the complete candidate inventory"
    )
