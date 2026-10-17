"""Limits, coordinate frames and text-identity resolution (``limits_identity``).

Centralised in one place so limit resolution, work accounting, coordinate-frame
reconciliation and NFC/trim char alignment are implemented exactly once and used
by the contract, binding and projection layers.  Pure: no filesystem, network,
clock or model access; structural errors raise ``ValueError``.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping
from company_wiki.resource_budget import WorkBudget as WorkBudget, WorkBudgetExceeded as WorkBudgetExceeded

#: ``du-layout-snapshot/1`` defaults (card requirement 6).  Callers may only
#: TIGHTEN these; ``resolve_limits`` clamps any attempted widening back down.
DEFAULT_LIMITS: dict[str, int] = {
    "max_units": 10_000,
    "max_pages": 64,
    "max_fine_elements": 200_000,
    "max_work_units": 1_000_000,
}

#: Coordinate frames the projection recognises.  Anything else is UNKNOWN and the
#: affected page/units are marked partial; physical size is never guessed.
UNROTATED_TEXT_FRAMES = frozenset({"dict", "text", "rawdict", "words", "span", "chars"})
ROTATED_RECT_FRAMES = frozenset({"page_rect", "rect", "rotated", "device"})
OTHER_KNOWN_FRAMES = frozenset({"user", "media", "cropbox", "transformed"})
KNOWN_FRAMES = UNROTATED_TEXT_FRAMES | ROTATED_RECT_FRAMES | OTHER_KNOWN_FRAMES

VALID_ROTATIONS = frozenset({0, 90, 180, 270})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def resolve_limits(limits: Mapping[str, Any] | None = None) -> dict[str, int]:
    """Caller limits may TIGHTEN the defaults, never widen them."""
    resolved = dict(DEFAULT_LIMITS)
    if limits is not None:
        _require(isinstance(limits, Mapping), "limits must be a mapping")
        for key in DEFAULT_LIMITS:
            if key in limits and limits[key] is not None:
                value = limits[key]
                _require(
                    isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                    f"limits[{key}] must be an int >= 0",
                )
                resolved[key] = min(int(value), DEFAULT_LIMITS[key])
    return resolved


@dataclass(frozen=True)
class Frame:
    """One page's declared coordinate frame plus its rotation/size."""

    label: str | None
    rotation: int | None
    width: float | None
    height: float | None
    known: bool
    converted: bool = False
    problems: tuple[str, ...] = ()


def normalize_frame(
    *,
    coordinate_frame: Any,
    rotation: Any,
    width: Any,
    height: Any,
    dict_size: tuple[float, float] | None = None,
    rect_size: tuple[float, float] | None = None,
    has_transform: bool = False,
) -> Frame:
    """Reconcile a page's declared frame; never invents a physical size.

    Returns a :class:`Frame` whose ``problems`` list the reason(s) the frame is
    partial.  Rotation is only reconciled when both the unrotated dict size and
    the rotated rect size are actually supplied; a mismatch is reported instead
    of silently swapping axes.
    """
    problems: list[str] = []

    label: str | None
    if isinstance(coordinate_frame, str) and coordinate_frame.strip():
        label = coordinate_frame.strip()
    else:
        label = None
        problems.append("frame_label_missing")
    known = label in KNOWN_FRAMES if label is not None else False
    if label is not None and not known:
        problems.append("frame_label_unknown")

    rot: int | None
    if isinstance(rotation, int) and not isinstance(rotation, bool) and rotation in VALID_ROTATIONS:
        rot = rotation
    elif rotation is None:
        rot = None
        problems.append("rotation_missing")
    else:
        rot = None
        problems.append("rotation_invalid")

    w = float(width) if _is_number(width) and float(width) > 0 else None
    h = float(height) if _is_number(height) and float(height) > 0 else None
    if w is None or h is None:
        problems.append("page_size_unknown")

    # Reconcile dict (unrotated) vs rect (rotated) sizes when both are supplied.
    if dict_size is not None and rect_size is not None and rot is not None:
        dw, dh = dict_size
        rw, rh = rect_size
        if dw is not None and dh is not None and rw is not None and rh is not None:
            if rot in (90, 270):
                consistent = _close(rw, dh) and _close(rh, dw)
            else:
                consistent = _close(rw, dw) and _close(rh, dh)
            if not consistent:
                problems.append("frame_size_mismatch")

    converted = bool(has_transform)
    return Frame(
        label=label,
        rotation=rot,
        width=w,
        height=h,
        known=known,
        converted=converted,
        problems=tuple(problems),
    )


def _close(a: float, b: float, eps: float = 0.05) -> bool:
    return abs(a - b) <= eps


def legal_bbox(value: Any) -> tuple[float, float, float, float] | None:
    """Return a normalised bbox or ``None`` when it is absent/illegal."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if not all(_is_number(v) for v in value):
        return None
    x0, y0, x1, y1 = (float(v) for v in value)
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def align_char_range(
    word_text: Any,
    char_start: Any,
    char_end: Any,
    unit_text: str,
) -> tuple[int | None, int | None, str]:
    """Align a fine element's char range to the (NFC/trimmed) unit text.

    Returns ``(start, end, alignment)`` where alignment is one of ``exact`` (the
    provided range strictly slices the unit text to the word), ``relocated`` (a
    unique occurrence was found and the range re-pinned) or ``unknown`` (cannot
    strictly align).  The unit text is never modified: an unalignable range is
    reported ``unknown`` and the caller keeps the element's real bbox as its
    geometry basis.  ``exact`` is deliberately STRICT (NFC codepoint equality,
    no whitespace collapsing) so an NFC/trim length shift cannot masquerade as a
    valid offset.
    """
    ntext = unicodedata.normalize("NFC", unit_text)
    nword = unicodedata.normalize("NFC", word_text) if isinstance(word_text, str) else ""

    # 1. exact: the provided range strictly slices to the word.
    if (
        isinstance(char_start, int)
        and not isinstance(char_start, bool)
        and isinstance(char_end, int)
        and not isinstance(char_end, bool)
        and 0 <= char_start < char_end <= len(ntext)
        and unicodedata.normalize("NFC", ntext[char_start:char_end]) == nword
    ):
        return char_start, char_end, "exact"

    # 2. relocated: a unique occurrence of the word exists in the unit text.
    if nword:
        hits = []
        pos = ntext.find(nword)
        while pos != -1:
            hits.append((pos, pos + len(nword)))
            pos = ntext.find(nword, pos + 1)
        if len(hits) == 1:
            return hits[0][0], hits[0][1], "relocated"

    return None, None, "unknown"
