"""ZR-506: section / chunk / tag / fact assertion — pure functions that
give the normalized body a document structure on top of the flat locator
stream (ZR-504/505):

  detect_sections(text)  — chapter-heading lines (CJK ordinal "一、",
                           "第X章/第X节", numeric "1.1") -> [{index, title,
                           line_offset}]; zero hardcoded names.
  chunk_spans(line_count, sections) — line ranges between section headers
                           (the implicit single chunk when no sections).
  extract_facts(text)     — "指标名：数字+单位" patterns -> [{metric, value,
                           unit}]; negative/percent/unit-less handled; no
                           match -> [] (never fabricated).

Hermetic and deterministic (regex only; no metric/entity name hardcoding).
Tagging reuses the ZR-503 detected_entities verdict; section/chunk/fact
are the structural layer the downstream attribution (ZR-510) builds on.
"""

from __future__ import annotations

import re

STRUCTURE_SCHEMA_VERSION = "1.0"

# Chapter-heading patterns (line-anchored, title lines only).
_CJK_ORDINAL = re.compile(r"^[一二三四五六七八九十百]{1,3}[、．.]\s*\S")
_CHAPTER = re.compile(r"^第[一二三四五六七八九十百0-9]+[章节]\s*\S")
_NUMERIC_HEADING = re.compile(r"^\d{1,2}(?:\.\d{1,2})*[\s、.．]\s*\S")

_MAX_TITLE_LEN = 40

# "指标名：数字 单位" — metric is CJK/alnum text, value is a signed
# decimal, unit is optional CJK/percent/symbol text (no unit vocabulary).
_FACT = re.compile(
    r"([\u4e00-\u9fffA-Za-z]{2,12})[:：]\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*"
    r"([\u4e00-\u9fff%‰a-zA-Z/]+)?"
)


def _content_lines(text: str) -> list[str]:
    """Body lines, dropping page/table headers and locator comments so
    section detection runs on real content."""
    lines: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## ") or stripped.startswith("<!--"):
            continue
        if stripped.startswith("# "):
            continue
        lines.append(stripped)
    return lines


def _is_heading(line: str) -> bool:
    if len(line) > _MAX_TITLE_LEN:
        return False
    return bool(
        _CJK_ORDINAL.match(line)
        or _CHAPTER.match(line)
        or _NUMERIC_HEADING.match(line)
    )


def detect_sections(text: str | None) -> list[dict[str, object]]:
    """Chapter-heading lines -> [{"index": 0, "title": "...", "line_offset": 0}]."""
    sections: list[dict[str, object]] = []
    for offset, line in enumerate(_content_lines(text or "")):
        if _is_heading(line):
            sections.append(
                {
                    "index": len(sections),
                    "title": line,
                    "line_offset": offset,
                }
            )
    return sections


def content_line_count(text: str | None) -> int:
    """Number of content lines (same filtering as detect_sections)."""
    return len(_content_lines(text or ""))


def chunk_spans(
    line_count: int, sections: list[dict[str, object]]
) -> list[list[int]]:
    """Line ranges [start, end) between section headers; the implicit
    single chunk when there are no sections.  Bounds are clamped and
    empty trailing chunks dropped."""
    bounds = [min(int(item["line_offset"]), line_count) for item in sections]
    chunks: list[list[int]] = []
    start = 0
    for bound in bounds:
        chunks.append([start, bound])
        start = bound
    if start < line_count or not chunks:
        chunks.append([start, line_count])
    return chunks


def _fact_value(raw: str) -> int | float:
    return float(raw) if "." in raw else int(raw)


def extract_facts(text: str | None) -> list[dict[str, object]]:
    """"指标名：数字+单位" -> [{"metric": ..., "value": ..., "unit": ...}]."""
    facts: list[dict[str, object]] = []
    for match in _FACT.finditer(text or ""):
        metric = match.group(1)
        unit = match.group(3)
        facts.append(
            {
                "metric": metric,
                "value": _fact_value(match.group(2)),
                "unit": unit if unit else None,
            }
        )
    return facts


__all__ = [
    "STRUCTURE_SCHEMA_VERSION",
    "detect_sections",
    "chunk_spans",
    "content_line_count",
    "extract_facts",
]
