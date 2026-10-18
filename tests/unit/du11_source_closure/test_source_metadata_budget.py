"""Measure actual source-container visits, not machine-dependent elapsed time."""
import pytest
from collections.abc import Mapping
from dataclasses import fields, is_dataclass

from company_wiki.source_catalog.narrative_reading import _prose_reading_packages
from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_continuity import native, source_case


class CountedIds(list):
    def __init__(self, values):
        super().__init__(values)
        self.visits = 0

    def __iter__(self):
        for value in super().__iter__():
            self.visits += 1
            yield value


def snapshot(value):
    """Copy all IR fields, including immutable mapping metadata, without pickle."""
    if is_dataclass(value):
        return {field.name: snapshot(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: snapshot(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(snapshot(item) for item in value)
    return value


@pytest.mark.parametrize("count", [16, 32])
def test_source_container_context_is_indexed_once_instead_of_for_every_member(count):
    parsed, pipeline = source_case(["公司已向客户交付新型设备。" for _ in range(count)])
    package = pipeline["packages"]["packages"][0]
    observed = CountedIds(package["member_unit_ids"])
    package["member_unit_ids"] = observed
    packages, _, _, _ = _prose_reading_packages(parsed, pipeline)
    assert len(packages) == count
    # Small fixed passes are permitted; rebuilding a whole-container member
    # set for every separate body member is quadratic and exceeds this bound.
    assert observed.visits <= 12 * count


def test_exhausted_parent_budget_does_not_start_an_unmetered_geometry_scan(monkeypatch):
    from company_wiki.document_understanding import narrative_continuity
    from company_wiki.resource_budget import WorkBudget

    parsed, pipeline = source_case(["公司开展客户生产验", "证，尚未量产。"])
    calls = []
    original = narrative_continuity._Analysis.native

    def observed(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(narrative_continuity._Analysis, "native", observed)
    candidates, _, _, complete, _ = reading._candidates(parsed, pipeline, work_budget=WorkBudget(0))
    assert not candidates and not complete
    assert calls == []


def test_geometry_scopes_charge_the_existing_parent_and_never_clone_its_balance():
    from company_wiki.document_understanding.narrative_continuity import build_native_continuity
    from company_wiki.resource_budget import WorkBudget

    rows = [native("公司开展客户生产验", 0), native("证，尚未量产。", 1)]
    views = [r[0] for r in rows]
    provenance = {r[0]["unit_id"]: r[1] for r in rows}
    profiles = {r[0]["unit_id"]: r[2] for r in rows}
    parent = WorkBudget(100)
    first = build_native_continuity(views, provenance=provenance, unit_profiles=profiles, work_budget=parent)
    second = build_native_continuity(views, provenance=provenance, unit_profiles=profiles, work_budget=parent)
    assert first["windows"] and second["windows"]
    assert parent.used == first["work_units"] + second["work_units"] > 0
    before = parent.used
    partial = build_native_continuity(views, provenance=provenance, unit_profiles=profiles,
                                     work_budget=parent, limits={"max_work_units": 2})
    assert not partial["complete"]
    assert parent.used == before + partial["work_units"]
    assert partial["work_units"] <= 2
    assert not parent.exhausted  # A phase ceiling does not exhaust other phases.


@pytest.mark.parametrize("limit", [0, 1, 1000])
def test_large_real_context_fanout_is_reserved_before_expansion(limit, monkeypatch):
    from company_wiki.document_understanding import narrative_continuity
    from company_wiki.resource_budget import WorkBudget

    parsed, pipeline = source_case(["公司已向客户交付新型设备。" for _ in range(96)])
    package = pipeline["packages"]["packages"][0]
    ids = [u.unit_id for u in parsed.units]
    body, context = CountedIds(ids[:32]), CountedIds(ids[32:])
    package.update(member_unit_ids=body, anchor_unit_ids=ids[:1], required_context_unit_ids=context)
    before = snapshot(parsed)
    calls = []
    original = narrative_continuity._Analysis.native

    def observed(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(narrative_continuity._Analysis, "native", observed)
    parent = WorkBudget(limit)
    candidates, metadata, eligible, complete, withheld = reading._candidates(parsed, pipeline, work_budget=parent)
    assert not candidates and not metadata and not eligible and not complete
    assert withheld[0]["reason"] == "OPERATING_WORK_BUDGET"
    assert parent.exhausted and parent.used <= limit
    assert not calls
    assert body.visits <= len(body) and context.visits <= len(context)
    assert snapshot(parsed) == before


def test_section_index_reserves_before_heading_iteration():
    from company_wiki.resource_budget import WorkBudget

    parsed, pipeline = source_case(["公司已向客户交付新型设备。" for _ in range(96)])
    ids = [u.unit_id for u in parsed.units]
    heads, body = CountedIds(ids[:32]), CountedIds(ids[32:])
    pipeline["structure"]["sections"] = [{"section_id": "business",
        "heading_unit_ids": heads, "body_unit_ids": body}]
    parent = WorkBudget(300)
    candidates, _, _, complete, _ = reading._candidates(parsed, pipeline, work_budget=parent)
    assert not candidates and not complete and parent.exhausted
    assert heads.visits == body.visits == 0


def test_native_section_reserves_before_copying_any_heading_or_body():
    from company_wiki.document_understanding.narrative_continuity import build_native_continuity
    from company_wiki.resource_budget import WorkBudget

    heads, body = CountedIds(range(32)), CountedIds(range(32, 96))
    result = build_native_continuity([], provenance={}, sections=[{
        "section_id": "business", "heading_unit_ids": heads, "body_unit_ids": body}],
        work_budget=WorkBudget(0))
    assert not result["complete"] and result["work_units"] == 0
    assert heads.visits == body.visits == 0

