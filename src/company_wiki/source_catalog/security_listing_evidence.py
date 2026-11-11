"""Evidence-backed listing relationships extracted from SEC Form 20-F tables.

This module deliberately has no storage or network access.  It accepts bytes
already verified by the Company Wiki source reader, extracts the standard
Section 12(b) securities table, and matches each symbol to an exact official
security-master row.  It never links by name or by a guessed ticker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from company_wiki.source_contract.source_version import VerifiedContent


LISTING_EVIDENCE_SCHEMA_VERSION = "sec-20f-listing-evidence/2"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_CIK_PATH = re.compile(r"/archives/edgar/data/(\d{1,10})/(\d{18})/", re.IGNORECASE)
_TOKEN = re.compile(r"[A-Z0-9]+")
_DEBT_OR_DERIVATIVE_TERMS = (
    "note", "bond", "debenture", "debt", "warrant", "right", "option",
)
_EQUITY_TERMS = (
    "ordinaryshare", "commonshare", "commonstock", "depositaryshare",
    "preferredshare", "preferredstock",
)


class ListingEvidenceError(ValueError):
    """A filing cannot establish a supported, exact listing relationship."""


@dataclass(frozen=True)
class IssuerListing:
    market: str
    exchange: str
    security_id: str
    security_class: str
    locator: str
    source_name: str
    source_record_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "market": self.market,
            "exchange": self.exchange,
            "security_id": self.security_id,
            "security_class": self.security_class,
            "locator": self.locator,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
        }


@dataclass(frozen=True)
class IssuerListingEvidence:
    schema_version: str
    issuer_link_id: str
    issuer_cik: str
    source_document_id: str
    source_id: str
    source_sha256: str
    source_url: str
    accession: str
    filed_date: str
    listings: tuple[IssuerListing, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "issuer_link_id": self.issuer_link_id,
            "issuer_cik": self.issuer_cik,
            "source_document_id": self.source_document_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "source_url": self.source_url,
            "accession": self.accession,
            "filed_date": self.filed_date,
            "listings": [item.to_dict() for item in self.listings],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {**payload, "evidence_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}

    @classmethod
    def from_dict(cls, value: object) -> "IssuerListingEvidence":
        if not isinstance(value, Mapping) or set(value) != {
            "schema_version", "issuer_link_id", "issuer_cik", "source_document_id",
            "source_id", "source_sha256", "source_url", "accession", "filed_date",
            "listings", "evidence_sha256",
        }:
            raise ListingEvidenceError("listing evidence fields do not match schema")
        payload = {key: item for key, item in value.items() if key != "evidence_sha256"}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected_evidence_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if value["evidence_sha256"] != expected_evidence_sha:
            raise ListingEvidenceError("listing evidence content hash does not match")
        if value["schema_version"] != LISTING_EVIDENCE_SCHEMA_VERSION:
            raise ListingEvidenceError("unsupported listing evidence schema")
        if not isinstance(value["listings"], list):
            raise ListingEvidenceError("listing evidence listings must be a list")
        listings: list[IssuerListing] = []
        for item in value["listings"]:
            if not isinstance(item, Mapping) or set(item) != {
                "market", "exchange", "security_id", "security_class", "locator",
                "source_name", "source_record_id",
            }:
                raise ListingEvidenceError("listing evidence row fields do not match schema")
            fields = tuple(item[key] for key in (
                "market", "exchange", "security_id", "security_class", "locator",
                "source_name", "source_record_id",
            ))
            if any(not isinstance(field, str) or not field.strip() for field in fields):
                raise ListingEvidenceError("listing evidence row contains an empty field")
            listings.append(IssuerListing(*fields))
        evidence = cls(
            schema_version=str(value["schema_version"]),
            issuer_link_id=str(value["issuer_link_id"]),
            issuer_cik=str(value["issuer_cik"]),
            source_document_id=str(value["source_document_id"]),
            source_id=str(value["source_id"]),
            source_sha256=str(value["source_sha256"]),
            source_url=str(value["source_url"]),
            accession=str(value["accession"]),
            filed_date=str(value["filed_date"]),
            listings=tuple(listings),
        )
        _validate_evidence(evidence)
        return evidence


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _exchange_market(value: str) -> tuple[str, str] | None:
    exchange = _normalized(value)
    if "hongkong" in exchange and "stockexchange" in exchange:
        return "HK", "HKEX"
    if "newyorkstockexchange" in exchange or exchange in {"nyse", "nyseamerican"}:
        return "US", "NYSE" if "american" not in exchange else "NYSE AMERICAN"
    if "nasdaq" in exchange:
        return "US", "NASDAQ"
    if "shanghaistockexchange" in exchange or exchange in {"sse", "shanghai"}:
        return "CN", "SSE"
    if "shenzhenstockexchange" in exchange or exchange in {"szse", "shenzhen"}:
        return "CN", "SZSE"
    return None


def _security_key(value: str, market: str) -> str:
    token = re.sub(r"[^A-Z0-9]", "", value.upper())
    if market == "HK" and token.isdigit() and len(token) <= 5:
        return token.zfill(5)
    if market == "CN" and token.isdigit() and len(token) <= 6:
        return token.zfill(6)
    return token


def _table_headers(table: Any) -> tuple[int, int, int] | None:
    for row in _table_grid(table):
        normalized = [_normalized(item) for item in row]
        title = next((i for i, value in enumerate(normalized) if "titleofeachclass" in value), None)
        symbol = next((i for i, value in enumerate(normalized) if "tradingsymbol" in value), None)
        exchange = next((i for i, value in enumerate(normalized) if "nameofeachexchangeonwhichregistered" in value), None)
        if title is not None and symbol is not None and exchange is not None:
            return title, symbol, exchange
    return None


def _table_grid(table: Any) -> tuple[tuple[str, ...], ...]:
    """Normalize table rows once so header and data cells share span offsets."""
    pending: dict[int, tuple[str, int]] = {}
    normalized_rows: list[tuple[str, ...]] = []
    for row in table.find_all("tr"):
        occupied = {column: value for column, (value, _remaining) in pending.items()}
        next_pending = {
            column: (value, remaining - 1)
            for column, (value, remaining) in pending.items()
            if remaining > 1
        }
        column = 0
        for cell in row.find_all(["th", "td"], recursive=False):
            try:
                width = max(1, min(int(cell.get("colspan", "1")), 20))
            except (TypeError, ValueError):
                width = 1
            while any(position in occupied for position in range(column, column + width)):
                column += 1
            try:
                height = max(1, min(int(cell.get("rowspan", "1")), 100))
            except (TypeError, ValueError):
                height = 1
            text = _clean(cell.get_text(" ", strip=True))
            for offset in range(width):
                target = column + offset
                occupied[target] = text
                if height > 1:
                    next_pending[target] = (text, height - 1)
            column += width
        pending = next_pending
        width = max(occupied, default=-1) + 1
        normalized_rows.append(tuple(occupied.get(index, "") for index in range(width)))
    return tuple(normalized_rows)


def _is_equity_class(value: str) -> bool:
    normalized = _normalized(value)
    if any(term in normalized for term in _DEBT_OR_DERIVATIVE_TERMS):
        return False
    return any(term in normalized for term in _EQUITY_TERMS)


def _validate_evidence(value: IssuerListingEvidence) -> None:
    if value.schema_version != LISTING_EVIDENCE_SCHEMA_VERSION:
        raise ListingEvidenceError("unsupported listing evidence schema")
    if re.fullmatch(r"\d{10}", value.issuer_cik) is None:
        raise ListingEvidenceError("issuer CIK must be ten digits")
    expected_link = "issuer-link-v1:" + hashlib.sha256(
        f"sec-cik:{value.issuer_cik}".encode("ascii")
    ).hexdigest()
    if value.issuer_link_id != expected_link:
        raise ListingEvidenceError("issuer link id does not match the SEC CIK")
    if not _SHA256.fullmatch(value.source_sha256):
        raise ListingEvidenceError("source SHA-256 is malformed")
    expected_source_id = f"urn:company-wiki:source:sha256:{value.source_sha256}"
    if value.source_id != expected_source_id:
        raise ListingEvidenceError("source id does not match source SHA-256")
    url = urlsplit(value.source_url)
    if url.scheme != "https" or url.hostname not in {"sec.gov", "www.sec.gov"}:
        raise ListingEvidenceError("listing evidence must come from SEC EDGAR")
    match = _CIK_PATH.search(url.path)
    if match is None or f"{int(match.group(1)):010d}" != value.issuer_cik:
        raise ListingEvidenceError("SEC filing URL CIK does not match evidence issuer CIK")
    accession = re.sub(r"[^0-9]", "", value.accession)
    if len(accession) != 18 or accession != match.group(2):
        raise ListingEvidenceError("SEC accession does not match filing URL")
    try:
        date.fromisoformat(value.filed_date)
    except (TypeError, ValueError) as exc:
        raise ListingEvidenceError("filed date must be an ISO calendar date") from exc
    if len(value.listings) < 2 or len({item.market for item in value.listings}) < 2:
        raise ListingEvidenceError("listing evidence must cover at least two markets")
    listing_keys = [(item.market, item.exchange, item.security_id) for item in value.listings]
    if len(listing_keys) != len(set(listing_keys)):
        raise ListingEvidenceError("listing evidence contains duplicate listings")
    if any(
        item.market not in {"CN", "HK", "US"}
        or not item.exchange.strip()
        or not item.security_id.strip()
        or not item.source_name.strip()
        or not item.source_record_id.strip()
        for item in value.listings
    ):
        raise ListingEvidenceError("listing evidence lacks an exact market-record identity")


def build_sec_20f_listing_evidence(
    content: VerifiedContent,
    *,
    metadata: Mapping[str, Any],
    master: Any,
) -> IssuerListingEvidence | None:
    """Extract exact cross-market equity rows from one verified SEC 20-F.

    ``content`` must be supplied by the CWP SourceVersionReader.  The SEC
    registrant CIK is bound to the official US security-master record; rows
    are linked only when their market, exchange, and exact security ID match
    an official market record.  A missing/unrecognized row yields no link.
    """
    if type(content) is not VerifiedContent:
        raise ListingEvidenceError("content must be verified by the CWP source reader")
    verified = content.verified_observation()
    if not isinstance(metadata, Mapping):
        raise ListingEvidenceError("filing metadata must be an object")
    if (
        str(metadata.get("provider") or "").casefold() not in {"official", "sec"}
        or str(metadata.get("market") or "").upper() != "US"
        or str(metadata.get("document_kind") or "") not in {"annual_report", "regulatory_filing"}
    ):
        raise ListingEvidenceError("listing evidence requires an official US filing source")
    if str(metadata.get("form_type") or "").upper() not in {"20-F", "20-F/A"}:
        raise ListingEvidenceError("only SEC Form 20-F can establish this listing relationship")
    source_url = metadata.get("source_url")
    accession_value = metadata.get("provider_document_id")
    filed_date = metadata.get("published_date")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ListingEvidenceError("SEC filing metadata is incomplete")
    if not isinstance(accession_value, str) or not accession_value.strip():
        raise ListingEvidenceError("SEC filing metadata is incomplete")
    if not isinstance(filed_date, str) or not filed_date.strip():
        raise ListingEvidenceError("SEC filing metadata is incomplete")
    parsed_url = urlsplit(source_url)
    cik_match = _CIK_PATH.search(parsed_url.path)
    if parsed_url.scheme != "https" or parsed_url.hostname not in {"sec.gov", "www.sec.gov"}:
        raise ListingEvidenceError("source URL is not an SEC EDGAR filing URL")
    if cik_match is None:
        raise ListingEvidenceError("source URL is not an SEC EDGAR filing URL")
    issuer_cik = f"{int(cik_match.group(1)):010d}"
    accession = str(accession_value).strip()
    if re.sub(r"[^0-9]", "", accession) != cik_match.group(2):
        raise ListingEvidenceError("filing accession does not match SEC source URL")
    if date.fromisoformat(filed_date[:10]).isoformat() != filed_date[:10]:
        raise ListingEvidenceError("SEC publication date is invalid")

    records = tuple(getattr(master, "records", ()))
    if not any(
        getattr(record, "market", None) == "US"
        and getattr(record, "source_name", None) == "sec_nasdaq"
        and str(getattr(record, "identifiers", {}).get("cik", "")).zfill(10) == issuer_cik
        for record in records
    ):
        raise ListingEvidenceError("SEC filing CIK does not match an official US security record")

    soup = BeautifulSoup(verified.data, "html.parser")
    selected: list[IssuerListing] = []
    table_index = -1
    for candidate_index, table in enumerate(soup.find_all("table")):
        headers = _table_headers(table)
        if headers is None:
            continue
        table_index = candidate_index
        title_index, symbol_index, exchange_index = headers
        for row_index, cells in enumerate(_table_grid(table), start=1):
            title = cells[title_index] if title_index < len(cells) else ""
            if not title or not _is_equity_class(title):
                continue
            exchange_text = cells[exchange_index] if exchange_index < len(cells) else ""
            normalized_exchange = _exchange_market(exchange_text)
            if normalized_exchange is None:
                continue
            market, exchange = normalized_exchange
            symbol_text = cells[symbol_index] if symbol_index < len(cells) else ""
            symbols = set(_TOKEN.findall(symbol_text.upper()))
            matching_records = [
                record for record in records
                if getattr(record, "market", None) == market
                and re.sub(r"[^A-Z0-9]", "", str(getattr(record, "exchange", "")).upper())
                    == re.sub(r"[^A-Z0-9]", "", exchange.upper())
                and _security_key(str(getattr(record, "security_id", "")), market)
                    in {_security_key(symbol, market) for symbol in symbols}
                and (
                    market != "US"
                    or str(getattr(record, "identifiers", {}).get("cik", "")).zfill(10)
                    == issuer_cik
                )
            ]
            for record in matching_records:
                selected.append(IssuerListing(
                    market=market,
                    exchange=exchange,
                    security_id=str(record.security_id),
                    security_class=title,
                    locator=f"sec-20f:registered-securities/table-{table_index}/row-{row_index}",
                    source_name=str(record.source_name),
                    source_record_id=str(record.source_record_id),
                ))
    if not selected or len({item.market for item in selected}) < 2:
        return None
    selected = sorted(
        {(item.market, item.exchange, item.security_id): item for item in selected}.values(),
        key=lambda item: (item.market, item.exchange, item.security_id),
    )
    sha256 = verified.content_sha256
    evidence = IssuerListingEvidence(
        schema_version=LISTING_EVIDENCE_SCHEMA_VERSION,
        issuer_link_id="issuer-link-v1:" + hashlib.sha256(
            f"sec-cik:{issuer_cik}".encode("ascii")
        ).hexdigest(),
        issuer_cik=issuer_cik,
        source_document_id=verified.document_id,
        source_id=verified.source_id,
        source_sha256=sha256,
        source_url=source_url,
        accession=accession,
        filed_date=filed_date[:10],
        listings=tuple(selected),
    )
    _validate_evidence(evidence)
    return evidence


def encode_evidence(value: IssuerListingEvidence) -> bytes:
    """Serialize one immutable evidence fact with stable canonical bytes."""
    _validate_evidence(value)
    return (json.dumps(value.to_dict(), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


__all__ = [
    "IssuerListing",
    "IssuerListingEvidence",
    "LISTING_EVIDENCE_SCHEMA_VERSION",
    "ListingEvidenceError",
    "build_sec_20f_listing_evidence",
    "encode_evidence",
]
