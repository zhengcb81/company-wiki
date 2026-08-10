"""FC-203: real activation/rollback transactions (ActivationSnapshot 1.0).

Cohort/epoch/policy-snapshot switches happen ONLY inside a catalog
transaction; partial batch failure rolls the whole transaction back with
no half-activation (CTRL-03).  Every apply/rollback appends an immutable
journal receipt; rollback is proven by the same request's before/after
response trace and never deletes assertions (CTRL-04).  Repeated apply or
rollback, wrong cohort, unknown receipt and stale policy hash all fail
closed.

The runtime policy snapshot (FC-201) remains the request-start pin; this
module changes the *database* activation state (visibility_state /
activation_epoch / cohort) that the snapshot's reader consumes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Sequence

from .store import CatalogStore

ACTIVATION_SCHEMA_VERSION = "1.0"
RECEIPT_SCHEMA_VERSION = "1.0"


class ActivationError(ValueError):
    """Raised when an activation/rollback violates the contract."""


def _utc_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _receipt_id(epoch: str, cohort: str, reason: str) -> str:
    digest = hashlib.sha256(
        f"{ACTIVATION_SCHEMA_VERSION}|{epoch}|{cohort}|{reason}|{_utc_iso()}"
        .encode("utf-8")
    )
    return digest.hexdigest()[:32]


def _validate_assertions(
    store: CatalogStore, assertion_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Return rows for the given assertions; raises on any unknown/non-
    verified assertion (batch must be atomic)."""
    if not assertion_ids:
        raise ActivationError("assertion_ids must not be empty")
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for assertion_id in assertion_ids:
        if assertion_id in seen:
            raise ActivationError(f"duplicate assertion_id {assertion_id}")
        seen.add(assertion_id)
        row = store.fetchone(
            "SELECT * FROM source_metadata_assertions WHERE assertion_id=?",
            (assertion_id,),
        )
        if row is None:
            raise ActivationError(f"unknown assertion_id {assertion_id}")
        record = dict(row)
        if record.get("decision") != "verified":
            raise ActivationError(
                f"assertion {assertion_id} is not verified "
                f"(decision={record.get('decision')!r})"
            )
        rows.append(record)
    return rows


def preview_activation(
    store: CatalogStore,
    *,
    assertion_ids: Sequence[str],
) -> dict[str, Any]:
    """Read-only preview: which rows would flip, which are already active."""
    rows = _validate_assertions(store, assertion_ids)
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "candidates": len(rows),
        "already_active": [
            r["assertion_id"] for r in rows
            if r.get("visibility_state") == "active"
        ],
        "will_flip": [
            r["assertion_id"] for r in rows
            if r.get("visibility_state") != "active"
        ],
    }


def apply_activation(
    store: CatalogStore,
    *,
    epoch: str,
    cohort: str,
    assertion_ids: Sequence[str],
    policy_hash: str,
    reviewer: str,
    reason: str,
    current_policy_hash: str | None = None,
) -> dict[str, Any]:
    """Flip the batch to active inside ONE catalog transaction.

    Any failure (unknown id, non-verified, already active, stale policy
    hash) raises ActivationError and the whole transaction rolls back —
    no half-activation (CTRL-03).  ``current_policy_hash`` (the RootPolicy
    export hash at request time) makes a stale ``policy_hash`` fail closed
    instead of silently accepting an outdated activation.
    """
    if not (isinstance(epoch, str) and epoch.strip()):
        raise ActivationError("epoch must be non-empty text")
    if not (isinstance(cohort, str) and cohort.strip()):
        raise ActivationError("cohort must be non-empty text")
    if not (isinstance(policy_hash, str) and len(policy_hash) == 64):
        raise ActivationError("policy_hash must be a 64-char sha256")
    if current_policy_hash is not None and policy_hash != current_policy_hash:
        raise ActivationError(
            f"stale policy hash: activation {policy_hash[:12]}... != "
            f"current policy {current_policy_hash[:12]}... (re-load the "
            f"RootPolicy snapshot and retry)"
        )
    if not (isinstance(reviewer, str) and reviewer.strip()):
        raise ActivationError("reviewer required")
    if not (isinstance(reason, str) and reason.strip()):
        raise ActivationError("reason required")

    rows = _validate_assertions(store, assertion_ids)
    already = [r["assertion_id"] for r in rows
               if r.get("visibility_state") == "active"]
    if already:
        raise ActivationError(
            f"already active, cannot re-apply: {already}"
        )

    receipt_id = _receipt_id(epoch, cohort, reason)
    created_at = _utc_iso()
    with store.transaction() as conn:
        for record in rows:
            conn.execute(
                "UPDATE source_metadata_assertions "
                "SET visibility_state='active', activation_epoch=?, cohort=? "
                "WHERE assertion_id=?",
                (epoch, cohort, record["assertion_id"]),
            )
        conn.execute(
            "INSERT INTO activation_journal "
            "(receipt_id, schema_version, kind, epoch, cohort, "
            " assertion_ids_json, policy_hash, reviewer, reason, created_at, "
            " applies_receipt_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                receipt_id, RECEIPT_SCHEMA_VERSION, "apply", epoch, cohort,
                json.dumps([r["assertion_id"] for r in rows],
                           ensure_ascii=False),
                policy_hash, reviewer, reason, created_at, None,
            ),
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "kind": "apply",
        "epoch": epoch,
        "cohort": cohort,
        "assertion_ids": [r["assertion_id"] for r in rows],
        "policy_hash": policy_hash,
        "reviewer": reviewer,
        "reason": reason,
        "created_at": created_at,
    }


def rollback_activation(
    store: CatalogStore,
    *,
    receipt_id: str,
    cohort: str | None = None,
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    """Revert a prior apply inside ONE catalog transaction.

    The apply receipt must exist; when ``cohort`` is given it must match
    (wrong cohort fails closed).  Assertions are NOT deleted — visibility
    flips back to shadow; the activation_epoch is preserved for audit.
    A second rollback of the same receipt is rejected (immutable receipt).
    """
    if not (isinstance(reviewer, str) and reviewer.strip()):
        raise ActivationError("reviewer required")
    if not (isinstance(reason, str) and reason.strip()):
        raise ActivationError("reason required")
    apply_row = store.fetchone(
        "SELECT * FROM activation_journal WHERE receipt_id=? AND kind='apply'",
        (receipt_id,),
    )
    if apply_row is None:
        raise ActivationError(f"unknown apply receipt {receipt_id}")
    apply_record = dict(apply_row)
    if cohort is not None and apply_record["cohort"] != cohort:
        raise ActivationError(
            f"cohort mismatch: receipt cohort {apply_record['cohort']!r} "
            f"!= {cohort!r}"
        )
    already_rolled = store.fetchone(
        "SELECT 1 FROM activation_journal "
        "WHERE applies_receipt_id=? AND kind='rollback' LIMIT 1",
        (receipt_id,),
    )
    if already_rolled is not None:
        raise ActivationError(f"receipt {receipt_id} already rolled back")

    assertion_ids = json.loads(apply_record["assertion_ids_json"] or "[]")
    rollback_id = _receipt_id(
        apply_record["epoch"], apply_record["cohort"], f"rollback:{reason}"
    )
    created_at = _utc_iso()
    with store.transaction() as conn:
        for assertion_id in assertion_ids:
            conn.execute(
                "UPDATE source_metadata_assertions "
                "SET visibility_state='shadow' WHERE assertion_id=?",
                (assertion_id,),
            )
        conn.execute(
            "INSERT INTO activation_journal "
            "(receipt_id, schema_version, kind, epoch, cohort, "
            " assertion_ids_json, policy_hash, reviewer, reason, created_at, "
            " applies_receipt_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                rollback_id, RECEIPT_SCHEMA_VERSION, "rollback",
                apply_record["epoch"], apply_record["cohort"],
                apply_record["assertion_ids_json"],
                apply_record["policy_hash"], reviewer, reason, created_at,
                receipt_id,
            ),
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": rollback_id,
        "kind": "rollback",
        "epoch": apply_record["epoch"],
        "cohort": apply_record["cohort"],
        "assertion_ids": assertion_ids,
        "policy_hash": apply_record["policy_hash"],
        "reviewer": reviewer,
        "reason": reason,
        "created_at": created_at,
        "applies_receipt_id": receipt_id,
    }


def journal_rows(store: CatalogStore) -> list[dict[str, Any]]:
    """Append-only journal, oldest first."""
    rows = store.fetchall(
        "SELECT * FROM activation_journal ORDER BY created_at ASC"
    )
    return [dict(r) for r in rows]


__all__ = [
    "ACTIVATION_SCHEMA_VERSION",
    "ActivationError",
    "apply_activation",
    "journal_rows",
    "preview_activation",
    "rollback_activation",
]
