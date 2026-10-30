"""Exact ranges of a named transient native PDF page view.

The view formats the existing single DICT snapshot in original block order;
it is not a substring coordinate system of PDF bytes. A caller supplies the
shared engine's already closed body members. This layer verifies their source
characters once, and never joins model prose, routes or classifies a document.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any
import unicodedata

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan

from .narrative_document import NarrativeUnit

NATIVE_PAGE_VIEW_FEATURE_VERSION = "native-pdf-page-view/1"
NATIVE_RANGE_SCHEMA_VERSION = "native-pdf-range/1"
NATIVE_RANGE_PARSER_NAME = "native_pdf_range_parser"
NATIVE_RANGE_PARSER_VERSION = "0.1.0"
NATIVE_RANGE_BASE_PARSER_VERSION = "0.1.1"
NATIVE_RANGE_CURRENT_PARSER_VERSION = "0.1.1"
# Historical range/base bindings are immutable. The new base produces a
# distinct range identity, even when the source text and coordinates agree.
NATIVE_RANGE_BASE_VERSIONS = MappingProxyType({
    NATIVE_RANGE_PARSER_VERSION: NATIVE_RANGE_BASE_PARSER_VERSION,
    NATIVE_RANGE_CURRENT_PARSER_VERSION: "0.1.2",
})
NATIVE_RANGE_LIMITS = MappingProxyType(
    {"max_total_chars": 2_000_000, "max_page_chars": 200_000}
)


def _text(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n"))


def native_range_limits(limits: Mapping[str, int] | None = None) -> dict[str, int]:
    """Only lower the bounded transient view budget; no new permission gate."""
    output = dict(NATIVE_RANGE_LIMITS)
    if limits is None:
        return output
    if not isinstance(limits, Mapping) or set(limits) - set(output):
        raise ValueError("unknown native range limit")
    for key, value in limits.items():
        if type(value) is not int or value < 0:
            raise ValueError("native range limits must be nonnegative integers")
        output[key] = min(value, output[key])
    return output


def build_native_page_view(
    blocks: Sequence[tuple[int, tuple[float, ...], str]], *, max_chars: int = 200_000
) -> Mapping[str, Any] | None:
    """One immutable view, retaining source strings by reference, never per unit."""
    if type(max_chars) is not int or max_chars < 0:
        raise ValueError("native page view limit must be a nonnegative integer")
    max_chars = min(max_chars, NATIVE_RANGE_LIMITS["max_page_chars"])
    records: list[Mapping[str, Any]] = []
    texts: list[str] = []
    position = 0
    previous = -1
    for block, bbox, source_text in blocks:
        if (
            type(block) is not int
            or block <= previous
            or not isinstance(source_text, str)
        ):
            raise ValueError(
                "native view blocks must retain unique original order and text"
            )
        previous = block
        # Bound normalization/allocation work too, before creating any new
        # string. A large decomposed block can fall back without losing its
        # original units even if NFC would make a somewhat smaller view.
        if position + bool(texts) + len(source_text) > max_chars:
            return None
        value = _text(source_text)
        if not value:
            continue
        start = position + bool(texts)
        end = start + len(value)
        if end > max_chars:
            return None
        records.append(
            MappingProxyType(
                {
                    "pdf_block": block,
                    "bbox": tuple(bbox),
                    "block_sha256": sha256(source_text.encode()).hexdigest(),
                    "source_text": source_text,
                    "view_char_start": start,
                    "view_char_end": end,
                    "nfc_unchanged": source_text == value,
                }
            )
        )
        texts.append(value)
        position = end
    if not records:
        return None
    text = "\n".join(texts)
    return MappingProxyType(
        {
            "schema_version": NATIVE_PAGE_VIEW_FEATURE_VERSION,
            "text": text,
            "page_view_sha256": sha256(text.encode()).hexdigest(),
            "blocks": tuple(records),
            "by_block": MappingProxyType(
                {record["pdf_block"]: record for record in records}
            ),
        }
    )


def _member_range(
    unit: NarrativeUnit, view: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    meta = unit.metadata
    block = meta.get("pdf_block")
    start, end = meta.get("block_char_start"), meta.get("block_char_end")
    if type(block) is not int or type(start) is not int or type(end) is not int:
        return None
    record = view["by_block"].get(block)
    if record is None:
        return None
    original = record["source_text"]
    if (
        not 0 <= start < end <= len(original)
        or meta.get("block_sha256") != record["block_sha256"]
        or _text(original[start:end]).strip() != unit.raw_text
    ):
        return None
    # Existing parser offsets refer to pre-NFC native block characters. The
    # uncommon decomposed case is mapped from actual source prefixes, not from
    # a guessed alignment or repaired unit string.
    if record["nfc_unchanged"]:
        a, b = start, end
    else:
        a, b = len(_text(original[:start])), len(_text(original[:end]))
    a += record["view_char_start"]
    b += record["view_char_start"]
    # Trim only the member's actual offset range, exactly like the base parser.
    while a < b and view["text"][a].isspace():
        a += 1
    while b > a and view["text"][b - 1].isspace():
        b -= 1
    if view["text"][a:b] != unit.raw_text:
        return None
    return MappingProxyType(
        {
            "unit_id": unit.unit_id,
            "locator": unit.coordinates.locator(),
            "text_sha256": unit.text_sha256,
            "pdf_block": block,
            "block_sha256": record["block_sha256"],
            "block_char_start": start,
            "block_char_end": end,
            "view_char_start": a,
            "view_char_end": b,
        }
    )


def native_range_unit(members: Sequence[NarrativeUnit]) -> NarrativeUnit | None:
    """Verify source ranges of an already geometry/scope-closed native window."""
    if not 1 <= len(members) <= 8 or any(
        not isinstance(u, NarrativeUnit) for u in members
    ):
        return None
    first = members[0]
    range_version = next((version for version, base in NATIVE_RANGE_BASE_VERSIONS.items()
                          if base == first.parser_version), None)
    if range_version is None:
        return None
    view = first.metadata.get("native_source_view")
    if (
        not isinstance(view, MappingProxyType)
        or view.get("schema_version") != NATIVE_PAGE_VIEW_FEATURE_VERSION
    ):
        return None
    if (
        first.coordinates.page_number is None
        or type(first.coordinates.paragraph_index) is not int
    ):
        return None
    ranges: list[Mapping[str, Any]] = []
    previous_index: int | None = None
    for unit in members:
        paragraph = unit.coordinates.paragraph_index
        if type(paragraph) is not int:
            return None
        if (
            unit.source_id != first.source_id
            or unit.coordinates.page_number != first.coordinates.page_number
            or unit.source_role != first.source_role
            or unit.source_role not in {"company_filing", "management"}
            or unit.language != first.language
            or unit.unit_kind != "pdf_text_block"
            or unit.parser_name != "selective_narrative_parser"
            or unit.parser_version != first.parser_version
            or unit.metadata.get("native_source_view") is not view
            or unit.coordinates.table_index is not None
            or (
                previous_index is not None
                and paragraph != previous_index + 1
            )
        ):
            return None
        binding = _member_range(unit, view)
        if binding is None:
            return None
        if ranges and (
            binding["view_char_start"] < ranges[-1]["view_char_end"]
            or view["text"][
                ranges[-1]["view_char_end"] : binding["view_char_start"]
            ].strip()
        ):
            return None
        ranges.append(binding)
        previous_index = paragraph
    if len({r["pdf_block"] for r in ranges}) > 4:
        return None
    start, end = ranges[0]["view_char_start"], ranges[-1]["view_char_end"]
    if end - start > 2048:
        return None
    raw = view["text"][start:end]
    coordinates = EvidenceCoordinates(
        page_number=first.coordinates.page_number,
        paragraph_index=first.coordinates.paragraph_index,
        char_start=start,
        char_end=end,
    )
    identity = {
        "coordinates": coordinates.locator(),
        "parser_name": NATIVE_RANGE_PARSER_NAME,
        "parser_version": range_version,
        "source_id": first.source_id,
        "text_sha256": sha256(raw.encode()).hexdigest(),
        "unit_kind": "pdf_native_range",
    }
    unit_id = (
        "urn:company-wiki:narrative-unit:sha256:"
        + sha256(
            json.dumps(
                identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )
    binding = MappingProxyType(
        {
            "schema_version": NATIVE_RANGE_SCHEMA_VERSION,
            "base_parser_version": first.parser_version,
            "coordinate_space": "native_page_view",
            "page_view_sha256": view["page_view_sha256"],
            "source_unit_ids": tuple(u.unit_id for u in members),
            "members": tuple(ranges),
        }
    )
    return NarrativeUnit(
        unit_id=unit_id,
        source_id=first.source_id,
        parser_name=NATIVE_RANGE_PARSER_NAME,
        parser_version=range_version,
        coordinates=coordinates,
        raw_text=raw,
        unit_kind="pdf_native_range",
        source_role=first.source_role,
        language=first.language,
        quality_flags=tuple(
            dict.fromkeys(flag for u in members for flag in u.quality_flags)
        ),
        metadata={"native_range": binding},
    )


def verify_native_range_span(
    span: EvidenceSpan,
    replay_units: Sequence[NarrativeUnit] | Mapping[str, NarrativeUnit],
) -> bool:
    """Bind every member and its exact view substring to fresh pinned-parser units."""
    if (
        span.parser_name != NATIVE_RANGE_PARSER_NAME
        or span.parser_version not in NATIVE_RANGE_BASE_VERSIONS
        or not isinstance(span.structured_value, Mapping)
        or span.structured_value.get("unit_kind") != "pdf_native_range"
    ):
        return False
    binding = span.structured_value.get("native_range")
    if (
        not isinstance(binding, Mapping)
        or binding.get("schema_version") != NATIVE_RANGE_SCHEMA_VERSION
        or binding.get("base_parser_version") != NATIVE_RANGE_BASE_VERSIONS[span.parser_version]
    ):
        return False
    ids = binding.get("source_unit_ids")
    if (
        not isinstance(ids, (tuple, list))
        or not 1 <= len(ids) <= 8
        or any(not isinstance(uid, str) for uid in ids)
        or len(ids) != len(set(ids))
    ):
        return False
    available = (
        replay_units
        if isinstance(replay_units, Mapping)
        else {unit.unit_id: unit for unit in replay_units}
    )
    if any(uid not in available for uid in ids):
        return False
    rebuilt = native_range_unit([available[uid] for uid in ids])
    return bool(
        rebuilt
        and rebuilt.parser_version == span.parser_version
        and rebuilt.source_id == span.source_id
        and rebuilt.coordinates == span.coordinates
        and rebuilt.raw_text == span.raw_text
        and rebuilt.metadata["native_range"] == binding
        and rebuilt.source_role == span.structured_value.get("source_role")
        and rebuilt.language == span.structured_value.get("language")
        and rebuilt.text_sha256 == span.structured_value.get("text_sha256")
        and rebuilt.quality_flags == span.quality_flags
    )


__all__ = [
    "NATIVE_PAGE_VIEW_FEATURE_VERSION",
    "NATIVE_RANGE_PARSER_NAME",
    "NATIVE_RANGE_PARSER_VERSION",
    "NATIVE_RANGE_BASE_PARSER_VERSION",
    "build_native_page_view",
    "native_range_unit",
    "native_range_limits",
    "verify_native_range_span",
]
