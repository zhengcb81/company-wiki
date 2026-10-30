"""Cell subranges are source coordinates, not blanket unstable locators."""
from dataclasses import replace
import hashlib

import pytest

from company_wiki.source_catalog import narrative_evidence as n
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeEvidencePackage
from company_wiki.source_catalog.narrative_replay import verify_replayed_pdf_spans
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256

CELL = '  7：新产线项目计划怎样？\n答：新产线尚未投产。预计明年启动。\n8：境外项目怎样？\n答：预计明年启动。  '


def emitted(text=CELL, *, version=None, page=1):
    digest = hashlib.sha256(text.encode()).hexdigest()
    state = n._PdfParseState(source_id_for_sha256(digest), digest,
                             version or n.NARRATIVE_PARSER_VERSION, 'zh')
    n._emit_pdf_row(state, page, 0, 0, ('问答记录', text), ('项目', '内容'), (40, 80, 520, 700))
    return tuple(u for u in state.units if u.unit_kind == 'pdf_table_qa_fragment')


def test_current_fragments_have_exact_distinct_cell_character_locators():
    units = emitted()
    assert len(units) == 5
    assert len({u.coordinates.locator() for u in units}) == len(units)
    for unit in units:
        a, b = unit.coordinates.char_start, unit.coordinates.char_end
        assert (a, b) == (unit.metadata['cell_fragment_start'], unit.metadata['cell_fragment_end'])
        assert CELL[a:b] == unit.raw_text
        assert unit.metadata['cell_fragment_sha256'] == unit.text_sha256
        assert 'locator_unstable' not in unit.quality_flags


def test_current_proven_fragments_pass_unchanged_production_material_boundary():
    from company_wiki.automation.narrative_select import NarrativeSelectHandler

    units = emitted()
    spans = tuple(u.to_evidence_span(topics=(), selection_reasons=()) for u in units)
    digest = hashlib.sha256(CELL.encode()).hexdigest()
    parsed = DocumentStructure(source_id_for_sha256(digest), digest, 'zh', units,
                               page_count=1, pages_read=1, mime_type='application/pdf')
    package = NarrativeEvidencePackage(parsed.source_id, digest, 'investor_relations',
                                       'selected', spans, 96, len(spans), 0, len(units), 0, True)
    NarrativeSelectHandler._verify_selected_material(parsed, package)


@pytest.mark.parametrize('text', ['问：新产品怎样？答：Cafe\u0301客户验证。',
                                  '问：新产品怎样？答：客户验证\r\n尚未完成。'])
def test_noncanonical_cell_slice_does_not_claim_stable_character_coordinates(text):
    units = emitted(text)
    changed = [u for u in units if '客户验证' in u.raw_text]
    assert changed
    assert all(u.coordinates.char_start is None and 'locator_unstable' in u.quality_flags
               for u in changed)


@pytest.mark.parametrize('field,value', [('cell_fragment_start', 1), ('cell_fragment_end', 2),
    ('cell_sha256', 'f'*64), ('cell_fragment_sha256', 'f'*64), ('qa_group_id', 'other'),
    ('qa_question_number', '99'), ('qa_state', 'unanswered'), ('source_role', 'investor_question')])
def test_current_replay_rejects_metadata_tampering(field, value):
    unit = next(u for u in emitted() if '尚未' in u.raw_text)
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    changed = EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=span.raw_text, structured_value={**dict(span.structured_value), field:value},
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags)
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((), (changed.span_id,))


def test_current_replay_rejects_character_locator_tampering():
    unit = emitted()[1]
    assert unit.coordinates.char_start is not None
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    coords = replace(span.coordinates, char_start=span.coordinates.char_start+1)
    changed = EvidenceSpan.create(source_id=span.source_id, coordinates=coords,
        raw_text=span.raw_text, structured_value=span.structured_value,
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags)
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((), (changed.span_id,))


@pytest.mark.parametrize('flag', ['locator_unstable', 'low_ocr_confidence'])
def test_replay_cannot_remove_the_native_producers_quality_flags(flag):
    from company_wiki.automation.narrative_select import NarrativeSelectHandler, _SelectFailure

    unit = replace(emitted()[1], quality_flags=(flag,))
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    changed = EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=span.raw_text, structured_value=span.structured_value,
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=())
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((), (changed.span_id,))
    digest = hashlib.sha256(CELL.encode()).hexdigest()
    parsed = DocumentStructure(unit.source_id, digest, 'zh', (unit,),page_count=1,pages_read=1)
    package = NarrativeEvidencePackage(unit.source_id, digest, 'investor_relations',
                                       'selected', (changed,), 96, 1, 0, 1, 0, True)
    with pytest.raises(_SelectFailure):
        NarrativeSelectHandler._verify_selected_material(parsed,package,mime_type='application/pdf')


def test_replay_allows_additional_conservative_quality_diagnostics():
    unit = emitted()[1]
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    changed = replace(span, quality_flags=('locator_unstable',))
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((changed.span_id,), ())


@pytest.mark.parametrize('version', ['0.1.0', '0.1.1'])
def test_legacy_fragment_coordinates_and_flags_remain_explicit(version):
    units = emitted('问：新产线项目计划怎样？答：尚未投产。', version=version)
    assert units
    assert all(u.coordinates.char_start is None and u.coordinates.char_end is None for u in units)
    assert all(u.quality_flags == ('locator_unstable',) for u in units)
    spans = tuple(u.to_evidence_span(topics=(), selection_reasons=()) for u in units)
    assert verify_replayed_pdf_spans(spans, units) == (tuple(s.span_id for s in spans), ())


def test_current_cross_page_answer_sentences_keep_the_same_question():
    question = emitted('7：新产线项目计划怎样？', page=1)
    answers = emitted('答：新产线尚未投产。预计明年启动。', page=2)
    # Same source identity, as in actual page traversal.
    answers = tuple(replace(u, source_id=question[0].source_id) for u in answers)
    linked = n._link_cross_page_qa((*question, *answers))
    assert len(linked) == 3
    assert len({u.metadata['qa_group_id'] for u in linked}) == 1
    assert all(u.metadata['qa_question_number'] == '7' for u in linked)


@pytest.mark.parametrize('base,range_version', [('0.1.1','0.1.0'), ('0.1.2','0.1.1')])
def test_native_ranges_pin_their_actual_base_parser_for_replay(base, range_version):
    from unit.test_narrative_native_ranges import members
    from company_wiki.source_catalog.narrative_native_ranges import native_range_unit
    from company_wiki.source_catalog.narrative_replay import _parser_version

    units, _ = members()
    units = tuple(n._make_unit(source_id=u.source_id, parser_version=base,
        coordinates=u.coordinates, raw_text=u.raw_text, unit_kind=u.unit_kind,
        source_role=u.source_role, language=u.language, metadata=u.metadata) for u in units)
    merged = native_range_unit(units)
    assert merged is not None
    assert merged.parser_version == range_version
    span = merged.to_evidence_span(topics=(), selection_reasons=())
    assert _parser_version((span,), n.NARRATIVE_PARSER_VERSION) == base
    assert verify_replayed_pdf_spans((span,), units) == ((span.span_id,), ())
    bad = {**dict(span.structured_value), 'native_range': {
        **dict(span.structured_value['native_range']), 'base_parser_version':'9.9.9'}}
    forged = EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=span.raw_text, structured_value=bad,
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags)
    with pytest.raises(ValueError, match='version'):
        _parser_version((forged,), n.NARRATIVE_PARSER_VERSION)
