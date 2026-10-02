"""Deterministic untranslated transcript text and byte locator extraction."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from company_wiki.source_contract import source_id_for_sha256
from .transcript_json_extract import (
    JsonTranscriptError,
    json_transcript_rows,
    replay_json_transcript_fragment,
)


TRANSCRIPT_MATERIAL_SCHEMA = "transcript-material/2"
TRANSCRIPT_MATERIAL_EXTRACTOR = "transcript-original-text/1.0.0"
TRANSCRIPT_JSON_EXTRACTOR = "transcript-original-json/1.0.0"
MAX_TRANSCRIPT_ORIGINAL_BYTES = 10 * 1024 * 1024
MAX_TRANSCRIPT_LINES = 20000
TRANSCRIPT_MIME_TYPES = frozenset(
    {"text/html", "application/xhtml+xml", "text/plain", "application/json"}
)
_SHA = re.compile(r"^[0-9a-f]{64}$")


class TranscriptMaterialError(ValueError):
    """Original/derived text or locator mapping is not replayable."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(text: str, *, html_entities: bool = False) -> str:
    return " ".join((html.unescape(text) if html_entities else text).split())


@dataclass(frozen=True)
class TranscriptTextLine:
    line_number: int
    source_byte_start: int
    source_byte_end: int
    text_sha256: str

    @property
    def source_locator(self) -> str:
        return f"byte:{self.source_byte_start}:{self.source_byte_end}"


@dataclass(frozen=True)
class TranscriptMaterial:
    schema_version: str
    original_source_id: str
    original_sha256: str
    original_mime_type: str
    original_byte_size: int
    text_sha256: str
    text_byte_size: int
    extractor_version: str
    lines: tuple[TranscriptTextLine, ...]
    text_utf8: str

    def lineage_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "original_source_id": self.original_source_id,
            "original_sha256": self.original_sha256,
            "original_mime_type": self.original_mime_type,
            "original_byte_size": self.original_byte_size,
            "text_sha256": self.text_sha256,
            "text_byte_size": self.text_byte_size,
            "extractor_version": self.extractor_version,
            "line_count": len(self.lines),
        }

    def verify(self, original: bytes) -> None:
        verify_transcript_material(self, original)


def _verify_identity(material: TranscriptMaterial) -> None:
    if material.schema_version != TRANSCRIPT_MATERIAL_SCHEMA:
        raise TranscriptMaterialError("unsupported material schema")
    expected_extractor = (
        TRANSCRIPT_JSON_EXTRACTOR if material.original_mime_type == "application/json"
        else TRANSCRIPT_MATERIAL_EXTRACTOR
    )
    if material.extractor_version != expected_extractor:
        raise TranscriptMaterialError("unsupported extractor version")
    if material.original_mime_type not in TRANSCRIPT_MIME_TYPES:
        raise TranscriptMaterialError("unsupported original MIME type")
    if material.original_source_id != source_id_for_sha256(material.original_sha256):
        raise TranscriptMaterialError("source ID does not match original")


def _verified_original(material: TranscriptMaterial, original: object) -> bytes:
    if not isinstance(original, bytes):
        raise TranscriptMaterialError("original bytes changed")
    if not 0 < len(original) <= MAX_TRANSCRIPT_ORIGINAL_BYTES:
        raise TranscriptMaterialError("original bytes changed")
    if material.original_byte_size != len(original) or (
        material.original_sha256 != _sha(original)
    ):
        raise TranscriptMaterialError("original bytes changed")
    return original


def _encoded_text(material: TranscriptMaterial, original: bytes) -> bytes:
    try:
        original.decode("utf-8", errors="strict")
        body = material.text_utf8.encode("utf-8", errors="strict")
    except (UnicodeDecodeError, UnicodeEncodeError) as exc:
        raise TranscriptMaterialError(
            "source or derived text is not UTF-8"
        ) from exc
    if material.text_byte_size != len(body) or material.text_sha256 != _sha(body):
        raise TranscriptMaterialError("derived text bytes changed")
    if not material.text_utf8.endswith("\n") or "\r" in material.text_utf8:
        raise TranscriptMaterialError("derived text line endings are not canonical")
    return body


def _replayed_source_text(
    original: bytes, line: TranscriptTextLine, mime_type: str
) -> str:
    try:
        source_text = original[line.source_byte_start : line.source_byte_end].decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise TranscriptMaterialError(
            "source locator splits UTF-8 code point"
        ) from exc
    if mime_type == "application/json":
        try:
            return replay_json_transcript_fragment(source_text)
        except JsonTranscriptError as exc:
            raise TranscriptMaterialError("invalid JSON source locator") from exc
    return _clean(
        source_text,
        html_entities=mime_type in {"text/html", "application/xhtml+xml"},
    )


def _verify_line(
    *,
    text: str,
    line: TranscriptTextLine,
    index: int,
    prior_end: int,
    original: bytes,
    mime_type: str,
) -> int:
    if line.line_number != index or not (
        0 <= line.source_byte_start < line.source_byte_end <= len(original)
    ):
        raise TranscriptMaterialError("invalid source byte locator")
    if line.source_byte_start < prior_end:
        raise TranscriptMaterialError("source byte locators overlap or go backward")
    if not _SHA.fullmatch(line.text_sha256) or line.text_sha256 != _sha(
        text.encode("utf-8")
    ):
        raise TranscriptMaterialError("derived line hash mismatch")
    if _replayed_source_text(original, line, mime_type) != text:
        raise TranscriptMaterialError("derived line does not replay from original")
    return line.source_byte_end


def _verify_lines(material: TranscriptMaterial, original: bytes) -> None:
    text_lines = material.text_utf8.splitlines()
    if not text_lines or len(text_lines) != len(material.lines):
        raise TranscriptMaterialError("derived line count changed")
    prior_end = 0
    for index, (text, line) in enumerate(
        zip(text_lines, material.lines, strict=True), start=1
    ):
        prior_end = _verify_line(
            text=text,
            line=line,
            index=index,
            prior_end=prior_end,
            original=original,
            mime_type=material.original_mime_type,
        )


def verify_transcript_material(
    material: TranscriptMaterial, original: bytes
) -> None:
    _verify_identity(material)
    checked = _verified_original(material, original)
    _encoded_text(material, checked)
    _verify_lines(material, checked)


def _text_lines(
    rows: list[tuple[str, int, int]]
) -> tuple[TranscriptTextLine, ...]:
    return tuple(
        TranscriptTextLine(index, start, end, _sha(text.encode("utf-8")))
        for index, (text, start, end) in enumerate(rows, start=1)
    )


def _material(
    original: bytes, mime_type: str, rows: list[tuple[str, int, int]]
) -> TranscriptMaterial:
    if not rows or len(rows) > MAX_TRANSCRIPT_LINES:
        raise TranscriptMaterialError("transcript has no text or exceeds line limit")
    text_utf8 = "\n".join(text for text, _, _ in rows) + "\n"
    original_sha = _sha(original)
    body = text_utf8.encode("utf-8")
    material = TranscriptMaterial(
        schema_version=TRANSCRIPT_MATERIAL_SCHEMA,
        original_source_id=source_id_for_sha256(original_sha),
        original_sha256=original_sha,
        original_mime_type=mime_type,
        original_byte_size=len(original),
        text_sha256=_sha(body),
        text_byte_size=len(body),
        extractor_version=(TRANSCRIPT_JSON_EXTRACTOR if mime_type == "application/json"
                           else TRANSCRIPT_MATERIAL_EXTRACTOR),
        lines=_text_lines(rows),
        text_utf8=text_utf8,
    )
    material.verify(original)
    return material


class _HTMLTextLines(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_starts = [0]
        for match in re.finditer("\n", source):
            self.line_starts.append(match.end())
        self.rows: list[tuple[str, int, int]] = []
        self.skip_depth = 0
        self._last_char_offset = 0
        self._last_byte_offset = 0

    def _char_offset(self, line: int, col: int) -> int:
        if line < 1 or line > len(self.line_starts):
            raise TranscriptMaterialError("HTML parser source position invalid")
        return self.line_starts[line - 1] + col

    def _byte_offset(self, char_offset: int) -> int:
        if char_offset < self._last_char_offset or char_offset > len(self.source):
            raise TranscriptMaterialError("HTML parser source offsets went backward")
        self._last_byte_offset += len(
            self.source[self._last_char_offset:char_offset].encode("utf-8")
        )
        self._last_char_offset = char_offset
        return self._last_byte_offset

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        line, col = self.getpos()
        start = self._char_offset(line, col)
        end = self.source.find("<", start)
        if end < 0:
            end = len(self.source)
        raw = self.source[start:end]
        if html.unescape(raw) != data:
            raise TranscriptMaterialError("HTML data cannot be mapped to original")
        cleaned = _clean(raw, html_entities=True)
        if not cleaned:
            return
        self.rows.append(
            (cleaned, self._byte_offset(start), self._byte_offset(end))
        )
        if len(self.rows) > MAX_TRANSCRIPT_LINES:
            raise TranscriptMaterialError("transcript exceeds line limit")


def _plain_rows(original: bytes) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    offset = 0
    for raw_line in original.splitlines(keepends=True):
        content = raw_line.rstrip(b"\r\n")
        text = _clean(content.decode("utf-8"))
        if text:
            rows.append((text, offset, offset + len(content)))
        offset += len(raw_line)
    return rows


def extract_transcript_material(
    original: bytes, *, mime_type: str
) -> TranscriptMaterial:
    """Derive untranslated UTF-8 lines with exact original byte locators."""
    if not isinstance(original, bytes) or not original or (
        len(original) > MAX_TRANSCRIPT_ORIGINAL_BYTES
    ):
        raise TranscriptMaterialError("original must be non-empty bounded bytes")
    try:
        source = original.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TranscriptMaterialError("original is not strict UTF-8") from exc
    if mime_type == "text/plain":
        return _material(original, mime_type, _plain_rows(original))
    if mime_type == "application/json":
        try:
            rows = json_transcript_rows(source, max_lines=MAX_TRANSCRIPT_LINES)
            return _material(original, mime_type, rows)
        except JsonTranscriptError as exc:
            raise TranscriptMaterialError(str(exc)) from exc
    if mime_type in {"text/html", "application/xhtml+xml"}:
        parser = _HTMLTextLines(source)
        parser.feed(source)
        parser.close()
        return _material(original, mime_type, parser.rows)
    raise TranscriptMaterialError("unsupported original MIME type")
