"""Split normalized.md into high-value sections (MD&A / business overview /
business & technology) for investment research analysis.

Phase 1: pure-function section splitting (no catalog writes). The catalog
integration (``extract_sections_catalog``) and the ``sections`` artifact are
added in Phase 2.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .admission import processing_priority_sql
from .artifact_handle import ARTIFACT_HANDLE_SCHEMA_VERSION
from .models import CatalogConfig, ProcessingReport, SECTION_EXTRACTOR_VERSION
from .store import CatalogStore, canonical_json


SECTION_EXTRACTOR_NAME = "source_catalog_section_extractor"
SECTION_ARTIFACT_ROLE = "sections"

# Spike-validated regex: matches Chinese-report top-level headings —
# "第X节 标题" (annual/semi-annual reports) and "第X章 标题" (prospectuses).
SECTION_RE = re.compile(r"^\s*(第[一二三四五六七八九十百千]+[节章])\s+(.{2,40}?)$", re.MULTILINE)

# PyMuPDF-path normalized bodies delimit pages with "## Page N".
PAGE_MARKER_RE = re.compile(r"^## Page (\d+)$", re.MULTILINE)

# High-value section keywords -> role (validated on real normalized.md;
# see docs/plans/core-section-extraction/findings.md discovery 3).
SECTION_KEYWORDS: dict[str, str] = {
    "管理层讨论与分析": "mda",
    "经营情况讨论与分析": "mda",
    "业务概要": "business_overview",
    "主要业务": "business_overview",
    "业务与技术": "business_and_technology",
}
# Recognized but lower priority (not the research core); still emitted so the
# consumer can opt in, but MD&A / business sections are the focus.
SECTION_KEYWORDS_LOW: dict[str, str] = {
    "财务报告": "financial_statements",
    "主要会计数据": "financial_data",
    "主要财务指标": "financial_data",
    "风险因素": "risk_factors",
    "重要事项": "important_events",
}

# Document kinds that carry the section structure this module targets.
TARGET_DOCUMENT_KINDS = ("annual_report", "semi_annual_report", "prospectus")


@dataclass(frozen=True)
class SectionSlice:
    """One recognized section within a normalized.md body.

    ``char_start`` / ``char_end`` are offsets within the body (after any
    frontmatter has been stripped).
    """

    role: str
    title: str
    ordinal: str  # e.g. "第四节", "第六章"
    char_start: int
    char_end: int
    body: str


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block (``--- ... ---``); return body."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :]
    return text


def _classify(title: str) -> str | None:
    """Map a section title to a role via keyword containment (high then low)."""
    for keyword, role in SECTION_KEYWORDS.items():
        if keyword in title:
            return role
    for keyword, role in SECTION_KEYWORDS_LOW.items():
        if keyword in title:
            return role
    return None


def extract_sections_from_text(text: str) -> list[SectionSlice]:
    """Split a normalized.md document into high-value :class:`SectionSlice`.

    Only sections whose title maps to a known role are emitted, but every
    top-level heading (``第X节/章``) still serves as a boundary — its start
    delimits the previous section's end — so slice bodies are contiguous and
    non-overlapping.
    """
    body = _strip_frontmatter(text)
    headings = [
        (m.group(1), m.group(2).strip(), m.start())
        for m in SECTION_RE.finditer(body)
    ]
    slices: list[SectionSlice] = []
    for index, (ordinal, title, start) in enumerate(headings):
        role = _classify(title)
        if role is None:
            continue
        char_end = headings[index + 1][2] if index + 1 < len(headings) else len(body)
        slices.append(
            SectionSlice(
                role=role,
                title=title,
                ordinal=ordinal,
                char_start=start,
                char_end=char_end,
                body=body[start:char_end],
            )
        )
    return slices


def chapter_page_range(
    body: str, char_start: int, char_end: int
) -> tuple[int, int] | None:
    """Map a body char range to the ``## Page N`` markers it covers.

    Returns ``(first_page, last_page)`` inclusive, or ``None`` when the body
    has no page markers (docling path) so callers can degrade to no association.
    """
    markers = [
        (match.start(), int(match.group(1)))
        for match in PAGE_MARKER_RE.finditer(body)
    ]
    if not markers:
        return None
    first = markers[0][1]
    last = markers[-1][1]
    for position, page_no in markers:
        if position <= char_start:
            first = page_no
        if position < char_end:
            last = page_no
    return first, last


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def extract_sections_catalog(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int | None = None,
    document_id: str | None = None,
    document_kind: str | None = None,
    force: bool = False,
    progress: Callable[..., None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> ProcessingReport:
    """Write a ``sections`` artifact for each normalized annual/semi-annual/prospectus.

    Selects documents that already have a ``normalized`` artifact but no ``sections``
    artifact (unless ``force``), reads the normalized.md, splits it into high-value
    sections, writes per-section markdown + index.json, and inserts one artifact row
    per document under ``CatalogOperationLock`` (held by the service-layer wrapper).
    A specific ``document_id`` overrides the document-kind filter (single document).
    """
    if document_kind is not None and document_kind not in TARGET_DOCUMENT_KINDS:
        raise ValueError(
            f"document_kind must be one of {TARGET_DOCUMENT_KINDS} or None"
        )

    where_clauses: list[str] = []
    params: list[Any] = [SECTION_ARTIFACT_ROLE, SECTION_EXTRACTOR_NAME]
    if document_id is not None:
        where_clauses.append("d.document_id = ?")
        params.append(document_id)
    else:
        kinds = (document_kind,) if document_kind else TARGET_DOCUMENT_KINDS
        placeholders = ",".join("?" for _ in kinds)
        where_clauses.append(f"d.document_kind IN ({placeholders})")
        params.extend(kinds)
    if not force:
        where_clauses.append("sec.artifact_id IS NULL")

    sql = (
        "SELECT d.document_id, d.primary_source_id, d.document_kind, d.title, "
        "norm.path AS normalized_path, norm.content_sha256 AS content_sha256, "
        "s.content_sha256 AS source_sha256 "
        "FROM documents d "
        "JOIN artifacts norm ON norm.document_id=d.document_id "
        "AND norm.artifact_role='normalized' "
        "AND norm.generator_name='source_catalog_normalizer' "
        "JOIN sources s ON s.source_id=d.primary_source_id "
        "LEFT JOIN artifacts sec ON sec.document_id=d.document_id "
        "AND sec.artifact_role=? AND sec.generator_name=? "
        "WHERE " + " AND ".join(where_clauses)
        + f" ORDER BY {processing_priority_sql('d')}, d.document_id"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    documents = store.fetchall(sql, tuple(params))

    completed = skipped = failed = 0
    last_failed_document_id: str | None = None
    last_failed_path: str | None = None
    for index, document in enumerate(documents, start=1):
        if should_stop is not None and should_stop():
            break
        normalized_path = Path(document["normalized_path"])
        if progress is not None:
            progress(
                current=index,
                total=len(documents),
                current_path=str(normalized_path.resolve(strict=False)),
                detail="extracting sections",
            )
        try:
            text = normalized_path.read_text(encoding="utf-8")
        except OSError:
            failed += 1
            last_failed_document_id = document["document_id"]
            last_failed_path = str(normalized_path.resolve(strict=False))
            continue
        slices = extract_sections_from_text(text)
        if not slices:
            skipped += 1
            continue
        body = _strip_frontmatter(text)
        spans = store.fetchall(
            "SELECT span_id, page_number FROM evidence_spans WHERE document_id=?",
            (document["document_id"],),
        )
        sha = document["content_sha256"]
        sections_dir = config.derived_dir / sha[:2] / sha / "sections"
        index_entries: list[dict[str, Any]] = []
        for sl in slices:
            section_path = sections_dir / f"{sl.role}.md"
            _atomic_write(section_path, sl.body)
            page_range = chapter_page_range(body, sl.char_start, sl.char_end)
            span_ids = [
                row["span_id"]
                for row in spans
                if page_range is not None
                and page_range[0] <= (row["page_number"] or 0) <= page_range[1]
            ]
            index_entries.append(
                {
                    "role": sl.role,
                    "title": sl.title,
                    "ordinal": sl.ordinal,
                    "char_start": sl.char_start,
                    "char_end": sl.char_end,
                    "path": str(section_path.resolve()),
                    "page_start": page_range[0] if page_range else None,
                    "page_end": page_range[1] if page_range else None,
                    "span_ids": span_ids,
                }
            )
        index_json = json.dumps(index_entries, ensure_ascii=False, indent=2)
        index_path = sections_dir / "index.json"
        _atomic_write(index_path, index_json)
        artifact_hash = hashlib.sha256(index_json.encode("utf-8")).hexdigest()
        artifact_id = (
            "urn:company-wiki:artifact:sha256:"
            + hashlib.sha256(
                (
                    document["document_id"] + "\0sections\0" + SECTION_EXTRACTOR_VERSION
                ).encode("utf-8")
            ).hexdigest()
        )
        with store.transaction() as connection:
            connection.execute(
                """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,
                content_sha256,byte_size,mime_type,generator_name,generator_version,status,error,
                schema_version,source_sha256,metadata_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                ON CONFLICT(document_id,artifact_role,generator_name,generator_version) DO UPDATE SET
                path=excluded.path,content_sha256=excluded.content_sha256,byte_size=excluded.byte_size,
                status=excluded.status,error=excluded.error,
                schema_version=excluded.schema_version,source_sha256=excluded.source_sha256,
                metadata_json=excluded.metadata_json,
                created_at=excluded.created_at""",
                (
                    artifact_id,
                    document["document_id"],
                    document["primary_source_id"],
                    SECTION_ARTIFACT_ROLE,
                    str(index_path.resolve()),
                    artifact_hash,
                    len(index_json.encode("utf-8")),
                    "application/json",
                    SECTION_EXTRACTOR_NAME,
                    SECTION_EXTRACTOR_VERSION,
                    "completed",
                    None,
                    ARTIFACT_HANDLE_SCHEMA_VERSION,
                    document["source_sha256"] if "source_sha256" in document.keys() else "",
                    canonical_json(
                        {"schema_version": ARTIFACT_HANDLE_SCHEMA_VERSION, "sections": index_entries, "count": len(index_entries)}
                    ),
                ),
            )
        completed += 1
    return ProcessingReport(
        "extract_sections",
        completed=completed,
        skipped=skipped,
        failed=failed,
        eligible=len(documents),
        last_failed_document_id=last_failed_document_id,
        last_failed_path=last_failed_path,
    )
