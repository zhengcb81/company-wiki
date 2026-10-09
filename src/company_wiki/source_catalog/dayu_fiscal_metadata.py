"""Fiscal evidence for CWP's Dayu SDK bridge; no request-derived facts."""

from __future__ import annotations

import calendar
from datetime import date
import re
import unicodedata
from typing import Any


class FiscalMetadataError(ValueError):
    """Provider metadata cannot prove the requested fiscal identity."""

    error_code = "fiscal_period_unresolved"


def sec_period(report_date: str | None, fiscal_year_end: str | None, form: str) -> tuple[int, str]:
    """Infer a candidate label, subsequently required to match primary DEI.

    SEC submissions' reportDate is a calendar date, not a fiscal year. The
    closest quarterly end within eight days covers month-end and 52-week
    calendars. Annual forms must match Q4. This remains a candidate inference:
    DEI in the downloaded original confirms label/end/CIK before staging.
    """
    if not isinstance(fiscal_year_end, str) or not re.fullmatch(r"\d{4}", fiscal_year_end):
        raise FiscalMetadataError("SEC fiscal year end is missing or invalid")
    try:
        actual = date.fromisoformat(report_date or "")
        month, day = int(fiscal_year_end[:2]), int(fiscal_year_end[2:])
        date(2000, month, day)
    except (ValueError, TypeError) as exc:
        raise FiscalMetadataError("SEC report date or fiscal year end is invalid") from exc
    normalized = form.upper().removesuffix("/A")
    if normalized not in {"10-K", "20-F", "10-Q"}:
        raise FiscalMetadataError("SEC form has no supported fiscal-period evidence")
    matches = []
    for year in range(actual.year - 1, actual.year + 2):
        for quarter in range(1, 5):
            index = year * 12 + month - 1 - (4 - quarter) * 3
            end_year, zero_month = divmod(index, 12)
            end_month = zero_month + 1
            expected = date(end_year, end_month, calendar.monthrange(end_year, end_month)[1])
            if abs((actual - expected).days) <= 8:
                if normalized == "10-Q" and quarter < 4:
                    matches.append((year, f"Q{quarter}"))
                elif normalized in {"10-K", "20-F"} and quarter == 4:
                    matches.append((year, "FY"))
    if len(matches) != 1:
        raise FiscalMetadataError("SEC report date does not identify one fiscal period")
    return matches[0]


def hk_title_year(title: str, sdk_year: int) -> dict[str, Any]:
    text = unicodedata.normalize("NFKC", title)
    text = text.translate(str.maketrans("零〇一二三四五六七八九", "00123456789"))
    years = {int(value) for value in re.findall(r"(?<!\d)(?:19|20|21)\d{2}(?!\d)", text)}
    if years != {sdk_year}:
        raise FiscalMetadataError("HK title does not prove one matching fiscal year")
    return {"kind": "explicit_title_year", "title": title, "year": sdk_year}


def _inline_date(text: str, transform: str) -> str:
    """Closed subset of XBRL TR4/5 date transforms; never guess date order.

    https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/
    REC-2022-02-16/inlineXBRL-transformationRegistry-REC-2022-02-16.html
    Unsupported declared transforms remain an explicit extraction gap.
    """
    try:
        if not transform:
            return date.fromisoformat(text).isoformat()
        name = transform.split(":")[-1]
        months = {value.lower(): number for number in range(1, 13)
                  for value in (calendar.month_name[number], calendar.month_abbr[number])}
        month = "(" + "|".join(sorted(months, key=len, reverse=True)) + ")"
        day, year = r"([0-9]{1,2})", r"([0-9]{4}|[0-9]{1,2})"
        patterns = {
            "date-monthname-day-year-en": month + r"[^0-9]+" + day + r"[^0-9]+" + year,
            "datemonthdayyearen": month + r"[^0-9]+" + day + r"[^0-9]+" + year,
            "date-day-monthname-year-en": day + r"[^0-9]+" + month + r"[^0-9]+" + year,
        }
        match = re.fullmatch(patterns.get(name, r"(?!)"), text, re.IGNORECASE)
        if not match:
            raise ValueError("unsupported or invalid inline date")
        first, second, last = match.groups()
        m, d = (months[first.lower()], int(second)) if name in {"date-monthname-day-year-en", "datemonthdayyearen"} \
            else (months[second.lower()], int(first))
        y = int(last) + (2000 if len(last) < 4 else 0)
        return date(y, m, d).isoformat()
    except (ValueError, TypeError) as exc:
        raise FiscalMetadataError("SEC primary inline date cannot be normalized") from exc


def _sec_raw_observations(data: bytes):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "html.parser")
    fields = ("documentfiscalyearfocus", "documentfiscalperiodfocus",
              "documentperiodenddate", "entitycentralindexkey", "documenttype")
    observed: dict[str, set[str]] = {key: set() for key in fields}
    dates = []
    for tag in soup.find_all(attrs={"name": True}):
        if not str(tag.name).lower().startswith("ix:"):
            continue
        field = str(tag.get("name", "")).split(":")[-1].lower()
        if field not in observed:
            continue
        value = tag.get_text(" ", strip=True)
        if field == "documentperiodenddate":
            observation = {"text": value, "format": str(tag.get("format", ""))}
            if observation not in dates:
                dates.append(observation)
        if field == "entitycentralindexkey":
            if not value.isdigit():
                raise FiscalMetadataError("SEC primary has invalid CIK")
            value = str(int(value))
        observed[field].add(value)
    titles = {tag.get_text(" ", strip=True) for tag in soup.select("head title")}
    title = next(iter(titles)) if len(titles) == 1 else None
    if not title or len(title) > 2048:
        title = None
    return observed, dates, title


def _normalize_sec_dates(dates):
    return [{**item, "normalized": _inline_date(item["text"], item["format"])}
            for item in dates]


def _sec_primary_observations(data: bytes):
    """Compatibility for the four-field SEC candidate validator."""
    observed, dates, _title = _sec_raw_observations(data)
    dates = _normalize_sec_dates(dates)
    observed["documentperiodenddate"] = {item["normalized"] for item in dates}
    return observed, dates


def extract_sec_scope(data: bytes) -> dict[str, Any]:
    """Actual issuer/year/period/form prove relevance before unrelated date parsing.

    Unreadable, missing or conflicting scope never proves absence. Cache year,
    filename, request labels and timestamps do not participate in this proof.
    """
    observed, dates, title = _sec_raw_observations(data)
    fields = set(observed) - {"documentperiodenddate"}
    if any(len(observed[key]) != 1 for key in fields):
        raise FiscalMetadataError("SEC primary DEI scope is missing or ambiguous")
    values = {key: next(iter(observed[key])) for key in fields}
    year = values["documentfiscalyearfocus"]
    period = values["documentfiscalperiodfocus"]
    form = re.sub(r"\s+", "", values["documenttype"]).upper()
    if not re.fullmatch(r"(?:19|20|21)\d{2}", year) or period not in {"Q1", "Q2", "Q3", "FY"} or form not in {"10-Q", "10-Q/A", "10-K", "10-K/A", "20-F", "20-F/A"}:
        raise FiscalMetadataError("SEC primary fiscal identity is unsupported")
    if (form.startswith("10-Q")) != (period != "FY"):
        raise FiscalMetadataError("SEC primary form and period conflict")
    return {"kind":"primary_dei", "cik":values["entitycentralindexkey"],
            "fiscal_year":int(year), "fiscal_period":period, "form_type":form,
            "date_observations":dates, "title":title}


def complete_sec_primary(scope: dict[str, Any]) -> dict[str, Any]:
    dates = _normalize_sec_dates(scope["date_observations"])
    ends = {item["normalized"] for item in dates}
    if len(ends) != 1:
        raise FiscalMetadataError("SEC primary period end is missing or ambiguous")
    return {**scope, "report_date":next(iter(ends)), "date_observations":dates}


def extract_sec_primary(data: bytes) -> dict[str, Any]:
    """Extract unambiguous source facts; request labels are never inputs."""
    return complete_sec_primary(extract_sec_scope(data))


def verify_sec_primary(
    data: bytes, *, cik: str, year: int, period: str, report_date: str,
) -> dict[str, Any]:
    """Require unambiguous DEI values in the actual HTML primary document."""
    observed, dates = _sec_primary_observations(data)
    fields = {"documentfiscalyearfocus":str(year), "documentfiscalperiodfocus":period,
              "documentperiodenddate":report_date, "entitycentralindexkey":str(int(cik))}
    if any(observed[key] != {expected} for key, expected in fields.items()):
        raise FiscalMetadataError("SEC primary DEI conflicts with candidate or is missing")
    return {"kind":"primary_dei", "cik":fields["entitycentralindexkey"],
            "fiscal_year":year, "fiscal_period":period, "report_date":report_date,
            "date_observations":dates}
