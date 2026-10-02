"""Decode one provider JSON transcript while retaining encoded byte spans."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any


_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
_COLON = re.compile(r'\s*:\s*')
_TOKEN = re.compile(r'\\(?:u[0-9a-fA-F]{4}|["\\/bfnrt])|[^\\]')
_BREAKS = frozenset('\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029')


class JsonTranscriptError(ValueError):
    """Provider JSON has no unambiguous, replayable transcript content."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonTranscriptError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise JsonTranscriptError(f'invalid JSON constant: {value}')


def replay_json_transcript_fragment(encoded: str) -> str:
    """Replay an encoded string-body span (the enclosing quotes are omitted)."""
    try:
        text = json.loads('"' + encoded + '"')
        text.encode('utf-8', errors='strict')
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise JsonTranscriptError('invalid JSON transcript string') from exc
    return ' '.join(text.split())


def _record_content(source: str) -> str:
    try:
        payload = json.loads(source, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise JsonTranscriptError('invalid provider JSON') from exc
    if isinstance(payload, list) and len(payload) == 1:
        payload = payload[0]
    if not isinstance(payload, dict) or not isinstance(payload.get('content'), str):
        raise JsonTranscriptError('expected exactly one transcript record')
    content: str = payload['content']
    return content


def _encoded_content_span(source: str) -> tuple[int, int]:
    spans: list[tuple[int, int]] = []
    for token in _STRING.finditer(source):
        colon = _COLON.match(source, token.end())
        if colon is None or json.loads(token.group()) != 'content':
            continue
        value = _STRING.match(source, colon.end())
        if value is not None:
            if spans:
                raise JsonTranscriptError('ambiguous transcript content field')
            spans.append((value.start() + 1, value.end() - 1))
    if len(spans) != 1:
        raise JsonTranscriptError('ambiguous transcript content field')
    return spans[0]


def _content_span(source: str) -> tuple[int, int]:
    content = _record_content(source)
    start, end = _encoded_content_span(source)
    if json.loads(source[start - 1:end + 1]) != content:
        raise JsonTranscriptError('transcript content is not the selected record')
    return start, end


def _is_break(token: str) -> bool:
    if token.startswith('\\u'):
        return chr(int(token[2:], 16)) in _BREAKS
    return token in _BREAKS or token in {'\\n', '\\r', '\\f'}


def _line_spans(source: str, start: int, end: int) -> Iterator[tuple[int, int]]:
    prior = start
    for token in _TOKEN.finditer(source, start, end):
        if _is_break(token.group()):
            yield prior, token.start()
            prior = token.end()
    yield prior, end


def json_transcript_rows(source: str, *, max_lines: int) -> list[tuple[str, int, int]]:
    """Return untranslated lines with offsets into the exact UTF-8 JSON bytes."""
    start, end = _content_span(source)
    rows: list[tuple[str, int, int]] = []
    cursor_char = 0
    cursor_byte = 0
    for row_start, row_end in _line_spans(source, start, end):
        cursor_byte += len(source[cursor_char:row_start].encode('utf-8'))
        byte_start = cursor_byte
        encoded = source[row_start:row_end]
        cursor_byte += len(encoded.encode('utf-8'))
        cursor_char = row_end
        text = replay_json_transcript_fragment(encoded)
        if text:
            if len(rows) >= max_lines:
                raise JsonTranscriptError('transcript exceeds line limit')
            rows.append((text, byte_start, cursor_byte))
    return rows
