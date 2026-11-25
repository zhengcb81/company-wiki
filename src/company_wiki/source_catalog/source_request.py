"""Immutable request values shared by source lookup and acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

from company_wiki.wire_json import canonical_json_hash


SOURCE_RESOLVER_SCHEMA_VERSION = "1.0"
SOURCE_QUERY_REQUEST_SCHEMA_VERSION = "1.1"
_SOURCE_QUERY_REQUEST_SCHEMA_VERSIONS = {
    SOURCE_RESOLVER_SCHEMA_VERSION,
    SOURCE_QUERY_REQUEST_SCHEMA_VERSION,
}
_ISSUER_LINK_ID_RE = re.compile(r"issuer-link-v1:[0-9a-f]{64}")


class SourceResolutionError(ValueError):
    """Raised when a source request violates the resolver contract."""


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SourceResolutionError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _canonical_date(value: Any, name: str) -> str:
    value = _required_text(value, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceResolutionError(f"{name} must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SourceResolutionError(f"{name} must be canonical YYYY-MM-DD")
    return value


@dataclass(frozen=True)
class SourceRequest:
    entity: str
    document_kind: str
    as_of_date: str
    market: str | None = None
    security_id: str | None = None
    identity_scope: str | None = None
    issuer_link_id: str | None = None
    form_type: str | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    language: str | None = None
    provider: str | None = None
    provider_document_id: str | None = None
    # WU-4.1: "exact" (default) requires fiscal_year semantics; "latest_as_of"
    # derives the latest period from as_of_date + document_kind. Legacy callers
    # omitting mode keep exact-any-year behavior.
    mode: str | None = None
    allow_download: bool = False
    # An opaque provider page cursor.  It travels to the provider only; it is
    # deliberately NOT part of ``identity_dict``, so the identity of a target
    # never depends on which page of it was asked for.
    cursor: str | None = None
    schema_version: str = SOURCE_RESOLVER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        schema_version = _required_text(self.schema_version, "schema_version")
        if schema_version not in _SOURCE_QUERY_REQUEST_SCHEMA_VERSIONS:
            raise SourceResolutionError(
                "schema_version must be one of "
                f"{', '.join(sorted(_SOURCE_QUERY_REQUEST_SCHEMA_VERSIONS))}"
            )
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "entity", _required_text(self.entity, "entity"))
        object.__setattr__(
            self,
            "document_kind",
            _required_text(self.document_kind, "document_kind").lower(),
        )
        object.__setattr__(
            self, "as_of_date", _canonical_date(self.as_of_date, "as_of_date")
        )
        market = _optional_text(self.market, "market")
        provider = _optional_text(self.provider, "provider")
        object.__setattr__(self, "market", market.upper() if market else None)
        object.__setattr__(
            self,
            "security_id",
            _optional_text(self.security_id, "security_id"),
        )
        identity_scope = _optional_text(self.identity_scope, "identity_scope")
        issuer_link_id = _optional_text(self.issuer_link_id, "issuer_link_id")
        if identity_scope not in {None, "listing", "issuer"}:
            raise SourceResolutionError("identity_scope must be 'listing' or 'issuer'")
        if issuer_link_id is not None and _ISSUER_LINK_ID_RE.fullmatch(issuer_link_id) is None:
            raise SourceResolutionError("issuer_link_id is malformed")
        if schema_version == SOURCE_RESOLVER_SCHEMA_VERSION and (
            identity_scope is not None or issuer_link_id is not None
        ):
            raise SourceResolutionError(
                "identity scope fields require source query request schema 1.1"
            )
        if (identity_scope is None) != (issuer_link_id is None):
            raise SourceResolutionError(
                "identity_scope and issuer_link_id must be supplied together"
            )
        if identity_scope == "issuer" and (
            market is None or self.security_id is not None
        ):
            raise SourceResolutionError(
                "issuer identity scope requires market and forbids security_id"
            )
        if identity_scope == "listing" and self.security_id is None:
            raise SourceResolutionError("listing identity scope requires security_id")
        object.__setattr__(self, "identity_scope", identity_scope)
        object.__setattr__(self, "issuer_link_id", issuer_link_id)
        object.__setattr__(self, "provider", provider.lower() if provider else None)
        object.__setattr__(
            self, "form_type", _optional_text(self.form_type, "form_type")
        )
        object.__setattr__(
            self, "fiscal_period", _optional_text(self.fiscal_period, "fiscal_period")
        )
        object.__setattr__(self, "language", _optional_text(self.language, "language"))
        object.__setattr__(
            self,
            "provider_document_id",
            _optional_text(self.provider_document_id, "provider_document_id"),
        )
        if self.fiscal_year is not None:
            if isinstance(self.fiscal_year, bool) or not isinstance(
                self.fiscal_year, int
            ):
                raise SourceResolutionError("fiscal_year must be an integer or null")
            if self.fiscal_year < 1900 or self.fiscal_year > 2200:
                raise SourceResolutionError(
                    "fiscal_year is outside the supported range"
                )
        if not isinstance(self.allow_download, bool):
            raise SourceResolutionError("allow_download must be boolean")
        cursor = self.cursor
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor.strip() or cursor.strip() != cursor:
                raise SourceResolutionError("cursor must be nonempty unpadded text")
            object.__setattr__(self, "cursor", cursor)
        mode = self.mode
        if mode is not None:
            mode = str(mode).strip().lower()
            if mode not in {"exact", "latest_as_of"}:
                raise SourceResolutionError(
                    f"mode must be 'exact' or 'latest_as_of': {self.mode!r}"
                )
            object.__setattr__(self, "mode", mode)

    def identity_dict(self) -> dict[str, Any]:
        identity = {
            "schema_version": self.schema_version,
            "entity": self.entity,
            "market": self.market,
            "security_id": self.security_id,
            "document_kind": self.document_kind,
            "form_type": self.form_type,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "language": self.language,
            "provider": self.provider,
            "provider_document_id": self.provider_document_id,
            "as_of_date": self.as_of_date,
            "mode": self.mode,
        }
        if self.schema_version == SOURCE_QUERY_REQUEST_SCHEMA_VERSION:
            identity["identity_scope"] = self.identity_scope
            identity["issuer_link_id"] = self.issuer_link_id
        return identity

    @property
    def request_id(self) -> str:
        return "urn:company-wiki:source-request:sha256:" + canonical_json_hash(
            self.identity_dict()
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {**self.identity_dict(), "allow_download": self.allow_download}
        if self.cursor is not None:
            # Provider paging scope.  It is absent for every request that does
            # not page, so an existing provider payload stays byte-identical.
            payload["cursor"] = self.cursor
        return payload


__all__ = [
    "SOURCE_QUERY_REQUEST_SCHEMA_VERSION", "SOURCE_RESOLVER_SCHEMA_VERSION",
    "SourceRequest", "SourceResolutionError",
]
