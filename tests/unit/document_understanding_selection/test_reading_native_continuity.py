"""Pure native provenance controls; no parser/provider/model or corpus writes."""

from copy import deepcopy
from importlib import import_module

import pytest


def native(
    text,
    index,
    *,
    source="source-a",
    page=7,
    block=None,
    start=0,
    box=None,
    kind="paragraph",
    scope="business",
    column=None,
):
    box = box or [90, 100 + index * 20, 550, 112 + index * 20]
    uid = f"{source}:{index}"
    view = {
        "unit_id": uid,
        "ordinal": index,
        "page": page,
        "text": text,
        "kind": kind,
        "role": "company_filing",
        "language": "zh",
        "layout": {
            "bbox": box,
            "page_width": 600,
            "page_height": 800,
            "coordinate_frame": "dict",
            "rotation": 0,
            "font_size": 12,
            "font_weight": "regular",
        },
        "hints": {
            "source_id": source,
            "section_key": scope,
            "font_runs": [
                {
                    "char_start": 0,
                    "char_end": len(text),
                    "font_size": 12,
                    "font_weight": "regular",
                    "source": "pdf_native_single_textpage",
                    "coordinate_frame": "dict",
                    "char_alignment": "exact",
                }
            ],
        },
    }
    if column is not None:
        view["layout"]["column"] = column
    provenance = {
        "source_id": source,
        "paragraph_index": index,
        "pdf_block": index if block is None else block,
        "block_sha256": str(block if block is not None else index),
        "block_char_start": start,
        "block_char_end": start + len(text),
    }
    profile = {"reading_profile_key": "root", "section_role": scope}
    return view, provenance, profile


def run(rows, **limits):
    module = import_module("company_wiki.document_understanding.narrative_continuity")
    views = [row[0] for row in rows]
    provenance = {row[0]["unit_id"]: row[1] for row in rows}
    profiles = {row[0]["unit_id"]: row[2] for row in rows}
    return module.build_native_continuity(
        views, provenance=provenance, unit_profiles=profiles, limits=limits or None
    )


@pytest.mark.parametrize(
    "texts",
    [
        ("未来四年，公司将通", "过扩产与客户认证覆盖55%的设备市", "场。"),
        ("该设备已进入客户进行生产验", "证。"),
        ("新产品持", "续服务客户，并获得重复订单。"),
        (
            "于报告期内启动新材料体系",
            "专用设备的开发，实验室已有进展。下",
            "半年将根据反馈安排样机交付，",
            "尽早送至客户开展验证。",
        ),
    ],
)
def test_only_original_ids_of_closed_two_to_four_native_blocks_are_windowed(texts):
    rows = [native(text, index) for index, text in enumerate(texts)]
    before = deepcopy(rows)
    result = run(rows)
    assert result["complete"]
    assert len(result["windows"]) == 1
    assert result["windows"][0]["member_unit_ids"] == [
        row[0]["unit_id"] for row in rows
    ]
    assert (
        result["windows"][0]["required_unit_ids"]
        == result["windows"][0]["member_unit_ids"]
    )
    assert "text" not in result["windows"][0] and "raw_text" not in result["windows"][0]
    assert rows == before


def test_same_actual_block_fragments_use_original_char_ranges_not_guessed_line_boxes():
    box = [90, 100, 550, 132]
    rows = [
        native("首个项目已启动。", 0, block=3, box=box),
        native("下一阶段将开展客户验证。", 1, block=3, start=9, box=box),
    ]
    result = run(rows)
    assert len(result["windows"]) == 1 and result["complete"]
    assert any(
        proof["basis"] == "native_block_character_ranges"
        for proof in result["windows"][0]["proof"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "page",
        "order",
        "heading",
        "table",
        "column",
        "scope",
        "frame",
        "font",
        "ocr",
        "gap",
        "terminal",
    ],
)
def test_an_observed_boundary_or_missing_native_proof_blocks_joining(change):
    rows = [native("设备将开展生产验", 0), native("证。", 1)]
    right, source, profile = rows[1]
    if change == "source":
        right["hints"]["source_id"] = source["source_id"] = "source-b"
    elif change == "page":
        right["page"] = 8
    elif change == "order":
        right["ordinal"] = source["paragraph_index"] = 3
    elif change in {"heading", "table"}:
        right["kind"] = "heading" if change == "heading" else "table_cell"
    elif change == "column":
        rows[0][0]["layout"]["column"], right["layout"]["column"] = 0, 1
    elif change == "scope":
        right["hints"]["section_key"] = profile["section_role"] = "financial_notes"
    elif change == "frame":
        right["layout"].pop("coordinate_frame")
    elif change == "font":
        right["hints"]["font_runs"] = []
    elif change == "ocr":
        right["hints"]["font_runs"][0]["source"] = "ocr_guess"
    elif change == "gap":
        right["layout"]["bbox"] = [90, 400, 550, 412]
    else:
        rows[0][0]["text"] = "上一句已完成。"
        rows[0][0]["hints"]["font_runs"][0]["char_end"] = len(rows[0][0]["text"])
        rows[0][1]["block_char_end"] = len(rows[0][0]["text"])
    assert run(rows)["windows"] == []


def test_missing_same_block_offsets_cannot_be_replaced_by_a_shared_bbox():
    box = [90, 100, 550, 132]
    rows = [
        native("设备开展验证，", 0, block=3, box=box),
        native("尚未达到量产。", 1, block=3, start=8, box=box),
    ]
    rows[1][1].pop("block_char_start")
    assert not run(rows)["windows"]


def test_source_section_boundary_wins_even_with_same_profile_role():
    rows = [native("订单将在下期转", 0), native("化为交付收入。", 1)]
    rows[1][0]["hints"]["section_key"] = "different-actual-section"
    assert not run(rows)["windows"]


def test_long_connected_unclosed_run_cannot_create_overlapping_windows_or_a_chapter_union():
    rows = [native("同一段中的原始片段" + str(index), index) for index in range(9)] + [
        native("结束。", 9)
    ]
    result = run(rows)
    assert not result["windows"]
    assert not result["complete"]
    assert any(d["code"] == "CONTINUITY_WINDOW_LIMIT" for d in result["diagnostics"])


def test_independent_closed_runs_do_not_share_original_members():
    rows = [
        native("客户样机进入验", 0),
        native("证。", 1),
        native("另一项扩产将在下", 2),
        native("半年完成。", 3),
    ]
    result = run(rows)
    assert [w["member_unit_ids"] for w in result["windows"]] == [
        ["source-a:0", "source-a:1"],
        ["source-a:2", "source-a:3"],
    ]
    assert len({uid for w in result["windows"] for uid in w["member_unit_ids"]}) == 4


@pytest.mark.parametrize(
    "limits",
    [
        {"max_work_units": 0},
        {"max_window_chars": 1},
        {"max_windows": 0},
        {"max_units": 1},
    ],
)
def test_caps_never_create_a_half_window_or_claim_complete(limits):
    result = run([native("设备仍在验", 0), native("证阶段。", 1)], **limits)
    assert not result["windows"] and not result["complete"]
    assert result["diagnostics"]


def test_same_block_sentence_fragments_do_not_turn_four_native_blocks_into_five():
    # A native line can hold the end of one sentence and the start of another.
    box = [90, 140, 550, 152]
    rows = [
        native("针对光通", 0, block=3),
        native("讯应用，公司于本期启动新材料体系", 1, block=4),
        native("设备研发，实验室已有进展。", 2, block=5, box=box),
        native(
            "下半年将根据客户反馈加快开发，",
            3,
            block=5,
            start=len("设备研发，实验室已有进展。"),
            box=box,
        ),
        native("安排样机送至客户开展生产验证。", 4, block=6, box=[90, 160, 550, 172]),
    ]
    result = run(rows)
    assert result["complete"]
    assert result["windows"][0]["member_unit_ids"] == [r[0]["unit_id"] for r in rows]


def test_long_native_run_can_split_only_at_an_actual_complete_statement_before_cap():
    texts = [
        "前一产品的开",
        "发已完成。",
        "公司已付",
        "运样机到客户验证。",
        "针对新兴应",
        "用，公司启动材料体系",
        "设备开发，实验室已有进展。",
        "下半年计划送至客户验",
        "证。",
    ]
    blocks = [0, 1, 1, 2, 2, 3, 4, 4, 5]
    rows = []
    starts = {}
    for i, (text, block) in enumerate(zip(texts, blocks)):
        rows.append(
            native(
                text,
                i,
                block=block,
                start=starts.get(block, 0),
                box=[90, 100 + block * 20, 550, 112 + block * 20],
            )
        )
        starts[block] = starts.get(block, 0) + len(text)
    result = run(rows)
    assert result["complete"]
    assert [w["member_unit_ids"] for w in result["windows"]] == [
        ["source-a:0", "source-a:1", "source-a:2", "source-a:3"],
        ["source-a:4", "source-a:5", "source-a:6", "source-a:7", "source-a:8"],
    ]
    assert all(
        len(
            {
                rows[int(uid.rsplit(":", 1)[-1])][1]["pdf_block"]
                for uid in w["member_unit_ids"]
            }
        )
        <= 4
        for w in result["windows"]
    )


def source_case(texts, *, native_rows=None, heading=False, role="business"):
    """Source-owned IR plus real-shaped typed observation; no parser or IO."""
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    source = source_id_for_sha256("a" * 64)
    rows = native_rows or [
        native(text, i, source=source) for i, text in enumerate(texts)
    ]
    units = []
    wires = []
    for i, (wire, provenance, profile) in enumerate(rows):
        metadata = {
            key: value
            for key, value in provenance.items()
            if key not in {"source_id", "paragraph_index"}
        }
        metadata["reading_layout"] = {
            "layout": wire["layout"],
            "upstream_hints": {"font_runs": wire["hints"]["font_runs"]},
        }
        unit = _make_unit(
            source_id=source,
            parser_version="1.0.0",
            coordinates=EvidenceCoordinates(
                page_number=wire["page"], paragraph_index=i
            ),
            raw_text=wire["text"],
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="zh",
            metadata=metadata,
        )
        units.append(unit)
        wires.append(
            {
                **wire,
                "unit_id": unit.unit_id,
                "hints": {**wire["hints"], "source_id": source},
            }
        )
    ids = [u.unit_id for u in units]
    body = ids[1:] if heading else ids
    if heading:
        wires[0] = {**wires[0], "kind": "heading"}
    pipeline = {
        "observation": {"units": wires},
        "reading_plan": {
            "unit_profiles": {
                uid: {
                    "reading_profile_key": "root",
                    "section_role": role,
                    "priority": 2,
                }
                for uid in ids
            }
        },
        "structure": {
            "sections": [
                {
                    "section_id": "business",
                    "parent_id": None,
                    "heading_unit_ids": ids[:1] if heading else [],
                    "body_unit_ids": body,
                }
            ]
        },
        "packages": {
            "packages": [
                {
                    "package_id": "background",
                    "kind": "background",
                    "member_unit_ids": body,
                    "anchor_unit_ids": body[:1],
                    "required_context_unit_ids": body[:1],
                }
            ]
        },
    }
    return DocumentStructure(
        source,
        "a" * 64,
        "zh",
        tuple(units),
        page_count=7,
        pages_read=7,
        mime_type="application/pdf",
    ), pipeline


def test_every_background_member_is_a_candidate_without_whole_container_dependency():
    from company_wiki.source_catalog.narrative_reading import _candidates

    texts = [
        "公司主要提供多种设备。",
        "我们的新产品已进入客户生产验证。",
        "公司下一阶段将推进客户认证。",
    ]
    parsed, pipeline = source_case(texts)
    candidates, metadata, eligible, complete, withheld = _candidates(parsed, pipeline)
    assert complete and not withheld
    assert {c.unit.unit_id for c in candidates} == {u.unit_id for u in parsed.units}
    for unit in parsed.units:
        assert not metadata[unit.unit_id]["context_only"]
        assert metadata[unit.unit_id]["required"] == ()
    assert len(eligible) == 3
    assert all(len(p["member_unit_ids"]) == 1 for p in eligible)


def test_joint_fact_requires_all_original_fragments_but_no_unrelated_background_members():
    from company_wiki.source_catalog.narrative_reading import _candidates

    parsed, pipeline = source_case(
        [
            "设备说明",
            "未来四年，公司将通",
            "过扩产与客户认证覆盖55%的设备市",
            "场。",
            "另一个普通产品的说明。",
        ],
        heading=True,
    )
    before = deepcopy(pipeline)
    candidates, metadata, eligible, complete, withheld = _candidates(parsed, pipeline)
    window_ids = [u.unit_id for u in parsed.units[1:4]]
    head = parsed.units[0].unit_id
    expected = {*window_ids, head}
    closed = [p for p in eligible if set(p["member_unit_ids"]) == set(window_ids)]
    assert len(closed) == 1 and complete and not withheld
    assert set(closed[0]["required_context_unit_ids"]) == {head}
    anchors = [uid for uid in window_ids if not metadata[uid]["context_only"]]
    assert anchors
    assert all(set(metadata[uid]["required"]) | {uid} == expected for uid in anchors)
    assert all(metadata[uid]["value_band"] == "meaningful_fact" for uid in anchors)
    assert metadata[head]["context_only"]
    assert metadata[parsed.units[-1].unit_id]["required"] == (head,)
    assert pipeline == before
    assert {c.unit.unit_id for c in candidates} == {u.unit_id for u in parsed.units}


def test_joint_closure_cannot_shrink_under_existing_span_budget():
    from company_wiki.source_catalog import narrative_reading as reading
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute

    parsed, pipeline = source_case(["该设备已进入客户进行生产验", "证。"])
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, pipeline
    )
    small = finalize_selection(
        parsed,
        DocumentRoute("semi_annual", 1, False),
        candidates,
        group_ids={},
        heading_pattern=reading._NEVER_HEADING,
        dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY,
        reading_metadata=metadata,
        max_chars=48000,
    )
    full = finalize_selection(
        parsed,
        DocumentRoute("semi_annual", 2, False),
        candidates,
        group_ids={},
        heading_pattern=reading._NEVER_HEADING,
        dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY,
        reading_metadata=metadata,
        max_chars=48000,
    )
    assert not small.evidence_spans
    assert len(full.evidence_spans) == 2
    assert [span.raw_text for span in full.evidence_spans] == [
        u.raw_text for u in parsed.units
    ]
    assert [span.coordinates for span in full.evidence_spans] == [
        u.coordinates for u in parsed.units
    ]
    assert len(eligible) == 1 and complete and not withheld


def test_finance_only_and_separate_financial_sentence_stay_rejected():
    from company_wiki.source_catalog.narrative_reading import _candidates

    parsed, pipeline = source_case(["营业收入为20亿元。", "净利润为3亿元。"])
    assert not _candidates(parsed, pipeline)[0]
    parsed, pipeline = source_case(["主要产品面向工业客户。", "净利润为3亿元。"])
    candidates = _candidates(parsed, pipeline)[0]
    assert {c.unit.unit_id for c in candidates} == {parsed.units[0].unit_id}


@pytest.mark.parametrize(
    "limits", [{"max_window_chars": 1}, {"max_units": 1}, {"max_work_units": 0}]
)
def test_known_deferred_native_statement_cannot_fall_back_to_complete_single_fragments(
    monkeypatch, limits
):
    from company_wiki.source_catalog import narrative_reading as reading

    actual = reading.build_native_continuity
    monkeypatch.setattr(
        reading,
        "build_native_continuity",
        lambda *args, **kwargs: actual(*args, **kwargs, limits=limits),
    )
    parsed, pipeline = source_case(["该设备已进入客户进行生产验", "证，尚未量产。"])
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, pipeline
    )
    assert not candidates and not eligible and not complete
    assert set(withheld[0]["known_unit_ids"]) == {u.unit_id for u in parsed.units}


def test_diagnostic_id_cap_cannot_silently_admit_remaining_deferred_originals(
    monkeypatch,
):
    from company_wiki.source_catalog import narrative_reading as reading

    actual = reading.build_native_continuity
    observed = []

    def capped(*args, **kwargs):
        result = actual(*args, **kwargs, limits={"max_window_chars": 1})
        observed.append(result)
        return result

    monkeypatch.setattr(reading, "build_native_continuity", capped)
    texts = [
        text
        for _i in range(70)
        for text in ("该设备已进入客户进行生产验", "证，尚未量产。")
    ]
    rows = [native(text, i) for i, text in enumerate(texts)]
    for row in rows:
        row[0]["layout"]["page_height"] = 4000
    parsed, pipeline = source_case(texts, native_rows=rows)
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, pipeline
    )
    assert not candidates and not eligible and not complete
    assert observed[0]["deferred_unit_count"] == 140
    assert (
        observed[0]["deferred_limited"] and len(observed[0]["deferred_unit_ids"]) == 128
    )
    assert len(observed[0]["deferred_unit_ranges"]) == 70
    assert set(withheld[0]["known_unit_ids"]) == {u.unit_id for u in parsed.units}


def test_two_closed_windows_share_heading_cost_but_not_each_others_body():
    from company_wiki.source_catalog import narrative_reading as reading
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute

    parsed, pipeline = source_case(
        [
            "主要业务",
            "该设备已进入客户生产验",
            "证，尚未量产。",
            "另一设备已送至客户进行生产验",
            "证。",
        ],
        heading=True,
    )
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, pipeline
    )
    head = parsed.units[0].unit_id
    pairs = [
        {u.unit_id for u in parsed.units[1:3]},
        {u.unit_id for u in parsed.units[3:5]},
    ]
    for pair in pairs:
        for uid in pair:
            if not metadata[uid]["context_only"]:
                assert set(metadata[uid]["required"]) | {uid} == pair | {head}
    assert len(eligible) == 2 and complete and not withheld
    full = finalize_selection(
        parsed,
        DocumentRoute("semi_annual", 5, False),
        candidates,
        group_ids={},
        heading_pattern=reading._NEVER_HEADING,
        dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY,
        reading_metadata=metadata,
        max_chars=48000,
    )
    assert len(full.evidence_spans) == 5
    assert [s.raw_text for s in full.evidence_spans] == [
        u.raw_text for u in parsed.units
    ]


def test_real_shared_context_groups_keep_original_span_ids_and_native_order():
    from company_wiki.source_catalog import narrative_reading as reading
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute

    parsed, pipeline = source_case(
        ["主要业务", "该设备已进入客户生产验", "证，尚未量产。"], heading=True
    )
    # Use the actual shared pipeline for policy/unread data, replacing only the
    # source-owned package container whose old anchor bug is under test.
    actual = reading._understand(
        parsed,
        title="2027年半年度报告",
        kind="semi_annual",
        mime_type="application/pdf",
    )
    actual["packages"] = pipeline["packages"]
    actual["reading_plan"]["unit_profiles"] = pipeline["reading_plan"]["unit_profiles"]
    actual["structure"]["sections"] = pipeline["structure"]["sections"]
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, actual
    )
    selected = finalize_selection(
        parsed,
        DocumentRoute("semi_annual", 3, False),
        candidates,
        group_ids={},
        heading_pattern=reading._NEVER_HEADING,
        dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY,
        reading_metadata=metadata,
        max_chars=48000,
    )
    actual["selected_span_ids"] = {
        u.unit_id: s.span_id for u, s in zip(parsed.units, selected.evidence_spans)
    }
    context = reading._context(actual, selected, eligible)
    assert complete and not withheld
    assert len(context["groups"]) == 1
    assert context["groups"][0]["kind"] == "native_continuity"
    assert context["groups"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans
    ]
    assert all(set(group) == {
        "group_id", "kind", "section_role", "evidence_ids", "citation_views",
    } for group in context["groups"])
    assert all(set(view) == {"support_evidence_ids", "context_evidence_ids"}
               for group in context["groups"] for view in group["citation_views"])
    assert not any(span.raw_text in str(context["groups"])
                   for span in selected.evidence_spans)


def test_independent_english_billing_relation_uses_originals_without_guessing_word_repair():
    from dataclasses import replace
    from company_wiki.source_catalog.narrative_reading import _candidates

    texts = ["Service charges depend on actual", "resources consumed by customers."]
    parsed, pipeline = source_case(texts, role="unknown")
    parsed = replace(
        parsed,
        language="en",
        units=tuple(replace(u, language="en") for u in parsed.units),
    )
    for wire in pipeline["observation"]["units"]:
        wire["language"] = "en"
    candidates, metadata, eligible, complete, withheld = _candidates(parsed, pipeline)
    assert len(eligible) == 1 and eligible[0]["kind"] == "native_continuity"
    assert complete and not withheld
    assert any(
        value.get("value_band") == "meaningful_fact" for value in metadata.values()
    )
    assert [c.unit.raw_text for c in candidates] == texts
    assert all(c.unit is u for c, u in zip(candidates, parsed.units))


@pytest.mark.parametrize(
    "texts",
    [
        # Already recorded p13/p18 text fragments; the carrier below is synthetic
        # geometry for a pure regression, not another real-PDF parse or fine-cell
        # claim. Corpus words never enter the implementation grammar.
        [
            "目前公司的五十多种设备产品已经覆盖了超30%前道集成电路设备产品，未来五年，公司将通",
            "过自主开发与外延并购，覆盖60%以上的集成电路高端设备市场和70%以上的先进封装设备市",
            "场，在规模上成为全球领先的高端设备平台型公司。",
        ],
        [
            "公司用于先进封装等离子体切割的Primo Matrix 即将发往国内",
            "头部客户产线验证。",
        ],
    ],
)
def test_recorded_word_breaks_preserve_current_future_and_verification_qualifiers(
    texts,
):
    from company_wiki.source_catalog.narrative_reading import _candidates

    parsed, pipeline = source_case(texts)
    original = [
        (u.unit_id, u.raw_text, u.coordinates, dict(u.metadata)) for u in parsed.units
    ]
    candidates, metadata, eligible, complete, withheld = _candidates(parsed, pipeline)
    assert len(eligible) == 1 and eligible[0]["kind"] == "native_continuity"
    assert complete and not withheld
    assert [c.unit.raw_text for c in candidates] == texts
    assert [
        (u.unit_id, u.raw_text, u.coordinates, dict(u.metadata)) for u in parsed.units
    ] == original
    assert set(eligible[0]["member_unit_ids"]) == {u.unit_id for u in parsed.units}
    assert any(
        value.get("value_band") == "meaningful_fact" for value in metadata.values()
    )
    assert all(
        "continuity" not in key
        for c in candidates
        for key in c.unit.to_evidence_span(
            topics=c.topics, selection_reasons=c.reasons
        ).structured_value
    )


def test_complete_prefix_before_cap_does_not_hide_a_single_open_statement_tail(
    monkeypatch,
):
    from company_wiki.source_catalog import narrative_reading as reading

    texts = ["首个设备已验证。", "第二个设备已交付。", "另一个项目仍处于"]
    rows = []
    start = 0
    for i, text in enumerate(texts):
        rows.append(native(text, i, block=3, start=start, box=[90, 100, 550, 132]))
        start += len(text)
    actual = reading.build_native_continuity
    monkeypatch.setattr(
        reading,
        "build_native_continuity",
        lambda *args, **kwargs: actual(*args, **kwargs, limits={"max_window_units": 2}),
    )
    result = run(rows, max_window_units=2)
    assert not result["complete"]
    assert result["deferred_unit_ids"] == [rows[-1][0]["unit_id"]]
    parsed, pipeline = source_case(texts, native_rows=rows)
    candidates, metadata, eligible, complete, withheld = reading._candidates(
        parsed, pipeline
    )
    assert not complete and withheld
    assert parsed.units[-1].unit_id not in {c.unit.unit_id for c in candidates}


@pytest.mark.parametrize("colon", [":", "："])
def test_body_definition_colon_is_an_open_continuation_not_a_heading(colon):
    rows = [
        native("我们的门店运营方式为" + colon, 0),
        native("通过直营和合伙人模式为消费者提供服务。", 1),
    ]
    result = run(rows)
    assert result["complete"]
    assert len(result["windows"]) == 1
    assert result["windows"][0]["member_unit_ids"] == [r[0]["unit_id"] for r in rows]



def _native_numbered_scope_case(*, reverse=False, indented=True):
    from dataclasses import replace
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view

    names = ["检测服务", "技术服务"]
    if reverse:
        names.reverse()
    blocks = [
        ("一、经营情况",),
        ("(1) " + names[0] + "实现收入12亿元。", "报告期内："),
        ("-\n新产品收入占比超过30%。",),
        ("(2) " + names[1] + "实现收入9亿元。", "报告期内："),
        ("-\n新产品收入占比超过30%。",),
        ("公司整体计划仍受市场变化影响。",),
    ]
    parsed, _ = source_fixture(blocks)
    boxes = [(110 if indented and i in {2, 4} else 90, 100 + 20*i,
              550, 112 + 20*i) for i in range(len(blocks))]
    view = build_native_page_view([(i, box, "\n".join(blocks[i])) for i, box in enumerate(boxes)])
    updated=[]
    for unit in parsed.units:
        metadata={key: deepcopy(value) for key, value in unit.metadata.items()
                  if key != "native_source_view"}
        metadata["reading_layout"]["layout"]["bbox"] = list(boxes[metadata["pdf_block"]])
        metadata["native_source_view"] = view
        updated.append(replace(unit, metadata=metadata))
    return replace(parsed, units=tuple(updated))


@pytest.mark.parametrize("reverse", [False, True])
def test_native_numbered_intro_and_indented_bullets_declare_own_bounded_scope(reverse):
    from company_wiki.source_catalog import narrative_reading as reading

    parsed = _native_numbered_scope_case(reverse=reverse)
    pipeline = reading._understand(parsed, title="年度报告", kind="annual_report", mime_type="application/pdf")
    units = {unit.unit_id: unit for unit in parsed.units}
    scope_for = {uid: section for section in pipeline["structure"]["sections"]
                 for uid in section.get("body_unit_ids", ())}
    for anchor, parent, intro, sibling in ((3, 1, 2, 4), (6, 4, 5, 1)):
        heads = scope_for[parsed.units[anchor].unit_id]["heading_unit_ids"]
        assert set(heads) == {parsed.units[parent].unit_id, parsed.units[intro].unit_id}
        assert parsed.units[sibling].unit_id not in heads
    assert not any("实现收入" in units[uid].raw_text
                   for uid in scope_for[parsed.units[-1].unit_id]["heading_unit_ids"])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    for anchor, parent, intro, sibling in ((3, 1, 2, 4), (6, 4, 5, 1)):
        required = set(metadata[parsed.units[anchor].unit_id]["required"])
        assert {parsed.units[parent].unit_id, parsed.units[intro].unit_id} <= required
        assert parsed.units[sibling].unit_id not in required
    assert complete and not withheld


def test_parenthetical_inline_enumeration_and_unindented_body_do_not_declare_scope():
    from dataclasses import replace
    from company_wiki.source_catalog import narrative_reading as reading

    parsed = _native_numbered_scope_case(indented=False)
    pipeline = reading._understand(parsed, title="年度报告", kind="annual_report", mime_type="application/pdf")
    assert not any("native_numbered_list" in section.get("basis", ())
                   for section in pipeline["structure"]["sections"])
    parsed = replace(parsed, units=tuple(
        replace(unit, raw_text="正文提到" + unit.raw_text) if unit.raw_text.startswith("(") else unit
        for unit in parsed.units))
    pipeline = reading._understand(parsed, title="年度报告", kind="annual_report", mime_type="application/pdf")
    assert not any("native_numbered_list" in section.get("basis", ())
                   for section in pipeline["structure"]["sections"])
