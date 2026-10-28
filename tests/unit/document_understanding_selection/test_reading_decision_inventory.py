"""Source-specific cache inventory includes decision losers, not whole catalog."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.document_understanding.profiles import registry


def _pipeline():
    return {"source_ref": {"source_id": "urn:company-wiki:source:sha256:" + "a" * 64},
            "route": {"family": "annual", "regime": "cn_exchange", "profile_id": "cn_annual"},
            "observation": {"metadata": {}}, "reading_plan": {"used_profiles": [
                {"profile_id": "cn_annual", "reading_profile_key": None}]}}


def test_decision_inventory_changes_for_unselected_applicable_policy(monkeypatch):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    # Use the actual installed binding ID rather than an imagined provider ID.
    binding = next(row for row in registry._CATALOG["legacy_bindings"]
                   if row["family"] == "annual" and row["regime"] == "cn_exchange")
    pipeline = _pipeline()
    pipeline["route"]["profile_id"] = binding["profile_id"]
    pipeline["reading_plan"]["used_profiles"][0]["profile_id"] = binding["profile_id"]
    before = module.build_decision_trace(pipeline)
    changed = deepcopy(registry._CATALOG)
    target = next(row for row in changed["families"] if row["applies_to"]["family"] == "annual"
                  and "cn_exchange" in row["applies_to"]["regimes"])
    target["sections"][0]["priority"] += 1
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert module.current_decision_trace(before) != before


def test_unrelated_family_content_does_not_invalidate_this_source(monkeypatch):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    binding = next(row for row in registry._CATALOG["legacy_bindings"]
                   if row["family"] == "annual" and row["regime"] == "cn_exchange")
    pipeline = _pipeline()
    pipeline["route"]["profile_id"] = binding["profile_id"]
    pipeline["reading_plan"]["used_profiles"][0]["profile_id"] = binding["profile_id"]
    before = module.build_decision_trace(pipeline)
    changed = deepcopy(registry._CATALOG)
    target = next(row for row in changed["families"] if row["applies_to"]["family"] == "prospectus")
    target["reading_questions"].append("Unrelated source question")
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert module.current_decision_trace(before) == before


def test_missing_inventory_cannot_claim_complete():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    trace = {"schema_version": "du-decision-trace/1", "scopes": [], "components": [],
             "candidates": [], "versions": {}, "inventory_complete": False}
    assert module.current_decision_trace(trace)["inventory_complete"] is False


@pytest.mark.parametrize("order", [("z-parent", "a-child"), ("a-child", "z-parent")])
def test_source_wide_facets_survive_scope_sorting_and_frozen_replay(order):
    """Source-global facets cannot acquire a new scope when freeze sorts IDs."""
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.document_understanding.decision_dependencies import (
        compare_decision_dependencies, freeze_decision_dependencies,
    )

    binding = next(row for row in registry._CATALOG["legacy_bindings"]
                   if row["family"] == "annual" and row["regime"] == "cn_exchange")
    scopes = [{"scope_id": sid, "family": "annual", "regime": "cn_exchange",
               "form_type": "unknown", "purpose": "annual"} for sid in order]
    used = {registry._CATALOG["facets"][0]["id"]}
    trace = decision_inventory._inventory(
        scopes, dict.fromkeys(order, binding["profile_id"]), used, carrier="text/plain")
    frozen = freeze_decision_dependencies(trace)
    assert frozen["status"] == "complete"
    current = decision_inventory.current_decision_trace(frozen)
    assert compare_decision_dependencies(frozen, current)["status"] == "same"
    reversed_trace = decision_inventory._inventory(
        list(reversed(scopes)), dict.fromkeys(order, binding["profile_id"]), used,
        carrier="text/plain")
    assert freeze_decision_dependencies(reversed_trace)["decision_digest"] == frozen["decision_digest"]


def test_transient_script_matching_change_invalidates_actual_decision(monkeypatch):
    from company_wiki.document_normalization import normalize_document, text_matching
    from company_wiki.document_understanding import understand_units
    from company_wiki.document_understanding.decision_dependencies import (
        compare_decision_dependencies, freeze_decision_dependencies,
    )

    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    raw = b"<html><body><p>INTERIM REPORT 2026. Our company launched a new product for overseas customers.</p></body></html>"
    digest = sha256(raw).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + digest
    parsed = normalize_document(raw, source_id=source_id, source_sha256=digest, mime_type="text/html")
    observed = understand_units(parsed.structure.units, source_id=source_id, source_sha256=digest,
                               title="INTERIM REPORT 2026", declared_kind="semi_annual_report", language="en",
                               mime_type="text/html", metadata={"regime": "hkex"})
    before = module.build_decision_trace(observed)
    frozen = freeze_decision_dependencies(before)
    assert frozen["status"] == "complete"
    assert before["versions"].get("script_matching") == text_matching.SCRIPT_MATCHING_VERSION
    assert compare_decision_dependencies(frozen, module.current_decision_trace(before))["status"] == "same"
    monkeypatch.setattr(text_matching, "SCRIPT_MATCHING_VERSION", "source-script-match/next")
    assert compare_decision_dependencies(frozen, module.current_decision_trace(before))["status"] == "changed"


def test_reading_business_admission_version_is_an_actual_cache_dependency(monkeypatch):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    policy = importlib.import_module("company_wiki.source_catalog.narrative_business_policy")
    before = module.build_decision_trace(_real_interim_pipeline())
    assert before["versions"].get("business_policy") == policy.READING_BUSINESS_POLICY_VERSION
    assert module.current_decision_trace(before) == before
    monkeypatch.setattr(policy, "READING_BUSINESS_POLICY_VERSION", policy.READING_BUSINESS_POLICY_VERSION + "/next")
    current = module.current_decision_trace(before)
    assert current != before, "a changed admission algorithm cannot reuse the old decision"
    assert current["versions"]["business_policy"] == policy.READING_BUSINESS_POLICY_VERSION
    assert {key: value for key, value in current.items() if key != "versions"} == {
        key: value for key, value in before.items() if key != "versions"
    }


def test_reporting_rule_only_change_invalidates_the_actual_decision_cache(tmp_path, monkeypatch):
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import (
        freeze_decision_dependencies, compare_decision_dependencies,
    )
    from company_wiki.source_catalog import narrative_reporting_rules as rules

    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/html"
    trace = inventory.build_decision_trace(observed)
    frozen = freeze_decision_dependencies(trace)
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(trace))["status"] == "same"
    changed = tmp_path / "reporting_rules.py"
    changed.write_bytes(Path(rules.__file__).read_bytes() + b"\n# changed reporting treatment rule\n")
    monkeypatch.setattr(rules, "__file__", str(changed))
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(trace))["status"] == "changed"


def test_changed_continuity_algorithm_invalidates_a_real_complete_manifest(monkeypatch):
    from company_wiki.document_understanding import decision_inventory, narrative_continuity
    from company_wiki.document_understanding.decision_dependencies import (
        freeze_decision_dependencies, compare_decision_dependencies,
    )
    observed = _real_interim_pipeline()
    # This fixture's actual carrier is explicit; the pure manifest cannot infer it.
    observed['observation']['metadata']['mime_type'] = 'text/plain'
    frozen = freeze_decision_dependencies(decision_inventory.build_decision_trace(observed))
    assert frozen['status'] == 'complete'
    assert compare_decision_dependencies(frozen, decision_inventory.current_decision_trace(frozen))['status'] == 'same'
    monkeypatch.setattr(narrative_continuity, 'NARRATIVE_CONTINUITY_FEATURE_VERSION', 'native-narrative-continuity/next')
    assert compare_decision_dependencies(frozen, decision_inventory.current_decision_trace(frozen))['status'] == 'changed'


def test_native_source_range_algorithm_is_a_pdf_dependency_only(monkeypatch):
    from company_wiki.source_catalog import narrative_native_ranges
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    before = module._versions(pdf_frontend=True)
    unrelated = module._versions(pdf_frontend=False)
    assert before.get("pdf_native_range") == narrative_native_ranges.NATIVE_PAGE_VIEW_FEATURE_VERSION
    monkeypatch.setattr(narrative_native_ranges, "NATIVE_PAGE_VIEW_FEATURE_VERSION", "native-pdf-page-view/next")
    assert module._versions(pdf_frontend=True) != before
    assert module._versions(pdf_frontend=False) == unrelated


def test_changed_table_meaning_invalidates_a_complete_manifest(monkeypatch):
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.document_understanding.structure import table_purpose
    from company_wiki.document_understanding.decision_dependencies import (
        freeze_decision_dependencies, compare_decision_dependencies,
    )
    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/html"
    frozen = freeze_decision_dependencies(decision_inventory.build_decision_trace(observed))
    assert frozen["status"] == "complete"
    monkeypatch.setattr(table_purpose, "FEATURE_VERSION", "operating-table-purpose/next")
    assert compare_decision_dependencies(
        frozen, decision_inventory.current_decision_trace(frozen))["status"] == "changed"


@pytest.mark.parametrize("first", ["inventory", "policy", "source-selector"])
def test_actual_business_version_import_chain_is_safe_from_fresh_entry_points(first):
    modules = {
        "inventory": "company_wiki.document_understanding.decision_inventory",
        "policy": "company_wiki.source_catalog.narrative_business_policy",
        "source-selector": "company_wiki.source_catalog.narrative_reading",
    }
    ordered = [modules[first], *(name for key, name in modules.items() if key != first)]
    repo = Path(__file__).resolve().parents[3]
    script = (
        "import importlib,json,sys; "
        "[importlib.import_module(name) for name in json.loads(sys.argv[1])]; "
        "inventory=importlib.import_module('company_wiki.document_understanding.decision_inventory'); "
        "policy=importlib.import_module('company_wiki.source_catalog.narrative_business_policy'); "
        "assert inventory._versions()['business_policy']==policy.READING_BUSINESS_POLICY_VERSION"
    )
    result = subprocess.run([sys.executable, "-c", script, json.dumps(ordered)],
                            cwd=repo, env={**os.environ, "PYTHONPATH": str(repo / "src"),
                                           "PYTHONDONTWRITEBYTECODE": "1"},
                            capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr


def _real_interim_pipeline():
    from company_wiki.document_understanding import understand_units
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    digest = "a" * 64
    source_id = source_id_for_sha256(digest)
    unit = _make_unit(source_id=source_id, parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="INTERIM REPORT 2026. Our company launched a new product for overseas customers.",
        unit_kind="pdf_text_block", source_role="company_filing", language="en", metadata={})
    pipeline = understand_units((unit,), source_id=source_id, source_sha256=digest,
        title="INTERIM REPORT 2026", declared_kind="semi_annual_report", language="en",
        metadata={"regime": "hkex"})
    assert pipeline["route"]["family"] == "interim"
    assert pipeline["profile"]["family"] == "interim"
    return pipeline


def test_real_hk_interim_inventory_records_the_resolved_family_and_invalidates_changed_policy(monkeypatch):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    trace = module.build_decision_trace(pipeline)
    assert trace["scopes"][0]["family"] == "interim"
    names = {row["candidate_id"].rsplit("|", 1)[-1] for row in trace["candidates"]}
    assert "hk_interim_report" in names and "hk_annual_report" not in names
    assert module.current_decision_trace(trace) == trace
    changed = deepcopy(registry._CATALOG)
    record = next(row for row in changed["families"] if row["id"] == "hk_interim_report")
    record["sections"][0]["priority"] += 1
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert module.current_decision_trace(trace) != trace


def test_actual_child_unit_family_wins_over_legacy_binding_and_parent_form():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    child_key = "hk_periodic:actually-read-child"
    pid = pipeline["profile"]["profile_id"]
    pipeline["reading_plan"]["used_profiles"].append({"profile_id": pid, "reading_profile_key": child_key})
    pipeline["reading_plan"]["unit_profiles"]["child-unit"] = {
        "profile_id": pid, "reading_profile_key": child_key, "family": "interim", "regime": "hkex"}
    # The child resolver explicitly clears the parent's form metadata.
    pipeline["observation"]["metadata"]["form_type"] = "10-K"
    trace = module.build_decision_trace(pipeline)
    child = next(row for row in trace["scopes"] if row["scope_id"].endswith(child_key))
    assert child["family"] == "interim" and child["regime"] == "hkex"
    assert child["form_type"] == "unknown"
    ids = {row["candidate_id"].rsplit("|", 1)[-1] for row in trace["candidates"] if row["scope_id"] == child["scope_id"]}
    assert "hk_interim_report" in ids and "hk_annual_report" not in ids


@pytest.mark.parametrize("origin", ["resolved_profile", "actual_units"])
def test_resolved_parent_family_is_not_replaced_by_an_obsolete_route_or_binding(origin):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    pipeline["route"]["family"] = "annual"
    if origin == "actual_units":
        pipeline.pop("profile")
    trace = module.build_decision_trace(pipeline)
    assert trace["scopes"][0]["family"] == "interim"


def test_actual_child_regime_does_not_inherit_the_parent_market_or_profile_default():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    child_key = "observed-sec-child"
    # This is an actual resolved scoped view. The compatibility profile ID is
    # deliberately shared, just as hk_periodic is shared by annual and interim.
    pipeline["reading_plan"]["used_profiles"].append({"profile_id": "hk_periodic", "reading_profile_key": child_key})
    pipeline["reading_plan"]["unit_profiles"]["child-unit"] = {
        "profile_id": "hk_periodic", "reading_profile_key": child_key, "family": "quarterly", "regime": "sec"}
    child = next(row for row in module.build_decision_trace(pipeline)["scopes"] if row["scope_id"].endswith(child_key))
    assert child["family"] == "quarterly" and child["regime"] == "sec"


def test_unresolved_child_scope_cannot_claim_complete_using_a_legacy_default():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    pipeline["reading_plan"]["used_profiles"].append({"profile_id": "hk_periodic", "reading_profile_key": "missing-child"})
    assert module.build_decision_trace(pipeline)["inventory_complete"] is False


def test_actual_scope_retains_ineligible_metadata_candidates_and_their_admission_matcher(monkeypatch):
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    trace = module.build_decision_trace(_real_interim_pipeline())
    ineligible = [row for row in trace["candidates"] if row["candidate_id"].startswith("family|") and not row["eligible"]]
    assert ineligible
    name = ineligible[0]["candidate_id"].rsplit("|", 1)[-1]
    changed = deepcopy(registry._CATALOG)
    record = next(row for row in changed["families"] if row["id"] == name)
    record["reading_questions"].append("Still inapplicable, do not invalidate unrelated content.")
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert module.current_decision_trace(trace) == trace
    record["applies_to"]["regimes"].append("hkex")
    assert module.current_decision_trace(trace) != trace


def test_missing_actual_root_family_cannot_be_filled_from_the_compatibility_binding():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _pipeline()
    pipeline["route"].pop("family")
    assert module.build_decision_trace(pipeline)["inventory_complete"] is False


def test_conflicting_actual_unit_families_cannot_be_reused_as_an_arbitrary_first_scope():
    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    pipeline = _real_interim_pipeline()
    first = next(iter(pipeline["reading_plan"]["unit_profiles"].values()))
    pipeline["reading_plan"]["unit_profiles"]["contradictory"] = {**first, "family": "annual"}
    assert module.build_decision_trace(pipeline)["inventory_complete"] is False


def test_real_multi_parent_reading_bridge_namespaces_actual_profiles_for_complete_inventory():
    from company_wiki.automation.narrative_official_json import _unit
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    from company_wiki.source_catalog.narrative_reading import _understand
    from unit.test_official_json_model_subject import selection

    module = importlib.import_module("company_wiki.document_understanding.decision_inventory")
    original = selection()
    units = tuple(_unit(span) for span in original.evidence_spans)
    parsed = DocumentStructure(original.source_ref.source_id, original.source_ref.content_sha256,
                               "en", units)
    pipeline = _understand(parsed, title="Investor relations activity record",
                           kind="investor_relations", mime_type="application/json")
    trace = module.build_decision_trace(pipeline)
    assert trace["inventory_complete"] is True
    assert len(trace["scopes"]) == 2
    actual = pipeline["child_profiles"]
    for used in pipeline["reading_plan"]["used_profiles"]:
        key = used["reading_profile_key"]
        scope = next(row for row in trace["scopes"] if row["scope_id"].endswith(key))
        assert scope["family"] == actual[key]["family"]
        assert scope["regime"] == actual[key]["regime"]
    assert {view["reading_profile_key"] for view in pipeline["reading_plan"]["unit_profiles"].values()} == set(actual)


@pytest.mark.parametrize("module_name", [
    "company_wiki.source_catalog.narrative_business_policy",
    "company_wiki.source_catalog.narrative_recognition_scope",
    "company_wiki.source_catalog.narrative_source_purpose",
    "company_wiki.source_catalog.narrative_support_use",
    "company_wiki.document_understanding.reading_context_contract",
    "company_wiki.document_understanding.operating_states.assertion_roles",
    "company_wiki.source_catalog.narrative_budget",
    "company_wiki.source_catalog.narrative_business_disclosures",
    "company_wiki.source_catalog.narrative_reading",
    "company_wiki.source_catalog.narrative_document",
    "company_wiki.document_understanding.profiles.registry",
    "company_wiki.document_understanding.layout_hints",
    "company_wiki.document_understanding.layout_hints.columns",
    "company_wiki.document_understanding.structure",
    "company_wiki.document_understanding.structure.layout",
    "company_wiki.document_understanding.structure.sections",
])
def test_w08_changed_source_implementation_invalidates_the_real_complete_decision(monkeypatch, module_name):
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import (
        compare_decision_dependencies, freeze_decision_dependencies,
    )
    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/html"
    source_file = Path(importlib.import_module(module_name).__file__).resolve()
    read_bytes = Path.read_bytes
    changed = False

    def source_bytes(path):
        raw = read_bytes(path)
        if changed and path.resolve() == source_file:
            return raw + b"\n# changed owned source algorithm\n"
        return raw

    # Exercise source bytes, independent of whether an owner is discovered
    # through its package or an explicit module import. No source is written.
    monkeypatch.setattr(Path, "read_bytes", source_bytes)
    frozen = freeze_decision_dependencies(inventory.build_decision_trace(observed))
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "same"
    changed = True
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "changed"


@pytest.mark.parametrize("pdf", [False, True])
def test_product_identity_source_bytes_are_part_of_the_actual_current_decision(monkeypatch, pdf):
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.document_understanding.operating_states import product_reference
    target = Path(product_reference.__file__).resolve()
    assert target.is_relative_to(Path(__file__).resolve().parents[3] / "src")
    read_bytes = Path.read_bytes
    before = decision_inventory._versions(pdf_frontend=pdf)
    with monkeypatch.context() as patch:
        def changed_source(path):
            raw = read_bytes(path)
            return raw + b"\n# changed source identity policy\n" if path.resolve() == target else raw
        patch.setattr(Path, "read_bytes", changed_source)
        changed = decision_inventory._versions(pdf_frontend=pdf)
        assert changed["business_algorithms"] != before["business_algorithms"]
        assert changed["budget"] == before["budget"]
    assert decision_inventory._versions(pdf_frontend=pdf) == before


def test_navigation_context_policy_content_changes_current_decision(monkeypatch):
    from company_wiki.document_understanding import decision_inventory as inventory
    before = inventory._versions(pdf_frontend=False)
    changed = deepcopy(registry._CATALOG)
    changed["context_policy"]["generic_navigation_titles"].append("Additional generic navigation")
    monkeypatch.setattr(registry, "_CATALOG", changed)
    after = inventory._versions(pdf_frontend=False)
    assert after["context_policy"] != before["context_policy"]
    assert after["budget"] == before["budget"]
