"""Independent POLICY contract expectations; no planner, PDF or supplier required."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from company_wiki.document_understanding.profiles import get_profile, list_profiles, route_document
from company_wiki.document_understanding.profiles import registry
from fixtures.document_understanding_profiles.builders import CN_IR_QA, observation, unit


UNKNOWN = {"discover": "unknown", "fine": "unknown", "demand_class": "unknown"}
OPERATING = {"discover": "on_tabular_evidence", "fine": "on_candidate", "demand_class": "operating"}
MIXED = dict(OPERATING, demand_class="mixed")
PROJECT = dict(OPERATING, demand_class="project")
ADMIN = {"discover": "context_only", "fine": "unknown", "demand_class": "administrative"}
CONTEXT = {"discover": "context_only", "fine": "explicit_only", "demand_class": "context"}


def compiler():
    return importlib.import_module(
        "company_wiki.document_understanding.profiles.geometry_policy"
    ).compile_geometry_policy


def sample(**changes):
    value = {"profile_id": "sample", "profile_version": "sample/v2+1", "section_rules": [{
        "family_id": "sample_family", "family_version": "1.0", "section_role": "business",
        "priority": 1, "heading_path": [["Part I"], ["Business"]],
        "aliases": ["Business"], "questions": ["What changed?"], "geometry_intent": OPERATING,
    }]}
    value.update(changes)
    return value


def resolved(family_id, *, modifiers=None):
    """Use the real resolver with explicit existing route identity; no new routing logic."""
    family = next(r for r in registry._CATALOG["families"] if r["id"] == family_id)
    binding = next(r for r in registry._CATALOG["legacy_bindings"] if family_id in r["family_ids"])
    applies = family["applies_to"]
    body = "向特定对象发行股票募集说明书" if family_id == "offering_cn_equity" else "source body"
    obs = observation([unit("body", 0, body, kind="heading")], title=body,
                      regime=applies["regimes"][0],
                      form_type=next(iter(applies["forms"]), None))
    route = {"profile_id": binding["profile_id"], "family": applies["family"],
             "regime": applies["regimes"][0], "form_type": next(iter(applies["forms"]), "unknown"),
             "subtype": family_id, "modifiers": modifiers or {"extent": "full", "revision": "original"}}
    # Unknown-purpose families need positive original evidence, never a guessed family.
    if applies["family"] == "unknown":
        return None
    return registry.resolve_reading_profile(get_profile(binding["profile_id"]), obs, route)


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


def test_compiler_is_pure_json_and_keeps_full_context_without_mutating_input():
    compile_policy = compiler()
    data = sample()
    frozen = deepcopy(data)
    with patch("builtins.open", side_effect=AssertionError("compiler file IO")), \
            patch("time.time", side_effect=AssertionError("compiler clock")), \
            patch("socket.socket", side_effect=AssertionError("compiler network")), \
            patch.object(registry, "_choose_family", side_effect=AssertionError("rerouting")):
        first = compile_policy(data)
        assert first == compile_policy(data)
    assert data == frozen
    assert json.loads(json.dumps(first)) == first
    assert first["schema_version"] == "du-geometry-policy/1"
    assert first["profile_version"] == data["profile_version"]
    rule = first["rules"][0]
    assert rule["heading_path"] == [["Part I"], ["Business"]]
    assert rule["reading_priority"] == 1 and rule["geometry_intent"] == OPERATING
    key_payload = {k: v for k, v in rule.items() if k != "rule_key"}
    assert rule["rule_key"] == digest(key_payload)
    assert len(rule["rule_key"]) == 64
    first["rules"][0]["aliases"].append("mutated")
    assert compile_policy(data)["rules"][0]["aliases"] == ["Business"]


def test_missing_fields_are_structured_unknown_and_priority_does_not_invent_intent():
    policy = compiler()({"section_rules": [{"section_role": "business", "priority": 1}]})
    assert policy["default_intent"] == UNKNOWN
    rule = policy["rules"][0]
    assert rule["geometry_intent"] == UNKNOWN
    assert rule["heading_path"] == [] and rule["aliases"] == [] and rule["questions"] == []
    assert compiler()({})["rules"] == []


def test_full_rule_keys_distinguish_part_aliases_priority_questions_and_intent():
    data = sample()
    original = data["section_rules"][0]
    variants = [original, dict(original, heading_path=[["Part II"], ["Business"]]),
                dict(original, aliases=["Our Business"]), dict(original, priority=2),
                dict(original, questions=["What risks?"]),
                dict(original, geometry_intent=PROJECT), dict(original, family_id="other"),
                dict(original, family_version="2.0")]
    keys = [r["rule_key"] for r in compiler()(sample(section_rules=variants))["rules"]]
    assert len(set(keys)) == len(variants)
    permuted = compiler()(sample(section_rules=list(reversed(variants))))
    assert [r["rule_key"] for r in permuted["rules"]] == list(reversed(keys))


@pytest.mark.parametrize("field,value,code", [
    ("geometry_intent", {"discover": "on_table"}, "GEOMETRY_POLICY_BAD_INTENT"),
    ("geometry_intent", [], "GEOMETRY_POLICY_BAD_INTENT"),
    ("geometry_intent", {"fine": 1}, "GEOMETRY_POLICY_BAD_INTENT"),
    ("geometry_intent", {"demand_class": "company"}, "GEOMETRY_POLICY_BAD_INTENT"),
    ("geometry_intent", {"extra": "signed"}, "GEOMETRY_POLICY_BAD_INTENT"),
    ("heading_path", ["Part I", "Business"], "GEOMETRY_POLICY_BAD_PATH"),
    ("heading_path", [["Part I"], []], "GEOMETRY_POLICY_BAD_PATH"),
    ("heading_path", [[7]], "GEOMETRY_POLICY_BAD_PATH"),
    ("aliases", "Business", "GEOMETRY_POLICY_BAD_ALIASES"),
    ("questions", [None], "GEOMETRY_POLICY_BAD_QUESTIONS"),
    ("section_role", "investment_rating", "GEOMETRY_POLICY_BAD_ROLE"),
    ("priority", True, "GEOMETRY_POLICY_BAD_PRIORITY"),
])
def test_malformed_rules_have_explicit_diagnostic_codes(field, value, code):
    data = sample()
    data["section_rules"][0][field] = value
    with pytest.raises(ValueError) as error:
        compiler()(data)
    assert error.value.code == code


def test_exact_duplicate_is_diagnosed_but_shared_path_distinct_aliases_are_legal():
    rule = sample()["section_rules"][0]
    with pytest.raises(ValueError) as error:
        compiler()(sample(section_rules=[rule, deepcopy(rule)]))
    assert error.value.code == "GEOMETRY_POLICY_DUPLICATE_RULE"
    assert len(compiler()(sample(section_rules=[rule, dict(rule, aliases=["Operations"])]))["rules"]) == 2


@pytest.mark.parametrize("family_id,role,expected", [
    ("cn_annual_report", "business", OPERATING),
    ("cn_interim_report", "operating_metrics", OPERATING),
    ("cn_quarterly_report", "financial_notes", MIXED),
    ("hk_annual_report", "business", OPERATING),
    ("hk_interim_report", "business", OPERATING),
    ("sec_10k", "financial_notes", MIXED),
    ("sec_10q", "management_discussion", MIXED),
    ("sec_20f", "risk", CONTEXT),
    ("prospectus_cn", "fundraising", PROJECT),
    ("prospectus_hk", "fundraising", PROJECT),
    ("prospectus_us", "fundraising", PROJECT),
    ("offering_cn_convertible", "fundraising", PROJECT),
    ("offering_cn_equity", "fundraising", PROJECT),
    ("offering_feasibility", "fundraising", PROJECT),
    ("project_change_notice", "fundraising", PROJECT),
    ("results_release", "operating_metrics", OPERATING),
    ("investor_presentation", "operating_metrics", OPERATING),
    ("investor_qa_record", "questions", CONTEXT),
    ("earnings_call_transcript", "operating_metrics", CONTEXT),
    ("administrative_document", "administrative", ADMIN),
    ("container_attachment", "business", OPERATING),
    ("event_response", "questions", CONTEXT),
    ("secondary_research", "risk", CONTEXT),
])
def test_single_catalog_has_explicit_family_section_intents(family_id, role, expected):
    family = next(r for r in registry._CATALOG["families"] if r["id"] == family_id)
    sections = [s for s in family["sections"] if s["role"] == role]
    assert sections
    assert all(s.get("geometry_intent") == expected for s in sections)


def test_all_catalog_rules_compile_and_keep_component_origins_without_role_collapse():
    for family in registry._CATALOG["families"] + [registry._CATALOG["fallback"]]:
        rules = [dict(s, section_role=s["role"], family_id=family["id"], family_version=family["version"])
                 for s in family["sections"]]
        assert all("geometry_intent" in s for s in rules), family["id"]
        result = compiler()(sample(section_rules=rules))
        assert len(result["rules"]) == len(rules)
    for family_id in ["hk_annual_report", "hk_interim_report", "sec_10q", "offering_cn_equity"]:
        result = compiler()(resolved(family_id))
        assert len({r["rule_key"] for r in result["rules"]}) == len(result["rules"])
        assert all(r["family_id"] == family_id for r in result["rules"])


def test_admin_priority_one_does_not_disable_its_business_attachment():
    family = next(r for r in registry._CATALOG["families"] if r["id"] == "administrative_document")
    assert family["sections"][0]["priority"] == 1
    assert family["sections"][0]["geometry_intent"] == ADMIN
    assert family["sections"][1]["geometry_intent"] == OPERATING


def test_convertible_alias_gap_is_fixed_in_catalog_path_without_flattening():
    family = next(r for r in registry._CATALOG["families"] if r["id"] == "offering_cn_convertible")
    root = family["sections"][0]
    assert "本次募集资金运用" in root["heading_path"][0]
    assert "募集资金运用" in root["heading_path"][0]
    for section in family["sections"]:
        if section["role"] in {"operating_metrics", "financial_notes"}:
            assert "本次募集资金运用" in section["heading_path"][0]


def test_legacy_wire_fingerprints_only_change_with_an_explicit_policy_upgrade():
    # DU11 deliberately adds the issuer's existing business to offering policy.
    # Its golden changes alongside the source-backed sales coverage test;
    # geometry metadata alone must still never leak into the legacy wire.
    path = Path(__file__).parents[2] / "fixtures/du9_geometry_policy/legacy_profile_sha256.json"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert {r["profile_id"]: digest(r) for r in list_profiles()} == expected
    assert all("geometry_intent" not in json.dumps(r) for r in list_profiles())


def test_adopted_geometry_changes_existing_causal_hash_but_other_family_does_not(monkeypatch):
    before = resolved("sec_10q")
    original_wire = get_profile("sec_10q")
    changed = deepcopy(registry._CATALOG)
    family = next(r for r in changed["families"] if r["id"] == "sec_10q")
    family["sections"][0]["geometry_intent"] = CONTEXT
    with monkeypatch.context() as m:
        m.setattr(registry, "_CATALOG", changed)
        after = resolved("sec_10q")
        assert before["profile_version"] != after["profile_version"]
        assert before["policy_components"] != after["policy_components"]
        assert compiler()(before)["content_digest"] != compiler()(after)["content_digest"]
        assert get_profile("sec_10q") == original_wire
    unrelated = deepcopy(registry._CATALOG)
    next(r for r in unrelated["families"] if r["id"] == "cn_annual_report")["sections"][0]["geometry_intent"] = CONTEXT
    monkeypatch.setattr(registry, "_CATALOG", unrelated)
    assert resolved("sec_10q") == before


@pytest.mark.parametrize("title,form,regime,kind,expected_family", [
    ("2025年年度报告", None, "cn_exchange", "annual_report", "cn_annual_report"),
    ("2025年半年度报告", None, "cn_exchange", "semi_annual_report", "cn_interim_report"),
    ("2025年第三季度报告", None, "cn_exchange", "quarterly_report", "cn_quarterly_report"),
    ("Annual Report", None, "hkex", "annual_report", "hk_annual_report"),
    ("FORM 10-K", "10-K", "sec", "annual_report", "sec_10k"),
    ("FORM 10-Q", "10-Q", "sec", "quarterly_report", "sec_10q"),
    ("FORM 20-F", "20-F", "sec", "annual_report", "sec_20f"),
    ("首次公开发行股票招股说明书", None, "cn_exchange", "prospectus", "prospectus_cn"),
    ("向不特定对象发行可转换公司债券募集说明书", None, "cn_exchange", "convertible_bond_prospectus", "offering_cn_convertible"),
    ("投资者关系活动记录表", None, "cn_exchange", "investor_relations", "investor_qa_record"),
    ("Full Conference Call Transcript", None, "sec", "investor_call_transcript", "earnings_call_transcript"),
    ("unclassified", None, "unknown", "unknown", None),
])
def test_public_route_resolve_compile_roundtrip_is_isolated(tmp_path, title, form, regime, kind, expected_family):
    compile_policy = compiler()
    sentinel = tmp_path / "keep.txt"
    sentinel.write_bytes(b"keep original")
    initial = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, set(tmp_path.iterdir()))
    units = ([unit(f"ir{i}", i, text, kind="heading" if i < 2 else "paragraph")
              for i, text in enumerate(CN_IR_QA)] if kind == "investor_relations" else
             [unit("cover", 0, title, kind="heading"), unit("body", 1, "经营情况 Business Review")])
    data = observation(units,
                       title=title, form_type=form, regime=regime, declared_kind=kind)
    frozen = deepcopy(data)
    route = route_document(data)
    profile = registry.resolve_reading_profile(get_profile(route["profile_id"]), data, route)
    assert profile["family_policy"]["id"] == expected_family
    result = compile_policy(profile)
    assert result["profile_id"] == route["profile_id"]
    assert result["profile_version"] == profile["profile_version"]
    assert result["policy_components"] == profile["policy_components"]
    assert result["default_intent"] == UNKNOWN
    assert len(result["rules"]) == len(profile["section_rules"])
    assert compile_policy(json.loads(json.dumps(profile))) == result
    assert data == frozen
    assert (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, set(tmp_path.iterdir())) == initial


@pytest.mark.parametrize("shape", ["family", "fallback", "overlay"])
@pytest.mark.parametrize("field", ["aliases", "heading_path", "questions", "geometry_intent"])
def test_resolved_nested_values_cannot_mutate_catalog_or_later_calls(monkeypatch, shape, field):
    original_catalog = deepcopy(registry._CATALOG)
    # Even a failed regression must not leak its poisoned catalog into other tests.
    monkeypatch.setattr(registry, "_CATALOG", deepcopy(original_catalog))

    def read():
        if shape == "fallback":
            return registry.resolve_reading_profile(get_profile("generic"), observation([]),
                {"family": "unknown", "regime": "unknown"})
        return resolved("sec_10q", modifiers=(
            {"extent": "summary", "revision": "amended"} if shape == "overlay" else None))

    result = read()
    frozen = deepcopy(result)
    row = result["section_rules"][-1] if shape == "overlay" else result["section_rules"][0]
    if field == "heading_path":
        if row[field]:
            row[field][0].append("caller contamination")
        else:
            row[field].append(["caller contamination"])
    elif field == "geometry_intent":
        row[field]["demand_class"] = "caller contamination"
    else:
        row[field].append("caller contamination")
    assert registry._CATALOG == original_catalog
    assert read() == frozen
