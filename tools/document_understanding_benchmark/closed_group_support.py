"""Test oracle for canonical spans from a production-validated selection.

Caller trust boundary: only current typed selection/closed packages, or stored
material reopened and checked by its public source owner. This is NOT bundle
ingress validation, nor another font/geometry verifier. Never infer native
continuity merely from an unvalidated foreign mapping that claims its kind.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import re
from typing import Any
import unicodedata

from company_wiki.source_contract import EvidenceSpan

_ROLES = frozenset({"company_filing", "management", "unknown"})
_CJK = re.compile(r"[\u3400-\u9fff]")
_CJK_PUNCTUATION = frozenset("。！？；，、：）》】”’（《【“‘")


def _fold(text: str) -> str:
    # Normalize observed spacing; never remove arbitrary whitespace to build
    # English words, alter decimal tokens, or merge separate source statements.
    return " ".join(unicodedata.normalize("NFC", text).split())


def _range_fold(text: str) -> str:
    """Observe CJK line wraps inside ONE byte-verified native range.

    English words, decimal quantities and unit boundaries keep their spaces.
    This is quote observation after source-owner replay, not range creation.
    """
    value = _fold(text)
    return re.sub(r"(?<=[\u3400-\u9fff。，！？；：“”‘’（）]) +(?=[\u3400-\u9fff。，！？；：“”‘’（）])", "", value)


def _terminal(text: str) -> bool:
    return text.rstrip().rstrip("\"'”’）)]》").endswith(("。", "！", "？", ".", "!", "?", ";", "；"))


def _prose(span: EvidenceSpan) -> bool:
    value = span.structured_value
    return (span.parser_name == "selective_narrative_parser"
        and value.get("unit_kind") == "pdf_text_block"
        and value.get("source_role") in _ROLES
        and not value.get("heading_level") and not value.get("is_heading")
        and value.get("table_id") is None and span.coordinates.table_index is None)


def _edge(left: EvidenceSpan, right: EvidenceSpan, *, cross_block: bool) -> bool:
    a, b = left.structured_value, right.structured_value
    if (not _prose(left) or not _prose(right) or left.source_id != right.source_id
        or left.coordinates.page_number is None
        or left.coordinates.page_number != right.coordinates.page_number
        or type(left.coordinates.paragraph_index) is not int
        or right.coordinates.paragraph_index != left.coordinates.paragraph_index + 1
        or a.get("source_role") != b.get("source_role")):
        return False
    block_a, block_b = a.get("pdf_block"), b.get("pdf_block")
    if type(block_a) is not int or type(block_b) is not int:
        return False
    if cross_block:
        # Production already owns actual font/frame/scope/closure proof.
        # Non-text blocks may leave native block-number gaps; sentence endings
        # within a proven window do not remove the following plan/qualifier.
        return block_b >= block_a
    if block_a == block_b:
        end, start = a.get("block_char_end"), b.get("block_char_start")
        return bool(a.get("block_sha256") and a.get("block_sha256") == b.get("block_sha256")
            and type(end) is int and type(start) is int and 0 <= start-end <= 2)
    return False


def _join(chain: Sequence[EvidenceSpan]) -> str:
    result = chain[0].raw_text or ""
    for span in chain[1:]:
        right = span.raw_text or ""
        left_char = result.rstrip()[-1:]
        right_char = right.lstrip()[:1]
        # Closing/opening CJK punctuation also borders native Chinese text.
        # This only chooses a boundary between proven original fragments; it
        # does not delete whitespace inside either original span or join two
        # separated Latin tokens into an invented English word.
        cjk_boundary = bool(
            _CJK.fullmatch(left_char) and (_CJK.fullmatch(right_char) or right_char in _CJK_PUNCTUATION)
            or _CJK.fullmatch(right_char) and left_char in _CJK_PUNCTUATION
        )
        separator = "" if cjk_boundary else " "
        result = result.rstrip() + separator + right.lstrip()
    return _fold(result)


def _native_body(material: Sequence[EvidenceSpan]) -> tuple[EvidenceSpan, ...]:
    # Compact context includes required headings, potentially on another page.
    # It does not preserve full transient body membership/font proof. Therefore
    # prefix context is single-span support only, not a guessed part of prose.
    first = next((i for i, span in enumerate(material)
        if "reading_plan" in span.structured_value.get("selection_reasons", ())), None)
    if first is None:
        return ()
    body = tuple(material[first:])
    if (len(body) > 8 or len({s.structured_value.get("pdf_block") for s in body}) > 4
        or sum(len(s.raw_text or "") for s in body) > 2048):
        raise ValueError("native continuity window exceeds its published bounds")
    if (not all(_prose(span) for span in body) or not body
        or not _terminal(body[-1].raw_text or "")):
        return ()
    return body


def _locations(evidence_spans: Sequence[EvidenceSpan], reading_context: Mapping[str, Any] | None):
    if any(not isinstance(span, EvidenceSpan) for span in evidence_spans):
        raise TypeError("oracle requires typed canonical EvidenceSpan objects")
    rows = tuple(evidence_spans)
    positions = {span.span_id: i for i, span in enumerate(rows)}
    if len(positions) != len(rows):
        raise ValueError("selection has duplicate span ids")
    output = [(tuple([span]), "single") for span in rows]
    if reading_context is None:
        return output
    if reading_context.get("schema_version") != "du-production-reading/1":
        raise ValueError("oracle requires canonical production reading context")
    seen = set()
    for group in reading_context.get("groups", ()):
        ids = group.get("evidence_ids")
        if (not isinstance(ids, (tuple, list)) or not ids or len(ids) != len(set(ids))
            or any(sid not in positions for sid in ids)):
            raise ValueError("group references must be unique, complete canonical spans")
        indices = [positions[sid] for sid in ids]
        if indices != sorted(indices):
            raise ValueError("group members must retain original selection order")
        digest = sha256(json.dumps(list(ids),separators=(",",":")).encode()).hexdigest()
        expected = "urn:company-wiki:reading-group:sha256:"+digest
        if group.get("group_id") != expected or expected in seen:
            raise ValueError("group id must match its canonical ordered closure")
        seen.add(expected)
        material = tuple(rows[i] for i in indices)
        native = group.get("kind") == "native_continuity"
        # Prevalidate native hard bounds even if a query happens to match only
        # one row; malformed declarations cannot silently become support.
        if native:
            _native_body(material)
        output.append((material, "native_continuity" if native else "group"))
    return output


def _eligible(span: EvidenceSpan, anchor: Mapping[str, Any], *, source_id: str, role: Any) -> bool:
    if span.source_id != source_id or anchor.get("source_id", source_id) != source_id or not span.raw_text:
        return False
    actual_role = span.structured_value.get("source_role")
    if actual_role not in _ROLES or role is not None and actual_role != role:
        return False
    kind = anchor.get("location_kind")
    if kind not in {None, "page", "document"}:
        return False
    return kind == "document" or anchor.get("page") is None or span.coordinates.page_number == anchor["page"]


def _supports(anchor: Mapping[str, Any], material: Sequence[EvidenceSpan], kind: str, *, source_id: str, role: Any) -> bool:
    raw_quote = anchor.get("exact_quote")
    if not isinstance(raw_quote, str) or not raw_quote or len(raw_quote) > 2048:
        return False
    quote = _fold(raw_quote)
    if any(_eligible(span,anchor,source_id=source_id,role=role) and (
            _range_fold(raw_quote) in _range_fold(span.raw_text or "")
            if span.parser_name == "native_pdf_range_parser" and span.parser_version == "0.1.0"
            and span.structured_value.get("unit_kind") == "pdf_native_range"
            else quote in _fold(span.raw_text or ""))
           for span in material):
        return True
    eligible = _native_body(material) if kind == "native_continuity" else tuple(material)
    chain: list[EvidenceSpan] = []
    for span in eligible:
        if not _eligible(span,anchor,source_id=source_id,role=role):
            chain = []
            continue
        if chain and not _edge(chain[-1],span,cross_block=kind == "native_continuity"):
            chain = []
        chain.append(span)
        # Ordinary groups may use original same-block character fragments only.
        # Both cases remain bounded and never flatten a whole page/group.
        if len(chain) > 8 or sum(len(s.raw_text or "") for s in chain) > 2048:
            chain = [span]
        if len(chain) > 1 and quote in _join(chain):
            return True
    return False


def score_facts(facts: Sequence[Mapping[str, Any]], *, evidence_spans: Sequence[EvidenceSpan],
                reading_context: Mapping[str, Any] | None, source_id: str) -> list[dict[str, Any]]:
    """Match each OR of AND anchors within ONE canonical closed group/span.

    `source_id` is the immutable source verified by the caller against its gold.
    Page anchors stay exact; explicit document anchors handle native HTML which
    has no physical page. This function neither opens nor validates a source.
    """
    locations = _locations(evidence_spans,reading_context)
    output = []
    for fact in facts:
        supports = fact["any_support_sets"]
        role = fact.get("role")
        found = any(support and any(all(_supports(anchor,material,kind,source_id=source_id,role=role)
                         for anchor in support) for material,kind in locations) for support in supports)
        individually = any(support and all(any(_supports(anchor,(span,),"single",source_id=source_id,role=role)
            for span in evidence_spans) for anchor in support) for support in supports)
        output.append({"id":fact["id"], "supported":bool(found),
                       "all_anchors_individually_present":bool(individually)})
    return output


__all__ = ["score_facts"]
