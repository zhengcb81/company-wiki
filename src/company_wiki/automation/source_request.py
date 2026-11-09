"""Compose AUTO batch requests from values returned by the source owner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .narrative_batch_request import NarrativeBatchRequest


def prepare_official_narrative_request(
    imports: Sequence[Mapping[str, Any]], *, batch_template: Mapping[str, Any]
) -> NarrativeBatchRequest:
    """Build an AUTO request from imported source references.

    A membership-free template explicitly selecting the shared engine gets the
    configured quote-primary recipe unless the caller specifies a projection.
    Complete serialized requests preserve their previous intent. Source
    acquisition supplies values; this AUTO-owned adapter validates the request.
    """
    value = dict(batch_template)
    if (value.get("selector_version") == "0.9.0"
            and "reading_model_projection" not in value
            and not {"sources", "items"}.intersection(value)):
        from .narrative_model_extractive import EXTRACTIVE_MODEL_PROJECTION_VERSION

        value["reading_model_projection"] = EXTRACTIVE_MODEL_PROJECTION_VERSION
    value["sources"] = [item["source_ref"] for item in imports]
    return NarrativeBatchRequest.from_dict(value)


__all__ = ["prepare_official_narrative_request"]
