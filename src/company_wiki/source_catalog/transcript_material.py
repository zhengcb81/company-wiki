"""Small, replayable original-to-English-TXT extraction for transcripts.

No files are written. Each output line carries an exact byte range in the
immutable original. This is a G1e building block, not a source catalog writer
or a general HTML normalizer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
from html.parser import HTMLParser
import re
from typing import Any, Mapping

from company_wiki.source_contract import source_id_for_sha256


TRANSCRIPT_MATERIAL_SCHEMA = "transcript-material/2"
TRANSCRIPT_MATERIAL_EXTRACTOR = "transcript-original-text/1.0.0"
_MAX_ORIGINAL_BYTES = 10 * 1024 * 1024
_MAX_LINES = 20000
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
        """Compact persisted metadata; locators are deterministically replayed."""
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
        if self.schema_version != TRANSCRIPT_MATERIAL_SCHEMA:
            raise TranscriptMaterialError("unsupported material schema")
        if self.extractor_version != TRANSCRIPT_MATERIAL_EXTRACTOR:
            raise TranscriptMaterialError("unsupported extractor version")
        if self.original_mime_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            raise TranscriptMaterialError("unsupported original MIME type")
        if (
            not isinstance(original, bytes)
            or not 0 < len(original) <= _MAX_ORIGINAL_BYTES
            or self.original_byte_size != len(original)
            or self.original_sha256 != _sha(original)
        ):
            raise TranscriptMaterialError("original bytes changed")
        if self.original_source_id != source_id_for_sha256(self.original_sha256):
            raise TranscriptMaterialError("source ID does not match original")
        try:
            original.decode("utf-8", errors="strict")
            body = self.text_utf8.encode("utf-8", errors="strict")
        except (UnicodeDecodeError, UnicodeEncodeError) as exc:
            raise TranscriptMaterialError("source or derived text is not UTF-8") from exc
        if self.text_byte_size != len(body) or self.text_sha256 != _sha(body):
            raise TranscriptMaterialError("derived text bytes changed")
        if not self.text_utf8.endswith("\n") or "\r" in self.text_utf8:
            raise TranscriptMaterialError("derived text line endings are not canonical")
        text_lines = self.text_utf8.splitlines()
        if not text_lines or len(text_lines) != len(self.lines):
            raise TranscriptMaterialError("derived line count changed")
        prior_end = 0
        for index, (text, line) in enumerate(zip(text_lines, self.lines, strict=True), start=1):
            if line.line_number != index or not 0 <= line.source_byte_start < line.source_byte_end <= len(original):
                raise TranscriptMaterialError("invalid source byte locator")
            if line.source_byte_start < prior_end:
                raise TranscriptMaterialError("source byte locators overlap or go backward")
            if not _SHA.fullmatch(line.text_sha256) or line.text_sha256 != _sha(text.encode("utf-8")):
                raise TranscriptMaterialError("derived line hash mismatch")
            try:
                source_text = original[line.source_byte_start : line.source_byte_end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TranscriptMaterialError("source locator splits UTF-8 code point") from exc
            if _clean(
                source_text,
                html_entities=self.original_mime_type in {"text/html", "application/xhtml+xml"},
            ) != text:
                raise TranscriptMaterialError("derived line does not replay from original")
            prior_end = line.source_byte_end


def _material(
    original: bytes, mime_type: str, rows: list[tuple[str, int, int]]
) -> TranscriptMaterial:
    if not rows or len(rows) > _MAX_LINES:
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
        extractor_version=TRANSCRIPT_MATERIAL_EXTRACTOR,
        lines=tuple(
            TranscriptTextLine(i, start, end, _sha(text.encode("utf-8")))
            for i, (text, start, end) in enumerate(rows, start=1)
        ),
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
        self.rows.append((cleaned, self._byte_offset(start), self._byte_offset(end)))
        if len(self.rows) > _MAX_LINES:
            raise TranscriptMaterialError("transcript exceeds line limit")


def extract_transcript_material(original: bytes, *, mime_type: str) -> TranscriptMaterial:
    """Derive untranslated UTF-8 lines with exact original byte locators."""
    if not isinstance(original, bytes) or not original or len(original) > _MAX_ORIGINAL_BYTES:
        raise TranscriptMaterialError("original must be non-empty bounded bytes")
    try:
        source = original.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TranscriptMaterialError("original is not strict UTF-8") from exc
    if mime_type == "text/plain":
        rows: list[tuple[str, int, int]] = []
        offset = 0
        for raw_line in original.splitlines(keepends=True):
            content = raw_line.rstrip(b"\r\n")
            text = _clean(content.decode("utf-8"))
            if text:
                rows.append((text, offset, offset + len(content)))
            offset += len(raw_line)
        return _material(original, mime_type, rows)
    if mime_type in {"text/html", "application/xhtml+xml"}:
        parser = _HTMLTextLines(source)
        parser.feed(source)
        parser.close()
        return _material(original, mime_type, parser.rows)
    raise TranscriptMaterialError("unsupported original MIME type")


def load_transcript_material(
    lineage: Mapping[str, Any],
    *,
    original: bytes,
    text_utf8: bytes,
    expected_mime_type: str,
) -> TranscriptMaterial:
    """Replay compact lineage using MIME trusted from the canonical source receipt."""
    expected = {
        "schema_version", "original_source_id", "original_sha256", "original_mime_type",
        "original_byte_size", "text_sha256", "text_byte_size", "extractor_version", "line_count",
    }
    if not isinstance(lineage, Mapping) or set(lineage) != expected:
        raise TranscriptMaterialError("lineage fields differ from schema")
    if any(
        not isinstance(lineage[key], str)
        for key in (
            "schema_version", "original_source_id", "original_sha256", "original_mime_type",
            "text_sha256", "extractor_version",
        )
    ):
        raise TranscriptMaterialError("lineage text fields must be strings")
    if any(
        type(lineage[key]) is not int
        for key in ("original_byte_size", "text_byte_size", "line_count")
    ):
        raise TranscriptMaterialError("lineage sizes and line count must be integers")
    if not isinstance(original, bytes) or not isinstance(text_utf8, bytes):
        raise TranscriptMaterialError("original and derived text must be bytes")
    if not isinstance(expected_mime_type, str) or expected_mime_type not in {
        "text/html", "application/xhtml+xml", "text/plain"
    }:
        raise TranscriptMaterialError("unsupported trusted original MIME type")
    if lineage["original_mime_type"] != expected_mime_type:
        raise TranscriptMaterialError("lineage MIME differs from trusted source receipt")
    if not 0 < lineage["line_count"] <= _MAX_LINES:
        raise TranscriptMaterialError("lineage line count is out of bounds")
    try:
        extracted = extract_transcript_material(original, mime_type=expected_mime_type)
    except TranscriptMaterialError:
        raise
    if extracted.lineage_dict() != dict(lineage):
        raise TranscriptMaterialError("lineage differs from deterministic extraction")
    if text_utf8 != extracted.text_utf8.encode("utf-8"):
        raise TranscriptMaterialError("derived text differs from deterministic extraction")
    return extracted
