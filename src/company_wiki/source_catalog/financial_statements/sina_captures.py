"""Read the observations recorded alongside retained Sina response bytes."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from .contracts import SINA_PROVIDER_ID, STATEMENT_PROVIDER_SOURCES
from .sina_provider import SINA_ENDPOINT, sina_paper_code


@dataclass(frozen=True)
class CapturedPage:
    url: str
    paper_code: str
    statement_type: str
    source_key: str
    page: int
    data: bytes
    sha256: str
    observed_at: str


def _endpoint_query(url: str) -> dict[str, list[str]] | None:
    actual, endpoint = urlsplit(url), urlsplit(SINA_ENDPOINT)
    if (actual.scheme, actual.netloc, actual.path, actual.fragment) != (
        endpoint.scheme, endpoint.netloc, endpoint.path, "",
    ):
        return None
    return parse_qs(actual.query, keep_blank_values=True)


def _selected_page(params: dict[str, list[str]], paper_code: str,
                   sources: Collection[str]) -> tuple[str, int] | None:
    source = params.get("source", [""])[0]
    if params.get("paperCode") != [paper_code] or source not in sources:
        return None
    page_values = params.get("page", [])
    if (params.get("source") != [source] or len(page_values) != 1
            or not re.fullmatch(r"[1-9][0-9]*", page_values[0])):
        raise ValueError("capture has an invalid statement page")
    return source, int(page_values[0])


def matches_replay_source(provider: object, url: object, *, exchange: str,
                          code: str, source_key: str) -> bool:
    """Use the retained attribution and any scope expressed by a Sina capture URL."""
    if provider not in (None, "", SINA_PROVIDER_ID):
        return False
    params = _endpoint_query(url) if isinstance(url, str) else None
    if params is None:
        return provider == SINA_PROVIDER_ID
    return _selected_page(params, sina_paper_code(exchange, code), (source_key,)) is not None


def read_captured_pages(
    observations: Path, *, exchange: str, code: str, statements: tuple[str, ...],
) -> list[CapturedPage]:
    """Select the requested provider scope, preserving the actual observation time."""
    paper_code = sina_paper_code(exchange, code)
    records = json.loads(observations.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("capture observations must be an array")
    statement_by_key = {STATEMENT_PROVIDER_SOURCES[name]: name for name in statements}
    root = observations.resolve().parent
    pages: list[CapturedPage] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("url"), str):
            raise ValueError("capture observation has no provider URL")
        params = _endpoint_query(record["url"])
        if params is None or record.get("http_status") != 200:
            continue
        selected = _selected_page(params, paper_code, statement_by_key)
        if selected is None:
            continue
        source, page_number = selected
        fixture = record.get("fixture")
        if not isinstance(fixture, str) or not fixture:
            raise ValueError("capture observation lacks its original bytes")
        file = (root / fixture).resolve()
        if not file.is_relative_to(root):
            raise ValueError("capture original must be inside the observation directory")
        size = record.get("bytes")
        sha = record.get("sha256")
        captured = record.get("retrieved_at")
        if (type(size) is not int or size < 1 or not isinstance(sha, str)
                or not re.fullmatch(r"[a-f0-9]{64}", sha) or not isinstance(captured, str)):
            raise ValueError("capture observation lacks byte identity or time")
        timestamp = datetime.fromisoformat(captured.replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("capture observation time has no timezone")
        with (gzip.open(file, "rb") if file.suffix.lower() == ".gz" else file.open("rb")) as stream:
            data = stream.read(size + 1)
        if len(data) != size:
            raise ValueError("capture original byte size mismatch")
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("capture original SHA-256 mismatch")
        pages.append(CapturedPage(
            url=record["url"], paper_code=paper_code,
            statement_type=statement_by_key[source], source_key=source,
            page=page_number, data=data, sha256=sha,
            observed_at=timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        ))
    return sorted(pages, key=lambda page: page.observed_at.removesuffix("Z"))
