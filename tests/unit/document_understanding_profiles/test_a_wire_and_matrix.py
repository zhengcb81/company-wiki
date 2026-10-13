"""A-node: frozen wire, profile matrix, and counter-example RED.

Every expectation here is stated from the plan's design matrix
(``docs/plans/document-understanding-2026-10-13/design.md`` section 5) and the card's
acceptance list. No expectation is derived by reading this package's implementation.
"""

from __future__ import annotations

import json

import pytest
from fixtures.document_understanding_profiles import builders as b

from .wire_contract import (
    REQUIRED_PROFILE_IDS,
    assert_profile_shape,
    assert_route_shape,
    import_profiles_module,
)


def test_module_exposes_the_three_frozen_functions():
    """INTERFACES section 3: exactly three public entry points, Mapping in, dict out."""
    module = import_profiles_module()
    for name in ("route_document", "get_profile", "list_profiles"):
        assert callable(getattr(module, name)), name
        assert getattr(module, name).__doc__, name


def test_route_document_accepts_keyword_only_limits():
    """``limits`` is keyword-only and optional."""
    module = import_profiles_module()
    observation = b.observation(
        [b.unit("u1", 0, "2025 年年度报告", kind="heading")],
        title="2025 年年度报告",
    )
    assert module.route_document(observation) == module.route_document(
        observation, limits=None
    )
    with pytest.raises(TypeError):
        module.route_document(observation, {})


def test_list_profiles_covers_the_required_matrix():
    """INTERFACES section 3: at least these fifteen profile ids must exist."""
    listed = import_profiles_module().list_profiles()
    assert isinstance(listed, list) and listed
    ids = set()
    for profile in listed:
        assert_profile_shape(profile)
        ids.add(profile["profile_id"])
    missing = REQUIRED_PROFILE_IDS - ids
    assert not missing, f"profile matrix incomplete: {sorted(missing)}"
    assert len(ids) == len(listed), "list_profiles must not repeat a profile id"


def test_list_profiles_is_deterministic():
    module = import_profiles_module()
    assert module.list_profiles() == module.list_profiles()


def test_list_profiles_returns_a_fresh_copy():
    """A caller must not be able to mutate the shared registry."""
    module = import_profiles_module()
    first = module.list_profiles()
    first[0]["family"] = "tampered"
    assert module.list_profiles() == module.list_profiles()
    assert module.list_profiles()[0]["family"] != "tampered"


def test_get_profile_returns_every_listed_profile():
    module = import_profiles_module()
    for listed in module.list_profiles():
        profile = module.get_profile(listed["profile_id"])
        assert_profile_shape(profile)
        assert profile == listed


def test_get_profile_rejects_unknown_id():
    """A wrong id is a real data error, not an invented generic profile."""
    with pytest.raises((KeyError, ValueError)):
        import_profiles_module().get_profile("no_such_profile_id")


def test_get_profile_rejects_empty_and_non_string_ids():
    module = import_profiles_module()
    for bad in ("", None, 7):
        with pytest.raises((KeyError, ValueError, TypeError)):
            module.get_profile(bad)


def test_every_profile_is_json_serializable():
    for profile in import_profiles_module().list_profiles():
        assert json.loads(json.dumps(profile, ensure_ascii=False))


def test_every_profile_version_is_content_addressed():
    """Two profiles with different content must not share a version string."""
    versions = [
        profile["profile_version"]
        for profile in import_profiles_module().list_profiles()
    ]
    assert len(set(versions)) == len(versions)


def _assert_reading_scope(profile):
    text = json.dumps(profile, ensure_ascii=False).casefold()
    # An offering can mention the original credit-rating report as a low-value
    # source section. That document name is not an investment rating output.
    text = text.replace("信用评级报告", "")
    for forbidden in ("买入", "卖出", "目标价", "评级", "仓位"):
        assert forbidden not in text, f"{profile['profile_id']} contains {forbidden}"


def test_profiles_do_not_contain_investment_conclusions():
    """Scope boundary: reading source sections is not producing investment conclusions."""
    for profile in import_profiles_module().list_profiles():
        _assert_reading_scope(profile)


def test_credit_document_name_does_not_hide_investment_output():
    _assert_reading_scope({"profile_id": "test", "negative_hints": ["信用评级报告"]})
    for forbidden in ("买入", "卖出", "目标价", "投资评级", "仓位"):
        with pytest.raises(AssertionError):
            _assert_reading_scope({"profile_id": "test", "summary_focus": "信用评级报告；" + forbidden})


def test_profiles_do_not_leak_probe_budgets():
    """Profiles must not be able to raise a paid budget."""
    for profile in import_profiles_module().list_profiles():
        for field in ("limits", "max_probe_units", "max_probe_chars", "max_child_routes"):
            assert field not in profile


def test_route_confidence_is_a_label_not_a_percentage():
    """No calibrated probability may be emitted without calibration."""
    module = import_profiles_module()
    observation = b.observation(
        [b.unit("u1", 0, "第一节 释义", kind="heading")],
        title="2025 年年度报告",
    )
    route = module.route_document(observation)
    assert_route_shape(route)
    assert isinstance(route["confidence"], str)
    assert "%" not in route["confidence"]
