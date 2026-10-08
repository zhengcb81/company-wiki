"""Fiscal labels must come from provider facts, never the requested year."""

import pytest


@pytest.mark.parametrize("report_date,fye,form,expected", [
    ("2025-09-30", "0630", "10-Q", (2026, "Q1")),
    ("2026-03-31", "0630", "10-Q/A", (2026, "Q3")),
    ("2025-09-30", "1231", "10-Q", (2025, "Q3")),
    ("2025-06-30", "0630", "10-K", (2025, "FY")),
    ("2025-12-27", "0926", "10-Q", (2026, "Q1")),
    ("2026-02-02", "0131", "10-K", (2026, "FY")),
])
def test_sec_cross_calendar_and_week_based_candidate_periods(report_date, fye, form, expected):
    from company_wiki.source_catalog.dayu_fiscal_metadata import sec_period
    assert sec_period(report_date, fye, form) == expected


@pytest.mark.parametrize("report_date,fye,form", [
    (None, "1231", "10-K"), ("2025-12-31", None, "10-K"),
    ("2025-05-12", "1231", "10-Q"), ("2025-12-31", "bogus", "10-K"),
    ("2025-12-31", "1231", "6-K"), ("2025-09-30", "1231", "10-K"),
])
def test_unproved_sec_period_is_explicit(report_date, fye, form):
    from company_wiki.source_catalog.dayu_fiscal_metadata import sec_period, FiscalMetadataError
    with pytest.raises(FiscalMetadataError):
        sec_period(report_date, fye, form)


@pytest.mark.parametrize("title,year", [
    ("2025年年度報告", 2025), ("二零二五年中期報告", 2025),
    ("二〇二六年第一季報告", 2026), ("２０２５年年報", 2025),
])
def test_hk_title_year_proves_sdk_label(title, year):
    from company_wiki.source_catalog.dayu_fiscal_metadata import hk_title_year
    assert hk_title_year(title, year)["year"] == year


@pytest.mark.parametrize("title,year", [
    ("年度報告", 2026), ("2024年年度報告", 2025),
    ("2024/2025年報", 2024), ("2024至2025年報", 2025),
])
def test_hk_missing_ambiguous_or_mismatched_year_is_not_filing_year_fallback(title, year):
    from company_wiki.source_catalog.dayu_fiscal_metadata import hk_title_year, FiscalMetadataError
    with pytest.raises(FiscalMetadataError):
        hk_title_year(title, year)


def _html(year="2026", period="Q1", end="2025-09-30", cik="0000000123"):
    return f'''<html><body><ix:nonNumeric name="dei:DocumentFiscalYearFocus">{year}</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">{period}</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate">{end}</ix:nonNumeric>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">{cik}</ix:nonNumeric></body></html>'''.encode()


def test_sec_primary_bytes_confirm_candidate_identity_year_period_and_end():
    from company_wiki.source_catalog.dayu_fiscal_metadata import verify_sec_primary
    proof = verify_sec_primary(_html(), cik="123", year=2026, period="Q1", report_date="2025-09-30")
    assert proof["fiscal_year"] == 2026
    assert proof["cik"] == "123"


@pytest.mark.parametrize("end,transform", [
    ("September 30 , 2025", "ixt:date-monthname-day-year-en"),
    ("Sep. 30th, 25", "ixt:date-monthname-day-year-en"),
    ("30 September 2025", "ixt:date-day-monthname-year-en"),
])
def test_sec_primary_declared_inline_date_transform(end, transform):
    from company_wiki.source_catalog.dayu_fiscal_metadata import verify_sec_primary
    data = _html(end=end).replace(b'name="dei:DocumentPeriodEndDate"',
        f'name="dei:DocumentPeriodEndDate" format="{transform}"'.encode())
    proof = verify_sec_primary(data, cik="123", year=2026, period="Q1", report_date="2025-09-30")
    assert proof["report_date"] == "2025-09-30"
    assert proof["date_observations"] == [{"text": end, "format": transform,
                                          "normalized": "2025-09-30"}]


@pytest.mark.parametrize("end,transform", [
    ("September 31, 2025", "ixt:date-monthname-day-year-en"),
    ("September 30, 2025", "unknown:date-format"),
    ("September 30, 2025", ""),
    ("October 30, 2025", "ixt:date-monthname-day-year-en"),
])
def test_date_normalization_does_not_weaken_primary_period(end, transform):
    from company_wiki.source_catalog.dayu_fiscal_metadata import verify_sec_primary, FiscalMetadataError
    data = _html(end=end).replace(b'name="dei:DocumentPeriodEndDate"',
        f'name="dei:DocumentPeriodEndDate" format="{transform}"'.encode())
    with pytest.raises(FiscalMetadataError):
        verify_sec_primary(data, cik="123", year=2026, period="Q1", report_date="2025-09-30")


@pytest.mark.parametrize("data", [
    _html(year="2025"), _html(period="Q2"), _html(cik="999"),
    _html(end="2025-12-31"), b"<html>no fiscal metadata</html>",
    _html()+b'<ix:nonNumeric name="dei:DocumentFiscalYearFocus">2025</ix:nonNumeric>',
])
def test_valid_hash_does_not_make_wrong_sec_fiscal_or_identity_fields_true(data):
    from company_wiki.source_catalog.dayu_fiscal_metadata import verify_sec_primary, FiscalMetadataError
    with pytest.raises(FiscalMetadataError):
        verify_sec_primary(data, cik="123", year=2026, period="Q1", report_date="2025-09-30")
