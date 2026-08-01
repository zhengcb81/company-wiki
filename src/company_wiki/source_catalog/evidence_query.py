"""Exact, read-only EvidenceSpan lookup over an existing source catalog."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    EvidenceSpanError,
)
from company_wiki.source_contract.source_manifest import SOURCE_ID_PREFIX


EVIDENCE_QUERY_SCHEMA_VERSION = "1.0.0"
MAX_EVIDENCE_QUERY_LIMIT = 500

_SOURCE_ID_RE = re.compile(rf"^{re.escape(SOURCE_ID_PREFIX)}[0-9a-f]{{64}}$")
_DOCUMENT_ID_RE = re.compile(
    r"^urn:company-wiki:document:sha256:[0-9a-f]{64}$"
)
_INTEGER_RE = re.compile(r"^(0|[1-9]\d*)$")
_CHAR_RANGE_RE = re.compile(r"^(0|[1-9]\d*)-(0|[1-9]\d*)$")
_COORDINATE_ORDER = {
    "page": 0,
    "paragraph": 1,
    "table": 2,
    "row": 3,
    "column": 4,
    "chars": 5,
}


class EvidenceQueryError(ValueError):
    """Base error for exact source-catalog evidence queries."""


class EvidenceQueryInputError(EvidenceQueryError):
    """Raised when an identifier, locator, or page request is invalid."""


class EvidenceQueryUnavailableError(EvidenceQueryError):
    """Raised when an existing catalog cannot be opened read-only."""


class EvidenceQueryNotFoundError(EvidenceQueryError):
    """Raised when no exact evidence row matches the supplied identity."""


class EvidenceQueryIntegrityError(EvidenceQueryError):
    """Raised when persisted evidence cannot pass its canonical contract."""


@dataclass(frozen=True)
class EvidenceLocationRef:
    location_id: str
    root_id: str
    relative_path: str
    absolute_path: str
    role: str
    location_status: str
    observed_size: int | None
    observed_mtime_ns: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "root_id": self.root_id,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "role": self.role,
            "location_status": self.location_status,
            "observed_size": self.observed_size,
            "observed_mtime_ns": self.observed_mtime_ns,
        }


@dataclass(frozen=True)
class EvidenceQueryResult:
    span: EvidenceSpan
    document_id: str
    title: str
    source_type: str
    document_kind: str
    published_date: str | None
    source_status: str
    content_sha256: str
    byte_size: int
    mime_type: str
    locations: tuple[EvidenceLocationRef, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_QUERY_SCHEMA_VERSION,
            "span": self.span.to_dict(),
            "document": {
                "document_id": self.document_id,
                "title": self.title,
                "source_type": self.source_type,
                "document_kind": self.document_kind,
                "published_date": self.published_date,
                "source_status": self.source_status,
            },
            "source": {
                "source_id": self.span.source_id,
                "content_sha256": self.content_sha256,
                "byte_size": self.byte_size,
                "mime_type": self.mime_type,
            },
            "locations": [item.to_dict() for item in self.locations],
        }


@dataclass(frozen=True)
class EvidenceQueryPage:
    source_id: str | None
    document_id: str | None
    total: int
    limit: int
    offset: int
    items: tuple[EvidenceQueryResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_QUERY_SCHEMA_VERSION,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "items": [item.to_dict() for item in self.items],
        }


def _validate_source_id(value: Any) -> str:
    if not isinstance(value, str) or not _SOURCE_ID_RE.fullmatch(value):
        raise EvidenceQueryInputError("source_id must be the canonical SHA-256 URN")
    return value


def _validate_document_id(value: Any) -> str:
    if not isinstance(value, str) or not _DOCUMENT_ID_RE.fullmatch(value):
        raise EvidenceQueryInputError(
            "document_id must be the canonical document SHA-256 URN"
        )
    return value


def _validate_locator(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("loc:v1/"):
        raise EvidenceQueryInputError("locator must use canonical loc:v1 syntax")
    values: dict[str, int | None] = {
        "page_number": None,
        "paragraph_index": None,
        "table_index": None,
        "row_index": None,
        "column_index": None,
        "char_start": None,
        "char_end": None,
    }
    field_names = {
        "page": "page_number",
        "paragraph": "paragraph_index",
        "table": "table_index",
        "row": "row_index",
        "column": "column_index",
    }
    previous_order = -1
    seen: set[str] = set()
    for segment in value.split("/")[1:]:
        key, separator, raw = segment.partition(":")
        if not separator or key not in _COORDINATE_ORDER or key in seen:
            raise EvidenceQueryInputError("locator contains invalid coordinate segments")
        order = _COORDINATE_ORDER[key]
        if order <= previous_order:
            raise EvidenceQueryInputError("locator segments must use canonical order")
        previous_order = order
        seen.add(key)
        if key == "chars":
            match = _CHAR_RANGE_RE.fullmatch(raw)
            if match is None:
                raise EvidenceQueryInputError("locator chars range is invalid")
            values["char_start"] = int(match.group(1))
            values["char_end"] = int(match.group(2))
        else:
            if _INTEGER_RE.fullmatch(raw) is None:
                raise EvidenceQueryInputError("locator coordinate must be an integer")
            values[field_names[key]] = int(raw)
    try:
        coordinates = EvidenceCoordinates(**values)
    except (EvidenceSpanError, TypeError, ValueError) as exc:
        raise EvidenceQueryInputError(f"locator is invalid: {exc}") from exc
    if coordinates.locator() != value:
        raise EvidenceQueryInputError("locator must use canonical loc:v1 syntax")
    return value


def _validate_page(limit: Any, offset: Any) -> tuple[int, int]:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise EvidenceQueryInputError("limit must be an integer")
    if limit <= 0 or limit > MAX_EVIDENCE_QUERY_LIMIT:
        raise EvidenceQueryInputError(
            f"limit must be in [1, {MAX_EVIDENCE_QUERY_LIMIT}]"
        )
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise EvidenceQueryInputError("offset must be a non-negative integer")
    return limit, offset


class EvidenceQueryService:
    """Query a pre-existing catalog through SQLite's enforced read-only mode."""

    def __init__(self, database_path: Path):
        if not isinstance(database_path, Path):
            raise TypeError("database_path must be pathlib.Path")
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if not self.database_path.is_file():
            raise EvidenceQueryUnavailableError("source catalog database is unavailable")
        wal_path = Path(str(self.database_path) + "-wal")
        shm_path = Path(str(self.database_path) + "-shm")
        if wal_path.exists() and not shm_path.is_file():
            raise EvidenceQueryUnavailableError(
                "source catalog WAL cannot be read without existing shared memory"
            )
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        if not wal_path.exists():
            uri += "&immutable=1"
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                uri,
                uri=True,
                timeout=5.0,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
        except EvidenceQueryError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise EvidenceQueryUnavailableError(
                f"source catalog read failed: {type(exc).__name__}: {str(exc)[:500]}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _locations(
        connection: sqlite3.Connection, *, source_id: str, document_id: str
    ) -> tuple[EvidenceLocationRef, ...]:
        rows = connection.execute(
            """SELECT l.location_id,l.root_id,l.relative_path,l.absolute_path,
            l.role,l.location_status,l.observed_size,l.observed_mtime_ns,r.priority
            FROM locations l JOIN roots r ON r.root_id=l.root_id
            WHERE l.source_id=? AND l.document_id=?
            ORDER BY CASE l.location_status WHEN 'active' THEN 0
                WHEN 'missing' THEN 1 WHEN 'quarantined' THEN 2 ELSE 3 END,
                r.priority,l.root_id,l.relative_path,l.location_id""",
            (source_id, document_id),
        ).fetchall()
        return tuple(
            EvidenceLocationRef(
                location_id=row["location_id"],
                root_id=row["root_id"],
                relative_path=row["relative_path"],
                absolute_path=row["absolute_path"],
                role=row["role"],
                location_status=row["location_status"],
                observed_size=row["observed_size"],
                observed_mtime_ns=row["observed_mtime_ns"],
            )
            for row in rows
        )

    @classmethod
    def _result(
        cls, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> EvidenceQueryResult:
        try:
            payload = json.loads(row["span_json"])
            span = EvidenceSpan.from_dict(payload)
        except (json.JSONDecodeError, EvidenceSpanError, TypeError, ValueError) as exc:
            raise EvidenceQueryIntegrityError(
                f"persisted span failed canonical validation: {type(exc).__name__}"
            ) from exc
        expected = {
            "span_id": row["span_id"],
            "source_id": row["source_id"],
            "locator": row["locator"],
            "parser_name": row["parser_name"],
            "parser_version": row["parser_version"],
            "parse_status": row["parse_status"],
            "raw_text": row["raw_text"],
        }
        actual = {
            "span_id": span.span_id,
            "source_id": span.source_id,
            "locator": span.locator,
            "parser_name": span.parser_name,
            "parser_version": span.parser_version,
            "parse_status": span.parse_status.value,
            "raw_text": span.raw_text,
        }
        if actual != expected or span.source_id != (
            SOURCE_ID_PREFIX + row["content_sha256"]
        ):
            raise EvidenceQueryIntegrityError(
                "persisted span conflicts with catalog identity columns"
            )
        return EvidenceQueryResult(
            span=span,
            document_id=row["document_id"],
            title=row["title"],
            source_type=row["source_type"],
            document_kind=row["document_kind"],
            published_date=row["published_date"],
            source_status=row["source_status"],
            content_sha256=row["content_sha256"],
            byte_size=row["byte_size"],
            mime_type=row["mime_type"],
            locations=cls._locations(
                connection,
                source_id=span.source_id,
                document_id=row["document_id"],
            ),
        )

    @staticmethod
    def _select_sql(where: str) -> str:
        return f"""SELECT e.span_id,e.document_id,e.source_id,e.locator,e.raw_text,
            e.span_json,e.parser_name,e.parser_version,e.parse_status,
            d.title,d.source_type,d.document_kind,d.published_date,d.source_status,
            s.content_sha256,s.byte_size,s.mime_type
            FROM evidence_spans e
            JOIN documents d ON d.document_id=e.document_id
            JOIN sources s ON s.source_id=e.source_id
            WHERE {where}"""

    def lookup(self, *, source_id: str, locator: str) -> EvidenceQueryResult:
        source_id = _validate_source_id(source_id)
        locator = _validate_locator(locator)
        with self._connection() as connection:
            row = connection.execute(
                self._select_sql("e.source_id=? AND e.locator=?"),
                (source_id, locator),
            ).fetchone()
            if row is None:
                raise EvidenceQueryNotFoundError(
                    "no evidence matches the exact source_id and locator"
                )
            return self._result(connection, row)

    def list_spans(
        self,
        *,
        source_id: str | None = None,
        document_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EvidenceQueryPage:
        if (source_id is None) == (document_id is None):
            raise EvidenceQueryInputError(
                "exactly one of source_id or document_id is required"
            )
        if source_id is not None:
            source_id = _validate_source_id(source_id)
            where = "e.source_id=?"
            identity = source_id
        else:
            assert document_id is not None
            document_id = _validate_document_id(document_id)
            where = "e.document_id=?"
            identity = document_id
        limit, offset = _validate_page(limit, offset)
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM evidence_spans e WHERE {where}",
                    (identity,),
                ).fetchone()[0]
            )
            if total == 0:
                raise EvidenceQueryNotFoundError(
                    "no evidence matches the exact source or document identity"
                )
            rows = connection.execute(
                self._select_sql(where)
                + " ORDER BY e.source_id,e.locator,e.span_id LIMIT ? OFFSET ?",
                (identity, limit, offset),
            ).fetchall()
            return EvidenceQueryPage(
                source_id=source_id,
                document_id=document_id,
                total=total,
                limit=limit,
                offset=offset,
                items=tuple(self._result(connection, row) for row in rows),
            )


__all__ = [
    "EVIDENCE_QUERY_SCHEMA_VERSION",
    "MAX_EVIDENCE_QUERY_LIMIT",
    "EvidenceLocationRef",
    "EvidenceQueryError",
    "EvidenceQueryInputError",
    "EvidenceQueryIntegrityError",
    "EvidenceQueryNotFoundError",
    "EvidenceQueryPage",
    "EvidenceQueryResult",
    "EvidenceQueryService",
    "EvidenceQueryUnavailableError",
]
