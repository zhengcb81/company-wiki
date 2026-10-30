"""Source-side framing, independent of company names and model output."""
import pytest

from company_wiki.document_understanding.assertion_frames import source_assertion_frames


@pytest.mark.parametrize('source,needle', [
    ('甲方积极开发新市场，持续完善服务网络。', '积极开发'),
    ('團隊正在開發新渠道，持續完善服務。', '正在開發'),
    ('The supplier is actively expanding its sales network.', 'expanding'),
    ('The operator continues to improve its distribution.', 'continues'),
])
def test_observed_ongoing_activity_is_not_a_future_plan(source, needle):
    from company_wiki.document_normalization.text_matching import matching_reading_text

    frame = next(frame for frame in source_assertion_frames(source) if matching_reading_text(needle) in frame.matching_text)
    assert frame.ongoing_activity and not frame.future_marker


@pytest.mark.parametrize('source', [
    '甲方将积极开发新市场。',
    '公司计划持续完善服务网络。',
    'The supplier plans to continue expanding its network.',
    'The operator will actively improve its distribution.',
])
def test_future_marker_prevents_promoting_intention_to_observed_ongoing(source):
    frames = source_assertion_frames(source)
    assert any(frame.future_marker for frame in frames)
    assert not any(frame.ongoing_activity for frame in frames)


def test_reporting_scope_follows_explicit_coordination_but_not_another_statement():
    frames = source_assertion_frames(
        '据控股企业提供的信息，甲方与乙方已经建立联系，并希望开展合作，公司目前没有该产品。'
    )
    wish = next(frame for frame in frames if '希望' in frame.matching_text)
    assert wish.reporting_prefix == '据控股企业提供的信息'
    assert wish.reporting_inherited
    independent = next(frame for frame in frames if '没有该产品' in frame.matching_text)
    assert independent.reporting_prefix is None


def test_reporting_scope_never_crosses_sentence_or_qa_boundary():
    frames = source_assertion_frames('根据行业报道，客户订单增长。公司正在完善渠道；并计划明年扩展。')
    assert frames[0].reporting_prefix == '根据行业报道'
    assert all(frame.reporting_prefix is None for frame in frames[1:])


def test_english_information_source_and_explicit_continuation_remain_attributed():
    frames = source_assertion_frames('According to the parent company, Alpha contacted Beta, and hopes to cooperate.')
    assert len(frames) == 2
    assert frames[1].reporting_prefix == 'According to the parent company'
    assert frames[1].reporting_inherited and frames[1].future_marker


def test_project_capacity_specification_is_distinct_from_start_and_actual_production():
    frames = source_assertion_frames('公司已启动新工厂建设项目，该项目包含年产能500吨，建成后将提供保障。现有产能100吨已投产。')
    spec = next(frame for frame in frames if '500' in frame.matching_text)
    assert spec.quantity_basis == 'project_capacity_specification'
    assert spec.project_condition is not None
    existing = next(frame for frame in frames if '100' in frame.matching_text)
    assert existing.quantity_basis == 'existing_capacity'
    assert existing.project_condition is None


def test_english_project_specification_is_not_a_shipment_quantity():
    frames = source_assertion_frames('We started construction of the project, with capacity of 450 tonnes per year, following completion it will support growth.')
    spec = next(frame for frame in frames if '450' in frame.matching_text)
    assert spec.quantity_basis == 'project_capacity_specification'
    assert spec.project_condition is not None


def test_framework_text_does_not_invent_a_reporter_or_an_operational_stage():
    frame, = source_assertion_frames('客户根据需要选择供应商。')
    assert frame.reporting_prefix is None
    assert frame.quantity_basis is None
    assert not frame.ongoing_activity


@pytest.mark.parametrize('source', [
    'According to reports Alpha is expanding its network.',
    'According to the subsidiary it will expand capacity to 500 tonnes.',
])
def test_english_attribution_without_a_delimited_prefix_never_discards_the_statement(source):
    frames = source_assertion_frames(source)
    assert frames and ' '.join(f.matching_text for f in frames) == source.rstrip('.')
    assert all(f.reporting_prefix is None for f in frames)


@pytest.mark.parametrize('source,needle', [
    ('According to the supplier, Alpha contacted Beta, and Gamma is expanding.', 'Gamma'),
    ('据第三方信息，甲方已经建立联系，并乙方正在开发渠道。', '乙方'),
])
def test_explicit_new_subject_after_coordinator_does_not_borrow_reporting_scope(source, needle):
    independent = next(f for f in source_assertion_frames(source) if needle in f.matching_text)
    assert independent.reporting_prefix is None


@pytest.mark.parametrize('source', [
    '请问公司是否正在开发新渠道？',
    'Is the supplier actively expanding its network?',
    '模板：企业正在建设项目，设计产能500吨。',
    'Accounting policy example: the existing capacity of 500 tonnes is depreciated.',
])
def test_questions_and_governing_templates_do_not_assert_operating_state_or_quantity(source):
    frames = source_assertion_frames(source)
    assert frames
    assert all(not f.ongoing_activity and f.quantity_basis is None for f in frames)


@pytest.mark.parametrize('source', [
    '一期项目已经投产，产能500吨。',
    'The first project is commissioned, with capacity of 500 tonnes.',
])
def test_commissioned_project_capacity_keeps_its_existing_stage_across_subjectless_clause(source):
    frame = next(f for f in source_assertion_frames(source) if '500' in f.matching_text)
    assert frame.quantity_basis == 'existing_capacity'
    assert frame.project_condition is None


def test_capacity_or_condition_cannot_come_from_an_unrelated_project_in_the_same_sentence():
    frames = source_assertion_frames(
        '公司启动一期项目，另一个部门产能500吨，二期项目建成后将提供保障。'
    )
    frame = next(f for f in frames if '500' in f.matching_text)
    assert frame.quantity_basis is None and frame.project_condition is None


def test_independent_project_condition_does_not_attach_to_earlier_project_specification():
    frames = source_assertion_frames('一期项目设计产能500吨，二期项目建成后将提供保障。')
    frame = next(f for f in frames if '500' in f.matching_text)
    assert frame.quantity_basis == 'project_capacity_specification'
    assert frame.project_condition is None


def test_traditional_quantity_and_decimal_separators_are_matching_views_not_raw_quotes():
    frames = source_assertion_frames('該項目設計產能約五百噸。現有產能1,500.5噸。')
    assert frames[0].matching_text == '该项目设计产能约五百吨'
    assert frames[0].quantity_basis == 'project_capacity_specification'
    assert frames[1].quantity_basis == 'existing_capacity'
    assert '1,500.5' in frames[1].matching_text


def test_accounting_capacity_word_without_a_quantity_is_not_a_project_specification():
    frames = source_assertion_frames('项目的现有产能折旧按照会计准则计算。')
    assert all(f.quantity_basis is None for f in frames)


def test_negated_ongoing_action_is_not_observed_ongoing_activity():
    frames = source_assertion_frames('公司并未持续开发新渠道。')
    assert not any(f.ongoing_activity for f in frames)


@pytest.mark.parametrize('source', [
    '据第三方信息，甲方已经建立联系，并且希望合作。',
    'According to the supplier, Alpha contacted Beta, and also hopes to cooperate.',
])
def test_subjectless_coordinator_variants_keep_attribution(source):
    frames = source_assertion_frames(source)
    assert frames[-1].reporting_inherited


def test_governing_disclosure_instruction_is_not_a_third_party_report():
    frames = source_assertion_frames('根据需要披露信息，企业正在建设项目，产能500吨。')
    assert all(f.reporting_prefix is None and not f.ongoing_activity and f.quantity_basis is None for f in frames)


def test_an_independent_subject_after_among_them_does_not_inherit_project_stage():
    frames = source_assertion_frames('公司正在建设项目，其中另一部门产能500吨。')
    assert frames[-1].quantity_basis is None


@pytest.mark.parametrize('stage', ['has not been commissioned', 'is not yet commissioned', 'will be commissioned'])
def test_negated_or_future_commissioning_does_not_become_existing_capacity(stage):
    frames = source_assertion_frames(f'The project {stage}, with capacity of 500 tonnes.')
    assert frames[-1].quantity_basis == 'project_capacity_specification'


def test_condition_annotation_does_not_duplicate_the_whole_consequence_per_capacity():
    frames = source_assertion_frames('项目设计产能500吨，建成后将为后续生产保障和长期服务安排提供支持。')
    assert frames[0].project_condition == '建成后'


@pytest.mark.parametrize('source,condition', [
    ('2021年启动配套建设项目，该项目设计产能约360吨/年，项目建成后将提供保障。', '建成后'),
    ('We started construction of a project, with capacity of 360 tonnes, the project after completion will support growth.', 'after completion'),
])
def test_bare_project_completion_refers_back_only_within_active_project_chain(source, condition):
    frames = source_assertion_frames(source)
    spec = next(f for f in frames if '360' in f.matching_text)
    assert spec.quantity_basis == 'project_capacity_specification'
    assert spec.project_condition == condition


@pytest.mark.parametrize('condition_clause', [
    '项目乙建成后将提供保障',
    '另一项目建成后将提供保障',
    'project Beta after completion will support growth',
    'another project after completion will support growth',
])
def test_named_or_independent_project_does_not_supply_completion_condition(condition_clause):
    frames = source_assertion_frames(f'项目设计产能360吨，{condition_clause}。')
    spec = next(f for f in frames if '360' in f.matching_text)
    assert spec.project_condition is None


def test_bare_project_completion_cannot_jump_an_independent_clause():
    frames = source_assertion_frames('项目设计产能360吨，公司正在开发渠道，项目建成后将提供保障。')
    assert frames[0].project_condition is None
