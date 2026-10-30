"""Source classifications are intrinsic; partial proof only excludes known mismatches."""
import pytest

from company_wiki.source_catalog.document_kinds import document_kind_matches,sec_primary_document_kind
from company_wiki.source_catalog.canonical_scope import SourceScope,ScopeRelation,scope_relatedness
from company_wiki.source_catalog.resolver import SourceRequest


@pytest.mark.parametrize(('form','kind'),(
    ('10-K','annual_report'),('10-K/A','annual_report'),('20-F','annual_report'),
    ('20-F/A','annual_report'),('10-Q','regulatory_filing'),('10-Q/A','regulatory_filing')))
def test_sec_kind_is_a_function_of_primary_form(form,kind):
    assert sec_primary_document_kind(form)==kind


@pytest.mark.parametrize(('requested','actual','matches'),(
    ('regulatory_filing','annual_report',True),('regulatory_filing','quarterly_report',True),
    ('regulatory_filing','semi_annual_report',True),('annual_report','regulatory_filing',False),
    ('annual_report','quarterly_report',False),('regulatory_filing','investor_relations',False),
    ('regulatory_filing','financial_statement_dataset',False)))
def test_generic_request_does_not_relabel_or_cross_unrelated_families(requested,actual,matches):
    assert document_kind_matches(requested,actual) is matches


@pytest.mark.parametrize(('year','expected'),((2022,ScopeRelation.NOT_RELEVANT),
                                          (2026,ScopeRelation.UNKNOWN),(None,ScopeRelation.UNKNOWN)))
def test_partial_observation_can_exclude_an_old_year_but_never_prove_the_target(year,expected):
    facts={'entity':'Acme','market':'US','security_id':'ACME','document_kind':'annual_report',
           'fiscal_year':year,'fiscal_period':'FY','form_type':'10-K'}
    request=SourceRequest(entity='Acme',market='US',security_id='ACME',document_kind='annual_report',
                          fiscal_year=2026,fiscal_period='FY',as_of_date='2026-10-30')
    assert scope_relatedness(SourceScope(facts,{},'source-facts-partial'),request) is expected
