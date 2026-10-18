"""B2 source-side antecedent window and production wiring controls.

Synthetic source text only: no parser, PDF, provider, model or corpus write.
"""
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_antecedent import (
    build_antecedent_windows, within_reference_envelope,
)
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

DECLARATION = "公司推出Preforma Uniflash系列金属硅化物集成系统，包含SA/SU、SPTi、ALDTiNM三类产品。"
TARGET = "该系列产品已交付多个先进客户。"
PLAIN = "公司向客户交付样机开展生产验证，尚未获准量产。"


def text_case(texts, *, kinds=None, sections=None, pages=None):
    source = source_id_for_sha256("a" * 64)
    units, wires = [], []
    for index, text in enumerate(texts):
        unit = _make_unit(source_id=source, parser_version="1.0.0",
            coordinates=EvidenceCoordinates(page_number=(pages or {}).get(index, 1),
                                            paragraph_index=index),
            raw_text=text, unit_kind="text_block", source_role="company_filing",
            language="zh", metadata={})
        units.append(unit)
        wires.append({"unit_id": unit.unit_id, "ordinal": index,
            "page": (pages or {}).get(index, 1),
            "text": text, "kind": (kinds or {}).get(index, "paragraph"),
            "role": "company_filing", "language": "zh", "layout": {},
            "hints": {"source_id": source, "section_key": (sections or {}).get(index, "business")}})
    ids = [unit.unit_id for unit in units]
    parsed = DocumentStructure(source_id=source, source_sha256="a" * 64,
        language="zh", units=tuple(units), line_count=len(texts), mime_type="text/plain")
    pipeline = {
        "observation": {"units": wires},
        "reading_plan": {"unit_profiles": {uid: {
            "reading_profile_key": "root", "section_role": "business", "priority": 2}
            for uid in ids}},
        "structure": {"sections": [
            {"section_id": section, "parent_id": None, "heading_unit_ids": [],
             "body_unit_ids": [ids[index] for index in range(len(ids))
                               if (sections or {}).get(index, "business") == section]}
            for section in dict.fromkeys((sections or {}).get(index, "business")
                                         for index in range(len(ids)))]},
        "packages": {"packages": [{"package_id": "background", "kind": "background",
            "member_unit_ids": ids, "anchor_unit_ids": ids}]},
    }
    return parsed, pipeline, ids


# ------------------------------------------------------------------- window


def test_window_returns_only_strictly_preceding_units_in_source_order():
    parsed, pipeline, ids = text_case([DECLARATION, PLAIN, TARGET])
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids))
    window = windows[ids[2]]
    assert window["predecessor_unit_ids"] == (ids[0], ids[1])
    assert window["complete"] is True


def test_window_stops_at_a_section_or_role_boundary():
    parsed, pipeline, ids = text_case([DECLARATION, PLAIN, TARGET],
        sections={0: "other-section"})
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids))
    assert windows[ids[2]]["predecessor_unit_ids"] == (ids[1],)
    assert windows[ids[2]]["stop_reason"] == "source_boundary"


def test_window_stops_at_excluded_or_table_ownership():
    parsed, pipeline, ids = text_case([DECLARATION, PLAIN, TARGET])
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids),
        excluded={ids[1]})
    assert windows[ids[2]]["predecessor_unit_ids"] == ()
    assert windows[ids[2]]["stop_reason"] == "source_boundary"


def test_window_marks_cap_truncation_as_incomplete():
    texts = [DECLARATION] + [PLAIN] * 9 + [TARGET]
    parsed, pipeline, ids = text_case(texts)
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids))
    window = windows[ids[-1]]
    assert len(window["predecessor_unit_ids"]) == 8
    assert window["complete"] is False
    assert window["stop_reason"] == "cap"


# ----------------------------------------------------------------- envelope


def _evidence(uid, *, page=1, block=None, text="x" * 10, parent="source-a"):
    metadata = {} if block is None else {"pdf_block": block}
    return _make_unit(source_id=parent, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=0),
        raw_text=text, unit_kind="text_block", source_role="company_filing",
        language="zh", metadata=metadata).__dict__ | {"unit_id": uid}


def test_envelope_accepts_exactly_eight_units_four_blocks_and_2048_characters():
    units = {f"u{i}": _evidence(f"u{i}", block=i % 4) for i in range(9)}
    assert within_reference_envelope(["u0"], ["u1", "u2", "u3"], ["u4", "u5", "u6", "u7"], units)
    assert not within_reference_envelope(["u0"], ["u1", "u2", "u3"], ["u4", "u5", "u6", "u7", "u8"], units)
    blocks = {f"b{i}": _evidence(f"b{i}", block=i) for i in range(5)}
    assert not within_reference_envelope(["b0"], ["b1", "b2", "b3"], ["b4"], blocks)
    long = {f"c{i}": _evidence(f"c{i}", text="y" * 1025) for i in range(3)}
    assert not within_reference_envelope(["c0"], ["c1"], ["c2"], long)


def test_same_block_number_on_two_pages_is_two_blocks():
    units = {"p7": _evidence("p7", page=7, block=3), "p8": _evidence("p8", page=8, block=3)}
    assert within_reference_envelope(["p7"], [], ["p8"], units)


# --------------------------------------------------------------- production


def _candidates(texts, **kwargs):
    parsed, pipeline, ids = text_case(texts, **kwargs)
    result = reading._candidates(parsed, pipeline)
    return ids, result


def test_unresolved_deictic_defers_only_that_card():
    ids, (ordered, metadata, packages, complete, withheld) = _candidates([PLAIN, TARGET])
    assert ids[1] not in {candidate.unit.unit_id for candidate in ordered}
    assert any(entry.get("reason") == "REFERENCE_UNRESOLVED" for entry in withheld)


def test_resolved_deictic_attaches_the_original_declaration_as_context():
    ids, (ordered, metadata, packages, complete, withheld) = _candidates([DECLARATION, TARGET])
    assert ids[1] in {candidate.unit.unit_id for candidate in ordered}
    assert ids[0] in metadata[ids[1]]["required"]
    assert not any(entry.get("reason") == "REFERENCE_UNRESOLVED" for entry in withheld)


def test_plain_statement_without_a_deictic_is_unchanged():
    ids, (ordered, metadata, packages, complete, withheld) = _candidates([DECLARATION, PLAIN])
    assert ids[1] in {candidate.unit.unit_id for candidate in ordered}
    assert not any(entry.get("reason") == "REFERENCE_UNRESOLVED" for entry in withheld)


def test_declaration_is_context_for_the_target_not_its_support():
    ids, (ordered, metadata, packages, complete, withheld) = _candidates([DECLARATION, TARGET])
    assert ids[0] in metadata[ids[1]]["required"]
    assert metadata[ids[1]]["context_only"] is False
    assert ids[0] not in {candidate.unit.unit_id for candidate in ordered
                          if candidate.unit.unit_id == ids[1] and ids[0] in candidate.reasons}



# ------------------------------------------------------- review-driven controls


def test_window_marks_an_unread_predecessor_as_incomplete():
    parsed, pipeline, ids = text_case([DECLARATION, PLAIN, TARGET])
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids),
        blocked=frozenset({ids[1]}))
    window = windows[ids[2]]
    assert window["predecessor_unit_ids"] == ()
    assert window["complete"] is False
    assert window["stop_reason"] == "unread"


def test_cross_page_predecessor_requires_a_proven_carry():
    parsed, pipeline, ids = text_case([DECLARATION, TARGET], pages={1: 2})
    unproven = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids),
        require_adjacency_proof=True)
    assert unproven[ids[1]]["predecessor_unit_ids"] == ()
    assert unproven[ids[1]]["complete"] is False
    assert unproven[ids[1]]["stop_reason"] == "unproved_order"
    proven = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids),
        page_carries=frozenset({(ids[0], ids[1])}), require_adjacency_proof=True)
    assert proven[ids[1]]["predecessor_unit_ids"] == (ids[0],)
    assert proven[ids[1]]["complete"] is True


def test_envelope_counts_one_block_across_paragraphs_on_the_same_page():
    units = {"a": _evidence("a", block=3), "b": _evidence("b", block=3),
             "c": _evidence("c", block=3), "d": _evidence("d", block=3)}
    assert within_reference_envelope(["a"], ["b", "c"], ["d"], units)


def test_envelope_expands_a_carrier_to_all_of_its_originals():
    units = {f"o{i}": _evidence(f"o{i}", block=i) for i in range(5)}
    def expand(uid):
        return tuple(units) if uid == "carrier" else (uid,)
    assert not within_reference_envelope(["carrier"], [], [], units, expand=expand)
    assert within_reference_envelope(["o0"], [], [], units, expand=expand)


def test_resolved_deictic_reaches_the_group_context_end_to_end():
    parsed, pipeline, ids = text_case([DECLARATION, TARGET])
    package = reading.select_reading_evidence(parsed, title="2027年半年度报告",
        existing_kind="semi_annual")
    texts = {span.span_id: span.raw_text for span in package.evidence_spans}
    assert any("Preforma Uniflash" in text for text in texts.values())
    assert any(text.startswith("该系列产品") for text in texts.values())
    declaration_ids = {span_id for span_id, text in texts.items()
                       if "Preforma Uniflash" in text}
    target_ids = {span_id for span_id, text in texts.items()
                  if text.startswith("该系列产品")}
    target_groups = [group for group in package.reading_context["groups"]
                     if set(group["evidence_ids"]) & target_ids]
    assert target_groups
    for group in target_groups:
        for view in group["citation_views"]:
            assert not (set(view["support_evidence_ids"]) & declaration_ids)
            assert set(view["context_evidence_ids"]) & declaration_ids



def test_reference_deferral_does_not_downgrade_the_whole_document():
    parsed, pipeline, ids = text_case([PLAIN, PLAIN, TARGET, PLAIN, PLAIN])
    package = reading.select_reading_evidence(parsed, title="T", existing_kind="semi_annual")
    assert package.coverage_complete is True
    assert package.status == "selected"
    assert len(package.evidence_spans) == 4
    reasons = [entry.get("reason") for entry in package.reading_context["deferred"]]
    assert "REFERENCE_UNRESOLVED" in reasons
