"""Source-marked notes keep their own introduction, not the preceding tail."""
import pytest

from .fixtures import (
    Row, aligned_source_members_without_geometry, inherited_heading_ids,
    observation, run_pipeline, source,
)


@pytest.mark.parametrize("actors,numbers", [
    (("甲方", "乙方", "甲方"), ("17", "18", "19")),
    (("甲方", "甲方", "甲方"), ("17", "18", "19")),
    (("甲方", "乙方", "甲方"), ("2", "17", "2")),
])
def test_each_new_note_owns_its_positive_introduction_even_for_same_actor(actors, numbers):
    rows = []
    for index, (actor, number) in enumerate(zip(actors, numbers, strict=True)):
        rows.extend((
            Row(f"intro{index}", f"备注{number}：{actor}关于事项{index + 1}的承诺："),
            Row(f"body{index}", f"“1、{actor}就事项{index + 1}承担披露义务。"),
            Row(f"tail{index}", f"3、{actor}承担事项{index + 1}的一切损失。”"),
        ))
    parsed, owned = source(tuple(rows))
    assert all("heading_level" not in unit.metadata for unit in parsed.units)
    result, _contexts = run_pipeline(parsed)
    for index in (1, 2, 0):
        context = inherited_heading_ids(result, owned[f"body{index}"])
        forbidden = {owned[f"intro{other}"].unit_id for other in range(3) if other != index}
        forbidden.update(owned[f"tail{other}"].unit_id for other in range(3) if other != index)
        assert not forbidden.intersection(context), {"target": index, "wrong_ancestors": context}
        assert owned[f"intro{index}"].unit_id in context, "removing wrong edges is not enough"


@pytest.mark.parametrize("multiline", [False, True])
def test_long_source_marked_intro_is_complete_context_without_a_heading_length_bypass(multiline):
    text = "备注18：乙方就新服务范围及披露义务作出以下明确的来源限定，" + "其适用范围以本备注载明的原始条件为准；" * 5 + "现说明如下："
    if multiline:
        text = text.replace("原始条件", "原始\n条件", 1)
    assert len(text) > 80
    parsed, owned = source((Row("intro", text), Row("body", "“1、乙方的检测平台已完成升级。")))
    result, _contexts = run_pipeline(parsed)
    assert owned["intro"].unit_id in inherited_heading_ids(result, owned["body"])
    assert owned["intro"].raw_text == text


def test_valid_source_membership_does_not_require_optional_geometry():
    parsed, owned = aligned_source_members_without_geometry()
    wire = observation(parsed)
    memberships = [unit["hints"]["paragraph_membership"] for unit in wire["units"]]
    assert memberships[0]["next"] == owned["body"].unit_id
    assert memberships[1]["previous"] == owned["intro"].unit_id
    assert memberships[0]["group"] == memberships[1]["group"]
    assert all("bbox" not in unit.get("layout", {}) for unit in wire["units"])
    result, _contexts = run_pipeline(parsed)
    assert owned["intro"].unit_id in inherited_heading_ids(result, owned["body"])


@pytest.mark.parametrize("kind", ["guide", "table_footnote", "running_furniture"])
def test_guide_table_note_and_furniture_are_not_new_local_note_parents(kind):
    if kind == "guide":
        rows = (Row("heading", "一、业务进展"),
                Row("note", "本事项的详细说明见备注18：有关安排已披露。"),
                Row("body", "检测平台已完成升级。"))
    elif kind == "table_footnote":
        rows = (Row("heading", "一、业务进展"),
                Row("note", "备注18：表格中的比例因四舍五入存在差异。", kind="html_footnote", table_index=0),
                Row("body", "检测平台已完成升级。"))
    else:
        rows = (Row("heading", "一、业务进展", box=(72., 100., 540., 124.)),
                Row("note", "备注18：重复页眉", box=(72., 10., 540., 24.)),
                Row("body", "检测平台已完成升级。", box=(72., 200., 540., 224.)),
                Row("repeated", "备注18：重复页眉", page=2, box=(72., 10., 540., 24.)))
    parsed, owned = source(rows)
    result, _contexts = run_pipeline(parsed)
    assert owned["note"].unit_id not in inherited_heading_ids(result, owned["body"])
    assert all(owned["note"].unit_id not in section["heading_unit_ids"]
               for section in result["structure"]["sections"])
