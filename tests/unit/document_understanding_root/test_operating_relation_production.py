"""Source-owned state consumption, native coordinates and one work owner."""
import importlib.util
from pathlib import Path

import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.operating_states import relations
from company_wiki.source_catalog import narrative_reading as reading


def native(bodies, **kwargs):
    path = Path(__file__).parents[1] / "document_understanding_selection/test_reading_native_carriers.py"
    spec = importlib.util.spec_from_file_location("state_native_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.source_fixture(bodies, **kwargs)


def observation(text):
    return {"schema_version": relations.OBSERVATION_SCHEMA, "unit_id": "u", "units": {
        "u": {"text": text, "parent_id": "source", "role": "management",
              "kind": "paragraph", "locator": "native:0"}}}


@pytest.mark.parametrize("text,activity", [
    ("如果客户认证通过，公司将交付ZX-9产品。", "shipment"),
    ("If customer qualification passes, the company will sign a supply contract.", "business_relationship"),
    ("If customer qualification succeeds, the company will deliver ZX-9 products.", "shipment"),
])
def test_fronted_condition_closes_over_dependent_comma_clause(text, activity):
    result = relations.detect_operating_relations(observation(text), work_budget=WorkBudget(100000))
    shipments = [r for r in result["relations"] if r["activity"] == activity]
    assert shipments
    assert all(r["stage"] == r["modality"] == "conditional" for r in shipments)
    assert all(any(text[ref["char_start"]:ref["char_end"]].lower().startswith(("如果", "if"))
                   for ref in r["qualifier_refs"]) for r in shipments)


@pytest.mark.parametrize("join", ["。", "；", "，但", ". However, "])
def test_condition_does_not_cross_independent_or_contrast_boundary(join):
    text = "如果客户认证通过" + join + "公司已交付ZX-9产品。"
    result = relations.detect_operating_relations(observation(text), work_budget=WorkBudget(100000))
    shipments = [r for r in result["relations"] if r["activity"] == "shipment"]
    assert shipments
    assert all(r["modality"] == "actual" for r in shipments)


@pytest.mark.parametrize("text,reason", [
    ("公司计划商业化新产品。", "operating_plan"),
    ("The company plans to commercialize new products.", "operating_plan"),
    ("如果客户认证通过，公司将交付ZX-9产品。", "operating_plan"),
    ("公司尚未量产ZX-9产品。", "operating_restriction"),
    ("已通过客户认证的供应商向公司提供设备。", "operating_other_party_state"),
    ("公司控股股东海岸公司与客户建立了联系，公司尚未签署供货合同。", "operating_other_party_state"),
])
def test_source_state_is_meaningful_without_inventing_issuer_progress(text, reason):
    parsed, pipeline = native([(text,)])
    candidates, _meta, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and candidates
    assert all("business_progress" not in c.topics for c in candidates)
    assert any(reason in c.reasons for c in candidates)


def test_actual_issuer_milestone_is_recalled():
    parsed, pipeline = native([("公司已量产ZX-9产品。",)])
    candidates, *_rest = reading._candidates(parsed, pipeline)
    assert candidates and "business_progress" in candidates[0].topics
    assert "operating_milestone" in candidates[0].reasons


@pytest.mark.parametrize("text,stage,modality,polarity", [
    ("The company has shipped ZX-9 products.", "current", "actual", "positive"),
    ("The company has not shipped ZX-9 products.", "current", "actual", "negative"),
    ("The company will deliver ZX-9 products.", "planned", "planned", "positive"),
    ("The company suspended shipments.", "suspended", "actual", "negative"),
])
def test_english_shipment_verb_group_is_not_silently_discarded(text, stage, modality, polarity):
    result = relations.detect_operating_relations(observation(text), work_budget=WorkBudget(100000))
    shipments = [r for r in result["relations"] if r["activity"] == "shipment"]
    assert shipments
    assert {(r["stage"], r["modality"], r["polarity"]) for r in shipments} == {(stage, modality, polarity)}
    assert all(text[ref["char_start"]:ref["char_end"]] for r in shipments for ref in r["predicate_refs"])


@pytest.mark.parametrize("text,topic", [
    ("公司产品包括精密传感器与控制器。", "core_business"),
    ("Our platform routes workloads across multiple models to reduce computing costs.", "core_business"),
    ("Industry export licensing requirements tightened.", "industry_dynamics"),
])
def test_independent_description_survives_empty_relation_result(text, topic):
    parsed, pipeline = native([(text,)])
    candidates, *_rest = reading._candidates(parsed, pipeline)
    assert candidates and topic in candidates[0].topics


def test_native_owner_is_detected_once_and_offsets_are_exact(monkeypatch):
    parsed, pipeline = native([("公司已量产ZX-9产", "品，但尚未签署供货合同。")])
    calls = []
    original = relations._clause_events
    def traced(view, scan, clause, text, budget):
        calls.append(view.text)
        return original(view, scan, clause, text, budget)
    monkeypatch.setattr(relations, "_clause_events", traced)
    budget = WorkBudget(100000)
    state = {}
    candidates, *_rest = reading._candidates(parsed, pipeline, work_budget=budget, _session_state=state)
    assert len(candidates) == 1 and candidates[0].unit.unit_kind == "pdf_native_range"
    session = state["session"]
    carrier = candidates[0].unit
    result = session.relations(carrier.unit_id)
    assert set(calls) == {"公司已量产ZX-9产品，但尚未签署供货合同。"}
    before = len(calls)
    assert session.fact(carrier.unit_id) is session.fact(carrier.unit_id)
    assert len(calls) == before and session.work_budget is budget
    assert set(session.results) == {carrier.unit_id}
    for relation in result["relations"]:
        for field in ("assertion_refs", "predicate_refs", "qualifier_refs"):
            for ref in relation[field]:
                assert ref["unit_id"] == carrier.unit_id
                assert carrier.raw_text[ref["char_start"]:ref["char_end"]]
    assert any("尚未" in carrier.raw_text[r["char_start"]:r["char_end"]]
               for relation in result["relations"] for r in relation["qualifier_refs"])


def test_closed_continuity_without_page_view_maps_refs_to_all_original_members():
    parsed, pipeline = native([("公司已量产ZX-9产", "品，但尚未签署供货合同。")], proven=False)
    state = {}
    candidates, metadata, _packages, complete, withheld = reading._candidates(
        parsed, pipeline, work_budget=WorkBudget(100000), _session_state=state)
    assert complete and not withheld and len(candidates) == 2
    assert "_material_units" not in pipeline
    session = state["session"]
    ids = {u.unit_id for u in parsed.units}
    assert len(session.results) == 1
    assert session.fact(parsed.units[0].unit_id) is session.fact(parsed.units[1].unit_id)
    assert all(metadata[uid]["value_band"] == "meaningful_fact" for uid in ids)
    assert all(set(metadata[uid]["required"]) | {uid} == ids for uid in ids)
    texts = {u.unit_id: u.raw_text for u in parsed.units}
    for relation in session.relations(parsed.units[0].unit_id)["relations"]:
        for field in ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs"):
            for ref in relation[field]:
                assert ref["unit_id"] in ids
                assert texts[ref["unit_id"]][ref["char_start"]:ref["char_end"]]


def test_prepared_context_reused_but_same_text_different_parents_not_deduplicated(monkeypatch):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    first, _ = native([("公司已量产ZX-9产品。",), ("公司已量产ZX-9产品。",), ("股东海岸公司相关事项？",)])
    second, _ = native([("公司已量产ZX-9产品。",)], source_sha="d" * 64)
    sibling, question = first.units[1:]
    units = {u.unit_id: u for u in (*first.units, *second.units)}
    budget = WorkBudget(100000)
    session = SourceOperatingSession(units, work_budget=budget,
        contexts={first.units[0].unit_id: (question.unit_id,), sibling.unit_id: (question.unit_id,),
                  second.units[0].unit_id: (question.unit_id,)})
    views = []
    original = relations.build_matching_view
    def traced(text):
        views.append(text)
        return original(text)
    monkeypatch.setattr(relations, "build_matching_view", traced)
    for unit in (first.units[0], sibling, second.units[0]):
        assert session.fact(unit.unit_id).eligible
    assert views.count(question.raw_text) == 1
    assert views.count(first.units[0].raw_text) == 3
    assert any(d["code"] == "context_parent_mismatch"
               for d in session.relations(second.units[0].unit_id)["diagnostics"])


def test_zero_budget_does_not_run_matching_or_plain_detector(monkeypatch):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    parsed, _ = native([("公司已量产ZX-9产品。",)])
    def forbidden(*_args, **_kwargs):
        pytest.fail("work continued after exhaustion")
    monkeypatch.setattr(relations, "build_matching_view", forbidden)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=WorkBudget(0))
    assert not session.fact(parsed.units[0].unit_id).eligible
    assert not session.complete
    assert session.relations(parsed.units[0].unit_id)["status"] == "partial"


def test_partial_keeps_closed_states_and_does_not_restart_full_text_scan(monkeypatch):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog import narrative_business_policy as policy
    text = "公司现无生产VC。公司尚未量产ZX-9产品。公司计划商业化新产品。"
    parsed, _ = native([(text,), ("公司已量产其他产品。",)])
    generous = relations.detect_operating_relations(observation(text), work_budget=WorkBudget(100000))
    budget = WorkBudget(generous["work_used"] * 2 // 3)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=budget)
    def forbidden(_text):
        pytest.fail("partial result restarted the full text-only recognizer")
    monkeypatch.setattr(policy, "detect_reading_business_fact", forbidden)
    fact = session.fact(parsed.units[0].unit_id)
    assert budget.exhausted and not session.complete
    assert "operating_restriction" in fact.reasons
    assert session.relations(parsed.units[0].unit_id)["relations"]
    assert session.fact(parsed.units[0].unit_id) is fact
    assert not session.fact(parsed.units[1].unit_id).eligible


def test_real_select_uses_callers_one_balance_and_exhaustion_never_skips():
    parsed, _ = native([("公司计划商业化新产品。",)])
    budget = WorkBudget(0)
    result = reading.select_reading_evidence(parsed, title="2025 annual report", work_budget=budget)
    assert budget.exhausted and budget.used == 0
    assert result.status == "needs_review" and not result.coverage_complete


def test_actual_qa_keeps_question_as_context_and_denial_as_answer_support():
    path = Path(__file__).parents[1] / "document_understanding_selection/test_reading_structured_qa.py"
    spec = importlib.util.spec_from_file_location("state_qa_fixtures", path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    question = fixture._unit("公司是否已经量产ZX-9产品？", "investor_question", 0)
    answer = fixture._unit("公司尚未量产ZX-9产品。", "management", 1)
    selected = fixture._select(question, answer)
    assert {span.raw_text for span in selected.evidence_spans} == {question.raw_text, answer.raw_text}
    by_text = {span.raw_text: span.span_id for span in selected.evidence_spans}
    for group in selected.reading_context["groups"]:
        for view in group["citation_views"]:
            assert by_text[question.raw_text] not in view["support_evidence_ids"]
            assert by_text[answer.raw_text] in view["support_evidence_ids"]
            assert by_text[question.raw_text] in view["context_evidence_ids"]
