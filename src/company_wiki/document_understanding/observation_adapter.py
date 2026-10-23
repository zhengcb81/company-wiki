"""Production adapter: existing narrative units -> frozen ``du-input/1``.

This is ROOT-owned integration code.  It does not re-parse a document, does not
re-hash an original, does not rewrite a locator, and does not touch disk: it
projects the units the existing parser already produced onto the frozen
``du-input/1`` wire so the pure route/structure packages can consume them.

The adapter projects actual parser geometry/font/page metadata and semantic
hints. It performs no gutter inference; ROOT invokes the single shared layout
engine through layout_bridge before structure building. Numbered text and
explicit parser/DOM heading hints remain supported for compatibility.

Everything else is passed through unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, cast
import hashlib
import json
import re

from company_wiki.document_normalization.form_fields import has_inline_form_response

INPUT_SCHEMA_VERSION = "du-input/1"

OBSERVATION_ADAPTER_VERSION = "du-observation-adapter/3"

_READING_LAYOUT_FIELDS = frozenset({"bbox", "page", "page_width", "page_height", "coordinate_frame", "rotation",
                                  "granularity", "font_size", "font_weight", "frame_converted", "cropbox", "cropbox_position"})
_FINE_LAYOUT_FIELDS = frozenset({"text", "bbox", "native_index", "char_start", "char_end", "char_start_supplied", "char_end_supplied",
                               "char_alignment", "page", "coordinate_frame", "row", "column", "table_id", "font_size", "font_weight", "font",
                               "span_index", "line_index", "block_index", "block", "line", "span", "partial_span",
                               "native_cell_char_start", "native_cell_char_end", "partial_cell", "flags", "source"})


def _fine_layout_field(key: str, value: Any) -> bool:
    if key not in _FINE_LAYOUT_FIELDS:
        return False
    # The public projector emits a neutral producer label here. A physical
    # location is not a source label and must not migrate from foreign metadata.
    return key != "source" or (isinstance(value, str) and len(value) <= 256
        and re.match(r"^(?:[A-Za-z]:[\\/]|\\\\|/|file:)", value) is None)


def _reading_layout_fields(metadata: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project the source owner's bounded transient geometry, never all metadata.

    Public snapshot projection owns fine-element bounds/alignment. This bridge
    neither truncates that original evidence nor replaces the source's old
    bbox/fonts/locator. Unknown whole-text/path fields are not transported.
    """
    reading = metadata.get("reading_layout")
    if not isinstance(reading, Mapping):
        return {}, {}
    supplied = reading.get("layout")
    layout = {key: deepcopy(value) for key, value in supplied.items() if key in _READING_LAYOUT_FIELDS} if isinstance(supplied, Mapping) else {}
    upstream = reading.get("upstream_hints")
    hints: dict[str, Any] = {}
    if isinstance(upstream, Mapping):
        for name in ("words", "cells", "font_runs", "spans"):
            entries = upstream.get(name)
            if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
                hints[name] = [{key: deepcopy(value) for key, value in entry.items() if _fine_layout_field(key, value)}
                               for entry in entries if isinstance(entry, Mapping)]
        if isinstance(upstream.get("geometry_granularity"), str):
            hints["geometry_granularity"] = upstream["geometry_granularity"]
    granularity = layout.get("granularity")
    if isinstance(granularity, str):
        layout["geometry_granularity"] = granularity
        hints["geometry_granularity"] = granularity
    version = reading.get("feature_version")
    if isinstance(version, str) and version:
        layout["reading_layout_feature_version"] = version
        hints["reading_layout_feature_version"] = version
    return layout, hints

# --- Q&A page: the two role sets the parser emits (ROOT decision, DU-S-ADAPT-5) --------
#
# A Q&A page is emitted TWICE by the production parser:
#
# * once as flat ``pdf_text_block`` fragments whose ``source_role`` is ``qa_text_shadow``
#   (the page's plain text layer, fragmented by sentence), and
# * once as structured units built from the detected Q&A structure, whose roles are
#   ``investor_question`` / ``management`` and which carry ``qa_state``/``qa_group_id``
#   metadata giving the speaker and the turn.
#
# Measured on the real 万润 IR original (302 units): 219 shadow, 18 investor_question,
# 55 management, 8 company_filing. Of the 74 packages the new layer produced from it,
# 53 were built *entirely* from shadow units and only 14 entirely from structured roles,
# while only 10 of 192 shadow strings were byte-identical to a structured string. The two
# copies are therefore mostly the SAME content fragmented differently, not two documents.
#
# ROOT decision, matching what production selection already does
# (``narrative_candidates._EXCLUDED_ROLES`` contains ``qa_text_shadow``):
#
# * BOTH copies stay in the observation. The structure lane needs them to pair a question
#   with its answer across pages, and deleting either side would make coverage look better
#   than it is. The lane is forbidden from dropping either copy.
# * The shadow copy is NOT selectable evidence. It is the text layer, so selecting from it
#   double-counts the same sentence and loses the speaker attribution that the structured
#   roles carry. It is marked on the wire so selection can exclude it without having to
#   know the parser's internal role name.
QA_SHADOW_ROLE = "qa_text_shadow"

#: Structured Q&A roles: these are the selectable ones.
QA_STRUCTURED_ROLES: frozenset[str] = frozenset({"investor_question", "management"})

#: ``hints`` key marking a unit as the non-selectable text-layer copy of a Q&A page.
QA_SHADOW_HINT = "qa_text_shadow"

_NUMBERED_HEADING = (
    # (regex, level)
    (r"^第[一二三四五六七八九十百零\d]+[节章编]\s*\S", 1),
    (r"^第[一二三四五六七八九十百零\d]+[部分篇]\s*\S", 1),
    (r"^(?:Item|ITEM)\s+\d+[A-Za-z]?\.?\s+\S", 1),
    (r"^[IVXLC]+\.\s+\S", 1),
    (r"^[一二三四五六七八九十]+[、．.]\s*\S", 2),
    (r"^（[一二三四五六七八九十]+）\s*\S", 3),
    (r"^\([一二三四五六七八九十]+\)\s*\S", 3),
    # A dotted outline number must be followed by a title word, not by a year
    # or a quantity: "1.2 经营情况" is a heading, "2020 年5 月" is prose.
    (r"^\d{1,2}(?:\.\d{1,2}){1,3}\s*[\u4e00-\u9fffA-Za-z]\S*", 3),
)

_HEADING_TERMINATOR = ("。", "；", ";", "：", ":")
_UNIT_CAPTION = (
    "单位：",
    "单位:",
    "币种：",
    "币种:",
    "单位: ",
    "人民币万元",
    "人民币元",
)

_MAX_HEADING_CHARS = 60


def _part_heading_level(text: str) -> int | None:
    value = " ".join(text.strip().split())
    match = re.fullmatch(
        r"PART\s+(II|I)\b(?:\s*[.—–:−-]\s*|\s+)?(.*)", value, re.IGNORECASE
    )
    if not match or len(value) > 100:
        return None
    title = match.group(2).strip()
    if not title:
        return 1
    if title.casefold() in {"financial information", "other information"}:
        return 1
    if (
        title == title.upper()
        and title.isascii()
        and re.fullmatch(r"[A-Z][A-Z /&-]*", title)
        and not title.startswith(("OF ", "IS ", "WAS ", "AND "))
    ):
        return 1
    return None


def _is_item_label(text: str) -> bool:
    return (
        re.fullmatch(r"Item\s+\d{1,2}[A-Za-z]?\.?", text.strip(), re.IGNORECASE)
        is not None
    )


def _is_item_heading(text: str) -> bool:
    return (
        re.match(r"^Item\s+\d{1,2}[A-Za-z]?\b(?:\.|\s|$)", text.strip(), re.IGNORECASE)
        is not None
    )


def _heading_level(text: str, metadata: Mapping[str, Any]) -> int | None:
    """Return a heading level only from evidence actually present.

    Two admissible sources, in order:

    1. An explicit HTML heading level carried through as ``heading_level``.
    2. A numbering scheme in the text itself, which is self-evident.

    A short block with a background colour is also accepted when the parser
    supplies ``heading_like``; the current PDF parser does not emit it, which is
    why an unnumbered paper heading such as ``Store Network`` stays a paragraph
    rather than being guessed into a section.  Guessing there would misfire on
    the equally short table fragments on the same page.
    """
    explicit = metadata.get("heading_level")
    tag = metadata.get("tag_name")
    if (
        explicit is None
        and isinstance(tag, str)
        and tag.lower() in {"h1", "h2", "h3", "h4", "h5", "h6"}
    ):
        explicit = int(tag[1])
    if isinstance(explicit, int) and not isinstance(explicit, bool) and explicit > 0:
        return explicit
    if has_inline_form_response(text):
        return None
    if metadata.get("heading_like") is True:
        return 2
    if _part_heading_level(text) is not None:
        return 1
    if _is_item_label(text):
        return 1

    stripped = text.strip()
    if not stripped or len(stripped) > _MAX_HEADING_CHARS or "\n" in stripped:
        return None
    if stripped.endswith(_HEADING_TERMINATOR):
        return None
    for pattern, level in _NUMBERED_HEADING:
        if re.match(pattern, stripped):
            return level
    return None


def _heading_level_source(metadata: Mapping[str, Any]) -> str:
    explicit = metadata.get("heading_level")
    tag = metadata.get("tag_name")
    if (isinstance(explicit, int) and not isinstance(explicit, bool) and explicit > 0
            or isinstance(tag, str) and tag.lower() in {"h1", "h2", "h3", "h4", "h5", "h6"}):
        return "native"
    return "layout" if metadata.get("heading_like") is True else "numbering"


def _is_unit_caption(text: str) -> bool:
    stripped = text.strip().lstrip("（(")
    return stripped.startswith(_UNIT_CAPTION)


def _bbox_of(unit: Any) -> tuple[float, float, float, float] | None:
    value = unit.metadata.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        coords = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None
    x0, y0, x1, y1 = coords
    if x1 <= x0 or y1 <= y0:
        return None
    return coords  # type: ignore[return-value]


def _detect_gutter_x(
    blocks: Sequence[tuple[float, float, float, float]],
    page_width: float | None = None,
) -> float | None:
    """Compatibility query only; canonical observation performs no inference."""
    from types import SimpleNamespace
    from .layout_hints.columns import compute_cuts
    from .layout_hints.contract import Unit, WorkBudget

    if not blocks:
        return None
    units = [SimpleNamespace(bbox=box, ordinal=i) for i, box in enumerate(blocks)]
    extent = max(box[2] for box in blocks) - min(box[0] for box in blocks)
    # This legacy query supplies the two fields consumed by compute_cuts; it
    # does not manufacture native/fine geometry or a second layout engine.
    cuts = compute_cuts(cast(list[Unit], units), page_width or extent, WorkBudget(2000000))
    return cuts[0] if len(cuts) == 1 else None


def _lane_for(
    x0: float, x1: float, gutter: float, text_span: tuple[float, float]
) -> int | None:
    """Assign a lane only to a block that sits clearly on one side.

    A block that straddles the gutter (a full-width table, a banner) belongs to
    neither lane and gets ``None`` rather than a guessed side.
    """
    if x0 < gutter <= x1:
        return None
    del text_span
    return 0 if x1 <= gutter else 1


def _locator_of(unit: Any, metadata: Mapping[str, Any]) -> str:
    """Return the unit's existing replay locator without inventing one.

    Two real forms exist in this repository and both must survive:

    * the format parsers (HTML/PPTX/DOCX) put their opaque locator in
      ``metadata['source_locator']``;
    * the narrative parser builds units from ``EvidenceCoordinates`` and the
      canonical locator is derived from those coordinates, e.g.
      ``loc:v1/page:62/paragraph:3``.  That derivation is what the read layer
      validates against, so it must be used rather than the unit id.

    A unit id is a content hash, so falling back to it would make a citation
    un-replayable: nothing in the read layer can turn a hash back into a page and
    paragraph.  The id is kept only as a last resort for stub units that carry
    neither form.
    """
    existing = metadata.get("source_locator")
    if isinstance(existing, str) and existing:
        return existing
    coordinates = getattr(unit, "coordinates", None)
    derive = getattr(coordinates, "locator", None)
    if callable(derive):
        try:
            derived = derive()
        except Exception:  # pragma: no cover - defensive for foreign stubs
            derived = None
        if isinstance(derived, str) and derived:
            return derived
    return str(unit.unit_id)


def _qa_hints(unit: Any, metadata: Mapping[str, Any]) -> dict[str, str]:
    """Project source-owned speaker and association, without inventing a turn.

    Native official JSON fields already identify the question and answer; they
    do not carry the PDF parser's ``qa_state`` or an artificial Q:/A: prefix.
    Association is scoped to the unit's actual parent, since one observation
    may contain several source originals. Prepared remarks carry a speaker but
    are explicitly not an answer to a neighbouring question.
    """
    state = str(metadata.get("qa_state") or "")
    original_role = metadata.get("original_role")
    group = (metadata.get("official_record_group_id")
             or metadata.get("qa_group_id"))
    speaker: str | None = None
    if original_role == "company_statement":
        speaker = "prepared_statement"
    elif unit.source_role == "investor_question":
        speaker = "investor"
    elif unit.source_role == "management":
        speaker = "management" if group or state else "prepared_statement"
    elif original_role == "company_official_answer":
        speaker = "company"
    elif state:
        speaker = "management" if "answer" in state else "investor"
    hints = {"speaker": speaker} if speaker else {}
    if group:
        parent = getattr(unit, "source_id", None)
        if parent:
            # Include the native parent even if a provider reuses a record ID.
            association = json.dumps([str(parent), str(group)], ensure_ascii=False)
            hints["turn_id"] = "source-qa:" + hashlib.sha256(
                association.encode("utf-8")
            ).hexdigest()
        else:
            # Foreign legacy stubs have no parent beyond their envelope.
            hints["turn_id"] = str(group)
    return hints


def build_observation(
    units: Sequence[Any],
    *,
    source_id: str,
    source_sha256: str,
    title: str = "",
    declared_kind: str = "unknown",
    mime_type: str = "application/pdf",
    language: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    native_scan: str = "complete",
    opaque_pages: Sequence[int] = (),
    deferred_pages: Sequence[int] = (),
) -> dict[str, Any]:
    """Project existing narrative units onto the frozen ``du-input/1`` wire.

    The function is pure with respect to the inputs: units are read, never
    modified, and no locator, id or byte digest is recomputed.
    """
    source_metadata = dict(metadata or {})
    if native_scan not in {"complete", "partial", "unavailable"}:
        native_scan = "unavailable"

    # A real body Part is not its earlier table-of-contents table copy.
    body_parts = [
        i
        for i, unit in enumerate(units)
        if unit.unit_kind != "html_table_cell"
        and _part_heading_level(unit.raw_text) is not None
    ]
    has_body_parts = bool(body_parts)
    toc_tables = set()
    if body_parts:
        first = body_parts[0]
        toc_intro = any(
            " ".join(unit.raw_text.casefold().split())
            in {"table of contents", "contents", "目录"}
            for unit in units[:first]
        )
        if toc_intro:
            toc_tables = {
                unit.metadata.get("table_index")
                for unit in units[:first]
                if unit.unit_kind == "html_table_cell"
                and _part_heading_level(unit.raw_text) is not None
            }
            toc_tables.discard(None)

    emitted: list[dict[str, Any]] = []
    for ordinal, unit in enumerate(units):
        coordinates = unit.coordinates
        page = coordinates.page_number
        metadata = unit.metadata
        box = _bbox_of(unit)

        layout: dict[str, Any] = {}
        if box is not None:
            layout["bbox"] = list(box)
            page_width = metadata.get("page_width")
            if isinstance(page_width, (int, float)):
                layout["page_width"] = float(page_width)
            page_height = metadata.get("page_height")
            if isinstance(page_height, (int, float)):
                layout["page_height"] = float(page_height)
        for key in (
            "font_size",
            "font_weight",
            "geometry_feature_version",
            "geometry_granularity",
        ):
            if key in metadata:
                layout[key] = metadata[key]
        hints: dict[str, Any] = {}
        reading_layout, fine_hints = _reading_layout_fields(metadata)
        layout.update(reading_layout)
        hints.update(fine_hints)
        parent_source_id = getattr(unit, "source_id", None)
        if isinstance(parent_source_id, str) and parent_source_id:
            # One projection may contain units from several native originals.
            # This is attribution, not another source verification step.
            hints["source_id"] = parent_source_id
        if metadata.get("geometry_granularity") and "geometry_granularity" not in hints:
            hints["geometry_granularity"] = metadata["geometry_granularity"]
        level = _heading_level(unit.raw_text, metadata)
        if (
            has_body_parts
            and unit.unit_kind == "html_paragraph"
            and metadata.get("heading_level") is None
            and metadata.get("tag_name") not in {"h1", "h2", "h3", "h4", "h5", "h6"}
            and _part_heading_level(unit.raw_text) is None
            and not _is_item_heading(unit.raw_text)
        ):
            # Text numbering is relative outline evidence, not native DOM depth.
            level = None
        if level is not None and unit.unit_kind in {"pdf_text_block", "html_heading"}:
            hints["heading_level"] = level
            hints["heading_level_source"] = _heading_level_source(metadata)
        if coordinates.table_index is not None:
            hints["table_id"] = f"p{page}:t{coordinates.table_index}"
        if coordinates.row_index is not None:
            hints["row"] = coordinates.row_index
        if coordinates.column_index is not None:
            hints["column"] = coordinates.column_index
        if unit.unit_kind.startswith("html_"):
            table_index = metadata.get("table_index")
            if isinstance(table_index, int) and not isinstance(table_index, bool):
                hints["table_id"] = f"html:t{table_index}"
            for source_key, target in (
                ("row_index", "row"),
                ("column_index", "column"),
            ):
                value = metadata.get(source_key)
                if isinstance(value, int) and not isinstance(value, bool):
                    hints[target] = value
        hints.update(_qa_hints(unit, metadata))
        source_view = metadata.get("native_source_view")
        if isinstance(source_view, Mapping):
            native_carriers = source_view.get("carriers")
            if isinstance(native_carriers, list) and native_carriers:
                # Native parser observations only; provider/form declarations
                # never synthesize a carrier. The collector owns validation.
                hints["native_source_carriers"] = deepcopy(native_carriers)
            native_tables = source_view.get("tables")
            if isinstance(native_tables, list) and native_tables:
                # A transient native grid is shared read-only by the binder;
                # it never enters canonical EvidenceSpan/model metadata.
                hints["native_tables"] = native_tables
        if unit.unit_kind.startswith("html_") and isinstance(
            metadata.get("dom_path"), str
        ):
            hints["dom_path"] = metadata["dom_path"]
        # Mark the non-selectable text-layer copy explicitly, so a consumer does not have to
        # know the parser's internal role name to avoid double-counting a Q&A page.
        if unit.source_role == QA_SHADOW_ROLE:
            hints[QA_SHADOW_HINT] = True

        kind = _wire_kind(unit, coordinates)
        if (
            unit.unit_kind in {"pdf_text_block", "html_paragraph", "html_heading"}
            and level is not None
        ):
            if (
                has_body_parts
                and _is_item_heading(unit.raw_text)
                and metadata.get("heading_level") is None
                and metadata.get("tag_name") not in {"h1", "h2", "h3", "h4", "h5", "h6"}
            ):
                level = 2
            hints["heading_level"] = level
            hints["heading_level_source"] = _heading_level_source(metadata)
            kind = "heading"
        if (
            unit.unit_kind == "html_table_cell"
            and metadata.get("table_index") in toc_tables
        ):
            kind = "toc_entry"
            hints.pop("heading_level", None)
            hints.pop("heading_level_source", None)
        emitted.append(
            {
                "unit_id": unit.unit_id,
                "ordinal": ordinal,
                "locator": _locator_of(unit, metadata),
                "page": page,
                "text": unit.raw_text,
                "kind": kind,
                "language": unit.language,
                "role": unit.source_role,
                "layout": layout,
                "hints": hints,
            }
        )

    resolved_language = language
    if resolved_language is None:
        resolved_language = next(
            (unit.language for unit in units if getattr(unit, "language", None)), "und"
        )

    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
        "metadata": {
            "title": title,
            "declared_kind": declared_kind,
            "mime_type": mime_type,
            "language": resolved_language,
            **{
                key: value
                for key, value in source_metadata.items()
                if key
                in {"regime", "form_type", "published_at", "period_end", "revision", "native_layout_frontend_version"}
            },
        },
        "coverage": {
            "native_scan": native_scan,
            "opaque_pages": [int(page) for page in opaque_pages],
            "deferred_pages": [int(page) for page in deferred_pages],
        },
        "units": emitted,
    }


def _wire_kind(unit: Any, coordinates: Any) -> str:
    """Map a parser unit kind onto the frozen wire vocabulary."""
    if unit.unit_kind == "pdf_table_row":
        # Row 0 of an extracted table is its header; the parser already carries
        # the header cells on every row, so this is evidence, not a guess.
        if coordinates.row_index == 0:
            return "table_header"
        return "table_row"
    if unit.unit_kind == "pdf_table_header":
        return "table_header"
    if unit.unit_kind == "html_heading":
        return "heading"
    if unit.unit_kind == "html_footnote":
        return "footnote"
    if unit.unit_kind == "html_table_cell":
        return "table_row"
    if _is_unit_caption(unit.raw_text):
        return "table_caption"
    if unit.unit_kind == "pdf_text_block":
        if _heading_level(unit.raw_text, unit.metadata) is not None:
            return "heading"
        if unit.raw_text.lstrip().startswith(("注：", "注:", "Note:", "Note：")):
            return "footnote"
        return "paragraph"
    return "paragraph"


def is_selectable(unit: Mapping[str, Any]) -> bool:
    """True when a ``du-input/1`` unit may be selected as evidence.

    The only exclusion today is the Q&A text-layer shadow: it duplicates the structured
    Q&A units, so selecting from it double-counts a sentence and loses the speaker
    attribution. Excluding it from *selection* is not deletion -- the unit stays in the
    observation and in the structure lane's member lists, so a package's dependency closure
    can still reach it.
    """
    if unit.get("role") == QA_SHADOW_ROLE:
        return False
    hints = unit.get("hints")
    if isinstance(hints, Mapping) and hints.get(QA_SHADOW_HINT) is True:
        return False
    return True


def selectable_unit_ids(observation: Mapping[str, Any]) -> list[str]:
    """The selectable unit ids of an observation, in reading order."""
    return [
        str(unit["unit_id"])
        for unit in observation.get("units", ())
        if is_selectable(unit)
    ]


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "QA_SHADOW_HINT",
    "QA_SHADOW_ROLE",
    "QA_STRUCTURED_ROLES",
    "build_observation",
    "is_selectable",
    "selectable_unit_ids",
]
