"""Source planning contracts: shared matcher, real probes and finite navigation."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from company_wiki.document_understanding.geometry_intent import reading
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded
from company_wiki.document_understanding.strategy_binding import SectionPolicyMatcher, bind_reading_plan


def rule(title, *, role="business", path=None, intent="operating"):
    return {"section_role": role, "aliases": [title], "heading_path": path or [[title]],
            "priority": 1, "geometry_intent": {
                "discover": "none" if role == "risk" else "on_tabular_evidence",
                "fine": "explicit_only" if role == "risk" else "on_candidate",
                "demand_class": intent}}


def profile(*rules, form="unknown"):
    return {"profile_id": "test", "profile_version": "1", "form_type": form,
            "section_rules": list(rules)}


@pytest.fixture
def routed(monkeypatch):
    selected = profile(rule("Business"), rule("Risks", role="risk", intent="context"),
                       rule("Projects", intent="project"))
    calls = []

    def observation(units, **kwargs):
        calls.append((tuple(units), kwargs))
        return {"units": [{"unit_id": u.unit_id, "text": u.raw_text} for u in units]}

    monkeypatch.setattr(reading, "build_observation", observation)
    monkeypatch.setattr(reading, "route_document", lambda o: {
        "profile_id": "test", "family": "annual", "confidence": "high", "form_type": "unknown"})
    monkeypatch.setattr(reading, "get_profile", lambda identity: selected if identity != "generic" else profile())
    monkeypatch.setattr(reading, "resolve_reading_profile", lambda base, o, r: deepcopy(base))
    return selected, calls


def unit(text="Actual cover annual report"):
    return SimpleNamespace(unit_id="original-unit", raw_text=text, metadata={},
                           source_id="source", source_role="company_filing", language="zh",
                           unit_kind="pdf_text_block", coordinates=SimpleNamespace(
                               page_number=1, table_index=None, row_index=None, column_index=None))


def prepare(outline, *, units=None, budget=None, pages=100, limits=None):
    return reading.prepare_geometry_reading(
        [unit()] if units is None else units, context=reading.PdfReadingContext(title="Annual report"),
        source_id="source", source_sha256="a" * 64, native_outline=outline, page_count=pages,
        limits=limits or {"max_pages": 64, "max_requests": 64},
        work_budget=budget if budget is not None else WorkBudget(2_000_000))


def codes(result):
    return {r["code"] for r in result["diagnostics"]}


def test_context_immutable():
    c = reading.PdfReadingContext()
    with pytest.raises(FrozenInstanceError):
        c.title = "changed"


def test_full_path_and_ascii_and_part_identity():
    p = profile(rule("Item 1. Business", path=[["Part I"], ["Item 1. Business"]]),
                rule("Item 1. Legal", path=[["Part II"], ["Item 1. Legal"]], role="risk"), form="10-K")
    m = SectionPolicyMatcher(p, WorkBudget(200_000))
    assert m.match(["Part I", "Item 1"])["section_role"] == "business"
    assert m.match(["Part II", "Item 1"])["section_role"] == "risk"
    assert m.match(["Part I", "Item 10"]) is None
    assert m.match(["Part I", "Item 1. Contrary title"]) is None
    assert any(d["code"] == "SECTION_TITLE_CONFLICT" for d in m.diagnostics)
    assert SectionPolicyMatcher(profile(rule("Risk")), WorkBudget(10000)).match(["Riskiness"]) is None


def test_matcher_shares_binding_owner_and_old_wire():
    p = profile(rule("Business"))
    structure = {"sections": [{"section_id": "s", "parent_id": None,
                              "heading_unit_ids": ["u"], "body_unit_ids": []}]}
    obs = {"units": [{"unit_id": "u", "text": "Business"}]}
    before = deepcopy(p)
    standalone = bind_reading_plan(obs, structure, route={}, profile=p)
    shared = bind_reading_plan(obs, structure, route={}, profile=p, work_budget=WorkBudget(200000))
    assert standalone == shared
    assert shared["unit_profiles"]["u"]["matched_section_rule"] == SectionPolicyMatcher(p, WorkBudget(200000)).match(["Business"])
    assert p == before


def test_matcher_zero_budget_before_material_copy():
    with pytest.raises(WorkBudgetExceeded):
        SectionPolicyMatcher(profile(rule("Business")), WorkBudget(0)).match(["Business"])


def test_outline_ancestry_and_physical_end(routed):
    selected, calls = routed
    result = prepare([[1, "Business", 10], [2, "Details", 12], [1, "Projects", 70]])
    assert len(calls) == 1 and calls[0][0][0].unit_id == "original-unit"
    assert result["resolved_profile"] == selected
    assert result["route"]["family"] == "annual"
    assert any(w["navigation_span"] == {"physical_start": 10, "physical_end": 69} for w in result["windows"])
    assert result["plan"]["summary"]["pages_reserved"] <= 64
    assert {w["scope_id"] for w in result["windows"]} == {"source"}
    assert not any("unit_id" in w.get("basis", {}) for w in result["windows"])


def test_navigation_detail_does_not_fragment_the_same_reading_quota(routed):
    outline = [[1, 'Business', 1]] + [[2, f'Detail {n}', n] for n in range(2, 81)]
    outline += [[1, 'Projects', 90]]
    result = prepare(outline, limits={'max_pages': 8, 'max_requests': 8})
    by_rule = {r['rule_key']: r for r in result['policy']['rules']}
    operating = [w for w in result['windows'] if
                 by_rule[w['rule_key']]['geometry_intent']['demand_class'] == 'operating']
    assert len(operating) == 1
    assert (operating[0]['physical_start'], operating[0]['physical_end']) == (1, 89)
    assert operating[0]['basis']['navigation_segment_count'] == 80
    allocation = next(a for a in result['plan']['allocations'] if a['window_key'] == operating[0]['window_key'])
    assert allocation['quota_pages'] >= 4


def test_adjacent_equal_rules_merge_but_never_across_explicit_risk(routed):
    result = prepare([[1, 'Business', 1], [2, 'Details', 2], [2, 'Risks', 5],
                      [2, 'Further details', 7], [2, 'Last details', 9], [1, 'Projects', 20]])
    by_rule = {r['rule_key']: r for r in result['policy']['rules']}
    business = [w for w in result['windows'] if by_rule[w['rule_key']]['section_role'] == 'business']
    assert [(w['physical_start'], w['physical_end']) for w in business] == [(1, 4), (7, 19), (20, 100)]
    assert not any(w['physical_start'] <= 5 <= w['physical_end'] for w in business)


def test_explicit_risk_child_is_not_washed_by_business_parent(routed):
    result = prepare([[1, "Business", 10], [2, "Risks", 20], [2, "Details", 30], [1, "Projects", 70]])
    rules = {r["rule_key"]: r for r in result["policy"]["rules"]}
    active = [w for w in result["windows"] if rules[w["rule_key"]]["section_role"] == "business"]
    assert active and not any(w["physical_start"] <= 25 <= w["physical_end"] for w in active)
    assert any(w["physical_start"] <= 35 <= w["physical_end"] for w in active)


def test_conflicting_bare_item_does_not_inherit_business(routed):
    routed[0]["form_type"] = "10-K"
    routed[0]["section_rules"] = [rule("Business"), rule("Item 1. Business"), rule("Item 1. Legal", role="risk", intent="context")]
    r = prepare([[1, "Business", 1], [2, "Item 1", 5]])
    assert "SECTION_NUMBER_AMBIGUOUS" in codes(r)
    assert not any(w["physical_start"] <= 10 <= w["physical_end"] for w in r["windows"])


@pytest.mark.parametrize("outline, code", [
    ([[1, "Business", -1]], "NAVIGATION_DESTINATION_INVALID"),
    ([[1, "Business", 101]], "NAVIGATION_DESTINATION_INVALID"),
    ([[1, "Business", True]], "NAVIGATION_DESTINATION_INVALID"),
    ([[3, "Business", 1]], "NAVIGATION_LEVEL_JUMP"),
    ([[1, "Business", 20], [1, "Projects", 10]], "NAVIGATION_OUT_OF_ORDER"),
    ([[1, "Business", 1, {"uri": "https://external"}]], "NAVIGATION_ENTRY_INVALID"),
    ([[1, "Business", 1], [34, "Projects", 5]], "NAVIGATION_LEVEL_INVALID"),
])
def test_invalid_navigation_reports_and_never_guesses(routed, outline, code):
    r = prepare(outline)
    assert code in codes(r)
    assert all(1 <= w["physical_start"] <= w["physical_end"] <= 100 for w in r["windows"])


def test_missing_outline_has_no_synthetic_windows(routed):
    r = prepare([])
    assert r["windows"] == [] and "NAVIGATION_MISSING" in codes(r)


def test_no_original_units_cannot_establish_profile(routed):
    r = prepare([[1, "Business", 1]], units=[])
    assert r["resolved_profile"]["section_rules"] == []
    assert "PROFILE_WITHOUT_ORIGINAL_PROBES" in codes(r)


def test_zero_budget_is_honest_partial_without_routing(routed):
    r = prepare([[1, "Business", 1]], budget=WorkBudget(0))
    assert routed[1] == []
    assert r["plan"]["summary"]["partial"] is True
    assert r["windows"] == [] and "READING_WORK_BUDGET_EXCEEDED" in codes(r)


def test_digest_changes_with_source_policy_navigation_and_limits(routed):
    base = prepare([[1, "Business", 10]])
    assert prepare([[1, "Business", 10]])["request_digest"] == base["request_digest"]
    assert prepare([[1, "Business", 11]])["request_digest"] != base["request_digest"]
    assert prepare([[1, "Business", 10]], limits={"max_pages": 2, "max_requests": 2})["request_digest"] != base["request_digest"]
    routed[0]["section_rules"][0]["geometry_intent"]["fine"] = "explicit_only"
    assert prepare([[1, "Business", 10]])["request_digest"] != base["request_digest"]


def test_limits_cannot_raise_native_hard_ceiling(routed):
    r = prepare([[1, "Business", 1]], limits={"max_pages": 1000, "max_requests": 1000})
    assert r["plan"]["limits"] == {"max_pages": 64, "max_requests": 64}


def test_large_outline_bounded_before_iteration(routed):
    r = prepare([[1, "Business", 1]] * 4100)
    assert "NAVIGATION_ENTRY_LIMIT" in codes(r)
    assert len(r["windows"]) <= 4096


def test_shared_page_conflict_excludes_ambiguous_physical_page(routed):
    result = prepare([[1, "Business", 1], [2, "Risks", 10], [2, "Details", 10]])
    assert "NAVIGATION_SHARED_PAGE_CONFLICT" in codes(result)
    assert not any(w["physical_start"] <= 10 <= w["physical_end"] for w in result["windows"])
    assert any(w["physical_start"] <= 11 <= w["physical_end"] for w in result["windows"])
    assert {'physical_start': 10, 'physical_end': 10} in result['blocked_navigation']


def test_unexplained_prefix_is_unknown_not_an_implicit_no_work_instruction(routed):
    result = prepare([[1, 'Business', 5]])
    assert result['unresolved_navigation'] == [{'physical_start': 1, 'physical_end': 4}]
    assert result['blocked_navigation'] == []


def test_mixed_operating_child_can_override_explicit_context_parent(routed):
    result = prepare([[1, "Risks", 1], [2, "Business", 10]])
    by_rule = {r['rule_key']: r for r in result['policy']['rules']}
    assert any(by_rule[w['rule_key']]['section_role'] == 'business' and
               w['physical_start'] == 10 for w in result['windows'])


def test_original_binding_actually_consumes_public_matcher_service(monkeypatch):
    called = []
    actual = SectionPolicyMatcher.match_section

    def observe(self, *args):
        called.append(self.profile)
        return actual(self, *args)

    monkeypatch.setattr(SectionPolicyMatcher, 'match_section', observe)
    p = profile(rule('Business'))
    bind_reading_plan({'units': [{'unit_id': 'u', 'text': 'Business'}]},
                      {'sections': [{'section_id': 's', 'parent_id': None,
                                     'heading_unit_ids': ['u'], 'body_unit_ids': []}]},
                      route={}, profile=p)
    assert called == [p]


def test_real_adapter_router_registry_policy_and_planner_compose():
    original = unit('宁德时代新能源科技股份有限公司 2025 年年度报告')
    result = prepare([[1, '第三节 管理层讨论与分析', 10], [2, '公司主要业务', 11]], units=[original])
    assert result['resolved_profile']['profile_id'] == 'cn_annual'
    assert result['policy']['rules'] and result['windows']
    assert result['partial'] is False
    assert original.unit_id == 'original-unit'


def test_real_empty_cover_stays_generic_despite_title():
    result = prepare([[1, '公司主要业务', 10]], units=[])
    assert result['resolved_profile']['profile_id'] == 'generic'
    assert all(r['geometry_intent']['demand_class'] == 'unknown' for r in result['policy']['rules'])


def test_mid_navigation_exhaustion_keeps_no_unbudgeted_windows(routed):
    probe = unit()
    initial = WorkBudget(2_000_000)
    prepare([], units=[probe], budget=initial)
    result = prepare([[1, 'Business', n] for n in range(1, 101)], budget=WorkBudget(initial.used + 10))
    assert result['partial'] is True and not result['windows']
    assert result['plan']['summary']['partial'] is True


def test_missing_budget_is_partial_and_does_not_read_probes(routed):
    result = reading.prepare_geometry_reading([unit()], context=reading.PdfReadingContext(),
        source_id='source', source_sha256='a' * 64, native_outline=[], page_count=1,
        limits={'max_pages': 2, 'max_requests': 2}, work_budget=None)
    assert result['partial'] and routed[1] == []


def test_real_catalog_same_page_ancestor_and_narrow_operating_child_keep_start():
    original = unit('某公司2025年年度报告')
    result = prepare([[1, '重要事项', 3], [1, '管理层讨论与分析', 75],
                      [2, '主要产品产销量', 75], [2, '产能', 79]], units=[original], pages=80)
    by_rule = {r['rule_key']: r for r in result['policy']['rules']}
    start = [w for w in result['windows'] if w['physical_start'] <= 75 <= w['physical_end']]
    assert len(start) == 1
    adopted = by_rule[start[0]['rule_key']]
    assert adopted['section_role'] == 'operating_metrics'
    assert len(adopted['heading_path']) == 2
    assert start[0]['basis']['outline_index'] == 2
    assert start[0]['navigation_span'] == {'physical_start': 75, 'physical_end': 78}
    assert 'NAVIGATION_SHARED_PAGE_CONFLICT' not in codes(result)


def test_same_page_equal_role_siblings_are_still_competing(routed):
    routed[0]['section_rules'] = [rule('Business'), rule('A', path=[['Business'], ['A']]),
                                  rule('B', path=[['Business'], ['B']])]
    result = prepare([[1, 'Business', 1], [2, 'A', 10], [2, 'B', 10]])
    assert 'NAVIGATION_SHARED_PAGE_CONFLICT' in codes(result)
    assert not any(w['physical_start'] <= 10 <= w['physical_end'] for w in result['windows'])


def test_same_page_risk_parent_cannot_be_promoted_by_operating_child(routed):
    routed[0]['section_rules'] = [rule('Risks', role='risk', intent='context'),
        rule('Business', path=[['Risks'], ['Business']])]
    result = prepare([[1, 'Risks', 10], [2, 'Business', 10]])
    assert 'NAVIGATION_SHARED_PAGE_CONFLICT' in codes(result)
    assert not any(w['physical_start'] <= 10 <= w['physical_end'] for w in result['windows'])
