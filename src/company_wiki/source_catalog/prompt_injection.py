"""FC-905-a: prompt-injection review receipt (per document).

The capture safety status must come from an explicit scanner/reviewer
receipt, never from a consumer's assumption.  The receipt lives in
``documents.metadata_json["prompt_injection_review"]``:

    {"status": "not_detected" | "detected_and_ignored",
     "reviewer": <non-empty>, "reviewed_at": <UTC>,
     "evidence_sha256": <64-hex>, "schema_version": "1.0",
     "state_domain": "review"}

Absent receipt == ``not_reviewed`` (the envelope reports that explicitly;
consumers block per policy — FC-905-b).  The writer validates fail-closed.

FIX-W06-GAPS repairs (oracle.md; COPIES ONLY — the product module is
untouched and stays byte-identical in before/):

  * P5-c dual binding MANDATORY for every status: ``source_sha256`` and
    ``policy_hash`` are required (lowercase SHA-256) — a receipt without
    source/policy binding is refused, closing the write-side gap the
    reader already treats as tampered.
  * P5-a payload binding + scan re-verification: ``evidence_payload`` (the
    scanned bytes/text) is required, ``sha256(payload) must ==
    evidence_sha256``, and ``scan_text(payload)`` is re-run internally —
    a declared status that contradicts the scan verdict is refused (a
    fabricated "clean" receipt over an actually-injected payload can no
    longer be written).  Residual forgery face (any hash recomputable from
    any payload) closes only with the OPEN-6 C1/C2 authorized-tuple +
    signature identity chain (letter B) — see decision.md.
  * P5-b disposal gate for ``detected_and_ignored`` (fail-closed): the
    authorization tuple (ignore_reason non-empty + ignore_authorizer +
    authorized_at + declared hit snapshot) must be complete, the trust root
    loaded (>= 1 signer key) and the authorizer signature verified — any
    gap is a defined ``disposal authorization unavailable: <item>``
    refusal.  Without an established trust root the status is ALWAYS
    refused (no identity => zero product-semantic lines).  The
    ``not_detected`` reviewer stays a free string but every write is
    audited (writer_pid / writer_write_at / explicit NOT-identity note).
  * P6-A optimistic concurrency control: the read-modify-write of the
    shared ``documents.metadata_json`` column is a CAS (bounded retries,
    then a defined ``concurrent write conflict`` refusal) and every write
    is read-back-provable via the append-only
    ``prompt_injection_review_audit`` trail — no silent displacement.
  * P6-B sqlite contention never escapes bare: writer/reader sqlite
    failures surface as ``store busy/lock timeout: ...``.
  * C7 state_domain disambiguation (fallback after the frozen-vocabulary
    conflict check): every receipt is stamped ``state_domain: "review"``;
    a record without it (or with an illegal value) is refused/fail-closed
    — the review conclusion ``detected_and_ignored`` can never be read as
    the cache state ``ignored`` and vice versa.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
from typing import Any

PROMPT_INJECTION_REVIEW_KEY = "prompt_injection_review"
PROMPT_INJECTION_REVIEW_AUDIT_KEY = "prompt_injection_review_audit"
PROMPT_INJECTION_REVIEW_SCHEMA_VERSION = "1.0"
PROMPT_INJECTION_REVIEW_STATUSES = frozenset(
    {"not_detected", "detected_and_ignored"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# C7: explicit domain tags on every state-carrying record (fail-closed:
# missing or illegal => refuse/strictest, never defaulted into either
# semantics).
STATE_DOMAIN_CACHE = "cache"
STATE_DOMAIN_REVIEW = "review"
STATE_DOMAINS = frozenset({STATE_DOMAIN_CACHE, STATE_DOMAIN_REVIEW})

WRITER_IDENTITY_NOTE = "writer metadata is an audit trail, NOT verified identity"

_CAS_MAX_ATTEMPTS = 5


class PromptInjectionReviewError(ValueError):
    """Raised when a review receipt cannot be written (fail closed)."""


def _require_sha256(value: str | None, field: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if value is None or not _SHA256_RE.fullmatch(value):
        raise PromptInjectionReviewError(
            f"{field} must be a lowercase SHA-256" + (" or None" if optional else ""))


def _validate_review_inputs(
    *,
    document_id: str,
    status: str,
    reviewer: str,
    evidence_sha256: str,
    schema_version: str,
    source_sha256: str | None,
    policy_hash: str | None,
) -> None:
    """Fail-closed validation shared by the receipt writer (ZR-302)."""
    if not document_id or not document_id.strip():
        raise PromptInjectionReviewError("document_id must be non-empty")
    if status not in PROMPT_INJECTION_REVIEW_STATUSES:
        raise PromptInjectionReviewError(
            f"status must be one of "
            f"{sorted(PROMPT_INJECTION_REVIEW_STATUSES)}, got {status!r}")
    if not reviewer or not reviewer.strip():
        raise PromptInjectionReviewError("reviewer must be non-empty")
    if schema_version != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
        raise PromptInjectionReviewError(
            f"schema_version must be "
            f"{PROMPT_INJECTION_REVIEW_SCHEMA_VERSION!r}")
    _require_sha256(evidence_sha256, "evidence_sha256")
    # FIX-W06-GAPS P5-c: dual binding MANDATORY for every status (was
    # optional=True — an unbound receipt was accepted while the reader
    # treats missing binding as tampered).
    _require_sha256(source_sha256, "source_sha256")
    _require_sha256(policy_hash, "policy_hash")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _load_scan_text():
    from .prompt_injection_guard import scan_text
    return scan_text


def _load_trust_root(path: str | None) -> dict[str, bytes]:
    """key_id -> raw ed25519 public key bytes; empty when unestablished."""
    if path is None:
        path = os.environ.get("PROMPT_INJECTION_TRUST_ROOT")
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        signers = raw.get("signers") if isinstance(raw, dict) else None
        if not isinstance(signers, dict):
            return {}
        keys: dict[str, bytes] = {}
        for key_id, entry in signers.items():
            if isinstance(entry, dict) and entry.get("algorithm") == "ed25519":
                try:
                    keys[str(key_id)] = base64.b64decode(
                        entry.get("public_key_base64", ""), validate=True)
                except (ValueError, TypeError):
                    continue
        return keys
    except (OSError, json.JSONDecodeError, TypeError, RecursionError):
        return {}


def _ed25519_verify(public_key_raw: bytes, message: bytes,
                    signature: bytes) -> bool | None:
    """True/False, or None when no signature backend is available."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError:
        return None
    try:
        key = Ed25519PublicKey.from_public_bytes(public_key_raw)
        key.verify(signature, message)
        return True
    except Exception:  # noqa: BLE001 — any verification failure == invalid
        return False


def _disposal_gate(
    *,
    document_id: str,
    status: str,
    source_sha256: str,
    policy_hash: str,
    evidence_sha256: str,
    ignore_reason: str | None,
    ignore_authorizer: str | None,
    authorized_at: str | None,
    declared_matches: Any,
    signer_key_id: str | None,
    authorizer_signature: str | None,
    trust_root_path: str | None,
) -> dict[str, str]:
    """P5-b: detected_and_ignored passes ONLY with (tuple) + (trust root)
    + (verified authorizer signature); every gap is a defined refusal."""
    if not ignore_reason or not str(ignore_reason).strip():
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: ignore_reason")
    if not ignore_authorizer or not str(ignore_authorizer).strip():
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: ignore_authorizer")
    if not authorized_at or not str(authorized_at).strip():
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: authorized_at")
    if not declared_matches:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: declared_matches")
    trust_root = _load_trust_root(trust_root_path)
    if not trust_root:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: trust root not established")
    if not signer_key_id:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: signer_key_id")
    if not authorizer_signature:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: authorizer signature")
    if signer_key_id not in trust_root:
        raise PromptInjectionReviewError(
            f"disposal authorization unavailable: signer key {signer_key_id!r} "
            f"not in trust root")
    message = _canonical_bytes({
        "authorized_at": str(authorized_at),
        "document_id": document_id,
        "evidence_sha256": evidence_sha256,
        "ignore_authorizer": str(ignore_authorizer),
        "ignore_reason": str(ignore_reason),
        "matches": list(declared_matches),
        "policy_hash": policy_hash,
        "source_sha256": source_sha256,
        "status": "detected_and_ignored",
    })
    signature_bytes = base64.b64decode(str(authorizer_signature), validate=True)
    verified = _ed25519_verify(trust_root[signer_key_id], message, signature_bytes)
    if verified is None:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: signature verification "
            "backend unavailable")
    if not verified:
        raise PromptInjectionReviewError(
            "disposal authorization unavailable: authorizer signature invalid")
    return {
        "ignore_reason": str(ignore_reason),
        "ignore_authorizer": str(ignore_authorizer),
        "authorized_at": str(authorized_at),
        "matches": json.dumps(list(declared_matches), ensure_ascii=False),
        "signer_key_id": str(signer_key_id),
    }


def _parse_metadata(raw: Any) -> dict:
    try:
        metadata = json.loads(raw or "{}")
        if not isinstance(metadata, dict):
            metadata = {}
    except (json.JSONDecodeError, TypeError, RecursionError):
        # B-VR05M2-04: the WRITE-side sibling of the reader fixed above; it also caught
        # only JSONDecodeError, so deep nesting raised RecursionError out of the receipt
        # writer (tests only today, but the same class of defect).
        metadata = {}
    return metadata


def record_prompt_injection_review(
    connection: Any,
    document_id: str,
    *,
    status: str,
    reviewer: str,
    evidence_sha256: str,
    now: str,
    schema_version: str = PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    source_sha256: str | None = None,
    policy_hash: str | None = None,
    evidence_payload: str | bytes | None = None,
    ignore_reason: str | None = None,
    ignore_authorizer: str | None = None,
    authorized_at: str | None = None,
    declared_matches: Any = None,
    signer_key_id: str | None = None,
    authorizer_signature: str | None = None,
    trust_root_path: str | None = None,
    state_domain: str | None = None,
) -> dict[str, str]:
    """Write (or overwrite) the document's prompt-injection review receipt.

    ``connection`` must be a sqlite3.Connection.  FIX-W06-GAPS P6-B contract
    amendment: the writer owns the transaction end of ITS own write (commit
    on success, rollback on failure) — the caller-side commit was where a
    bare ``database is locked`` escaped under contention.  Callers may still
    commit/rollback afterwards for their own pending work.
    Validates fail-closed: status enum, non-empty reviewer, sha256 evidence,
    non-empty document_id, schema version.  FIX-W06-GAPS additionally:
    mandatory dual binding (P5-c), mandatory evidence payload binding +
    scan re-verification (P5-a), the detected_and_ignored disposal gate
    (P5-b), CAS concurrency + audit trail (P6-A) and wrapped sqlite
    contention (P6-B).  Timeout semantics: the caller's connection/timeout
    parameters may only be tightened — this writer adds no waits.
    """
    _validate_review_inputs(
        document_id=document_id,
        status=status,
        reviewer=reviewer,
        evidence_sha256=evidence_sha256,
        schema_version=schema_version,
        source_sha256=source_sha256,
        policy_hash=policy_hash,
    )
    # C7: receipts are review-domain records; a conflicting tag is refused.
    if state_domain is not None and state_domain != STATE_DOMAIN_REVIEW:
        raise PromptInjectionReviewError(
            f"state_domain must be 'review' for a review receipt "
            f"(got {state_domain!r})")
    # P5-a payload binding.
    if evidence_payload is None:
        raise PromptInjectionReviewError(
            "evidence_payload must be provided "
            "(evidence_sha256 must bind the evidence bytes)")
    payload_bytes = (evidence_payload.encode("utf-8")
                     if isinstance(evidence_payload, str) else bytes(evidence_payload))
    if hashlib.sha256(payload_bytes).hexdigest() != evidence_sha256:
        raise PromptInjectionReviewError(
            "evidence_sha256 does not match sha256(evidence_payload)")
    # P5-a scan re-verification: the declared status must match scan fact.
    scan_text = _load_scan_text()
    scan = scan_text(evidence_payload.decode("utf-8", "replace")
                     if isinstance(evidence_payload, bytes) else evidence_payload)
    if scan.status != status:
        raise PromptInjectionReviewError(
            f"declared status {status!r} contradicts scan verdict "
            f"{scan.status!r} (fail closed)")
    disposal_fields: dict[str, str] = {}
    if status == "detected_and_ignored":
        disposal_fields = _disposal_gate(
            document_id=document_id, status=status,
            source_sha256=str(source_sha256), policy_hash=str(policy_hash),
            evidence_sha256=evidence_sha256,
            ignore_reason=ignore_reason, ignore_authorizer=ignore_authorizer,
            authorized_at=authorized_at, declared_matches=declared_matches,
            signer_key_id=signer_key_id,
            authorizer_signature=authorizer_signature,
            trust_root_path=trust_root_path,
        )
    receipt: dict[str, str] = {
        "schema_version": schema_version,
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": now,
        "evidence_sha256": evidence_sha256,
        "source_sha256": str(source_sha256),
        "policy_hash": str(policy_hash),
        # C7: explicit review-domain tag (fail-closed on missing/illegal).
        "state_domain": STATE_DOMAIN_REVIEW,
        # P5-b: reviewer is a free string — writer metadata is recorded for
        # audit only and is explicitly NOT identity.
        "writer_pid": str(os.getpid()),
        "writer_write_at": str(now),
        "writer_identity_note": WRITER_IDENTITY_NOTE,
    }
    receipt.update(disposal_fields)
    audit_entry = {
        "writer_pid": str(os.getpid()),
        "write_at": str(now),
        "evidence_sha256": evidence_sha256,
        "source_sha256": str(source_sha256),
        "policy_hash": str(policy_hash),
        "status": status,
    }
    try:
        for _attempt in range(_CAS_MAX_ATTEMPTS):
            row = connection.execute(
                "SELECT metadata_json FROM documents WHERE document_id=?",
                (document_id,),
            ).fetchone()
            if row is None:
                raise PromptInjectionReviewError(f"unknown document {document_id}")
            old_raw = row[0]
            metadata = _parse_metadata(old_raw)
            audit = metadata.get(PROMPT_INJECTION_REVIEW_AUDIT_KEY)
            if not isinstance(audit, list):
                audit = []
            metadata[PROMPT_INJECTION_REVIEW_AUDIT_KEY] = audit + [
                dict(audit_entry, seq=len(audit) + 1)
            ]
            metadata[PROMPT_INJECTION_REVIEW_KEY] = receipt
            new_raw = json.dumps(metadata, ensure_ascii=False)
            # P6-A: compare-and-swap on the value this write was computed
            # from — a concurrent change is never silently overwritten.
            if old_raw is None:
                cursor = connection.execute(
                    "UPDATE documents SET metadata_json=? WHERE document_id=? "
                    "AND metadata_json IS NULL",
                    (new_raw, document_id),
                )
            else:
                cursor = connection.execute(
                    "UPDATE documents SET metadata_json=? WHERE document_id=? "
                    "AND metadata_json=?",
                    (new_raw, document_id, old_raw),
                )
            if cursor.rowcount == 1:
                # P6-B: the writer owns the transaction end of ITS write —
                # the caller-side commit is where a bare "database is locked"
                # used to escape (06 Phase A2).  Commit here so every lock
                # failure surfaces as the defined store error instead.
                connection.commit()
                return receipt
        connection.rollback()
        raise PromptInjectionReviewError(
            f"concurrent write conflict: document {document_id}")
    except sqlite3.Error as exc:  # P6-B: never a bare sqlite3.* escape
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
        raise PromptInjectionReviewError(
            f"store busy/lock timeout: {type(exc).__name__}: {exc}") from exc


def read_prompt_injection_review(
    store: Any, document_id: str,
) -> dict[str, Any] | None:
    """Read the document's review receipt, or None when not reviewed.

    ``store`` must expose ``fetchone(sql, params)`` (CatalogStore-compatible).
    A malformed receipt (bad schema/status, missing or illegal state_domain)
    fails closed as ``not_reviewed`` rather than being trusted.
    """
    try:
        row = store.fetchone(
            "SELECT metadata_json FROM documents WHERE document_id=?",
            (document_id,),
        )
    except sqlite3.Error as exc:  # P6-B: reader path too
        raise PromptInjectionReviewError(
            f"store busy/lock timeout: {type(exc).__name__}: {exc}") from exc
    if row is None:
        return None
    try:
        metadata = json.loads(row[0] or "{}")
        if not isinstance(metadata, dict):
            return None
        receipt = metadata.get(PROMPT_INJECTION_REVIEW_KEY)
        if not isinstance(receipt, dict):
            return None
        if receipt.get("schema_version") != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
            return None
        if receipt.get("status") not in PROMPT_INJECTION_REVIEW_STATUSES:
            return None
        # C7 fail-closed: a state-carrying record without a valid domain tag
        # is ambiguous — never defaulted into either semantics.
        if receipt.get("state_domain") != STATE_DOMAIN_REVIEW:
            return None
        return receipt
    except (json.JSONDecodeError, TypeError, RecursionError, UnicodeDecodeError):
        # B-VR05M-03 (P1): the shared column is written by several modules and can be
        # malformed in more ways than one.  Catching only JSONDecodeError let a
        # non-UTF-8 byte sequence - and deeply nested JSON, since RecursionError is a
        # RuntimeError - escape this function, which the envelope calls BEFORE the
        # conflict check, so the read side said "blocked" while the envelope crashed on
        # the same document.  A malformed receipt is not-reviewed, never a crash.
        return None
