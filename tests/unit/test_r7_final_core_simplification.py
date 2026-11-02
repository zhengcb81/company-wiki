"""Explicit resources and typed source content replace hidden permissions."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, PhysicalPathLeakError
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_summary_execution import parse_summary_job_result
from company_wiki.automation.models import HandlerOutcome
from company_wiki.source_contract import EvidenceSpan
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter, CanonicalImportError
from contract.test_source_catalog_canonical_writer import _catalog, _staged_contract
from support.narrative_model_request_fixture import selection, response_draft
from unit.test_narrative_batch import _request
from unit.test_narrative_summarize_handler import _context


@pytest.mark.parametrize('count', [101, 250])
def test_explicit_batch_members_do_not_have_a_second_hidden_count_quota(count):
    value = _request().to_dict()
    original = value['sources'][0]
    value['sources'] = [{**original, 'document_id': 'doc-' + str(i),
        'source_id': 'urn:company-wiki:source:sha256:' + format(i, '064x'),
        'content_sha256': format(i, '064x')} for i in range(1, count + 1)]
    before = deepcopy(value)
    actual = NarrativeBatchRequest.from_dict(value)
    assert len(actual.sources) == count
    assert actual.max_tokens == _request().max_tokens
    assert actual.max_seconds == _request().max_seconds
    assert actual.max_micro_usd == _request().max_micro_usd
    assert value == before


def test_explicit_final_budget_roundtrips_above_old_emergency_ceiling():
    value = _request().to_dict()
    value.update(max_final_bytes=5 * 1024**2, max_persistent_bytes=1024**3, max_scratch_bytes=2 * 1024**3)
    actual = NarrativeBatchRequest.from_dict(value)
    assert actual.max_final_bytes == 5 * 1024**2
    assert NarrativeBatchRequest.from_dict(actual.to_dict()) == actual


def test_actual_object_writer_uses_the_requested_final_budget_without_hidden_ceiling(tmp_path):
    from types import SimpleNamespace
    from company_wiki.automation.narrative_batch import _BudgetedObjects
    guard = SimpleNamespace(max_scratch_bytes=8 * 1024**2, owned_accounting=None, peak=0,
                            check=lambda: None)
    store = _BudgetedObjects(tmp_path / 'objects', guard, 5 * 1024**2)
    assert store.put(b'x' * (3 * 1024**2))
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))
    with pytest.raises(ValueError, match='FINAL_BYTES_EXCEEDED'):
        store.put(b'x' * (5 * 1024**2 + 1))
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*')) == before


@pytest.mark.parametrize('field,value', [('max_final_bytes', True), ('max_final_bytes', 0),
    ('max_tokens', -1), ('max_seconds', float('inf'))])
def test_actual_explicit_resources_stay_validated(field, value):
    wire = _request().to_dict()
    wire[field] = value
    with pytest.raises(ValueError):
        NarrativeBatchRequest.from_dict(wire)


def test_large_optional_provenance_preserves_real_original_and_full_trace(tmp_path):
    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    original = staged.read_bytes()
    extensions = {'provider_trace': {'notes': '原始来源诊断🙂' * 3000, 'complete': False, 'unknown': None}}
    before = deepcopy(extensions)
    try:
        result = CanonicalSourceWriter(catalog).import_staged(request, candidate, receipt,
            provenance_extensions=extensions)
        from pathlib import Path
        assert Path(result.canonical_path).read_bytes() == original
        assert json.loads(Path(result.provenance_path).read_bytes())['provenance_extensions'] == before
        assert extensions == before and not staged.exists()
    finally:
        catalog.close()


@pytest.mark.parametrize('bad', [object(), float('nan')], ids=['not-json', 'nonfinite'])
def test_provenance_correctness_failure_does_not_commit_or_delete_staged_original(tmp_path, bad):
    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    before = staged.read_bytes()
    try:
        with pytest.raises(CanonicalImportError):
            CanonicalSourceWriter(catalog).import_staged(request, candidate, receipt,
                provenance_extensions={'provider_trace': {'invalid': bad}})
        assert staged.read_bytes() == before
    finally:
        catalog.close()


def test_large_optional_provenance_does_not_make_wrong_original_identity_valid(tmp_path):
    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    before = staged.read_bytes()
    try:
        with pytest.raises(CanonicalImportError):
            CanonicalSourceWriter(catalog).import_staged(request, candidate,
                replace(receipt, content_sha256='f' * 64), provenance_extensions={'provider_trace': 'x' * 17000})
        assert staged.read_bytes() == before
    finally:
        catalog.close()


def source_quote(text):
    selected = selection(1)
    wire = selected.to_dict()
    span = selected.evidence_spans[0]
    wire['source_metadata']['language'] = 'en'
    wire['evidence_spans'] = [EvidenceSpan.create(source_id=span.source_id,
        coordinates=span.coordinates, raw_text=text, structured_value={**span.structured_value, 'language': 'en'},
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags).to_dict()]
    return wire


@pytest.mark.parametrize('text', [r'C:\subscription\contract — Subscription contracts generate revenue.',
    r'\\example.invalid\published — Subscription contracts generate revenue.',
    'file://public-document-example — Subscription contracts generate revenue.'])
def test_source_body_path_text_is_content_in_public_select_contract(text):
    wire = source_quote(text)
    parsed = NarrativeSelectResult.from_dict(wire)
    assert parsed.evidence_spans[0].raw_text == text
    assert parsed.to_dict() == wire


@pytest.mark.parametrize('wrong_citation', [False, True])
def test_real_summary_handler_preserves_path_text_and_retains_reference_checks(wrong_citation):
    source = NarrativeSelectResult.from_dict(source_quote('file://public-source-example — Subscription contracts generate revenue.'))
    class Model:
        def generate(self, request):
            body = response_draft(json.loads(request.data_json))
            if wrong_citation:
                body['draft']['claims'][0]['evidence_ids'] = ['not-in-source']
            return NarrativeModelResponse('fixture', 'fixture', request.prompt_version,
                canonical_json(body).encode('utf-8'))
    result = NarrativeSummarizeHandler(model=Model())(_context(source))
    if wrong_citation:
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == 'SUMMARY_INVALID'
        return
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    summary = parse_summary_job_result(result.result, selected=source)
    assert summary.draft.claims[0].text == source.evidence_spans[0].raw_text
    assert summary.draft.claims[0].evidence_ids == (source.evidence_spans[0].span_id,)


def test_scoped_decoder_keeps_source_body_paths_without_changing_scope():
    from unit.test_narrative_reading_transport import reading_context
    from unit.test_scoped_source_admission import decode, clause
    source = NarrativeSelectResult.from_dict(source_quote('file://public-source-example — Subscription contracts generate revenue.'))
    source = replace(source, reading_context=reading_context(source))
    draft = decode(source, {'t1': [clause(source, 0)]})
    assert draft['claims'][0]['text'] == source.evidence_spans[0].raw_text
    assert draft['claims'][0]['evidence_ids'] == [source.evidence_spans[0].span_id]


@pytest.mark.parametrize('position', ['structured-text', 'metadata-title', 'metadata-key'])
def test_source_body_exception_does_not_allow_storage_metadata_paths(position):
    wire = source_quote('Ordinary source business statement.')
    if position == 'structured-text':
        wire['evidence_spans'][0]['structured_value']['text'] = r'C:\actual-storage\location'
    elif position == 'metadata-title':
        wire['source_metadata']['title'] = r'C:\actual-storage\location'
    else:
        wire['evidence_spans'][0]['structured_value']['local_path'] = 'private-location'
    with pytest.raises(PhysicalPathLeakError):
        NarrativeSelectResult.from_dict(wire)
