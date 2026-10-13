"""Behavior contracts for received DU packages, not company-specific oracles."""
from copy import deepcopy
from importlib import import_module
from itertools import permutations
from types import SimpleNamespace

from company_wiki.document_understanding.selection_bridge import dependency_closure
from company_wiki.document_understanding.summary_input import build_summary_input
from company_wiki.document_understanding.pipeline import understand_units


def package(name, members, required):
    return {"package_id": name, "kind": "project", "section_ids": [],
            "section_role": "fundraising", "member_unit_ids": members,
            "anchor_unit_ids": members[:1], "required_context_unit_ids": required,
            "completeness": "complete", "truncated": False, "diagnostics": []}


def result(packages, ids="abcd"):
    units = [{"unit_id": uid, "ordinal": i, "locator": "loc-" + uid, "page": 1,
              "text": "evidence-" + uid, "kind": "paragraph", "role": "company_filing",
              "hints": {}} for i, uid in enumerate(ids)]
    return {"schema_version": "du-pipeline/1", "observation": {"units": units},
            "packages": {"packages": packages}, "route": {}, "profile": {}, "structure": {}}


def test_dependency_chain_is_closed_independent_of_package_ranking():
    chain = [package("p1", ["c", "d"], ["d"]),
             package("p2", ["b", "c"], ["c"]),
             package("p3", ["a", "b"], ["b"])]
    for order in permutations(chain):
        closed = dependency_closure(["a"], {"packages": list(order)}, {})
        assert set(closed["selected_unit_ids"]) == set("abcd")
        request = build_summary_input(result(list(order)), selected_unit_ids=["a"])
        by_id = {p["package_id"]: p for p in request["evidence_packages"]}
        assert {m["unit_id"] for m in by_id["p1"]["members"]} >= {"c", "d"}


def test_missing_required_source_is_deferred_not_complete():
    request = build_summary_input(result([package("p", ["a", "missing"], ["missing"])], "a"))
    assert request["evidence_packages"] == []
    assert request["deferred"][0]["reason"] == "MISSING_REQUIRED_CONTEXT"


def test_closure_limit_cannot_be_bypassed_by_summary_member_expansion():
    pack = package("p", ["a", "b", "c"], ["b", "c"])
    request = build_summary_input(result([pack]), selected_unit_ids=["a"], max_context_units=1)
    assert request["evidence_packages"] == []
    assert any(d["reason"] == "MISSING_REQUIRED_CONTEXT" for d in request["deferred"])


def test_required_same_text_does_not_prove_same_source_context():
    pack = package("p", ["a", "b"], ["b"])
    closed = dependency_closure(["a"], {"packages": [pack]}, {"a": "24个月", "b": "24个月"})
    assert set(closed["selected_unit_ids"]) == {"a", "b"}


def test_truncated_package_never_claims_complete():
    pack = package("p", ["a"], [])
    pack["truncated"] = True
    request = build_summary_input(result([pack], "a"))
    assert request["evidence_packages"][0]["completeness"] == "partial"


def observation():
    return {"units": [{"unit_id": "h", "text": "Customer Deployment Review", "ordinal": 0},
                      {"unit_id": "u", "text": "We opened a new plant.", "ordinal": 1}]}


def test_profile_alias_really_binds_section_roles_and_keeps_input():
    bind = import_module("company_wiki.document_understanding.strategy_binding").bind_reading_plan
    o = observation()
    s = {"sections": [{"section_id": "s", "heading_unit_ids": ["h"],
                       "body_unit_ids": ["u"], "section_role": "unknown"}]}
    p = {"profile_id": "generic", "profile_version": "p1", "summary_focus": "business",
         "section_priorities": [{"section_role": "business", "aliases": ["Customer Deployment Review"], "priority": 1}]}
    before = deepcopy((o, s, p))
    bound = bind(o, s, route={"child_routes": []}, profile=p)
    assert bound["structure"]["sections"][0]["section_role"] == "business"
    assert (o, s, p) == before
    p["section_priorities"][0]["aliases"] = ["unrelated"]
    other = bind(o, s, route={"child_routes": []}, profile=p)
    assert other["structure"]["sections"][0]["section_role"] == "unknown"


def test_child_policy_is_applied_only_to_read_body_not_external_links():
    bind = import_module("company_wiki.document_understanding.strategy_binding").bind_reading_plan
    parent = {"profile_id": "generic", "profile_version": "v1", "section_priorities": []}
    child = {"profile_id": "results_release", "profile_version": "v2", "summary_focus": "business changes", "section_priorities": []}
    route = {"child_routes": [{"unit_ids": ["u"], "profile_id": "results_release", "reason": "embedded_results"},
                              {"unit_ids": ["h"], "profile_id": "results_release", "reason": "EXTERNAL_ATTACHMENT_NOT_READ"}]}
    bound = bind(observation(), {"sections": []}, route=route, profile=parent,
                 child_profiles={"results_release": child})
    assert bound["unit_profiles"]["u"]["profile_id"] == "results_release"
    assert bound["unit_profiles"]["h"]["profile_id"] == "generic"


def test_source_metadata_survives_pipeline_without_new_identity_checks():
    unit = SimpleNamespace(unit_id="u", raw_text="Business", unit_kind="html_heading",
                           source_role="company_filing", language="en", metadata={"source_locator": "loc-u"},
                           coordinates=SimpleNamespace(page_number=None, table_index=None, row_index=None, column_index=None))
    metadata = {"regime": "sec", "form_type": "F-1", "published_at": "2026-01-02",
                "period_end": "2025-12-31", "revision": "amended"}
    output = understand_units([unit], source_id="s", source_sha256="d", mime_type="text/html", metadata=metadata)
    for key, value in metadata.items():
        assert output["observation"]["metadata"][key] == value


def test_final_package_budget_must_keep_transitive_context_or_defer():
    chain = [package("p1", ["a", "b"], ["b"]), package("p2", ["b", "c"], ["c"])]
    for selected in (["a"], None):
        request = build_summary_input(result(chain), selected_unit_ids=selected, max_packages=1)
        assert request["evidence_packages"] == []
        assert any(d["reason"] == "MISSING_TRANSITIVE_CONTEXT" for d in request["deferred"])


def test_final_character_budget_must_keep_transitive_context_or_defer():
    chain = [package("p1", ["a", "b"], ["b"]), package("p2", ["b", "c"], ["c"])]
    request = build_summary_input(result(chain), selected_unit_ids=["a"], max_chars=20)
    assert request["evidence_packages"] == []


def test_negation_is_a_final_output_dependency_even_if_not_in_required_list():
    pack = package("p", ["a", "b", "c"], ["b"])
    pipeline = result([pack])
    pipeline["observation"]["units"][2]["text"] = "does not produce yet"
    request = build_summary_input(pipeline, selected_unit_ids=["a"], max_context_units=1)
    assert request["evidence_packages"] == []
    assert any(d["reason"] == "MISSING_TRANSITIVE_CONTEXT" for d in request["deferred"])


def test_missing_optional_member_is_partial_and_visible():
    pack = package("p", ["a", "missing"], [])
    request = build_summary_input(result([pack], "a"))
    assert request["evidence_packages"][0]["completeness"] == "partial"
    assert request["evidence_packages"][0]["omitted_unit_ids"] == ["missing"]
