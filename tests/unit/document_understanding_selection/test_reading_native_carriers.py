"""Source-proven semantic slots, with exact original characters and references."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view, native_range_unit
from company_wiki.source_catalog.narrative_routing import DocumentRoute
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def source_fixture(bodies, *, heading=False, source_sha="c" * 64, proven=True):
    blocks = [("业务进展",)] if heading else []
    blocks += list(bodies)
    source = source_id_for_sha256(source_sha)
    native_blocks = [(i, (90, 100 + 20 * i, 550, 112 + 20 * i), "\n".join(parts))
                     for i, parts in enumerate(blocks)]
    view = build_native_page_view(native_blocks)
    units, wires = [], []
    for block, box, full in native_blocks:
        start = 0
        for text in blocks[block]:
            index = len(units)
            layout = {"bbox": list(box), "page_width": 600, "page_height": 800,
                      "coordinate_frame": "dict", "rotation": 0, "column": 0}
            fonts = [{"char_start": 0, "char_end": len(text), "font_size": 12,
                      "font_weight": "regular", "coordinate_frame": "dict",
                      "source": "pdf_native_single_textpage", "char_alignment": "exact"}]
            meta = {"pdf_block": block, "block_sha256": sha256(full.encode()).hexdigest(),
                    "block_char_start": start, "block_char_end": start + len(text),
                    "reading_layout": {"layout": layout, "upstream_hints": {"font_runs": fonts}}}
            if proven:
                meta["native_source_view"] = view
            unit = _make_unit(source_id=source, parser_version="0.1.1",
                coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
                raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
                language="zh", metadata=meta)
            units.append(unit)
            wires.append({"unit_id": unit.unit_id, "ordinal": index, "page": 1, "text": text,
                "kind": "heading" if heading and block == 0 else "paragraph",
                "role": "company_filing", "language": "zh", "layout": layout,
                "hints": {"source_id": source, "font_runs": fonts}})
            start += len(text) + 1
    ids = [unit.unit_id for unit in units]
    body = ids[1:] if heading else ids
    pipeline = {"observation": {"units": wires},
        "reading_plan": {"unit_profiles": {uid: {"reading_profile_key": "root",
            "section_role": "business", "priority": 2} for uid in ids}},
        "structure": {"sections": [{"section_id": source, "parent_id": None,
            "heading_unit_ids": ids[:1] if heading else [], "body_unit_ids": body}]},
        "packages": {"packages": [{"package_id": source + ":body", "kind": "background",
            "member_unit_ids": body, "anchor_unit_ids": body[:1],
            "required_context_unit_ids": body[:1]}]}}
    return DocumentStructure(source, source_sha, "zh", tuple(units), page_count=1,
        pages_read=1, mime_type="application/pdf"), pipeline


def selected(parsed, pipeline, candidates, metadata, *, limit=96, max_chars=48000):
    material = replace(parsed, units=tuple(pipeline.get("_material_units", parsed.units)))
    return finalize_selection(material, DocumentRoute("semi_annual_report", limit, False),
        candidates, group_ids={}, heading_pattern=reading._NEVER_HEADING,
        dropped_financial_count=0, budget_policy=reading.READING_BUDGET_POLICY,
        reading_metadata=metadata, max_chars=max_chars)


def fragments(text, count):
    return tuple(text[len(text) * i // count:len(text) * (i + 1) // count]
                 for i in range(count))


def test_96_original_fragments_use_12_real_semantic_slots_without_cap_increase():
    bodies = [fragments(f"公司已交付第{i}套专用设备至客户开展生产验证，但尚未完成量产认证。", 8)
              for i in range(12)]
    old, old_pipeline = source_fixture(bodies, proven=False)
    old_candidates, old_meta, _, _, _ = reading._candidates(old, old_pipeline)
    old_result = selected(old, old_pipeline, old_candidates, old_meta, limit=12)
    assert len(old.units) == 96 and len(old_result.evidence_spans) < 96

    parsed, pipeline = source_fixture(bodies)
    originals = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    assert len(candidates) == len(pipeline["_material_units"]) == 12
    assert len(pipeline["_carrier_origins"]) == 96
    assert all(item.unit.unit_kind == "pdf_native_range" for item in candidates)
    assert {uid for package in packages for uid in package["member_unit_ids"]} == set(pipeline["_carrier_origins"])
    result = selected(parsed, pipeline, candidates, metadata, limit=12)
    assert len(result.evidence_spans) == 12
    assert sum(len(span.raw_text) for span in result.evidence_spans) == sum(len("\n".join(body)) for body in bodies)
    assert len({span.span_id for span in result.evidence_spans}) == 12
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == originals
    assert reading.MAX_READING_CHARS == 48000 and reading.READING_BUDGET_POLICY == "reading_plan/3"


def test_one_slot_keeps_negation_and_future_qualifiers_and_counts_all_native_characters():
    parsed, pipeline = source_fixture([("公司已交付设备至客户开展生产验", "证，但尚未完成认证，预计明年量产。")])
    expected = native_range_unit(parsed.units)
    assert expected is not None
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and packages[0]["member_unit_ids"] == [u.unit_id for u in parsed.units]
    assert [candidate.unit for candidate in candidates] == [expected]
    assert not selected(parsed, pipeline, candidates, metadata, limit=1, max_chars=len(expected.raw_text) - 1).evidence_spans
    result = selected(parsed, pipeline, candidates, metadata, limit=1, max_chars=len(expected.raw_text))
    assert [span.raw_text for span in result.evidence_spans] == [expected.raw_text]
    assert "尚未" in result.evidence_spans[0].raw_text and "预计明年" in result.evidence_spans[0].raw_text
    assert "native_source_view" not in result.evidence_spans[0].structured_value


def test_two_carriers_share_one_real_heading_in_original_material_order():
    parsed, pipeline = source_fixture([
        ("公司已交付设备至客户开展生产验", "证，但尚未完成量产认证。"),
        ("公司新增制造基地已经投入运", "行，仍需完成客户认证。")], heading=True)
    heading = parsed.units[0]
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    material = pipeline["_material_units"]
    assert material[0] is heading and len(material) == 3
    assert [unit.unit_kind for unit in material] == ["pdf_text_block", "pdf_native_range", "pdf_native_range"]
    assert all(metadata[unit.unit_id]["required"] == (heading.unit_id,) for unit in material[1:])
    assert [package["required_context_unit_ids"] for package in packages] == [[heading.unit_id], [heading.unit_id]]
    result = selected(parsed, pipeline, candidates, metadata, limit=3)
    assert len(result.evidence_spans) == 3 and sum(span.raw_text == heading.raw_text for span in result.evidence_spans) == 1
    assert len(pipeline["_carrier_origins"]) == 4


@pytest.mark.parametrize("invalid", ["missing", "different_view", "wrong_block_hash"])
def test_missing_or_invalid_source_proof_keeps_old_complete_fragment_group(invalid):
    parsed, pipeline = source_fixture([("公司已交付设备至客户开展生产验", "证，尚未完成量产认证。")])
    last = parsed.units[-1]
    metadata = dict(last.metadata)
    if invalid == "missing":
        metadata.pop("native_source_view")
    elif invalid == "different_view":
        metadata["native_source_view"] = dict(metadata["native_source_view"])
    else:
        metadata["block_sha256"] = "b" * 64
    # A wrong maker proof must not be converted even if upstream geometry is
    # otherwise continuous. Wrong block SHA also correctly stops continuity.
    parsed = replace(parsed, units=(*parsed.units[:-1], replace(last, metadata=metadata)))
    before = deepcopy(pipeline)
    candidates, meta, _, _, _ = reading._candidates(parsed, pipeline)
    assert "_material_units" not in pipeline and "_carrier_origins" not in pipeline
    assert pipeline == before
    assert all(candidate.unit.unit_kind == "pdf_text_block" for candidate in candidates)
    assert all(candidate.unit.unit_id in {u.unit_id for u in parsed.units} for candidate in candidates)
    if invalid != "wrong_block_hash":
        assert not selected(parsed, pipeline, candidates, meta, limit=1).evidence_spans
        assert len(selected(parsed, pipeline, candidates, meta, limit=2).evidence_spans) == 2


def test_identical_text_from_two_parents_remains_two_source_bound_carriers():
    bodies = [("公司已交付设备至客户开展生产验", "证，尚未完成量产认证。")]
    first, pipeline = source_fixture(bodies)
    second, child = source_fixture(bodies, source_sha="d" * 64)
    parsed = replace(first, units=(*first.units, *second.units))
    pipeline["observation"]["units"].extend(child["observation"]["units"])
    pipeline["reading_plan"]["unit_profiles"].update(child["reading_plan"]["unit_profiles"])
    pipeline["structure"]["sections"].extend(child["structure"]["sections"])
    pipeline["packages"]["packages"].extend(child["packages"]["packages"])
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(candidates) == 2
    assert {candidate.unit.source_id for candidate in candidates} == {first.source_id, second.source_id}
    assert len(set(pipeline["_carrier_origins"].values())) == 2
    assert len(selected(parsed, pipeline, candidates, metadata, limit=2).evidence_spans) == 2


def test_carrier_mapping_reuses_original_fact_and_does_not_reclassify_range_text(monkeypatch):
    bodies = [("公司已交付设备至客户开展生产验", "证，尚未完成量产认证。")]
    detector = reading.detect_reading_business_fact
    observed = []
    def traced(text):
        observed.append(text)
        return detector(text)
    monkeypatch.setattr(reading, "detect_reading_business_fact", traced)
    old, old_pipeline = source_fixture(bodies, proven=False)
    reading._candidates(old, old_pipeline)
    old_calls = list(observed)
    observed.clear()
    parsed, pipeline = source_fixture(bodies)
    candidates, _, _, _, _ = reading._candidates(parsed, pipeline)
    assert observed == old_calls
    assert len(candidates) == 1
    assert candidates[0].unit.raw_text not in observed


def test_carrier_conversion_keeps_unrelated_qa_missing_anchor_compatibility():
    parsed, pipeline = source_fixture([("公司已交付设备至客户开展生产验", "证，尚未完成量产认证。")])
    question = _make_unit(source_id=parsed.source_id, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=2, paragraph_index=0), raw_text="产线认证情况如何？",
        unit_kind="paragraph", source_role="investor_question", language="zh", metadata={})
    answer = _make_unit(source_id=parsed.source_id, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=2, paragraph_index=1),
        raw_text="公司已交付设备至客户开展生产验证，尚未完成量产认证。",
        unit_kind="paragraph", source_role="management", language="zh", metadata={})
    parsed = replace(parsed, units=(*parsed.units, question, answer))
    for i, unit in enumerate((question, answer), start=2):
        pipeline["observation"]["units"].append({"unit_id": unit.unit_id, "ordinal": i, "page": 2,
            "text": unit.raw_text, "kind": "paragraph", "role": unit.source_role, "language": "zh",
            "hints": {"source_id": unit.source_id}})
        pipeline["reading_plan"]["unit_profiles"][unit.unit_id] = {"section_role": "business", "priority": 2}
    pipeline["packages"]["packages"].append({"package_id": "legacy-qa", "kind": "qa_exchange",
        "member_unit_ids": [question.unit_id, answer.unit_id], "required_context_unit_ids": [question.unit_id]})
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(packages) == 2
    assert not metadata[answer.unit_id]["context_only"] and metadata[question.unit_id]["context_only"]
    assert [unit.unit_id for unit in pipeline["_material_units"]][-2:] == [question.unit_id, answer.unit_id]
    assert len(selected(parsed, pipeline, candidates, metadata, limit=3).evidence_spans) == 3


def test_reused_pipeline_cannot_keep_stale_material_after_source_proof_disappears():
    parsed, pipeline = source_fixture([("公司已交付设备至客户开展生产验", "证，尚未完成量产认证。")])
    reading._candidates(parsed, pipeline)
    assert "_material_units" in pipeline and "_carrier_origins" in pipeline
    fresh = replace(parsed, units=tuple(replace(unit, metadata={key: value for key, value in unit.metadata.items()
        if key != "native_source_view"}) for unit in parsed.units))
    candidates, metadata, _, complete, withheld = reading._candidates(fresh, pipeline)
    assert complete and not withheld
    assert "_material_units" not in pipeline and "_carrier_origins" not in pipeline
    assert len(selected(fresh, pipeline, candidates, metadata, limit=2).evidence_spans) == 2
