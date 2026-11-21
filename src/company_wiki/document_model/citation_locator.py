"""Match an excerpt or native locator against one normalized original."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
from typing import Any
import unicodedata

from .narrative import NarrativeUnit


@dataclass(frozen=True)
class CitationBlock:
    kind: str
    value: str
    page_kind: str | None
    text: str


def native_paragraphs(units: Iterable[NarrativeUnit]) -> Iterable[CitationBlock]:
    for unit in units:
        coordinates = unit.coordinates
        kind = "table" if coordinates.table_index is not None else "paragraph"
        yield CitationBlock(kind, coordinates.locator(), None, unit.raw_text)


def native_pdf_pages(pages: Iterable[str]) -> Iterable[CitationBlock]:
    for index, text in enumerate(pages, start=1):
        yield CitationBlock("page", str(index), "physical", text)


def match_native_citation(
    blocks: Iterable[CitationBlock],
    *,
    quote: str | None,
    locator: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Replay a selected block or find the single occurrence of an excerpt."""
    requested = (locator["kind"], locator["value"], locator["page_kind"]) if locator else None
    excerpt = locator.get("excerpt") if locator else None
    anchor = quote if quote is not None else excerpt
    result = {
        "locator": None,
        "normalization": "unicode-nfc-whitespace-remove/1",
        "quote_sha256": hashlib.sha256(anchor.encode("utf-8")).hexdigest() if anchor else None,
    }

    def normalized(value: str) -> str:
        return "".join(unicodedata.normalize("NFC", value).split())

    needles = tuple(dict.fromkeys(normalized(value) for value in (anchor, excerpt) if value))
    hit = None
    for block in blocks:
        if requested is not None and (block.kind, block.value, block.page_kind) != requested:
            continue
        if needles:
            body = normalized(block.text)
            if not all(needle in body for needle in needles):
                continue
            start = body.find(needles[0])
            if body.find(needles[0], start + 1) >= 0 and requested is None:
                return {**result, "state": "ambiguous", "reason": "evidence_quote_not_unique"}
        if hit is not None:
            return {**result, "state": "ambiguous", "reason": "evidence_quote_not_unique"}
        hit = block
    if hit is None:
        return {**result, "state": "not_found",
                "reason": "evidence_locator_not_found" if requested else "evidence_quote_not_found"}
    return {
        **result,
        "state": "verified",
        "locator": {"kind": hit.kind, "value": hit.value, "page_kind": hit.page_kind, "excerpt": anchor},
        "text": hit.text,
    }
