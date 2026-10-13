"""ROOT: profile-driven summary request assembly (implementation.md step 5).

The plan requires the profile to drive summary aggregation: the profile supplies the focus,
the preferred semantic units and the negative hints. Until this module existed nothing read
``summary_focus`` at all, so a summary would have been written from a generic instruction.

These tests lock the two properties that make the request usable as evidence:

* every materialised member keeps the provenance that lets it be replayed to the original,
  and a unit absent from the observation is dropped rather than invented;
* a budget cut is reported as ``deferred``, and what was never read is reported as
  ``unread`` -- neither may quietly become a claim of completeness.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import (  # noqa: E402
    SUMMARY_INPUT_SCHEMA_VERSION,
    build_summary_input,
    understand_units,
)


class _Coords:
    def __init__(self, page=1):
        self.page_number = page
        self.row_index = None
        self.table_index = None
        self.column_index = None


class _Unit:
    def __init__(self, unit_id, text, *, page=1, kind="pdf_text_block", role="company_filing"):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = kind
        self.source_role = role
        self.language = "zh"
        self.coordinates = _Coords(page)
        self.metadata = {"source_locator": f"loc:v1/page:{page}/paragraph:{unit_id}"}


def _annual_units():
    return [
        _Unit("u1", "公司代码：688012", page=1),
        _Unit("u2", "2025 年年度报告", page=1),
        _Unit("u3", "第三节 管理层讨论与分析", page=9),
        _Unit("u4", "报告期内公司实现营业收入同比增长约30%。", page=13),
        _Unit("u5", "公司计划在未来两年扩大产能。", page=14),
        _Unit("u6", "公司现无生产VC（碳酸亚乙烯酯）的情况。", page=15),
        _Unit("u7", "第四节 公司治理", page=42),
    ]


def _pipeline(*, units=None, title="某公司：2025年年度报告", declared_kind="annual_report"):
    return understand_units(
        units if units is not None else _annual_units(),
        source_id="opaque-source-id",
        source_sha256="opaque-digest",
        title=title,
        declared_kind=declared_kind,
        language="zh",
    )


def test_summary_input_has_the_frozen_shape():
    request = build_summary_input(_pipeline())
    assert request["schema_version"] == SUMMARY_INPUT_SCHEMA_VERSION
    for key in (
        "source_ref",
        "profile_id",
        "profile_version",
        "focus",
        "prefer_semantic_units",
        "section_priorities",
        "negative_hints",
        "constraints",
        "evidence_packages",
        "budget",
        "deferred",
        "unread",
    ):
        assert key in request, key


def test_focus_comes_from_the_profile_not_a_constant():
    """A different document type must produce a different focus."""
    annual = build_summary_input(_pipeline())
    admin = build_summary_input(
        _pipeline(
            units=[_Unit("u1", "投资者关系管理制度"), _Unit("u2", "第一章 总则")],
            title="某公司：投资者关系管理制度",
            declared_kind="ir_policy",
        )
    )
    assert annual["focus"]
    assert admin["focus"]
    assert annual["focus"] != admin["focus"]
    assert annual["profile_id"] != admin["profile_id"]


def test_profile_version_matches_the_route():
    result = _pipeline()
    request = build_summary_input(result)
    assert request["profile_version"] == result["route"]["profile_version"]
    assert request["profile_id"] == result["route"]["profile_id"]


def test_every_member_keeps_replayable_provenance():
    """A summary claim must be able to point back at the original."""
    request = build_summary_input(_pipeline())
    assert request["evidence_packages"], "the sample must yield at least one package"
    seen = 0
    for package in request["evidence_packages"]:
        for member in package["members"]:
            seen += 1
            assert member["unit_id"]
            assert member["locator"], "a member without a locator cannot be replayed"
            assert member["page"] is not None
    assert seen > 0


def test_members_reference_real_observation_units():
    result = _pipeline()
    request = build_summary_input(result)
    known = {u["unit_id"] for u in result["observation"]["units"]}
    cited = {
        member["unit_id"]
        for package in request["evidence_packages"]
        for member in package["members"]
    }
    assert cited <= known


def test_unit_absent_from_the_observation_is_dropped_not_invented():
    """A package may reference a unit the observation lost; the request must not fabricate it."""
    result = _pipeline()
    tampered = copy.deepcopy(result)
    first = tampered["packages"]["packages"][0]
    first["member_unit_ids"] = list(first["member_unit_ids"]) + ["ghost-unit"]
    request = build_summary_input(tampered)
    cited = {
        member["unit_id"]
        for package in request["evidence_packages"]
        for member in package["members"]
    }
    assert "ghost-unit" not in cited


def test_package_budget_is_reported_as_deferred():
    """A cut must be visible, never silently dropped."""
    result = _pipeline()
    request = build_summary_input(result, max_packages=1)
    assert request["budget"]["packages_used"] <= 1
    if result["packages"]["package_count"] > 1:
        assert request["deferred"], "dropped packages must be listed"
        assert all(item["reason"] == "PACKAGE_BUDGET" for item in request["deferred"])


def test_char_budget_is_reported_as_deferred():
    result = _pipeline()
    request = build_summary_input(result, max_chars=1)
    assert request["budget"]["chars_used"] <= 1
    reasons = {item["reason"] for item in request["deferred"]}
    assert reasons & {"CHAR_BUDGET", "EMPTY_TEXT"}


def test_budget_accounting_matches_the_materialised_text():
    request = build_summary_input(_pipeline())
    counted = sum(
        len(member["text"])
        for package in request["evidence_packages"]
        for member in package["members"]
    )
    assert request["budget"]["chars_used"] == counted


def test_unread_reports_scan_gaps():
    result = understand_units(
        _annual_units(),
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
        native_scan="partial",
        opaque_pages=[7, 8],
        deferred_pages=[9],
    )
    request = build_summary_input(result)
    assert request["unread"]["native_scan"] == "partial"
    assert request["unread"]["opaque_pages"] == [7, 8]
    # Opaque and deferred are different facts about a page and must not be merged.
    assert request["unread"]["deferred_pages"] == [9]


def test_unread_keys_match_what_structure_actually_emits():
    """A key this module reads but structure never emits would silently report an empty gap."""
    result = understand_units(
        _annual_units(),
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    coverage = result["structure"]["coverage"]
    request = build_summary_input(result)
    assert set(request["unread"]) - {"structure_complete"} <= set(coverage) | {
        "native_scan",
        "opaque_pages",
        "deferred_pages",
        "deferred_unit_ids",
        "unassigned_unit_ids",
    }
    for key in ("native_scan", "opaque_pages", "deferred_unit_ids", "unassigned_unit_ids"):
        assert key in coverage, f"structure no longer emits {key!r}; summary_input reads it"


def test_constraints_forbid_translation_and_investment_conclusions():
    request = build_summary_input(_pipeline())
    joined = " ".join(request["constraints"])
    assert "原语言" in joined
    for forbidden in ("评级", "目标价", "仓位"):
        assert forbidden in joined, "the request must forbid this explicitly"


def test_negative_hints_come_from_the_profile():
    request = build_summary_input(_pipeline())
    assert request["negative_hints"]
    profile = _pipeline()["profile"]
    assert request["negative_hints"] == profile["negative_hints"]


def test_request_is_deterministic():
    first = build_summary_input(_pipeline())
    second = build_summary_input(_pipeline())
    assert first == second


def test_administrative_document_yields_an_honest_request():
    """An administrative original produces a request with the honest reason, not silence."""
    request = build_summary_input(
        _pipeline(
            units=[_Unit("u1", "投资者关系管理制度"), _Unit("u2", "第一章 总则")],
            title="某公司：投资者关系管理制度",
            declared_kind="ir_policy",
        )
    )
    codes = {item["code"] for item in request["diagnostics"]}
    assert "NO_NARRATIVE_EXPECTED" in codes
    assert request["disposition_hint"] == "administrative_candidate"


def test_package_order_is_preserved_from_the_orchestrator():
    """The request must read the document in the order the profile chose."""
    result = _pipeline()
    request = build_summary_input(result)
    ranked = [package["rank"] for package in request["evidence_packages"]]
    assert ranked == sorted(ranked)
    orchestrator_ids = [p["package_id"] for p in result["packages"]["packages"]]
    request_ids = [p["package_id"] for p in request["evidence_packages"]]
    assert request_ids == [pid for pid in orchestrator_ids if pid in set(request_ids)]


def test_exported_from_the_parent_package():
    import company_wiki.document_understanding as package

    assert "build_summary_input" in package.__all__
    assert "SUMMARY_INPUT_SCHEMA_VERSION" in package.__all__
