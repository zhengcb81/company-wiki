"""Native list-body measurement; never rewrites a unit or relaxes flow guards."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from typing import Any

HANGING_INDENT_GEOMETRY_VERSION = "native-hanging-indent/1"
_MARKERS = frozenset("•●▪◦‣⁃-–")


def _marker_end(text: str) -> int | None:
    if len(text) < 2 or text[0] not in _MARKERS or not text[1].isspace():
        return None
    end = 1
    while end < len(text) and text[end].isspace():
        end += 1
    return end if end < len(text) else None


def _numbers(value: Any, count: int) -> tuple[float, ...] | None:
    if not isinstance(value, (list, tuple)) or len(value) != count:
        return None
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
        for v in value
    ):
        return None
    return tuple(float(v) for v in value)


def hanging_body_proof(
    unit: Mapping[str, Any],
    *,
    bbox: tuple[float, ...],
    page: int,
    frame: str,
    size: float,
    charge: Callable[[int], bool],
) -> dict[str, Any] | None:
    """Observe a marker followed by complete, same-baseline native body spans.

    Source/page/scope/order/style/column and sentence barriers belong to the
    continuity owner. This helper only proves why a block's marker left edge
    is different from its text body. Missing or partial measurements abstain.
    """
    text = unit["text"]
    end = _marker_end(text)
    spans = unit.get("hints", {}).get("spans")
    if (
        end is None
        or not isinstance(spans, Sequence)
        or isinstance(spans, (str, bytes))
        or len(spans) < 2
        or not charge(len(spans) + len(text))
    ):
        return None
    previous = 0
    boxes: list[tuple[float, ...]] = []
    baseline = None
    marker_box = None
    for index, span in enumerate(spans):
        if not isinstance(span, Mapping):
            return None
        start, stop = span.get("char_start"), span.get("char_end")
        box, origin = _numbers(span.get("bbox"), 4), _numbers(span.get("origin"), 2)
        direction = _numbers(span.get("direction"), 2)
        if (
            type(start) is not int
            or type(stop) is not int
            or not previous <= start < stop <= len(text)
            or text[previous:start].strip()
            or box is None
            or origin is None
            or direction != (1.0, 0.0)
            or span.get("partial_span") is not False
            or span.get("char_alignment") != "exact"
            or span.get("page") != page
            or span.get("coordinate_frame") != frame
            or span.get("source") != "pdf_dict_native_span"
            or not bbox[0] <= box[0] < box[2] <= bbox[2]
            or not bbox[1] <= box[1] < box[3] <= bbox[3]
            or not box[0] <= origin[0] <= box[2]
            or not box[1] <= origin[1] <= box[3]
        ):
            return None
        if index == 0:
            if start != 0 or text[start:stop].strip() != text[0] or stop > end:
                return None
            marker_box, baseline = box, origin[1]
        else:
            if (
                baseline is None
                or start < end
                or abs(origin[1] - baseline) > size * 0.05
            ):
                return None
            if boxes and box[0] < boxes[-1][2] - size * 0.05:
                return None
            boxes.append(box)
        previous = stop
    if text[previous:].strip() or not boxes or marker_box is None:
        return None
    body = (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )
    if marker_box[2] >= body[0] or body[2] - body[0] < 8 * size:
        return None
    return {
        "body_bbox": body,
        "marker_bbox": marker_box,
        "baseline": baseline,
        "body_char_start": end,
        "body_char_end": previous,
        "version": HANGING_INDENT_GEOMETRY_VERSION,
    }


def is_bullet_start(text: str) -> bool:
    return _marker_end(text.lstrip()) is not None
