"""Bounded PDF layout from the parser's single native text/table reads.

This frontend owns source extraction and character provenance. The shared pure
layout projector owns validation/binding. No raw snapshot is written to disk,
no fine box is inferred from whitespace, and no original unit is regenerated.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import replace
import hashlib
import json
from math import isfinite
from time import monotonic
from typing import Any, Mapping, Sequence
import unicodedata

from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot
from company_wiki.document_normalization.layout_snapshots.identity import resolve_limits

PDF_READING_LAYOUT_FEATURE_VERSION = "pdf-reading-layout/2"
PDF_LAYOUT_CAPTURE_SCHEMA = "pdf-layout-capture/1"
PDF_LAYOUT_CAPTURE_STRATEGY = "requested-pages/1"


def _text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n"))


def _box(value: Any) -> list[float] | None:
    try:
        values = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if len(values) != 4 or not all(isfinite(item) for item in values):
        return None
    return values if values[0] < values[2] and values[1] < values[3] else None


class PdfLayoutCollector:
    """One document-wide budget; transient native records disappear per page."""

    def __init__(
        self, *, limits: Mapping[str, Any] | None = None, max_seconds: float = 15
    ):
        if (
            isinstance(max_seconds, bool)
            or not isinstance(max_seconds, (int, float))
            or not isfinite(max_seconds)
            or max_seconds < 0
        ):
            raise ValueError("layout_max_seconds must be a finite nonnegative number")
        self.limits = resolve_limits(limits)
        self.deadline = monotonic() + min(float(max_seconds), 15.0)
        self.pages: dict[int, dict] = {}
        self.diagnostics: list[dict] = []
        self.work = 0
        self.fine = 0
        self.processed = 0
        self.captured_pages = 0
        self.captured_fine = 0
        self.bound_ids: set[str] = set()
        self.failed = False
        self.exhausted = False
        # Source parsing opts into deferred fine capture after observing page
        # purpose. Native material is held for at most the current/previous page.
        # Direct collector callers retain their established immediate behavior.
        self.defer_capture = False
        self.pending_pages: dict[int, tuple[Any, Any, Mapping[str, Any]]] = {}
        self.capture_mode = "direct"
        self.source_page_count = 0
        self.max_seconds = min(float(max_seconds), 15.0)
        self.requested_pages: set[int] = set()
        self.captured_page_ids: set[int] = set()
        self.projected_page_ids: set[int] = set()

    def _diag(
        self, code: str, *, page: int | None = None, unit_id: str | None = None
    ) -> None:
        self.failed = True
        if len(self.diagnostics) < 128:
            item: dict[str, Any] = {
                "code": code,
                "unit_ids": [unit_id] if unit_id else [],
            }
            if page is not None:
                item["page"] = page
            self.diagnostics.append(item)

    def record_failure(self, code: str, *, page: int) -> None:
        """Optional layout failure never discards a successfully read original."""
        self._diag(code, page=page)

    def _take(self, cost: int = 1) -> bool:
        if self.exhausted:
            return False
        if monotonic() >= self.deadline:
            self.exhausted = True
            self._diag("LAYOUT_DEADLINE_EXCEEDED")
            return False
        if self.work + cost > self.limits["max_work_units"]:
            self.exhausted = True
            self._diag("LAYOUT_WORK_BUDGET_EXCEEDED")
            return False
        self.work += cost
        return True

    def _native_element(self, *, page: int) -> bool:
        if self.captured_fine >= self.limits["max_fine_elements"]:
            self._diag("NATIVE_FINE_ELEMENTS_DEFERRED", page=page)
            return False
        if not self._take():
            return False
        self.captured_fine += 1
        return True

    def read_snapshot(self, page: Any, page_number: int) -> Mapping[str, Any]:
        if self.defer_capture:
            return self._read_pending_snapshot(page, page_number)
        self.requested_pages.add(page_number)
        enabled = (
            self.captured_pages < self.limits["max_pages"]
            and self.limits["max_units"] > 0
            and self.limits["max_fine_elements"] > 0
            and self.captured_fine < self.limits["max_fine_elements"]
            and self._take()
        )
        if not enabled:
            self._diag("LAYOUT_CAPTURE_DEFERRED", page=page_number)
            return page.get_text("dict", sort=False)
        try:
            import fitz  # type: ignore[import-untyped]

            text_page = page.get_textpage(flags=fitz.TEXTFLAGS_DICT)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._diag("NATIVE_TEXT_PAGE_UNAVAILABLE", page=page_number)
            return page.get_text("dict", sort=False)
        snapshot = page.get_text("dict", sort=False, textpage=text_page)
        self.captured_pages += 1
        try:
            words = text_page.extractWORDS()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            words = []
            self._diag("NATIVE_WORD_GEOMETRY_UNAVAILABLE", page=page_number)
        try:
            self._capture(page, page_number, snapshot, words)
            self.captured_page_ids.add(page_number)
        except Exception:
            self.pages.pop(page_number, None)
            self._diag("NATIVE_LAYOUT_CAPTURE_FAILED", page=page_number)
        return snapshot

    def _read_pending_snapshot(self, page: Any, number: int) -> Mapping[str, Any]:
        """One native TextPage supplies base text and any later demanded fine view."""
        text_page = None
        if (self.limits["max_pages"] and self.limits["max_units"]
                and self.limits["max_fine_elements"] and self._take()):
            try:
                import fitz  # type: ignore[import-untyped]
                text_page = page.get_textpage(flags=fitz.TEXTFLAGS_DICT)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                self._diag("NATIVE_TEXT_PAGE_UNAVAILABLE", page=number)
        snapshot = (page.get_text("dict", sort=False, textpage=text_page)
                    if text_page is not None else page.get_text("dict", sort=False))
        # Image payload is never used by the text parser. Retain its original
        # block position/type, not full image bytes in the one-page lookahead.
        for block in snapshot.get("blocks", ()):
            if isinstance(block, dict) and block.get("type") != 0:
                block.pop("image", None)
                block.pop("mask", None)
        self.pending_pages[number] = (page, text_page, snapshot)
        return snapshot

    def capture_pending_page(self, number: int, *, requested: bool) -> None:
        """Capture a real demand once, before its canonical page units are emitted."""
        material = self.pending_pages.pop(number, None)
        if not requested:
            return
        self.requested_pages.add(number)
        enabled = (material is not None and material[1] is not None
                   and self.captured_pages < self.limits["max_pages"]
                   and self.processed < self.limits["max_units"]
                   and self.captured_fine < self.limits["max_fine_elements"]
                   and self._take())
        if not enabled:
            self._diag("LAYOUT_CAPTURE_DEFERRED", page=number)
            return
        assert material is not None  # enabled proves an existing native carrier
        page, text_page, snapshot = material
        try:
            words = text_page.extractWORDS()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            words = []
            self._diag("NATIVE_WORD_GEOMETRY_UNAVAILABLE", page=number)
        self.captured_pages += 1
        try:
            self._capture(page, number, snapshot, words)
            self.captured_page_ids.add(number)
        except Exception:
            self.pages.pop(number, None)
            self._diag("NATIVE_LAYOUT_CAPTURE_FAILED", page=number)

    def _capture(
        self, page: Any, number: int, snapshot: Mapping, words: Sequence
    ) -> None:
        crop = _box(getattr(page, "cropbox", None))
        position = getattr(page, "cropbox_position", None)
        try:
            crop_position = [
                float(getattr(position, "x")),
                float(getattr(position, "y")),
            ]
        except (AttributeError, TypeError, ValueError):
            crop_position = None
        if (
            crop is None
            or crop_position is None
            or not all(isfinite(v) for v in crop_position)
        ):
            self._diag("CROPBOX_FRAME_UNAVAILABLE", page=number)
        rect = getattr(page, "rect", None)
        record: dict[str, Any] = {
            "page": number,
            "width": snapshot.get("width"),
            "height": snapshot.get("height"),
            "dict_width": snapshot.get("width"),
            "dict_height": snapshot.get("height"),
            "rect_width": getattr(rect, "width", None),
            "rect_height": getattr(rect, "height", None),
            "rotation": getattr(page, "rotation", None),
            "coordinate_frame": "dict",
            "cropbox": crop,
            "cropbox_position": crop_position,
            "blocks": {},
            "tables": {},
        }
        self.pages[number] = record
        # DICT includes image blocks; native WORDS numbers only text blocks.
        # Both views come from the same TextPage, so use their actual ordering
        # instead of assigning a word to an image or the following paragraph.
        text_block_indices = {
            text_index: raw_index
            for text_index, raw_index in enumerate(
                index
                for index, block in enumerate(snapshot.get("blocks", ()))
                if block.get("type") == 0
            )
        }
        for block_no, block in enumerate(snapshot.get("blocks", ())):
            if block.get("type") != 0:
                continue
            if not self._take():
                break
            lines = block.get("lines", ())
            raw_lines = [
                "".join(span.get("text", "") for span in line.get("spans", ()))
                for line in lines
            ]
            full = "\n".join(raw_lines)
            trim = len(full) - len(full.lstrip())
            raw = full.strip()
            entry: dict[str, Any] = {
                "text": raw,
                "lines": raw_lines,
                "line_starts": [],
                "spans": [],
                "words": [],
            }
            position = 0
            for line_no, line in enumerate(lines):
                entry["line_starts"].append(position - trim)
                for span_no, span in enumerate(line.get("spans", ())):
                    if not self._native_element(page=number):
                        break
                    value = span.get("text", "")
                    start, end = (
                        max(0, position - trim),
                        min(len(raw), position + len(value) - trim),
                    )
                    entry["spans"].append(
                        {
                            "start": start,
                            "end": end,
                            "bbox": _box(span.get("bbox")),
                            "font_size": span.get("size"),
                            "font": span.get("font"),
                            "font_weight": ("bold" if span["flags"] & 16 else "regular")
                            if isinstance(span.get("flags"), int)
                            and not isinstance(span.get("flags"), bool)
                            else None,
                            "native_index": len(entry["spans"]),
                            "block": block_no,
                            "line": line_no,
                            "span": span_no,
                        }
                    )
                    position += len(value)
                position += 1
            record["blocks"][block_no] = entry
        cursors: dict[tuple[int, int], int] = {}
        for index, word in enumerate(words):
            if not self._native_element(page=number):
                self._diag("NATIVE_FINE_ELEMENTS_DEFERRED", page=number)
                break
            if len(word) < 8:
                self._diag("NATIVE_WORD_INDEX_UNAVAILABLE", page=number)
                continue
            native_block_no, line_no, word_no = word[5:8]
            word_block_no = text_block_indices.get(native_block_no)
            entry = record["blocks"].get(word_block_no)
            if (
                entry is None
                or not isinstance(line_no, int)
                or not 0 <= line_no < len(entry["lines"])
            ):
                self._diag("NATIVE_WORD_SOURCE_UNAVAILABLE", page=number)
                continue
            line_text = entry["lines"][line_no]
            key = (native_block_no, line_no)
            start = line_text.find(word[4], cursors.get(key, 0))
            if start < 0:
                self._diag("WORD_CHARACTER_ALIGNMENT_UNAVAILABLE", page=number)
                continue
            end = start + len(word[4])
            cursors[key] = end
            entry["words"].append(
                {
                    "text": word[4],
                    "bbox": list(word[:4]),
                    "native_index": index,
                    "block": word_block_no,
                    "native_text_block": native_block_no,
                    "line": line_no,
                    "word": word_no,
                    "start": start + entry["line_starts"][line_no],
                    "end": end + entry["line_starts"][line_no],
                }
            )
            entry["word_ends"] = None  # built once after capture, not per fragment
        for entry in record["blocks"].values():
            entry["words"].sort(key=lambda item: (item["start"], item["native_index"]))
            entry["word_ends"] = [item["end"] for item in entry["words"]]
            entry["span_ends"] = [item["end"] for item in entry["spans"]]
            entry["nfc_identity"] = entry["text"] == _text(entry["text"])

    def capture_table(
        self, page: int, index: int, table: Any, rows: Sequence[Sequence[str]]
    ) -> None:
        record = self.pages.get(page)
        if record is None:
            return
        try:
            native_rows = table.rows
        except (AttributeError, RuntimeError, ValueError):
            self._diag("NATIVE_CELL_GEOMETRY_UNAVAILABLE", page=page)
            return
        captured = []
        for row_no, row in enumerate(rows):
            if not self._take():
                break
            boxes = (
                getattr(native_rows[row_no], "cells", ())
                if row_no < len(native_rows)
                else ()
            )
            cells = []
            for column, value in enumerate(row):
                if not self._native_element(page=page):
                    break
                box = _box(boxes[column]) if column < len(boxes) else None
                if value and box is None:
                    self._diag("NATIVE_CELL_GEOMETRY_UNAVAILABLE", page=page)
                if value and box is not None:
                    cells.append(
                        {
                            "text": value,
                            "bbox": box,
                            "native_index": column,
                            "row": row_no,
                            "column": column,
                            "table_id": f"p{page}:t{index}",
                        }
                    )
            captured.append(cells)
        record["tables"][index] = captured

    def _binding(self, unit: Any, record: dict) -> tuple[dict, list[dict]]:
        metadata = unit.metadata
        binding = {
            "unit_id": unit.unit_id,
            "bbox": metadata.get("bbox"),
            "source": "pdf_native_single_textpage",
            "words": [],
            "cells": [],
            "font_runs": [],
        }
        spans: list[dict[str, Any]] = []
        block_no = metadata.get("pdf_block")
        block = record["blocks"].get(block_no)
        if block is not None:
            start, end = metadata["block_char_start"], metadata["block_char_end"]
            raw = block["text"]
            if _text(raw[start:end]).strip() != unit.raw_text:
                self._diag("UNIT_CHARACTER_ALIGNMENT_UNAVAILABLE", unit_id=unit.unit_id)
                return binding, spans
            first = bisect_right(block["word_ends"], start)
            for index in range(first, len(block["words"])):
                word = block["words"][index]
                if word["start"] >= end:
                    break
                if not self._take():
                    break
                if start <= word["start"] and word["end"] <= end:
                    if not block["nfc_identity"] and not self._take(
                        word["end"] - start
                    ):
                        break
                    char_start = (
                        word["start"] - start
                        if block["nfc_identity"]
                        else len(_text(raw[start : word["start"]]))
                    )
                    char_end = (
                        word["end"] - start
                        if block["nfc_identity"]
                        else len(_text(raw[start : word["end"]]))
                    )
                    if unit.raw_text[char_start:char_end] != _text(word["text"]):
                        self._diag(
                            "WORD_CHARACTER_ALIGNMENT_UNAVAILABLE", unit_id=unit.unit_id
                        )
                        continue
                    binding["words"].append(
                        {k: v for k, v in word.items() if k not in {"start", "end"}}
                        | {"char_start": char_start, "char_end": char_end}
                    )
            first = bisect_right(block["span_ends"], start)
            for index in range(first, len(block["spans"])):
                span = block["spans"][index]
                if span["start"] >= end:
                    break
                if not self._take():
                    break
                left, right = max(start, span["start"]), min(end, span["end"])
                if left >= right:
                    continue
                if not block["nfc_identity"] and not self._take(right - start):
                    break
                char_start = (
                    left - start
                    if block["nfc_identity"]
                    else len(_text(raw[start:left]))
                )
                char_end = (
                    right - start
                    if block["nfc_identity"]
                    else len(_text(raw[start:right]))
                )
                binding["font_runs"].append(
                    {
                        "char_start": char_start,
                        "char_end": char_end,
                        "font_size": span["font_size"],
                        "font_weight": span["font_weight"],
                        "font": span["font"],
                    }
                )
                spans.append(
                    {
                        k: span[k]
                        for k in ("bbox", "native_index", "block", "line", "span")
                    }
                    | {
                        "char_start": char_start,
                        "char_end": char_end,
                        "partial_span": left != span["start"] or right != span["end"],
                        "page": record["page"],
                        "coordinate_frame": record["coordinate_frame"],
                        "source": "pdf_dict_native_span",
                    }
                )
        table_no, row_no = unit.coordinates.table_index, unit.coordinates.row_index
        if table_no is not None and row_no is not None:
            rows = record["tables"].get(table_no, ())
            cells = rows[row_no] if row_no < len(rows) else ()
            if unit.coordinates.column_index is not None:
                cells = [
                    cell
                    for cell in cells
                    if cell["column"] == unit.coordinates.column_index
                ]
                fragment_start = metadata.get("cell_fragment_start")
                fragment_end = metadata.get("cell_fragment_end")
                actual_cells = []
                for cell in cells:
                    if (
                        not isinstance(fragment_start, int)
                        or not isinstance(fragment_end, int)
                        or not 0 <= fragment_start < fragment_end <= len(cell["text"])
                        or _text(cell["text"][fragment_start:fragment_end]).strip()
                        != unit.raw_text
                    ):
                        self._diag(
                            "CELL_FRAGMENT_PROVENANCE_UNAVAILABLE", unit_id=unit.unit_id
                        )
                        continue
                    actual_cells.append(
                        dict(
                            cell,
                            text=unit.raw_text,
                            char_start=0,
                            char_end=len(unit.raw_text),
                            native_cell_char_start=fragment_start,
                            native_cell_char_end=fragment_end,
                            partial_cell=fragment_start != 0
                            or fragment_end != len(cell["text"]),
                        )
                    )
                cells = actual_cells
            else:
                cursor = 0
                offsets = {}
                for column, value in enumerate(metadata.get("row_cells", ())):
                    if value:
                        offsets[column] = (cursor, cursor + len(_text(value)))
                        cursor += len(_text(value)) + 3
                cells = [dict(cell) for cell in cells]
                for cell in cells:
                    cell["char_start"], cell["char_end"] = offsets[cell["column"]]
            binding["cells"] = cells
            binding["source"] = "pdf_find_tables_cells"
        return binding, spans

    def project_page(self, page: int, units: Sequence[Any]) -> tuple[Any, ...]:
        try:
            return self._project_page(page, units)
        except Exception:
            self.pages.pop(page, None)
            self._diag("LAYOUT_PROJECTION_FAILED", page=page)
            return tuple(units)

    def _project_page(self, page: int, units: Sequence[Any]) -> tuple[Any, ...]:
        record = self.pages.pop(page, None)
        if record is None or not self._take():
            return tuple(units)
        limit = max(0, self.limits["max_units"] - self.processed)
        actual = tuple(units[:limit])
        if len(actual) < len(units):
            self._diag("LAYOUT_UNIT_BUDGET_EXCEEDED", page=page)
        bindings, spans, cell_provenance = [], {}, {}
        for unit in actual:
            if not self._take():
                break
            binding, native_spans = self._binding(unit, record)
            bindings.append(binding)
            spans[unit.unit_id] = native_spans
            cell_provenance[unit.unit_id] = {
                (cell["row"], cell["column"], cell["native_index"]): {
                    key: cell[key]
                    for key in (
                        "native_cell_char_start",
                        "native_cell_char_end",
                        "partial_cell",
                    )
                    if key in cell
                }
                for cell in binding["cells"]
            }
        snapshot = {
            "schema_version": "du-layout-snapshot/1",
            "pages": [
                {k: v for k, v in record.items() if k not in {"blocks", "tables"}}
                | {"bindings": bindings}
            ],
        }
        wire = [
            {
                "unit_id": unit.unit_id,
                "page": unit.coordinates.page_number,
                "text": unit.raw_text,
            }
            for unit in actual
        ]
        projected = project_layout_snapshot(
            snapshot,
            wire,
            limits={
                "max_units": limit,
                "max_pages": 1,
                "max_fine_elements": max(
                    0, self.limits["max_fine_elements"] - self.fine
                ),
                "max_work_units": max(0, self.limits["max_work_units"] - self.work),
            },
        )
        self.work += int(
            next(
                (
                    item["detail"]
                    for item in projected["diagnostics"]
                    if item["code"] == "WORK_UNITS"
                ),
                0,
            )
        )
        if not projected["coverage"]["complete"]:
            self.failed = True
        for item in projected["diagnostics"][: max(0, 128 - len(self.diagnostics))]:
            ids = item.get("unit_ids", ())
            self.diagnostics.append(
                dict(
                    item,
                    unit_ids=list(ids[:128]),
                    unit_count=len(ids),
                    unit_ids_limited=len(ids) > 128,
                )
            )
        result = []
        for unit in units:
            patch = projected["unit_metadata"].get(unit.unit_id)
            if patch is None:
                result.append(unit)
                continue
            upstream = patch["upstream_hints"]
            upstream = dict(
                upstream,
                cells=[
                    dict(
                        cell,
                        **cell_provenance[unit.unit_id].get(
                            (
                                cell.get("row"),
                                cell.get("column"),
                                cell.get("native_index"),
                            ),
                            {},
                        ),
                    )
                    for cell in upstream["cells"]
                ],
            )
            for kind in ("words", "cells", "font_runs"):
                if any(
                    item.get("char_alignment") != "exact" for item in upstream[kind]
                ):
                    self._diag(
                        "PROJECTED_CHARACTER_ALIGNMENT_UNAVAILABLE",
                        unit_id=unit.unit_id,
                    )
            native_spans = spans.get(unit.unit_id, [])
            count = sum(
                len(upstream[key]) for key in ("words", "cells", "font_runs")
            ) + len(native_spans)
            if self.fine + count > self.limits["max_fine_elements"] or not self._take():
                self._diag("LAYOUT_FINE_BUDGET_EXCEEDED", unit_id=unit.unit_id)
                result.append(unit)
                continue
            self.fine += count
            self.processed += 1
            self.bound_ids.add(unit.unit_id)
            metadata = dict(unit.metadata)
            metadata["reading_layout"] = {
                "feature_version": PDF_READING_LAYOUT_FEATURE_VERSION,
                "layout": dict(
                    patch["layout"],
                    cropbox=record["cropbox"],
                    cropbox_position=record["cropbox_position"],
                ),
                "hints": dict(patch["hints"]),
                "upstream_hints": dict(upstream, spans=native_spans),
            }
            result.append(replace(unit, metadata=metadata))
        self.projected_page_ids.add(page)
        return tuple(result)

    def summary(self, units: Sequence[Any]) -> tuple[dict, tuple[dict, ...]]:
        deferred = [
            unit.unit_id for unit in units if unit.unit_id not in self.bound_ids
        ]
        if deferred:
            self.failed = True
        self.pages.clear()
        self.pending_pages.clear()
        requested = sorted(self.requested_pages)
        captured = sorted(self.captured_page_ids)
        projected = sorted(self.projected_page_ids)
        deferred_pages = sorted(self.requested_pages - self.projected_page_ids)
        request = {"strategy": PDF_LAYOUT_CAPTURE_STRATEGY,
                   "mode": self.capture_mode, "pages": requested,
                   "limits": self.limits, "max_seconds": self.max_seconds}
        capture = {
            "schema_version": PDF_LAYOUT_CAPTURE_SCHEMA,
            "strategy": PDF_LAYOUT_CAPTURE_STRATEGY,
            "mode": self.capture_mode,
            "request_sha256": hashlib.sha256(json.dumps(
                request, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "complete": not deferred_pages and not self.exhausted,
            "not_requested_page_count": max(0, self.source_page_count - len(requested)),
        }
        for name, values in (("requested", requested), ("captured", captured),
                             ("projected", projected), ("deferred", deferred_pages)):
            capture[name + "_page_count"] = len(values)
            capture[name + "_pages"] = values[:128]
            capture[name + "_pages_limited"] = len(values) > 128
        return {
            "feature_version": PDF_READING_LAYOUT_FEATURE_VERSION,
            "complete": not self.failed,
            "processed_unit_count": self.processed,
            "processed_page_count": self.captured_pages,
            "deferred_unit_count": len(deferred),
            "deferred_unit_ids": deferred[:128],
            "deferred_limited": len(deferred) > 128,
            "fine_element_count": self.fine,
            "work_units": self.work,
            "capture": capture,
        }, tuple(self.diagnostics)
