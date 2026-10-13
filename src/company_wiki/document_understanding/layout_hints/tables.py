"""Candidate table regions, row groups and caption/footnote context groups.

Everything here is structural *hint* evidence: quantities are never invented,
columns are only claimed when cell geometry proves them, and wrapped rows that
cannot be resolved are flagged instead of guessed.  Bands are addressed by
index (they are plain dataclasses and not hashable).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .contract import Page, Unit
from .geometry import (
    Band,
    Cell,
    ColumnSlot,
    assign_cell_columns,
    band_cells,
    band_geometry_units,
    cluster_column_slots,
)
from .text_evidence import (
    has_quantity_token,
    is_caption_title,
    is_date_text,
    is_footnote_text,
    is_period_text,
    is_plain_sentence,
    is_unit_line,
    normalize_ws,
)

SENTENCE_PUNCTUATION = set("，。；！？,.;!?:")

NUMBERED_HEADING = re.compile(r"^(?:第[一二三四五六七八九十百零0-9]+[章节部篇]|[一二三四五六七八九十]+[、．.]|[（(][一二三四五六七八九十0-9]+[）)]|\d+[、．.](?!\d))")


def _stripped_of_numbers(text: str) -> str:
    tokens = []
    for token in normalize_ws(text).split(" "):
        stripped = token.strip("()（）[]【】:：，,")
        if stripped and not any(ch.isdigit() for ch in stripped):
            tokens.append(token)
    return " ".join(tokens)


def _has_sentence_punctuation(text: str) -> bool:
    return any(ch in SENTENCE_PUNCTUATION for ch in _stripped_of_numbers(text))


def band_context_kind(band: Band, cells: list[Cell]) -> str | None:
    """Classify one-cell bands as caption/period/unit/footnote context."""
    if len(cells) != 1:
        return None
    text = normalize_ws(cells[0].text)
    if not text:
        return None
    if is_footnote_text(text):
        return "footnote"
    if is_caption_title(text):
        return "caption"
    if is_unit_line(text) or is_period_text(text):
        return "period"
    return None


def _is_prose_band(band: Band, page_width: float | None, cells: list[Cell]) -> bool:
    if len(cells) == 1:
        text = normalize_ws(cells[0].text)
        if is_plain_sentence(text):
            return True
        if page_width and cells[0].bbox[2] - cells[0].bbox[0] > 0.55 * page_width:
            return _has_sentence_punctuation(cells[0].text)
        return False
    return any(_has_sentence_punctuation(cell.text) for cell in cells)


def band_has_quantity(band: Band, cells: list[Cell]) -> bool:
    for cell in cells:
        text = cell.text
        if is_period_text(text) or is_date_text(text):
            continue
        if has_quantity_token(text):
            return True
    return False


@dataclass
class RegionDraft:
    page: Page
    bands: list[Band]
    member_indices: list[int] = field(default_factory=list)
    leading_context: list[int] = field(default_factory=list)
    trailing_context: list[int] = field(default_factory=list)
    context_kinds: dict = field(default_factory=dict)
    granularity: bool = False
    header_indices: list[int] = field(default_factory=list)
    row_indices: list[int] = field(default_factory=list)
    slots: list[ColumnSlot] = field(default_factory=list)
    diagnostics: list[tuple] = field(default_factory=list)

    def bbox(self) -> tuple[float, float, float, float]:
        boxes = [self.bands[i].bbox for i in self.member_indices]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )


@dataclass
class PageBands:
    page: Page
    bands: list[Band] = field(default_factory=list)
    cells: dict = field(default_factory=dict)  # band index -> list[Cell]
    meta: dict = field(default_factory=dict)  # band index -> {"context","prose","multi","quantity"}


def analyse_page(page: Page, page_units: list[Unit], budget, furniture_ids: set | None = None) -> PageBands:
    furniture_ids = furniture_ids or set()
    result = PageBands(page=page)
    result.bands = band_geometry_units(page_units, budget)
    for index, band in enumerate(result.bands):
        if not budget.charge(1):
            break
        cells = band_cells(band, budget)
        result.cells[index] = cells
        context = band_context_kind(band, cells)
        single = len(band.units) == 1
        result.meta[index] = {
            "context": context,
            "prose": context is None and _is_prose_band(band, page.width, cells),
            "multi": len(cells) >= 2,
            "quantity": band_has_quantity(band, cells),
            "furniture": all(unit.unit_id in furniture_ids for unit in band.units),
            "heading_like": (
                single
                and context is None
                and not band_has_quantity(band, cells)
                and NUMBERED_HEADING.match(normalize_ws(band.units[0].text)) is not None
            ),
        }
    return result


def build_region_drafts(page_bands: PageBands, budget) -> list[RegionDraft]:
    bands = page_bands.bands
    meta = page_bands.meta
    members = [
        i
        for i in range(len(bands))
        if meta.get(i)
        and meta[i]["context"] is None
        and not meta[i]["prose"]
        and not meta[i]["furniture"]
        and not meta[i]["heading_like"]
    ]
    gap_tol = _run_gap_tolerance([bands[i] for i in members]) if members else 22.0

    runs: list[list[int]] = []
    current: list[int] = []
    for index in members:
        if not budget.charge(1):
            break
        if not current:
            current = [index]
            continue
        gap = bands[index].bbox[1] - bands[current[-1]].bbox[3]
        if gap <= gap_tol:
            current.append(index)
        else:
            runs.append(current)
            current = [index]
    if current:
        runs.append(current)

    drafts: list[RegionDraft] = []
    for run in runs:
        multi = [i for i in run if meta[i]["multi"]]
        if len(multi) >= 2:
            draft = RegionDraft(
                page=page_bands.page,
                bands=bands,
                member_indices=list(run),
                granularity=False,
            )
            _attach_context(draft, page_bands, gap_tol)
            drafts.append(draft)
            continue
        for sub_run in _aligned_subruns(run, page_bands):
            draft = RegionDraft(
                page=page_bands.page,
                bands=bands,
                member_indices=list(sub_run),
                granularity=True,
            )
            _attach_context(draft, page_bands, gap_tol)
            drafts.append(draft)
    return drafts


def _aligned_subruns(run: list[int], page_bands: PageBands) -> list[list[int]]:
    """Grid rows: whole-row single units with aligned edges and quantities."""
    cells, meta = page_bands.cells, page_bands.meta
    page = page_bands.page
    tolerance = max(4.0, 0.012 * (page.width or 595.0))
    subruns: list[list[int]] = []
    current: list[int] = []
    for index in run:
        if meta[index]["multi"] or len(cells[index]) != 1:
            if current:
                subruns.append(current)
                current = []
            continue
        box = cells[index][0].bbox
        if current:
            reference = cells[current[0]][0].bbox
            if abs(box[0] - reference[0]) <= tolerance and abs(box[2] - reference[2]) <= tolerance:
                current.append(index)
                continue
            subruns.append(current)
            current = [index]
        else:
            current = [index]
    if current:
        subruns.append(current)
    return [
        sub
        for sub in subruns
        if len(sub) >= 3 and sum(1 for i in sub if meta[i]["quantity"]) >= 2
    ]


def _run_gap_tolerance(bands: list[Band]) -> float:
    heights = sorted(band.mean_height for band in bands)
    median = heights[len(heights) // 2] if heights else 12.0
    return max(22.0, 2.5 * median)


def _attach_context(draft: RegionDraft, page_bands: PageBands, gap_tol: float) -> None:
    bands, meta = page_bands.bands, page_bands.meta
    first = draft.member_indices[0]
    cursor = first - 1
    leading: list[int] = []
    reference_top = bands[first].bbox[1]
    while cursor >= 0 and meta.get(cursor, {}).get("context") in {"caption", "period"}:
        gap = reference_top - bands[cursor].bbox[3]
        if gap > gap_tol:
            break
        leading.insert(0, cursor)
        reference_top = bands[cursor].bbox[1]
        cursor -= 1
    draft.leading_context = leading

    last = draft.member_indices[-1]
    cursor = last + 1
    trailing: list[int] = []
    reference_bottom = bands[last].bbox[3]
    while cursor < len(bands) and meta.get(cursor, {}).get("context") == "footnote":
        gap = bands[cursor].bbox[1] - reference_bottom
        if gap > gap_tol:
            break
        trailing.append(cursor)
        reference_bottom = bands[cursor].bbox[3]
        cursor += 1
    draft.trailing_context = trailing

    for index in draft.leading_context:
        draft.context_kinds[index] = meta[index]["context"]
    for index in draft.trailing_context:
        draft.context_kinds[index] = "footnote"


def analyse_region(draft: RegionDraft, page_bands: PageBands, budget) -> None:
    """Split member bands into header block / rows and map cells to slots."""
    cells, meta = page_bands.cells, page_bands.meta
    quantity_members = [i for i in draft.member_indices if meta[i]["quantity"]]
    seed_cells = [cell for i in quantity_members for cell in cells[i]]
    if not seed_cells:
        seed_cells = [cell for i in draft.member_indices for cell in cells[i]]
    draft.slots = [] if draft.granularity else cluster_column_slots(seed_cells, budget)

    header: list[int] = []
    rows: list[int] = []
    in_header = True
    has_quantity_rows = bool(quantity_members)
    for index in draft.member_indices:
        if not budget.charge(1):
            rows.append(index)
            in_header = False
            continue
        if in_header and not meta[index]["quantity"]:
            # a header block only exists in front of quantity rows; a
            # quantity-less table keeps at most one header band
            if has_quantity_rows or not header:
                header.append(index)
                if not has_quantity_rows and len(header) >= 1:
                    in_header = False
                continue
        in_header = False
        rows.append(index)
    draft.header_indices = header
    draft.row_indices = rows

    _flag_wrapped_rows(draft, page_bands, budget)


def _flag_wrapped_rows(draft: RegionDraft, page_bands: PageBands, budget) -> None:
    """A column slot that vanishes for one line and reappears is a wrapped row."""
    cells = page_bands.cells
    position = {index: pos for pos, index in enumerate(draft.member_indices)}
    slot_presence: dict = {}
    for index in draft.member_indices:
        for cell in cells[index]:
            budget.charge(1)
            column, _span = assign_cell_columns(cell, draft.slots)
            if column is None:
                continue
            slot_presence.setdefault(column, []).append((position[index], index, cell))
    heights = [page_bands.bands[i].mean_height for i in draft.member_indices]
    median_height = sorted(heights)[len(heights) // 2] if heights else 12.0
    seen: set = set()
    for entries in slot_presence.values():
        entries.sort(key=lambda item: item[0])
        for (pos_a, index_a, cell_a), (pos_b, index_b, cell_b) in zip(entries, entries[1:]):
            if pos_b - pos_a <= 1:
                continue
            gap = cell_b.bbox[1] - cell_a.bbox[3]
            key = (index_a, index_b)
            if gap <= 2.0 * median_height and key not in seen:
                seen.add(key)
                draft.diagnostics.append(
                    (
                        "LOGICAL_ROW_UNRESOLVED",
                        sorted({u.unit_id for u in cell_a.members} | {u.unit_id for u in cell_b.members}),
                        "column content wraps across line bands; logical rows kept separate",
                    )
                )
