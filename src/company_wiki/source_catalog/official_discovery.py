"""Bounded official index discovery: candidates are not captured business text."""

from __future__ import annotations
from datetime import date
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from typing import Any
from bs4 import BeautifulSoup
from .narrative_routing import classify_document_kind

DISCOVERY_RESULT_SCHEMA = "official-discovery-result/1"

# Document file suffixes are a bounded lead signal: accepted only when no
# legal/site-section veto applies, and never treated as a business original.
_DOCUMENT_SUFFIXES = (
    ".pdf",
    ".txt",
    ".json",
    ".pptx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
)

# Title cues that identify a business-material lead on an index page.
_MATERIAL_TITLE_TOKENS = (
    "earnings",
    "transcript",
    "presentation",
    "results",
    "announcement",
    "press release",
    "news release",
    "report",
    "prospectus",
    "circular",
    "proxy",
    "webcast",
    "dividend",
    "deck",
    "investor conference",
    "conference call",
    "investor day",
    "招股",
    "发行",
    "可转债",
    "活动记录",
    "业绩",
    "说明会",
    "路演",
    "公告",
    "报告",
    "年报",
    "半年报",
    "季报",
    "募集说明",
    "电话会",
    "纪要",
)
# Short Latin filing/meeting codes need word boundaries: "agm" is a substring
# of ordinary words such as "fragment".
_MATERIAL_TITLE_PATTERNS = (re.compile(r"\b(?:agm|egm|6-k|8-k|10-k|10-q|20-f)\b"),)

# Page-section/legal navigation: never a material lead, even when one material
# word also appears in the same title.
_LEGAL_PAGE_TITLE_TOKENS = (
    "legal",
    "accessibility",
    "imprint",
    "sitemap",
    "site map",
    "网站地图",
    "法律声明",
    "免责声明",
)
# A legal document title is excluded unless a material clue is also present
# (for example "Investor Presentation - Privacy Update" stays material).
_LEGAL_DOCUMENT_TITLE_TOKENS = (
    "privacy",
    "terms of use",
    "term of use",
    "cookie",
    "media briefing",
    "press briefing",
    "隐私",
    "使用条款",
)
# Site utility/navigation text: excluded unless a material clue or a document
# suffix is present, so "Contact Information" is a lead only as a file.
_NAVIGATION_TITLE_TOKENS = (
    "contact",
    "联系方式",
    "careers",
    "招聘",
    "subscribe",
    "订阅",
)
# The call-transcript identity requires a transcript/record clue; the word
# "earnings" alone denotes a release or presentation, not a transcript.
_TRANSCRIPT_TITLE_TOKENS = ("transcript", "电话会", "纪要")
# Event notices stay candidates with disposition "index_notice" but never
# consume the material item budget ahead of real documents. A notice needs a
# business-event noun, so "Upcoming Events" or "Upcoming Careers Fair" is not
# promoted to a candidate.
_NOTICE_TITLE_TOKENS = (
    "upcoming",
    "notice",
    "will present",
    "会议通知",
    "关于召开",
)
_EVENT_TITLE_TOKENS = (
    "conference",
    "investor",
    "说明会",
    "路演",
    "电话会",
)


def _is_event_notice(folded: str) -> bool:
    return any(token in folded for token in _NOTICE_TITLE_TOKENS) and any(
        token in folded for token in _EVENT_TITLE_TOKENS
    )


def _has_material_clue(folded: str) -> bool:
    return any(token in folded for token in _MATERIAL_TITLE_TOKENS) or any(
        pattern.search(folded) for pattern in _MATERIAL_TITLE_PATTERNS
    )


def _is_material_link(folded: str, path: str) -> bool:
    """Decide whether an anchor is a business-material lead.

    Order matters: a page-section/legal veto wins; an explicit material clue
    wins over secondary legal-document and navigation words; otherwise a
    document suffix is accepted; everything else is not a lead.
    """
    if any(token in folded for token in _LEGAL_PAGE_TITLE_TOKENS):
        return False
    if _has_material_clue(folded):
        return True
    if any(token in folded for token in _LEGAL_DOCUMENT_TITLE_TOKENS):
        return False
    if any(token in folded for token in _NAVIGATION_TITLE_TOKENS):
        return False
    return path.lower().endswith(_DOCUMENT_SUFFIXES)


def _anchor_title(anchor) -> str:
    """Lead text for an anchor: visible text, then accessibility attributes."""
    text = anchor.get_text(" ", strip=True)
    if text:
        return text
    for attribute in ("aria-label", "title"):
        value = anchor.get(attribute)
        if isinstance(value, str) and value.strip():
            return value.strip()
    image = anchor.find("img")
    if image is not None:
        for attribute in ("alt", "title"):
            value = image.get(attribute)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _item_container(anchor):
    """Nearest item-level block: article/li/tr, or a div containing one link.

    A wider wrapper is not an item container: its date children belong to the
    page or to a list, not to this anchor.
    """
    for name in ("article", "li", "tr"):
        block = anchor.find_parent(name)
        if block is not None:
            return block if len(block.find_all("a", href=True)) == 1 else None
    block = anchor.find_parent("div")
    if block is not None and len(block.find_all("a", href=True)) == 1:
        return block
    return None


def _item_title(anchor, title: str, folded: str) -> tuple[str, str]:
    """Recover the document name when the anchor text is only an icon label.

    Index tables often put the document name in a neighbouring cell and only
    "Download" inside the anchor; the item block supplies the real lead.
    """
    if _has_material_clue(folded):
        return title, folded
    block = _item_container(anchor)
    if block is None:
        return title, folded
    block_text = block.get_text(" ", strip=True)[:300]
    if title and title in block_text:
        block_text = block_text.replace(title, " ", 1).strip(" -|·\t")
    return (block_text, block_text.casefold()) if block_text else (title, folded)


def discover_official_documents(
    pages, *, entity, as_of_date, start_date, max_items=30, max_bytes=8388608
):
    """Parse bounded actual index snapshots, preserving unknown and partial coverage.

    Fetching is separate and uses the existing AcquisitionBudget HTTP transport;
    no second provider registry, content lake, permissions, or task DB is made.
    """
    asof = date.fromisoformat(as_of_date)
    start = date.fromisoformat(start_date)
    if (
        start > asof
        or type(max_items) is not int
        or not 1 <= max_items <= 30
        or type(max_bytes) is not int
        or not 0 < max_bytes <= 8388608
    ):
        raise ValueError("invalid_discovery_limits")
    candidates: list[Any] = []
    limitations: list[Any] = []
    events = []
    used = 0
    seen = set()
    excluded = []
    pending: list[tuple[dict, bool]] = []
    for page in pages:
        original = page["original"]
        used += len(original)
        events.append(page["capture_id"])
        if used > max_bytes:
            limitations.append("byte_limit_reached")
            break
        if page.get("mime_type") not in {"text/html", "application/xhtml+xml"}:
            limitations.append("unsupported_index_format")
            continue
        soup = BeautifulSoup(original, "html.parser")
        text = soup.get_text(" ", strip=True).casefold()
        if "loading" in text or soup.find("script", src=True):
            limitations.append("dynamic_content_unresolved")
        page_parts = urlsplit(page["url"])
        page_key = urlunsplit(
            (page_parts.scheme, page_parts.netloc, page_parts.path,
             page_parts.query, "")
        )
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not isinstance(href, str) or not href.strip() or href.strip() == "#":
                continue
            try:
                url = urljoin(page["url"], href)
                parsed = urlsplit(url)
            except ValueError:
                limitations.append("invalid_anchor_url")
                continue
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                continue
            # Fragments never reach the server: dedupe on the resource URL and
            # never let an empty/hash anchor point back at the index itself.
            dedupe_key = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
            )
            if dedupe_key == page_key or dedupe_key in seen:
                continue
            title = _anchor_title(anchor)
            folded = title.casefold()
            if not _has_material_clue(folded):
                # Icon/table rows often carry the document name outside the
                # anchor text; prefer the item block when it names a document.
                recovered_title, recovered_folded = _item_title(
                    anchor, title, folded
                )
                if _has_material_clue(recovered_folded):
                    title, folded = recovered_title, recovered_folded
            if not _is_material_link(folded, parsed.path) and not _is_event_notice(
                folded
            ):
                if parsed.path.lower().endswith(_DOCUMENT_SUFFIXES):
                    # A document link whose title carried no recognised clue:
                    # never silently report a clean index.
                    limitations.append("unclassified_document_links")
                continue
            seen.add(dedupe_key)
            published = anchor.get("data-date")
            if not published:
                block = _item_container(anchor)
                time = block.find("time") if block is not None else None
                published = time.get("datetime") if time is not None else None
            if published:
                try:
                    published = date.fromisoformat(published[:10]).isoformat()
                except (ValueError, TypeError):
                    published = None
            if published and not start_date <= published <= as_of_date:
                excluded.append(
                    {
                        "source_url": url,
                        "published_date": published,
                        "reason": "after_as_of"
                        if published > as_of_date
                        else "before_window",
                    }
                )
                continue
            notice = any(t in folded for t in _NOTICE_TITLE_TOKENS)
            kind = classify_document_kind(title, "investor_relations")
            if any(token in folded for token in _TRANSCRIPT_TITLE_TOKENS):
                kind = "investor_call_transcript"
            # "Earnings release/presentation/event notice" stays the shared
            # classifier's kind: the word "earnings" is not a call identity.
            disposition = (
                "index_notice"
                if notice
                else "date_unknown"
                if published is None
                else "candidate"
            )
            pending.append(
                (
                    {
                        "candidate_id": "urn:company-wiki:official-candidate:sha256:"
                        + hashlib.sha256(url.encode()).hexdigest(),
                        "entity": entity,
                        "title": title,
                        "source_url": url,
                        "document_kind": kind,
                        "published_date": published,
                        "disposition": disposition,
                        "capture_id": page["capture_id"],
                        "index_source_sha256": hashlib.sha256(original).hexdigest(),
                        "is_business_original": False,
                        "materiality": "not_assessed",
                        "metadata_only": True,
                    },
                    notice,
                )
            )
    # Materials first: an event notice must never consume the item budget
    # ahead of a real document, and the total stays bounded by max_items.
    materials = [record for record, notice in pending if not notice]
    notices = [record for record, notice in pending if notice]
    candidates = materials[:max_items]
    if len(materials) > max_items:
        limitations.append("item_limit_reached")
    remaining = max_items - len(candidates)
    if remaining > 0:
        candidates.extend(notices[:remaining])
    if len(notices) > remaining:
        limitations.append("item_limit_reached")
    if any(x["published_date"] is None for x in candidates):
        limitations.append("publication_date_unknown")
    payload = {
        "entity": entity,
        "start_date": start_date,
        "as_of_date": as_of_date,
        "event_ids": events,
        "response_bytes": used,
        "max_items": max_items,
        "max_bytes": max_bytes,
    }
    return {
        "schema_version": DISCOVERY_RESULT_SCHEMA,
        "coverage_status": "partial" if limitations else "checked_index_only",
        "candidates": candidates,
        "excluded": excluded,
        "limitations": list(dict.fromkeys(limitations)),
        "receipt": {
            **payload,
            "event_sha256": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
        },
        "no_documents_claimed": False,
    }


def fetch_official_indexes(urls, *, max_bytes=8388608, max_seconds=120, transport=None):
    """Bound actual index GETs through existing shared byte/deadline accounting.

    At most six explicitly supplied official index URLs. No crawling, paid API,
    implicit body import or infinite daemon. Async operation deadline encloses
    headers and streamed body; every redirect/response uses the same budget.
    """
    import asyncio
    from datetime import datetime, timezone
    import uuid
    import httpx
    from .download_budget import AcquisitionBudget
    from .bounded_http import BudgetedAsyncHTTPTransport

    if not isinstance(urls, list) or not 1 <= len(urls) <= 6:
        raise ValueError("invalid_index_urls")
    for url in urls:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("invalid_index_url")
    if (
        type(max_bytes) is not int
        or not 0 < max_bytes <= 8388608
        or isinstance(max_seconds, bool)
        or not isinstance(max_seconds, (int, float))
        or not 0 < max_seconds <= 120
    ):
        raise ValueError("invalid_discovery_limits")
    budget = AcquisitionBudget.from_limits(
        max_response_bytes=max_bytes, max_seconds=max_seconds, max_cost_usd="0"
    )

    async def fetch():
        pages = []
        receipts = []
        inner = transport or httpx.AsyncHTTPTransport(retries=0)
        async with httpx.AsyncClient(
            transport=BudgetedAsyncHTTPTransport(inner, budget),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            for url in urls:
                event = "official-index-" + uuid.uuid4().hex
                receipt = {
                    "event_id": event,
                    "url": url,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                }

                async def one():
                    async with client.stream("GET", url) as response:
                        receipt.update(
                            http_status=response.status_code,
                            effective_url=str(response.url),
                        )
                        original = b"".join(
                            [chunk async for chunk in response.aiter_bytes()]
                        )
                        receipt.update(
                            response_body_bytes=len(original),
                            content_sha256=hashlib.sha256(original).hexdigest(),
                        )
                        response.raise_for_status()
                        mime = (
                            response.headers.get("content-type", "")
                            .split(";")[0]
                            .strip()
                            .lower()
                        )
                        pages.append(
                            {
                                "url": str(response.url),
                                "original": original,
                                "mime_type": mime,
                                "capture_id": event,
                            }
                        )
                        receipt["status"] = "opened"

                try:
                    await asyncio.wait_for(one(), timeout=budget.remaining_seconds)
                except Exception as exc:
                    receipt["error_type"] = type(exc).__name__
                    if isinstance(exc, (httpx.TransportError, asyncio.TimeoutError)):
                        budget.observe_provider(started=True, complete=None)
                finally:
                    receipt.update(
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        cumulative_response_bytes=budget.response_bytes_used,
                        usage_complete=budget.usage_complete,
                        cost_usd="0",
                    )
                    receipts.append(receipt)
                if (
                    budget.remaining_seconds <= 0
                    or budget.remaining_response_bytes <= 0
                    or not budget.usage_complete
                ):
                    break
        if len(receipts) < len(urls):
            receipts.append(
                {
                    "status": "not_run",
                    "reason": "shared_budget_exhausted",
                    "remaining_urls": len(urls) - len(receipts),
                    "usage_complete": budget.usage_complete,
                }
            )
        return pages, receipts

    return asyncio.run(fetch())
