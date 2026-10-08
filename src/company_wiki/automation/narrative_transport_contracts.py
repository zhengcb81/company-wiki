"""Versioned logical references and requests for persistent narrative bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

from .narrative_contracts import (
    BUNDLE_MAX_BYTES,
    NarrativeContractError,
    SourceRefValue,
    assert_no_physical_paths,
)


NARRATIVE_REF_SCHEMA = "narrative-ref/1"
NARRATIVE_REFERENCE_REQUEST_SCHEMA = "narrative-reference-request/1"
NARRATIVE_READ_REQUEST_SCHEMA = "narrative-read-request/1"
NARRATIVE_READ_RECEIPT_SCHEMA = "narrative-read-receipt/1"
MAX_REQUEST_BYTES = 16 * 1024
MAX_RECEIPT_BYTES = 16 * 1024
EXPECTED_SOURCE_FIELDS = frozenset({
    "canonical_entity_id", "market", "security_id", "document_kind",
    "fiscal_year", "fiscal_period",
})
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_REF_FIELDS = frozenset({
    "schema_version", "artifact_version_id", "artifact_sha256", "byte_size",
    "source_ref",
})


class NarrativeTransportError(ValueError):
    """A stable refusal; public diagnostics never contain paths or source text."""

    def __init__(self, status: str, reason: str):
        self.status = status
        self.reason = reason
        super().__init__(f"{status}: {reason}")


def _exact(value: object, fields: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise NarrativeContractError("narrative transport fields are not exact")
    assert_no_physical_paths(value)
    return value


def _source_constraints(value: object) -> dict[str, str | int | None]:
    item = _exact(value, EXPECTED_SOURCE_FIELDS)
    for key, constraint in item.items():
        if constraint is None:
            continue
        if key == "fiscal_year":
            if type(constraint) is not int or not 1900 <= constraint <= 9999:
                raise NarrativeContractError("fiscal_year must be an integer year or null")
        elif (
            not isinstance(constraint, str) or not constraint.strip()
            or constraint != constraint.strip() or len(constraint) > 256
        ):
            raise NarrativeContractError("source constraint must be trimmed text or null")
    return dict(item)


@dataclass(frozen=True)
class NarrativeRef:
    schema_version: str
    artifact_version_id: str
    artifact_sha256: str
    byte_size: int
    source_ref: SourceRefValue

    @classmethod
    def from_dict(cls, value: object) -> NarrativeRef:
        item = _exact(value, _REF_FIELDS)
        if item["schema_version"] != NARRATIVE_REF_SCHEMA:
            raise NarrativeContractError("unsupported narrative reference schema")
        identifier = item["artifact_version_id"]
        digest = item["artifact_sha256"]
        size = item["byte_size"]
        if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
            raise NarrativeContractError("artifact_version_id must be a logical identifier")
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise NarrativeContractError("artifact_sha256 must be lowercase SHA-256")
        if type(size) is not int or not 0 < size <= BUNDLE_MAX_BYTES:
            raise NarrativeContractError("narrative artifact size is invalid")
        return cls(
            NARRATIVE_REF_SCHEMA, identifier, digest, size,
            SourceRefValue.from_dict(item["source_ref"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_version_id": self.artifact_version_id,
            "artifact_sha256": self.artifact_sha256,
            "byte_size": self.byte_size,
            "source_ref": self.source_ref.to_dict(),
        }


@dataclass(frozen=True)
class NarrativeReadRequest:
    schema_version: str
    narrative_ref: NarrativeRef
    as_of_date: str | None
    expected_source: dict[str, str | int | None]

    @classmethod
    def from_dict(cls, value: object) -> NarrativeReadRequest:
        item = _exact(value, frozenset({
            "schema_version", "narrative_ref", "as_of_date", "expected_source",
        }))
        if item["schema_version"] != NARRATIVE_READ_REQUEST_SCHEMA:
            raise NarrativeContractError("unsupported narrative read request schema")
        cutoff = item["as_of_date"]
        # Explicit null requests current material, without a historical claim.
        # The field remains mandatory; malformed dates never imply this mode.
        if cutoff is not None:
            if not isinstance(cutoff, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cutoff):
                raise NarrativeContractError("as_of_date must be an ISO date or null")
            try:
                date.fromisoformat(cutoff)
            except ValueError as exc:
                raise NarrativeContractError("as_of_date must be an ISO date or null") from exc
        return cls(
            NARRATIVE_READ_REQUEST_SCHEMA,
            NarrativeRef.from_dict(item["narrative_ref"]), cutoff,
            _source_constraints(item["expected_source"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "narrative_ref": self.narrative_ref.to_dict(),
            "as_of_date": self.as_of_date,
            "expected_source": dict(self.expected_source),
        }


def parse_reference_request(value: object) -> SourceRefValue:
    item = _exact(value, frozenset({"schema_version", "source_ref"}))
    if item["schema_version"] != NARRATIVE_REFERENCE_REQUEST_SCHEMA:
        raise NarrativeContractError("unsupported narrative reference request schema")
    return SourceRefValue.from_dict(item["source_ref"])
