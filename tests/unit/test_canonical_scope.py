"""Source-layer scope algebra, independent from storage and identity providers."""
from dataclasses import replace
import pytest
from company_wiki.source_catalog.canonical_scope import SourceScope, ScopeRelation, scope_relatedness
from company_wiki.source_catalog.resolver import SourceRequest


def request():
    return SourceRequest(entity="Acme",market="HK",security_id="09999",
        document_kind="annual_report",fiscal_year=2024,fiscal_period="FY",as_of_date="2026-01-01")


def scope():
    req=request()
    facts={key:value for key,value in req.identity_dict().items() if value is not None}
    return SourceScope(facts,{},"source-facts")


def test_known_target_matches_and_other_year_is_irrelevant():
    assert scope_relatedness(scope(),request()) is ScopeRelation.MATCH
    assert scope_relatedness(scope(),replace(request(),fiscal_year=2025)) is ScopeRelation.NOT_RELEVANT


@pytest.mark.parametrize("field",["entity","market","security_id","document_kind","fiscal_year","fiscal_period"])
def test_missing_requested_scope_is_unknown(field):
    known=scope()
    facts={key:value for key,value in known.facts.items() if key != field}
    assert scope_relatedness(SourceScope(facts,{},known.authority),request()) is ScopeRelation.UNKNOWN


def test_identity_conflict_is_unknown_even_if_old_period():
    facts={**scope().facts,"security_id":"00001","fiscal_year":2023}
    assert scope_relatedness(SourceScope(facts,{},"source-facts"),request()) is ScopeRelation.UNKNOWN


def test_fiscal_period_and_kind_are_compared_without_calendar_guesses():
    known=SourceScope({**scope().facts,"document_kind":"quarterly_report","fiscal_period":"Q2"},{},"source-facts")
    req=replace(request(),document_kind="quarterly_report",fiscal_period="Q3")
    assert scope_relatedness(known,req) is ScopeRelation.NOT_RELEVANT


def test_unverified_declaration_cannot_match_or_exclude_even_if_shape_complete():
    unverified=SourceScope(scope().facts,{},"unverified-declaration")
    assert scope_relatedness(unverified,request()) is ScopeRelation.UNKNOWN
    assert scope_relatedness(unverified,replace(request(),fiscal_year=2025)) is ScopeRelation.UNKNOWN
