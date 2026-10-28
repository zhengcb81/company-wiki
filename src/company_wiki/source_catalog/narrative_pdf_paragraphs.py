"""Transient, source-exact paragraph boundary proposals for the PDF reading owner.

Proposals are untrusted layout observations. They cannot supply canonical text,
fonts, facts or locators. Alignment is bounded and complete over original units.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
import math
from pathlib import Path
import re
import unicodedata
from typing import Any

from company_wiki.resource_budget import WorkBudget
from company_wiki.document_normalization import table_shapes
from .narrative_document import DocumentStructure, NarrativeUnit

PARAGRAPH_ALIGNMENT_VERSION = "pdf-paragraph-membership/1"
_FRAMES = {"dict", "rawdict", "text", "words", "span"}
_END = re.compile(r"[。！？.!?;；][\"'”’）)\]》]*$")
_DEPENDENT = re.compile(r"^(?:該|该|上述|其(?![他它])|由於|由于|因此|百萬|百万|億元|亿元|萬元|万元|"
                        r"million\b|billion\b|and\b|but\b|which\b|because\b|this\b)", re.I)


@dataclass(frozen=True)
class ParagraphProposal:
    source_id: str
    source_sha256: str
    page: int
    text: str
    bbox: tuple[float, ...]
    page_width: float
    page_height: float
    rotation: int = 0
    coordinate_frame: str = "dict"


@dataclass(frozen=True)
class GapTriage:
    pages: tuple[int, ...]
    reasons: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ParagraphAlignment:
    parsed: DocumentStructure
    accepted_groups: int
    rejected_groups: int


def paragraph_triage_dependencies() -> dict[str, str]:
    """Bind the shared shape implementation actually consumed by this owner."""
    return {"company_wiki.document_normalization.table_shapes": sha256(
        Path(table_shapes.__file__).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()}


@dataclass(frozen=True)
class _GapObservation:
    complete_value_row: bool
    dependent_tail: bool
    terminal: bool


def _comparison(text: str) -> str:
    # Explicit marker/space compatibility only. No OCR/glyph/quote repair.
    text = re.sub(r"^\s*[•●▪]\s*", "", text)
    return "".join(unicodedata.normalize("NFKC", text).split())


def _layout(unit: NarrativeUnit) -> dict[str, Any]:
    return dict(unit.metadata.get("reading_layout", {}).get("layout", {}))


def _box(value: Any, width: Any, height: Any) -> tuple[float, ...] | None:
    numbers = (*value, width, height) if isinstance(value, (tuple, list)) and len(value) == 4 else ()
    if not numbers or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in numbers):
        return None
    a, b, c, d, w, h = map(float, numbers)
    return (a, b, c, d) if 0 <= a < c <= w and 0 <= b < d <= h else None


def triage_paragraph_gaps(parsed: DocumentStructure, *, work_budget: WorkBudget,
                          max_pages: int = 3) -> GapTriage:
    """Rank unresolved physical fractures, never duplicate business selection."""
    if type(max_pages) is not int or not 0 <= max_pages <= 16:
        raise ValueError("paragraph page limit must be between 0 and 16")
    work_budget.charge(1 + len(parsed.units))
    from company_wiki.document_understanding.observation_adapter import build_observation
    from company_wiki.document_understanding.narrative_continuity import build_native_continuity
    observation = build_observation(parsed.units, source_id=parsed.source_id, source_sha256=parsed.source_sha256)
    provenance = {u.unit_id: {"source_id": u.source_id, "paragraph_index": u.coordinates.paragraph_index,
        **{key: u.metadata.get(key) for key in ("pdf_block", "block_sha256", "block_char_start", "block_char_end")}}
        for u in parsed.units}
    physical = build_native_continuity(observation["units"], provenance=provenance, work_budget=work_budget)
    proven = {(edge["left"], edge["right"]) for edge in physical["adjacency_edges"]}
    boundary = physical["unexamined_from_index"]
    reasons: list[dict[str, Any]] = []
    page_scores: dict[int, int] = {}
    prepared: dict[int, _GapObservation] = {}

    def observe(index: int) -> _GapObservation:
        if index not in prepared:
            text = parsed.units[index].raw_text
            work_budget.charge(1 + len(text))
            prepared[index] = _GapObservation(
                table_shapes.observe_value_cells(text).complete_value_row,
                bool(_DEPENDENT.search(text)), bool(_END.search(text)),
            )
        return prepared[index]

    for index, (left, right) in enumerate(zip(parsed.units, parsed.units[1:])):
        work_budget.charge()
        page = left.coordinates.page_number
        if (page is None or page != right.coordinates.page_number
                or left.unit_kind != "pdf_text_block" or right.unit_kind != "pdf_text_block"
                or left.source_role != right.source_role
                or (left.unit_id, right.unit_id) in proven or boundary is not None and index + 1 >= boundary):
            continue
        a, b = _layout(left), _layout(right)
        box_a, box_b = (_box(x.get("bbox"), x.get("page_width"), x.get("page_height")) for x in (a, b))
        if (box_a is None or box_b is None or a.get("coordinate_frame") != b.get("coordinate_frame")
                or a.get("rotation") != b.get("rotation") or a.get("column") != b.get("column")
                or min(box_a[2], box_b[2]) <= max(box_a[0], box_b[0])):
            continue
        left_observation, right_observation = observe(index), observe(index + 1)
        if left_observation.terminal:
            continue
        # A literal label/value shape also fits native-wrapped prose. Positive
        # amount/dependency evidence must survive that weaker observation.
        reason: str | None
        if right_observation.dependent_tail:
            reason = "amount_or_dependent_tail"
        elif left_observation.complete_value_row and right_observation.complete_value_row:
            continue
        else:
            reason = ("unproven_wrapped_prose" if len(left.raw_text) >= 32
                      and re.match(r"[a-z\u3400-\u9fff]", right.raw_text) else None)
        if reason is not None:
            score = (3 if re.search(r"\d$", left.raw_text) and right_observation.dependent_tail
                     else 2 if right_observation.dependent_tail else 1)
            page_scores[page] = max(score, page_scores.get(page, 0))
            reasons.append({"page": page, "reason": reason, "priority": score,
                            "left": left.unit_id, "right": right.unit_id})
    pages = tuple(sorted(page_scores, key=lambda p: (-page_scores[p], p))[:max_pages])
    return GapTriage(pages, tuple(r for r in reasons if r["page"] in pages)[:64])


def align_paragraphs(parsed: DocumentStructure, proposals: Sequence[ParagraphProposal], *,
                     work_budget: WorkBudget) -> ParagraphAlignment:
    """Strict complete members in native order; overlapping proposals all lose."""
    if len(proposals) > 2048 or len(parsed.units) > 50_000:
        raise ValueError("paragraph alignment input bound exceeded")
    work_budget.charge(1 + len(parsed.units) + len(proposals))
    pages: dict[int | None, list[tuple[int, NarrativeUnit]]] = {}
    for i, unit in enumerate(parsed.units):
        pages.setdefault(unit.coordinates.page_number, []).append((i, unit))
    candidates = []
    for proposal in proposals:
        rows = pages.get(proposal.page, ())
        work_budget.charge(1 + len(rows) + len(proposal.text))
        box = _box(proposal.bbox, proposal.page_width, proposal.page_height)
        if (box is None or proposal.source_id != parsed.source_id
                or proposal.source_sha256 != parsed.source_sha256 or proposal.coordinate_frame not in _FRAMES
                or type(proposal.page) is not int or proposal.page < 1
                or type(proposal.rotation) is not int or proposal.rotation not in {0, 90, 180, 270}
                or not 0 < len(proposal.text) <= 16_384):
            continue
        members = []
        invalid = False
        for index, unit in rows:
            layout = _layout(unit)
            native_box = _box(layout.get("bbox"), layout.get("page_width"), layout.get("page_height"))
            if native_box is None:
                continue
            cx, cy = (native_box[0] + native_box[2]) / 2, (native_box[1] + native_box[3]) / 2
            # Original blocks may include multiple sentence fragments, all of
            # which must be included when the paragraph covers that block.
            if not box[0] - 2 <= cx <= box[2] + 2 or not box[1] - 2 <= cy <= box[3] + 2:
                continue
            # Docling glyph bounds and native font ascender bounds differ.
            # Require the WHOLE native block within a small measured font
            # padding, never merely its centre (a thin stripe is not a page).
            size = layout.get("font_size")
            tolerance = min(3., max(2., 0.25 * size)) if isinstance(size, (int, float)) and not isinstance(size, bool) and math.isfinite(size) and size > 0 else 2.
            if (native_box[0] < box[0] - tolerance or native_box[1] < box[1] - tolerance
                    or native_box[2] > box[2] + tolerance or native_box[3] > box[3] + tolerance):
                invalid = True
            if (unit.source_id != parsed.source_id or unit.unit_kind != "pdf_text_block"
                    or unit.source_role not in {"company_filing", "management", "unknown"}
                    or layout.get("coordinate_frame") != proposal.coordinate_frame
                    or layout.get("rotation") != proposal.rotation
                    or layout.get("page_width") != proposal.page_width
                    or layout.get("page_height") != proposal.page_height):
                invalid = True
            members.append((index, unit))
        if invalid or not 2 <= len(members) <= 64:
            continue
        indices = [i for i, _ in members]
        texts = [u.raw_text for _, u in members]
        work_budget.charge(sum(map(len, texts)))
        first_paragraph = members[0][1].coordinates.paragraph_index
        if type(first_paragraph) is not int:
            continue
        if (indices != list(range(indices[0], indices[-1] + 1))
                or len({u.unit_id for _, u in members}) != len(members)
                or any(type(u.coordinates.paragraph_index) is not int for _, u in members)
                or [u.coordinates.paragraph_index for _, u in members] != list(range(
                    first_paragraph, first_paragraph + len(members)))
                or len({u.source_role for _, u in members}) != 1
                or _comparison(" ".join(texts)) != _comparison(proposal.text)):
            continue
        columns = {_layout(u).get("column") for _, u in members} - {None}
        if len(columns) > 1:
            continue
        candidates.append(members)
    counts: dict[int, int] = {}
    for members in candidates:
        for index, _ in members:
            counts[index] = counts.get(index, 0) + 1
    updated = list(parsed.units)
    accepted = 0
    for members in candidates:
        if any(counts[index] != 1 for index, _ in members):
            continue
        accepted += 1
        digest = sha256((parsed.source_sha256 + "\0" + "\0".join(u.unit_id for _, u in members)).encode()).hexdigest()
        for position, (index, unit) in enumerate(members):
            proof = {"version": PARAGRAPH_ALIGNMENT_VERSION, "group": digest,
                     "position": position, "count": len(members),
                     "previous": members[position - 1][1].unit_id if position else None,
                     "next": members[position + 1][1].unit_id if position + 1 < len(members) else None}
            reading = dict(unit.metadata.get("reading_layout", {}))
            updated[index] = replace(unit, metadata={**unit.metadata,
                "reading_layout": {**reading, "paragraph_membership": proof}})
    return ParagraphAlignment(replace(parsed, units=tuple(updated)), accepted, len(proposals) - accepted)
