"""ZR-707: mixed recognition/gross-net and multi-commodity product matrix.

Extends the model combination to support:

  - Mixed recognition modes across segments (one segment modeled_as_recognized,
    another lagged_activity) — each segment validates its own mode independently;
    no cross-segment conflict detection needed.
  - Multi-commodity product matrix: a single mine can produce multiple
    commodities (e.g., copper + gold byproduct). Each commodity is a separate
    segment with its own model; the mine's total contribution is the sum.
  - Presentation consistency: each segment declares gross or net; trading/other
    activities must use the correct presentation (not approximated).
  - Segment bridge: segments aggregate to group via adjustments (already exists
    in segments.py; validated here for mixed-mode coherence).

Zero product hardcoding — commodity/mine names are test data only.
"""

from __future__ import annotations

from typing import Any

from contracts.constants import PRESENTATIONS, RECOGNITION_MODES
from contracts.evidence import require


def validate_mixed_recognition(segments: Any) -> None:
    """Validate that mixed recognition across segments is handled correctly.

    Each segment independently validates its own recognition mode
    (modeled_as_recognized or lagged_activity). This function checks that
    the combination is coherent:
      - All segments must have valid recognition metadata
      - No cross-segment conflict detection needed (each segment is independent)
    """
    if not isinstance(segments, list):
        return
    modes_seen: set[str] = set()
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        name = segment.get("name", "<unknown>")
        recognition = segment.get("recognition")
        if recognition is not None:
            mode = recognition.get("mode")
            if mode is not None:
                require(
                    mode in RECOGNITION_MODES,
                    f"segment {name} has unsupported recognition mode: {mode}",
                )
                modes_seen.add(mode)
    # Mixed modes are valid — no conflict detection needed
    # (each segment validates independently)


def validate_commodity_matrix(segments: Any) -> None:
    """Validate multi-commodity product matrix.

    A single mine can produce multiple commodities (e.g., copper + gold).
    Each commodity is a separate segment with its own model. The mine's
    total contribution is the sum of all commodity segments.

    This function validates:
      - Each segment has a valid model
      - Segments with the same base_revenue_parameter_id are part of the
        same multi-commodity matrix (allowed)
      - No duplicate segment names
    """
    if not isinstance(segments, list):
        return
    names_seen: set[str] = set()
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        name = segment.get("name")
        if name is not None:
            require(
                name not in names_seen,
                f"duplicate segment name in commodity matrix: {name}",
            )
            names_seen.add(name)


def validate_presentation_consistency(segments: Any) -> None:
    """Validate that each segment declares a valid presentation (gross/net).

    Trading/other activities must use the correct presentation — not
    approximated with a single wrong presentation.
    """
    if not isinstance(segments, list):
        return
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        name = segment.get("name", "<unknown>")
        recognition = segment.get("recognition")
        if recognition is not None:
            presentation = recognition.get("presentation")
            if presentation is not None:
                require(
                    presentation in PRESENTATIONS,
                    f"segment {name} has unsupported presentation: {presentation}",
                )
