"""ROOT end-to-end: parsed units -> observation -> route -> structure -> packages.

This exercises the whole chain in one call, which is what a production consumer will
actually use (``implementation.md`` steps 4-5). It asserts the properties that only hold
if the stages are wired together correctly:

* the route is resolved to its profile, and the profile actually orders packages;
* each stage's own schema version survives into the combined result;
* an honest empty result is distinguished from a coverage gap.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import understand_units  # noqa: E402
from company_wiki.document_understanding.pipeline import (  # noqa: E402
    NARRATIVE_FAMILIES,
    PIPELINE_SCHEMA_VERSION,
)


class _Coordinates:
    """Stand-in for the parser's coordinate record (only the fields the adapter reads)."""

    def __init__(
        self,
        page_number,
        *,
        bbox=None,
        row_index=None,
        table_index=None,
        column_index=None,
    ):
        self.page_number = page_number
        self.bbox = bbox
        self.row_index = row_index
        self.table_index = table_index
        self.column_index = column_index


class _Unit:
    """Minimal stand-in for the parser's narrative unit shape.

    Only the attributes ``observation_adapter`` actually reads are provided, so this stub
    fails loudly if the adapter starts depending on something new.
    """

    def __init__(
        self,
        unit_id,
        text,
        *,
        page=1,
        locator=None,
        metadata=None,
        bbox=None,
        unit_kind="pdf_text_block",
        source_role=None,
        language=None,
    ):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = unit_kind
        self.source_role = source_role
        self.language = language
        self.coordinates = _Coordinates(page, bbox=bbox)
        self.locator = locator or f"loc:{unit_id}"
        # The adapter takes the locator from the unit metadata, which is where the parser
        # carries its real opaque locator; ``source_locator`` is therefore what must
        # survive verbatim into the wire.
        self.metadata = {"source_locator": self.locator, **(metadata or {})}


def _annual_units():
    return [
        _Unit("u1", "公司代码：688012", page=1),
        _Unit("u2", "2025 年年度报告", page=1),
        _Unit("u3", "第一节 释义", page=3),
        _Unit("u4", "第三节 管理层讨论与分析", page=9),
        _Unit("u5", "公司持续保持国际氮化镓基MOCVD 设备市场领先地位。", page=13),
        _Unit("u6", "报告期内公司实现营业收入同比增长。", page=14),
        _Unit("u7", "第四节 公司治理", page=42),
    ]


def test_pipeline_runs_end_to_end():
    result = understand_units(
        _annual_units(),
        source_id="opaque-source-id",
        source_sha256="opaque-passed-through-digest",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    assert result["schema_version"] == PIPELINE_SCHEMA_VERSION
    assert result["route"]["schema_version"] == "du-route/1"
    assert result["structure"]["schema_version"] == "du-structure/1"
    assert result["packages"]["schema_version"] == "du-packages/1"


def test_every_stage_schema_survives():
    """A combined result must not flatten the stages into one anonymous blob."""
    result = understand_units(
        _annual_units(),
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    assert result["route"]["profile_id"]
    assert result["profile"]["profile_id"] == result["route"]["profile_id"]
    assert "sections" in result["structure"]
    assert "packages" in result["packages"]


def test_route_and_profile_agree():
    result = understand_units(
        _annual_units(),
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    plan = result["plan"]
    assert plan["profile_id"] == result["route"]["profile_id"]
    assert plan["profile_version"] == result["route"]["profile_version"]
    assert plan["family"] == result["route"]["family"]


def test_plan_reports_read_first_roles_from_the_profile():
    """The plan must expose the profile's priority-1 roles, not a hardcoded list."""
    result = understand_units(
        _annual_units(),
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    read_first = result["plan"]["read_first_roles"]
    assert read_first, "an A-share annual profile must name at least one read-first role"
    assert set(read_first) <= {
        entry["section_role"]
        for entry in result["profile"]["section_priorities"]
        if entry["priority"] == 1
    }


def test_pipeline_does_not_mutate_input_units():
    units = _annual_units()
    before = [(u.unit_id, u.raw_text, u.coordinates.page_number, u.locator) for u in units]
    understand_units(
        units,
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    after = [(u.unit_id, u.raw_text, u.coordinates.page_number, u.locator) for u in units]
    assert after == before


def test_observation_keeps_source_ref_and_locators_verbatim():
    """The adapter must pass the opaque source identity and locators through untouched."""
    result = understand_units(
        _annual_units(),
        source_id="opaque-source-id",
        source_sha256="opaque-passed-through-digest",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    assert result["source_ref"] == {
        "source_id": "opaque-source-id",
        "source_sha256": "opaque-passed-through-digest",
    }
    locators = {unit["locator"] for unit in result["observation"]["units"]}
    assert locators == {u.locator for u in _annual_units()}


def test_administrative_document_reports_no_narrative_expected():
    """An administrative original must not be reported as a coverage failure."""
    units = [_Unit("u1", "投资者关系管理制度", page=1), _Unit("u2", "第一章 总则", page=1)]
    result = understand_units(
        units,
        source_id="s",
        source_sha256="d",
        title="某公司：投资者关系管理制度",
        declared_kind="ir_policy",
        language="zh",
    )
    codes = {item["code"] for item in result["diagnostics"]}
    assert result["route"]["family"] == "administrative"
    assert "NO_NARRATIVE_EXPECTED" in codes
    assert "NO_NARRATIVE_PACKAGES" not in codes
    assert result["plan"]["expects_business_narrative"] is False


def test_unknown_document_is_still_readable():
    units = [_Unit("u1", "some unstructured working note")]
    result = understand_units(
        units,
        source_id="s",
        source_sha256="d",
        title="",
        declared_kind="unknown",
    )
    assert result["route"]["disposition_hint"] == "generic_read"
    # Unknown purpose is not evidence that business content is absent.
    assert result["plan"]["expects_business_narrative"] is None


def test_limits_are_forwarded_and_never_raised():
    """A tightened caller budget must reach both pure lanes."""
    units = _annual_units()
    result = understand_units(
        units,
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
        limits={"max_probe_units": 1, "max_probe_chars": 1},
    )
    route_codes = {item["code"] for item in result["route"]["reasons"]}
    assert "ROUTE_PROBE_LIMIT" in route_codes
    assert result["route"]["confidence"] in {"low", "unknown"}


def test_pipeline_is_deterministic():
    kwargs = dict(
        source_id="s",
        source_sha256="d",
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        language="zh",
    )
    first = understand_units(_annual_units(), **kwargs)
    second = understand_units(_annual_units(), **kwargs)
    assert first == second


def test_narrative_families_match_the_profiles_vocabulary():
    """The pipeline's expectation set must be real families, not typos."""
    from company_wiki.document_understanding.profiles.vocabulary import FAMILIES

    assert NARRATIVE_FAMILIES <= set(FAMILIES)
    assert "administrative" not in NARRATIVE_FAMILIES
    assert "unknown" not in NARRATIVE_FAMILIES
