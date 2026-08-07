"""Read-only lookup of extracted sections artifacts over an existing catalog."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


SECTION_QUERY_SCHEMA_VERSION = "1.0.0"


class SectionQueryError(ValueError):
    """Base error for read-only section queries."""


class SectionQueryInputError(SectionQueryError):
    """Raised when a document_id is missing or malformed."""


class SectionQueryNotFoundError(SectionQueryError):
    """Raised when no sections artifact matches the document_id."""


@dataclass(frozen=True)
class SectionEntry:
    role: str
    title: str
    ordinal: str
    char_start: int
    char_end: int
    path: str
    page_start: int | None = None
    page_end: int | None = None
    span_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "title": self.title,
            "ordinal": self.ordinal,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "path": self.path,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "span_ids": list(self.span_ids),
        }


@dataclass(frozen=True)
class SectionQueryResult:
    document_id: str
    document_kind: str
    title: str
    index_path: str
    sections: tuple[SectionEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_kind": self.document_kind,
            "title": self.title,
            "index_path": self.index_path,
            "count": len(self.sections),
            "sections": [entry.to_dict() for entry in self.sections],
        }


class SectionQueryService:
    """Read-only access to ``sections`` artifacts (no transaction, no lock)."""

    def __init__(self, database_path: Path | str):
        self._database_path = str(database_path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            f"file:{self._database_path}?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def list_sections(self, *, document_id: str) -> SectionQueryResult:
        if not document_id or not document_id.strip():
            raise SectionQueryInputError("document_id is required")
        with self._connection() as connection:
            row = connection.execute(
                """SELECT a.document_id, a.path, a.metadata_json,
                          d.document_kind, d.title
                   FROM artifacts a
                   JOIN documents d ON d.document_id = a.document_id
                   WHERE a.artifact_role = 'sections'
                     AND a.generator_name = 'source_catalog_section_extractor'
                     AND a.document_id = ?""",
                (document_id,),
            ).fetchone()
            if row is None:
                raise SectionQueryNotFoundError(
                    "no sections artifact for document_id"
                )
            try:
                meta = json.loads(row["metadata_json"] or "{}")
            except json.JSONDecodeError as exc:
                raise SectionQueryError(
                    "sections artifact metadata is not valid JSON"
                ) from exc
            entries = tuple(
                SectionEntry(
                    role=e["role"],
                    title=e["title"],
                    ordinal=e["ordinal"],
                    char_start=e["char_start"],
                    char_end=e["char_end"],
                    path=e["path"],
                    page_start=e.get("page_start"),
                    page_end=e.get("page_end"),
                    span_ids=tuple(e.get("span_ids") or ()),
                )
                for e in meta.get("sections", [])
            )
            return SectionQueryResult(
                document_id=row["document_id"],
                document_kind=row["document_kind"],
                title=row["title"],
                index_path=row["path"],
                sections=entries,
            )


__all__ = [
    "SECTION_QUERY_SCHEMA_VERSION",
    "SectionEntry",
    "SectionQueryError",
    "SectionQueryInputError",
    "SectionQueryNotFoundError",
    "SectionQueryResult",
    "SectionQueryService",
]
