"""Verify gold quote anchors against the real original they claim.

This is the ``错页行`` (wrong page / wrong line) mechanism the card names: a
gold anchor is only worth what its ``exact_quote`` is worth, and a quote that
is not on the page it claims cannot be repaired by any amount of matching
logic later.

The helper is deliberately dumb: it extracts text from the bound original
(PyMuPDF for PDFs, tag-stripped text for HTML/DOCX/plain text) and checks the
anchor's quote with the same containment fold the oracle uses
(:func:`textutil.text_contains`). It never edits gold and never consults the
selector's output.

Used by the real-data tests and by the DU5-CORPUS authoring QA run, which
verifies every anchor before the gold set is frozen.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from typing import Any

from tools.document_understanding_benchmark.textutil import text_contains
from tools.document_understanding_benchmark.gold import resolve_original

HTML_SUFFIXES = {".htm", ".html"}
TEXT_SUFFIXES = {".txt", ".md"}
DOCX_SUFFIXES = {".docx"}


def _strip_html(raw: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    body = re.sub(r"</(p|div|tr|br|h[1-6])[^>]*>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    return html.unescape(body)


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf8", errors="replace")
    xml = xml.replace("</w:p>", "\n")
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def extract_text_pages(path: Path) -> dict[int | None, str]:
    """Return ``{page_number: text}``; a single ``None`` key means no pages.

    Page numbers are physical and 1-based, matching the parser's
    ``enumerate(document, start=1)`` convention.
    """

    target = Path(path)
    suffix = target.suffix.casefold()
    if suffix == ".pdf":
        import fitz  # local dependency of the reading host, not of the oracle

        pages: dict[int | None, str] = {}
        with fitz.open(target) as document:
            for index, page in enumerate(document):
                pages[index + 1] = page.get_text()
        return pages
    if suffix in HTML_SUFFIXES:
        return {None: _strip_html(target.read_text(encoding="utf8", errors="replace"))}
    if suffix in DOCX_SUFFIXES:
        return {None: _docx_text(target)}
    raw = target.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return {None: raw.decode(encoding)}
        except UnicodeDecodeError:
            continue
    return {None: raw.decode("utf-8", errors="replace")}


def verify_gold_anchors(gold: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    """Check every anchor of one gold record against the original at ``path``.

    Returns one row per anchor: ``ok`` shows whether the quote is present at
    the claimed location (page key ``None`` = whole-document sources).
    """

    source_id = str(gold.get("sample_id") or "anchor-source")
    source = resolve_original(source_id, gold.get("source_sha256"), {source_id: str(path)})
    if source["status"] != "OK":
        raise ValueError("gold original SHA mismatch or source unavailable")
    pages = extract_text_pages(path)
    document_text = pages.get(None, "")
    document_lines = document_text.splitlines()
    rows: list[dict[str, Any]] = []
    for fact in gold.get("facts") or []:
        for set_index, support_set in enumerate(fact.get("any_support_sets") or []):
            for anchor_index, anchor in enumerate(support_set):
                quote = anchor.get("exact_quote") or ""
                page = anchor.get("page")
                line = anchor.get("line")
                location_kind = anchor.get("location_kind") or (
                    "line" if line is not None else "page" if page is not None else "document"
                )
                if location_kind == "line":
                    last = anchor.get("line_end", line)
                    valid = (isinstance(line, int) and not isinstance(line, bool)
                             and isinstance(last, int) and not isinstance(last, bool)
                             and 1 <= line <= last <= len(document_lines))
                    haystack = "\n".join(document_lines[line-1:last]) if valid else ""
                    where = f"line {line}" + (f"-{last}" if last != line else "")
                elif location_kind == "document":
                    # Historical HTML gold carries a virtual page=1 but is
                    # explicitly marked document-kind: match the whole source,
                    # never a fabricated physical page.
                    haystack = document_text
                    where = "document"
                elif location_kind == "page":
                    haystack = pages.get(page, "")
                    where = f"page {page}"
                else:
                    haystack = ""
                    where = f"unsupported location {location_kind}"
                rows.append(
                    {
                        "sample_id": gold.get("sample_id"),
                        "fact_id": fact.get("id"),
                        "set_index": set_index,
                        "anchor_index": anchor_index,
                        "where": where,
                        "ok": bool(quote) and text_contains(haystack, quote),
                        "quote": quote,
                    }
                )
    return rows
