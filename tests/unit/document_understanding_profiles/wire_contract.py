"""Public wire contract for ``company_wiki.document_understanding.profiles``.

Frozen by ``docs/plans/document-understanding-2026-10-13/INTERFACES.md`` section 3.
This module states the contract only; it does not restate any routing expectation.

The package under test is obtained through :func:`import_profiles_module` rather than a
pytest fixture. An imported fixture whose name is also a test parameter trips ruff's
``F811`` redefinition check, so the import is expressed as an ordinary function.
"""

from __future__ import annotations

from typing import Any

ROUTE_KEYS = {
    "schema_version",
    "profile_id",
    "profile_version",
    "regime",
    "family",
    "subtype",
    "confidence",
    "reasons",
    "alternatives",
    "child_routes",
    "disposition_hint",
}

PROFILE_KEYS = {
    "profile_id",
    "profile_version",
    "family",
    "section_priorities",
    "semantic_units",
    "summary_focus",
    "negative_hints",
}

REGIMES = {"cn_exchange", "hkex", "sec", "other", "unknown"}
FAMILIES = {
    "annual",
    "interim",
    "quarterly",
    "prospectus",
    "offering",
    "results_release",
    "presentation",
    "investor_qa",
    "earnings_call",
    "administrative",
    "unknown",
}
CONFIDENCES = {"high", "medium", "low", "unknown"}
DISPOSITIONS = {"read", "generic_read", "administrative_candidate"}
SECTION_ROLES = {
    "business",
    "industry",
    "management_discussion",
    "outlook",
    "risk",
    "operating_metrics",
    "fundraising",
    "financial_notes",
    "questions",
    "administrative",
    "unknown",
}
SEMANTIC_UNITS = {
    "paragraph_event",
    "qa_exchange",
    "project",
    "operating_table",
    "risk",
    "background",
}
REQUIRED_PROFILE_IDS = {
    "cn_annual",
    "cn_interim",
    "cn_quarterly",
    "hk_periodic",
    "sec_10k",
    "sec_10q",
    "sec_20f",
    "prospectus",
    "offering",
    "investor_qa",
    "earnings_call",
    "results_release",
    "presentation",
    "administrative",
    "generic",
}


def import_profiles_module():
    """Return the package under test; a missing entry point is a real RED failure."""
    import company_wiki.document_understanding.profiles as module

    return module


def assert_route_shape(route: Any) -> None:
    """Structural assertions shared by every route test."""
    assert isinstance(route, dict), f"route must be a dict, got {type(route)!r}"
    missing = ROUTE_KEYS - set(route)
    assert not missing, f"route missing frozen keys: {sorted(missing)}"
    assert route["schema_version"] == "du-route/1"
    assert isinstance(route["profile_id"], str) and route["profile_id"]
    assert isinstance(route["profile_version"], str) and route["profile_version"]
    assert route["regime"] in REGIMES, route["regime"]
    assert route["family"] in FAMILIES, route["family"]
    assert route["subtype"] is None or isinstance(route["subtype"], str)
    assert route["confidence"] in CONFIDENCES, route["confidence"]
    assert route["disposition_hint"] in DISPOSITIONS, route["disposition_hint"]
    assert route["disposition_hint"] != "skip"
    for reason in route["reasons"]:
        assert set(reason) == {"code", "unit_ids", "detail"}
        assert isinstance(reason["code"], str) and reason["code"]
        assert isinstance(reason["unit_ids"], list)
        assert isinstance(reason["detail"], str)
    for alternative in route["alternatives"]:
        assert set(alternative) == {"profile_id", "reason"}
    for child in route["child_routes"]:
        base = {"unit_ids", "profile_id", "reason"}
        actual = {"family", "regime", "form_type", "subtype"}
        assert base <= set(child) <= base | actual
        # Older stored three-field views remain readable. A new resolved view
        # carries the entire purpose/market/form tuple, never a partial guess.
        if actual & set(child):
            assert actual <= set(child)
            assert child["family"] in FAMILIES
            assert child["regime"] in REGIMES
            assert isinstance(child["form_type"], str) and child["form_type"]
            assert child["subtype"] is None or isinstance(child["subtype"], str)
        assert isinstance(child["unit_ids"], list) and child["unit_ids"]


def assert_profile_shape(profile: Any) -> None:
    """Structural assertions shared by every ``get_profile`` test."""
    assert isinstance(profile, dict), f"profile must be a dict, got {type(profile)!r}"
    missing = PROFILE_KEYS - set(profile)
    assert not missing, f"profile missing frozen keys: {sorted(missing)}"
    assert isinstance(profile["profile_id"], str) and profile["profile_id"]
    assert isinstance(profile["profile_version"], str) and profile["profile_version"]
    assert profile["family"] in FAMILIES, profile["family"]
    assert isinstance(profile["section_priorities"], list)
    for entry in profile["section_priorities"]:
        assert set(entry) == {"section_role", "aliases", "priority"}
        assert entry["section_role"] in SECTION_ROLES, entry["section_role"]
        assert isinstance(entry["aliases"], list)
        assert all(isinstance(alias, str) and alias for alias in entry["aliases"])
        assert entry["priority"] in (1, 2, 3), entry["priority"]
    assert isinstance(profile["semantic_units"], list)
    for semantic_unit in profile["semantic_units"]:
        assert semantic_unit in SEMANTIC_UNITS, semantic_unit
    assert isinstance(profile["summary_focus"], str) and profile["summary_focus"]
    assert isinstance(profile["negative_hints"], list)
