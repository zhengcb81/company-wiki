"""Source-shaped behavior of the actual shared PDF production port."""
import hashlib
from types import SimpleNamespace

import pymupdf as fitz
import pytest

from company_wiki.automation import narrative_select as execution
from company_wiki.automation import narrative_selector_binding as binding
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded
from company_wiki.source_catalog import narrative_evidence as source
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeEvidencePackage


def package(parsed, *, complete=True):
    return NarrativeEvidencePackage(parsed.source_id, parsed.source_sha256, 'annual_report',
        'skipped_no_narrative' if complete else 'needs_review', (), 64, 0, 0, 0, 0, complete)


def payload():
    return SimpleNamespace(source_ref=SimpleNamespace(mime_type='application/pdf', source_id='source',
        content_sha256='a' * 64), source_metadata=SimpleNamespace(language='en',
        title='Annual Report', document_kind='annual_report'))


@pytest.mark.parametrize('version,expected', [('0.9.0', [False]), ('0.8.0', [False, True])])
def test_shared_empty_selection_never_resets_source_by_full_scan(version, expected):
    calls = []
    def parser(data, **kwargs):
        calls.append(kwargs['full_table_scan'])
        return DocumentStructure('source', 'a' * 64, 'en', (), page_count=3,
            pages_read=3, deferred_table_pages=(3,))
    handler = execution.NarrativeSelectHandler(reader=object(), pdf_parser=parser,
        selector=lambda parsed, **kw: package(parsed, complete=False), selector_version=version)
    with pytest.raises(execution._SelectFailure):
        handler._select_pdf(payload(), b'not opened by injected parser', SimpleNamespace(checkpoint=lambda: None))
    assert calls == expected


def test_production_passes_one_budget_from_source_to_builtin_selector(monkeypatch):
    from company_wiki import resource_budget
    from dataclasses import replace
    configured = replace(resource_budget.load_budget_policy(), document_work_limit=123_456)
    monkeypatch.setattr(resource_budget, 'load_budget_policy', lambda *args, **kwargs: configured)
    observed = {}
    def parser(data, **kwargs):
        observed['source'] = kwargs.get('work_budget')
        assert observed['source'] is not None
        assert observed['source'].max_work_units == 123_456
        observed['source'].charge(17)
        return DocumentStructure('source', 'a' * 64, 'en', (), page_count=1, pages_read=1)
    def selector(parsed, **kwargs):
        observed['selector'] = kwargs.get('work_budget')
        assert observed['selector'] is observed['source']
        assert observed['selector'].used == 17
        observed['selector'].charge(11)
        return package(parsed)
    monkeypatch.setattr(binding, 'select_narrative_evidence', selector)
    handler = execution.NarrativeSelectHandler(reader=object(), pdf_parser=parser, selector_version='0.9.0')
    handler._select_pdf(payload(), b'fixture', SimpleNamespace(checkpoint=lambda: None))
    assert observed['source'].used == 28


def synthetic_pdf():
    with fitz.open() as doc:
        for number in range(1, 81):
            page = doc.new_page()
            text = ('年度报告 管理层讨论与分析' if number == 1 else
                    '风险因素 ………… 3' if number == 2 else
                    '重要事项：公司治理说明，不涉及具体业务变化。')
            page.insert_text((50, 60), text, fontname='china-s', fontsize=11)
            if number in (75, 79):
                heading = '主要产品产销量' if number == 75 else '产能'
                page.insert_text((50, 90), heading, fontname='china-s')
                for y, cells in [(120, ('产品', '2025年', '2024年')), (145, ('设备产量（台）', '120', '100'))]:
                    for x, value in zip((50, 230, 390), cells):
                        page.insert_text((x, y), value, fontname='china-s')
        doc.set_toc([[1, '重要事项', 3], [1, '管理层讨论与分析', 75],
                     [2, '主要产品产销量', 75], [2, '产能', 79]])
        return doc.tobytes()


def test_actual_default_demand_reaches_deep_operating_pages_without_prefix_scan(monkeypatch):
    calls = []
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number + 1) or SimpleNamespace(tables=[]))
    data = synthetic_pdf()
    from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
    budget = WorkBudget(2_000_000)
    parsed = source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
        selector_version='0.9.0', language='zh', work_budget=budget,
        reading_context=PdfReadingContext('年度报告', 'annual_report', 'zh'))
    assert {75, 79} <= set(calls)
    assert not set(range(3, 75)).intersection(calls)
    assert len(calls) <= 64
    assert len(calls) == len(set(calls))
    assert parsed.pages_read == 80
    assert parsed.layout_coverage['planning']['request_digest']
    assert budget.used > parsed.layout_coverage['work_units'] > 0
    legacy = source.parse_pdf_bytes(data, source_id='source', source_sha256=parsed.source_sha256,
                                   table_pages=(), language='zh')
    assert [(u.unit_id, u.raw_text, u.coordinates) for u in parsed.units] == [
        (u.unit_id, u.raw_text, u.coordinates) for u in legacy.units]


def test_zero_shared_work_stops_before_native_text_or_tables(monkeypatch):
    calls = []
    monkeypatch.setattr(source, '_pdf_text_blocks',
        lambda *args, **kw: calls.append('native_text'))
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number) or SimpleNamespace(tables=[]))
    data = synthetic_pdf()
    budget = WorkBudget(0)
    with pytest.raises(WorkBudgetExceeded) as failure:
        source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
            selector_version='0.9.0', work_budget=budget)
    assert calls == []
    assert budget.used == 0 and budget.exhausted
    assert failure.value.dimension == 'document_work' and failure.value.limit == 0


def test_source_work_limit_has_a_specific_terminal_production_diagnostic(monkeypatch):
    from company_wiki import resource_budget
    observed = []
    monkeypatch.setattr(resource_budget, 'new_document_work_budget', lambda: WorkBudget(0))
    monkeypatch.setattr(source, '_pdf_text_blocks', lambda *args, **kw: observed.append('read'))
    handler = execution.NarrativeSelectHandler(reader=object(), selector_version='0.9.0')
    monkeypatch.setattr(handler, '_run_selector', lambda *args, **kw: observed.append('select'))
    data = synthetic_pdf()
    original = payload()
    original.source_ref.content_sha256 = hashlib.sha256(data).hexdigest()
    with pytest.raises(execution._SelectFailure) as failure:
        handler._select_pdf(original, data, SimpleNamespace(checkpoint=lambda: None))
    assert failure.value.code == 'PARSER_INCOMPLETE'
    assert failure.value.outcome == execution.HandlerOutcome.TERMINAL_FAILURE
    assert 'document_work limit reached' in failure.value.detail
    assert observed == []


def test_resource_exhausted_during_capture_cannot_execute_a_reserved_finder(monkeypatch):
    from company_wiki.source_catalog.narrative_pdf_layout import PdfLayoutCollector
    calls = []
    original_capture = PdfLayoutCollector.capture_pending_page
    def exhaust_after_capture(collector, number, *, requested):
        original_capture(collector, number, requested=requested)
        if requested:
            collector.exhausted = True
    monkeypatch.setattr(PdfLayoutCollector, 'capture_pending_page', exhaust_after_capture)
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number + 1) or SimpleNamespace(tables=[]))
    data = synthetic_pdf()
    parsed = source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
        selector_version='0.9.0')
    assert calls == []
    assert parsed.layout_coverage['planning']['complete'] is False
    assert parsed.layout_coverage['planning']['reason_counts']['discovery_resource_deferred']


def test_budget_rechecked_after_text_emission_at_the_actual_finder(monkeypatch):
    calls = []
    emit = source._emit_pdf_text_units
    def expire_while_emitting(state, number, blocks):
        answer = emit(state, number, blocks)
        if number in state.table_scan_pages:
            state.layout_collector.exhausted = True
        return answer
    monkeypatch.setattr(source, '_emit_pdf_text_units', expire_while_emitting)
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number + 1) or SimpleNamespace(tables=[]))
    data = synthetic_pdf()
    parsed = source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
                                    selector_version='0.9.0')
    assert not calls
    planning = parsed.layout_coverage['planning']
    assert planning['reason_counts']['discovery_resource_deferred']
    assert planning['deferred_pages'] and planning['complete'] is False


@pytest.mark.parametrize('options', [{'full_table_scan': True}, {'table_pages': (75,)}])
def test_explicit_geometry_request_cannot_bypass_the_same_zero_budget(monkeypatch, options):
    calls = []
    monkeypatch.setattr(source, '_pdf_text_blocks',
        lambda *args, **kw: calls.append('native_text'))
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number + 1) or SimpleNamespace(tables=[]))
    data = synthetic_pdf()
    budget = WorkBudget(0)
    with pytest.raises(WorkBudgetExceeded) as failure:
        source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
            selector_version='0.9.0', work_budget=budget, **options)
    assert not calls and budget.used == 0 and budget.exhausted
    assert failure.value.dimension == 'document_work' and failure.value.limit == 0


@pytest.mark.parametrize('heading,expected', [('XYZ_unmatched_heading', True), ('风险因素', False)])
def test_unmatched_native_navigation_is_unknown_not_an_explicit_skip(monkeypatch, heading, expected):
    calls = []
    monkeypatch.setattr(fitz.Page, 'find_tables',
        lambda page, **kw: calls.append(page.number + 1) or SimpleNamespace(tables=[]))
    with fitz.open(stream=synthetic_pdf(), filetype='pdf') as document:
        document.set_toc([[1, heading, 1]] if expected else
                         [[1, '管理层讨论与分析', 1], [2, heading, 1]])
        data = document.tobytes()
    from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
    parsed = source.parse_pdf_bytes(data, source_id='source', source_sha256=hashlib.sha256(data).hexdigest(),
        selector_version='0.9.0', reading_context=PdfReadingContext('年度报告', 'annual_report', 'zh'))
    assert bool(calls) is expected
    if expected:
        assert parsed.layout_coverage['planning']['complete'] is False
        assert parsed.layout_coverage['planning']['unresolved_navigation_count']
