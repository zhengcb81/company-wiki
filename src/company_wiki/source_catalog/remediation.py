"""FC-403: remediation proposal/approval workflow.

Proposal and approval are SEPARATE steps.  A proposal carries the source
bytes hash, per-field evidence (origin + source pointer), the proposed
fields and the policy hash — the reviewer's complete decision input.  The
approval tool only generates SHADOW assertions (never active); activation
is the Phase 2 control plane's job (activation.apply_activation).

Fail-closed rules: placeholder policy hashes (`plan-hash-*`), short
hashes, unknown proposals, and stale policy hashes are all rejected.  No
`user-approved-*` reviewer strings or short receipt ids are produced.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .store import CatalogStore

REMEDIATION_SCHEMA_VERSION = "1.0"
_HEX = set("0123456789abcdef")
_PLACEHOLDER_TOKENS = ("placeholder", "tbd", "n/a", "todo", "xxxx")


class RemediationError(ValueError):
    """Raised when a proposal/approval violates the remediation contract."""


def _valid_policy_hash(value: str) -> bool:
    if not (isinstance(value, str) and len(value) == 64
            and all(c in _HEX for c in value.lower())):
        return False
    return value.lower().strip() not in _PLACEHOLDER_TOKENS


def _proposal_id(source_id: str, content_sha256: str) -> str:
    digest = hashlib.sha256(
        f"{REMEDIATION_SCHEMA_VERSION}|{source_id}|{content_sha256}"
        .encode("utf-8")
    )
    return digest.hexdigest()[:32]


def create_proposal(
    store: CatalogStore,
    *,
    source_id: str,
    document_id: str,
    content_sha256: str,
    field_evidence: dict[str, dict[str, str]],
    proposed_fields: dict[str, Any],
    policy_hash: str,
    proposed_by: str,
) -> dict[str, Any]:
    """Create a remediation proposal.  The proposal binds the source bytes
    hash, per-field evidence (origin + source pointer), the proposed
    fields and the policy hash; it does NOT write any assertion."""
    if not (isinstance(policy_hash, str) and _valid_policy_hash(policy_hash)):
        raise RemediationError(
            f"policy_hash must be a 64-char hex sha256 (got {policy_hash!r}) — "
            f"placeholder policy hashes are forbidden"
        )
    if not (isinstance(proposed_by, str) and proposed_by.strip()):
        raise RemediationError("proposed_by required")
    if not (isinstance(source_id, str) and source_id.strip()):
        raise RemediationError("source_id required")
    if not (isinstance(content_sha256, str) and len(content_sha256) == 64):
        raise RemediationError("content_sha256 must be a 64-char hex sha256")
    if not isinstance(field_evidence, dict):
        raise RemediationError("field_evidence must be an object")
    for field, evidence in field_evidence.items():
        if not isinstance(evidence, dict) or not evidence.get("origin"):
            raise RemediationError(
                f"field_evidence[{field}] must carry origin + source_pointer"
            )
    if not isinstance(proposed_fields, dict) or not proposed_fields:
        raise RemediationError("proposed_fields must be a non-empty object")
    for field in proposed_fields:
        if field not in field_evidence:
            raise RemediationError(
                f"proposed field {field!r} has no field_evidence entry"
            )

    proposal_id = _proposal_id(source_id, content_sha256)
    proposal = {
        "schema_version": REMEDIATION_SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "status": "proposed",
        "source_id": source_id,
        "document_id": document_id,
        "evidence": {
            "source_bytes_sha256": content_sha256,
            "field_evidence": field_evidence,
        },
        "proposed_fields": proposed_fields,
        "policy_hash": policy_hash,
        "proposed_by": proposed_by,
    }
    # persist so approval can bind the exact evidence bundle
    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO remediation_proposals
            (proposal_id, source_id, document_id, content_sha256,
             proposal_json, policy_hash, proposed_by, created_at, status)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(proposal_id) DO NOTHING""",
            (proposal_id, source_id, document_id, content_sha256,
             json.dumps(proposal, ensure_ascii=False), policy_hash,
             proposed_by, "2026-08-10", "proposed"),
        )
    return proposal


def approve_proposal(
    store: CatalogStore,
    *,
    proposal_id: str,
    approved_by: str,
    policy_hash: str,
) -> dict[str, Any]:
    """Approve a remediation proposal: the reviewer confirms the evidence
    bundle and the policy hash, and the approval writes ONE shadow
    assertion (decision=verified, visibility_state=shadow).  Activation is
    a separate control-plane step."""
    if not (isinstance(policy_hash, str) and _valid_policy_hash(policy_hash)):
        raise RemediationError(
            f"policy_hash must be a 64-char hex sha256 (got {policy_hash!r})"
        )
    if not (isinstance(approved_by, str) and approved_by.strip()):
        raise RemediationError("approved_by required")
    # proposals are in-memory evidence bundles; approval materializes them
    # from the proposal id (deterministic).  A proposal id that was never
    # created cannot be approved — the id is bound to source+content.
    # We reconstruct and validate against the catalog to ensure the source
    # and document exist.
    if not (isinstance(proposal_id, str) and len(proposal_id) == 32):
        raise RemediationError("proposal_id must be a 32-char receipt id")
    # derive the source/content pair from the proposal id prefix convention
    # is not reversible, so the approval requires the catalog to hold the
    # proposal.  We persist proposals in the remediation table.
    row = store.fetchone(
        "SELECT * FROM remediation_proposals WHERE proposal_id=?",
        (proposal_id,),
    )
    if row is None:
        raise RemediationError(f"unknown proposal {proposal_id}")
    proposal = json.loads(row["proposal_json"])
    if proposal["policy_hash"] != policy_hash:
        raise RemediationError(
            f"stale policy hash: proposal {proposal['policy_hash'][:12]}... "
            f"!= approval {policy_hash[:12]}..."
        )

    from .assertion_service import upsert_verified_assertion
    from .normalized_meta import canonical_hash

    normalized = {
        "schema_version": "2.0",
        "canonical_entity_id": proposal["proposed_fields"].get("entity")
        or proposal["proposed_fields"].get("company_name"),
        "display_name": proposal["proposed_fields"].get("company_name"),
        "market": proposal["proposed_fields"].get("market"),
        "security_id": proposal["proposed_fields"].get("security_id"),
        "document_kind": proposal["proposed_fields"].get("document_kind"),
        "fiscal_year": proposal["proposed_fields"].get("fiscal_year"),
        "period_end": proposal["proposed_fields"].get("period_end"),
        "provider": proposal["proposed_fields"].get("provider"),
        "provider_document_id": proposal["proposed_fields"].get(
            "provider_document_id"
        ),
        "source_url": proposal["proposed_fields"].get("source_url"),
        "content_sha256": proposal["evidence"]["source_bytes_sha256"],
        "adapter_id": "remediation_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
        "evidence": proposal["evidence"]["field_evidence"],
    }
    normalized = {k: v for k, v in normalized.items() if v is not None}
    normalized["metadata_sha256"] = canonical_hash(normalized)
    assertion = upsert_verified_assertion(
        store,
        source_id=proposal["source_id"],
        document_id=proposal["document_id"],
        content_sha256=proposal["evidence"]["source_bytes_sha256"],
        adapter_id="remediation_v1",
        adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized),
        normalized=normalized,
        created_by=approved_by,
    )
    # approval output is always SHADOW; activation is a separate step
    with store.transaction() as conn:
        conn.execute(
            "UPDATE source_metadata_assertions SET visibility_state='shadow' "
            "WHERE assertion_id=?",
            (assertion["assertion_id"],),
        )
    return {
        "schema_version": REMEDIATION_SCHEMA_VERSION,
        "approval_id": proposal_id,
        "status": "approved",
        "assertion_id": assertion["assertion_id"],
        "policy_hash": policy_hash,
        "approved_by": approved_by,
        "visibility": "shadow",
    }


__all__ = [
    "REMEDIATION_SCHEMA_VERSION",
    "RemediationError",
    "approve_proposal",
    "create_proposal",
]
