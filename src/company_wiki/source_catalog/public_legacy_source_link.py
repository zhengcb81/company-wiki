"""Resolve an owner-registered legacy path key to a currently verified version.

The path-derived key is only a location hint. It does not attest which bytes an
old research run used. No unregistered path is opened, and all reads use the
existing exact-version reader and its current root/admission policy.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re
import time
from typing import Any

from .public_document_browser import document_version_id
from .service import SourceCatalog
from .source_location import relative_segments
from .source_reader import SourceReadError, SourceRef, SourceVersionReader

REQUEST_SCHEMA = "company-wiki-legacy-source-link-request/1"
RESPONSE_SCHEMA = "company-wiki-legacy-source-link/1"
_FIELDS = frozenset(
    {"schema_version", "legacy_source_id", "expected_byte_size", "evidence"}
)
_KEY = re.compile(r"src_[0-9a-f]{16}\Z")
_MAX_LOCATIONS = 100_000
_MAX_SECONDS = 15.0
_ROLES = ("original_primary", "original_attachment", "indexed_only")


class LegacyLinkError(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def legacy_source_key(resolved_path: str) -> str:
    """The existing StockWiki stable_source_id algorithm; not a byte digest."""
    return "src_" + hashlib.sha1(resolved_path.encode("utf-8")).hexdigest()[:16]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _result(key: str, state: str, reason: str, **payload: Any) -> dict[str, Any]:
    value = {
        "schema_version": RESPONSE_SCHEMA,
        "state": state,
        "reason_codes": [reason],
        "legacy_source_id": key,
        "historical_version_status": "legacy_source_version_unpinned",
        "source_ref": None,
        "document_version_id": None,
        "current_byte_verification": None,
        **payload,
    }
    value["receipt_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def retirement_diagnostics(catalog: SourceCatalog, ref: SourceRef) -> dict[str, Any]:
    """Read the existing bounded recovery gate; never restore or read inactive bytes."""
    from .assertion_service import get_verified_assertion
    from .local_inventory import metadata_retirement, observe_document

    observation = observe_document(catalog, ref.document_id)
    reader_store: Any = catalog.reader
    known = {
        (
            "legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)",
            "phase-15.6-governance",
        ): "legacy_source_url_metadata_missing",
        (
            "phase-15.6 audit reconciliation (reconcile-retire)",
            "reconcile-retire-20260806",
        ): "legacy_retirement_audit_reconciled",
        (
            "source_metadata_insufficient",
            "automated-source-metadata",
        ): "source_metadata_insufficient",
    }
    return {
        "metadata_only_recovery_eligible": metadata_retirement(observation),
        "retire_audit": [
            {
                "audit_id": str(item["audit_id"]),
                "reason_code": known.get(
                    (item["reason"], item["created_by"]), "other_retirement"
                ),
            }
            for item in observation["retire_audit"]
        ],
        "retirement_observation_sha256": hashlib.sha256(
            _canonical(observation)
        ).hexdigest(),
        "active_verified_source_facts": get_verified_assertion(
            reader_store, ref.source_id, ref.content_sha256, reader="steady"
        )
        is not None,
        "recovery_interface": "company_wiki.source_catalog.local_prepare_cli",
    }


def resolve_legacy_source(
    catalog: SourceCatalog, request: dict[str, Any]
) -> dict[str, Any]:
    if (
        not isinstance(request, dict)
        or not {"schema_version", "legacy_source_id"} <= set(request)
        or set(request) - _FIELDS
    ):
        raise LegacyLinkError("request_fields_invalid")
    if request["schema_version"] != REQUEST_SCHEMA:
        raise LegacyLinkError("request_schema_unsupported")
    key = request["legacy_source_id"]
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise LegacyLinkError("legacy_source_id_invalid")
    size = request.get("expected_byte_size")
    if size is not None and (type(size) is not int or size < 0 or size > 2**53 - 1):
        raise LegacyLinkError("expected_byte_size_invalid")
    evidence = request.get("evidence")
    if evidence is not None:
        if (
            not isinstance(evidence, dict)
            or set(evidence) - {"quote", "legacy_page", "legacy_page_kind"}
            or not isinstance(evidence.get("quote"), str)
            or len("".join(evidence["quote"].split())) < 12
            or len(evidence["quote"]) > 4096
            or evidence.get("legacy_page_kind")
            not in {None, "unknown", "physical", "printed"}
            or (
                evidence.get("legacy_page") is not None
                and (
                    not isinstance(evidence["legacy_page"], str)
                    or len(evidence["legacy_page"]) > 30
                )
            )
        ):
            raise LegacyLinkError("evidence_invalid")
    started = time.monotonic()
    rows = catalog.reader.fetchall(
        """SELECT l.document_id, l.source_id, l.root_id, l.relative_path,
                  l.absolute_path, l.location_status, s.content_sha256,
                  s.byte_size, s.mime_type
           FROM locations l JOIN sources s ON s.source_id=l.source_id
           WHERE l.role IN ('original_primary','original_attachment','indexed_only')
           ORDER BY l.location_id LIMIT ?""",
        (_MAX_LOCATIONS + 1,),
    )
    if len(rows) > _MAX_LOCATIONS:
        return _result(key, "unavailable", "registered_location_budget_exceeded")
    roots = {root.root_id: root for root in catalog.config.roots}
    matches: dict[tuple[str, str, str], SourceRef] = {}
    for row in rows:
        if time.monotonic() - started > _MAX_SECONDS:
            return _result(key, "unavailable", "registered_location_deadline")
        # Historical absolute_path is compared lexically as a key only. It is
        # never resolved or opened and cannot grant access to any file.
        aliases = {str(row["absolute_path"] or "")}
        root = roots.get(str(row["root_id"]))
        if root is not None and row["location_status"] == "active":
            segments = relative_segments(str(row["relative_path"]))
            if segments is not None:
                # This is a lexical lookup key, not a file open. The exact
                # version reader below applies realpath/root/symlink policy.
                aliases.add(str(root.path.joinpath(*segments)))
        if not any(value and legacy_source_key(value) == key for value in aliases):
            continue
        ref = SourceRef(
            document_id=str(row["document_id"]),
            source_id=str(row["source_id"]),
            content_sha256=str(row["content_sha256"]),
            byte_size=int(row["byte_size"]),
            mime_type=str(row["mime_type"]),
            schema_version="2.0",
        )
        matches[(ref.document_id, ref.source_id, ref.content_sha256)] = ref
    if not matches:
        return _result(key, "not_found", "legacy_source_not_registered")
    if len(matches) != 1:
        return _result(key, "ambiguous", "legacy_source_multiple_versions")
    ref = next(iter(matches.values()))
    if size is not None and ref.byte_size != size:
        return _result(key, "conflict", "legacy_source_size_changed")
    try:
        receipt = SourceVersionReader(catalog).verify_version(
            ref, purpose="source_export"
        )
    except SourceReadError as exc:
        document = catalog.reader.document(ref.document_id)
        return _result(
            key,
            "unavailable",
            exc.reason,
            candidate_source_ref=asdict(ref),
            candidate_source_status=str(document["source_status"])
            if document
            else None,
            retirement_diagnostics=retirement_diagnostics(catalog, ref)
            if document and document["source_status"] == "retired"
            else None,
        )
    extra = {}
    if ref.mime_type == "application/pdf":
        from .cn_primary_issuer import (
            PrimaryIssuerUnavailable,
            extract_cn_issuer,
            pdf_text_pages,
            validate_quote,
        )

        try:
            opened, metadata = SourceVersionReader(catalog).open_described_version(
                ref, purpose="source_export"
            )
            pages = pdf_text_pages(opened.data)
            if evidence is not None:
                extra["evidence_validation"] = validate_quote(pages, evidence["quote"])
            try:
                extra["issuer_proof"] = extract_cn_issuer(
                    catalog, ref, pages=pages, metadata=metadata
                )
            except PrimaryIssuerUnavailable as exc:
                extra["issuer_proof"] = {"state": "unavailable", "reason": exc.reason}
        except (PrimaryIssuerUnavailable, SourceReadError) as exc:
            extra["issuer_proof"] = {"state": "unavailable", "reason": exc.reason}
            if evidence is not None:
                extra["evidence_validation"] = {
                    "state": "unavailable",
                    "reason": exc.reason,
                }
    elif evidence is not None:
        extra["evidence_validation"] = {
            "state": "unavailable",
            "reason": "native_pdf_required",
        }
    return _result(
        key,
        "available",
        "legacy_source_current_version_verified",
        **extra,
        source_ref=asdict(ref),
        document_version_id=document_version_id(
            ref.document_id, ref.source_id, ref.content_sha256
        ),
        current_byte_verification={
            "content_sha256": receipt.content_sha256,
            "byte_size": receipt.byte_size,
            "source_read_policy_sha256": receipt.source_read_policy_sha256,
            "read_at": receipt.read_at,
        },
    )
