"""Original-ID source proofs and local failure reach material compilation."""
from dataclasses import replace

import pytest

from company_wiki.document_understanding.structure.source_scopes import match_source_note_marker
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_native_materials import prepare_native_materials

from .fixtures import Row, inherited_heading_ids, run_pipeline, source


@pytest.mark.parametrize("text,label", [("备注１８：产品服务范围：", "１８"),
                                       ("備註二十：服务说明：", "二十")])
def test_original_marker_labels_do_not_become_scope_identity(text, label):
    marker = match_source_note_marker(text)
    assert marker is not None and marker.label == label
    assert text[marker.start:marker.end].endswith("：")


@pytest.mark.parametrize("text", ["本事项见备注18：已另行披露。", "备注如下：", "18：份额变化",
                                  "根据備註十八：资料已披露。"])
def test_reference_and_unlabelled_prose_do_not_open_source_scope(text):
    assert match_source_note_marker(text) is None


def test_split_intro_uses_real_block_character_members_without_geometry():
    box = (72., 80., 528., 168.)
    parsed, owned = source((Row("marker", "备注18：", block=0, box=box),
                            Row("intro", "乙方就新服务范围说明如下：", block=0, box=box),
                            Row("body", "“1、乙方的检测平台已完成升级。”", block=0, box=box)), geometry=False)
    result, contexts = run_pipeline(parsed)
    context = inherited_heading_ids(result, owned["body"])
    assert {owned["marker"].unit_id, owned["intro"].unit_id} <= context
    witness = contexts[parsed.source_id].member_neighbour(owned["marker"].unit_id,
                                                        owned["intro"].unit_id)
    assert witness is not None and witness["basis"] == "native_block_character_ranges"
    assert not any(d["code"].startswith("SOURCE_SCOPE_") for d in result["structure"]["diagnostics"])
    semantic = next(s for s in result["structure"]["semantic_units"]
                    if owned["body"].unit_id in s["member_unit_ids"])
    assert semantic["completeness"] == "complete"
    # Optional geometry has its own pre-existing coverage diagnostic; this
    # source-member proof neither fabricates geometry nor discards valid refs.


def test_overlapping_original_character_members_cannot_create_a_complete_scope():
    box = (72., 80., 528., 168.)
    parsed, owned = source((Row("intro", "备注18：乙方服务范围：", block=0, box=box),
                            Row("body", "“1、乙方的检测平台已完成升级。”", block=0, box=box)), geometry=False)
    unit = owned["body"]
    broken = replace(unit, metadata={**unit.metadata, "block_char_start": 1})
    parsed = replace(parsed, units=(parsed.units[0], broken))
    result, contexts = run_pipeline(parsed)
    assert contexts[parsed.source_id].member_neighbour(parsed.units[0].unit_id, broken.unit_id) is None
    assert owned["intro"].unit_id not in inherited_heading_ids(result, broken)
    assert result["structure"]["coverage"]["complete"] is False
    assert any(s["completeness"] == "partial" and broken.unit_id in s["member_unit_ids"]
               for s in result["structure"]["semantic_units"])


def test_unproven_note_relation_blocks_only_exact_material_target():
    parsed, owned = source((Row("intro", "备注18：乙方服务范围："),
                            Row("body", "“1、乙方的检测平台已完成升级。”"),
                            Row("healthy", "一、业务进展"),
                            Row("healthy_body", "公司已交付新设备三十台。")), geometry=False)
    result, contexts = run_pipeline(parsed)
    packages, _facts, continuity, blocked = prepare_native_materials(
        parsed, result, work_budget=WorkBudget(16_000_000), _native_contexts=contexts)
    assert continuity["complete"] is False
    assert owned["body"].unit_id in blocked
    assert owned["healthy_body"].unit_id not in blocked
    assert all(owned["body"].unit_id not in p["anchor_unit_ids"] for p in packages)
    assert any(owned["healthy_body"].unit_id in p["anchor_unit_ids"] for p in packages)


def test_geometry_without_known_column_is_not_a_source_adjacency_proof():
    parsed, owned = source((Row("intro", "备注18：乙方服务范围："),
                            Row("body", "“1、乙方的检测平台已完成升级。”")), column=None)
    result, contexts = run_pipeline(parsed)
    context = contexts[parsed.source_id]
    assert context.member_neighbour(owned["intro"].unit_id, owned["body"].unit_id) is None
    assert context.same_page_neighbour(owned["intro"].unit_id, owned["body"].unit_id) is None
    assert result["structure"]["coverage"]["complete"] is False


def test_long_note_cannot_silently_retain_an_oversized_complete_scope():
    parsed, owned = source((Row("intro", "备注18：乙方服务范围："),
                           *(Row(f"b{i}", f"{i+1}、公司已交付新设备。") for i in range(26))))
    result, _contexts = run_pipeline(parsed)
    assert result["structure"]["coverage"]["complete"] is False
    diagnostics = result["structure"]["diagnostics"]
    assert any(d["code"] == "SOURCE_SCOPE_LIMIT_REACHED" and owned["b23"].unit_id in d["unit_ids"]
               for d in diagnostics)
    assert owned["intro"].unit_id not in inherited_heading_ids(result, owned["b23"])
