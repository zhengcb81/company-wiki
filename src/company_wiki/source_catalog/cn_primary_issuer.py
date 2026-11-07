"""Bounded native-PDF proof of a CN issuer's own legal registration.

This is an original-source observation, not a name/ticker registry. A usable
proof requires an own-company registration passage containing a checksum-valid
USCC, own-company legal-name and listing tables, and the owner's cache-only
verified official security record. Ambiguity and missing native text refuse.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import re
from typing import Any

from .security_identity import (
    CNINFO_STOCK_URL,
    SecurityIdentityError,
    SecurityIdentityResolver,
    SecurityMasterStore,
)
from .source_reader import SourceRef, SourceVersionReader

SCHEMA_VERSION = "company-wiki-cn-primary-issuer/1"
VERIFIER = "cn-primary-uscc/1"
NORMALIZATION = "unicode-whitespace-remove/1"
MAX_BYTES = 16_000_000
MAX_PAGES = 1_000
MAX_TEXT_CHARACTERS = 8_000_000
SUPPORTED_CN_FILING_KINDS = frozenset({
    "annual_report", "semi_annual_report", "quarterly_report",
})
_USCC_ALPHABET = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)


class PrimaryIssuerUnavailable(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def normalize_text(value: str) -> str:
    return "".join(value.split())


def valid_uscc(value: str) -> bool:
    if (
        len(value) != 18
        or len(set(value)) < 2
        or any(char not in _USCC_ALPHABET for char in value)
    ):
        return False
    expected = (
        31
        - sum(
            _USCC_ALPHABET.index(char) * weight
            for char, weight in zip(value[:17], _USCC_WEIGHTS)
        )
        % 31
    ) % 31
    return value[-1] == _USCC_ALPHABET[expected]


def pdf_text_pages(data: bytes) -> list[str]:
    if len(data) > MAX_BYTES:
        raise PrimaryIssuerUnavailable("primary_pdf_byte_limit")
    try:
        import pymupdf
    except ImportError as exc:
        raise PrimaryIssuerUnavailable("native_pdf_reader_unavailable") from exc
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.is_encrypted or len(document) > MAX_PAGES:
                raise PrimaryIssuerUnavailable("primary_pdf_page_limit_or_encrypted")
            pages, length = [], 0
            for page in document:
                text = page.get_text("text")
                length += len(text)
                if length > MAX_TEXT_CHARACTERS:
                    raise PrimaryIssuerUnavailable("primary_pdf_text_limit")
                pages.append(text)
            return pages
    except PrimaryIssuerUnavailable:
        raise
    except Exception as exc:
        raise PrimaryIssuerUnavailable("native_pdf_unreadable") from exc


def _locator(page: int, excerpt: str) -> dict[str, Any]:
    return {
        "kind": "page",
        "value": str(page),
        "page_kind": "physical",
        "excerpt": excerpt,
    }


def validate_quote(pages: list[str], quote: str) -> dict[str, Any]:
    normalized = normalize_text(quote)
    if len(normalized) < 12 or len(quote) > 4096:
        raise PrimaryIssuerUnavailable("evidence_quote_length_invalid")
    matches = []
    for page, raw in enumerate(pages, start=1):
        text = normalize_text(raw)
        first = text.find(normalized)
        if first >= 0:
            matches.append(page)
            # Overlapping occurrences also invalidate uniqueness. Stop once
            # ambiguity is proven instead of materializing all match indices.
            if text.find(normalized, first + 1) >= 0:
                matches.append(page)
        if len(matches) > 1:
            break
    if len(matches) != 1:
        return {
            "state": "not_found" if not matches else "ambiguous",
            "reason": "evidence_quote_not_found"
            if not matches
            else "evidence_quote_not_unique",
            "physical_page": None,
            "locator": None,
            "normalization": NORMALIZATION,
            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        }
    return {
        "state": "verified",
        "physical_page": matches[0],
        "locator": _locator(matches[0], quote),
        "normalization": NORMALIZATION,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    }


def observe_cn_original(
    catalog, ref: SourceRef, *, pages: list[str], metadata: dict[str, Any]
) -> dict[str, Any]:
    if metadata.get("market") != "CN" or metadata.get("document_kind") not in SUPPORTED_CN_FILING_KINDS:
        raise PrimaryIssuerUnavailable("cn_primary_filing_scope_missing")
    compact = [normalize_text(value) for value in pages]
    # Restrict company-name and listing observations to the primary company
    # introduction (not subsidiary/shareholder tables in the financial notes).
    introductions = [
        (number, text)
        for number, text in enumerate(compact[:50], start=1)
        if "公司基本情况" in text or "公司股票简况" in text
    ]
    names: dict[str, list[tuple[int, str]]] = {}
    tickers: dict[str, list[tuple[int, str]]] = {}
    for page, text in introductions:
        for match in re.finditer(
            r"公司的中文名称(.{4,100}?(?:股份有限公司|有限公司))", text
        ):
            names.setdefault(match[1], []).append((page, match[0]))
        if "公司股票简况" in text:
            for match in re.finditer(
                r"股票代码.{0,120}?(?<![0-9])([0-9]{6})(?![0-9])", text
            ):
                tickers.setdefault(match[1], []).append((page, match[0]))
    if len(names) != 1 or len(tickers) != 1:
        raise PrimaryIssuerUnavailable("cn_primary_company_tables_ambiguous_or_missing")
    legal_name = next(iter(names))
    ticker = next(iter(tickers))
    # A captured identity field corroborates the original table; it cannot
    # replace it, and the official record below must independently be exact.
    if str(metadata.get("security_id") or "") != ticker:
        raise PrimaryIssuerUnavailable("cn_primary_security_conflict")
    registration: dict[str, list[tuple[int, str]]] = {}
    comparable_name = legal_name.replace("（", "(").replace("）", ")")
    predecessor_name = comparable_name.removesuffix("股份有限公司") + "有限公司"
    # Positive grammar for an own-company conversion/registration history.
    # There is no arbitrary text bridge from a legal-name definition to a
    # first-person registration quoted from another company's document.
    date = r"[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日"
    registration_pattern = re.compile(
        re.escape(comparable_name)
        + r"\(以下简称[“\"]?本公司[”\"]?\)的前身为"
        + re.escape(predecessor_name)
        + r"\(以下简称[“\"]?原公司[”\"]?\)由"
        + r"[A-Za-z0-9&.,\-]{2,160}\(以下简称[“\"]?(?!本公司|原公司)[A-Za-z\u4e00-\u9fff]{2,30}[”\"]?\)于"
        + date
        + r"在中华人民共和国[\u4e00-\u9fff]{2,15}成立。"
        + r"根据原公司全体股东于"
        + date
        + r"签署的《"
        + re.escape(comparable_name)
        + r"创立大会暨[0-9]{4}年第一次临时股东大会决议》[，,]"
        + r"本公司整体改制变更为股份有限公司。于"
        + date
        + r"取得新营业执照[，,]统一社会信用代码为([0-9A-Z]{18})"
    )
    for page, raw in enumerate(compact, start=1):
        text = raw.replace("（", "(").replace("）", ")")
        for match in registration_pattern.finditer(text):
            if not valid_uscc(match[1]):
                raise PrimaryIssuerUnavailable("cn_primary_uscc_checksum_invalid")
            registration.setdefault(match[1], []).append((page, match[0]))
    if len(registration) != 1:
        raise PrimaryIssuerUnavailable(
            "cn_primary_own_registration_ambiguous_or_missing"
        )
    try:
        master = SecurityMasterStore(
            catalog.config.catalog_dir / "security_master"
        ).load(markets=("CN",))
        identity = (
            SecurityIdentityResolver(master).identify(ticker, market="CN").resolved
        )
    except SecurityIdentityError as exc:
        raise PrimaryIssuerUnavailable(
            "cn_official_security_cache_unavailable"
        ) from exc
    if (
        identity is None
        or not identity.verified
        or not identity.active
        or identity.match_basis != "ticker_exact"
        or identity.ticker != ticker
        or identity.source_name != "cninfo"
        or identity.source_url != CNINFO_STOCK_URL
    ):
        raise PrimaryIssuerUnavailable("cn_official_security_not_exact")
    # Official CNINFO snapshots carry a short name. It must occur as the
    # source's explicit own-company Chinese abbreviation, never fuzzy text.
    abbreviations = set()
    for _, text in introductions:
        abbreviations.update(
            re.findall(
                r"公司的中文简称([^，。；:：]{2,30}?)(?=公司的|公司[的股注网]|$)", text
            )
        )
    if (
        identity.canonical_name not in abbreviations
        and identity.canonical_name != legal_name
    ):
        raise PrimaryIssuerUnavailable("cn_official_company_name_conflict")
    uscc = next(iter(registration))
    evidence = [
        {"field": "legal_name", "locator": _locator(*names[legal_name][0])},
        {"field": "security_id", "locator": _locator(*tickers[ticker][0])},
        {"field": "uscc", "locator": _locator(*registration[uscc][0])},
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "original_verified_pending_source_facts",
        "key": {"namespace": "cn.uscc", "value": uscc},
        "verifier": VERIFIER,
        "source_ref": asdict(ref),
        "assertion_id": None,
        "legal_name": legal_name,
        "security": {
            name: getattr(identity, name)
            for name in (
                "market",
                "ticker",
                "exchange",
                "security_id",
                "source_name",
                "source_url",
                "source_record_id",
            )
        },
        "evidence": evidence,
        "normalization": NORMALIZATION,
    }


def extract_cn_issuer(
    catalog, ref: SourceRef, *, pages: list[str], metadata: dict[str, Any]
) -> dict[str, Any]:
    from .assertion_service import get_verified_assertion

    assertion = get_verified_assertion(
        catalog.reader, ref.source_id, ref.content_sha256, reader="steady"
    )
    if assertion is None or assertion.get("evidence_basis") != "source-facts":
        raise PrimaryIssuerUnavailable("cn_verified_source_facts_missing")
    value = observe_cn_original(catalog, ref, pages=pages, metadata=metadata)
    value.update(state="verified", assertion_id=str(assertion["assertion_id"]))
    return value


def read_cn_primary_issuer(catalog, ref: SourceRef) -> dict[str, Any]:
    if ref.mime_type != "application/pdf" or ref.byte_size > MAX_BYTES:
        raise PrimaryIssuerUnavailable("cn_primary_pdf_required")
    opened, metadata = SourceVersionReader(catalog).open_described_version(
        ref, purpose="source_export"
    )
    return extract_cn_issuer(
        catalog, ref, pages=pdf_text_pages(opened.data), metadata=metadata
    )
