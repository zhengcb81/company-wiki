"""Original statement/value boundaries, independent of issuer or gold vocabulary."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_routing import DocumentRoute
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def fixture(texts, *, same_block=True, language="zh", heading=False):
    source = source_id_for_sha256("e" * 64)
    original = "\n".join(texts)
    units, wires, start = [], [], 0
    for index, text in enumerate(texts):
        block = 0 if same_block else index
        box = [90, 100 + 20 * block, 550, 112 + 20 * block]
        layout = {"bbox": box, "page_width": 600, "page_height": 800,
                  "coordinate_frame": "dict", "rotation": 0, "column": 0}
        fonts = [{"char_start": 0, "char_end": len(text), "font_size": 12,
                  "font_weight": "regular", "coordinate_frame": "dict",
                  "source": "pdf_native_single_textpage", "char_alignment": "exact"}]
        metadata = {"pdf_block": block, "block_sha256": sha256(original.encode()).hexdigest(),
                    "block_char_start": start if same_block else 0,
                    "block_char_end": (start if same_block else 0) + len(text),
                    "reading_layout": {"layout": layout, "upstream_hints": {"font_runs": fonts}}}
        unit = _make_unit(source_id=source, parser_version="1.0.0",
                          coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
                          raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
                          language=language, metadata=metadata)
        units.append(unit)
        wires.append({"unit_id": unit.unit_id, "ordinal": index, "page": 1, "text": text,
                      "kind": "heading" if heading and index == 0 else "paragraph",
                      "role": "company_filing", "language": language, "layout": layout,
                      "hints": {"source_id": source, "font_runs": fonts}})
        start += len(text) + 1
    ids = [unit.unit_id for unit in units]
    body = ids[1:] if heading else ids
    pipeline = {"observation": {"units": wires},
                "reading_plan": {"unit_profiles": {uid: {"reading_profile_key": "root",
                                                         "section_role": "business", "priority": 2}
                                                   for uid in ids}},
                "structure": {"sections": [{"section_id": "business", "parent_id": None,
                                              "heading_unit_ids": ids[:1] if heading else [],
                                              "body_unit_ids": body}]},
                "packages": {"packages": [{"package_id": "body", "kind": "background",
                                             "member_unit_ids": body, "anchor_unit_ids": body[:1],
                                             "required_context_unit_ids": body[:1]}]}}
    return DocumentStructure(source, "e" * 64, language, tuple(units), page_count=1,
                             pages_read=1, mime_type="application/pdf"), pipeline


def select(parsed, candidates, metadata, *, limit=96):
    return finalize_selection(parsed, DocumentRoute("semi_annual_report", limit, False), candidates,
                              group_ids={}, heading_pattern=reading._NEVER_HEADING,
                              dropped_financial_count=0, budget_policy=reading.READING_BUDGET_POLICY,
                              reading_metadata=metadata, max_chars=48000)


@pytest.mark.parametrize("language,texts", [
    ("zh", ["公司已交付专用设备至客户开展生产验证。", "公司新增制造基地已经投入运行。"]),
    ("en", ["Our company delivered equipment to customers for production qualification.",
            "Our company opened a new manufacturing facility for customers."]),
])
def test_independent_complete_statements_are_not_one_atomic_business_claim(language, texts):
    parsed, pipeline = fixture(texts, language=language)
    before = deepcopy(pipeline)
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    ids = [unit.unit_id for unit in parsed.units]
    assert complete and not withheld
    assert [package["member_unit_ids"] for package in packages] == [[uid] for uid in ids]
    assert all(not metadata[uid]["context_only"] for uid in ids)
    assert all(metadata[uid]["required"] == () for uid in ids)
    assert len(select(parsed, candidates, metadata, limit=1).evidence_spans) == 1
    assert pipeline == before
    assert [unit.raw_text for unit in parsed.units] == texts


@pytest.mark.parametrize("qualifier", [
    "但公司尚未完成产线认证，不代表已经形成批量销售。",
    "该设备仍需完成认证，预计明年进入量产。",
    "报告期内样机继续验证，并获得重复订单。",
    "下半年将根据客户反馈安排开发，预计随后进行认证。",
])
def test_sentence_terminator_does_not_drop_reference_negation_or_forward_condition(qualifier):
    parsed, pipeline = fixture(["公司已交付设备样机至客户开展生产验证。", qualifier])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    ids = {unit.unit_id for unit in parsed.units}
    assert complete and not withheld and len(packages) == 1
    assert set(packages[0]["member_unit_ids"]) == ids
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    full = select(parsed, candidates, metadata, limit=2)
    assert [span.raw_text for span in full.evidence_spans] == [unit.raw_text for unit in parsed.units]


@pytest.mark.parametrize("qualification", [
    "公司尚未完成产线认证，不代表已经形成批量销售。",
    "公司计划在下一期开展客户认证，量产仍取决于认证结果。",
])
def test_preceding_qualification_cannot_be_detached_from_later_positive_statement(qualification):
    parsed, pipeline = fixture([qualification, "公司已交付专用设备至客户开展生产验证。"])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(packages) == 1
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    assert len(select(parsed, candidates, metadata, limit=2).evidence_spans) == 2


@pytest.mark.parametrize("order", [("table", "description"), ("description", "table")])
def test_weaker_package_does_not_overwrite_source_owned_table_fact_value(order):
    parsed, pipeline = fixture(["Device A | 15", "Product shipments | 2026 | thousand units"], same_block=False,
                               language="en")
    uid, header = [unit.unit_id for unit in parsed.units]
    packages = {
        "table": {"package_id": "operating-row", "kind": "operating_table",
                  "member_unit_ids": [uid, header], "anchor_unit_ids": [uid],
                  "required_context_unit_ids": [header]},
        "description": {"package_id": "description", "kind": "project",
                        "member_unit_ids": [uid], "anchor_unit_ids": [uid],
                        "required_context_unit_ids": []},
    }
    pipeline["packages"]["packages"] = [packages[key] for key in order]
    candidates, metadata, _packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    assert metadata[uid]["value_band"] == "meaningful_fact"
    assert metadata[uid]["topics"] == (), "a weaker section description cannot claim factual novelty"
    assert not metadata[uid]["context_only"]
    assert metadata[uid]["required"] == (header,)
    full = select(parsed, candidates, metadata, limit=2)
    assert len(full.evidence_spans) == 2
    assert len({span.span_id for span in full.evidence_spans}) == 2


def test_real_wrapped_statement_is_still_complete_and_costs_every_original_fragment():
    parsed, pipeline = fixture(["报告期内，公司将开展客户生产验", "证，并保留未完成认证的条件。"])
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(packages) == 1
    assert not select(parsed, candidates, metadata, limit=1).evidence_spans
    full = select(parsed, candidates, metadata, limit=2)
    assert [span.raw_text for span in full.evidence_spans] == [unit.raw_text for unit in parsed.units]
    assert [span.coordinates for span in full.evidence_spans] == [unit.coordinates for unit in parsed.units]
    assert reading.READING_BUDGET_POLICY == "reading_plan/3"
    assert reading.MAX_READING_CHARS == 48000


@pytest.mark.parametrize("language,texts,expected", [
    ("mixed", ["公司产品将通", "过合作研", "发提高效率。"], "公司产品将通过合作研发提高效率。"),
    ("mixed", ["公司已交付设备。", "但尚未完成验", "证，预计明年量产。"],
        "公司已交付设备。但尚未完成验证，预计明年量产。"),
    ("zh", ["Our company introduced owner", "ship services for customers."],
        "Our company introduced owner ship services for customers."),
    ("mixed", ["Our company introduced cloud", "services for customers."],
        "Our company introduced cloud services for customers."),
    ("zh", ["公司已交付产能为12", "3万件的设备，额定电压12", "V，仍需客户认证。"],
        "公司已交付产能为12 3万件的设备，额定电压12 V，仍需客户认证。"),
])
def test_linguistic_boundary_depends_on_actual_characters_not_declared_language(language, texts, expected):
    parsed, pipeline = fixture(texts, language=language)
    before = tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units)
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert expected in seen
    assert len(packages) == 1 and packages[0]["kind"] == "native_continuity"
    assert packages[0]["member_unit_ids"] == [unit.unit_id for unit in parsed.units]
    assert tuple(unit.to_evidence_span(topics=(), selection_reasons=()) for unit in parsed.units) == before


def test_wrong_zh_label_cannot_create_eligible_english_product_word():
    texts = ["Our company launched prod", "ucts."]
    parsed, pipeline = fixture(texts, language="zh")
    assert reading.detect_reading_business_fact("Our company launched products.").eligible
    assert not reading.detect_reading_business_fact("Our company launched prod ucts.").eligible
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(
        parsed, pipeline, reading.detect_reading_business_fact)
    assert all(package["kind"] != "native_continuity" for package in packages)
    assert [unit.raw_text for unit in parsed.units] == texts


def test_statement_split_and_window_fact_share_the_same_cjk_boundary_rule():
    texts = ["公司已交付专用设备至客户开展生产验", "证。",
             "公司新增制造基地已经投入运", "行。"]
    parsed, pipeline = fixture(texts, language="mixed")
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert [package["member_unit_ids"] for package in packages] == [
        [unit.unit_id for unit in parsed.units[:2]], [unit.unit_id for unit in parsed.units[2:]]]
    assert "公司已交付专用设备至客户开展生产验证。" in seen
    assert "公司新增制造基地已经投入运行。" in seen
    assert not any("验 证" in text or "运 行" in text for text in seen)


def test_different_native_sources_never_share_a_linguistic_view_even_with_two_language_labels():
    parsed, pipeline = fixture(["公司产品将通", "过合作研发提高效率。"], language="mixed")
    last = parsed.units[-1]
    source = source_id_for_sha256("f" * 64)
    changed = _make_unit(source_id=source, parser_version=last.parser_version,
        coordinates=last.coordinates, raw_text=last.raw_text, unit_kind=last.unit_kind,
        source_role=last.source_role, language="zh", metadata=last.metadata)
    parsed = replace(parsed, units=(parsed.units[0], changed))
    old = last.unit_id
    pipeline["observation"]["units"][-1].update(unit_id=changed.unit_id, language="zh")
    pipeline["observation"]["units"][-1]["hints"]["source_id"] = source
    profiles = pipeline["reading_plan"]["unit_profiles"]
    profiles[changed.unit_id] = profiles.pop(old)
    pipeline["structure"]["sections"][0]["body_unit_ids"][-1] = changed.unit_id
    pipeline["packages"]["packages"][0]["member_unit_ids"][-1] = changed.unit_id
    seen = []
    def classify(text):
        seen.append(text)
        return reading.detect_reading_business_fact(text)
    packages, _facts, _continuity, _blocked = reading._prose_reading_packages(parsed, pipeline, classify)
    assert "公司产品将通过合作研发提高效率。" not in seen
    assert all(package["kind"] != "native_continuity" for package in packages)
