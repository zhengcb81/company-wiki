"""Single packaged reading policy catalog; consumption, not registration counts."""
from __future__ import annotations
import copy
import inspect
import json
from pathlib import Path
import subprocess
import sys
import pytest
from company_wiki.document_understanding import profiles

ROOT = Path(__file__).resolve().parents[3]

def observation(texts=(), **metadata):
    return {"schema_version": "du-input/1", "source_ref": {"source_id": "original", "source_sha256": "a" * 64},
            "metadata": metadata, "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
            "units": [{"unit_id": f"u{i}", "ordinal": i, "locator": f"original:{i}", "page": None,
                       "text": text, "kind": "heading" if i == 0 else "paragraph", "hints": {}} for i, text in enumerate(texts)]}

def resolve(pid, observation, **route):
    function = getattr(profiles, "resolve_reading_profile", None)
    assert callable(function), "The catalog must affect the real ReadingPlan"
    return function(profiles.get_profile(pid), observation, {"profile_id": pid, **route})

def select(text, **kwargs):
    function = getattr(profiles, "select_business_facets", None)
    assert callable(function), "Actual final material must choose actual facet instructions"
    return function([{"unit_id": "u1", "locator": "raw:1", "text": text}], **kwargs)

def test_old_document_specific_profile_builder_is_removed():
    from company_wiki.document_understanding.profiles import registry
    assert "def _build_profiles" not in inspect.getsource(registry)

def test_packaged_catalog_contains_all_delivered_policies():
    path = Path(profiles.__file__).parent / "reading_catalog.json"
    assert path.exists()
    catalog = json.loads(path.read_text(encoding="utf-8"))
    assert len(catalog["families"]) == 24
    assert len(catalog["facets"]) == 14
    assert len(catalog["legacy_bindings"]) == 15

def test_sec_parts_survive_policy_consumption():
    result = resolve("sec_10q", observation(["FORM 10-Q", "PART I", "PART II"], regime="sec", form_type="10-Q"), family="quarterly", regime="sec", confidence="high")
    assert result["family_policy"]["id"] == "sec_10q"
    admin = [s for s in result["section_rules"] if s["role"] == "administrative"]
    assert {s["heading_path"][0][0] for s in admin} == {"PART I", "PART II"}
    assert result["context_requirements"]
    assert result["reading_questions"]
    assert result["policy_components"]

@pytest.mark.parametrize("extent,revision", [("summary", "original"), ("full", "amended"), ("unknown", "supplement")])
def test_lifecycle_axes_are_independent_and_not_forced(extent, revision):
    result = resolve("cn_annual", observation(["年度报告", "管理层讨论与分析"], regime="cn_exchange", revision=revision), family="annual", regime="cn_exchange", modifiers={"extent": extent, "revision": revision})
    assert result["family_policy"]["id"] == "cn_annual_report"
    assert result["modifiers"] == {"extent": extent, "revision": revision}

def test_hk_interim_uses_interim_policy_without_new_legacy_id():
    result = resolve("hk_periodic", observation(["中期報告", "業務回顧"], regime="hkex"), family="interim", regime="hkex")
    assert result["family_policy"]["id"] == "hk_interim_report"

def test_strong_sec_form_is_not_overwritten_by_attachment_words():
    result = resolve("sec_10k", observation(["FORM 10-K", "年度报告", "业务与技术", "首次公开发行"], regime="sec", form_type="10-K"), family="annual", regime="sec", confidence="high")
    assert result["family_policy"]["id"] == "sec_10k"
    assert result["family"] == "annual"

def test_unknown_document_keeps_unknown_and_proposed_state_is_honest():
    result = resolve("generic", observation(["Unclassified notes", "miscellaneous text"]), family="unknown", regime="unknown")
    assert result["family"] == "unknown" and result["family_policy"]["id"] is None
    offered = resolve("offering", observation(["募集资金投资项目的可行性研究报告", "可行性研究", "建设规模"], regime="cn_exchange"), family="offering", regime="cn_exchange")
    assert offered["family_policy"]["evidence_status"]
    assert offered["family_policy"]["integration_status"] == "not_integrated"

def test_resolve_is_immutable_and_deterministic():
    obs = observation(["FORM 10-Q", "PART I"], regime="sec", form_type="10-Q")
    before = copy.deepcopy(obs)
    assert resolve("sec_10q", obs, family="quarterly", regime="sec") == resolve("sec_10q", obs, family="quarterly", regime="sec")
    assert obs == before

def test_policy_changes_change_the_actual_instructions_and_local_version(monkeypatch):
    from company_wiki.document_understanding.profiles import registry
    obs = observation(["FORM 10-Q"], regime="sec", form_type="10-Q")
    before = resolve("sec_10q", obs, family="quarterly", regime="sec")
    catalog = copy.deepcopy(registry._CATALOG)
    chosen = next(r for r in catalog["families"] if r["id"] == "sec_10q")
    chosen["reading_questions"].append("Preserve the causal business explanation")
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    after = resolve("sec_10q", obs, family="quarterly", regime="sec")
    assert before["profile_version"] != after["profile_version"]
    assert "Preserve the causal business explanation" in after["reading_questions"]

def test_unrelated_family_or_facet_edit_does_not_invalidate_current_policy(monkeypatch):
    from company_wiki.document_understanding.profiles import registry
    obs = observation(["FORM 10-Q"], regime="sec", form_type="10-Q")
    before = resolve("sec_10q", obs, family="quarterly", regime="sec")
    catalog = copy.deepcopy(registry._CATALOG)
    next(r for r in catalog["families"] if r["id"] == "prospectus_hk")["reading_questions"].append("other unrelated policy")
    catalog["facets"][0]["summary_focus"].append("other unrelated facet")
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    assert resolve("sec_10q", obs, family="quarterly", regime="sec")["profile_version"] == before["profile_version"]

def test_new_policy_resolver_is_probe_bounded():
    function = getattr(profiles, "resolve_reading_profile", None)
    assert callable(function)
    obs = observation(["x" * 100 for _ in range(1000)])
    result = function(profiles.get_profile("generic"), obs, {"family": "unknown", "regime": "unknown"}, limits={"max_probe_units": 3, "max_probe_chars": 18})
    assert result["policy_probe"]["probed_unit_count"] <= 3
    assert result["policy_probe"]["probed_chars"] <= 18
    assert result["policy_probe"]["limited"]

def test_selected_facets_are_the_actual_rules_and_quantity_is_conditional():
    selected = select("我们的主营业务涉及新产品，送样后进行客户验证，目前尚未量产；海外门店网络新增直营店。", max_facets=8)
    assert selected and len(selected) <= 8
    assert any(r["id"] == "semantic_stage_progression" for r in selected)
    assert all(r["required_context"] and r["absence_rules"] for r in selected)
    assert all(r["business_questions"] and r["summary_focus"] for r in selected)
    assert all("facts" not in r and "extracted_quantity" not in r for r in selected)
    for rule in selected:
        for context in rule["required_context"]:
            if "quantity" in context["slots"]:
                assert context["required_when"] == "quantity_emitted"

def test_consumer_label_does_not_activate_consumption_billing():
    selected = select("Microsoft 365 Consumer revenue increased.")
    assert not any(r["id"] == "mechanism_subscription_consumption" for r in selected)
    assert not any("observed_mechanism" in r for r in selected)

def test_facet_selection_only_sees_supplied_final_material_and_budget():
    assert select("", max_facets=4) == []
    assert select("subscription revenue", max_facets=0) == []
    assert select("subscription revenue", max_probe_chars=0) == []
    selected = select("subscription seats", max_facets=1)
    assert len(selected) == 1
    assert selected[0]["selection_basis"]

@pytest.mark.parametrize("kw", [{"max_facets": -1}, {"max_probe_chars": -1}, {"max_facets": True}])
def test_invalid_facet_budgets_fail_real_type_checks(kw):
    function = getattr(profiles, "select_business_facets", None)
    assert callable(function)
    with pytest.raises((TypeError, ValueError)):
        function([], **kw)

def test_runtime_resolution_does_not_read_docs(monkeypatch):
    function = getattr(profiles, "resolve_reading_profile", None)
    assert callable(function)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert "docs" not in path.parts, "runtime policy must use its packaged asset"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    result = resolve("sec_10q", observation(["FORM 10-Q"], regime="sec", form_type="10-Q"), family="quarterly", regime="sec")
    assert result["family_policy"]["id"] == "sec_10q"

def test_compiler_check_matches_single_asset_and_detects_drift(tmp_path):
    compiler = ROOT / "tools/import_reading_policies.py"
    assert compiler.exists()
    command = [sys.executable, "-B", str(compiler), "--check"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    altered = tmp_path / "reading_catalog.json"
    altered.write_text('{}', encoding="utf-8")
    result = subprocess.run(command + ["--output", str(altered)], cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert altered.read_text(encoding="utf-8") == '{}'


def test_navigation_context_policy_has_one_maintained_defaults_owner():
    from tools.import_reading_policies import compile_catalog
    from company_wiki.document_understanding.profiles import registry
    defaults = json.loads((ROOT / "src/company_wiki/document_understanding/profiles/reading_defaults.json").read_text(encoding="utf-8"))
    assert defaults.get("context_policy") == registry._CATALOG["context_policy"]
    assert compile_catalog(ROOT)["context_policy"] == defaults["context_policy"]


def test_context_policy_default_change_is_preserved_by_compiler(tmp_path):
    from tools.import_reading_policies import compile_catalog
    defaults = json.loads((ROOT / "src/company_wiki/document_understanding/profiles/reading_defaults.json").read_text(encoding="utf-8"))
    policy = {"schema_version": "reading-context-policy/1", "version": "test-change",
              "generic_navigation_titles": ["Neutral business navigation"]}
    defaults["context_policy"] = policy
    path = tmp_path / "defaults.json"
    path.write_text(json.dumps(defaults), encoding="utf-8")
    assert compile_catalog(ROOT, path)["context_policy"] == policy


def test_shared_adopted_instructions_are_part_of_local_profile_version(monkeypatch):
    from company_wiki.document_understanding.profiles import registry
    obs = observation(["FORM 10-Q"], regime="sec", form_type="10-Q")
    before = resolve("sec_10q", obs, family="quarterly", regime="sec")
    catalog = copy.deepcopy(registry._CATALOG)
    catalog["shared_focus"] += " Keep conditional guidance separate from achieved results."
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    after = resolve("sec_10q", obs, family="quarterly", regime="sec")
    assert before["summary_focus"] != after["summary_focus"]
    assert before["profile_version"] != after["profile_version"]

def test_facet_changes_affect_only_selected_instructions(monkeypatch):
    from company_wiki.document_understanding.profiles import registry
    before = select("subscription seats")
    assert before
    identifier = before[0]["id"]
    catalog = copy.deepcopy(registry._CATALOG)
    chosen = next(record for record in catalog["facets"] if record["id"] == identifier)
    chosen["summary_focus"].append("Keep the charging mechanism and recognition timing")
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    after = select("subscription seats")
    assert before[0]["content_digest"] != after[0]["content_digest"]
    assert "Keep the charging mechanism and recognition timing" in after[0]["summary_focus"]
    assert "confusions" not in after[0] and "case_ids" not in after[0]


def test_unknown_fallback_retains_source_navigation_and_toc_hints():
    result = resolve("generic", observation(["unclassified source notes"]), family="unknown", regime="unknown")
    assert any("目录" in hint for hint in result["negative_hints"])
    assert any("导航" in hint for hint in result["negative_hints"])
