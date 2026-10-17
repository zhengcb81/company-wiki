"""Offering documents contain the issuer's existing business as well as projects."""
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext, prepare_geometry_reading
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_evidence import _make_unit, NARRATIVE_PARSER_VERSION
from company_wiki.source_contract import EvidenceCoordinates


def test_actual_offering_policy_keeps_sales_and_project_windows_independent():
    sha = 'a' * 64
    unit = _make_unit(source_id='urn:company-wiki:source:sha256:' + sha,
        parser_version=NARRATIVE_PARSER_VERSION, coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text='公开发行可转换公司债券募集说明书', unit_kind='pdf_text_block',
        source_role='company_filing', language='zh', metadata={})
    prepared = prepare_geometry_reading((unit,), context=PdfReadingContext('公开发行可转换公司债券募集说明书', 'convertible_bond_prospectus'),
        source_id=unit.source_id, source_sha256=sha, page_count=280,
        native_outline=[[1, '发行人基本情况', 70], [2, '主要业务及主要产品', 90],
                        [3, '销售情况', 93], [1, '本次募集资金运用', 223]],
        limits={'max_pages':64,'max_requests':64}, work_budget=WorkBudget(2_000_000))
    allocations = prepared['plan']['allocations']
    assert any(r['physical_start'] <= 93 <= r['physical_end'] and r['status'] == 'reserved'
               and r['demand_class'] == 'operating' for r in allocations)
    assert any(r['physical_start'] <= 223 <= r['physical_end'] and r['status'] == 'reserved'
               and r['demand_class'] == 'project' for r in allocations)
