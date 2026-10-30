"""Neutral offline review probes; no real PDF, SDK, transport or catalog IO."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import types
from dataclasses import replace

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['COMPANY_WIKI_NETWORK'] = 'blocked'
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
import pytest
from company_wiki.source_catalog import narrative_evidence as n
from company_wiki.source_catalog import narrative_native_ranges as ranges
from company_wiki.source_catalog.narrative_replay import _parser_version, verify_replayed_pdf_spans
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256

BASELINE = 'f88221d2578eac078bb7b30d9a8c00b08f2ee6d2'
SID = source_id_for_sha256('a' * 64)
CELL = '7：新产线怎样？\n答：产线尚未投产。预计明年启动。\n8：另一产线怎样？\n答：预计明年启动。'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('independent review forbids network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def legacy(module):
    relative = 'src/company_wiki/source_catalog/' + module + '.py'
    raw = subprocess.run(['git', 'show', BASELINE + ':' + relative], cwd=ROOT,
                         capture_output=True, check=True).stdout.decode('utf-8')
    name = 'company_wiki.source_catalog._independent_old_' + module
    loaded = types.ModuleType(name)
    loaded.__package__ = 'company_wiki.source_catalog'
    sys.modules[name] = loaded
    exec(compile(raw, relative + '@baseline', 'exec'), loaded.__dict__)
    return loaded


def emit(version='0.1.2', text=CELL, page=1, row=0, engine=n):
    state = engine._PdfParseState(SID, 'a' * 64, version, 'zh')
    engine._emit_pdf_row(state, page, 0, row, ('问答', text), ('项目', '内容'), (0, 0, 100, 100))
    return tuple(state.units)


def span(u):
    return u.to_evidence_span(topics=(), selection_reasons=())


def change(s, **changes):
    data = dict(source_id=s.source_id, coordinates=s.coordinates, raw_text=s.raw_text,
                structured_value=s.structured_value, parser_name=s.parser_name,
                parser_version=s.parser_version, parse_status=s.parse_status,
                quality_flags=s.quality_flags)
    data.update(changes)
    return EvidenceSpan.create(**data)


@pytest.mark.parametrize('version', ['0.1.0', '0.1.1'])
@pytest.mark.parametrize('text', [CELL, '问：投产了吗？答：尚未投产。', '答：Cafe\u0301设备\r\n尚未完成验证。'])
def test_old_qa_evidence_bytes_identical_to_git_baseline(version, text):
    old = legacy('narrative_evidence')
    before = old._link_cross_page_qa(emit(version, text=text, engine=old))
    after = n._link_cross_page_qa(emit(version, text=text))
    image = lambda units: json.dumps([{
        'unit_id': u.unit_id, 'source_id': u.source_id, 'parser_name': u.parser_name,
        'parser_version': u.parser_version, 'coordinates': u.coordinates.to_dict(),
        'raw_text': u.raw_text, 'unit_kind': u.unit_kind, 'source_role': u.source_role,
        'language': u.language, 'quality_flags': u.quality_flags, 'metadata': dict(u.metadata),
    } for u in units], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    assert image(before) == image(after)
    assert [u.unit_id for u in before] == [u.unit_id for u in after]


@pytest.mark.parametrize('version', ['0.1.1', '0.1.2'])
def test_trusted_unstable_unit_cannot_be_upgraded_by_clearing_span_flag(version):
    unit = emit(version)[1]
    unit = replace(unit, quality_flags=('locator_unstable',))
    forged = change(span(unit), quality_flags=())
    assert verify_replayed_pdf_spans((forged,), (unit,)) == ((), (forged.span_id,))


@pytest.mark.parametrize('source_flags,span_flags,valid', [
    ((), ('locator_unstable',), True),
    (('locator_unstable',), ('locator_unstable', 'low_ocr_confidence'), True),
    (('locator_unstable', 'low_ocr_confidence'), ('low_ocr_confidence', 'locator_unstable'), True),
    (('locator_unstable', 'low_ocr_confidence'), ('locator_unstable',), False),
    (('locator_unstable',), ('low_ocr_confidence',), False),
])
def test_conservative_quality_additions_preserve_all_source_restrictions(source_flags, span_flags, valid):
    unit = replace(emit()[1], quality_flags=source_flags)
    evidence = change(span(unit), quality_flags=span_flags)
    expected = ((evidence.span_id,), ()) if valid else ((), (evidence.span_id,))
    assert verify_replayed_pdf_spans((evidence,), (unit,)) == expected


@pytest.mark.parametrize('flag', ['locator_unstable', 'low_ocr_confidence'])
def test_production_material_guard_and_replay_both_reject_quality_forgery(flag):
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeEvidencePackage
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, NativePdfBackend
    base = emit()[1]
    unit = replace(base, quality_flags=(flag,))
    parsed = DocumentStructure(SID, 'a'*64, 'zh', (unit,), page_count=1, pages_read=1,
                               mime_type='application/pdf')
    for evidence in (span(unit), change(span(unit), quality_flags=())):
        package = NarrativeEvidencePackage(SID, 'a'*64, 'investor_relations', 'selected',
            (evidence,), 96, 1, 0, 1, 0, True)
        with pytest.raises(Exception) as error:
            NarrativeSelectHandler._verify_selected_material(parsed, package,
                pdf_reading=PdfReading(backend=NativePdfBackend()))
        assert 'PARSER_INCOMPLETE' in str(error.value)


@pytest.mark.parametrize('text', ['问：验证怎样？答：Cafe\u0301客户验证。',
                                  '问：验证怎样？答：客户\r\n尚未验证。'])
def test_noncanonical_fragment_retains_quality_failure(text):
    answers = [u for u in emit(text=text) if u.source_role == 'management']
    assert answers and all(u.coordinates.char_start is None for u in answers)
    assert all('locator_unstable' in u.quality_flags for u in answers)


@pytest.mark.parametrize('field,value', [('cell_fragment_start', 0), ('cell_fragment_end', 1),
    ('cell_fragment_sha256', 'f'*64), ('cell_sha256', 'f'*64), ('qa_group_id', 'other'),
    ('qa_question_number', '9'), ('qa_state', 'other')])
def test_new_metadata_and_coordinate_tampering_fails(field, value):
    unit = emit()[1]
    original = span(unit)
    forged = change(original, structured_value={**dict(original.structured_value), field: value})
    assert verify_replayed_pdf_spans((forged,), (unit,)) == ((), (forged.span_id,))
    coord = replace(original.coordinates, char_start=original.coordinates.char_start + 1)
    forged = change(original, coordinates=coord)
    assert verify_replayed_pdf_spans((forged,), (unit,)) == ((), (forged.span_id,))


@pytest.mark.parametrize('version', ['0.1.1', '0.1.2'])
def test_cross_page_sentences_link_without_next_cell_leak(version):
    question = emit(version, '7：新产线怎样？', 1, 3)
    answers = emit(version, '答：尚未投产。预计明年启动。', 2)
    next_cell = emit(version, '答：公司产品已通过客户验证。', 2, 1)
    linked = n._link_cross_page_qa((*question, *answers, *next_cell))
    assert len({u.metadata['qa_group_id'] for u in linked[:-1]}) == 1
    assert all(u.metadata['qa_question_number'] == '7' for u in linked[:-1])
    assert linked[-1].metadata['qa_group_id'] is None
    if version == '0.1.2':
        assert len({u.coordinates.locator() for u in linked}) == len(linked)


def members(base='0.1.1', engine=n):
    texts = ['客户生产验', '证尚未完成。']
    view = ranges.build_native_page_view([(i, (0, i*20, 100, i*20+10), t)
                                           for i, t in enumerate(texts)])
    result = []
    for i, text in enumerate(texts):
        result.append(engine._make_unit(source_id=SID, parser_version=base,
            coordinates=EvidenceCoordinates(page_number=2, paragraph_index=i),
            raw_text=text, unit_kind='pdf_text_block', source_role='company_filing',
            language='zh', metadata={'pdf_block': i,
                'block_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'block_char_start': 0, 'block_char_end': len(text), 'native_source_view': view}))
    return result


def test_native_range_old_bytes_and_new_identity_and_binding():
    old = legacy('narrative_native_ranges')
    originals = members()
    before, after = old.native_range_unit(originals), ranges.native_range_unit(originals)
    assert before.unit_id == after.unit_id and span(before).to_dict() == span(after).to_dict()
    current = members('0.1.2')
    newer = ranges.native_range_unit(current)
    assert newer.unit_id != after.unit_id and newer.parser_version == '0.1.1'
    assert _parser_version((span(newer),), 'unknown') == '0.1.2'
    assert verify_replayed_pdf_spans((span(newer),), current) == ((span(newer).span_id,), ())
    assert ranges.native_range_unit([current[0], originals[1]]) is None
    with pytest.raises(ValueError, match='one parser version'):
        _parser_version((span(newer), span(originals[0])), 'unknown')
    for changed_version in ['0.1.0', '9.9.9']:
        forged = change(span(newer), parser_version=changed_version)
        assert verify_replayed_pdf_spans((forged,), current) == ((), (forged.span_id,))
    badbinding = {**dict(span(newer).structured_value), 'native_range': {
        **dict(newer.metadata['native_range']), 'base_parser_version': '0.1.1'}}
    forged = change(span(newer), structured_value=badbinding)
    assert verify_replayed_pdf_spans((forged,), current) == ((), (forged.span_id,))


def test_cache_recipe_and_decision_inventory_publish_current_versions():
    from company_wiki.source_catalog.narrative_pdf_reading import NativePdfBackend
    from company_wiki.document_understanding.decision_inventory import _versions
    recipe = NativePdfBackend().describe_recipe()
    assert recipe['parser_version'] == '0.1.2'
    assert _versions(pdf_frontend=True)['pdf_native_range_parser'] == '0.1.1'
    old = {**recipe, 'parser_version': '0.1.1'}
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    assert digest(old) != digest(recipe)
    from types import SimpleNamespace
    from company_wiki.automation.narrative_generation import generation_manifest, generation_sha256
    payload = SimpleNamespace(
        source_ref=SimpleNamespace(mime_type='application/pdf', to_dict=lambda: {'source_id': SID}),
        source_metadata=SimpleNamespace(source_class='filing', to_dict=lambda: {'source_class':'filing'}))
    request = SimpleNamespace(model_options={'model_id':'fixture', 'max_output_tokens':100}, profile='fixture')
    current = generation_manifest(request, payload, execution_versions={'selector':'0.8.0'},
        parser_components=recipe, reading_model_projection=None)
    previous = generation_manifest(request, payload, execution_versions={'selector':'0.8.0'},
        parser_components=old, reading_model_projection=None)
    assert generation_sha256(current) != generation_sha256(previous)
