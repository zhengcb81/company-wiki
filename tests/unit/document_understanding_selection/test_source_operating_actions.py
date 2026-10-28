"""Direct product actions retain source actor, object and future qualifications."""
from dataclasses import replace

import pytest

from company_wiki.document_understanding.operating_states.relations import detect_operating_relations
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_reading import _candidates
from unit.document_understanding_selection.test_reading_native_continuity import source_case


def observed(text):
    return detect_operating_relations({'schema_version': 'du4-operating-observation/1',
        'unit_id': 'u', 'units': {'u': {'text': text, 'parent_id': 'source',
        'role': 'management', 'kind': 'paragraph', 'locator': 'native:0'}}},
        work_budget=WorkBudget(1_000_000))['relations']


@pytest.mark.parametrize('text,modality,polarity', [
    ('We launched a new software platform for enterprise customers.', 'actual', 'positive'),
    ('The company has launched the Orion platform.', 'actual', 'positive'),
    ('We will launch a new software platform.', 'planned', 'positive'),
    ('We may launch the Orion platform.', 'conditional', 'positive'),
    ('We did not launch the Orion platform.', 'actual', 'negative'),
])
def test_direct_launch_binds_its_observed_product_and_modifiers(text, modality, polarity):
    rows = [row for row in observed(text) if row['activity'] == 'product_launch']
    assert rows
    assert {(row['modality'], row['polarity'], row['attribution']) for row in rows} == {
        (modality, polarity, 'issuer')}
    assert all(row['object_refs'] for row in rows)
    assert all('platform' in text[ref['char_start']:ref['char_end']]
               for row in rows for ref in row['object_refs'])


@pytest.mark.parametrize('text', [
    'Our launch cost increased by 8%.', 'Product launch event: Orion platform.',
    'We discussed the launch of a new software platform.',
    'We launched it.', 'Launched a new software platform.',
])
def test_launch_mentions_do_not_fabricate_issuer_product_progress(text):
    assert not [row for row in observed(text) if row['activity'] == 'product_launch'
                and row['attribution'] == 'issuer' and row['polarity'] == 'positive'
                and row['modality'] == 'actual']


@pytest.mark.parametrize('text', ['Our supplier launched the Orion platform.',
                                 'The parent has launched a new software platform.'])
def test_explicit_other_party_launch_is_not_donated_to_issuer(text):
    rows = [row for row in observed(text) if row['activity'] == 'product_launch']
    assert rows and all(row['attribution'] != 'issuer' for row in rows)


@pytest.mark.parametrize('texts', [
    ['本公司用于材料切割的Orion设备即将发往海外', '客户产线验证。'],
    ['公司用於封裝切割的Vega Matrix 即將發往國內', '客戶產線驗證。'],
])
def test_planned_destination_keeps_product_subject_and_qualification_purpose(texts):
    text = ''.join(texts)
    rows = observed(text)
    shipment = [row for row in rows if row['activity'] == 'shipment']
    assert shipment
    assert all(row['attribution'] == 'issuer' and row['modality'] == 'planned'
               and row['object_refs'] for row in shipment)
    assert not [row for row in rows if row['activity'] == 'qualification'
                and row['modality'] == 'actual' and row['polarity'] == 'positive']
    parsed, pipeline = source_case(texts)
    original = [(u.unit_id, u.raw_text, u.coordinates) for u in parsed.units]
    candidates, metadata, packages, complete, withheld = _candidates(parsed, pipeline)
    assert candidates and complete and not withheld and len(packages) == 1
    assert any(value.get('value_band') == 'meaningful_fact' for value in metadata.values())
    assert any('operating_plan' in candidate.reasons for candidate in candidates)
    assert [(u.unit_id, u.raw_text, u.coordinates) for u in parsed.units] == original


def test_actual_launch_is_meaningful_in_source_projection_without_heading_support():
    parsed, pipeline = source_case(['We launched a new software platform.'])
    parsed = replace(parsed, language='en', units=tuple(replace(u, language='en') for u in parsed.units))
    pipeline['observation']['units'][0]['language'] = 'en'
    candidates, metadata, _, complete, withheld = _candidates(parsed, pipeline)
    assert complete and not withheld and candidates
    assert any(value.get('value_band') == 'meaningful_fact' for value in metadata.values())


@pytest.mark.parametrize('text,modality,polarity', [
    ('公司计划将Orion设备发往国内客户产线验证。', 'planned', 'positive'),
    ('公司并未将Orion设备发往国内客户产线验证。', 'actual', 'negative'),
    ('公司Orion设备尚未发往国内客户产线验证。', 'actual', 'negative'),
])
def test_shipment_object_between_actor_modifier_and_predicate_is_source_bound(text, modality, polarity):
    rows = [row for row in observed(text) if row['activity'] == 'shipment']
    assert rows and all((r['modality'], r['polarity']) == (modality, polarity) for r in rows)
    assert all(text[ref['char_start']:ref['char_end']] == 'Orion设备'
               for row in rows for ref in row['object_refs'])


@pytest.mark.parametrize('text', ['公司即将发往国内客户产线验证。',
                                 'Orion设备即将发往国内客户产线验证。',
                                 '公司用于测试的费用即将发往国内客户产线验证。'])
def test_shipment_without_observed_actor_and_product_is_not_issuer_progress(text):
    assert not [row for row in observed(text) if row['activity'] == 'shipment'
                and row['attribution'] == 'issuer' and row['polarity'] == 'positive']


@pytest.mark.parametrize('text', ['We launched a free beta research platform.',
                                 'The company has launched a free platform; it generates no revenue.'])
def test_launch_does_not_invent_commercialization_or_revenue(text):
    rows = observed(text)
    assert any(row['activity'] == 'product_launch' for row in rows)
    assert not any(row['activity'] == 'commercialization' for row in rows)


@pytest.mark.parametrize('text,expected_launches', [
    ('We launched a marketing campaign and shipped Orion devices to customers.', 0),
    ('We launched it and shipped Orion devices to customers.', 0),
    ('We launched the Orion platform and shipped Vega devices to customers.', 1),
])
def test_only_valid_accepted_event_range_can_hide_later_candidates(text, expected_launches):
    rows = observed(text)
    assert len([r for r in rows if r['activity'] == 'product_launch']) == expected_launches
    shipments = [r for r in rows if r['activity'] == 'shipment']
    assert shipments
    assert all('Orion platform' not in text[ref['char_start']:ref['char_end']]
               for r in shipments for ref in r['object_refs'])


@pytest.mark.parametrize('text,activity,modality', [
    ('去年公司已将Orion设备发往国内客户验证。', 'shipment', 'actual'),
    ('报告期内公司已将Orion设备发往国内客户验证。', 'shipment', 'actual'),
    ('去年本公司將Orion設備發往國內客戶驗證。', 'shipment', 'actual'),
    ('下月公司将Orion设备发往国内客户验证。', 'shipment', 'planned'),
    ('公司将在下月将Orion设备发往国内客户验证。', 'shipment', 'planned'),
    ('公司將在下月將Orion設備發往國內客戶驗證。', 'shipment', 'planned'),
    ('Last quarter we launched a new software platform.', 'product_launch', 'actual'),
    ('During the period we launched a new software platform.', 'product_launch', 'actual'),
    ('Next year the company will launch a new software platform.', 'product_launch', 'planned'),
])
def test_proven_temporal_frame_is_preserved_separately_from_actor_and_object(text, activity, modality):
    rows = [row for row in observed(text) if row['activity'] == activity]
    assert rows and all(row['modality'] == modality for row in rows)
    assert all(text[ref['char_start']:ref['char_end']] not in {'去年', 'Last quarter', '下月'}
               for row in rows for ref in row['actor_refs'])
    if activity == 'shipment':
        assert all(not text[ref['char_start']:ref['char_end']].startswith(('将', '將', '在下月'))
                   for row in rows for ref in row['object_refs'])


def test_bare_disposal_marker_does_not_assert_time_or_split_a_product_name():
    bare = [r for r in observed('公司将Orion设备发往国内客户验证。') if r['activity'] == 'shipment']
    assert bare and all(r['modality'] == 'uncertain' for r in bare)
    assert all(ref['char_start'] == 3 for r in bare for ref in r['object_refs'])
    text = '公司将星设备即将发往国内客户验证。'
    named = [r for r in observed(text) if r['activity'] == 'shipment']
    assert named and all(text[ref['char_start']:ref['char_end']] == '将星设备'
                         for r in named for ref in r['object_refs'])


def test_arbitrary_discussion_lead_is_not_a_proven_temporal_frame():
    text = 'During the meeting we discussed whether the company launched a new platform.'
    assert not [r for r in observed(text) if r['activity'] == 'product_launch']


@pytest.mark.parametrize('scope', ['量产', '安全', '注册'])
def test_qualification_class_does_not_replace_the_previous_product_subject(scope):
    text = f'该设备已完成客户验证，但尚未获得{scope}认证。'
    rows = observed(text)
    restrictions = [r for r in rows if r['polarity'] == 'negative' and r['stage'] == 'not_yet']
    assert restrictions
    assert any(r['polarity'] == 'positive' and r['stage'] == 'current' for r in rows)
    assert all([text[ref['char_start']:ref['char_end']] for ref in r['object_refs']] == ['设备']
               for r in restrictions)
    assert all(scope in [text[ref['char_start']:ref['char_end']] for ref in r['qualifier_refs']]
               for r in restrictions)


@pytest.mark.parametrize('next_subject,object_text,attribution', [
    ('乙设备', '乙设备', 'unknown'), ('供应商', None, 'other'),
])
def test_new_explicit_qualification_subject_never_borrows_previous_product(next_subject, object_text, attribution):
    text = f'甲设备已完成客户验证，但{next_subject}尚未获得量产认证。'
    restrictions = [r for r in observed(text) if r['polarity'] == 'negative' and r['stage'] == 'not_yet']
    assert restrictions and all(r['attribution'] == attribution for r in restrictions)
    objects = [text[ref['char_start']:ref['char_end']] for r in restrictions for ref in r['object_refs']]
    assert '甲设备' not in objects and ('乙设备' in objects if object_text else not objects)


@pytest.mark.parametrize('text,entity', [
    ('甲设备已完成客户验证，但尚未完成乙设备的认证。', '乙设备'),
    ('甲设备已完成客户验证，但尚未获得Vega模块认证。', 'Vega模块'),
    ('甲設備已完成客戶驗證，但尚未完成乙設備的認證。', '乙設備'),
])
def test_explicit_product_inside_qualification_slot_remains_an_entity(text, entity):
    restrictions = [r for r in observed(text) if r['polarity'] == 'negative' and r['stage'] == 'not_yet']
    assert restrictions
    assert all([text[ref['char_start']:ref['char_end']] for ref in r['object_refs']] == [entity]
               for r in restrictions)
    assert all(entity not in [text[ref['char_start']:ref['char_end']] for ref in r['qualifier_refs']]
               for r in restrictions)
