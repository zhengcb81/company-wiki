"""Fit one optional final observation into its actual durable failure envelope."""
from __future__ import annotations

from dataclasses import replace

from .models import HandlerOutcome, HandlerResult, canonical_json
from .narrative_model import FAILED_FINAL_ATTEMPT_MAX_BYTES, FailedFinalDiagnostic


def fit_failed_final_result(base: HandlerResult, diagnostic: FailedFinalDiagnostic) -> HandlerResult:
    """No IO, no fees, and no JSON byte slicing: choose a codepoint prefix."""
    if base.outcome is HandlerOutcome.SUCCEEDED:
        raise ValueError("failed final cannot be attached to a successful result")
    original = diagnostic.final_prefix

    def candidate(length: int) -> HandlerResult:
        prefix = original[:length] if original is not None else None
        size = len(prefix.encode("utf-8")) if prefix is not None else 0
        observed = replace(diagnostic, final_prefix=prefix, prefix_bytes=size,
            clipped=diagnostic.final_content_bytes is not None and size < diagnostic.final_content_bytes)
        return replace(base, result={**base.result, "failed_final": observed.to_dict()})

    def fits(value: HandlerResult) -> bool:
        return len(canonical_json(value.to_dict()).encode("utf-8")) < FAILED_FINAL_ATTEMPT_MAX_BYTES

    fitted = candidate(0)
    if not fits(fitted):
        return base  # Optional diagnostics cannot replace the primary failure/meter.
    low, high = 0, len(original) if original is not None else 0
    while low < high:
        middle = (low + high + 1) // 2
        if fits(candidate(middle)):
            low = middle
        else:
            high = middle - 1
    fitted = candidate(low)
    if not fits(fitted):
        return base
    return fitted
