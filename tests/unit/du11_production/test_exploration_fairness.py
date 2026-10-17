"""Unclassified pages cannot spend the work reserved for known business intent."""
from types import SimpleNamespace
import pytest

from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
from company_wiki.source_catalog import narrative_pdf_intent as execution
from company_wiki.source_catalog.narrative_evidence import _make_unit, NARRATIVE_PARSER_VERSION
from company_wiki.source_contract import EvidenceCoordinates


@pytest.mark.parametrize('limit', [2_000_000, 16_000_000])
def test_unknown_exploration_has_a_shared_ceiling_and_cannot_starve_later_business(monkeypatch, limit):
    sha = 'a' * 64
    unit = _make_unit(source_id='source', parser_version=NARRATIVE_PARSER_VERSION,
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text='年度报告 管理层讨论与分析', unit_kind='pdf_text_block',
        source_role='company_filing', language='zh', metadata={})
    budget = WorkBudget(limit)
    collector = SimpleNamespace(limits={'max_pages':64}, exhausted=False)
    state = SimpleNamespace(source_id='source', source_sha256=sha, page_count=80,
                            parser_version=NARRATIVE_PARSER_VERSION)
    session = execution.SourceGeometrySession((unit,), context=PdfReadingContext('年度报告', 'annual_report'),
        state=state, outline=[[1, 'Unmatched chapter', 1], [1, '管理层讨论与分析', 75]],
        budget=budget, collector=collector)
    accounts = []
    def expensive_observation(snapshot, *, work_budget, **kwargs):
        accounts.append(work_budget)
        try:
            work_budget.charge(120_000)
            return {'candidate':True, 'partial':False, 'continuation':None}
        except WorkBudgetExceeded:
            return {'candidate':False, 'partial':True, 'continuation':None}
    monkeypatch.setattr(execution, 'observe_pdf_candidate', expensive_observation)
    session.request(1, {})
    session.request(2, {})
    session.request(3, {})
    assert session.exploration_budget.exhausted and not budget.exhausted
    assert session.exploration_budget.used == 240_000
    assert session.request(75, {}) == (True, True)
    assert accounts[-1] is budget
    assert all(account._parent is budget for account in accounts[:-1])
    assert budget.used >= 360_000
    assert session.summary()['complete'] is False
