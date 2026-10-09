"""Focused selector responsibilities; synthetic OCR port is not a provider receipt."""

from dataclasses import replace
import hashlib
import pytest
from company_wiki.source_catalog import narrative_evidence as selector
from company_wiki.source_catalog.narrative_candidates import assess_unit
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.n6_candidate_completion import linkable
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "c" * 64
SID = source_id_for_sha256(SHA)


def unit(text, index=0, *, metadata=None, **changes):
    base = {
        "slide_number": 7,
        "slide_id": "262",
        "shape_path": [0],
        "media_sha256": "d" * 64,
        "ocr_fingerprint": "e" * 64,
        "coordinate_space": "image_pixels",
        "image_width": 2800,
        "image_height": 1600,
        "ocr_line_index": index,
        "ocr_confidence": 0.99,
        "ocr_box": [95, 804 + 44 * index, 2380, 844 + 44 * index],
    }
    base.update(metadata or {})
    value = selector._make_unit(
        source_id=SID,
        parser_version="2.0.0",
        coordinates=EvidenceCoordinates(page_number=7, paragraph_index=index),
        raw_text=text,
        unit_kind="pptx_image_ocr_line",
        source_role="company_filing",
        language="en",
        metadata=base,
    )
    return replace(value, **changes)


def package(units):
    structure = DocumentStructure(
        SID,
        SHA,
        "en",
        tuple(units),
        page_count=22,
        pages_read=22,
        opaque_pages=tuple(range(1, 23)),
    )
    return selector.select_narrative_evidence(
        structure,
        title="Business definitions update",
        existing_kind="investor_relations",
    )


@pytest.mark.parametrize(
    "text,reason",
    [
        (
            "We will transition to two reporting segments for FY27.",
            "reporting_definition_change",
        ),
        (
            "Our Devices segment will include Windows, games and advertising businesses.",
            "business_scope_change",
        ),
        (
            "Commercial cloud now includes developer and security offerings previously reported in another segment.",
            "business_scope_change",
        ),
        (
            "Server products now excludes on-premises developer services which have moved to Commercial products.",
            "business_scope_change",
        ),
        (
            "Consumer products has been renamed from Office consumer products, but is otherwise unchanged.",
            "reporting_rename",
        ),
        (
            "Frontier and support services was previously reported as Enterprise and Partner services, but is otherwise unchanged",
            "reporting_rename",
        ),
        (
            "Marketing solutions and Premium subscriptions will now be reported in the Search and advertising revenue growth metric.",
            "reporting_definition_change",
        ),
        (
            "We are updating our product and services reporting definitions to better represent the businesses as we manage them today.",
            "reporting_definition_change",
        ),
        (
            "The customer growth metric will now exclude trial users previously included in subscribers.",
            "business_scope_change",
        ),
        (
            "公司将把云服务业务从软件分部调整至智能基础设施分部。",
            "business_scope_change",
        ),
        ("消费产品现更名为家庭产品，其业务范围保持不变。", "reporting_rename"),
        (
            "活跃用户指标的定义为付费及试用用户，本期口径调整为仅包含付费用户。",
            "reporting_definition_change",
        ),
    ],
)
def test_concrete_scope_changes_are_candidates_without_growth_claim(text, reason):
    value = unit(text, language="zh" if any("一" <= c <= "鿿" for c in text) else "en")
    hit = assess_unit(value, selector._candidate_rules()).candidate
    assert hit is not None
    assert reason in hit.reasons
    assert "quantified_operating_status" not in hit.reasons
    assert hit.unit.raw_text == text
    if "otherwise unchanged" in text or "保持不变" in text:
        assert "scope_unchanged" in hit.reasons


@pytest.mark.parametrize(
    "text",
    [
        "FY27 Segment changes and resulting new product and service reporting updates",
        "Agents and Infrastructure",
        "Cloud revenue growth metric",
        "Revenue 100 200 300",
        "Revenue grew by 20% to $100 million.",
        "The business is otherwise unchanged.",
        "Segment means a component of an entity.",
        "生产方式是指订单式生产。",
        "We updated our financial statements to comply with accounting standards.",
        "The interest expense metric now includes 12 million dollars.",
        "Cloud revenue is now 100 million dollars.",
        "Product reporting definitions",
    ],
)
def test_titles_numbers_static_definitions_and_financial_accounting_stay_empty(text):
    assert not package([unit(text)]).evidence_spans


def test_split_existing_milestone_uses_pixel_groups_and_original_spans():
    values = [unit("We launched", 0), unit("a new product for overseas customers.", 1)]
    result = package(values)
    assert len(result.evidence_spans) == 2
    assert result.status == "partial" and not result.coverage_complete
    for span, original in zip(result.evidence_spans, values, strict=True):
        assert span.raw_text == original.raw_text
        assert span.coordinates == original.coordinates
        assert tuple(span.structured_value["ocr_box"]) == tuple(
            original.metadata["ocr_box"]
        )
        assert span.structured_value["coordinate_space"] == "image_pixels"
        assert "bbox" not in span.structured_value
        assert (
            span.structured_value["text_sha256"]
            == hashlib.sha256(original.raw_text.encode()).hexdigest()
        )
    assert (
        len({s.structured_value["selection_group_id"] for s in result.evidence_spans})
        == 1
    )


def test_definition_fragment_completion_retains_future_and_unchanged():
    values = [
        unit("Our consumer products will be renamed from", 0),
        unit("Office consumer products, but are otherwise unchanged.", 1),
    ]
    result = package(values)
    assert len(result.evidence_spans) == 2
    assert "will be" in result.evidence_spans[0].raw_text
    assert "otherwise unchanged" in result.evidence_spans[1].raw_text
    assert any(
        "reporting_rename" in s.structured_value["selection_reasons"]
        for s in result.evidence_spans
    )


@pytest.mark.parametrize(
    "metadata,changes",
    [
        ({"media_sha256": "a" * 64}, {}),
        ({"shape_path": [1]}, {}),
        ({"ocr_fingerprint": "b" * 64}, {}),
        ({"coordinate_space": "page_points"}, {}),
        ({"ocr_line_index": 2}, {}),
        ({"ocr_box": [1800, 848, 2790, 888]}, {}),
        ({"ocr_box": [95, 1000, 2380, 1040]}, {}),
        ({"ocr_confidence": 0.5}, {"quality_flags": ("low_ocr_confidence",)}),
        ({}, {"coordinates": EvidenceCoordinates(page_number=8, paragraph_index=1)}),
        ({}, {"language": "zh"}),
        ({}, {"source_role": "management"}),
        ({}, {"parser_version": "2.0.1"}),
    ],
)
def test_ocr_join_cannot_cross_identity_columns_missing_or_unreliable_lines(
    metadata, changes
):
    left = unit("We launched", 0)
    right = unit(
        "a new product for overseas customers.", 1, metadata=metadata, **changes
    )
    assert not linkable(left, right)
    groups = selector._pdf_context_groups([left, right])
    assert all(len(members) == 1 for _, members, _ in groups)
    assert not package([left, right]).evidence_spans


def test_ocr_groups_are_bounded_and_sentence_barriers_stop_context():
    many = [
        unit(
            "continuing detailed operating context " * 3,
            i,
            metadata={"ocr_box": [95, 50 + 44 * i, 2380, 90 + 44 * i]},
        )
        for i in range(9)
    ]
    groups = selector._pdf_context_groups(many)
    assert sum(len(members) for _, members, _ in groups) == 9
    assert max(len(members) for _, members, _ in groups) == 8
    values = [
        unit("Unrelated historical context.", 0),
        unit("We launched", 1),
        unit("a new product for overseas customers.", 2),
    ]
    result = package(values)
    assert [s.raw_text for s in result.evidence_spans] == [
        v.raw_text for v in values[1:]
    ]


def test_no_low_confidence_standalone_candidate_or_empty_complete_success():
    bad = unit(
        "Our segment now includes cloud services.",
        quality_flags=("low_ocr_confidence",),
    )
    assert not package([bad]).evidence_spans
    empty = package([unit("Revenue 100 200 300")])
    assert empty.status == "needs_review" and not empty.coverage_complete


def test_selector_version_upgrades_generation_identity(monkeypatch):
    from unit.test_narrative_batch import _request, Reader, _module
    from company_wiki.automation.narrative_generation import generation_manifest
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation import narrative_batch_request
    import json

    request = _request()
    batch = _module()
    event = batch.build_batch_events(
        request, Reader(), now="2026-10-09T00:00:00Z"
    ).events[0]
    payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
    manifest = generation_manifest(
        request, payload, execution_versions=batch._execution_versions(request)
    )
    current_version = selector.NARRATIVE_SELECTOR_VERSION
    assert manifest["execution_versions"]["selector"] == current_version
    from company_wiki.automation.narrative_generation import generation_sha256

    old = {
        **manifest,
        "execution_versions": {**manifest["execution_versions"], "selector": "0.4.2"},
    }
    assert generation_sha256(old) != generation_sha256(manifest)

    # Test version propagation and invalidation, independent of release numbers.
    intent_sha = request.request_sha256
    input_hash = request.input_hash
    next_version = f"{current_version}-contract-next"
    monkeypatch.setattr(narrative_batch_request, "NARRATIVE_SELECTOR_VERSION", next_version)
    next_event = batch.build_batch_events(
        request, Reader(), now="2026-10-09T00:00:00Z"
    ).events[0]
    next_payload = SourceRevisionEventPayload.from_dict(json.loads(next_event.payload_json))
    next_manifest = generation_manifest(
        request, next_payload, execution_versions=batch._execution_versions(request)
    )
    assert next_manifest["execution_versions"]["selector"] == next_version
    assert request.request_sha256 == intent_sha
    assert request.input_hash != input_hash
    assert generation_sha256(next_manifest) != generation_sha256(manifest)
    assert manifest["execution_versions"]["selector"] == current_version


def test_real_normalization_interface_with_explicit_synthetic_split_ocr_port(tmp_path):
    from unit.test_narrative_ocr_composition import (
        fixture_deck,
        config,
        FakeOCR,
        normalize,
    )
    from company_wiki import document_normalization as dn
    from company_wiki.source_catalog.narrative_normalization import (
        NarrativeNormalization,
    )

    class SplitOCR(FakeOCR):
        def transcribe(self, data, *, limits):
            limits.check_deadline()
            self.calls += 1
            return dn.ImageOCRResult(
                1,
                1,
                (
                    dn.OCRLine("We launched", (0.1, 0.1, 0.9, 0.4), 0.99),
                    dn.OCRLine(
                        "a new product for overseas customers.",
                        (0.1, 0.45, 0.9, 0.8),
                        0.99,
                    ),
                ),
            )

    port = NarrativeNormalization(
        dn.LocalOCRConfig.from_dict(config(tmp_path / "models")),
        adapter_factory=SplitOCR,
    )
    data = fixture_deck(with_picture_only_slide=True)
    document = normalize(port, data)
    structure = port.language_structure(document, "en")
    result = selector.select_narrative_evidence(
        structure, title="Product update", existing_kind="investor_relations"
    )
    spans = tuple(
        s
        for s in result.evidence_spans
        if s.structured_value["unit_kind"] == "pptx_image_ocr_line"
    )
    assert len(spans) == 2
    assert all(s.structured_value["coordinate_space"] == "image_pixels" for s in spans)
    assert result.status == "partial" and not result.coverage_complete
    assert (
        port.replay(
            data,
            source_id=document.source_id,
            source_sha256=document.source_sha256,
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            evidence_spans=spans,
            language="en",
        )
        == 2
    )
    # Pure writer check on synthetic evidence never replaces a live receipt.
    import importlib.util
    import json
    from pathlib import Path

    helper_path = (
        Path(__file__).resolve().parents[2]
        / "docs/implementation/main-ocr-selection/sample_page7.py"
    )
    spec = importlib.util.spec_from_file_location("sample_receipt_writer", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    report = json.loads(json.dumps(helper.selection_receipt(result)))
    assert report["selected_count"] == len(result.evidence_spans)
    assert report["omitted_count"] == result.omitted_candidate_count
    assert (
        port.ocr_adapter.calls == 2
    )  # synthetic port only, never local engine/provider


def test_ocr_neighbor_uses_same_carrier_and_bounded_context():
    import re
    from company_wiki.source_catalog.narrative_neighbors import (
        NeighborRules,
        enrich_neighbor_context,
    )
    from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate

    prefix = unit("Named product serves enterprise customers", 0)
    event = unit("We launched a new product.", 1)
    rules = NeighborRules(
        topics=lambda t: ("core_business",) if t.startswith("Named") else (),
        high_value_event=re.compile("launched"),
    )
    candidate = EvidenceCandidate(
        event, ("products_rd",), ("specific_business_event",), 3
    )
    result = enrich_neighbor_context(
        [prefix, event],
        initial_candidates=[candidate],
        initial_group_ids={},
        rules=rules,
    )
    assert {c.unit.unit_id for c in result.candidates} == {
        prefix.unit_id,
        event.unit_id,
    }
    different = replace(prefix, metadata={**prefix.metadata, "media_sha256": "f" * 64})
    result = enrich_neighbor_context(
        [different, event],
        initial_candidates=[candidate],
        initial_group_ids={},
        rules=rules,
    )
    assert len(result.candidates) == 1
