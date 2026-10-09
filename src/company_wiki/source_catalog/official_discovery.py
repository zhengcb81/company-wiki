"""Bounded official index discovery: candidates are not captured business text."""

from __future__ import annotations
from datetime import date
import hashlib
import json
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .narrative_routing import classify_document_kind

DISCOVERY_RESULT_SCHEMA = "official-discovery-result/1"


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
    candidates = []
    limitations = []
    events = []
    used = 0
    seen = set()
    excluded = []
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
        for anchor in soup.find_all("a", href=True):
            title = anchor.get_text(" ", strip=True)
            url = urljoin(page["url"], anchor["href"])
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or url in seen
            ):
                continue
            # Content links, not every navigation/footer link.
            folded = title.casefold()
            if not (
                parsed.path.lower().endswith((".pdf", ".txt", ".json", ".pptx"))
                or any(
                    t in folded
                    for t in [
                        "earnings",
                        "transcript",
                        "presentation",
                        "conference",
                        "business",
                        "investor",
                        "招股",
                        "发行",
                        "可转债",
                        "活动记录",
                    ]
                )
            ):
                continue
            seen.add(url)
            parent = anchor.find_parent(["article", "li", "tr", "div"])
            time = parent.find("time") if parent else None
            published = anchor.get("data-date") or (
                time.get("datetime") if time else None
            )
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
            notice = any(
                t in folded
                for t in ["upcoming", "notice", "will present", "会议通知", "关于召开"]
            )
            kind = classify_document_kind(title, "investor_relations")
            if "earnings" in folded or "transcript" in folded:
                kind = "investor_call_transcript"
            disposition = (
                "index_notice"
                if notice
                else "date_unknown"
                if published is None
                else "candidate"
            )
            if len(candidates) >= max_items:
                limitations.append("item_limit_reached")
                break
            candidates.append(
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
                }
            )
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
