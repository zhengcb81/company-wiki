"""Public SDK orchestration owned by CWP; Dayu remains an external dependency."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
import re
from typing import Any, Callable

from .dayu_fiscal_metadata import FiscalMetadataError, hk_title_year, sec_period
from .resolver import SourceRequest


class DayuBridgeError(ValueError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def discovery_window(request: SourceRequest) -> tuple[date, date]:
    end = date.fromisoformat(request.as_of_date)
    # A fiscal year's first quarter can end in the previous calendar year.
    start_year = request.fiscal_year - 1 if request.fiscal_year else end.year - 2
    return date(start_year, 1, 1), end


def _matches(request: SourceRequest, value: dict[str, Any]) -> bool:
    return (
        value["filing_date"] <= request.as_of_date
        and (request.fiscal_year is None or value["fiscal_year"] == request.fiscal_year)
        and (request.fiscal_period is None or value["fiscal_period"] == request.fiscal_period)
        and (request.provider is None or value["provider"] == request.provider)
        and (request.provider_document_id is None
             or value["provider_document_id"] == request.provider_document_id)
    )


def _current_versions(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select one current revision per fiscal period; accession pins filter first."""
    chosen: dict[tuple[int, str], dict[str, Any]] = {}
    for value in sorted(values, key=lambda v: (
        v["filing_date"], v["amended"], v["provider_document_id"],
    )):
        chosen[value["fiscal_year"], value["fiscal_period"]] = value
    return sorted(chosen.values(), key=lambda v: (v["fiscal_year"], v["fiscal_period"]), reverse=True)


async def discover_sec(
    request: SourceRequest, downloader: Any, *, collect: Callable[..., None],
) -> list[dict[str, Any]]:
    if request.market != "US" or not request.security_id:
        raise DayuBridgeError("invalid_request", "SEC request requires US security identity")
    if request.language and not request.language.lower().startswith("en"):
        raise DayuBridgeError("unsupported_language", "SEC original is not translated")
    allowed = {
        "annual_report": ("10-K", "10-K/A", "20-F", "20-F/A"),
        "quarterly_report": ("10-Q", "10-Q/A"),
    }.get(request.document_kind)
    forms = (request.form_type.upper(),) if request.form_type else allowed
    if not allowed or not forms or any(form not in allowed for form in forms):
        raise DayuBridgeError("unsupported_sec_form", "SEC primary fiscal report capability does not cover this form")
    start, end = discovery_window(request)
    if start > end:
        return []
    cik, company_name, cik10 = await downloader.resolve_company(request.security_id)
    submissions = await downloader.fetch_submissions(cik10)
    if str(int(submissions.get("cik", 0))) != str(int(cik)):
        raise DayuBridgeError("identity_mismatch", "SEC submissions identity differs from ticker mapping")
    records: dict[str, Any] = {}
    filings = submissions.get("filings", {})
    windows = {form: start for form in forms}
    collect(records=records, table=filings.get("recent", {}), form_windows=windows, end_date=end)
    for history in filings.get("files", []):
        if history.get("filingTo", "") < start.isoformat() or history.get("filingFrom", "9999") > end.isoformat():
            continue
        name = history.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", name):
            raise DayuBridgeError("invalid_provider_metadata", "SEC history filename is invalid")
        table = await downloader.fetch_json("https://data.sec.gov/submissions/" + name)
        collect(records=records, table=table, form_windows=windows, end_date=end)
    values = []
    unresolved = []
    for record in records.values():
        if request.provider_document_id and record.accession_number != request.provider_document_id:
            continue
        try:
            year, period = sec_period(record.report_date, submissions.get("fiscalYearEnd"), record.form_type)
        except FiscalMetadataError as exc:
            unresolved.append(exc)
            continue
        value = {
            "candidate_id": "sec:" + record.accession_number,
            "provider": "sec", "provider_document_id": record.accession_number,
            "market": "US", "entity": request.entity,
            "title": f"{company_name} {record.form_type} {record.report_date}",
            "document_kind": request.document_kind, "form_type": record.form_type,
            "filing_date": record.filing_date, "fiscal_year": year, "fiscal_period": period,
            "language": "en", "amended": record.form_type.endswith("/A"),
            "cik": str(int(cik)), "report_date": record.report_date,
            "fiscal_year_basis": {"kind": "submissions_candidate_requires_primary_dei",
                                  "report_date": record.report_date,
                                  "fiscal_year_end": submissions.get("fiscalYearEnd")},
            "sdk_company_profile": {"company_name": company_name, "cik": str(int(cik)),
                                    "ticker": request.security_id},
        }
        if not _matches(request, value):
            continue
        primary = record.primary_document
        accession = record.accession_number.replace("-", "")
        if not primary:
            primary = await downloader.resolve_primary_document(cik, accession, record.form_type)
        files = await downloader.list_filing_files(
            cik, accession, primary, record.form_type, include_xbrl=False,
            include_exhibits=False, include_http_metadata=False,
        )
        descriptor = next((item for item in files if item.name == primary), None)
        if descriptor is None:
            raise DayuBridgeError("primary_missing", "SEC SDK did not return the primary descriptor")
        value.update(source_url=descriptor.source_url, primary_document=primary,
                     remote_size=descriptor.remote_size, etag=descriptor.http_etag,
                     last_modified=descriptor.http_last_modified)
        values.append(value)
    if not values and unresolved:
        raise unresolved[0]
    return _current_versions(values)


def discover_hk(
    request: SourceRequest, client: Any, *, query_type: Callable[..., Any],
) -> list[dict[str, Any]]:
    if request.market != "HK" or not request.security_id:
        raise DayuBridgeError("invalid_request", "HK request requires security identity")
    if request.language and not request.language.lower().startswith("zh"):
        raise DayuBridgeError("unsupported_language", "HK SDK currently discovers Chinese originals only")
    allowed = {"annual_report": ("FY",), "semi_annual_report": ("H1",),
               "quarterly_report": ("Q1", "Q2", "Q3", "Q4")}.get(request.document_kind)
    periods = (request.fiscal_period.upper(),) if request.fiscal_period else allowed
    if not allowed or not periods or any(period not in allowed for period in periods):
        raise DayuBridgeError("unsupported_hk_period", "HK report kind and fiscal period do not match")
    if request.form_type and request.form_type.upper() not in periods:
        raise DayuBridgeError("unsupported_hk_period", "HK form must match its report period")
    start, end = discovery_window(request)
    if start > end:
        return []
    query = query_type(market="HK", normalized_ticker=request.security_id,
                       start_date=start.isoformat(), end_date=end.isoformat(), target_periods=tuple(periods))
    profile = client.resolve_company(query)
    if profile.provider != "hkexnews" or profile.ticker != request.security_id:
        raise DayuBridgeError("identity_mismatch", "HK provider profile differs from query identity")
    values = []
    unresolved = []
    for candidate in client.list_report_candidates(query, profile):
        if candidate.filing_date > request.as_of_date:
            continue
        raw = asdict(candidate) if is_dataclass(candidate) else vars(candidate).copy()
        value = {
            "candidate_id": "hkexnews:" + candidate.source_id,
            "provider": "hkexnews", "provider_document_id": candidate.source_id,
            "market": "HK", "entity": request.entity, "title": candidate.title,
            "source_url": candidate.source_url, "document_kind": request.document_kind,
            "form_type": candidate.fiscal_period, "filing_date": candidate.filing_date,
            "fiscal_year": candidate.fiscal_year, "fiscal_period": candidate.fiscal_period,
            "language": candidate.language, "amended": candidate.amended,
            "remote_size": candidate.content_length, "etag": candidate.etag,
            "last_modified": candidate.last_modified,
            "sdk_report_candidate": raw,
            "sdk_company_profile": {"provider": profile.provider, "company_id": profile.company_id,
                                    "company_name": profile.company_name, "ticker": profile.ticker},
        }
        if _matches(request, value):
            try:
                value["fiscal_year_basis"] = hk_title_year(candidate.title, candidate.fiscal_year)
            except FiscalMetadataError as exc:
                unresolved.append(exc)
                continue
            values.append(value)
    if not values and unresolved:
        raise unresolved[0]
    return _current_versions(values)
