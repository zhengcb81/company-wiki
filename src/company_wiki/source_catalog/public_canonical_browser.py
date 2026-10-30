"""Public, pathless, read-only canonical issuer → document bridge.

G-CWP-CANONICAL-01 (Dashboard unified harness): the plain
``public_document_browser`` matches captured entity keys and never verifies
StockWiki proof.  This module is the issuer-scoped cabinet on top of the same
zero-write read model:

- the request names ONE StockWiki canonical entity (``ENT_…``), an explicit
  UTC ``as_of``, and optionally the selected listing; the StockWiki issuer
  proof is read through the frozen ``stockwiki.dashboard_issuer_proof/1``
  seam from the operator-configured public proof CLI — never from the
  request body, and never from name/ticker joins;
- the envelope is validated structurally (exact fields, query echo, active
  verified owner package, identity revision, ``receipt_sha256`` recomputed
  over the canonical envelope body); a caller-supplied hash is never
  authority;
- CWP-side issuer attribution reuses the existing verified source-facts read
  faces only (``get_verified_assertion`` plus the existing
  ``source_scope_qualification`` DEI verifier with a cache-only security
  master).  Only documents whose verified issuer key equals the
  StockWiki-proven issuer key are returned as ``items``, each with its
  complete SourceRef v2 and the same opaque ``document_version_id`` the
  plain browse and the owner reader use;
- supported namespace matrix (see docs/handoffs): StockWiki source bindings
  in the ``cwp_source_export_v2`` namespace resolve natively inside CWP by
  exact source URN; the proven CWP issuer namespace is ``sec.cik`` verified
  by the existing ``sec-primary-dei/1`` original-DEI evidence.  Any other
  StockWiki namespace is reported ``unknown`` — never converted by guess;
- binding states are honest: ``verified`` / ``ambiguous`` / ``unknown`` /
  ``conflict`` / ``stale`` / ``unavailable`` / ``incompatible``.  Without a
  verified binding no item is returned, ``total`` is ``unknown`` (never a
  fake exact zero), and pathless unverified diagnostic candidates are listed
  separately, never mixed into ``items``;
- pagination pins a ``proof_snapshot_id`` to the exact query, the StockWiki
  identity revision + receipt, the resolved issuer pin and the content
  addressed candidate revision; any change is ``stale`` and never silently
  mixes revisions;
- association scope is ``issuer_only``: a selected listing only proves the
  security belongs to the proven issuer; documents are never claimed to be
  partitioned by listing, and analysis subjects are unsupported unless a
  separate owner proof exists;
- read-only throughout: no download, refresh, OCR, parsing, registration or
  backfill, and no physical path, root or catalog layout detail is emitted.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from .assertion_service import get_verified_assertion, source_scope_qualification
from .public_document_browser import (
    PublicDocumentBrowser,
    document_version_id,
)
from .source_reader import SOURCE_REF_SCHEMA_VERSION, SourceRef
from .service import SourceCatalog


REQUEST_SCHEMA = "company-wiki-canonical-document-browse-request/1"
RESPONSE_SCHEMA = "company-wiki-canonical-document-browse/1"

#: Frozen StockWiki owner proof-read seam (contracts/stockwiki.dashboard_issuer_proof-1).
SW_ENVELOPE_SCHEMA_VERSION = "stockwiki.dashboard_issuer_proof/1"
SW_LIBRARY_REVISION = "not_provided_no_global_revision"

ASSOCIATION_SCOPE = "issuer_only"

#: StockWiki source-binding namespaces this bridge resolves natively in CWP.
#: ``cwp_source_export_v2`` records are CWP's own source URNs; anything else
#: needs a cross-owner namespace contract (D00/D01) before it may be used.
SUPPORTED_SOURCE_NAMESPACES = ("cwp_source_export_v2",)

#: CWP issuer namespace proven by the existing original-DEI verifier.
ISSUER_NAMESPACE_SEC_CIK = "sec.cik"
ISSUER_VERIFIER_SEC_DEI = "sec-primary-dei/1"

_SOURCE_URN_RE = re.compile(
    r"urn:company-wiki:source:sha256:[0-9a-f]{64}\Z")
_ENT_ID_RE = re.compile(
    r"ENT_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_LST_ID_RE = re.compile(
    r"LST_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_AS_OF_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)\Z")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
_REASON_RE = re.compile(r"[a-z0-9_]{1,100}\Z")

_MAX_LIMIT = 500
_DEFAULT_LIMIT = 50
_MAX_TOKEN_LENGTH = 8192
_MAX_ENVELOPE_BYTES = 1_048_576
_PROOF_DEADLINE_SECONDS = 60.0

#: Bounded verified-fact scan per query.  Beyond this the bridge refuses by
#: name instead of silently truncating the proven set.
_MAX_ASSERTION_SCAN = 20_000
_MAX_UNVERIFIED_CANDIDATES = 32

_REQUEST_FIELDS = frozenset({
    "schema_version", "canonical_entity_id", "listing_id",
    "analysis_subject_id", "as_of", "document_kinds", "fiscal_years",
    "language", "limit", "cursor", "proof_snapshot_id",
})
_FILTER_KEYS = ("document_kinds", "fiscal_years", "language")
_SNAPSHOT_VERSION = 1

_ENVELOPE_TOP_FIELDS = frozenset({
    "schema_version", "authority", "state", "reason_codes", "query",
    "selected_listing_id", "identity_revision", "library_revision",
    "owner_package", "receipt_sha256",
})
_ENVELOPE_STATES = frozenset({
    "available", "ambiguous", "not_found", "unverified", "unavailable",
    "incompatible",
})
_OWNER_PACKAGE_FIELDS = frozenset({
    "schema_version", "object_type", "payload", "trusted_context",
})
_TRUSTED_CONTEXT_FIELDS = frozenset({
    "market_registry", "identity_receipts", "source_bindings",
})

#: Frozen envelope state → binding status for negative proofs.
_ENVELOPE_STATE_TO_BINDING = {
    "ambiguous": "ambiguous",
    "not_found": "unknown",
    "unverified": "unknown",
    "unavailable": "unavailable",
    "incompatible": "incompatible",
}


class CanonicalBrowseError(RuntimeError):
    """A named, in-band refusal (invalid request)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ProofTransportError(RuntimeError):
    """The configured StockWiki proof CLI could not deliver a usable envelope."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _encode_token(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_token(token: Any, field: str) -> dict[str, Any]:
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token) \
            or len(token) > _MAX_TOKEN_LENGTH:
        raise CanonicalBrowseError(f"invalid_{field}")
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, UnicodeError, json.JSONDecodeError):
        raise CanonicalBrowseError(f"invalid_{field}") from None
    if not isinstance(payload, dict) or payload.get("v") != _SNAPSHOT_VERSION:
        raise CanonicalBrowseError(f"unsupported_{field}")
    return payload


def _required_text(value: Any, field: str, *, max_length: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() \
            or len(value) > max_length:
        raise CanonicalBrowseError(f"invalid_{field}")
    return value.strip()


def _optional_text_list(value: Any, field: str) -> tuple[str, ...] | None:
    if value is None or value == []:
        return None
    if not isinstance(value, list) or not value \
            or len(value) > 32 \
            or any(not isinstance(item, str) or not _TOKEN_RE.fullmatch(item)
                   or len(item) > 100 for item in value):
        raise CanonicalBrowseError(f"invalid_{field}")
    return tuple(sorted(dict.fromkeys(value)))


def _optional_int_list(value: Any, field: str) -> tuple[int, ...] | None:
    if value is None or value == []:
        return None
    if not isinstance(value, list) or not value \
            or len(value) > 200 \
            or any(isinstance(item, bool) or not isinstance(item, int)
                   or not 1900 <= item <= 2200 for item in value):
        raise CanonicalBrowseError(f"invalid_{field}")
    return tuple(sorted(dict.fromkeys(value)))


# --- frozen StockWiki proof-read seam ----------------------------------------


def _reject_constant(name: str) -> Any:
    raise ValueError(f"nonfinite JSON constant: {name}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_bounded_json(raw: bytes, *, max_bytes: int) -> Any:
    """Strict bounded JSON: UTF-8, duplicate keys, NaN/Inf and depth refused."""
    if len(raw) > max_bytes:
        raise ProofTransportError("stockwiki_proof_output_limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProofTransportError("stockwiki_proof_not_utf8") from exc
    try:
        return json.loads(
            text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant,
        )
    except RecursionError:
        raise ProofTransportError("stockwiki_proof_envelope_too_deep") from None
    except ValueError as exc:
        raise ProofTransportError("stockwiki_proof_envelope_not_json") from exc


def receipt_sha256(envelope: dict[str, Any]) -> str:
    """Recompute the frozen integrity receipt (canonical UTF-8, no receipt)."""
    body = {key: value for key, value in envelope.items()
            if key != "receipt_sha256"}
    try:
        canonical = json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ProofTransportError("stockwiki_proof_envelope_not_canonical") from exc
    return hashlib.sha256(canonical).hexdigest()


def validate_proof_envelope(raw: Any, *, entity_id: str, listing_id: str | None,
                            as_of: str) -> dict[str, Any]:
    """Structural validation of one frozen proof-read envelope.

    Schema fields, query echo, receipt recomputation and the available-state
    invariants are checked here; semantic owner-package checks stay in the
    browser.  Every refusal is named; no field is trusted on assertion.
    """
    if not isinstance(raw, dict) or set(raw) != _ENVELOPE_TOP_FIELDS:
        raise ProofTransportError("stockwiki_proof_envelope_fields_invalid")
    if raw["schema_version"] != SW_ENVELOPE_SCHEMA_VERSION:
        raise ProofTransportError("stockwiki_proof_envelope_version_unsupported")
    if raw["authority"] != "stockwiki" or raw["state"] not in _ENVELOPE_STATES:
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    reason_codes = raw["reason_codes"]
    if not isinstance(reason_codes, list) \
            or any(not isinstance(item, str) or not _REASON_RE.fullmatch(item)
                   for item in reason_codes) \
            or len(set(reason_codes)) != len(reason_codes):
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    query = raw["query"]
    if not isinstance(query, dict) or set(query) != {
            "entity_id", "listing_id", "as_of"}:
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    if query["entity_id"] != entity_id or query["as_of"] != as_of \
            or query["listing_id"] != listing_id:
        raise ProofTransportError("stockwiki_proof_query_echo_mismatch")
    if raw["library_revision"] != SW_LIBRARY_REVISION:
        raise ProofTransportError("stockwiki_proof_envelope_version_unsupported")
    selected = raw["selected_listing_id"]
    if selected is not None \
            and (not isinstance(selected, str)
                 or not _LST_ID_RE.fullmatch(selected)):
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    revision = raw["identity_revision"]
    if revision is not None and (isinstance(revision, bool)
                                 or not isinstance(revision, int) or revision < 1):
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    if not isinstance(raw["receipt_sha256"], str) \
            or not re.fullmatch(r"[0-9a-f]{64}", raw["receipt_sha256"]):
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    if receipt_sha256(raw) != raw["receipt_sha256"]:
        raise ProofTransportError("stockwiki_proof_receipt_mismatch")
    package = raw["owner_package"]
    if raw["state"] == "available":
        if not isinstance(selected, str) or not isinstance(revision, int):
            raise ProofTransportError("stockwiki_proof_envelope_invalid")
        if not isinstance(package, dict) \
                or set(package) != _OWNER_PACKAGE_FIELDS \
                or package["schema_version"] != "2.2.0" \
                or package["object_type"] != "entity" \
                or not isinstance(package["payload"], dict):
            raise ProofTransportError("stockwiki_proof_envelope_invalid")
        context = package["trusted_context"]
        if not isinstance(context, dict) \
                or set(context) != _TRUSTED_CONTEXT_FIELDS \
                or not all(isinstance(context[key], dict) for key in
                           _TRUSTED_CONTEXT_FIELDS):
            raise ProofTransportError("stockwiki_proof_envelope_invalid")
    elif package is not None:
        raise ProofTransportError("stockwiki_proof_envelope_invalid")
    return raw


class StockWikiProofClient:
    """Transport to the operator-configured public StockWiki proof CLI.

    Only the fixed ``read`` command is spoken; the workspace root is an
    operator argument and never appears in business JSON.  Output bounds,
    deadline and strict parsing mirror the frozen seam.  A nonzero exit with
    a well-formed envelope on stderr is the seam's named negative; a bodyless
    failure is a transport fault.
    """

    def __init__(self, *, python_executable: str, cli_path: str,
                 workspace_root: str,
                 deadline_seconds: float = _PROOF_DEADLINE_SECONDS):
        import os
        if not (isinstance(python_executable, str) and python_executable
                and os.path.isfile(python_executable)):
            raise ProofTransportError("stockwiki_proof_not_configured")
        if not (isinstance(cli_path, str) and cli_path
                and os.path.isfile(cli_path)):
            raise ProofTransportError("stockwiki_proof_not_configured")
        if not (isinstance(workspace_root, str) and workspace_root
                and os.path.isdir(workspace_root)):
            raise ProofTransportError("stockwiki_proof_not_configured")
        self.command = [python_executable, "-B", cli_path,
                        "read", "--root", workspace_root]
        self.deadline_seconds = deadline_seconds

    def read(self, *, entity_id: str, listing_id: str | None,
             as_of: str) -> dict[str, Any]:
        request = json.dumps(
            {"entity_id": entity_id, "listing_id": listing_id, "as_of": as_of},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        try:
            completed = subprocess.run(
                self.command, input=request, capture_output=True,
                timeout=self.deadline_seconds,
            )
        except subprocess.TimeoutExpired:
            raise ProofTransportError("stockwiki_proof_deadline") from None
        except OSError:
            raise ProofTransportError("stockwiki_proof_cli_unavailable") from None
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            if stderr.startswith(b"{"):
                try:
                    envelope = parse_bounded_json(
                        stderr, max_bytes=_MAX_ENVELOPE_BYTES)
                except ProofTransportError:
                    raise ProofTransportError(
                        "stockwiki_proof_cli_failed") from None
                return validate_proof_envelope(
                    envelope, entity_id=entity_id, listing_id=listing_id,
                    as_of=as_of,
                )
            raise ProofTransportError("stockwiki_proof_cli_failed")
        envelope = parse_bounded_json(completed.stdout,
                                      max_bytes=_MAX_ENVELOPE_BYTES)
        return validate_proof_envelope(
            envelope, entity_id=entity_id, listing_id=listing_id, as_of=as_of,
        )


# --- issuer binding -----------------------------------------------------------


@dataclass(frozen=True)
class IssuerKey:
    """One exact issuer key in a supported namespace."""

    namespace: str
    value: str

    def qualified(self) -> str:
        return self.namespace + ":" + self.value


@dataclass(frozen=True)
class ResolvedIssuer:
    key: IssuerKey
    verifier: str
    assertion_id: str
    source_id: str
    content_sha256: str

    def pin(self) -> dict[str, Any]:
        return {
            "namespace": self.key.namespace, "value": self.key.value,
            "verifier": self.verifier, "assertion_id": self.assertion_id,
            "source_id": self.source_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class Binding:
    """The cross-owner issuer binding result for one query."""

    status: str
    reason_codes: list[str]
    issuer_pin: dict[str, Any] | None = None
    stockwiki: dict[str, Any] | None = None
    resolved_source: dict[str, Any] | None = None

    def with_reasons(self, *codes: str) -> "Binding":
        return Binding(
            status=self.status,
            reason_codes=list(dict.fromkeys([*self.reason_codes, *codes])),
            issuer_pin=self.issuer_pin, stockwiki=self.stockwiki,
            resolved_source=self.resolved_source,
        )


def _reasons(*codes: str) -> list[str]:
    return list(dict.fromkeys(codes))


class _Snapshot:
    """The pinned proof identity: query, proof pins and candidate revision."""

    def __init__(self, entity: str, listing: str | None, as_of: str,
                 filters: dict[str, Any], stockwiki: dict[str, Any] | None,
                 issuer_pin: dict[str, Any] | None, revision: str,
                 token_text: str | None = None):
        self.entity = entity
        self.listing = listing
        self.as_of = as_of
        self.filters = filters
        self.stockwiki = stockwiki
        self.issuer_pin = issuer_pin
        self.revision = revision
        self._token_text = token_text

    def pin_payload(self) -> dict[str, Any]:
        return {
            "v": _SNAPSHOT_VERSION,
            "query": {"entity": self.entity, "listing": self.listing,
                      "as_of": self.as_of},
            "filters": {key: (list(value) if value else None)
                        for key, value in self.filters.items()},
            "stockwiki": {
                "identity_revision": (self.stockwiki or {}).get(
                    "identity_revision"),
                "receipt_sha256": (self.stockwiki or {}).get("receipt_sha256"),
            },
            "issuer": self.issuer_pin,
            "revision": self.revision,
        }

    def token(self) -> str:
        if self._token_text is None:
            self._token_text = _encode_token(self.pin_payload())
        return self._token_text


class PublicCanonicalBrowser:
    """Zero-write canonical issuer browse over the local source catalog."""

    def __init__(self, catalog: SourceCatalog,
                 proof_client: StockWikiProofClient | None = None):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        if proof_client is not None \
                and not isinstance(proof_client, StockWikiProofClient):
            raise TypeError("proof_client must be StockWikiProofClient")
        self.catalog = catalog
        self.proof_client = proof_client

    # -- public entry point ---------------------------------------------------

    def browse(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict) or set(request) != _REQUEST_FIELDS:
            raise CanonicalBrowseError("request_fields_not_exact")
        if request["schema_version"] != REQUEST_SCHEMA:
            raise CanonicalBrowseError("unsupported_request_version")
        entity = _required_text(request["canonical_entity_id"],
                                "canonical_entity_id")
        if not _ENT_ID_RE.fullmatch(entity):
            raise CanonicalBrowseError("invalid_canonical_entity_id")
        listing = request["listing_id"]
        if listing is not None:
            listing = _required_text(listing, "listing_id")
            if not _LST_ID_RE.fullmatch(listing):
                raise CanonicalBrowseError("invalid_listing_id")
        if request["analysis_subject_id"] is not None:
            _required_text(request["analysis_subject_id"],
                           "analysis_subject_id", max_length=200)
            return self._unsupported_subject(entity, listing)
        as_of = _required_text(request["as_of"], "as_of", max_length=40)
        if not _AS_OF_RE.fullmatch(as_of):
            raise CanonicalBrowseError("invalid_as_of")
        limit = request["limit"]
        if limit is None:
            limit = _DEFAULT_LIMIT
        elif isinstance(limit, bool) or not isinstance(limit, int) \
                or not 1 <= limit <= _MAX_LIMIT:
            raise CanonicalBrowseError("invalid_limit")
        filters = {
            "document_kinds": _optional_text_list(
                request["document_kinds"], "document_kinds"),
            "fiscal_years": _optional_int_list(
                request["fiscal_years"], "fiscal_years"),
            "language": _optional_text_list(request["language"], "language"),
        }
        cursor_token = _optional_token(request["cursor"], "cursor")
        snapshot_token = _optional_token(request["proof_snapshot_id"],
                                         "proof_snapshot_id")

        binding = self._resolve_binding(entity, listing, as_of)
        if binding.status != "verified":
            return self._envelope(
                state="empty", reason_codes=binding.reason_codes,
                entity=entity, listing=listing, as_of=as_of, binding=binding,
                items=(), snapshot=None, next_cursor=None, total=None,
                candidates=[], catalog_revision=None,
            )

        versions = self._proven_versions(binding)
        if self._conflicted_documents:
            binding = binding.with_reasons("document_issuer_conflict")
        revision = self._revision(versions, binding)
        snapshot = _Snapshot(entity, listing, as_of, filters,
                             binding.stockwiki, binding.issuer_pin, revision)

        pinned = self._pinned_snapshot(entity, listing, as_of, filters,
                                       cursor_token, snapshot_token)
        if pinned is not None \
                and pinned.pin_payload() != snapshot.pin_payload():
            fresh = _Snapshot(entity, pinned.listing, pinned.as_of,
                              pinned.filters, binding.stockwiki,
                              binding.issuer_pin, revision)
            return self._envelope(
                state="stale",
                reason_codes=_reasons("proof_snapshot_stale"),
                entity=entity, listing=listing, as_of=as_of, binding=binding,
                items=(), snapshot=fresh, next_cursor=None, total=None,
                candidates=[], catalog_revision=revision,
            )

        if pinned is not None:
            snapshot = pinned
        offset = 0
        if cursor_token is not None:
            cursor_payload = _decode_token(cursor_token, "cursor")
            if cursor_payload.get("snapshot") != snapshot.token():
                raise CanonicalBrowseError("cursor_snapshot_mismatch")
            next_offset = cursor_payload.get("offset")
            if isinstance(next_offset, bool) or not isinstance(next_offset, int) \
                    or next_offset < 0:
                raise CanonicalBrowseError("invalid_cursor")
            offset = next_offset

        return self._serve(entity, versions, snapshot, offset, limit, binding)

    # -- binding ----------------------------------------------------------------

    def _unsupported_subject(self, entity: str, listing: str | None) -> dict:
        binding = Binding(
            status="unavailable",
            reason_codes=_reasons("analysis_subject_unsupported"),
        )
        return self._envelope(
            state="unsupported",
            reason_codes=_reasons("analysis_subject_unsupported"),
            entity=entity, listing=listing, as_of=None, binding=binding,
            items=(), snapshot=None, next_cursor=None, total=None,
            candidates=[], catalog_revision=None,
        )

    def _resolve_binding(self, entity: str, listing: str | None,
                         as_of: str) -> Binding:
        """One cross-owner issuer resolution: StockWiki proof, then CWP facts."""
        if self.proof_client is None:
            return Binding(
                status="unavailable",
                reason_codes=_reasons("stockwiki_proof_not_configured"),
            )
        try:
            envelope = self.proof_client.read(
                entity_id=entity, listing_id=listing, as_of=as_of)
        except ProofTransportError as exc:
            return Binding(status="unavailable",
                           reason_codes=_reasons(exc.reason))
        sw_view = {
            "entity_id": entity,
            "selected_listing_id": envelope["selected_listing_id"],
            "identity_revision": envelope["identity_revision"],
            "receipt_sha256": envelope["receipt_sha256"],
            "envelope_state": envelope["state"],
            "library_revision": envelope["library_revision"],
        }
        if envelope["state"] != "available":
            return Binding(
                status=_ENVELOPE_STATE_TO_BINDING[envelope["state"]],
                reason_codes=_reasons("stockwiki_proof_not_available",
                                      *envelope["reason_codes"]),
                stockwiki=sw_view,
            )
        package = envelope["owner_package"]
        payload = package["payload"]
        context = package["trusted_context"]
        if payload.get("entity_id") != entity:
            return Binding(status="incompatible",
                           reason_codes=_reasons("envelope_entity_mismatch"),
                           stockwiki=sw_view)
        if payload.get("identity_revision") != envelope["identity_revision"]:
            return Binding(status="incompatible",
                           reason_codes=_reasons("envelope_revision_mismatch"),
                           stockwiki=sw_view)
        receipts = context["identity_receipts"]
        if not receipts or not any(
                isinstance(receipt, dict)
                and receipt.get("kind") == "verified_issuer"
                for receipt in receipts.values()):
            return Binding(status="incompatible",
                           reason_codes=_reasons("verified_receipt_missing"),
                           stockwiki=sw_view)
        for receipt_id, receipt in receipts.items():
            if not isinstance(receipt, dict) \
                    or receipt.get("receipt_id") != receipt_id \
                    or receipt.get("entity_id") != entity \
                    or receipt.get("identity_revision") \
                    != envelope["identity_revision"] \
                    or receipt.get("effective_status") != "active":
                return Binding(status="incompatible",
                               reason_codes=_reasons("receipt_not_active"),
                               stockwiki=sw_view)
        listings = payload.get("listings")
        if not isinstance(listings, list) or not listings:
            return Binding(status="incompatible",
                           reason_codes=_reasons("envelope_listings_invalid"),
                           stockwiki=sw_view)
        selected = next((item for item in listings
                         if isinstance(item, dict)
                         and item.get("listing_id")
                         == envelope["selected_listing_id"]), None)
        if selected is None:
            return Binding(status="incompatible",
                           reason_codes=_reasons("selected_listing_unknown"),
                           stockwiki=sw_view)
        if selected.get("listing_status") != "active":
            return Binding(status="conflict",
                           reason_codes=_reasons("selected_listing_not_active"),
                           stockwiki=sw_view)
        binding_ref = selected.get("source_binding_ref")
        binding_row = context["source_bindings"].get(binding_ref)
        if not isinstance(binding_row, dict):
            return Binding(status="incompatible",
                           reason_codes=_reasons("selected_binding_missing"),
                           stockwiki=sw_view)
        if (binding_row.get("listing_id") != selected.get("listing_id")
                or binding_row.get("security_id") != selected.get("security_id")
                or binding_row.get("market") != selected.get("market")
                or binding_row.get("entity_id") != entity
                or binding_row.get("status") != "active"):
            return Binding(status="incompatible",
                           reason_codes=_reasons("selected_binding_mismatch"),
                           stockwiki=sw_view)
        sw_view["selected_security_id"] = selected.get("security_id")
        sw_view["selected_market"] = selected.get("market")
        if binding_row.get("source_namespace") not in SUPPORTED_SOURCE_NAMESPACES:
            return Binding(
                status="unknown",
                reason_codes=_reasons(
                    "unsupported_source_namespace",
                    "stockwiki_proof_verified_but_unresolvable"),
                stockwiki=sw_view,
            )
        record = binding_row.get("source_record_id")
        if not isinstance(record, str) or not _SOURCE_URN_RE.fullmatch(record):
            return Binding(
                status="unknown",
                reason_codes=_reasons("unsupported_source_record_urn"),
                stockwiki=sw_view,
            )
        resolution = self._resolve_source_facts(record)
        if isinstance(resolution, Binding):
            return Binding(
                status=resolution.status,
                reason_codes=resolution.reason_codes,
                stockwiki=sw_view,
                resolved_source=resolution.resolved_source,
            )
        issuer, cwp_pin = resolution
        return Binding(
            status="verified",
            reason_codes=_reasons("same_issuer_proven"),
            issuer_pin=issuer.pin(),
            stockwiki=sw_view,
            resolved_source=cwp_pin,
        )

    def _resolve_source_facts(self, source_id: str) -> tuple[ResolvedIssuer, dict] \
            | Binding:
        """Resolve one CWP source URN to its proven issuer key.

        Only the existing verified-facts read faces are used: the active
        verified assertion (hash bound) and the existing original-DEI scope
        verifier with a cache-only security master.  No original bytes are
        read; incomplete proofs stay unknown by name.
        """
        from .source_reader import SourceReadError, SourceVersionReader

        row = self.catalog.reader.fetchone(
            "SELECT content_sha256, byte_size, mime_type FROM sources "
            "WHERE source_id = ?", (source_id,))
        if row is None:
            return Binding(status="unknown",
                           reason_codes=_reasons("resolved_source_not_indexed"))
        content_sha256 = str(row["content_sha256"])
        # Runtime face parity: assertion_service itself passes the catalog
        # reader here (same fetchall/Row contract); the annotation names the
        # writer-side store, so the reader goes through the local Any pin.
        reader_store: Any = self.catalog.reader
        assertion = get_verified_assertion(
            reader_store, source_id, content_sha256, reader="steady")
        if assertion is None:
            return Binding(
                status="unknown",
                reason_codes=_reasons("resolved_source_unverified_facts"),
                resolved_source={"source_id": source_id,
                                 "content_sha256": content_sha256},
            )
        document_id = str(assertion["document_id"])
        cwp_pin = {
            "source_id": source_id, "content_sha256": content_sha256,
            "assertion_id": str(assertion["assertion_id"]),
        }
        ref = SourceRef(
            document_id=document_id, source_id=source_id,
            content_sha256=content_sha256, byte_size=int(row["byte_size"]),
            mime_type=str(row["mime_type"]),
            schema_version=SOURCE_REF_SCHEMA_VERSION,
        )
        try:
            manifest = SourceVersionReader(self.catalog).describe_version(ref)
            qualification = source_scope_qualification(
                self.catalog, ref, metadata=manifest,
                identity_cache_dir=self.catalog.config.catalog_dir
                / "security_master")
        except SourceReadError as exc:
            status = "conflict" if exc.reason == "primary_issuer_conflict" \
                else "unknown"
            return Binding(
                status=status,
                reason_codes=_reasons(f"source_facts_{exc.status}", exc.reason),
                resolved_source=cwp_pin,
            )
        if qualification is None:
            return Binding(
                status="unknown",
                reason_codes=_reasons("issuer_namespace_unsupported_for_document"),
                resolved_source=cwp_pin,
            )
        if qualification.needs_original:
            return Binding(
                status="unknown",
                reason_codes=_reasons("issuer_proof_requires_original_read"),
                resolved_source=cwp_pin,
            )
        cik = qualification.identity.identifiers.get("cik")
        if not isinstance(cik, str) or not cik.isdigit():
            return Binding(status="unknown",
                           reason_codes=_reasons("issuer_key_unresolved"),
                           resolved_source=cwp_pin)
        issuer = ResolvedIssuer(
            key=IssuerKey(ISSUER_NAMESPACE_SEC_CIK, str(int(cik))),
            verifier=ISSUER_VERIFIER_SEC_DEI,
            assertion_id=str(assertion["assertion_id"]),
            source_id=source_id, content_sha256=content_sha256,
        )
        return issuer, cwp_pin

    # -- proven document set ------------------------------------------------------

    def _verified_assertions(self) -> list[dict[str, Any]]:
        """Active verified source-facts assertions, bounded, newest per source."""
        rows = self.catalog.reader.fetchall(
            """SELECT assertion_id, source_id, document_id, content_sha256,
                      evidence_basis, evidence_json, created_at,
                      supersedes_assertion_id
               FROM source_metadata_assertions
               WHERE decision='verified'
                 AND visibility_state IN ('legacy','active')
               ORDER BY created_at, assertion_id""",
            (),
        )
        if len(rows) > _MAX_ASSERTION_SCAN:
            from .source_reader import SourceReadError
            raise SourceReadError("unavailable", "issuer_scan_budget_exceeded")
        superseded = {
            str(row["supersedes_assertion_id"]) for row in rows
            if row["supersedes_assertion_id"] is not None
        }
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            if str(row["evidence_basis"]) != "source-facts" \
                    or str(row["assertion_id"]) in superseded:
                continue
            latest[str(row["source_id"])] = dict(row)
        return list(latest.values())

    def _issuer_for_source(self, source_id: str,
                           memo: dict[str, Any]) -> ResolvedIssuer | None:
        if source_id in memo:
            return memo[source_id]
        # Fail closed per source: one unreadable fact row must not sink the
        # whole bounded scan; the conservative outcome is "not proven".
        try:
            resolution = self._resolve_source_facts(source_id)
        except Exception:
            resolution = None
        issuer = resolution[0] if isinstance(resolution, tuple) else None
        memo[source_id] = issuer
        return issuer

    def _proven_versions(self, binding: Binding) -> list[Any]:
        """All document versions of documents proven to the bound issuer."""
        assert binding.issuer_pin is not None  # verified binding precondition
        self._conflicted_documents = []
        wanted = IssuerKey(ISSUER_NAMESPACE_SEC_CIK,
                           str(binding.issuer_pin["value"])).qualified()
        memo: dict[str, Any] = {}
        by_document: dict[str, set[str]] = {}
        for assertion in self._verified_assertions():
            issuer = self._issuer_for_source(str(assertion["source_id"]), memo)
            if issuer is None:
                continue
            by_document.setdefault(str(assertion["document_id"]),
                                   set()).add(issuer.key.qualified())
        versions: list[Any] = []
        for document_id, keys in sorted(by_document.items()):
            if wanted not in keys:
                continue
            if len(keys) > 1:
                # One document whose own sources prove conflicting issuers is
                # never served; it stays out of items and is named in reasons.
                self._conflicted_documents.append(document_id)
                continue
            document = self._fallback_browser()._document(document_id)
            if document is None:
                continue
            versions.extend(self._fallback_browser()._document_versions(document))
        versions.sort(key=lambda row: row.sort_key())
        return versions

    def _fallback_browser(self) -> PublicDocumentBrowser:
        # Shares the plain browse's exact document/version enumeration,
        # filtering, facets and revision semantics (read-only reuse).
        if not hasattr(self, "_browser"):
            self._browser = PublicDocumentBrowser(self.catalog)
        return self._browser

    def _unverified_candidates(self, versions: list[Any],
                               binding: Binding) -> list[dict[str, Any]]:
        """Pathless diagnostics: same CWP entity keys, unproven or differing."""
        if binding.issuer_pin is None or not versions:
            return []
        browser = self._fallback_browser()
        item_documents = {version.document_id for version in versions}
        entity_keys: set[str] = set()
        for document_id in sorted(item_documents):
            for row in self.catalog.reader.fetchall(
                    "SELECT entity_id FROM document_entities "
                    "WHERE document_id = ?", (document_id,)):
                entity_keys.add(str(row["entity_id"]))
            document = browser._document(document_id)
            if document is not None and document["canonical_entity_id"]:
                entity_keys.add(document["canonical_entity_id"])
        wanted = IssuerKey(ISSUER_NAMESPACE_SEC_CIK,
                           str(binding.issuer_pin["value"])).qualified()
        memo: dict[str, Any] = {}
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for entity in sorted(entity_keys):
            for document in browser._entity_documents(entity):
                if document["document_id"] in item_documents \
                        or document["document_id"] in seen:
                    continue
                seen.add(document["document_id"])
                for version in browser._document_versions(document):
                    issuer = self._issuer_for_source(version.source_id, memo)
                    if issuer is None:
                        reason = "issuer_proof_missing"
                    elif issuer.key.qualified() == wanted:
                        reason = "superseded_version"
                    else:
                        reason = "issuer_differs"
                    candidates.append({
                        "document_version_id": document_version_id(
                            version.document_id, version.source_id,
                            version.content_sha256),
                        "document_id": version.document_id,
                        "title": version.title,
                        "document_kind": version.document_kind,
                        "reason_code": reason,
                    })
        candidates.sort(key=lambda item: (
            item["reason_code"], item["document_id"],
            item["document_version_id"]))
        return candidates[:_MAX_UNVERIFIED_CANDIDATES]

    # -- snapshot / paging --------------------------------------------------------

    @staticmethod
    def _revision(versions: list[Any], binding: Binding) -> str:
        payload = json.dumps(
            {
                "issuer": binding.issuer_pin,
                "rows": [version.revision_member() for version in versions],
            },
            ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _pinned_snapshot(self, entity: str, listing: str | None, as_of: str,
                         filters: dict[str, Any], cursor_token: str | None,
                         snapshot_token: str | None) -> _Snapshot | None:
        """Rebuild the pinned snapshot from a cursor or explicit snapshot."""
        pinned_payload: dict[str, Any] | None = None
        if snapshot_token is not None:
            pinned_payload = _decode_token(snapshot_token, "proof_snapshot_id")
        if cursor_token is not None:
            cursor_payload = _decode_token(cursor_token, "cursor")
            embedded = cursor_payload.get("snapshot")
            if not isinstance(embedded, str):
                raise CanonicalBrowseError("invalid_cursor")
            cursor_snapshot = _decode_token(embedded, "proof_snapshot_id")
            if pinned_payload is None:
                pinned_payload = cursor_snapshot
            elif _encode_token(pinned_payload) != embedded:
                raise CanonicalBrowseError("cursor_snapshot_mismatch")
        if pinned_payload is None:
            return None
        query = pinned_payload.get("query")
        if not isinstance(query, dict) or query.get("entity") != entity:
            raise CanonicalBrowseError("snapshot_entity_mismatch")
        if query.get("listing") != listing or query.get("as_of") != as_of:
            raise CanonicalBrowseError("snapshot_query_mismatch")
        pinned_filters = pinned_payload.get("filters")
        if not isinstance(pinned_filters, dict) \
                or set(pinned_filters) != set(_FILTER_KEYS):
            raise CanonicalBrowseError("invalid_proof_snapshot_id")
        for key in _FILTER_KEYS:
            requested = filters.get(key)
            pinned = pinned_filters.get(key)
            if requested is not None and requested != [] \
                    and (pinned is None or pinned == []
                         or list(requested) != list(pinned)):
                raise CanonicalBrowseError("snapshot_filter_conflict")
        revision = pinned_payload.get("revision")
        if not isinstance(revision, str) or not _TOKEN_RE.fullmatch(revision):
            raise CanonicalBrowseError("invalid_proof_snapshot_id")
        stockwiki = pinned_payload.get("stockwiki")
        return _Snapshot(
            entity, listing, as_of, pinned_filters,
            stockwiki if isinstance(stockwiki, dict) else None,
            pinned_payload.get("issuer"), revision,
            token_text=_encode_token(pinned_payload),
        )

    def _serve(self, entity: str, versions: list[Any], snapshot: _Snapshot,
               offset: int, limit: int, binding: Binding) -> dict[str, Any]:
        filtered = [
            version for version in versions
            if self._matches(snapshot.filters, version)
        ]
        total = len(filtered)
        page_items = filtered[offset:offset + limit]
        next_cursor = None
        if offset + limit < total:
            next_cursor = _encode_token({
                "v": _SNAPSHOT_VERSION, "snapshot": snapshot.token(),
                "offset": offset + limit,
            })
        state = "available" if total else "empty"
        reason_codes: list[str] = []
        if not versions:
            reason_codes.append("no_documents_proven_same_issuer")
        elif not total:
            reason_codes.append("no_documents_match_filters")
        elif offset >= total:
            # A cursor past the end of the pinned snapshot (forged, or the
            # snapshot shrank behind the stale check) is an honestly empty
            # page, never zero proven items.
            state = "empty"
            reason_codes.append("page_offset_beyond_total")
        if any(not version.resolvable for version in page_items):
            state = "partial"
            reason_codes.append("some_versions_not_resolvable")
        return self._envelope(
            state=state, reason_codes=reason_codes, entity=entity,
            listing=snapshot.listing, as_of=snapshot.as_of, binding=binding,
            items=page_items, snapshot=snapshot, next_cursor=next_cursor,
            total=total,
            candidates=self._unverified_candidates(versions, binding),
            catalog_revision=snapshot.revision,
        )

    @staticmethod
    def _matches(filters: dict[str, Any], version: Any) -> bool:
        if filters.get("document_kinds") is not None \
                and version.document_kind not in filters["document_kinds"]:
            return False
        if filters.get("fiscal_years") is not None \
                and version.fiscal_year not in filters["fiscal_years"]:
            return False
        if filters.get("language") is not None \
                and version.language not in filters["language"]:
            return False
        return True

    # -- response -----------------------------------------------------------------

    def _envelope(self, *, state: str, reason_codes: list[str], entity: str,
                  listing: str | None, as_of: str | None, binding: Binding,
                  items: tuple[Any, ...] | list[Any],
                  snapshot: _Snapshot | None, next_cursor: str | None,
                  total: int | None, candidates: list[dict[str, Any]],
                  catalog_revision: str | None) -> dict[str, Any]:
        verified = binding.status == "verified"
        page: dict[str, Any] = {
            "next_cursor": next_cursor if verified else None,
            "proof_snapshot_id": snapshot.token() if snapshot is not None
            else None,
            "total": total if verified and total is not None else None,
            "total_status": "exact" if verified and total is not None
            else "unknown",
        }
        return {
            "schema_version": RESPONSE_SCHEMA,
            "state": state,
            "reason_codes": reason_codes,
            "canonical_context": {
                "requested": {
                    "canonical_entity_id": entity,
                    "listing_id": listing,
                    "as_of": as_of,
                },
            },
            "binding": {
                "status": binding.status,
                "reason_codes": binding.reason_codes,
                "association_scope": ASSOCIATION_SCOPE,
                "issuer": binding.issuer_pin,
                "stockwiki": binding.stockwiki,
                "cwp_resolved_source": binding.resolved_source,
            },
            "items": [version.to_item() for version in items] if verified
            else [],
            "unverified_candidates": list(candidates) if verified else [],
            "page": page,
            "catalog_revision": catalog_revision,
        }


def _optional_token(value: Any, field: str) -> str | None:
    if value is None:
        return None
    token = _required_text(value, field, max_length=_MAX_TOKEN_LENGTH)
    if not _TOKEN_RE.fullmatch(token):
        raise CanonicalBrowseError(f"invalid_{field}")
    return token
