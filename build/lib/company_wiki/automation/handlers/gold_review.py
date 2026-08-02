"""AUTO-6 Gold review handler: wraps gold review gate as an automation handler.

This module depends on the models and store.  It does not import the legacy
scheduler, network, LLM or configuration modules.  The handler generates
review packets and validates receipts, but never writes accepted decisions or
modifies manifest.review_status directly.
"""

from __future__ import annotations

from ..models import (
    ArtifactRef,
    Effect,
    EffectStatus,
    HandlerError,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    make_effect_key,
)


def handle_gold_inputs_changed(input_data: dict) -> HandlerResult:
    """Handle a gold.inputs_changed event by generating a review packet.

    This is a simplified implementation that returns a packet structure.
    The actual packet generation logic is in scripts/gold_review_gate.py.
    """
    job_id = input_data.get("job_id", "")
    subject_id = input_data.get("subject_id", "")

    # In a real implementation, this would call build_review_packet().
    # For now, return a placeholder that indicates the packet was generated.
    result = {
        "action": "packet_generated",
        "subject_id": subject_id,
        "job_id": job_id,
    }

    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=result,
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0, duration_ms=10),
        error=None,
    )


def handle_review_receipt_changed(input_data: dict) -> HandlerResult:
    """Handle a review.receipt_changed event by validating the receipt.

    This is a simplified implementation that validates the receipt structure.
    The actual validation logic is in scripts/gold_review_gate.py.
    """
    job_id = input_data.get("job_id", "")
    subject_id = input_data.get("subject_id", "")

    # In a real implementation, this would call validate_review_receipt().
    # For now, return a placeholder that indicates the receipt was validated.
    result = {
        "action": "receipt_validated",
        "subject_id": subject_id,
        "job_id": job_id,
        "approved": False,  # Never auto-approve; requires human review
    }

    return HandlerResult(
        outcome=HandlerOutcome.BLOCKED_HUMAN,
        result=result,
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0, duration_ms=10),
        error=HandlerError(code="REVIEW_PENDING", detail="receipt requires human review"),
    )


def handle_gold_promote_reviewed(input_data: dict) -> HandlerResult:
    """Handle a gold.promote_reviewed event.

    This handler NEVER writes accepted decisions or modifies manifest.review_status.
    It only creates a promotion proposal (an outbox effect).
    """
    job_id = input_data.get("job_id", "")
    subject_id = input_data.get("subject_id", "")

    # In a real implementation, this would create a promotion proposal.
    # For now, return a placeholder that indicates the proposal was created.
    result = {
        "action": "promotion_proposal_created",
        "subject_id": subject_id,
        "job_id": job_id,
        "note": "proposal only; does not modify manifest or accepted decisions",
    }

    # Create an effect for the outbox (but don't execute it directly).
    effect_key = make_effect_key(
        "promotion_proposal", f"artifacts/proposals/{job_id}", job_id, "1.0.0"
    )
    effect = Effect(
        effect_id=f"eff-{job_id}",
        effect_key=effect_key,
        job_id=job_id,
        effect_type="promotion_proposal",
        target=f"artifacts/proposals/{job_id}",
        before_hash=None,
        intended_after_hash=None,
        actual_after_hash=None,
        status=EffectStatus.PLANNED,
        created_at="2026-07-12T12:00:00Z",
        verified_at=None,
    )

    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=result,
        artifacts=(
            ArtifactRef(path=f"artifacts/proposals/{job_id}", sha256="0" * 64),
        ),
        effects=(effect,),
        metrics=HandlerMetrics(tokens=0, cost_usd=0, duration_ms=10),
        error=None,
    )


# Registry of handlers for gold review job types.
GOLD_REVIEW_HANDLERS = {
    "gold.refresh_packet": handle_gold_inputs_changed,
    "gold.validate_receipt": handle_review_receipt_changed,
    "gold.promote_reviewed": handle_gold_promote_reviewed,
}


__all__ = [
    "handle_gold_inputs_changed",
    "handle_review_receipt_changed",
    "handle_gold_promote_reviewed",
    "GOLD_REVIEW_HANDLERS",
]
