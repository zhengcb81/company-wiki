"""Pure physical owner controls; no sentence or business scope is manufactured."""

from copy import deepcopy
from collections.abc import Mapping

import pytest

from company_wiki.document_understanding import narrative_continuity as native
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
from unit.document_understanding_selection.test_reading_native_list_ancestry import (
    _source,
)


def _context_inputs(furniture=False):
    rows = [(1, "- First product shipments increased 13%.", 0, (110, 720, 550, 732))]
    if furniture:
        rows += [
            (1, "Neutral annual report", 1, (90, 780, 550, 792)),
            (2, "Neutral annual report", 0, (90, 12, 550, 24)),
        ]
    rows += [
        (
            2,
            "ii. Customer orders increased 19%.",
            1 if furniture else 0,
            (110, 70, 550, 82),
        )
    ]
    parsed = _source(rows)
    wire = build_observation(
        parsed.units, source_id=parsed.source_id, source_sha256=parsed.source_sha256
    )
    metadata = {
        u.unit_id: {
            "source_id": u.source_id,
            "paragraph_index": u.coordinates.paragraph_index,
            **{
                key: u.metadata[key]
                for key in (
                    "pdf_block",
                    "block_sha256",
                    "block_char_start",
                    "block_char_end",
                )
            },
        }
        for u in parsed.units
    }
    return wire, metadata


def _edge(wire, metadata, furniture=()):
    account = WorkBudget(10000)
    context = native.NativeSourceContext(
        wire["units"],
        provenance=metadata,
        coverage=wire["coverage"],
        work_budget=account,
    )
    left, right = wire["units"][0]["unit_id"], wire["units"][-1]["unit_id"]
    proof = context.page_neighbour(left, right, furniture_unit_ids=frozenset(furniture))
    assert 0 < account.used < account.max_work_units
    return proof


@pytest.mark.parametrize("furniture", (False, True))
def test_physical_complete_item_page_neighbour_has_no_sentence_policy(furniture):
    wire, metadata = _context_inputs(furniture)
    original = deepcopy((wire, metadata))
    skip = [u["unit_id"] for u in wire["units"][1:-1]]
    proof = _edge(wire, metadata, skip)
    assert proof is not None
    assert proof["left"] == wire["units"][0]["unit_id"]
    assert proof["right"] == wire["units"][-1]["unit_id"]
    assert set(proof["furniture_unit_ids"]) == set(skip)
    assert (wire, metadata) == original


@pytest.mark.parametrize(
    "fault",
    (
        "unknown_column",
        "missing_coverage",
        "invalid_coverage",
        "disjoint_column",
        "frame",
        "rotation",
        "font",
        "role",
        "source",
        "ordinal",
        "coverage",
        "deferred",
        "opaque",
        "lane",
        "page_gap",
        "unproven_furniture",
        "furniture_ordinal",
        "furniture_paragraph",
    ),
)
def test_native_physical_observer_rejects_unproven_boundary(fault):
    use_furniture = "furniture" in fault
    wire, metadata = _context_inputs(use_furniture)
    left, right = wire["units"][0], wire["units"][-1]
    skip = [u["unit_id"] for u in wire["units"][1:-1]]
    if fault == "unknown_column":
        left["layout"].pop("column", None)
        right["layout"].pop("column", None)
    elif fault == "disjoint_column":
        right["layout"]["column"] = 1
    elif fault == "frame":
        right["layout"]["coordinate_frame"] = "rawdict"
    elif fault == "rotation":
        right["layout"]["rotation"] = 90
    elif fault == "font":
        right["hints"]["font_runs"][0]["font_size"] = 14
    elif fault == "role":
        right["role"] = "management"
    elif fault == "source":
        right["hints"]["source_id"] = "foreign"
    elif fault == "ordinal":
        right["ordinal"] += 1
    elif fault == "missing_coverage":
        wire["coverage"].pop("opaque_pages")
    elif fault == "invalid_coverage":
        wire["coverage"]["deferred_pages"] = None
    elif fault == "coverage":
        wire["coverage"]["native_scan"] = "partial"
    elif fault == "deferred":
        wire["coverage"]["deferred_pages"] = [2]
    elif fault == "opaque":
        wire["coverage"]["opaque_pages"] = [1]
    elif fault == "lane":
        right["layout"]["bbox"] = [400, 70, 550, 82]
    elif fault == "page_gap":
        right["page"] = 3
    elif fault == "unproven_furniture":
        skip = []
    elif fault == "furniture_ordinal":
        wire["units"][1]["ordinal"] += 1
    elif fault == "furniture_paragraph":
        metadata[wire["units"][1]["unit_id"]]["paragraph_index"] += 1
    assert _edge(wire, metadata, skip) is None


def test_zero_shared_work_rejects_before_native_index_allocation():
    class NeverRead(dict):
        def __iter__(self):
            raise AssertionError("must reserve before copying/indexing native units")

        def get(self, *args):
            raise AssertionError("must reserve before reading native fields")

    account = WorkBudget(0)
    with pytest.raises(WorkBudgetExceeded):
        native.NativeSourceContext(
            [NeverRead()],
            provenance=NeverRead(),
            coverage=NeverRead(),
            work_budget=account,
        )
    assert account.used == 0


def _native_structure(mode="cross_page", fault=None):
    from dataclasses import replace
    from company_wiki.document_understanding.pipeline import understand_units
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source,
    )

    parsed, owned = _list_source(mode)
    target = owned["second"]
    units = list(parsed.units)
    if fault in {"font", "rotation", "lane", "column", "unindented"}:

        def mutable(value):
            if isinstance(value, Mapping):
                return {key: mutable(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [mutable(item) for item in value]
            return value

        meta = mutable(target.metadata)
        layout = meta["reading_layout"]["layout"]
        if fault == "font":
            meta["reading_layout"]["upstream_hints"]["font_runs"][0]["font_size"] = 14
        elif fault == "rotation":
            layout["rotation"] = 90
        elif fault == "lane":
            layout["bbox"] = [400, 70, 550, 82]
        elif fault == "column":
            layout.pop("column")
        else:
            layout["bbox"] = [90, 70, 550, 82]
        units[units.index(target)] = replace(target, metadata=meta)
    before = [
        (u.unit_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
        for u in units
    ]
    budget = WorkBudget(16_000_000)
    result = understand_units(
        units,
        source_id=parsed.source_id,
        source_sha256=parsed.source_sha256,
        title="Neutral annual report",
        declared_kind="annual_report",
        native_scan="partial" if fault == "partial" else "complete",
        deferred_pages=(2,) if fault == "deferred" else (),
        opaque_pages=(1,) if fault == "opaque" else (),
        work_budget=budget,
    )
    assert [
        (u.unit_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
        for u in units
    ] == before
    sections = {
        uid: section
        for section in result["structure"]["sections"]
        for uid in section["body_unit_ids"]
    }
    return result, owned, sections


@pytest.mark.parametrize(
    "mode",
    (
        "same_page",
        "same_page_roman",
        "cross_page",
        "cross_page_roman",
        "cross_page_furniture",
    ),
)
def test_structure_owns_parent_and_explicit_original_dependencies(mode):
    from company_wiki.document_understanding.structure.contract import (
        NativeSourceDependencies,
    )

    result, owned, sections = _native_structure(mode)
    required = {owned["parent"].unit_id, owned["intro"].unit_id}
    assert required <= set(sections[owned["second"].unit_id]["heading_unit_ids"])
    assert (
        owned["sibling"].unit_id
        not in sections[owned["second"].unit_id]["heading_unit_ids"]
    )
    assert (
        owned["parent"].unit_id
        not in sections[owned["sibling_body"].unit_id]["heading_unit_ids"]
    )
    semantics = result["structure"]["semantic_units"]
    context_field = "required_context_by_unit_id"
    source_field = "required_source_unit_ids_by_unit_id"
    assert {context_field, source_field, "native_source_proofs_by_unit_id"} == set(
        NativeSourceDependencies.__optional_keys__
    )
    maps = {
        target: ids
        for semantic in semantics
        for target, ids in semantic.get(context_field, {}).items()
    }
    witness = {
        target: ids
        for semantic in semantics
        for target, ids in semantic.get(source_field, {}).items()
    }
    if mode.startswith("cross_page"):
        assert required == set(maps[owned["second"].unit_id])
        assert owned["first"].unit_id not in maps  # dependency is per original target
    else:
        assert not maps and not witness
    furniture = {
        uid
        for d in result["structure"]["diagnostics"]
        if d["code"] == "REPEATED_RUNNING_HEADER"
        for uid in d["unit_ids"]
    }
    if mode.endswith("furniture"):
        assert len(furniture) == 2
        assert set(witness[owned["second"].unit_id]) == furniture | {
            owned["first"].unit_id
        }
        assert not furniture.intersection(maps[owned["second"].unit_id])
    elif mode.startswith("cross_page"):
        assert set(witness[owned["second"].unit_id]) == {owned["first"].unit_id}
    else:
        assert not witness


@pytest.mark.parametrize(
    "fault",
    (
        "font",
        "rotation",
        "lane",
        "column",
        "unindented",
        "partial",
        "deferred",
        "opaque",
    ),
)
def test_early_structure_cannot_borrow_parent_without_physical_evidence(fault):
    _result, owned, sections = _native_structure(fault=fault)
    assert (
        owned["parent"].unit_id
        not in sections[owned["second"].unit_id]["heading_unit_ids"]
    )


@pytest.mark.parametrize(
    "module",
    (
        "company_wiki.source_catalog.narrative_native_dependencies",
        "company_wiki.source_catalog.narrative_reading",
        "company_wiki.document_understanding.pipeline",
        "company_wiki.document_understanding.structure",
        "company_wiki.document_understanding.structure.sections",
        "company_wiki.document_understanding.narrative_continuity",
        "company_wiki.document_understanding.observation_adapter",
    ),
)
def test_actual_early_native_owner_bytes_invalidate_complete_cache(module, monkeypatch):
    from importlib import import_module
    from pathlib import Path
    from company_wiki.automation.narrative_generation import (
        current_reading_decision_matches,
    )
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import (
        freeze_decision_dependencies,
    )
    from unit.document_understanding_selection.test_reading_decision_inventory import (
        _real_interim_pipeline,
    )

    pipeline = _real_interim_pipeline()
    pipeline["observation"]["metadata"]["mime_type"] = "text/html"
    dependencies = freeze_decision_dependencies(
        inventory.build_decision_trace(pipeline)
    )
    assert dependencies["status"] == "complete"
    manifest = {
        "reading_dependencies": dependencies,
        "selection_generation": {"decision_digest": dependencies["decision_digest"]},
    }
    assert current_reading_decision_matches(manifest)
    target = Path(import_module(module).__file__).resolve()
    actual = Path.read_bytes
    with monkeypatch.context() as patch:

        def changed(path):
            raw = actual(path)
            return (
                raw + b"\n# native owner byte control\n"
                if path.resolve() == target
                else raw
            )

        patch.setattr(Path, "read_bytes", changed)
        assert not current_reading_decision_matches(manifest)
    assert current_reading_decision_matches(manifest)


@pytest.mark.parametrize(
    "barrier",
    (
        "ordinary",
        "heading",
        "sibling",
        "page_gap",
        "unproven_header",
        "roman_word",
        "third_page",
        "unit_limit",
    ),
)
def test_native_list_scope_stops_at_real_barrier_and_total_limits(barrier):
    from company_wiki.document_understanding.pipeline import understand_units

    parent = "(1) Laboratory services generated revenue of USD 23 million."
    intro = "During the reporting period:"
    first = "- Product shipments increased 13%."
    target = "ii. Customer contracts increased 17%."
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, parent, 1, (90, 640, 550, 672)),
        (1, intro, 1, (90, 640, 550, 672)),
        (1, first, 2, (110, 720, 550, 732)),
    ]
    page, block, top = 2, 0, 70
    if barrier in {"ordinary", "heading", "sibling", "unproven_header"}:
        middle = {
            "ordinary": "The following paragraph describes local administration.",
            "heading": "二、风险因素",
            "sibling": "(2) Engineering service update:",
            "unproven_header": "Unproven page title",
        }[barrier]
        rows.append((2, middle, 0, (90, 20, 550, 32)))
        block, top = 1, 90
    elif barrier == "page_gap":
        page = 3
    elif barrier == "roman_word":
        target = "civil. Customer contracts increased 17%."
    elif barrier == "third_page":
        rows.append((2, "- Product delivery increased 16%.", 0, (110, 70, 550, 82)))
        rows.append((2, "- Product orders increased 18%.", 1, (110, 720, 550, 732)))
        page = 3
    elif barrier == "unit_limit":
        # One real open list must not roll a fresh24-unit window for each edge.
        rows = rows[:3] + [
            (
                1,
                f"- Native list item {n} remains complete.",
                n + 2,
                (110, 680 + n * 4, 550, 683 + n * 4),
            )
            for n in range(22)
        ]
    rows.append((page, target, block, (110, top, 550, top + 12)))
    parsed = _source(rows)
    result = understand_units(
        parsed.units,
        source_id=parsed.source_id,
        source_sha256=parsed.source_sha256,
        declared_kind="annual_report",
        work_budget=WorkBudget(16_000_000),
    )
    wanted = next(u for u in parsed.units if u.raw_text == target)
    opener = next(u for u in parsed.units if u.raw_text == parent)
    section = next(
        section
        for section in result["structure"]["sections"]
        if wanted.unit_id in section["body_unit_ids"]
    )
    assert opener.unit_id not in section["heading_unit_ids"]


@pytest.mark.parametrize(
    "mode", ("cross_page", "cross_page_furniture", "cross_page_roman")
)
def test_production_uses_one_call_local_physical_observation_per_original(
    monkeypatch, mode
):
    from collections import Counter
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source,
    )

    parsed, owned = _list_source(mode)
    counts = Counter()
    observer = native.observe_native_source_unit

    def observe(unit, provenance, charge):
        counts[unit["unit_id"]] += 1
        return observer(unit, provenance, charge)

    monkeypatch.setattr(native, "observe_native_source_unit", observe)
    selected = reading.select_reading_evidence(
        parsed,
        title="中性年度报告",
        existing_kind="annual_report",
        max_selected=96,
        max_chars=48000,
    )
    assert selected.evidence_spans
    assert counts[owned["first"].unit_id] == counts[owned["second"].unit_id] == 1
    assert max(counts.values()) == 1


def test_call_local_physical_context_is_not_serialized_into_pipeline():
    import json
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source,
    )

    parsed, _owned = _list_source("cross_page")
    contexts = {}
    budget = WorkBudget(16_000_000)
    result = reading._understand(
        parsed,
        title="中性年度报告",
        kind="annual_report",
        mime_type="application/pdf",
        work_budget=budget,
        _native_contexts=contexts,
    )
    assert set(contexts) == {parsed.source_id}
    assert contexts[parsed.source_id].work_budget is budget
    assert json.loads(json.dumps(result))["schema_version"] == "du-pipeline/1"


def test_each_original_parent_reuses_its_own_native_ordinal_space(monkeypatch):
    from collections import Counter
    from dataclasses import replace
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source,
    )

    first, owned = _list_source("cross_page")
    second = _source(
        [
            (
                u.coordinates.page_number,
                u.raw_text.replace("20%", "29%"),
                u.metadata["pdf_block"],
                tuple(u.metadata["reading_layout"]["layout"]["bbox"]),
            )
            for u in first.units
        ]
    )
    combined = replace(first, units=first.units + second.units)
    counts = Counter()
    observer = native.observe_native_source_unit

    def observe(unit, provenance, charge):
        counts[unit["unit_id"]] += 1
        return observer(unit, provenance, charge)

    monkeypatch.setattr(native, "observe_native_source_unit", observe)
    selected = reading.select_reading_evidence(
        combined,
        title="Annual report",
        existing_kind="annual_report",
        max_selected=96,
        max_chars=48000,
    )
    wanted = {owned["second"].raw_text, owned["second"].raw_text.replace("20%", "29%")}
    assert wanted <= {span.raw_text for span in selected.evidence_spans}
    assert max(counts.values()) == 1


@pytest.mark.parametrize("marker", ("II.", "II)"))
def test_uppercase_roman_keeps_actual_native_ancestry_and_model_context(marker):
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_list_ancestry import (
        _list_source,
    )
    from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
        _model,
        _spans_for,
    )

    original, owned = _list_source("cross_page_roman")
    target_text = marker + " " + owned["second"].raw_text.split(" ", 1)[1]
    parsed = _source(
        [
            (
                u.coordinates.page_number,
                target_text if u.unit_id == owned["second"].unit_id else u.raw_text,
                u.metadata["pdf_block"],
                tuple(u.metadata["reading_layout"]["layout"]["bbox"]),
            )
            for u in original.units
        ]
    )
    selected = reading.select_reading_evidence(
        parsed,
        title="Annual report",
        existing_kind="annual_report",
        max_selected=96,
        max_chars=48000,
    )
    target = next(u for u in parsed.units if u.raw_text == target_text)
    target_ids = {s.span_id for s in _spans_for(selected, target)}
    assert target_ids
    actual_parent = next(
        u for u in parsed.units if u.raw_text == owned["parent"].raw_text
    )
    needed = {
        s.span_id
        for u in (actual_parent, parsed.units[2])
        for s in _spans_for(selected, u)
    }
    assert needed
    citations = [
        c
        for g in selected.reading_context["groups"]
        for c in g["citation_views"]
        if target_ids.intersection(c["support_evidence_ids"])
    ]
    assert citations and all(
        needed <= set(c["context_evidence_ids"]) for c in citations
    )
    view, texts = _model(selected)
    tasks = [t for t in view.plan.tasks if target_ids.intersection(t.support_ids)]
    assert tasks and all(needed <= set(t.member_ids) for t in tasks)
    assert all(any(target_text in text for text in texts[t.key]) for t in tasks)
