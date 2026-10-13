"""ROOT cross-lane contract: routing must actually inform package ordering.

The three lanes are independent pure packages, so nothing inside them can catch a
mismatch between *what one lane returns* and *what another lane expects*. This module
covers exactly that seam.

The defect this locks down was real: ``build_dependency_packages`` read
``route["section_priorities"]``, but ``route_document`` (the profiles lane) does not
return that key -- it lives on ``get_profile(route["profile_id"])``. The result was that
every document silently received the same generic priority order, so routing a document
had no effect on what the reader looked at first. Nothing failed; the output was just
quietly less informed. A no-op integration is exactly the kind of bug that unit tests on
either side of the seam cannot see.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding.orchestration import (  # noqa: E402
    build_dependency_packages,
)
from company_wiki.document_understanding.profiles import (  # noqa: E402
    get_profile,
    route_document,
)


def _observation(*, title: str, declared_kind: str, regime: str, units):
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "opaque-source-id", "source_sha256": "opaque-digest"},
        "metadata": {
            "title": title,
            "declared_kind": declared_kind,
            "regime": regime,
            "form_type": None,
            "mime_type": "application/pdf",
            "language": "zh",
        },
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": list(units),
    }


def _unit(unit_id, ordinal, text, *, kind="paragraph"):
    return {
        "unit_id": unit_id,
        "ordinal": ordinal,
        "locator": f"opaque-locator-{ordinal + 1}",
        "page": 1,
        "text": text,
        "kind": kind,
        "language": "zh",
        "role": None,
    }


def _annual_observation():
    units = [
        _unit("u1", 0, "第一节 释义", kind="heading"),
        _unit("u2", 1, "第三节 管理层讨论与分析", kind="heading"),
        _unit("u3", 2, "公司持续保持国际氮化镓基MOCVD 设备市场领先地位。"),
        _unit("u4", 3, "未来发展展望：公司将扩大产能。"),
        _unit("u5", 4, "第四节 公司治理"),
    ]
    return _observation(
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        units=units,
    )


def test_route_key_absent_from_route_is_the_documented_shape():
    """The seam exists because these two calls return different objects."""
    route = route_document(_annual_observation())
    profile = get_profile(route["profile_id"])
    assert "section_priorities" not in route
    assert "section_priorities" in profile
    assert profile["profile_id"] == route["profile_id"]


def test_profile_changes_package_priority_order():
    """Passing the profile must change ordering; passing only the route must not."""
    from company_wiki.document_understanding.orchestration import _role_priority

    route = route_document(_annual_observation())
    profile = get_profile(route["profile_id"])

    generic = _role_priority(None)
    route_only = _role_priority(route)
    with_profile = _role_priority(route, profile)

    # Route alone is documented as a valid but generic result.
    assert route_only == generic
    # The profile must actually move at least one section role.
    assert with_profile != generic
    # Adopt the declared priorities; a data-only policy need not retain the
    # old hardcoded risk band. A changed instruction must change the rank.
    for entry in profile["section_priorities"]:
        assert with_profile[entry["section_role"]] == 4 - entry["priority"]
    changed = get_profile(route["profile_id"])
    risk = next(row for row in changed["section_priorities"] if row["section_role"] == "risk")
    risk["priority"] = 1 if risk["priority"] != 1 else 3
    assert _role_priority(route, changed)["risk"] == 4 - risk["priority"]
    assert _role_priority(route, changed)["risk"] != with_profile["risk"]
    assert _role_priority(route, profile) == with_profile


def test_build_dependency_packages_accepts_profile_and_reorders():
    """A real package build must order by the profile, not by a constant."""
    units = (
        _unit("u1", 0, "第四节 公司治理", kind="heading"),
        _unit("u2", 1, "公司治理情况说明。"),
    )
    observation = _observation(
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        units=units,
    )
    route = route_document(observation)
    profile = get_profile(route["profile_id"])

    structure = {
        "schema_version": "du-structure/1",
        "source_ref": observation["source_ref"],
        "sections": [
            {
                "section_id": "s1",
                "parent_id": None,
                "heading_unit_ids": ["u1"],
                "body_unit_ids": ["u2"],
                "section_role": "outlook",
                "language": "zh",
                "confidence": "high",
                "basis": ["heading_level"],
            },
            {
                "section_id": "s2",
                "parent_id": None,
                "heading_unit_ids": [],
                "body_unit_ids": [],
                "section_role": "financial_notes",
                "language": "zh",
                "confidence": "medium",
                "basis": ["reading_order"],
            },
        ],
        "semantic_units": [
            {
                "semantic_id": "m1",
                "kind": "paragraph_event",
                "section_ids": ["s1"],
                "member_unit_ids": ["u1", "u2"],
                "anchor_unit_ids": ["u2"],
                "required_context_unit_ids": ["u2"],
                "completeness": "complete",
                "diagnostics": [],
            },
            {
                "semantic_id": "m2",
                "kind": "risk",
                "section_ids": ["s2"],
                "member_unit_ids": ["u1"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": ["u1"],
                "completeness": "complete",
                "diagnostics": [],
            },
        ],
        "relations": [],
        "coverage": {},
        "diagnostics": [],
    }

    without_profile = build_dependency_packages(structure, route=route)
    with_profile = build_dependency_packages(structure, route=route, profile=profile)

    priority = {p["package_id"]: p["priority"] for p in with_profile["packages"]}
    assert priority["m1"] > priority["m2"], "outlook must outrank financial_notes"

    # Both calls are valid and produce the same membership: only ordering differs.
    ids_without = [p["package_id"] for p in without_profile["packages"]]
    ids_with = [p["package_id"] for p in with_profile["packages"]]
    assert sorted(ids_without) == sorted(ids_with)


def test_profile_never_removes_a_package():
    """Prioritisation must not become a filter: routing never deletes evidence."""
    route = route_document(_annual_observation())
    profile = get_profile(route["profile_id"])

    structure = {
        "schema_version": "du-structure/1",
        "source_ref": {},
        "sections": [
            {
                "section_id": "s1",
                "parent_id": None,
                "heading_unit_ids": [],
                "body_unit_ids": ["u1"],
                "section_role": "administrative",
                "language": "zh",
                "confidence": "low",
                "basis": ["reading_order"],
            }
        ],
        "semantic_units": [
            {
                "semantic_id": "m1",
                "kind": "background",
                "section_ids": ["s1"],
                "member_unit_ids": ["u1"],
                "anchor_unit_ids": ["u1"],
                "required_context_unit_ids": ["u1"],
                "completeness": "complete",
                "diagnostics": [],
            }
        ],
        "relations": [],
        "coverage": {},
        "diagnostics": [],
    }
    result = build_dependency_packages(structure, route=route, profile=profile)
    assert [p["package_id"] for p in result["packages"]] == ["m1"]


def test_unknown_profile_id_is_a_real_error_not_a_silent_fallback():
    """A broken route/profile pairing must surface, not degrade quietly."""
    with pytest.raises((KeyError, ValueError)):
        get_profile("definitely_not_a_profile")


def test_every_profile_id_the_router_can_return_is_resolvable():
    """Exhaustive seam check: route -> get_profile must never dead-end."""
    shapes = [
        _annual_observation(),
        _observation(
            title="投资者关系管理制度",
            declared_kind="ir_policy",
            regime="cn_exchange",
            units=[_unit("u1", 0, "投资者关系管理制度", kind="heading")],
        ),
        _observation(
            title=None,
            declared_kind="unknown",
            regime="unknown",
            units=[_unit("u1", 0, "unstructured note")],
        ),
    ]
    for observation in shapes:
        route = route_document(observation)
        profile = get_profile(route["profile_id"])
        assert profile["family"] == route["family"] or profile["family"] == "unknown"
        assert profile["profile_version"] == route["profile_version"]
