"""Strict read-only source resolver for query-before-download reuse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .service import SourceCatalog


def _verified_assertion_identity(
    store: Any, source_id: str, content_sha256: str, document_id: str
) -> dict[str, Any] | None:
    """Try to resolve legacy identity via a verified assertion.

    Phase 15.5: assertions are matched by source_id first; when the source
    path cannot match (placeholder documents surface source_id as NULL), fall
    back to the document_id path.
    """
    try:
        from .assertion_service import (
            get_verified_assertion,
            get_verified_assertion_by_document,
        )

        candidates = [get_verified_assertion(store, source_id, content_sha256)]
        if source_id != document_id:
            candidates.append(
                get_verified_assertion_by_document(store, document_id, content_sha256)
            )
        for a in candidates:
            if a is None:
                continue
            return {
                "market": a.get("market"),
                "security_id": a.get("security_id"),
                "fiscal_year": a.get("fiscal_year"),
                "fiscal_period": a.get("fiscal_period"),
                "document_kind": a.get("document_kind"),
                "provider": a.get("provider"),
                "provider_document_id": a.get("provider_document_id"),
                "source_url": a.get("source_url"),
                "filing_date": a.get("filing_date"),
            }
        return None
    except ImportError:
        return None


SOURCE_RESOLVER_SCHEMA_VERSION = "1.0"
_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)")


class SourceResolutionError(ValueError):
    """Raised when a source request violates the resolver contract."""


class ResolutionStatus(str, Enum):
    """Resolution outcome for query-before-download reuse.

    IDENTITY_CONFLICT means a document's metadata *contradicts* the request
    identity (market or security_id present but different), or would be
    reusable without verifiable identity — it blocks reuse and download.  A
    document that merely *lacks* identity metadata (missing_fail_closed, no
    verified assertion) and has no canonical file (placeholder) is NOT a
    conflict (Phase 15.3): it falls through the year/form/handle checks and
    resolves MISSING, which permits a download.
    """

    REUSED_EXACT = "reused_exact"
    REUSED_EQUIVALENT = "reused_equivalent"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    IDENTITY_CONFLICT = "identity_conflict"


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


def _json_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceRequest:
    entity: str
    document_kind: str
    as_of_date: str
    market: str | None = None
    security_id: str | None = None
    form_type: str | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    language: str | None = None
    provider: str | None = None
    provider_document_id: str | None = None
    allow_download: bool = False
    schema_version: str = SOURCE_RESOLVER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_RESOLVER_SCHEMA_VERSION:
            raise SourceResolutionError(
                f"schema_version must be {SOURCE_RESOLVER_SCHEMA_VERSION}"
            )
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

    def identity_dict(self) -> dict[str, Any]:
        return {
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
        }

    @property
    def request_id(self) -> str:
        return "urn:company-wiki:source-request:sha256:" + _json_hash(
            self.identity_dict()
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_dict(), "allow_download": self.allow_download}


@dataclass(frozen=True)
class SourceHandle:
    schema_version: str
    document_id: str
    source_id: str
    entity_ids: tuple[str, ...]
    title: str
    source_type: str
    document_kind: str
    published_date: str
    fiscal_year: int | None
    fiscal_period: str | None
    form_type: str | None
    language: str | None
    provider: str | None
    provider_document_id: str | None
    https_url: str | None
    canonical_location_id: str
    canonical_path: str
    content_sha256: str
    snapshot_sha256: str
    mime_type: str
    byte_size: int
    retrieved_at: str
    collector_name: str
    collector_version: str
    source_status: str
    duplicate_group_id: str
    exact_duplicate_location_count: int
    capture_ready: bool
    missing_capture_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "entity_ids": list(self.entity_ids),
            "missing_capture_fields": list(self.missing_capture_fields),
        }


@dataclass(frozen=True)
class ResolutionResult:
    schema_version: str
    request_id: str
    status: ResolutionStatus
    reason: str
    download_required: bool
    download_allowed: bool
    matches: tuple[SourceHandle, ...]
    # Phase 19.6: per-candidate exclusion reasons for diagnostics (empty when
    # no candidate passed the entity gate and none were rejected).
    debug_trace: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status.value,
            "reason": self.reason,
            "download_required": self.download_required,
            "download_allowed": self.download_allowed,
            "matches": [item.to_dict() for item in self.matches],
        }
        if self.debug_trace:
            payload["debug_trace"] = list(self.debug_trace)
        return payload


def _source_metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    for key in ("acquisition", "dayu_meta"):
        value = metadata.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def _fiscal_year(document: dict[str, Any], metadata: dict[str, Any]) -> int | None:
    value = metadata.get("fiscal_year")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    years = [int(item) for item in _YEAR_RE.findall(document["title"])]
    return years[-1] if years else None


def _provider_identity(
    metadata: dict[str, Any],
) -> tuple[str | None, str | None, set[str]]:
    provider_value = metadata.get("provider")
    provider = str(provider_value).strip().lower() if provider_value else None
    form_type = str(metadata.get("form_type") or "").upper()
    if provider is None and (
        metadata.get("accession_number") or form_type.startswith(("10-", "20-", "6-"))
    ):
        provider = "sec"
    identities = {
        str(value).strip()
        for value in (
            metadata.get("accession_number"),
            metadata.get("provider_document_id"),
            metadata.get("source_id"),
            metadata.get("document_id"),
        )
        if value is not None and str(value).strip()
    }
    preferred = next(
        (
            str(value).strip()
            for value in (
                metadata.get("accession_number"),
                metadata.get("provider_document_id"),
                metadata.get("source_id"),
                metadata.get("document_id"),
            )
            if value is not None and str(value).strip()
        ),
        None,
    )
    return provider, preferred, identities


# Sentinel issuer: a token shared by more than one issuer never anchors.
_AMBIGUOUS_ISSUER = ""


@lru_cache(maxsize=8)
def _load_issuer_index(
    catalog_dir: str,
) -> tuple[dict[str, str], dict[str, frozenset[str]]]:
    """Build a ticker/alias -> issuer (canonical-name) index from security_master.

    Phase 18.1: dual-class tickers (GOOGL/GOOG) and same-issuer names share the
    same canonical issuer, so a request by any one ticker can reuse documents
    filed under the issuer name.  Returns ``(token_to_issuer, issuer_tokens)``:
    every token of every record maps to its canonical issuer, and every issuer
    maps to the full set of its tokens (all classes, aliases, tickers).  A
    token shared by two different issuers maps to ``_AMBIGUOUS_ISSUER`` and
    never anchors (fail-closed).
    """
    token_to_issuer: dict[str, str] = {}
    issuer_tokens: dict[str, set[str]] = {}
    root = Path(catalog_dir) / "security_master"
    for market_file in ("cn", "hk", "us"):
        path = root / f"{market_file}.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for record in payload.get("records") or []:
            canonical = str(record.get("canonical_name") or "").strip()
            if not canonical:
                continue
            issuer = canonical.casefold()
            tokens = {issuer}
            for alias in record.get("aliases") or []:
                alias_text = str(alias).strip()
                if alias_text:
                    tokens.add(alias_text.casefold())
            for key in ("ticker", "security_id", "canonical_name"):
                value = str(record.get(key) or "").strip()
                if value:
                    tokens.add(value.casefold())
            issuer_tokens.setdefault(issuer, set()).update(tokens)
            for token in tokens:
                existing = token_to_issuer.get(token)
                if existing is None:
                    token_to_issuer[token] = issuer
                elif existing != issuer:
                    token_to_issuer[token] = _AMBIGUOUS_ISSUER
    return token_to_issuer, {
        issuer: frozenset(values) for issuer, values in issuer_tokens.items()
    }


class SourceResolver:
    """Resolve existing catalog sources without performing acquisition side effects."""

    def __init__(self, catalog: SourceCatalog):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog

    def resolve(self, request: SourceRequest) -> ResolutionResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        semantic: list[SourceHandle] = []
        exact: list[SourceHandle] = []
        future_matches = 0
        unknown_date_matches = 0
        identity_mismatch = 0
        # Phase 19.6: per-candidate exclusion reasons for diagnostics, plus the
        # count of documents rejected at the entity gate.
        trace: list[str] = []
        entity_gate_rejected = 0
        # Only locations under a *reusable* root kind are canonical reuse
        # candidates. Config-driven (CatalogConfig.reusable_root_kinds,
        # default company_raw): adding a kind makes every already-indexed
        # document under such roots directly reusable without a download.
        # filing-fetch enforces its own independent path allowance
        # (config-driven too), so the two gates stay in sync via
        # configuration, not code.
        reusable_root_ids = frozenset(
            root.root_id
            for root in self.catalog.config.roots
            if root.kind in set(self.catalog.config.reusable_root_kinds)
        )
        # WU-3.2 (F-021/F-026): SQL-pushdown candidate lookup — the full-table
        # Python scan is replaced by a kind/status-filtered, capped query.
        # root_ids/entity are deliberately NOT pushed to SQL: the per-document
        # gates below (entity anchoring, identity conflict before the
        # reusable-root check, form/date) are the source of truth, and a
        # contradictory-identity document must surface as IDENTITY_CONFLICT
        # even when its root is not reusable (fail-closed, Phase 15.3).
        candidates = self.catalog.query_filing_candidates(
            document_kind=request.document_kind,
            source_statuses=("active",),
            limit=100,
        )
        for document in candidates:
            if not self._entity_matches(request.entity, document):
                entity_gate_rejected += 1
                continue
            if document["document_kind"] != request.document_kind:
                trace.append(f"{document['title']}: document_kind_mismatch")
                continue
            # WU-3.1 (F-024) defense-in-depth: even if the query layer leaked
            # a non-active document, the resolver refuses to form a handle.
            if document["source_status"] != "active":
                trace.append(
                    f"{document['title']}: rejected_source_status="
                    f"{document['source_status']}"
                )
                continue
            metadata = _source_metadata(document)
            # --- identity-aware market/security_id filtering ---
            market_match = self._identity_matches(request, metadata)
            if market_match == "conflict":
                identity_mismatch += 1
                trace.append(
                    f"{document['title']}: identity_conflict_market_or_security_id"
                )
                continue
            if market_match == "missing_fail_closed":
                # Try verified assertion as fallback identity source (CW-2.28 T2-11).
                assertion = _verified_assertion_identity(
                    self.catalog.store,
                    document["source_id"],
                    document.get("content_sha256") or None,
                    document["document_id"],
                )
                if assertion and request.market and request.security_id:
                    a_market = (
                        str(assertion.get("market") or "").strip().upper() or None
                    )
                    a_secid = str(assertion.get("security_id") or "").strip() or None
                    if a_market and a_secid:
                        if (
                            request.market.upper() == a_market
                            and request.security_id == a_secid
                        ):
                            market_match = "match"
                            # Enrich metadata with assertion values
                            if "market" not in metadata or not metadata.get("market"):
                                metadata["market"] = a_market
                                metadata["security_id"] = a_secid
                                metadata["fiscal_year"] = metadata.get(
                                    "fiscal_year"
                                ) or assertion.get("fiscal_year")
                # Missing identity metadata with no verified assertion is NOT a
                # true identity conflict (Phase 15.3): the year/form/handle
                # checks below decide whether the document satisfies the
                # request.  A placeholder with no canonical file yields
                # handle=None → MISSING, which permits a download.  A
                # document that WOULD be reusable still stays fail-closed —
                # the strict check runs after the handle is built below.
            year = _fiscal_year(document, metadata)
            if request.fiscal_year is not None and year != request.fiscal_year:
                trace.append(f"{document['title']}: fiscal_year_mismatch")
                continue
            form_type = str(metadata.get("form_type") or "").strip() or None
            if request.form_type and form_type != request.form_type:
                trace.append(f"{document['title']}: form_type_mismatch")
                continue
            fiscal_period = str(metadata.get("fiscal_period") or "").strip() or None
            if request.fiscal_period and fiscal_period != request.fiscal_period:
                trace.append(f"{document['title']}: fiscal_period_mismatch")
                continue
            language = str(metadata.get("language") or "").strip() or None
            if request.language and language != request.language:
                trace.append(f"{document['title']}: language_mismatch")
                continue
            provider, provider_document_id, identities = _provider_identity(metadata)
            if request.provider and provider and provider != request.provider:
                trace.append(f"{document['title']}: provider_mismatch")
                continue
            strong_identity = bool(
                request.provider_document_id
                and request.provider_document_id in identities
                and (not request.provider or provider == request.provider)
            )
            if request.provider_document_id and not strong_identity:
                trace.append(f"{document['title']}: provider_document_id_not_strong")
                continue
            published = document["published_date"]
            if not published:
                unknown_date_matches += 1
                trace.append(f"{document['title']}: published_date_unknown")
                continue
            if published > request.as_of_date:
                future_matches += 1
                trace.append(f"{document['title']}: published_after_as_of_date")
                continue
            canonical_locations = [
                item
                for item in document["locations"]
                if item.get("is_canonical")
                and item.get("role") == "original_primary"
                and item.get("location_status") == "active"
                # WU-3.1: provider-rejected paths never count as canonical.
                and ".rejections" not in item.get("relative_path", "").replace("\\", "/")
            ]
            if not canonical_locations:
                if any(
                    item.get("role") == "original_primary"
                    and ".rejections" in item.get("relative_path", "").replace("\\", "/")
                    for item in document["locations"]
                ):
                    trace.append(f"{document['title']}: rejections_path")
                else:
                    trace.append(f"{document['title']}: no_canonical_active_location")
                continue
            if not any(
                item.get("root_id") in reusable_root_ids
                for item in canonical_locations
            ):
                # No canonical location under a reusable root kind: not a
                # reusable source (add the root kind to
                # `reusable_root_kinds` in source_catalog.yaml to reuse it).
                trace.append(f"{document['title']}: no_reusable_root_location")
                continue
            handle = self._handle(
                document,
                metadata=metadata,
                fiscal_year=year,
                fiscal_period=fiscal_period,
                form_type=form_type,
                language=language,
                provider=provider,
                provider_document_id=provider_document_id,
            )
            if handle is None:
                trace.append(f"{document['title']}: placeholder_no_handle")
                continue
            if market_match == "missing_fail_closed":
                # Reusable, but identity is unverifiable (no metadata, no
                # assertion): stay fail-closed for reuse (CW-3.5 strict).
                # Only placeholders (handle=None) fall through to MISSING so
                # an authorized download can proceed (Phase 15.3).
                identity_mismatch += 1
                trace.append(f"{document['title']}: identity_unverifiable_strict")
                continue
            if not handle.capture_ready:
                # Phase 16.2: a capture-incomplete handle (e.g. missing
                # https_url) cannot be consumed by filing-fetch; offering it
                # as reusable deadlocks the download path. Treat as no match
                # so the acquisition path proceeds to the adapter.
                trace.append(f"{document['title']}: capture_incomplete")
                continue
            semantic.append(handle)
            trace.append(f"{document['title']}: matched")
            if strong_identity:
                exact.append(handle)
        if trace or entity_gate_rejected:
            trace.insert(0, f"entity_gate_rejected: {entity_gate_rejected}")
        debug_trace = tuple(trace)
        if len(exact) == 1:
            return self._result(
                request,
                ResolutionStatus.REUSED_EXACT,
                "one_existing_source_matches_provider_identity",
                (exact[0],),
                debug_trace,
            )
        if len(exact) > 1:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "multiple_existing_sources_match_provider_identity",
                tuple(exact),
                debug_trace,
            )
        if len(semantic) == 1:
            return self._result(
                request,
                ResolutionStatus.REUSED_EQUIVALENT,
                "one_existing_source_satisfies_semantic_request",
                (semantic[0],),
                debug_trace,
            )
        if len(semantic) > 1:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "multiple_existing_sources_match_semantic_request",
                tuple(semantic),
                debug_trace,
            )
        if identity_mismatch:
            return self._result(
                request,
                ResolutionStatus.IDENTITY_CONFLICT,
                "identity_mismatch_market_or_security_id",
                (),
                debug_trace,
            )
        if future_matches:
            reason = "only_sources_published_after_as_of_date"
        elif unknown_date_matches:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "matching_sources_have_unknown_published_date",
                (),
                debug_trace,
            )
        else:
            reason = "no_existing_source_satisfies_request"
        return self._result(
            request, ResolutionStatus.MISSING, reason, (), debug_trace
        )

    @staticmethod
    def _identity_matches(request: SourceRequest, metadata: dict[str, Any]) -> str:
        """Check market/security_id identity.

        Returns:
            "match" — identity matches or request has no identity filter
            "conflict" — explicit identity conflict (market or security_id mismatch)
            "missing_fail_closed" — request has identity but candidate has none
        """
        req_market = request.market
        req_security_id = request.security_id
        if not req_market and not req_security_id:
            return "match"
        cand_market = str(metadata.get("market") or "").strip().upper() or None
        cand_security_id = str(metadata.get("security_id") or "").strip() or None
        # CW-3.5: truly empty identity → fail_closed (strict).
        # Company-name-as-security_id → soft-match (CW-2.27H).
        if not cand_market and not cand_security_id:
            return "missing_fail_closed"
        if req_market and cand_market and req_market != cand_market:
            return "conflict"

        def _ticker_norm(value: str) -> str:
            # Exchange-style tickers compare modulo leading zeros and case:
            # HKEX "03896" == "3896", "02020" == "2020" (ADR-008 Strategy B;
            # same normalization as the portfolio promoter).
            return value.strip().lstrip("0").casefold()

        if (
            req_security_id
            and cand_security_id
            and _ticker_norm(req_security_id) != _ticker_norm(cand_security_id)
        ):
            # CW-2.27H: cand_security_id stored as a company name (non-numeric
            # prefix) was the default before identity normalization.  Treat as
            # unknown (match) — the remaining document-kind / fiscal-year
            # filters still guarantee precision.
            if cand_security_id and not cand_security_id[0].isdigit():
                return "match"
            return "conflict"
        return "match"

    def _issuer_index(self) -> tuple[dict[str, str], dict[str, frozenset[str]]]:
        catalog_dir = getattr(self.catalog.config, "catalog_dir", None)
        if catalog_dir is None:
            return {}, {}
        return _load_issuer_index(str(catalog_dir))

    def _entity_matches(self, entity: str, document: dict[str, Any]) -> bool:
        wanted = entity.casefold()
        doc_values = {
            str(item.get("entity_id") or "").casefold()
            for item in document["entities"]
        } | {
            str(item.get("name") or "").casefold()
            for item in document["entities"]
        }
        metadata = _source_metadata(document)
        doc_values.update(
            str(value).casefold()
            for value in (
                metadata.get("ticker"),
                metadata.get("security_id"),
                metadata.get("company_name"),
            )
            if value
        )
        doc_values.discard("")
        if wanted in doc_values:
            return True
        # Phase 18.1: anchor a ticker request to its issuer (security_master
        # canonical name) so dual-class tickers (GOOGL/GOOG) and issuer aliases
        # match documents filed under the issuer name.  Market filtering stays
        # strict in _identity_matches (18.0 decision 2); tokens shared by
        # multiple issuers never anchor (fail-closed).
        token_to_issuer, issuer_tokens = self._issuer_index()
        issuer = token_to_issuer.get(wanted)
        if not issuer:
            return False
        return bool(issuer_tokens.get(issuer, frozenset()) & doc_values)

    @staticmethod
    def _handle(
        document: dict[str, Any],
        *,
        metadata: dict[str, Any],
        fiscal_year: int | None,
        fiscal_period: str | None,
        form_type: str | None,
        language: str | None,
        provider: str | None,
        provider_document_id: str | None,
    ) -> SourceHandle | None:
        canonical = next(
            (
                item
                for item in document["locations"]
                if item["is_canonical"]
                and item["role"] == "original_primary"
                and item["location_status"] == "active"
                # WU-3.1: provider-rejected paths are never canonical, even
                # when the row is still marked active.
                and ".rejections" not in item["relative_path"].replace("\\", "/")
            ),
            None,
        )
        if canonical is None or not Path(canonical["absolute_path"]).is_file():
            return None
        try:
            manifest = json.loads(canonical["manifest_json"] or "{}")
        except json.JSONDecodeError:
            manifest = {}
        source_id = str(canonical["source_id"] or document["source_id"] or "")
        content_sha256 = str(
            manifest.get("content_sha256") or source_id.rsplit(":", 1)[-1]
        )
        url_value = metadata.get("source_url") or metadata.get("https_url")
        https_url = str(url_value).strip() if url_value else None
        if https_url and not https_url.startswith("https://"):
            https_url = None
        missing: list[str] = []
        if not https_url:
            missing.append("https_url")
        if not document["published_date"]:
            missing.append("published_date")
        if not source_id or len(content_sha256) != 64:
            missing.append("snapshot_sha256")
        retrieved_at = str(manifest.get("retrieved_at") or "")
        collector_name = str(manifest.get("collector_name") or "")
        collector_version = str(manifest.get("collector_version") or "")
        if not retrieved_at or not collector_name or not collector_version:
            missing.append("capture_trace")
        return SourceHandle(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            document_id=document["document_id"],
            source_id=source_id,
            entity_ids=tuple(
                sorted(item["entity_id"] for item in document["entities"])
            ),
            title=document["title"],
            source_type=document["source_type"],
            document_kind=document["document_kind"],
            published_date=document["published_date"],
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            form_type=form_type,
            language=language,
            provider=provider,
            provider_document_id=provider_document_id,
            https_url=https_url,
            canonical_location_id=canonical["location_id"],
            canonical_path=canonical["absolute_path"],
            content_sha256=content_sha256,
            snapshot_sha256=content_sha256,
            mime_type=str(manifest.get("mime_type") or "application/octet-stream"),
            byte_size=int(manifest.get("byte_size") or canonical["observed_size"] or 0),
            retrieved_at=retrieved_at,
            collector_name=collector_name,
            collector_version=collector_version,
            source_status=document["source_status"],
            duplicate_group_id=document["exact_duplicate_group_id"],
            exact_duplicate_location_count=document["exact_duplicate_location_count"],
            capture_ready=not missing,
            missing_capture_fields=tuple(missing),
        )

    @staticmethod
    def _result(
        request: SourceRequest,
        status: ResolutionStatus,
        reason: str,
        matches: tuple[SourceHandle, ...],
        debug_trace: tuple[str, ...] = (),
    ) -> ResolutionResult:
        return ResolutionResult(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            request_id=request.request_id,
            status=status,
            reason=reason,
            download_required=status is ResolutionStatus.MISSING,
            download_allowed=request.allow_download,
            matches=matches,
            debug_trace=debug_trace,
        )


__all__ = [
    "ResolutionResult",
    "ResolutionStatus",
    "SOURCE_RESOLVER_SCHEMA_VERSION",
    "SourceHandle",
    "SourceRequest",
    "SourceResolutionError",
    "SourceResolver",
]
