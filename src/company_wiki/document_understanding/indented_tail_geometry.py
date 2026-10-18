"""Narrow measured shape of an indented CJK first line and terminal short tail.

This pure observer does not certify a source, page, column, speaker or semantic
assertion. The caller must FIRST establish same source/page/scope/frame/font,
adjacent ordinal/paragraph flow and all column/table/heading/role barriers.
No source text is changed or returned as a manufactured continuation.
"""
from __future__ import annotations

import math
import unicodedata


INDENTED_TAIL_GEOMETRY_VERSION = 'indented-terminal-tail/1'
_TERMINATORS = frozenset('。！？；.!?;')
_CLOSE_QUOTES = '\"\'”’）)]》」』】'
_MAX_LEFT_CHARACTERS = 2048
_MAX_TAIL_CHARACTERS = 4


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _box(value):
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        return None
    coordinates = tuple(_finite_number(v) for v in value)
    if any(v is None for v in coordinates):
        return None
    x0, y0, x1, y1 = coordinates
    if not (0 <= x0 < x1 and 0 <= y0 < y1):
        return None
    return coordinates


def _cjk(character):
    return unicodedata.name(character, '').startswith((
        'CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-'))


def _terminal(text):
    value = text.rstrip().rstrip(_CLOSE_QUOTES)
    return bool(value and value[-1] in _TERMINATORS)


def indented_terminal_tail_proof(left_bbox, right_bbox, font_size, left_text, right_text) -> dict | None:
    """Observe a font-relative body-line/short-tail shape, or return unknown.

    A normal CJK first line indents about one or two full glyph cells. Require
    at least eight em of body width and at most three em (and one quarter of
    that width) for the terminal tail. Both boxes must have a glyph-line
    height (half to one-and-a-half em), rather than a tall paragraph or rule.
    This permits an actual negative x
    overlap only with the full indentation/flow/script/termination evidence;
    it never claims that an existing positive-overlap rule passed.

    Absent caller source/layout guards or this geometric observation must not
    be replaced by model text repair. The result carries no such certification.
    """
    if (not isinstance(left_text, str) or not isinstance(right_text, str)
            or not 0 < len(left_text) <= _MAX_LEFT_CHARACTERS
            or not 0 < len(right_text) <= _MAX_TAIL_CHARACTERS):
        return None
    size = _finite_number(font_size)
    a, b = _box(left_bbox), _box(right_bbox)
    if size is None or size <= 0 or a is None or b is None:
        return None
    left, right = left_text.rstrip(), right_text.strip()
    if not left or not right or _terminal(left) or not _cjk(left[-1]):
        return None
    terminal_tail = right.rstrip(_CLOSE_QUOTES)
    if not terminal_tail or terminal_tail[-1] not in _TERMINATORS:
        return None
    glyphs = terminal_tail[:-1]
    if not glyphs or not all(_cjk(c) and not c.isnumeric() for c in glyphs):
        return None
    width, tail_width = a[2] - a[0], b[2] - b[0]
    indentation, gap = a[0] - b[0], b[1] - a[3]
    body_em, tail_em = width / size, tail_width / size
    indent_em, gap_em = indentation / size, gap / size
    heights_em = ((a[3] - a[1]) / size, (b[3] - b[1]) / size)
    if (not all(math.isfinite(v) for v in (body_em, tail_em, indent_em, gap_em, *heights_em))
            or body_em < 8 or not 1 <= indent_em <= 2.2
            or tail_em > 3 or tail_width > width / 4
            or b[2] > a[2] or not 0 <= gap_em <= 1
            or not all(0.5 <= height <= 1.5 for height in heights_em)):
        return None
    return {
        'basis': 'native_indented_terminal_tail',
        'geometry_feature_version': INDENTED_TAIL_GEOMETRY_VERSION,
        'left_bbox': a, 'right_bbox': b,
        'x0_delta': b[0] - a[0], 'indentation_em': indent_em,
        'horizontal_overlap': min(a[2], b[2]) - max(a[0], b[0]),
        'vertical_gap': gap, 'measured_font_size': size,
        'body_width_em': body_em, 'tail_width_em': tail_em,
        'terminal_cjk_characters': len(glyphs),
    }
