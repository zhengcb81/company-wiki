"""One classification script view; originals and operating row closure stay exact."""
from copy import deepcopy

import pytest

from company_wiki.document_understanding.profiles import registry
from company_wiki.document_understanding.structure.table_purpose import qualify_table
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_matching import matching_text
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize('traditional,simplified', [
    ('本公司通過經銷渠道銷售產品。', '本公司通过经销渠道销售产品。'),
    ('本公司產品主要通過經銷渠道向客戶供應。', '本公司产品主要通过经销渠道向客户供应。'),
    ('本公司通過外購原材料製造產品，以降低交付成本。', '本公司通过外购原材料制造产品，以降低交付成本。'),
])
def test_script_variant_is_the_same_operating_relationship(traditional, simplified):
    first, second = detect_reading_business_fact(traditional), detect_reading_business_fact(simplified)
    assert first.eligible and second.eligible
    assert first == second


def test_old_matching_facade_keeps_only_script_conversion():
    raw = '本公司產品\n與服務使用3.5 million units，公司名稱為Delta’s。'
    result = matching_text(raw)
    assert '\n' in result and '3.5 million units' in result and 'Delta’s' in result
    assert raw == '本公司產品\n與服務使用3.5 million units，公司名稱為Delta’s。'


@pytest.mark.parametrize('label', ['主要產品', '存貨周轉日數', '存货周转天数', 'inventory turnover days', 'days inventory outstanding'])
def test_single_configured_discovery_service_interprets_operating_fields(label):
    assert registry.configured_table_signal(label+' | 2026 | 2025\n137 | 123')


@pytest.mark.parametrize('label', ['存貨周轉日數', '存货周转天数', 'Inventory turnover days', 'Days inventory outstanding'])
def test_turnover_days_in_mixed_financial_table_keep_only_operating_row(label):
    header = '指标 | 2026年 | 2025年'
    rows = ['营业收入 | 900 | 800', '股东权益 | 500 | 480', label+' | 137 | 123', '净利润 | 40 | 35']
    frozen = deepcopy((header, rows))
    result = qualify_table([header], rows)
    assert result.eligible and result.eligible_row_indices == (2,)
    assert (header, rows) == frozen


@pytest.mark.parametrize('row', [
    '存货资产总计 | 137 | 123', '股东权益 | 137 | 123',
    '存货周转日数是指库存持有的平均天数。',
    'Inventory turnover days is defined as the mean time inventory is held.',
])
def test_account_totals_and_metric_glossaries_are_not_operating_table_data(row):
    assert not qualify_table(['财务指标说明'], [row]).eligible


def test_traditional_relation_is_selected_as_exact_original_without_new_io():
    text = '本公司通過經銷渠道銷售產品。'
    source = source_id_for_sha256('a'*64)
    unit = _make_unit(source_id=source, parser_version='0.1.1',
        coordinates=EvidenceCoordinates(paragraph_index=0),raw_text=text,
        unit_kind='html_paragraph',source_role='company_filing',language='mixed',metadata={})
    parsed = DocumentStructure(source,'a'*64,'mixed',(unit,),mime_type='text/html',line_count=1)
    selected = select_narrative_evidence(parsed,title='Company update',selector_version='0.9.0',max_selected=8)
    assert [s.raw_text for s in selected.evidence_spans] == [text]
    assert selected.evidence_spans[0].coordinates == unit.coordinates
    assert selected.evidence_spans[0].source_id == source
    assert unit.raw_text == text


def test_discovery_still_obeys_the_one_configured_asset(monkeypatch):
    catalog = deepcopy(registry._CATALOG)
    for facet in catalog['facets']:
        for evidence in facet['positive_evidence']:
            evidence['table_scan'] = False
    monkeypatch.setattr(registry,'_CATALOG',catalog)
    assert not registry.configured_table_signal('平均存貨周轉日數 | 137 | 123')


def test_only_fixed_catalog_signals_are_memoized_and_changed_catalog_content_is_current(monkeypatch):
    catalog = deepcopy(registry._CATALOG)
    for facet in catalog['facets']:
        for evidence in facet['positive_evidence']:
            evidence['table_scan'] = False
    evidence = next(e for f in catalog['facets'] for e in f['positive_evidence'] if 'pdf_table_row' in e['unit_kinds'])
    evidence['table_scan'] = True
    evidence['signals'] = ['獨立周轉欄位']
    monkeypatch.setattr(registry,'_CATALOG',catalog)
    calls = []
    original = registry.matching_script_text

    def observed(text):
        calls.append(text)
        return original(text)

    monkeypatch.setattr(registry,'matching_script_text',observed)
    text = '同一份實際文檔含獨立周轉欄位 | 137 | 123'
    assert registry.configured_table_signal(text)
    assert registry.configured_table_signal(text)
    assert calls.count('獨立周轉欄位') == 1
    assert calls.count(text) == 2, 'original document strings must never enter a global folding cache'
    evidence['signals'] = ['替代庫存欄位']
    assert not registry.configured_table_signal(text)
    assert registry.configured_table_signal('實際來源有替代庫存欄位 | 100')
