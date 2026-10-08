from pathlib import Path

test = Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite/tests/unit/test_cninfo_api_fixture_contract.py')
text = test.read_text(encoding='utf-8').replace('tz=_dt.timezone.utc',
    'tz=_dt.timezone(_dt.timedelta(hours=8))')
text = text.replace('API returns announcementTime as epoch milliseconds (UTC canonical).',
    'UTC epoch instant converts to the official China disclosure calendar date.')
test.write_text(text, encoding='utf-8')
