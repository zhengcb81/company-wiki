"""Bounded official index discovery: candidates are not captured business text."""

from __future__ import annotations
from datetime import date
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from typing import Any
from bs4 import BeautifulSoup, Comment
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

# Strong title cues identify a document by itself ("Annual Report 2025",
# "Q3 Earnings Call Transcript", "2026年半年度报告").
_STRONG_TITLE_TOKENS = (
    "earnings",
    "transcript",
    "presentation",
    "annual report",
    "interim report",
    "semi-annual report",
    "semiannual report",
    "quarterly report",
    "results announcement",
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
    "业绩说明会",
    "业绩报告",
    "年度报告",
    "半年度报告",
    "季度报告",
    "年报",
    "季报",
    "募集说明",
    "电话会",
    "纪要",
)
# Short Latin filing/meeting codes need word boundaries: "agm" is a substring
# of ordinary words such as "fragment".
_STRONG_TITLE_PATTERNS = (re.compile(r"\b(?:agm|egm|6-k|8-k|10-k|10-q|20-f)\b"),)
# Broad title cues ("Results", "Reports", "公告") are also section/navigation
# labels. They identify a document only when the URL is a document file or the
# anchor sits in a dated item block.
_WEAK_TITLE_TOKENS = (
    "results",
    "announcement",
    "press release",
    "news release",
    "report",
    "公告",
    "业绩",
    "报告",
    "说明会",
    "路演",
)
# Exact section labels that are navigation to a listing, not a document.
_SECTION_LABEL_TITLES = frozenset(
    {
        "annual report",
        "annual reports",
        "interim report",
        "interim reports",
        "report",
        "reports",
        "results",
        "announcement",
        "announcements",
        "news release",
        "news releases",
        "press release",
        "press releases",
        "publications",
        "filings",
        "financial reports",
        "公告",
        "公司公告",
        "公告及通函",
        "业绩",
        "报告",
        "定期报告",
        "临时公告",
    }
)

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

# This is coverage observation, not a second link extractor. A declared
# document which the anchor-only parser has not inspected must remain unknown.
_JSONLD_MIME = re.compile(r"^\s*application/ld\+json\s*(?:;.*)?$", re.I)
_DECLARED_DOCUMENT_TYPES = frozenset({
    "DigitalDocument", "TextDigitalDocument", "SpreadsheetDigitalDocument",
    "PresentationDigitalDocument", "DataDownload", "MediaObject", "Report",
})
_MAX_JSONLD_SCRIPTS = 32
_MAX_JSONLD_BYTES = 65_536
_MAX_JSONLD_NODES = 128
_MAX_JSONLD_DEPTH = 8
_DOCUMENT_PROPERTIES = frozenset({"contentUrl", "encoding", "associatedMedia", "distribution"})
_LOADING_PLACEHOLDER = re.compile(
    r"^\s*(?:loading|(?:正在)?(?:加载|加載)中)(?:\s*(?:\.{1,3}|…))*\s*$", re.I
)
_NON_CONTENT_TAGS = ("head", "title", "script", "style", "template", "nav", "header", "footer")


def _reject_jsonld_constant(value: str):
    raise ValueError("nonfinite JSON-LD constant: " + value)


def _unique_jsonld_object(pairs):
    """Duplicate fields cannot silently replace an earlier document declaration."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON-LD field")
        result[key] = value
    return result


def _schema_term(value: str) -> str:
    return value.rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]


def _dynamic_content_unresolved(soup, *, has_material: bool) -> bool:
    """Observe a pending placeholder or unreadable shell, not a script filename.

    A static material index may load analytics or describe downloading files.
    Those observations say nothing about missing document content. Explicit
    pending content and an external-script shell with no readable body remain
    unknown even though no JS is executed here.
    """
    for text in soup.find_all(string=_LOADING_PLACEHOLDER):
        if not isinstance(text, Comment) and text.find_parent(_NON_CONTENT_TAGS) is None:
            return True
    if has_material or soup.find("script", src=True) is None:
        return False
    content = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    for text in content.find_all(string=True):
        if (not isinstance(text, Comment) and text.strip()
                and text.find_parent((*_NON_CONTENT_TAGS, "h1", "h2", "h3", "h4", "h5", "h6")) is None):
            return False
    return True


def _embedded_document_limitations(soup) -> list[str]:
    """Observe bounded declared structures without inventing material URLs.

    Non-material Event/Organization declarations are harmless. Malformed or
    unexamined structure stays partial; no JS, external context or URL is read.
    """
    limitations = []
    scripts = soup.find_all("script", attrs={"type": _JSONLD_MIME},
                            limit=_MAX_JSONLD_SCRIPTS + 1)
    if len(scripts) > _MAX_JSONLD_SCRIPTS:
        limitations.append("embedded_data_unresolved")
    for script in scripts[:_MAX_JSONLD_SCRIPTS]:
        raw = script.get_text()
        if len(raw.encode("utf-8")) > _MAX_JSONLD_BYTES:
            limitations.append("embedded_data_unresolved")
            continue
        try:
            value = json.loads(raw, parse_constant=_reject_jsonld_constant,
                               object_pairs_hook=_unique_jsonld_object)
        except (ValueError, RecursionError):
            limitations.append("embedded_data_unresolved")
            continue
        if not isinstance(value, (dict, list)):
            limitations.append("embedded_data_unresolved")
            continue
        # Root arrays and @graph contain nodes. Ordinary properties may have
        # literal arrays (sameAs, keywords, etc.); these are not invalid graphs.
        pending: list[tuple[Any, int, bool]] = [(value, 0, True)]
        visited = 0
        while pending:
            node, depth, requires_nodes = pending.pop()
            visited += 1
            if visited > _MAX_JSONLD_NODES or depth > _MAX_JSONLD_DEPTH:
                limitations.append("embedded_data_unresolved")
                break
            if isinstance(node, dict):
                graph = node.get("@graph")
                if graph is not None and not isinstance(graph, (dict, list)):
                    limitations.append("embedded_data_unresolved")
                declared = node.get("@type")
                types = [declared] if isinstance(declared, str) else declared
                if declared is not None:
                    if (not isinstance(types, list) or len(types) > _MAX_JSONLD_NODES
                            or not all(isinstance(kind, str) for kind in types)):
                        limitations.append("embedded_data_unresolved")
                    elif any(_schema_term(kind) in _DECLARED_DOCUMENT_TYPES for kind in types):
                        limitations.append("embedded_document_unresolved")
                if any(_schema_term(key) in _DOCUMENT_PROPERTIES and value is not None
                       for key, value in node.items()):
                    # Explicit content/encoding relations are useful even if
                    # the node omits @type or uses an unsupported document type.
                    # This is still only an unexamined declaration, not a URL
                    # extractor, original, or proof of document availability.
                    limitations.append("embedded_document_unresolved")
                children = ((child, key in {"@graph", "@included"})
                            for key, child in node.items())
            else:
                children = ((child, requires_nodes) for child in node)
            for child, child_requires_nodes in children:
                if child_requires_nodes and not isinstance(child, (dict, list)):
                    limitations.append("embedded_data_unresolved")
                if isinstance(child, (dict, list)):
                    if visited + len(pending) >= _MAX_JSONLD_NODES:
                        limitations.append("embedded_data_unresolved")
                        pending.clear()
                        break
                    pending.append((child, depth + 1, child_requires_nodes))
    return list(dict.fromkeys(limitations))


def _is_event_notice(folded: str) -> bool:
    return any(token in folded for token in _NOTICE_TITLE_TOKENS) and any(
        token in folded for token in _EVENT_TITLE_TOKENS
    )


def _has_strong_clue(folded: str) -> bool:
    return any(token in folded for token in _STRONG_TITLE_TOKENS) or any(
        pattern.search(folded) for pattern in _STRONG_TITLE_PATTERNS
    )


def _has_weak_clue(folded: str) -> bool:
    return any(token in folded for token in _WEAK_TITLE_TOKENS)


def _normalized_title(folded: str) -> str:
    return " ".join(folded.split()).strip(" :：-–—|")


def _is_section_label(folded: str) -> bool:
    return _normalized_title(folded) in _SECTION_LABEL_TITLES


def _is_in_site_chrome(anchor) -> bool:
    """True when the anchor sits in nav/header/footer chrome."""
    return anchor.find_parent(["nav", "header", "footer"]) is not None


def _is_document_path(path: str) -> bool:
    return path.lower().endswith(_DOCUMENT_SUFFIXES)


def _is_material_link(folded: str, path: str, *, has_date_context: bool,
                      in_chrome: bool) -> bool:
    """Decide whether an anchor is a business-material lead.

    Order matters: a title-only section label is navigation; a page-section
    legal veto wins unless a strong clue points at a document file; a strong
    clue wins; a legal document title is excluded; a weak/broad clue needs a
    document suffix or a dated item block; chrome-only links need a suffix.
    """
    if _is_section_label(folded) and not _is_document_path(path):
        # "Annual Reports" / "公告" as a listing link is navigation; the same
        # label pointing at a document file is the document itself.
        return False
    if in_chrome and not _is_document_path(path):
        return False
    if any(token in folded for token in _LEGAL_PAGE_TITLE_TOKENS):
        return _has_strong_clue(folded) and _is_document_path(path)
    if _has_strong_clue(folded):
        return True
    if any(token in folded for token in _LEGAL_DOCUMENT_TITLE_TOKENS):
        return False
    if any(token in folded for token in _NAVIGATION_TITLE_TOKENS):
        return False
    if _has_weak_clue(folded):
        return _is_document_path(path) or has_date_context
    return _is_document_path(path)


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


def _item_container(anchor, *, allow_div: bool = True):
    """Nearest item-level block: article/li/tr, optionally a one-link div.

    A wider wrapper is not an item container: its date children belong to the
    page or to a list, not to this anchor. Dates never use the div fallback,
    so a page-level "Last updated" cannot become a material date.
    """
    block = anchor.find_parent(["article", "li", "tr"])
    if block is not None:
        return block if len(block.find_all("a", href=True)) == 1 else None
    if not allow_div:
        return None
    block = anchor.find_parent("div")
    if block is not None and len(block.find_all("a", href=True)) == 1:
        return block
    return None


def _item_has_date(anchor) -> bool:
    block = _item_container(anchor)
    return block is not None and block.find("time") is not None


def _shorten(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0] or text[:limit]
    return cut.strip(" -|·\t") + "…"


def _item_title(anchor, title: str, folded: str) -> tuple[str, str]:
    """Recover the document name when the anchor text is only an icon label.

    Index tables often put the document name in a neighbouring cell and only
    "Download" inside the anchor; the item block supplies the real lead.
    """
    if _has_strong_clue(folded) or _has_weak_clue(folded):
        return title, folded
    block = _item_container(anchor)
    if block is None:
        return title, folded
    block_text = _shorten(block.get_text(" ", strip=True))
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
    pending: list[tuple[dict, bool, bool]] = []
    pending_limit = max_items * 10 + 30
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
        page_parts = urlsplit(page["url"])
        if (
            page_parts.scheme not in {"http", "https"}
            or not page_parts.hostname
            or page_parts.username
            or page_parts.password
        ):
            raise ValueError("invalid_index_page_url")
        soup = BeautifulSoup(original, "html.parser")
        limitations.extend(_embedded_document_limitations(soup))
        page_key = urlunsplit(
            (page_parts.scheme, page_parts.netloc, page_parts.path,
             page_parts.query, "")
        )
        page_sha256 = hashlib.sha256(original).hexdigest()
        page_has_material = False
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
            # never let a same-document/pagination anchor become a lead.
            dedupe_key = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
            )
            same_document = (
                parsed.scheme == page_parts.scheme
                and parsed.netloc == page_parts.netloc
                and parsed.path == page_parts.path
                and not _is_document_path(parsed.path)
            )
            if dedupe_key == page_key or same_document or dedupe_key in seen:
                continue
            title = _anchor_title(anchor)
            folded = title.casefold()
            if not (_has_strong_clue(folded) or _has_weak_clue(folded)):
                # Icon/table rows often carry the document name outside the
                # anchor text; prefer the item block when it names a document.
                recovered_title, recovered_folded = _item_title(
                    anchor, title, folded
                )
                if _has_strong_clue(recovered_folded) or _has_weak_clue(
                    recovered_folded
                ):
                    title, folded = recovered_title, recovered_folded
            material = _is_material_link(
                folded,
                parsed.path,
                has_date_context=_item_has_date(anchor),
                in_chrome=_is_in_site_chrome(anchor),
            )
            if not material and not _is_event_notice(folded):
                continue
            page_has_material = True
            seen.add(dedupe_key)
            published = anchor.get("data-date")
            if not published:
                block = _item_container(anchor, allow_div=False)
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
            notice = (not material) or any(
                t in folded for t in _NOTICE_TITLE_TOKENS
            )
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
                        "index_source_sha256": page_sha256,
                        "is_business_original": False,
                        "materiality": "not_assessed",
                        "metadata_only": True,
                    },
                    notice,
                    _is_document_path(parsed.path),
                )
            )
            if len(pending) >= pending_limit:
                break
        if _dynamic_content_unresolved(soup, has_material=page_has_material):
            limitations.append("dynamic_content_unresolved")
        if len(pending) >= pending_limit:
            limitations.append("item_limit_reached")
            break
    # Document files first, then other materials, then notices: navigation and
    # event links never consume the item budget ahead of a real document.
    materials = [(record, suffix) for record, notice, suffix in pending if not notice]
    notices = [record for record, notice, _suffix in pending if notice]
    materials.sort(key=lambda pair: not pair[1])
    ordered = [record for record, _suffix in materials]
    candidates = ordered[:max_items]
    if len(ordered) > max_items:
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
