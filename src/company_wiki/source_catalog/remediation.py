"""Retired proposal/approval writer; current metadata belongs to source facts.

Keep import signatures for historical callers without database/config IO.
Existing proposal rows remain readable; no review identity or policy digest
can reactivate this obsolete second metadata-writing workflow.
"""

from __future__ import annotations

from typing import Any


class RemediationError(ValueError):
    """Named retirement of the legacy metadata proposal/approval workflow."""


def create_proposal(
    store: Any,
    *,
    source_id: str,
    document_id: str,
    content_sha256: str,
    field_evidence: dict[str, dict[str, str]],
    proposed_fields: dict[str, Any],
    policy_hash: str,
    proposed_by: str,
) -> dict[str, Any]:
    """Historical entry; use current source-facts/local-prepare metadata APIs."""
    raise RemediationError(
        "legacy_remediation_retired: use source-facts or local-prepare; "
        "no proposal or human approval is required"
    )


def approve_proposal(
    store: Any,
    *,
    proposal_id: str,
    approved_by: str,
    policy_hash: str,
) -> dict[str, Any]:
    """Historical entry; never write a shadow assertion or approval receipt."""
    raise RemediationError(
        "legacy_remediation_retired: use source-facts or local-prepare; "
        "no proposal or human approval is required"
    )


__all__ = ["RemediationError", "create_proposal", "approve_proposal"]
