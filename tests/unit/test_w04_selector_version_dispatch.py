"""New semantic policy routes explicitly; archived policies remain replayable."""
import pytest

from company_wiki.automation.narrative_generation import generation_sha256
from company_wiki.automation.narrative_selector_binding import bind_narrative_selector
from company_wiki.source_catalog import narrative_evidence as policy
from unit.test_narrative_business_recall import FIXTURE, package_fingerprint
from unit.test_narrative_generation import manifest
from unit.test_narrative_selector_binding import parsed_fixture


@pytest.mark.parametrize("version,expected", [
    ("0.6.0", "11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f"),
    ("0.7.0", "c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478"),
    ("0.7.1", "c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478"),
])
def test_explicit_archived_selector_keeps_real_ordered_fingerprint(version, expected):
    package = policy.select_narrative_evidence(parsed_fixture(), title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=version)
    assert package_fingerprint(package) == expected


def test_default_semantic_policy_is_public_and_bound_once():
    assert policy.NARRATIVE_SELECTOR_VERSION == "0.8.0"
    bound = bind_narrative_selector()
    assert bound.selector_version == "0.8.0"
    assert "0.8.0" in policy.SUPPORTED_NARRATIVE_SELECTOR_VERSIONS


@pytest.mark.parametrize("version,semantic,native", [
    ("0.7.0", False, False), ("0.7.1", False, True), ("0.8.0", True, True),
])
def test_business_context_upgrade_is_explicit_version_route(monkeypatch, version, semantic, native):
    observed = []
    original = policy.enrich_business_groups
    def spy(*args, **kwargs):
        observed.append((kwargs.get("preserve_operating_context", False),
                         kwargs.get("respect_native_structure", False)))
        # The actual leaf is independently verified against source business fixtures.
        return original(*args, **kwargs)
    monkeypatch.setattr(policy, "enrich_business_groups", spy)
    policy.select_narrative_evidence(parsed_fixture(), title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=version)
    assert observed == [(semantic, native)]


def test_new_selector_changes_content_generation_without_new_permission():
    current = manifest()
    assert current["execution_versions"]["selector"] == "0.8.0"
    archived = manifest(versions={**current["execution_versions"], "selector": "0.7.1"})
    assert generation_sha256(current) != generation_sha256(archived)
    for field in ("source_ref", "source_metadata", "model", "profile", "parser_component"):
        assert current[field] == archived[field]


@pytest.mark.parametrize("version,expected", [
    ("0.7.1", {"context-restored", "context-unrestored", "business-removed"}),
    ("0.8.0", {"context-unrestored", "business-removed"}),
])
def test_restoration_crosses_the_selection_boundary_only_for_new_policy(monkeypatch, version, expected):
    from types import SimpleNamespace
    observed = []
    original_context = policy.enrich_context_groups
    original_finalize = policy.finalize_selection
    def context(*args, **kwargs):
        result = original_context(*args, **kwargs)
        return SimpleNamespace(candidates=result.candidates, group_ids=result.group_ids,
            excluded_context_unit_ids=frozenset({"context-restored", "context-unrestored"}))
    def business(*args, **kwargs):
        return SimpleNamespace(candidates=kwargs["initial_candidates"], group_ids=kwargs["initial_group_ids"],
            excluded_unit_ids=frozenset({"business-removed"}), restored_unit_ids=frozenset({"context-restored"}))
    def final(*args, **kwargs):
        observed.append(set(kwargs["excluded_context_unit_ids"]))
        return original_finalize(*args, **kwargs)
    monkeypatch.setattr(policy, "enrich_context_groups", context)
    monkeypatch.setattr(policy, "enrich_business_groups", business)
    monkeypatch.setattr(policy, "finalize_selection", final)
    policy.select_narrative_evidence(parsed_fixture(), title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=version)
    assert observed == [expected]


@pytest.mark.parametrize("version,expected", [("0.6.0", "legacy"), ("0.7.0", "legacy"), ("0.7.1", "legacy"), ("0.8.0", "semantic_coverage/1")])
def test_public_selector_passes_explicit_budget_policy(monkeypatch, version, expected):
    seen = []
    original = policy.finalize_selection
    def spy(*args, **kwargs):
        seen.append(kwargs["budget_policy"])
        return original(*args, **kwargs)
    monkeypatch.setattr(policy, "finalize_selection", spy)
    policy.select_narrative_evidence(parsed_fixture(), title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=version)
    assert seen == [expected]
