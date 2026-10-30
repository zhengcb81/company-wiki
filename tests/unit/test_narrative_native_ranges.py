"""Exact named native-view ranges; no model joining, original rewrites or IO."""

from dataclasses import replace
from hashlib import sha256
from importlib import import_module

import pytest

from company_wiki.source_catalog.narrative_evidence import (
    _make_unit,
    parse_pdf_bytes,
    verify_pdf_evidence_spans_bytes,
)
from company_wiki.source_catalog.narrative_replay import (
    prepare_pdf_replay_bytes,
    verify_replayed_pdf_spans,
)
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    source_id_for_sha256,
)

SOURCE = source_id_for_sha256("a" * 64)


def api():
    return import_module("company_wiki.source_catalog.narrative_native_ranges")


def members(texts=("设备已进入客户生产验", "证，尚未量产。"), *, blocks=None):
    blocks = list(range(len(texts))) if blocks is None else blocks
    full = {}
    for block, text in zip(blocks, texts):
        full[block] = full.get(block, "") + text
    view = api().build_native_page_view(
        [(block, (0, 0, 400, 12), text) for block, text in full.items()]
    )
    offsets = {}
    result = []
    for i, (block, text) in enumerate(zip(blocks, texts)):
        start = offsets.get(block, 0)
        offsets[block] = start + len(text)
        result.append(
            _make_unit(
                source_id=SOURCE,
                parser_version="0.1.1",
                coordinates=EvidenceCoordinates(page_number=2, paragraph_index=i),
                raw_text=text,
                unit_kind="pdf_text_block",
                source_role="company_filing",
                language="zh",
                metadata={
                    "pdf_block": block,
                    "block_sha256": sha256(full[block].encode()).hexdigest(),
                    "block_char_start": start,
                    "block_char_end": start + len(text),
                    "native_source_view": view,
                },
            )
        )
    return result, view


def as_span(unit):
    return unit.to_evidence_span(
        topics=("business_progress",), selection_reasons=("reading_plan",)
    )


@pytest.mark.parametrize("value", [None, [], True])
def test_native_parser_with_non_mapping_binding_is_rejected_without_attribute_error(value):
    original, _ = members()
    row = EvidenceSpan.create(source_id=SOURCE, coordinates=original[0].coordinates,
        raw_text=original[0].raw_text, structured_value=value,
        parser_name="native_pdf_range_parser", parser_version="0.1.0",
        parse_status="parsed", quality_flags=())
    assert api().verify_native_range_span(row, original) is False
    verified, failed = verify_replayed_pdf_spans([row], original)
    assert verified == () and failed == (row.span_id,)


def test_native_parser_name_cannot_fall_back_to_an_ordinary_raw_locator_match():
    original, _ = members()
    row = edited(as_span(original[0]), parser_name="native_pdf_range_parser")
    verified, failed = verify_replayed_pdf_spans([row], original)
    assert verified == () and failed == (row.span_id,)


def edited(
    span,
    *,
    text=None,
    value=None,
    coordinates=None,
    parser_name=None,
    parser_version=None,
    source_id=None,
):
    return EvidenceSpan.create(
        source_id=source_id or span.source_id,
        coordinates=coordinates or span.coordinates,
        raw_text=span.raw_text if text is None else text,
        structured_value=span.structured_value if value is None else value,
        parser_name=parser_name or span.parser_name,
        parser_version=parser_version or span.parser_version,
        parse_status=span.parse_status,
        quality_flags=span.quality_flags,
    )


def plain(value):
    from collections.abc import Mapping

    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def test_named_view_is_immutable_nfc_and_preserves_native_line_sequence():
    raw = "Cafe\u0301\r\n设备"
    view = api().build_native_page_view(
        [(7, (1, 2, 3, 4), raw), (9, (1, 6, 3, 8), "客户验证。")]
    )
    assert view["schema_version"] == "native-pdf-page-view/1"
    assert view["text"] == "Café\n设备\n客户验证。"
    assert view["page_view_sha256"] == sha256(view["text"].encode()).hexdigest()
    assert view["blocks"][0]["block_sha256"] == sha256(raw.encode()).hexdigest()
    assert [b["pdf_block"] for b in view["blocks"]] == [7, 9]
    with pytest.raises(TypeError):
        view["text"] = "changed"
    with pytest.raises(TypeError):
        view["blocks"][0]["view_char_start"] = 1


def test_range_is_one_exact_view_substring_with_full_original_member_binding():
    units, view = members()
    unit = api().native_range_unit(units)
    assert unit is not None
    assert (
        unit.parser_name == "native_pdf_range_parser" and unit.parser_version == "0.1.0"
    )
    assert unit.unit_kind == "pdf_native_range"
    assert (
        unit.raw_text
        == view["text"][unit.coordinates.char_start : unit.coordinates.char_end]
    )
    assert unit.raw_text == units[0].raw_text + "\n" + units[1].raw_text
    assert unit.coordinates.page_number == 2 and unit.coordinates.paragraph_index == 0
    binding = unit.metadata["native_range"]
    assert binding["base_parser_version"] == "0.1.1"
    assert tuple(binding["source_unit_ids"]) == tuple(u.unit_id for u in units)
    assert len(binding["members"]) == 2
    assert "native_source_view" not in unit.metadata
    assert api().verify_native_range_span(as_span(unit), units)


def test_nfd_original_offsets_map_to_the_exact_nfc_view_coordinates():
    raw = "Cafe\u0301设备。客户验证。"
    view = api().build_native_page_view([(4, (0, 0, 100, 20), raw)])
    parts = [raw[:8], raw[8:]]
    units = []
    for i, text in enumerate(parts):
        start = 0 if i == 0 else 8
        units.append(
            _make_unit(
                source_id=SOURCE,
                parser_version="0.1.1",
                coordinates=EvidenceCoordinates(page_number=2, paragraph_index=i),
                raw_text=text,
                unit_kind="pdf_text_block",
                source_role="company_filing",
                language="zh",
                metadata={
                    "pdf_block": 4,
                    "block_sha256": sha256(raw.encode()).hexdigest(),
                    "block_char_start": start,
                    "block_char_end": start + len(text),
                    "native_source_view": view,
                },
            )
        )
    unit = api().native_range_unit(units)
    assert unit is not None and unit.raw_text == "Café设备。客户验证。"
    assert unit.coordinates.char_end == len(view["text"])


def test_transient_view_does_not_change_old_unit_or_evidence_ids():
    original = _make_unit(
        source_id=SOURCE,
        parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="设备已完成客户验证。",
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="zh",
        metadata={"pdf_block": 0},
    )
    enriched = replace(
        original,
        metadata={
            **original.metadata,
            "native_source_view": {"text": "must-never-export"},
        },
    )
    assert enriched.unit_id == original.unit_id
    assert as_span(enriched) == as_span(original)


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "page",
        "paragraph",
        "kind",
        "role",
        "block_sha",
        "word",
        "view",
        "version",
        "missing",
    ],
)
def test_invalid_or_missing_native_member_provenance_is_not_a_range(change):
    units, view = members()
    u = units[1]
    meta = dict(u.metadata)
    if change == "source":
        u = replace(u, source_id=source_id_for_sha256("b" * 64))
    elif change == "page":
        u = replace(
            u, coordinates=EvidenceCoordinates(page_number=3, paragraph_index=1)
        )
    elif change == "paragraph":
        u = replace(
            u, coordinates=EvidenceCoordinates(page_number=2, paragraph_index=4)
        )
    elif change == "kind":
        u = replace(u, unit_kind="pdf_table_row")
    elif change == "role":
        u = replace(u, source_role="investor_question")
    elif change == "block_sha":
        meta["block_sha256"] = "b" * 64
    elif change == "word":
        u = replace(u, raw_text="证，已达到量产。")
    elif change == "view":
        meta["native_source_view"] = dict(view)
    elif change == "version":
        u = replace(u, parser_version="0.1.0")
    else:
        meta.pop("native_source_view")
    units[1] = replace(u, metadata=meta)
    assert api().native_range_unit(units) is None


def test_skipped_non_whitespace_source_stage_cannot_be_hidden_in_a_range():
    units, view = members(
        ("客户已开展验证。", "尚未量产。", "未来将交付样机。"), blocks=[0, 0, 0]
    )
    # Even if a caller falsifies the paragraph counter, the unbound stage bytes
    # in the real source view cannot be skipped or silently included.
    last = replace(
        units[2], coordinates=EvidenceCoordinates(page_number=2, paragraph_index=1)
    )
    assert api().native_range_unit([units[0], last]) is None


@pytest.mark.parametrize(
    "texts,blocks",
    [
        (tuple("研发片段" for _ in range(9)), [0] * 9),
        (("研发",) * 5, list(range(5))),
        (("研" * 1024, "发" * 1024), [0, 1]),
    ],
)
def test_pure_range_bounds_include_native_view_characters(texts, blocks):
    units, _view = members(texts, blocks=blocks)
    assert api().native_range_unit(units) is None


@pytest.mark.parametrize(
    "change", ["stage", "binding", "locator", "name", "version", "source"]
)
def test_replay_rejects_changed_range_bytes_bindings_or_pinned_parser(change):
    units, _view = members()
    unit = api().native_range_unit(units)
    span = as_span(unit)
    value = plain(span.structured_value)
    if change == "stage":
        changed = edited(span, text=span.raw_text.replace("尚未", "已经"))
    elif change == "binding":
        value["native_range"]["source_unit_ids"].pop()
        changed = edited(span, value=value)
    elif change == "locator":
        changed = edited(
            span,
            coordinates=replace(
                span.coordinates, char_end=span.coordinates.char_end - 1
            ),
        )
    elif change == "name":
        changed = edited(span, parser_name="unverified_range_parser")
    elif change == "version":
        changed = edited(span, parser_version="9.9.9")
    else:
        changed = edited(span, source_id=source_id_for_sha256("b" * 64))
    assert not api().verify_native_range_span(changed, units)
    assert verify_replayed_pdf_spans([changed], units) == ((), (changed.span_id,))


def tiny_pdf():
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (60, 80),
        "产品研发已取得进展。\n下半年将根据客户反馈开展验证。",
        fontname="china-s",
        fontsize=12,
    )
    raw = document.tobytes()
    document.close()
    digest = sha256(raw).hexdigest()
    return raw, source_id_for_sha256(digest), digest


@pytest.mark.parametrize('parser_version', ['0.1.1', '0.1.2'])
def test_real_small_pdf_range_reopens_exactly_and_can_coexist_with_old_spans(parser_version):
    raw, source, digest = tiny_pdf()
    legacy = parse_pdf_bytes(raw, source_id=source, source_sha256=digest,
                             parser_version=parser_version)
    parsed = parse_pdf_bytes(
        raw, source_id=source, source_sha256=digest, selector_version="0.9.0",
        parser_version=parser_version,
    )
    assert [u.unit_id for u in parsed.units] == [u.unit_id for u in legacy.units]
    assert [as_span(u) for u in parsed.units] == [as_span(u) for u in legacy.units]
    views = [
        u.metadata["native_source_view"]
        for u in parsed.units
        if u.unit_kind == "pdf_text_block"
    ]
    assert len(views) >= 2 and all(view is views[0] for view in views)
    unit = api().native_range_unit(parsed.units[:2])
    assert unit is not None
    native = as_span(unit)
    old = as_span(legacy.units[0])
    plan = prepare_pdf_replay_bytes(
        raw,
        source_id=source,
        source_sha256=digest,
        evidence_spans=[native, old],
        default_parser_version="9.9.9",
    )
    assert plan.parser_version == parser_version and plan.native_ranges is True
    verified, failed = verify_pdf_evidence_spans_bytes(
        raw, source_id=source, source_sha256=digest, evidence_spans=[native, old]
    )
    assert verified == (native.span_id, old.span_id) and not failed
    assert "native_source_view" not in native.structured_value


def test_native_view_zero_budget_preserves_all_old_units_and_marks_no_range():
    raw, source, digest = tiny_pdf()
    legacy = parse_pdf_bytes(raw, source_id=source, source_sha256=digest)
    bounded = parse_pdf_bytes(
        raw,
        source_id=source,
        source_sha256=digest,
        selector_version="0.9.0",
        native_range_limits={"max_total_chars": 0},
    )
    assert [as_span(u) for u in legacy.units] == [as_span(u) for u in bounded.units]
    # Optional view unavailability is not a failure to read immutable bytes.
    assert bounded.errors == legacy.errors
    assert bounded.layout_coverage["native_ranges"]["complete"] is False
    assert any(
        d["code"] == "NATIVE_RANGE_VIEW_BUDGET" for d in bounded.layout_diagnostics
    )
    assert all("native_source_view" not in u.metadata for u in bounded.units)
    assert api().native_range_unit(bounded.units[:2]) is None


def test_snapshot_is_not_read_again_for_native_view(monkeypatch):
    from company_wiki.source_catalog import narrative_evidence as module

    calls = []

    class Page:
        def get_text(self, kind, sort=False):
            calls.append(kind)
            return {
                "blocks": [
                    {
                        "type": 0,
                        "bbox": [0, 0, 100, 20],
                        "lines": [{"spans": [{"text": "设备已进入客户验证。"}]}],
                    }
                ]
            }

    blocks = module._pdf_text_blocks(Page())
    view = api().build_native_page_view(blocks)
    assert view["text"] == blocks[0][2] and calls == ["dict"]


def test_legacy_qa_parser_version_and_unknown_mixed_versions_are_preserved():
    raw = b"immutable"
    digest = sha256(raw).hexdigest()
    source = source_id_for_sha256(digest)
    unit = _make_unit(
        source_id=source,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="legacy",
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="en",
        metadata={},
    )
    plan = prepare_pdf_replay_bytes(
        raw,
        source_id=source,
        source_sha256=digest,
        evidence_spans=[as_span(unit)],
        default_parser_version="9.9.9",
    )
    assert plan.parser_version == "0.1.0" and plan.native_ranges is False
    other = replace(unit, parser_version="0.2.0")
    with pytest.raises(ValueError, match="one parser version"):
        prepare_pdf_replay_bytes(
            raw,
            source_id=source,
            source_sha256=digest,
            evidence_spans=[as_span(unit), as_span(other)],
            default_parser_version="9.9.9",
        )


def test_page_view_and_total_view_limits_cannot_be_raised_or_truthy():
    assert (
        api().build_native_page_view([(0, (0, 0, 1, 1), "text")], max_chars=0) is None
    )
    assert (
        api().build_native_page_view(
            [(0, (0, 0, 1, 1), "x" * 200001)], max_chars=999999
        )
        is None
    )
    assert (
        api().native_range_limits({"max_total_chars": 9999999})["max_total_chars"]
        == 2000000
    )
    for invalid in (True, -1, "1"):
        with pytest.raises(ValueError):
            api().native_range_limits({"max_page_chars": invalid})


def test_total_page_view_budget_defer_is_diagnostic_and_preserves_second_page():
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for _i in range(2):
        page = document.new_page()
        page.insert_text(
            (60, 80), "产品已进入客户验证。", fontname="china-s", fontsize=12
        )
    raw = document.tobytes()
    document.close()
    digest = sha256(raw).hexdigest()
    source = source_id_for_sha256(digest)
    legacy = parse_pdf_bytes(raw, source_id=source, source_sha256=digest)
    bounded = parse_pdf_bytes(
        raw,
        source_id=source,
        source_sha256=digest,
        native_ranges=True,
        native_range_limits={"max_total_chars": len(legacy.units[0].raw_text)},
    )
    assert [as_span(u) for u in legacy.units] == [as_span(u) for u in bounded.units]
    assert bounded.errors == legacy.errors
    coverage = bounded.layout_coverage["native_ranges"]
    assert coverage["captured_chars"] == len(legacy.units[0].raw_text)
    assert (
        coverage["deferred_pages"] == [2]
        and coverage["deferred_page_count"] == 1
        and not coverage["complete"]
    )


def test_malformed_frozen_member_binding_fails_without_crashing():
    units, _view = members()
    span = as_span(api().native_range_unit(units))
    value = plain(span.structured_value)
    value["native_range"]["source_unit_ids"] = [{"not": "a member id"}]
    assert not api().verify_native_range_span(edited(span, value=value), units)
    value["native_range"] = None
    with pytest.raises(ValueError, match="unverified native range"):
        prepare_pdf_replay_bytes(
            b"original",
            source_id=SOURCE,
            source_sha256=sha256(b"original").hexdigest(),
            evidence_spans=[edited(span, value=value)],
            default_parser_version="0.1.1",
        )


def test_shared_replay_index_is_built_once_for_multiple_native_ranges():
    units, _view = members(
        tuple("设备研发已进入客户验证阶段。" for _ in range(8)), blocks=list(range(8))
    )
    spans = [as_span(api().native_range_unit(units[i : i + 2])) for i in range(0, 8, 2)]

    class Counted(list):
        passes = 0

        def __iter__(self):
            self.passes += 1
            return super().__iter__()

    fresh = Counted(units)
    assert verify_replayed_pdf_spans(spans, fresh) == (
        tuple(s.span_id for s in spans),
        (),
    )
    assert fresh.passes <= 2
