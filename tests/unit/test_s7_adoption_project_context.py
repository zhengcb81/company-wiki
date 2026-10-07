"""Business classification and real-layout table associations, independent of issuer names."""
from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_evidence as n
from company_wiki.source_catalog.n6_candidate_operating_facts import detect_operating_fact
from company_wiki.source_catalog.narrative_budget import BudgetItem, budget_diagnostics, select_budget_items
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_project_context import enrich_fundraising_table_context
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize('text', [
    '公司的工业设备已应用于全球先进制造生产线。',
    '公司的新系统已经应用于汽车客户的生产线。',
    '公司的新能源产品实现了批量销售。',
])
def test_completed_product_adoption_is_distinct_from_commissioning_a_site(text):
    fact = detect_operating_fact(text)
    assert 'customer_adoption_milestone' in fact.reasons
    assert 'applied_operating_milestone' in fact.reasons


@pytest.mark.parametrize('text', [
    '公司生产和研发基地已正式投入使用。', '公司研发车间已投入使用。',
    '公司拟将新设备应用于客户生产线。', '公司的新设备尚未应用于客户生产线。',
    '来自海外客户的营业收入增长了20%。',
])
def test_plans_sites_and_financial_ratios_are_not_completed_customer_adoption(text):
    assert 'customer_adoption_milestone' not in detect_operating_fact(text).reasons


def test_busy_site_milestones_cannot_consume_every_product_adoption_slot():
    def item(name, page, reason, score):
        return BudgetItem(name, None, ('page', page), f'loc:v1/page:{page}',
                          (page,), (reason,), score, False, name)
    items = tuple(item(f'site-{i}', i, 'applied_operating_milestone', 30) for i in range(20)) + (
        item('product', 1, 'customer_adoption_milestone', 13),
        item('industry', 21, 'current_industry_context', 8),
        item('event', 22, 'specific_business_event', 8),
    )
    chosen = select_budget_items(items, limit=12)
    assert 'product' in {i.item_id for i in chosen} and len(chosen) == 12
    assert chosen == select_budget_items(tuple(reversed(items)), limit=12)
    assert select_budget_items(items, limit=1)[0].item_id == 'product'
    # An atomic pair cannot fit one slot; diagnose its business category.
    pair = (replace(items[20], group_id='adoption-pair'),
            replace(items[20], item_id='product-detail', group_id='adoption-pair'))
    diagnostics = budget_diagnostics(pair, limit=1)
    product = next(d for d in diagnostics if 'product' in d.item_ids)
    assert product.category == 'customer_adoption'


HEADERS = ('序号', '募集资金运用方向', '项目总投资', '拟投入募集资金')


def unit(index, text, *, kind='pdf_text_block', bbox=(80, 390, 510, 404), cells=()):
    coords = (EvidenceCoordinates(page_number=2, table_index=0, row_index=index)
              if kind == 'pdf_table_row' else EvidenceCoordinates(page_number=2, paragraph_index=index))
    metadata = {'bbox': bbox, 'pdf_block': 9 if index in (0, 1) else index}
    if kind == 'pdf_table_row':
        metadata.update(row_cells=cells, table_headers=HEADERS)
    return n._make_unit(source_id=source_id_for_sha256('a' * 64), parser_version='0.1.1',
                        coordinates=coords, raw_text=text, unit_kind=kind,
                        source_role='company_filing', language='zh', metadata=metadata)


def documents():
    intro = (unit(0, '本次募集资金扣除费用后将投资于以下'),
             unit(1, '项目：', bbox=(80, 410, 510, 424)))
    legal = unit(2, '公司将遵守资金使用管理规定。', bbox=(80, 560, 510, 574))
    rows = tuple(unit(i, ' | '.join(cells), kind='pdf_table_row', bbox=(80, 455, 510, 550), cells=cells)
                 for i, cells in enumerate((HEADERS,
                     ('1', '工业设备扩产升级项目', '100', '90'),
                     ('2', '技术研发中心建设升级项目', '120', '100'),
                     ('3', '补充流动资金', '50', '50'), ('合计', '', '270', '240'))))
    return (*intro, legal, *rows)  # extraction order intentionally disagrees with visual order


def enrich(units, *, candidates=(), groups=None):
    return enrich_fundraising_table_context(units, n._pdf_context_groups(units),
                                            initial_candidates=candidates, initial_group_ids=groups or {})


def test_split_introduction_and_named_rows_share_one_replayable_atomic_group():
    units = documents()
    result = enrich(units)
    expected = {units[i].unit_id for i in (0, 1, 4, 5)}
    assert {c.unit.unit_id for c in result.candidates} == expected
    assert len(set(result.group_ids.values())) == 1
    assert set(result.group_ids) == expected
    assert all('concrete_fundraising_project' in c.reasons for c in result.candidates)
    assert all(c.unit in units for c in result.candidates)
    reversed_result = enrich(tuple(reversed(units)))
    assert result.group_ids == reversed_result.group_ids


@pytest.mark.parametrize('field,value', [
    ('source_id', source_id_for_sha256('b' * 64)), ('parser_version', '0.1.0'),
    ('language', 'en'), ('source_role', 'management'),
    ('coordinates', EvidenceCoordinates(page_number=3, table_index=0, row_index=1)),
])
def test_project_rows_cannot_borrow_another_identity_or_page(field, value):
    units = documents()
    changed = tuple(replace(u, **{field: value}) if u.unit_kind == 'pdf_table_row' else u for u in units)
    assert enrich(changed).candidates == ()


@pytest.mark.parametrize('bbox', [None, (80, 600, 510, 690), (550, 455, 700, 550),
                                 (80, 300, 510, 370), (80, float('nan'), 510, 550)])
def test_missing_distant_side_column_or_above_table_is_not_a_visual_link(bbox):
    changed = tuple(replace(u, metadata={**u.metadata, 'bbox': bbox})
                    if u.unit_kind == 'pdf_table_row' else u for u in documents())
    assert enrich(changed).candidates == ()


@pytest.mark.parametrize('middle', ['公司将严格管理募集资金。', '七、利润分配安排'])
def test_intervening_body_or_heading_is_a_barrier(middle):
    units = documents() + (unit(10, middle, bbox=(80, 435, 510, 449)),)
    assert enrich(units).candidates == ()


def test_unit_caption_is_allowed_but_financial_rows_and_wrong_headers_are_not():
    units = documents() + (unit(10, '单位：万元', bbox=(450, 435, 510, 449)),)
    assert len(enrich(units).candidates) == 4
    wrong = tuple(replace(u, metadata={**u.metadata, 'table_headers': ('序号', '金额', '项目总投资')})
                  if u.unit_kind == 'pdf_table_row' else u for u in units)
    assert enrich(wrong).candidates == ()
    finance_only = tuple(u for i,u in enumerate(units) if i not in (4,5))
    assert enrich(finance_only).candidates == ()


def test_existing_local_group_is_consolidated_but_cross_event_group_is_not_stolen():
    units = documents()
    original = EvidenceCandidate(units[0], ('capacity_projects',), ('existing_business',), 17)
    result = enrich(units, candidates=(original,), groups={units[0].unit_id:'old', units[1].unit_id:'old'})
    candidate = next(c for c in result.candidates if c.unit.unit_id == original.unit.unit_id)
    assert candidate.score >= 17 and 'existing_business' in candidate.reasons
    assert 'concrete_fundraising_project' in candidate.reasons
    conflict = {units[0].unit_id:'old', units[2].unit_id:'old'}
    refused = enrich(units, candidates=(original,), groups=conflict)
    assert refused.candidates == (original,) and refused.group_ids == conflict


@pytest.mark.parametrize('too_many,too_large', [(True, False), (False, True)])
def test_visual_context_does_not_exceed_unit_or_character_bounds(too_many, too_large):
    units = documents()
    if too_many:
        units += tuple(unit(i, '新设备建设项目 | 100', kind='pdf_table_row',
                            bbox=(80,455,510,550), cells=(str(i),'新设备建设项目','100','90'))
                       for i in range(6,13))
    if too_large:
        units = tuple(replace(u, raw_text=u.raw_text+'研'*1600) if u == units[0] else u for u in units)
    assert enrich(units).candidates == ()


def test_whole_project_context_is_refused_when_the_budget_cannot_fit_it():
    units = documents()
    parsed = n.NarrativeParseResult(units[0].source_id, 'a'*64, 'zh', units, page_count=2,pages_read=2)
    result = n.select_narrative_evidence(parsed, title='招股说明书', existing_kind='prospectus',max_selected=3)
    assert result.evidence_spans == ()


def test_two_equally_near_project_tables_do_not_guess_an_association():
    units = documents()
    second = tuple(replace(u, unit_id=u.unit_id+'-second',
                           coordinates=replace(u.coordinates, table_index=1))
                   for u in units if u.unit_kind == 'pdf_table_row')
    assert enrich((*units, *second)).candidates == ()
