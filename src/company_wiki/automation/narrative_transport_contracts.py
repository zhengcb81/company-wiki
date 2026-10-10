"""Versioned logical references and requests for persistent narrative bundles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any

from company_wiki.narrative_subject import NarrativeSubject

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
NARRATIVE_PROJECTED_REF_SCHEMA = "narrative-ref/2"
NARRATIVE_PROJECTED_REFERENCE_REQUEST_SCHEMA = "narrative-reference-request/2"
NARRATIVE_PROJECTED_READ_REQUEST_SCHEMA = "narrative-read-request/2"
NARRATIVE_PROJECTED_READ_RECEIPT_SCHEMA = "narrative-read-receipt/2"
MAX_REQUEST_BYTES = 16 * 1024
MAX_RECEIPT_BYTES = 16 * 1024
EXPECTED_SOURCE_FIELDS = frozenset(
    {
        "canonical_entity_id",
        "market",
        "security_id",
        "document_kind",
        "fiscal_year",
        "fiscal_period",
    }
)
EXPECTED_ISSUER_FIELDS = frozenset(
    {
        "market",
        "security_id",
        "provider_company_id",
        "provider_activity_company_id",
        "canonical_name",
        "entity_name",
    }
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_REF_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_version_id",
        "artifact_sha256",
        "byte_size",
        "source_ref",
    }
)


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
                raise NarrativeContractError(
                    "fiscal_year must be an integer year or null"
                )
        elif (
            not isinstance(constraint, str)
            or not constraint.strip()
            or constraint != constraint.strip()
            or len(constraint) > 256
        ):
            raise NarrativeContractError(
                "source constraint must be trimmed text or null"
            )
    return dict(item)


def _generation(value: object) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise NarrativeContractError("generation_sha256 must be lowercase SHA-256")
    return value


def _projection_subject(value: object) -> NarrativeSubject:
    try:
        subject = NarrativeSubject.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise NarrativeContractError("invalid narrative subject binding") from exc
    if subject.kind != "official_json":
        raise NarrativeContractError(
            "projected transport requires official_json subject"
        )
    return subject


def _issuer_constraints(value: object) -> dict[str, str | int] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or not value
        or not set(value) <= EXPECTED_ISSUER_FIELDS
    ):
        raise NarrativeContractError(
            "expected_issuer must contain concrete issuer constraints or null"
        )
    assert_no_physical_paths(value)
    for key, item in value.items():
        if (
            key in {"provider_company_id", "provider_activity_company_id"}
            and type(item) is int
        ):
            continue
        if (
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 256
        ):
            raise NarrativeContractError(
                "issuer constraint must be concrete trimmed text or provider integer"
            )
    return dict(value)


def _cutoff(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise NarrativeContractError("as_of_date must be an ISO date or null")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise NarrativeContractError("as_of_date must be an ISO date or null") from exc
    return value


@dataclass(frozen=True)
class NarrativeRef:
    schema_version: str
    artifact_version_id: str
    artifact_sha256: str
    byte_size: int
    source_ref: SourceRefValue | None = None
    subject_binding: NarrativeSubject | None = None
    generation_sha256: str | None = None

    @property
    def subject(self) -> NarrativeSubject:
        if self.subject_binding is not None:
            return self.subject_binding
        if self.source_ref is None:
            raise NarrativeContractError("narrative reference has no subject")
        return NarrativeSubject.from_raw(self.source_ref.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> NarrativeRef:
        projected = (
            isinstance(value, dict)
            and value.get("schema_version") == NARRATIVE_PROJECTED_REF_SCHEMA
        )
        fields = (
            (_REF_FIELDS - {"source_ref"}) | {"subject_binding", "generation_sha256"}
            if projected
            else _REF_FIELDS
        )
        item = _exact(value, frozenset(fields))
        if item["schema_version"] not in {
            NARRATIVE_REF_SCHEMA,
            NARRATIVE_PROJECTED_REF_SCHEMA,
        }:
            raise NarrativeContractError("unsupported narrative reference schema")
        identifier, digest, size = (
            item["artifact_version_id"],
            item["artifact_sha256"],
            item["byte_size"],
        )
        if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
            raise NarrativeContractError(
                "artifact_version_id must be a logical identifier"
            )
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise NarrativeContractError("artifact_sha256 must be lowercase SHA-256")
        if type(size) is not int or not 0 < size <= BUNDLE_MAX_BYTES:
            raise NarrativeContractError("narrative artifact size is invalid")
        if projected:
            return cls(
                NARRATIVE_PROJECTED_REF_SCHEMA,
                identifier,
                digest,
                size,
                subject_binding=_projection_subject(item["subject_binding"]),
                generation_sha256=_generation(item["generation_sha256"]),
            )
        return cls(
            NARRATIVE_REF_SCHEMA,
            identifier,
            digest,
            size,
            SourceRefValue.from_dict(item["source_ref"]),
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "artifact_version_id": self.artifact_version_id,
            "artifact_sha256": self.artifact_sha256,
            "byte_size": self.byte_size,
        }
        if self.schema_version == NARRATIVE_PROJECTED_REF_SCHEMA:
            if self.source_ref is not None or self.subject_binding is None:
                raise NarrativeContractError(
                    "projected reference cannot contain a raw source reference"
                )
            value.update(
                subject_binding=self.subject_binding.to_dict(),
                generation_sha256=self.generation_sha256,
            )
        else:
            if (
                self.source_ref is None
                or self.subject_binding is not None
                or self.generation_sha256 is not None
            ):
                raise NarrativeContractError(
                    "raw reference cannot contain projected binding"
                )
            value["source_ref"] = self.source_ref.to_dict()
        return value


@dataclass(frozen=True)
class NarrativeReadRequest:
    schema_version: str
    narrative_ref: NarrativeRef
    as_of_date: str | None
    expected_source: dict[str, str | int | None] = field(default_factory=dict)
    expected_issuer: dict[str, str | int] | None = None

    @classmethod
    def from_dict(cls, value: object) -> NarrativeReadRequest:
        projected = (
            isinstance(value, dict)
            and value.get("schema_version") == NARRATIVE_PROJECTED_READ_REQUEST_SCHEMA
        )
        constraint_field = "expected_issuer" if projected else "expected_source"
        item = _exact(
            value,
            frozenset(
                {"schema_version", "narrative_ref", "as_of_date", constraint_field}
            ),
        )
        expected_schema = (
            NARRATIVE_PROJECTED_READ_REQUEST_SCHEMA
            if projected
            else NARRATIVE_READ_REQUEST_SCHEMA
        )
        if item["schema_version"] != expected_schema:
            raise NarrativeContractError("unsupported narrative read request schema")
        reference = NarrativeRef.from_dict(item["narrative_ref"])
        if (reference.schema_version == NARRATIVE_PROJECTED_REF_SCHEMA) != projected:
            raise NarrativeContractError(
                "read schema must match narrative reference schema"
            )
        if projected:
            return cls(
                expected_schema,
                reference,
                _cutoff(item["as_of_date"]),
                expected_issuer=_issuer_constraints(item["expected_issuer"]),
            )
        return cls(
            expected_schema,
            reference,
            _cutoff(item["as_of_date"]),
            _source_constraints(item["expected_source"]),
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "narrative_ref": self.narrative_ref.to_dict(),
            "as_of_date": self.as_of_date,
        }
        if self.schema_version == NARRATIVE_PROJECTED_READ_REQUEST_SCHEMA:
            if self.expected_source:
                raise NarrativeContractError(
                    "projected read cannot contain raw identity constraints"
                )
            value["expected_issuer"] = (
                None if self.expected_issuer is None else dict(self.expected_issuer)
            )
        else:
            if self.expected_issuer is not None:
                raise NarrativeContractError(
                    "raw read cannot contain projected issuer constraints"
                )
            value["expected_source"] = dict(self.expected_source)
        return value


def parse_reference_request(value: object) -> SourceRefValue:
    item = _exact(value, frozenset({"schema_version", "source_ref"}))
    if item["schema_version"] != NARRATIVE_REFERENCE_REQUEST_SCHEMA:
        raise NarrativeContractError("unsupported narrative reference request schema")
    return SourceRefValue.from_dict(item["source_ref"])


def parse_projected_reference_request(value: object) -> tuple[NarrativeSubject, str]:
    item = _exact(
        value, frozenset({"schema_version", "subject_binding", "generation_sha256"})
    )
    if item["schema_version"] != NARRATIVE_PROJECTED_REFERENCE_REQUEST_SCHEMA:
        raise NarrativeContractError(
            "unsupported projected narrative reference request schema"
        )
    return _projection_subject(item["subject_binding"]), _generation(
        item["generation_sha256"]
    )
