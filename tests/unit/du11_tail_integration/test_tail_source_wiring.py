"""Physical tail evidence must reach every prose family through one owner."""
from copy import deepcopy

import pytest

from unit.document_understanding_selection.test_reading_native_continuity import (
    native, run, source_case,
)


def rows():
    pair = [native("如果政策发生变化，将会对公司经营产生不利影", 0,
                   box=[110.88, 100, 530.76, 110.45]),
            native("响。", 1, box=[89.88, 120.4, 110.77, 130.85])]
    for wire, _, _ in pair:
        wire["hints"]["font_runs"][0]["font_size"] = 10.45
        wire["layout"]["column"] = "observed-main"
    return pair


def test_measured_indented_tail_uses_original_ids_and_honest_negative_overlap():
    pair = rows()
    before = deepcopy(pair)
    result = run(pair)
    assert result["complete"]
    assert len(result["windows"]) == 1
    window = result["windows"][0]
    assert window["member_unit_ids"] == [row[0]["unit_id"] for row in pair]
    proof = window["proof"][0]
    assert proof["basis"] == "native_indented_terminal_tail"
    assert proof["horizontal_overlap"] == pytest.approx(-0.11)
    assert pair == before


@pytest.mark.parametrize("kind", ["background", "paragraph_event", "risk", "project"])
def test_prose_family_does_not_skip_physical_closure(kind):
    from company_wiki.source_catalog.narrative_reading import _prose_reading_packages

    parsed, pipeline = source_case([], native_rows=rows())
    pipeline["packages"]["packages"][0]["kind"] = kind
    before = deepcopy(pipeline)
    packages, _, audit, blocked = _prose_reading_packages(parsed, pipeline)
    joined = [p for p in packages if p["kind"] == "native_continuity"]
    ids = [u.unit_id for u in parsed.units]
    if kind == "project":
        assert not joined
        assert packages[0]["kind"] == "project"
        assert packages[0]["member_unit_ids"] == ids
        assert packages[0]["citation_support_views"] == [ids]
        assert packages[0]["required_context_unit_ids"] == pipeline["packages"]["packages"][0]["required_context_unit_ids"]
    else:
        assert len(joined) == 1
        assert joined[0]["member_unit_ids"] == ids
    assert audit["windows"] and not blocked
    assert pipeline == before


@pytest.mark.parametrize("boundary", ["column", "page", "role", "source", "scope", "font", "table", "heading"])
def test_tail_shape_never_overrides_native_boundary(boundary):
    pair = rows()
    wire, meta, profile = pair[1]
    if boundary == "column":
        pair[0][0]["layout"]["column"] = 0
        wire["layout"]["column"] = 1
    elif boundary == "page":
        wire["page"] += 1
    elif boundary == "role":
        wire["role"] = "management"
    elif boundary == "source":
        wire["hints"]["source_id"] = meta["source_id"] = "another-source"
    elif boundary == "scope":
        wire["hints"]["section_key"] = profile["section_role"] = "another-section"
    elif boundary == "font":
        wire["hints"]["font_runs"][0]["font_size"] = 11
    else:
        wire["kind"] = boundary
    assert not run(pair)["windows"]


def test_absent_column_labels_cannot_certify_negative_overlap():
    pair = rows()
    for wire, _, _ in pair:
        wire["layout"].pop("column")
    result = run(pair)
    assert not result["windows"]
    assert set(result["deferred_unit_ids"]) == {r[0]["unit_id"] for r in pair}


@pytest.mark.parametrize("boundary", [None, "heading", "table", "role", "font", "scope", "gap", "margin", "far_ordinal"])
def test_unknown_columns_require_an_immediately_adjacent_actual_body_band(boundary):
    pair = rows()
    for wire, _, _ in pair:
        wire["layout"].pop("column")
    anchor = native("公司持续开展新产品研发，并推进客户验证。", 2,
                    box=[89.88, 140.8, 530.76, 172])
    anchor[0]["hints"]["font_runs"][0]["font_size"] = 10.45
    if boundary in {"heading", "table"}:
        anchor[0]["kind"] = boundary
    elif boundary == "role":
        anchor[0]["role"] = "management"
    elif boundary == "font":
        anchor[0]["hints"]["font_runs"][0]["font_size"] = 11
    elif boundary == "scope":
        anchor[0]["hints"]["section_key"] = "other"
    elif boundary == "gap":
        anchor[0]["layout"]["bbox"] = [89.88, 300, 530.76, 332]
    elif boundary == "margin":
        anchor[0]["layout"]["bbox"] = [120, 140.8, 530.76, 172]
    elif boundary == "far_ordinal":
        anchor[0]["ordinal"] = anchor[1]["paragraph_index"] = 8
    result = run([*pair, anchor])
    if boundary is None:
        assert len(result["windows"]) == 1
        assert result["windows"][0]["member_unit_ids"] == [r[0]["unit_id"] for r in pair]
        proof = result["windows"][0]["proof"][0]
        assert proof["column_proof"]["anchor_unit_id"] == anchor[0]["unit_id"]
    else:
        assert not result["windows"]


def test_tail_algorithm_bytes_are_causal_not_just_a_constant(tmp_path, monkeypatch):
    from company_wiki.document_understanding import decision_inventory, indented_tail_geometry

    before = decision_inventory._versions(pdf_frontend=True, mime_type="application/pdf")
    alternate = tmp_path / "tail.py"
    alternate.write_text("# another physical tail algorithm\n", encoding="utf-8")
    monkeypatch.setattr(indented_tail_geometry, "__file__", str(alternate))
    after = decision_inventory._versions(pdf_frontend=True, mime_type="application/pdf")
    assert after != before
    assert after["continuity_algorithms"] != before["continuity_algorithms"]


@pytest.mark.parametrize("max_units,closed", [(4, True), (3, False)])
def test_indented_next_paragraph_can_supply_a_bounded_contiguous_lane(max_units, closed):
    pair = rows()
    for wire, _, _ in pair:
        wire["layout"].pop("column")
    following = [native("公司将继续开展新产品的研发并推进客户验证", 2,
                        box=[110.88, 140, 521.16, 153.71]),
                 native("并进一步拓展海外市场。", 3,
                        box=[89.88, 162, 530.75, 172.45])]
    for wire, _, _ in following:
        wire["hints"]["font_runs"][0]["font_size"] = 10.45
    result = run([*pair, *following], max_units=max_units)
    first = {r[0]["unit_id"] for r in pair}
    joined = [w for w in result["windows"] if set(w["member_unit_ids"]) == first]
    assert bool(joined) is closed
    if closed:
        proof = joined[0]["proof"][0]["column_proof"]
        assert [w["unit_id"] for w in proof["flow_witnesses"]] == [r[0]["unit_id"] for r in following]


@pytest.mark.parametrize("hint", ["missing", None, "", "   "])
def test_project_physical_audit_retains_real_section_boundaries_without_hint(hint):
    from company_wiki.source_catalog.narrative_reading import _prose_reading_packages

    parsed, pipeline = source_case([], native_rows=rows())
    pipeline["packages"]["packages"][0]["kind"] = "project"
    for wire in pipeline["observation"]["units"]:
        if hint == "missing":
            wire["hints"].pop("section_key")
        else:
            wire["hints"]["section_key"] = hint
    pipeline["structure"]["sections"] = [
        {"section_id": str(i), "heading_unit_ids": [], "body_unit_ids": [u.unit_id]}
        for i, u in enumerate(parsed.units)]
    _, _, audit, _ = _prose_reading_packages(parsed, pipeline)
    assert not audit["windows"]


def test_native_window_cannot_expand_one_project_into_unbounded_citation_views():
    from company_wiki.source_catalog.narrative_reading import _prose_reading_packages
    from company_wiki.document_understanding.summary_tasks import build_summary_task_plan

    original = [*rows(), native("公司已启动新工厂的建设。", 2),
                native("公司已交付设备，并获得重复订单。", 3)]
    parsed, pipeline = source_case([], native_rows=original)
    package = pipeline["packages"]["packages"][0]
    package["kind"] = "project"
    ids = [u.unit_id for u in parsed.units]
    package["anchor_unit_ids"] = ids
    packages, _, audit, _ = _prose_reading_packages(parsed, pipeline)
    assert audit["windows"]
    assert packages[0]["citation_support_views"] == [ids]
    spans = [u.to_evidence_span(topics=(), selection_reasons=()) for u in parsed.units]
    mapped = {u.unit_id: span.span_id for u, span in zip(parsed.units, spans)}
    context = {"schema_version": "du-production-reading/2", "groups": [{
        "group_id": "project-anchors", "kind": "project", "section_role": "business",
        "evidence_ids": [s.span_id for s in spans], "citation_views": [{
            "support_evidence_ids": [mapped[uid] for uid in view],
            "context_evidence_ids": [mapped[uid] for uid in ids if uid not in view],
        } for view in packages[0]["citation_support_views"]]}]}
    plan = build_summary_task_plan(spans, reading_context=context, max_claims=8)
    assert len(plan.tasks) == 1
    assert set(plan.tasks[0].support_ids) == set(mapped.values())


@pytest.mark.parametrize("work", [4, 5, 6])
def test_lookahead_exhaustion_never_releases_unproven_left_fragment(work):
    pair = rows()
    for wire, _, _ in pair:
        wire["layout"].pop("column")
    anchor = native("公司持续推进客户验证。", 2, box=[89.88, 140.8, 530.76, 151.25])
    anchor[0]["hints"]["font_runs"][0]["font_size"] = 10.45
    result = run([*pair, anchor], max_work_units=work)
    assert not result["complete"]
    assert not result["windows"]
    assert {r[0]["unit_id"] for r in pair} <= set(result["deferred_unit_ids"])
    assert result["standalone_unit_count"] == 0
