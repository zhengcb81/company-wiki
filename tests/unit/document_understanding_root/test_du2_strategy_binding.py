"""Actual hierarchy binding, without company names or invented source ids."""
from copy import deepcopy
import json
from pathlib import Path

from company_wiki.document_understanding.strategy_binding import bind_reading_plan


def rule(role, aliases, path=(), priority=1, question="What changed?"):
    return {"role": role, "aliases": list(aliases), "heading_path": list(path),
            "priority": priority, "questions": [question]}


def profile(rules, *, name="sec_10q", version="p1", focus="operating changes"):
    return {"profile_id": name, "profile_version": version, "family": "quarterly",
            "section_rules": rules, "section_priorities": [
                {"section_role": r["role"], "aliases": r["aliases"], "priority": r["priority"]} for r in rules],
            "summary_focus": focus, "policy_components": [{"kind": "family", "id": name, "version": version, "content_digest": "opaque"}],
            "reading_questions": ["Current quarter versus YTD?"],
            "negative_hints": ["Do not infer missing business facts"],
            "semantic_units": ["paragraph_event", "project"],
            "family_policy": {"spec_status": "proposed", "evidence_status": "missing", "integration_status": "not_integrated"},
            "context_requirements": [{"when": "quantity_emitted", "slots": ["period", "unit"], "missing_behavior": "partial", "reason": "Period matters."}]}


def tree(nodes):
    units = []
    sections = []
    for i, (sid, parent, heading, body) in enumerate(nodes):
        units.extend([{"unit_id": sid + "h", "ordinal": i * 2, "text": heading, "locator": "opaque-heading-" + sid},
                      {"unit_id": sid + "b", "ordinal": i * 2 + 1, "text": body, "locator": "opaque-body-" + sid}])
        sections.append({"section_id": sid, "parent_id": parent, "heading_unit_ids": [sid + "h"],
                         "body_unit_ids": [sid + "b"], "section_role": "unknown"})
    return {"units": units}, {"sections": sections}


def bind(nodes, p):
    observation, structure = tree(nodes)
    return bind_reading_plan(observation, structure, route={}, profile=p)


def test_repeated_items_keep_the_part_scope_and_actual_rule_priority():
    p = profile([rule("financial_notes", ["Item 1"], [["PART I"], ["Item 1"]], 2),
                 rule("administrative", ["Item 1"], [["PART II"], ["Item 1"]], 3)])
    result = bind([("p1", None, "PART I", ""), ("f", "p1", "Item 1. Financial Statements", "financial explanation"),
                   ("p2", None, "PART II", ""), ("l", "p2", "Item 1. Legal Proceedings", "legal explanation")], p)
    assert result["unit_profiles"]["fb"]["section_role"] == "financial_notes"
    assert result["unit_profiles"]["fb"]["priority"] == 2
    assert result["unit_profiles"]["lb"]["section_role"] == "administrative"
    assert result["unit_profiles"]["lb"]["priority"] == 3


def test_part_i_alias_cannot_match_part_ii():
    p = profile([rule("business", ["Item 2"], [["PART I"], ["Item 2"]])])
    result = bind([("p2", None, "PART II", ""), ("i2", "p2", "Item 2. Business", "evidence")], p)
    assert result["unit_profiles"]["i2b"]["section_role"] == "unknown"


def test_item_one_cannot_match_item_one_a():
    p = profile([rule("financial_notes", ["Item 1"], [["PART II"], ["Item 1"]])])
    result = bind([("p2", None, "PART II", ""), ("risk", "p2", "Item 1A. Risk Factors", "evidence")], p)
    assert result["unit_profiles"]["riskb"]["section_role"] == "unknown"


def test_failed_scoped_rule_never_retries_flat_legacy_alias():
    p = profile([rule("management_discussion", ["Management's Discussion"], [["PART I"], ["Management's Discussion"]])])
    result = bind([("p2", None, "PART II", ""), ("m", "p2", "Management's Discussion", "evidence")], p)
    assert result["unit_profiles"]["mb"]["section_role"] == "unknown"


def test_unmatched_deep_heading_inherits_matching_parent_entry_priority():
    p = profile([rule("business", ["Operations"], [["PART I"], ["Operations"]], 1),
                 rule("business", ["Operations"], [["PART II"], ["Operations"]], 3)])
    result = bind([("deep", "ops", "Product deployment review", "evidence"),
                   ("ops", "part", "Operations", "evidence"), ("part", None, "PART II", "")], p)
    assert result["unit_profiles"]["deepb"]["section_role"] == "business"
    assert result["unit_profiles"]["deepb"]["priority"] == 3


def test_level_aliases_are_or_and_hierarchy_levels_are_and():
    p = profile([rule("business", ["Our Business"], [["PART I", "Financial Information"], ["Business", "Our Business"]], 2)])
    result = bind([("p", None, "Financial Information", ""), ("b", "p", "Our Business", "evidence")], p)
    assert result["unit_profiles"]["bb"]["section_role"] == "business"
    assert result["unit_profiles"]["bb"]["priority"] == 2


def test_chosen_unit_policy_exposes_components_questions_context_and_keeps_input():
    p = profile([rule("business", ["Business"], priority=2, question="New markets?")])
    o, s = tree([("b", None, "Business", "evidence")])
    before = deepcopy((o, s, p))
    result = bind_reading_plan(o, s, route={}, profile=p)
    read = result["unit_profiles"]["bb"]
    assert read["policy_components"] == p["policy_components"]
    assert "New markets?" in read["reading_questions"]
    assert "Current quarter versus YTD?" in read["reading_questions"]
    assert read["context_requirements"] == p["context_requirements"]
    assert read["family_policy"] == p["family_policy"]
    assert read["negative_hints"] == p["negative_hints"]
    assert read["semantic_units"] == p["semantic_units"]
    assert result["policy_components"] == p["policy_components"]
    assert (o, s, p) == before
    read["reading_questions"].append("output only")
    read["family_policy"]["evidence_status"] = "output only"
    read["negative_hints"].append("output only")
    read["semantic_units"].append("output only")
    assert (o, s, p) == before


def test_same_profile_id_child_scopes_keep_distinct_resolved_reading_policy():
    parent = profile([], name="generic")
    a = profile([], name="results_release", version="a", focus="new products")
    b = profile([], name="results_release", version="b", focus="new stores")
    o, s = tree([("a", None, "Exhibit A", "evidence A"), ("b", None, "Exhibit B", "evidence B")])
    route = {"child_routes": [{"unit_ids": ["ah", "ab"], "profile_id": "results_release", "reading_profile_key": "scope-a"},
                              {"unit_ids": ["bh", "bb"], "profile_id": "results_release", "reading_profile_key": "scope-b"}]}
    result = bind_reading_plan(o, s, route=route, profile=parent, child_profiles={"scope-a": a, "scope-b": b})
    assert result["unit_profiles"]["ab"]["summary_focus"] == "new products"
    assert result["unit_profiles"]["bb"]["summary_focus"] == "new stores"
    assert result["unit_profiles"]["ab"]["profile_id"] == "results_release"
    assert result["unit_profiles"]["ab"]["reading_profile_key"] == "scope-a"


def test_equal_child_ranges_with_distinct_policy_keys_remain_ambiguous():
    p = profile([], name="generic")
    o, s = tree([("b", None, "Business", "evidence")])
    route = {"child_routes": [{"unit_ids": ["bh", "bb"], "profile_id": "results_release", "reading_profile_key": key} for key in ("a", "b")]}
    result = bind_reading_plan(o, s, route=route, profile=p, child_profiles={key: profile([], name="results_release", version=key) for key in ("a", "b")})
    assert result["unit_profiles"]["bb"]["profile_id"] == "generic"
    assert any(d["code"] == "CHILD_RANGE_AMBIGUOUS" for d in result["diagnostics"])


def test_child_priority_remains_narrowest_and_external_links_are_not_read():
    parent = profile([], name="generic")
    o, s = tree([("a", None, "Business", "evidence"), ("b", None, "Other", "evidence")])
    route = {"child_routes": [{"unit_ids": ["ah", "ab", "bh", "bb"], "profile_id": "wide"},
                              {"unit_ids": ["ab"], "profile_id": "narrow"},
                              {"unit_ids": ["bb"], "profile_id": "external", "reason": {"code": "EXTERNAL_ATTACHMENT_NOT_READ"}}]}
    result = bind_reading_plan(o, s, route=route, profile=parent, child_profiles={x: profile([], name=x) for x in ("wide", "narrow", "external")})
    assert result["unit_profiles"]["ab"]["profile_id"] == "narrow"
    assert result["unit_profiles"]["bb"]["profile_id"] == "wide"


def test_legacy_flat_profile_still_binds_and_deeply_inherits():
    p = {"profile_id": "legacy", "profile_version": "v1", "section_priorities": [
        {"section_role": "business", "aliases": ["Business"], "priority": 2}]}
    result = bind([("top", None, "Business", ""), ("deep", "top", "Customer Updates", "evidence")], p)
    assert result["unit_profiles"]["topb"]["priority"] == 2
    assert result["unit_profiles"]["deepb"]["section_role"] == "business"
    assert result["unit_profiles"]["deepb"]["priority"] == 2


def test_received_ten_q_policy_binds_controls_and_legal_to_correct_parts():
    root = Path(__file__).resolve().parents[3]
    path = root / "docs/plans/document-understanding-2026-10-13/review/deliverables/families/records/sec_10q.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    p = profile(spec["sections"])
    result = bind([("one", None, "PART I", ""), ("control", "one", "Item 4. Controls and Procedures", "controls"),
                   ("two", None, "PART II", ""), ("legal", "two", "Item 1. Legal Proceedings", "legal"),
                   ("mine", "two", "Item 4. Mine Safety Disclosures", "mine safety")], p)
    assert result["unit_profiles"]["controlb"]["section_role"] == "administrative"
    assert result["unit_profiles"]["legalb"]["section_role"] == "administrative"
    assert result["unit_profiles"]["mineb"]["section_role"] == "unknown"


def test_child_body_does_not_reuse_the_mutated_parent_section_role():
    p = profile([rule("business", ["Business"], priority=1)], name="parent")
    child = profile([], name="child", focus="child content")
    o, s = tree([("b", None, "Business", "evidence")])
    route = {"child_routes": [{"unit_ids": ["bb"], "profile_id": "child"}]}
    output = bind_reading_plan(o, s, route=route, profile=p, child_profiles={"child": child})
    assert output["unit_profiles"]["bh"]["section_role"] == "business"
    assert output["unit_profiles"]["bb"]["section_role"] == "unknown"


def test_bad_parent_cycle_finishes_with_diagnostic_and_preserves_source():
    p = profile([rule("business", ["Business"], priority=2)])
    o, s = tree([("a", "b", "Business", "evidence"), ("b", "a", "Other", "evidence")])
    before = deepcopy((o, s))
    output = bind_reading_plan(o, s, route={}, profile=p)
    assert any(d["code"] == "SECTION_ANCESTRY_CYCLE" for d in output["diagnostics"])
    assert (o, s) == before


def test_legacy_native_role_keeps_legacy_config_priority():
    p = {"profile_id": "legacy", "profile_version": "v1", "section_priorities": [
        {"section_role": "business", "aliases": ["unrelated alias"], "priority": 3}]}
    o, s = tree([("native", None, "Customer deployment report", "evidence")])
    s["sections"][0]["section_role"] = "business"
    output = bind_reading_plan(o, s, route={}, profile=p)
    assert output["unit_profiles"]["nativeb"]["section_role"] == "business"
    assert output["unit_profiles"]["nativeb"]["priority"] == 3


def test_declared_unknown_role_keeps_parent_policy_priority_and_questions():
    p = profile([rule("unknown", ["Appendix"], priority=3, question="Any usable note?")])
    output = bind([("a", None, "Appendix", ""), ("n", "a", "Detailed supporting note", "evidence")], p)
    reading = output["unit_profiles"]["nb"]
    assert reading["section_role"] == "unknown"
    assert reading["priority"] == 3
    assert "Any usable note?" in reading["reading_questions"]


def test_typographic_apostrophe_matches_spec_without_rewriting_original():
    p = profile([rule("management_discussion", ["Management's Discussion"],
                      [["PART I"], ["Item 2. Management's Discussion and Analysis"]])])
    o, s = tree([("part", None, "PART I", ""),
                 ("item", "part", "Item 2. Management’s Discussion and Analysis", "source evidence")])
    before = deepcopy((o, s, p))
    output = bind_reading_plan(o, s, route={}, profile=p)
    assert output["unit_profiles"]["itemb"]["section_role"] == "management_discussion"
    assert output["unit_profiles"]["itemb"]["matched_section_rule"]["heading_path"] == p["section_rules"][0]["heading_path"]
    assert (o, s, p) == before
    assert "Management’s" in o["units"][2]["text"]


def test_matching_view_preserves_chemical_prime_notation():
    p = profile([rule("business", ["Drug 3' stage"])])
    output = bind([("drug", None, "Drug 3′ stage", "source evidence")], p)
    assert output["unit_profiles"]["drugb"]["section_role"] == "unknown"
