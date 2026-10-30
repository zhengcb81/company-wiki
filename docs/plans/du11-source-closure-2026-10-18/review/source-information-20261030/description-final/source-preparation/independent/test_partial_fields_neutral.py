"""Field-level provenance may exclude a scope, never fabricate positive access."""
from types import SimpleNamespace
import pytest

from company_wiki.source_catalog.assertion_service import _observed_sec_scope_fields, SOURCE_SCOPE_METHOD
from company_wiki.source_catalog.canonical_scope import SourceScope, ScopeRelation, scope_relatedness
from company_wiki.source_catalog.resolver import SourceRequest


@pytest.mark.parametrize(('change', 'expected'), [
    ({}, ScopeRelation.NOT_RELEVANT),
    ({'content_sha256': 'b' * 64}, ScopeRelation.UNKNOWN),
    ({'locator': 'primary-dei:/DocumentType'}, ScopeRelation.UNKNOWN),
    ({'value': 2026}, ScopeRelation.UNKNOWN),
    ({'extraction_method': 'provider-metadata-import/1'}, ScopeRelation.UNKNOWN),
])
def test_only_bound_original_year_can_exclude(change, expected):
    ref = SimpleNamespace(content_sha256='a' * 64)
    patch = {'entity': 'Acme', 'market': 'US', 'security_id': 'ACME',
             'fiscal_year': 2001, 'fiscal_period': 'Q2', 'form_type': '10-Q', 'period_end': None}
    proof = {}
    for key, field in [('fiscal_year', 'DocumentFiscalYearFocus'), ('fiscal_period', 'DocumentFiscalPeriodFocus'),
                       ('form_type', 'DocumentType')]:
        proof[key] = {'value': patch[key], 'content_sha256': ref.content_sha256,
                      'locator': 'primary-dei:/' + field, 'extraction_method': SOURCE_SCOPE_METHOD}
    proof['fiscal_year'].update(change)
    # The caller has already verified the three identity bindings; exercise only
    # this new field-projection owner, rather than replacing identity validation.
    observed = _observed_sec_scope_fields(ref, patch, proof)
    request = SourceRequest(entity='Acme', market='US', security_id='ACME',
                            document_kind='regulatory_filing', fiscal_year=2026, fiscal_period='Q2',
                            as_of_date='2026-10-30')
    assert scope_relatedness(SourceScope(observed, proof, 'source-facts-partial'), request) is expected
