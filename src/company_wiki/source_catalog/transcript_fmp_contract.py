"""FMP-only transcript envelope checks, isolated from the legacy provider path."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .acquisition import DownloadCandidate
from .resolver import SourceRequest
from .transcript_tool_errors import TranscriptToolContractError

_FMP_HOST = "financialmodelingprep.com"
_FMP_PATH = "/stable/earning-call-transcript"


def _canonical_date(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TranscriptToolContractError(f"invalid {name}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise TranscriptToolContractError(f"invalid {name}") from exc
    if parsed.isoformat() != value:
        raise TranscriptToolContractError(f"invalid {name}")
    return value


def _query_matches(query: dict[str, list[str]], request: SourceRequest) -> bool:
    return (
        set(query) == {"symbol", "year", "quarter"}
        and all(len(values) == 1 and values[0] for values in query.values())
        and query.get("symbol") == [request.security_id]
        and query.get("year") == [str(request.fiscal_year)]
        and query.get("quarter") == [(request.fiscal_period or "").removeprefix("Q")]
    )


def _url_authority_matches(parsed: Any) -> bool:
    return (
        parsed.scheme == "https"
        and parsed.hostname == _FMP_HOST
        and parsed.port is None
        and parsed.path == _FMP_PATH
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def validate_fmp_url(source_url: str, request: SourceRequest) -> None:
    parsed = urlsplit(source_url)
    if not _url_authority_matches(parsed):
        raise TranscriptToolContractError("FMP source URL is not canonical")
    try:
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise TranscriptToolContractError("FMP source URL query is invalid") from exc
    if not _query_matches(query, request):
        raise TranscriptToolContractError("FMP source URL does not match requested security and period")


def _unknown_cutoff(candidate: DownloadCandidate, verified: Any) -> None:
    if verified or candidate.filing_date is not None:
        raise TranscriptToolContractError("unknown publication date has invalid cutoff")


def _known_cutoff(value: Any, candidate: DownloadCandidate, request: SourceRequest, verified: Any) -> str:
    publication_date = _canonical_date(value, "publication_date")
    if not verified or publication_date > request.as_of_date or publication_date != candidate.filing_date:
        raise TranscriptToolContractError("publication cutoff is not verified")
    return publication_date


def _validate_cutoff(payload: dict[str, Any], candidate: DownloadCandidate, request: SourceRequest) -> tuple[str, str | None, bool]:
    call_date = _canonical_date(payload.get("call_date"), "call_date")
    verified = payload.get("as_of_cutoff_verified")
    if type(verified) is not bool or call_date > request.as_of_date:
        raise TranscriptToolContractError("invalid FMP cutoff metadata")
    publication_date = payload.get("publication_date")
    if publication_date is None:
        _unknown_cutoff(candidate, verified)
        return call_date, None, False
    publication_date = _known_cutoff(publication_date, candidate, request, verified)
    return call_date, publication_date, True


def validate_fmp_period(payload: dict[str, Any], candidate: DownloadCandidate, request: SourceRequest) -> tuple[str, str | None, bool]:
    if payload.get("fiscal_period") != f"{request.fiscal_year}-{request.fiscal_period}":
        raise TranscriptToolContractError("result fiscal period does not match request")
    if payload.get("as_of_date") != request.as_of_date:
        raise TranscriptToolContractError("result as_of_date does not match request")
    return _validate_cutoff(payload, candidate, request)


def _decode_record(original: bytes) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for key, value in pairs:
            if key in record:
                raise TranscriptToolContractError("duplicate FMP original JSON key")
            record[key] = value
        return record

    try:
        data = json.loads(original.decode("utf-8", errors="strict"), object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError, TranscriptToolContractError) as exc:
        raise TranscriptToolContractError("FMP original JSON is invalid") from exc
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise TranscriptToolContractError("FMP original must contain one record")
    return data[0]


def _validate_record_identity(record: dict[str, Any], payload: dict[str, Any], request: SourceRequest, candidate: DownloadCandidate) -> None:
    # Provider raw JSON is preserved, not rewritten into our envelope schema.
    # Optional metadata does not change the required identity/content binding.
    if not {"symbol", "year", "date", "content"}.issubset(record):
        raise TranscriptToolContractError("FMP original is missing required fields")
    year = record["year"]
    if isinstance(year, str) and re.fullmatch(r"[0-9]{4}", year):
        year = int(year)
    if type(year) is not int:
        raise TranscriptToolContractError("FMP original fiscal year is invalid")
    quarters = []
    for name in ("period", "quarter"):
        if name not in record:
            continue
        value = record[name]
        if type(value) is int and 1 <= value <= 4:
            quarters.append(f"Q{value}")
        elif isinstance(value, str) and (match := re.fullmatch(r"Q?([1-4])", value.strip(), re.IGNORECASE)):
            quarters.append("Q" + match.group(1))
        else:
            raise TranscriptToolContractError("FMP original fiscal quarter is invalid")
    if not quarters or len(set(quarters)) != 1:
        raise TranscriptToolContractError("FMP original fiscal quarter is absent or conflicting")
    expected = (request.security_id, request.fiscal_period, request.fiscal_year)
    if (record["symbol"], quarters[0], year) != expected:
        raise TranscriptToolContractError("FMP original identity or period mismatch")
    raw_date = record["date"]
    if not isinstance(raw_date, str):
        raise TranscriptToolContractError("invalid FMP original call date")
    try:
        call_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        call_date = _canonical_date(raw_date, "FMP original call date")
    document_date = candidate.provider_document_id.rsplit(":", maxsplit=1)[-1]
    if call_date != payload["call_date"] or document_date != call_date:
        raise TranscriptToolContractError("FMP original call date mismatch")


def _validate_record_content(record: dict[str, Any], payload: dict[str, Any]) -> None:
    content = record["content"]
    if not isinstance(content, str) or not content.strip():
        raise TranscriptToolContractError("FMP original transcript content is empty")
    canonical = content.replace("\r\n", "\n").replace("\r", "\n").strip().encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != payload["canonical_content_sha256"] or len(canonical) != payload["content_bytes"]:
        raise TranscriptToolContractError("FMP canonical content hash or size mismatch")


def validate_fmp_original(payload: dict[str, Any], original: bytes, request: SourceRequest, candidate: DownloadCandidate) -> None:
    record = _decode_record(original)
    _validate_record_identity(record, payload, request, candidate)
    _validate_record_content(record, payload)
