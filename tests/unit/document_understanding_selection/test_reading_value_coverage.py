"""Source-owned value and fair topical coverage in the single reading planner.

No files, provider, LLM, company vocabulary or raw payload classifier are used
by the planner. Small counterexamples preserve the 48K/96/2M production caps.
"""
from dataclasses import fields, replace
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import narrative_budget as budget
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import _budget_item
from company_wiki.source_catalog.narrative_semantic_coverage import coverage_signature
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

POLICY = "reading_plan/2"


def item(uid, order, *, value="meaningful_fact", priority=2, topics=("operations",),
         required=(), context=False, chars=100, score=10, group=None, signature=None):
    kwargs = {"value_band": value} if "value_band" in {field.name for field in fields(budget.BudgetItem)} else {}
    return budget.BudgetItem(item_id=uid, group_id=group, page_key=("page", 1),
        locator=f"loc:{uid}", order_key=(order,), reasons=(), score=score,
        is_heading=False, payload=object(), evidence_chars=chars,
        reading_priority=priority, reading_topics=topics, required_item_ids=required,
        is_context_only=context, coverage_signature=signature, **kwargs)


def plan(items, *, limit=2, **options):
    return budget.plan_budget_items(tuple(items), limit=limit, policy=POLICY, **options)


def ids(items):
    return {row.item_id for row in items}


def test_current_reading_policy_is_versioned_and_value_is_neutral_additive_metadata():
    assert budget.READING_BUDGET_POLICY == "reading_plan/3"
    assert budget.REPLAY_VALUE_READING_BUDGET_POLICY == POLICY
    assert "value_band" in {field.name for field in fields(budget.BudgetItem)}
    assert item("a", 0).value_band == "meaningful_fact"
    assert next(field for field in fields(budget.BudgetItem) if field.name == "value_band").default == "description"


@pytest.mark.parametrize("value", [None, 0, [], "scope", "made_up_fact"])
def test_value_band_must_be_source_owned_typed_metadata(value):
    with pytest.raises(ValueError, match="value_band"):
        plan((item("a", 0, value=value),))


def test_operating_fact_outranks_high_priority_scope_only_descriptions():
    descriptions = [item(f"description-{i}", i, value="description", priority=1, score=1000)
                    for i in range(12)]
    fact = item("mechanism", 20, priority=3, topics=("billing",), score=1)
    selected, _ = plan((*descriptions, fact), limit=1)
    assert ids(selected) == {fact.item_id}


def test_uncovered_actual_topic_survives_repeated_higher_priority_facts():
    repeated = [item(f"existing-{i}", i, priority=1) for i in range(12)]
    mechanism = item("new-mechanism", 20, priority=3, topics=("billing",))
    selected, _ = plan((*repeated, mechanism), limit=2)
    assert ids(selected) == {"existing-0", "new-mechanism"}


def test_multiple_labels_do_not_penalize_the_same_average_visit_count():
    seed = item("seed", 0, priority=1, topics=("supply", "billing"))
    rich = item("rich", 1, topics=("supply", "billing"))
    narrow = item("narrow", 2, topics=("supply",))
    selected, _ = plan((seed, rich, narrow), limit=2)
    assert ids(selected) == {"seed", "rich"}


def test_empty_topics_are_not_a_permanently_novel_category():
    seed = item("seed", 0, priority=1)
    unlabeled = item("unlabeled", 1, priority=1, topics=())
    mechanism = item("mechanism", 2, priority=2, topics=("billing",))
    selected, _ = plan((seed, unlabeled, mechanism), limit=2)
    assert ids(selected) == {"seed", "mechanism"}


def test_policy_priority_still_changes_selection_with_equal_value_and_novelty():
    a = item("a", 0, priority=1, topics=("a",))
    b = item("b", 1, priority=2, topics=("b",))
    assert ids(plan((a, b), limit=1)[0]) == {"a"}
    assert ids(plan((replace(a, reading_priority=3), b), limit=1)[0]) == {"b"}


def test_existing_conservative_repetition_hint_prefers_distinct_facts():
    repeated = coverage_signature("Our company product remains in customer qualification before commercial delivery to overseas customers.")
    distinct = coverage_signature("Our supplier contract restricts production capacity until the qualification work is complete.")
    assert budget.softly_repeats(repeated, repeated)
    a = item("first", 0, signature=repeated)
    b = item("duplicate", 1, signature=repeated)
    c = item("distinct", 2, signature=distinct)
    assert ids(plan((a, b, c), limit=2)[0]) == {"first", "distinct"}


def test_context_does_not_claim_fact_value_or_topical_coverage_and_costs_once():
    context = item("header", 9, context=True, priority=1, topics=("billing",), score=1000, chars=50)
    first = item("first", 0, priority=1, required=(context.item_id,), chars=100, score=20)
    second = item("second", 1, priority=3, required=(context.item_id,), topics=("billing",), chars=100)
    duplicate = item("duplicate", 2, priority=1, chars=100)
    selected, _ = plan((first, second, duplicate, context), limit=3, max_chars=250)
    assert ids(selected) == {"first", "second", "header"}
    assert sum(row.evidence_chars for row in selected) == 250


@pytest.mark.parametrize("cap", [1, 199])
def test_value_rank_does_not_shrink_atomic_closure_to_fit(cap):
    fact = item("fact", 0, required=("context",), chars=100)
    context = item("context", 1, context=True, chars=100)
    selected, diagnostics = plan((fact, context), limit=cap if cap == 1 else 2,
                                 max_chars=48000 if cap == 1 else cap)
    assert not selected
    assert diagnostics
    assert diagnostics[0].item_ids == ("fact",)


def test_twenty_thousand_descriptions_leave_late_fact_anchors_inside_existing_caps():
    items = tuple(item(f"description-{i}", i, value="description", priority=1, chars=100)
                  for i in range(19997)) + tuple(
        item(f"fact-{i}", 19997+i, priority=3, topics=(f"mechanism-{i}",), chars=500)
        for i in range(3))
    selected, diagnostics = plan(items, limit=96, max_chars=48000, max_work_units=2_000_000)
    assert {f"fact-{i}" for i in range(3)} <= ids(selected)
    assert len(selected) == len(ids(selected)) == 96
    assert sum(row.evidence_chars for row in selected) <= 48000
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_explicit_work_stop_keeps_all_members_of_emitted_group():
    items = tuple(item(f"unit-{i}", i, group=f"group-{i//10}") for i in range(20000))
    selected, diagnostics = plan(items, limit=96, max_chars=48000, max_work_units=50000)
    assert any(row.reason == "work_budget_exhausted" for row in diagnostics)
    assert all(sum(row.group_id == group for row in selected) == 10
               for group in {row.group_id for row in selected})


def test_real_shared_immutable_signature_prefix_cannot_exhaust_work_before_late_facts():
    # The production finalizer interns equal text signatures before calling the
    # planner. Validation/hash work for that same frozen metadata must be shared,
    # rather than charged four times for each separate original locator.
    from company_wiki.source_catalog.narrative_semantic_coverage import CoverageSignature

    signature = CoverageSignature(tuple(f"vocabulary-{i}" for i in range(50)), (), (), True)
    descriptions = tuple(item(f"description-{i}", i, value="description", priority=1,
                              signature=signature) for i in range(19997))
    facts = tuple(item(f"fact-{i}", 19997+i, priority=3, topics=(f"mechanism-{i}",))
                  for i in range(3))
    selected, diagnostics = plan((*descriptions, *facts), limit=96, max_chars=48000,
                                 max_work_units=2_000_000)
    assert ids(facts) <= ids(selected)
    assert len(selected) == 96 and len(ids(selected)) == 96
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_v1_reading_replay_retains_original_strict_priority_ranking():
    a = item("a", 0, priority=1)
    b = item("b", 1, priority=1)
    late = item("late", 2, priority=3, topics=("new",))
    selected, _ = budget.plan_budget_items((a, b, late), limit=2, policy="reading_plan/1")
    assert ids(selected) == {"a", "b"}
    assert ids(plan((a, b, late), limit=2)[0]) == {"a", "late"}


def test_legacy_and_semantic_do_not_consume_reading_value():
    a = item("a", 0, value="description")
    b = item("b", 1, value="meaningful_fact")
    for policy in (budget.LEGACY_BUDGET_POLICY, budget.SEMANTIC_BUDGET_POLICY):
        before = budget.plan_budget_items((a, b), limit=1, policy=policy)
        after = budget.plan_budget_items((replace(a, value_band="meaningful_fact"),
                                         replace(b, value_band="description")), limit=1, policy=policy)
        assert ids(before[0]) == ids(after[0]) == {"a"}
        assert before[1] == after[1]


@pytest.mark.parametrize("text", ["•", "4", "2026", "-", "…", "(4)", "12 / 24",
    "一", "二〇二六", "壹佰", "一、", "IV", "XII.", "Ⅳ", "(a)", "（b）"])
def test_scope_cannot_turn_punctuation_or_page_count_into_an_anchor(text):
    unit = SimpleNamespace(raw_text=text, source_role="company_filing", unit_kind="html_paragraph")
    assert not reading._admitted(unit, {"section_role": "business"}, "narrative")[0]


def source_candidates(texts, *, headings=(), kinds=None, table=False):
    source = source_id_for_sha256("b"*64)
    units = tuple(_make_unit(source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=i), raw_text=text,
        unit_kind=(kinds or {}).get(i, "html_paragraph"), source_role="company_filing", language="en", metadata={})
        for i, text in enumerate(texts))
    parsed = DocumentStructure(source, "b"*64, "en", units, line_count=len(units), mime_type="text/html")
    pipeline = {"reading_plan": {"unit_profiles": {unit.unit_id: {
        "section_role": "business", "priority": 1} for unit in units}},
        "structure": {"sections": [{"heading_unit_ids": [units[i].unit_id for i in headings]}]},
        "packages": {"packages": [{"package_id": f"p-{i}",
            "kind": "operating_table" if table else "narrative",
            "member_unit_ids": [unit.unit_id], "anchor_unit_ids": [unit.unit_id],
            "required_context_unit_ids": []} for i, unit in enumerate(units)]}}
    return units, reading._candidates(parsed, pipeline)


def test_observed_heading_alone_is_context_not_a_value_anchor():
    units, result = source_candidates(["A General Product Group", "Our software comes in several editions."], headings=(0,))
    candidates = result[0]
    assert units[0].unit_id not in {candidate.unit.unit_id for candidate in candidates}
    assert units[1].unit_id in {candidate.unit.unit_id for candidate in candidates}


def test_actual_operating_fact_and_scope_only_description_receive_different_bands():
    units, result = source_candidates(["Our service charges depend on actual resources consumed.",
                                      "Our software comes in several editions."])
    metadata = result[1]
    assert metadata[units[0].unit_id]["value_band"] == "meaningful_fact"
    assert metadata[units[1].unit_id]["value_band"] == "description"
    assert "business" not in metadata[units[0].unit_id]["topics"], "scope is not a factual topic"
    assert "business" in metadata[units[1].unit_id]["topics"]
    emitted = _budget_item(result[0][0], {}, reading._NEVER_HEADING, reading=metadata[units[0].unit_id])
    assert emitted.value_band == "meaningful_fact"


def test_qualified_operating_table_preserves_numeric_cells_and_their_context():
    source = source_id_for_sha256("c" * 64)
    units = tuple(_make_unit(source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(table_index=0, row_index=i, column_index=0),
        raw_text=text, unit_kind="html_table_cell", source_role="company_filing", language="en", metadata={})
        for i, text in enumerate(("Product shipments | thousand units | current period", "15")))
    parsed = DocumentStructure(source, "c" * 64, "en", units, mime_type="text/html")
    pipeline = {"reading_plan": {"unit_profiles": {unit.unit_id: {
        "section_role": "operating_metrics", "priority": 1} for unit in units}},
        "structure": {"sections": []}, "packages": {"packages": [{"package_id": "table",
            "kind": "operating_table", "member_unit_ids": [u.unit_id for u in units],
            "required_context_unit_ids": [units[0].unit_id]}]}}
    result = reading._candidates(parsed, pipeline)
    assert {candidate.unit.unit_id for candidate in result[0]} == {unit.unit_id for unit in units}
    assert result[1][units[1].unit_id]["value_band"] == "meaningful_fact"
    assert result[1][units[0].unit_id]["context_only"] is True


def test_current_budget_version_is_an_actual_inventory_dependency(monkeypatch):
    from company_wiki.document_understanding.decision_inventory import _versions

    assert _versions()["budget"] == budget.READING_BUDGET_POLICY == "reading_plan/3"
    monkeypatch.setattr(budget, "READING_BUDGET_POLICY", "reading_plan/future")
    assert _versions()["budget"] == "reading_plan/future"


def carrier_trace(mime, *, actual_frontend=True):
    from company_wiki.document_understanding import understand_units
    from company_wiki.document_understanding.decision_inventory import build_decision_trace

    source = source_id_for_sha256("d" * 64)
    unit = _make_unit(source_id=source, parser_version="1.0.0", metadata={},
        coordinates=EvidenceCoordinates(paragraph_index=0), raw_text="FORM 10-K. Our product services target industrial customers.",
        unit_kind="pdf_text_block" if mime == "application/pdf" else "html_paragraph",
        source_role="company_filing", language="en")
    metadata = {}
    if mime == "application/pdf" and actual_frontend:
        from company_wiki.source_catalog.narrative_pdf_layout import PDF_READING_LAYOUT_FEATURE_VERSION
        metadata["native_layout_frontend_version"] = PDF_READING_LAYOUT_FEATURE_VERSION
    pipeline = understand_units((unit,), source_id=source, source_sha256="d" * 64,
        mime_type=mime, declared_kind="annual_report", language="en", metadata=metadata)
    return build_decision_trace(pipeline)


def test_pdf_frontend_version_only_invalidates_actual_pdf_carriers(monkeypatch):
    from company_wiki.document_understanding.decision_inventory import current_decision_trace
    from company_wiki.source_catalog import narrative_pdf_layout as frontend

    pdf = carrier_trace("application/pdf")
    html = carrier_trace("text/html")
    assert pdf["versions"].get("pdf_frontend") == frontend.PDF_READING_LAYOUT_FEATURE_VERSION
    assert "pdf_frontend" not in html["versions"]
    assert current_decision_trace(pdf) == pdf and current_decision_trace(html) == html
    monkeypatch.setattr(frontend, "PDF_READING_LAYOUT_FEATURE_VERSION", "pdf-reading-layout/next")
    assert current_decision_trace(pdf) != pdf
    assert current_decision_trace(html) == html


def test_missing_actual_carrier_proof_cannot_recover_a_complete_pdf_dependency():
    from company_wiki.document_understanding.decision_inventory import current_decision_trace

    frozen = carrier_trace("application/pdf")
    frozen["components"] = [item for item in frozen["components"] if not item["component_id"].startswith("carrier|")]
    assert current_decision_trace(frozen)["inventory_complete"] is False


def test_conflicting_carrier_proofs_are_partial_instead_of_guessing_from_source_name():
    from company_wiki.document_understanding.decision_inventory import current_decision_trace

    pdf = carrier_trace("application/pdf")
    html = carrier_trace("text/html")
    pdf["components"].extend(item for item in html["components"] if item["component_id"].startswith("carrier|"))
    assert current_decision_trace(pdf)["inventory_complete"] is False


def test_actual_pdf_projection_version_only_invalidates_its_used_pdf_scope(monkeypatch):
    from company_wiki.document_understanding.decision_inventory import current_decision_trace
    from company_wiki.document_normalization import layout_snapshots

    pdf = carrier_trace("application/pdf")
    html = carrier_trace("text/html")
    assert pdf["versions"].get("pdf_projection") == layout_snapshots.FEATURE_VERSION
    assert "pdf_projection" not in html["versions"]
    monkeypatch.setattr(layout_snapshots, "FEATURE_VERSION", "du3-geometry/next")
    assert current_decision_trace(pdf) != pdf
    assert current_decision_trace(html) == html


def test_pdf_mime_alone_does_not_prove_the_native_frontend_was_used():
    trace = carrier_trace("application/pdf", actual_frontend=False)
    assert trace["inventory_complete"] is False
    assert "pdf_frontend" not in trace["versions"] and "pdf_projection" not in trace["versions"]


def test_missing_frozen_actual_frontend_proof_is_partial():
    from company_wiki.document_understanding.decision_inventory import current_decision_trace

    frozen = carrier_trace("application/pdf")
    frozen["components"] = [item for item in frozen["components"] if not item["component_id"].startswith("pdf-frontend-used|")]
    assert current_decision_trace(frozen)["inventory_complete"] is False


@pytest.mark.parametrize("missing", ["module", "version"])
def test_missing_pure_projection_component_cannot_claim_complete_pdf(monkeypatch, missing):
    from importlib import import_module
    from company_wiki.document_understanding import decision_inventory

    pdf = carrier_trace("application/pdf")
    html = carrier_trace("text/html")

    def actual_import(name):
        if name == "company_wiki.document_normalization.layout_snapshots":
            if missing == "module":
                raise ModuleNotFoundError("Missing geometry component", name=name)
            return SimpleNamespace()
        return import_module(name)

    monkeypatch.setattr(decision_inventory, "import_module", actual_import, raising=False)
    assert decision_inventory.current_decision_trace(pdf)["inventory_complete"] is False
    assert decision_inventory.current_decision_trace(html) == html


def test_marker_filter_does_not_remove_words_with_digits_or_roman_prefixes():
    for text in ("IV therapy services are provided to hospitals.", "Our 2026 product portfolio includes recycling systems.",
                 "一体化生产服务覆盖多个下游客户工序。"):
        unit = SimpleNamespace(raw_text=text, source_role="company_filing", unit_kind="html_paragraph")
        assert reading._admitted(unit, {"section_role": "business"}, "narrative")[0]


@pytest.mark.parametrize('text', ['Our 2026 product portfolio', '一体化生产服务'])
def test_noun_only_product_labels_are_readable_context_not_independent_summary_anchors(text):
    from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact, reading_financial_only
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    unit = SimpleNamespace(raw_text=text, source_role='company_filing', unit_kind='html_paragraph')
    fact = detect_reading_business_fact(unit.raw_text)
    use, reason = source_support_use(unit.raw_text, fact=fact, financial_only=reading_financial_only(unit.raw_text,fact))
    assert (use, reason) == ('context_only','no_independent_business_support')
    assert not reading._admitted(unit, {'section_role':'business'}, 'narrative')[0]
    assert unit.raw_text == text
