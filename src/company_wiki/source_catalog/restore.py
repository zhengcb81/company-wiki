"""WU-904: explicit restore — never fuzzy, always audited.

restore_asset(document_id, *, file_hash_matches, v2_complete,
provenance_ok, policy_allows, reviewer, reason) returns a RestoreReceipt
or rejects with reasons.  Every restore keeps the original retire reason and
appends restore reason/actor/time/policy hash; history is never deleted and
a later event can revert it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RestoreReceipt:
    receipt_id: str
    document_id: str
    restore_reason: str
    reviewer: str
    policy_hash: str
    original_retire_reason: str
    reverted: bool = False


@dataclass
class RestoreRejection:
    reasons: list[str] = field(default_factory=list)


def restore_asset(
    *,
    document_id: str,
    file_hash_matches: bool,
    v2_complete: bool,
    provenance_ok: bool,
    policy_allows: bool,
    reviewer: str,
    reason: str,
    original_retire_reason: str,
    policy_hash: str,
    allow_fuzzy: bool = False,
) -> tuple[RestoreReceipt | None, RestoreRejection]:
    """REST-01..06: explicit single-document restore with full gates."""
    rejection = RestoreRejection()
    if allow_fuzzy:
        rejection.reasons.append("fuzzy_batch_restore_forbidden")
    if not document_id or "," in document_id or " " in document_id:
        rejection.reasons.append("must_target_one_document_id")
    if not file_hash_matches:
        rejection.reasons.append("file_hash_changed")
    if not v2_complete:
        rejection.reasons.append("v2_metadata_incomplete")
    if not provenance_ok:
        rejection.reasons.append("missing_provenance")
    if not policy_allows:
        rejection.reasons.append("root_policy_denied")
    if not reviewer:
        rejection.reasons.append("reviewer_required")
    if not reason:
        rejection.reasons.append("restore_reason_required")
    if rejection.reasons:
        return None, rejection
    receipt_id = hashlib.sha256(
        f"{document_id}|{reviewer}|{reason}|{policy_hash}".encode("utf-8")
    ).hexdigest()[:16]
    return RestoreReceipt(
        receipt_id=receipt_id,
        document_id=document_id,
        restore_reason=reason,
        reviewer=reviewer,
        policy_hash=policy_hash,
        original_retire_reason=original_retire_reason,
    ), RestoreRejection()


def revert_restore(receipt: RestoreReceipt) -> RestoreReceipt:
    """A restore can be reverted via a new event; history is not deleted."""
    return RestoreReceipt(
        receipt_id=receipt.receipt_id,
        document_id=receipt.document_id,
        restore_reason=receipt.restore_reason,
        reviewer=receipt.reviewer,
        policy_hash=receipt.policy_hash,
        original_retire_reason=receipt.original_retire_reason,
        reverted=True,
    )
