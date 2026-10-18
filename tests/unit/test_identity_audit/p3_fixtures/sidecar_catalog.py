"""Synthetic sidecar-catalog fixtures for the P3 read-only identity audit.

Lane write set: ``tools/identity_audit/``, ``tests/unit/test_identity_audit/``
and this card's plan directory.  The catalog-construction pattern was copied
from ``tests/unit/du11_identity_projection`` (not imported); nothing here reads
production config, a production catalog or a real original.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan

REQUEST_SCHEMA = "identity-audit-request/1"
REF_SCHEMA = "2.0"
SPAN_SCHEMA = "1.0.0"

# One real, unit-marked UTF-8 original.  "单位：百万元" is inside the closed
# unit-token set frozen by the card, so both the "token present" and the
# "token absent" shapes can be produced from the same file.
DEFAULT_BODY = "Acme 2026 H1 单位：百万元 营业收入 1,234\n".encode("utf-8")
PLAIN_BODY = "Acme 2026 H1 revenue 1,234\n".encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_binding(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": sha256_bytes(data), "bytes": len(data)}


@dataclass
class Fixture:
    """One indexed synthetic source plus the config that exposes it."""

    root: Path
    lake: Path
    catalog_dir: Path
    config_path: Path
    raw_path: Path
    sidecar_path: Path
    body: bytes
    facts: dict[str, Any]
    catalog: SourceCatalog
    ref: SourceRef
    manifest: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def sha256(self) -> str:
        return self.facts["content_sha256"]

    @property
    def document_id(self) -> str:
        return self.ref.document_id

    @property
    def source_id(self) -> str:
        return self.ref.source_id

    def reader(self) -> SourceVersionReader:
        return SourceVersionReader(self.catalog)

    def ref_payload(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": self.ref.document_id,
            "source_id": self.ref.source_id,
            "content_sha256": self.ref.content_sha256,
            "byte_size": self.ref.byte_size,
            "mime_type": self.ref.mime_type,
            "schema_version": REF_SCHEMA,
        }
        payload.update(overrides)
        return payload

    def text(self) -> str:
        return self.body.decode("utf-8")

    def close(self) -> None:
        self.catalog.close()


def _write_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: catalog\n"
        "reusable_root_kinds: [directory]\n"
        "roots:\n"
        "  - root_id: raw\n"
        "    path: lake\n"
        "    kind: directory\n"
        "    adapter_id: sidecar_filing_v1\n"
        "    reusable_for_filing: true\n",
        encoding="utf-8",
    )


def build_fixture(
    root: Path,
    *,
    body: bytes = DEFAULT_BODY,
    facts: dict[str, Any] | None = None,
    capture: bool = False,
    filename: str = "annual.txt",
) -> Fixture:
    """Index exactly one synthetic source under ``root`` and return the handle.

    ``capture=True`` additionally embeds the two dictionaries
    ``verified_availability_evidence`` needs to establish a prior verified
    capture, so the "availability present" path is reachable without any
    network access.
    """
    lake = root / "lake" / "Acme"
    lake.mkdir(parents=True, exist_ok=True)
    raw_path = lake / filename
    raw_path.write_bytes(body)
    digest = sha256_bytes(body)
    sidecar: dict[str, Any] = {
        "schema_version": "1.0",
        "canonical_entity_id": "Acme",
        "display_name": "Acme",
        "market": "CN",
        "security_id": "688012",
        "document_kind": "annual_report",
        "source_title": "Acme annual report",
        "fiscal_year": 2026,
        "fiscal_period": "H1",
        "period_end": "2026-06-30",
        "form_type": "annual",
        "provider": "sse",
        "provider_document_id": "acme-2026",
        "source_url": "https://example.invalid/acme-2026.txt",
        "language": "zh",
        "content_sha256": digest,
    }
    if capture:
        sidecar.update(
            {
                "byte_size": len(body),
                "mime_type": "text/plain",
                "retrieved_at": "2026-08-02T03:04:05Z",
                "adapter_name": "sse_adapter",
                "adapter_version": "1.0.0",
                "candidate": {
                    "provider": "sse",
                    "provider_document_id": "acme-2026",
                    "source_url": "https://example.invalid/acme-2026.txt",
                },
                "receipt": {
                    "candidate_id": "candidate-1",
                    "provider": "sse",
                    "provider_document_id": "acme-2026",
                    "source_url": "https://example.invalid/acme-2026.txt",
                    "staged_path": "staging/acme-2026.txt",
                    "content_sha256": digest,
                    "byte_size": len(body),
                    "mime_type": "text/plain",
                    "retrieved_at": "2026-08-02T03:04:05Z",
                    "http_status": 200,
                    "adapter_name": "sse_adapter",
                    "adapter_version": "1.0.0",
                },
            }
        )
    if facts:
        sidecar.update(facts)
    sidecar_path = raw_path.with_name(raw_path.name + ".source.json")
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf8")

    config_path = root / "config" / "source_catalog.yaml"
    _write_config(config_path)
    config = load_catalog_config(config_path)
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        row = catalog.reader.fetchone(
            "SELECT document_id, primary_source_id AS source_id FROM documents"
        )
        if row is None:
            raise AssertionError("fixture catalog indexed no document")
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["source_id"], digest)
        manifest = reader.describe_version(ref)
    except BaseException:
        catalog.close()
        raise
    # Freeze the fixture database without SQLite side files: the audit must be
    # able to prove it writes nothing, and a WAL-mode fixture makes the child's
    # read-only open create ``-shm`` on Linux (it stays invisible on Windows).
    catalog.close()
    store = catalog._store  # noqa: SLF001 - fixture owns this temporary catalog
    if store is not None and store._coalesced_connection is not None:  # noqa: SLF001
        store._coalesced_connection.close()  # noqa: SLF001
        store._coalesced_connection = None  # noqa: SLF001
    with sqlite3.connect(config.database_path) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
    for suffix in ("-wal", "-shm"):
        Path(str(config.database_path) + suffix).unlink(missing_ok=True)
    return Fixture(
        root=root,
        lake=lake,
        catalog_dir=config.catalog_dir,
        config_path=config_path,
        raw_path=raw_path,
        sidecar_path=sidecar_path,
        body=body,
        facts=sidecar,
        catalog=catalog,
        ref=ref,
        manifest=manifest,
    )


def make_span(
    source_id: str,
    *,
    char_start: int,
    char_end: int,
    raw_text: str | None,
    page_number: int | None = None,
    paragraph_index: int | None = None,
    table_index: int | None = None,
    row_index: int | None = None,
    column_index: int | None = None,
    structured_value: Any = None,
    parser_name: str = "fixture_parser",
    parser_version: str = "1.0.0",
    parse_status: str = "parsed",
    quality_flags: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a wire-valid span dict (derived ids are computed, never invented)."""
    coordinates = EvidenceCoordinates(
        page_number=page_number,
        paragraph_index=paragraph_index,
        table_index=table_index,
        row_index=row_index,
        column_index=column_index,
        char_start=char_start,
        char_end=char_end,
    )
    span = EvidenceSpan.create(
        source_id=source_id,
        coordinates=coordinates,
        raw_text=raw_text,
        structured_value=structured_value,
        parser_name=parser_name,
        parser_version=parser_version,
        parse_status=parse_status,
        quality_flags=tuple(quality_flags),
    )
    return span.to_dict()


def request_payload(
    refs: Iterable[dict[str, Any]],
    *,
    spans: Iterable[dict[str, Any]] = (),
    expect: dict[str, Any] | None = None,
    schema_version: str = REQUEST_SCHEMA,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "source_refs": list(refs),
        "evidence_spans": list(spans),
    }
    if expect is not None:
        payload["expect"] = expect
    return payload


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def write_request(root: Path, payload: Any, name: str = "request.json") -> Path:
    return write_json(root / name, payload)


def write_raw_request(root: Path, text: str, name: str = "request-raw.json") -> Path:
    """Write request bytes verbatim so duplicate keys and NaN survive."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def snapshot_tree(root: Path) -> dict[str, tuple[str, int, int]]:
    """Name-independent read-only proof: sha256, size and mtime_ns of every file.

    Keys are POSIX-normalized so prefix filters are platform independent.
    """
    state: dict[str, tuple[str, int, int]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        key = str(path.relative_to(root)).replace("\\", "/")
        state[key] = (
            sha256_bytes(path.read_bytes()),
            stat.st_size,
            stat.st_mtime_ns,
        )
    return state


__all__ = [
    "DEFAULT_BODY",
    "Fixture",
    "PLAIN_BODY",
    "REF_SCHEMA",
    "REQUEST_SCHEMA",
    "SPAN_SCHEMA",
    "build_fixture",
    "file_binding",
    "make_span",
    "request_payload",
    "sha256_bytes",
    "snapshot_tree",
    "write_json",
    "write_raw_request",
    "write_request",
    "CatalogConfig",
    "RootSpec",
]
