"""Build and mutate ``p4-consumer-observation/1`` payloads.

The lane's comparators must be exercised even when ROOT supplies no consumer
manifest.  ``observation_from_manifest`` derives a *correct* observation from a
genuine CWP manifest and read receipt; the ``mutate_*`` helpers then break
exactly one property each so the corresponding check has to catch it.

A derived observation is a property of the lane's guard, not evidence about a
real consumer - the receipt records that in ``limitations``.
"""

from __future__ import annotations

import copy
from typing import Any

from . import constants as C


def observation_from_manifest(
    *,
    consumer: str,
    manifest: dict[str, Any],
    receipt: dict[str, Any],
    spans: list[dict[str, Any]],
    quote_texts: list[str] | None = None,
) -> dict[str, Any]:
    """A shape-correct observation mirroring the upstream manifest."""
    texts = quote_texts if quote_texts is not None else [
        span["raw_text"] for span in spans
    ]
    span_by_text = {span["raw_text"]: span for span in spans}
    quotes = []
    for text in texts:
        span = span_by_text.get(text, {})
        quotes.append({
            "text": text,
            "unit_tokens": [
                {"text": token} for token in (span.get("unit_tokens") or [])
            ],
        })
    availability_evidence = receipt.get("availability_evidence")
    return {
        "schema_version": C.P4_OBSERVATION_SCHEMA,
        "consumer": consumer,
        "source_ref": {
            "document_id": manifest["document_id"],
            "source_id": manifest["source_id"],
            "content_sha256": manifest["content_sha256"],
            "byte_size": manifest["byte_size"],
            "mime_type": manifest["mime_type"],
            "schema_version": C.SOURCE_REF_SCHEMA_VERSION,
        },
        "facts": {
            key: manifest.get(key) for key in C.FACT_KEYS
        },
        "availability": {
            "status": (
                C.AVAILABILITY_UNKNOWN if availability_evidence is None
                else C.AVAILABILITY_OBSERVED
            ),
            "evidence": availability_evidence,
        },
        "quotes": quotes,
        "downloads": {"count": 0},
        "model_calls": {"count": 0},
    }


# --- one-property mutations (card section 6 RED list) ------------------------

def mutate_byte_size(observation: dict[str, Any], delta: int) -> dict[str, Any]:
    """``byte_size`` off by ``delta`` - must fail the ref roundtrip check."""
    mutated = copy.deepcopy(observation)
    mutated["source_ref"]["byte_size"] = mutated["source_ref"]["byte_size"] + delta
    return mutated


def mutate_security_id_width(observation: dict[str, Any], width: int) -> dict[str, Any]:
    """Zero-pad ``security_id`` to ``width`` - a silent identity rewrite."""
    mutated = copy.deepcopy(observation)
    value = mutated["facts"].get("security_id")
    if isinstance(value, str) and value.isdigit():
        mutated["facts"]["security_id"] = value.zfill(width)
    else:
        mutated["facts"]["security_id"] = str(value).zfill(width)
    return mutated


def mutate_fill_published_date(
    observation: dict[str, Any], value: str = "2026-03-01"
) -> dict[str, Any]:
    """Fill a null ``published_date`` - unknown must never become a date."""
    mutated = copy.deepcopy(observation)
    mutated["facts"]["published_date"] = value
    return mutated


def mutate_drop_unit_token(observation: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Remove a unit token the CWP span carries."""
    mutated = copy.deepcopy(observation)
    quotes = mutated["quotes"]
    if index < len(quotes) and quotes[index]["unit_tokens"]:
        quotes[index]["unit_tokens"].pop(0)
    return mutated


def mutate_rescale_quote(observation: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Rewrite a grounded quote into a converted magnitude (``1.2亿元``)."""
    mutated = copy.deepcopy(observation)
    quotes = mutated["quotes"]
    if index < len(quotes):
        quotes[index]["text"] = "1.2亿元"
        quotes[index]["unit_tokens"] = [{"text": "亿元"}]
    return mutated


def mutate_availability_observed(observation: dict[str, Any]) -> dict[str, Any]:
    """Turn an unknown upstream into ``observed`` - the loss P4 hunts for."""
    mutated = copy.deepcopy(observation)
    mutated["availability"] = {
        "status": C.AVAILABILITY_OBSERVED,
        "evidence": {"available_by": "2026-03-01"},
    }
    return mutated


def mutate_unmapped(observation: dict[str, Any]) -> dict[str, Any]:
    """Drop a required key so the shape no longer maps."""
    mutated = copy.deepcopy(observation)
    mutated.pop("downloads", None)
    return mutated


def mutate_add_field(observation: dict[str, Any]) -> dict[str, Any]:
    """Add an unknown top-level key - an added field is a shape violation."""
    mutated = copy.deepcopy(observation)
    mutated["extra"] = True
    return mutated
