from pathlib import Path

root = Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
src = root / 'src/cninfo_api.py'
text = src.read_text(encoding='utf-8')
text = text.replace('from datetime import date, datetime, timezone',
                    'from datetime import date, datetime, timedelta, timezone')
text = text.replace('filing_date: str  # canonical YYYY-MM-DD UTC interpretation of epoch ms',
                    'filing_date: str  # disclosure calendar date in China (UTC+08:00)')
text = text.replace('# canonical filing_date: UTC date from epoch milliseconds',
                    '# Epoch milliseconds are UTC instants; publication dates and the\n'
                    '        # official detail query use China disclosure time (UTC+08:00).')
text = text.replace('tz=timezone.utc)', 'tz=timezone(timedelta(hours=8)))')
src.write_text(text, encoding='utf-8')

test = root / 'tests/unit/test_cninfo_api.py'
text = test.read_text(encoding='utf-8').replace(
    '# canonical filing_date UTC interpretation of epoch ms',
    '# Official China disclosure date from the captured epoch milliseconds')
text = text.replace('assert parsed.filing_date == "2025-03-24"',
                    'assert parsed.filing_date == "2025-03-25"')
test.write_text(text, encoding='utf-8')

for relative in ('tests/unit/test_company_wiki_adapter.py',
                 'tests/unit/test_g4_latest_discovery.py',
                 'tests/unit/test_cninfo_api_fixture_contract.py'):
    test = root / relative
    text = test.read_text(encoding='utf-8').replace('tz=_dt.timezone.utc)',
        'tz=_dt.timezone(_dt.timedelta(hours=8)))')
    if 'test_company_wiki_adapter' in relative:
        text = text.replace('UTC 2025-03-24 16:00 → date 2025-03-24',
                            '2025-03-24T16:00Z → China 2025-03-25')
        text = text.replace('assert candidate.filing_date == "2025-03-24"',
                            'assert candidate.filing_date == "2025-03-25"')
    if 'fixture_contract' in relative:
        text = text.replace('canonical filing_date (UTC interpretation) is 2025-03-24.',
                            'official China disclosure date is 2025-03-25.')
        text = text.replace('test_real_fixture_fy2024_full_canonical_filing_date_is_2025_03_24_utc',
                            'test_real_fixture_fy2024_full_china_disclosure_date_is_2025_03_25')
        text = text.replace('assert canonical_date == "2025-03-24"',
                            'assert canonical_date == "2025-03-25"')
    if 'g4_latest' in relative:
        text = text.replace('test_latest_cutoff_uses_utc_filing_date_at_day_boundary',
                            'test_latest_cutoff_uses_china_filing_date_at_day_boundary')
        text = text.replace('ms=1780358399000,  # 2026-06-01T23:59:59Z',
                            'ms=1780329599000,  # China 2026-06-01T23:59:59+08:00')
        text = text.replace('ms=1780358400000,  # 2026-06-02T00:00:00Z',
                            'ms=1780329600000,  # China 2026-06-02T00:00:00+08:00')
        text = text.replace('test_announcement_time_is_canonicalised_in_utc_across_midnight',
                            'test_announcement_time_uses_china_disclosure_date')
    test.write_text(text, encoding='utf-8')
print('China disclosure timezone corrected; epoch instants and fixture payloads untouched')
