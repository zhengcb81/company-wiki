"""A document's own periodic cover outranks historical issuance vocabulary."""
import pytest
from fixtures.document_understanding_profiles import builders as b
from company_wiki.document_understanding.profiles import route_document


@pytest.mark.parametrize('cover,family', [
    ('Annual Report 2024 年報', 'annual'), ('2025 中期報告 Interim Report', 'interim'),
])
@pytest.mark.parametrize('historical', ['所得款項用途', '全球發售', 'Use of proceeds'])
def test_actual_periodic_cover_keeps_its_purpose_with_issuance_history(cover, family, historical):
    observed = b.observation([
        b.unit('cover', 0, cover, kind='heading', page=1),
        b.unit('contents', 1, '目錄 Contents', kind='heading', page=2),
        b.unit('business', 2, '業務回顧及展望', kind='heading', page=12),
        b.unit('historic', 3, historical, kind='heading', page=30),
        b.unit('history', 4, 'Our previous issue proceeds funded the business expansion.', page=30),
    ], declared_kind='unknown', regime='hkex')
    result = route_document(observed)
    assert result['family'] == family
    assert result['profile_id'] == 'hk_periodic'


def test_false_periodic_metadata_cannot_erase_an_actual_offering_cover():
    observed = b.observation([
        b.unit('cover', 0, '全球發售 Global Offering', kind='heading', page=1),
        b.unit('contents', 1, '目錄', kind='heading', page=2),
        b.unit('business', 2, '業務', kind='heading', page=20),
        b.unit('use', 3, '所得款項用途', kind='heading', page=30),
    ], title='Annual Report', declared_kind='annual_report', regime='hkex')
    result = route_document(observed)
    assert result['family'] == 'prospectus'
    assert any(row['code'] == 'DECLARED_KIND_CONFLICT' for row in result['reasons'])


def test_offering_signal_cannot_cite_unrelated_cover_as_its_wording():
    observed = b.observation([
        b.unit('cover', 0, 'Annual Report 2024 年報', kind='heading', page=1),
        b.unit('contents', 1, '目錄', kind='heading', page=2),
        b.unit('business', 2, '業務回顧及展望', kind='heading', page=12),
        b.unit('historic', 3, '全球發售', kind='heading', page=30),
    ], regime='hkex')
    from company_wiki.document_understanding.profiles.observation import parse_observation
    from company_wiki.document_understanding.profiles.signals import detect_signals
    bag = detect_signals(parse_observation(observed))
    assert not any(signal.code == 'COVER_HEADING' and '全球发售' in signal.detail
                   and 'cover' in signal.unit_ids for signal in bag.all)


@pytest.mark.parametrize('cover,family', [('2025年年度报告', 'annual'),
    ('2026年半年度报告', 'interim'), ('2026年第一季度报告', 'quarterly')])
@pytest.mark.parametrize('historical', ['首次公开发行招股说明书', '可转换公司债券募集说明书'])
def test_cn_periodic_cover_also_survives_historical_issuance_sections(cover, family, historical):
    observed = b.observation([
        b.unit('cover', 0, cover, kind='heading', page=1),
        b.unit('contents', 1, '目录', kind='heading', page=2),
        b.unit('business', 2, '第三节 管理层讨论与分析', kind='heading', page=8),
        b.unit('history', 3, historical, kind='heading', page=30),
        b.unit('proceeds', 4, '募集资金运用', kind='heading', page=31),
    ], regime='cn_exchange')
    result = route_document(observed)
    assert result['family'] == family
