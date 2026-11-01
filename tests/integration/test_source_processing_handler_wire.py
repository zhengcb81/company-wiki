"""Reading capability state crosses the real handler/strict public wire."""
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import patch

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeContractError, NarrativeSelectResult
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.document_understanding import statement_grammar as grammar
from unit.test_narrative_select_handler import FakeReader, _context, _payload


BUSINESS = 'Our vessels transport liquefied gas between coastal terminals. Net income was $20 million.'
TYPED = 'Our software processes customer orders.'


def _handler_result(*, missing_resource=False):
    text = BUSINESS + ('</p><p>' + TYPED if missing_resource else '')
    data = ('<html><body><p>' + text + '</p></body></html>').encode()
    payload = _payload(data, title='Annual business review', document_kind='annual_report',
                       language='en', mime_type='text/html')
    handler = NarrativeSelectHandler(reader=FakeReader(payload, data), selector_version='0.9.0')
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')) if missing_resource else nullcontext():
        result = handler(_context(payload, lambda: None))
    return result


@pytest.fixture(scope='module')
def normal_wire():
    result = _handler_result()
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    return NarrativeSelectResult.from_dict(result.result).to_dict()


@pytest.fixture(scope='module')
def deferred_wire():
    result = _handler_result(missing_resource=True)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    return NarrativeSelectResult.from_dict(result.result).to_dict()


@pytest.mark.parametrize('missing_resource', (False, True))
def test_real_handler_serializes_source_processing_state(missing_resource):
    result = _handler_result(missing_resource=missing_resource)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    wire = NarrativeSelectResult.from_dict(result.result).to_dict()
    assert wire['reading_context']['source_processing_complete'] is (not missing_resource)
    assert wire['selection']['status'] == ('partial' if missing_resource else 'selected')
    checked = NarrativeSelectResult.from_dict(wire).to_dict()
    assert checked == wire
    if missing_resource:
        diagnostics = checked['reading_context']['selection_diagnostics']
        assert any(row['code'] == 'source_grammar_unavailable' for row in diagnostics)
        assert {span['raw_text'] for span in checked['evidence_spans']} == {TYPED}


@pytest.mark.parametrize('bad', (None, 0, 1, 'false', [], {}))
def test_public_result_rejects_non_boolean_processing_state(bad, normal_wire):
    wire = deepcopy(normal_wire)
    wire['reading_context']['source_processing_complete'] = bad
    with pytest.raises(NarrativeContractError, match='source_processing_complete'):
        NarrativeSelectResult.from_dict(wire)


def test_old_optional_absence_is_preserved_and_arbitrary_fields_are_still_rejected(normal_wire):
    old = deepcopy(normal_wire)
    del old['reading_context']['source_processing_complete']
    assert NarrativeSelectResult.from_dict(old).to_dict() == old
    old['reading_context']['unexpected_future_permission'] = True
    with pytest.raises(NarrativeContractError, match='unknown fields'):
        NarrativeSelectResult.from_dict(old)


def test_current_optional_field_cannot_be_backported_to_old_schema(normal_wire):
    wire = deepcopy(normal_wire)
    wire['reading_context']['schema_version'] = 'du-production-reading/3'
    with pytest.raises(NarrativeContractError, match='unknown fields'):
        NarrativeSelectResult.from_dict(wire)


@pytest.mark.parametrize(('field', 'bad'), (
    ('known_unit_ids', ['invalid-id']),
    ('known_unit_count', 0),
    ('known_unit_ids_limited', True),
    ('phase', 'arbitrary_phase'),
    ('dimension', 'selection_work'),
    ('code', 'unregistered_unknown_reason'),
    ('unexpected_field', True),
))
def test_new_diagnostic_shape_stays_strict(deferred_wire, field, bad):
    wire = deepcopy(deferred_wire)
    row = next(row for row in wire['reading_context']['selection_diagnostics']
               if row['code'] == 'source_grammar_unavailable')
    row[field] = bad
    with pytest.raises(NarrativeContractError):
        NarrativeSelectResult.from_dict(wire)


def test_current_wire_feature_is_bound_to_the_actual_recipe():
    from company_wiki.document_understanding.reading_context_contract import READING_CONTEXT_CONTRACT_FEATURE_VERSION
    from company_wiki.source_catalog.narrative_decision_inventory import _versions
    from company_wiki.source_catalog.reading_recipe import business_algorithm_hashes

    assert _versions()['reading_context_contract'] == READING_CONTEXT_CONTRACT_FEATURE_VERSION
    assert 'company_wiki.document_understanding.reading_context_contract' in business_algorithm_hashes(pdf_frontend=False)
