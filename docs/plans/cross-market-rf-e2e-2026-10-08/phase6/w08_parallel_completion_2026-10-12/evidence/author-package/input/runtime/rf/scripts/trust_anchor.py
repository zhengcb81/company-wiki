"""Input-anchor binding invariant (R1.1, roadmap RC-1 / N-01).

An artifact's ``input_sha256`` must be the canonical hash of the input that
was actually validated — not a self-reported anchor.  Every validation entry
point (output validator, snapshot validator, invest-core adapter) shares this
single implementation so the rule can never drift between paths.
"""

from __future__ import annotations

from typing import Any

from contracts.evidence import ForecastInputError, canonical_sha256


def verify_input_binding(
    result: dict[str, Any], validated_input: dict[str, Any] | None = None
) -> None:
    """Fail closed unless every input the result carries or claims is bound.

    - When ``result`` embeds ``input_document``, its canonical hash must equal
      ``result["input_sha256"]``.
    - When *validated_input* is supplied (the input the validator actually
      re-runs), its canonical hash must also equal ``result["input_sha256"]``.
    """
    claimed = result.get("input_sha256")
    if not isinstance(claimed, str):
        raise ForecastInputError(
            "input binding mismatch: missing input_sha256 anchor"
        )
    embedded = result.get("input_document")
    if isinstance(embedded, dict) and canonical_sha256(embedded) != claimed:
        raise ForecastInputError(
            "input binding mismatch: embedded input_document does not hash to "
            "input_sha256"
        )
    if validated_input is not None and canonical_sha256(validated_input) != claimed:
        raise ForecastInputError(
            "input binding mismatch: validated input does not hash to input_sha256"
        )
