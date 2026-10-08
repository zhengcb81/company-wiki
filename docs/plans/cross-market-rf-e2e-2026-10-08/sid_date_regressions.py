from pathlib import Path

root = Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
test = root / 'tests/unit/test_cninfo_api.py'
extra = '''

def test_official_china_disclosure_date_uses_exchange_timezone():
    from src.cninfo_api import CninfoAnnouncementClient
    raw = dict(_load_real_payload()["announcements"][1])
    raw.update(announcementId="1225482884", secCode="688012",
               announcementTitle="2026年半年度报告",
               announcementTime=1787155200000,
               adjunctUrl="finalpage/2026-08-20/1225482884.PDF")
    parsed = CninfoAnnouncementClient()._parse_announcement(raw, stock_code="688012")
    assert parsed.filing_date == "2026-08-20"
    assert parsed.announcement_time_ms == 1787155200000
    assert "announcementTime=2026-08-20" in parsed.detail_url


def test_latest_cannot_include_tomorrow_china_report_via_utc_date():
    from src.cninfo_api import CninfoAnnouncementClient
    raw = dict(_load_real_payload()["announcements"][1])
    raw.update(announcementId="1225482884", secCode="688012",
               announcementTitle="2026年半年度报告",
               announcementTime=1787155200000,
               adjunctUrl="finalpage/2026-08-20/1225482884.PDF")
    payload = {"totalRecordNum": 1, "totalpages": 1, "hasMore": False,
               "announcements": [raw]}
    records, _meta = CninfoAnnouncementClient()._filter_latest_page(
        payload, stock_code="688012", document_kind="semi_annual_report",
        cutoff="2026-08-19", fiscal_period="H1", form_type=None,
    )
    assert records == []
'''
test.write_text(test.read_text(encoding='utf-8') + extra, encoding='utf-8')
