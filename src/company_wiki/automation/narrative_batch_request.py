"""Pathless, finite batch requests; storage paths belong to composition only."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import math
import re
from typing import Any

from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_VERSION,
)

from .models import canonical_json, canonical_json_hash
from .narrative_contracts import SourceRefValue
from .narrative_http_model import NarrativeHTTPModel
from .narrative_model import MODEL_REQUEST_SCHEMA, NARRATIVE_PROMPT_VERSION
from .narrative_formats import NORMALIZED_MIME_TYPES
from company_wiki.document_normalization import (
    PARSER_VERSION as NORMALIZATION_PARSER_VERSION,
)


BATCH_REQUEST_SCHEMA = "narrative-batch-request/1"
PROJECTED_BATCH_REQUEST_SCHEMA = "narrative-batch-request/2"
_MODEL_DEFAULTS = {
    "max_output_tokens": 2400,
    "timeout_seconds": 60,
    "max_request_bytes": 262144,
    "max_response_bytes": 262144,
    "allow_local_http": False,
}
_MAX_INT = (1 << 63) - 1


def _integer(value: Any, field: str, *, positive: bool = True) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= _MAX_INT:
        raise ValueError(f"{field} must be a bounded integer")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be nonempty unpadded text")
    return value


def _money(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("max_cost_usd must be a finite decimal amount")
    try:
        micros = Decimal(str(value)) * 1_000_000
        if (
            not micros.is_finite()
            or micros < 0
            or micros > _MAX_INT
            or micros != micros.to_integral_value()
        ):
            raise ValueError(
                "max_cost_usd must be nonnegative and precise to micro-USD"
            )
        return int(micros)
    except InvalidOperation:
        raise ValueError("max_cost_usd must be a finite decimal amount") from None


@dataclass(frozen=True)
class NarrativeBatchItem:
    """Explicit raw version or compact projection pointer; no copied records."""

    kind: str
    source_ref: SourceRefValue | None = None
    projection_id: str | None = None
    projection_sha256: str | None = None

    @classmethod
    def from_dict(cls, value: object) -> NarrativeBatchItem:
        if not isinstance(value, dict):
            raise ValueError("batch item must be an object")
        if value.get("kind") == "raw" and set(value) == {"kind", "source_ref"}:
            return cls("raw", source_ref=SourceRefValue.from_dict(value["source_ref"]))
        if value.get("kind") == "official_json" and set(value) == {
            "kind",
            "projection_id",
            "projection_sha256",
        }:
            digest = value["projection_sha256"]
            if (
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or value["projection_id"]
                != "urn:company-wiki:source-projection:sha256:" + digest
            ):
                raise ValueError("projection item ID/hash differ")
            return cls(
                "official_json",
                projection_id=value["projection_id"],
                projection_sha256=digest,
            )
        raise ValueError("invalid batch item fields")

    @property
    def item_key(self) -> str:
        if self.kind == "raw" and self.source_ref is not None:
            return self.source_ref.document_id
        if self.kind == "official_json" and self.projection_id is not None:
            return self.projection_id
        raise ValueError("invalid constructed batch item")

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "raw" and self.source_ref is not None:
            return {"kind": "raw", "source_ref": self.source_ref.to_dict()}
        return {
            "kind": self.kind,
            "projection_id": self.projection_id,
            "projection_sha256": self.projection_sha256,
        }


@dataclass(frozen=True)
class NarrativeBatchRequest:
    run_id: str
    sources: tuple[SourceRefValue, ...]
    profile: str
    max_seconds: float
    max_tokens: int
    max_micro_usd: int
    model_options_json: str
    pricing_version: str
    input_micro_usd_per_million_tokens: int
    output_micro_usd_per_million_tokens: int
    max_final_bytes: int
    max_persistent_bytes: int
    max_scratch_bytes: int
    refresh: bool = False
    items: tuple[NarrativeBatchItem, ...] = ()
    schema_version: str = BATCH_REQUEST_SCHEMA

    @classmethod
    def from_dict(cls, value: object) -> NarrativeBatchRequest:
        if not isinstance(value, dict) or value.get("schema_version") not in {
            BATCH_REQUEST_SCHEMA,
            PROJECTED_BATCH_REQUEST_SCHEMA,
        }:
            raise ValueError("unsupported narrative batch request schema")
        projected = value["schema_version"] == PROJECTED_BATCH_REQUEST_SCHEMA
        membership_field = "items" if projected else "sources"
        required = {
            "run_id",
            membership_field,
            "profile",
            "max_seconds",
            "max_tokens",
            "max_cost_usd",
            "model",
            "pricing",
        }
        if projected and set(value) - (
            required
            | {
                "schema_version",
                "refresh",
                "max_final_bytes",
                "max_persistent_bytes",
                "max_scratch_bytes",
            }
        ):
            raise ValueError("unsupported projected batch request fields")
        if not required <= value.keys():
            raise ValueError("batch request is missing required fields")
        if type(value.get("refresh", False)) is not bool:
            raise ValueError("refresh must be a boolean")
        membership = value[membership_field]
        if not isinstance(membership, list) or not 1 <= len(membership) <= 100:
            raise ValueError("batch must contain 1 to 100 explicit work items")
        sources: dict[str, SourceRefValue] = {}
        items: dict[str, NarrativeBatchItem] = {}
        for raw in membership:
            item = (
                NarrativeBatchItem.from_dict(raw)
                if projected
                else NarrativeBatchItem("raw", source_ref=SourceRefValue.from_dict(raw))
            )
            if item.item_key in items and items[item.item_key] != item:
                raise ValueError("batch has conflicting versions for one item")
            items[item.item_key] = item
            if item.source_ref is not None:
                sources[item.source_ref.document_id] = item.source_ref
        profile = value["profile"]
        if not isinstance(profile, str) or profile not in {"P1", "P2", "P4"}:
            raise ValueError("batch profile must be P1, P2 or P4")
        seconds = value["max_seconds"]
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
            or seconds <= 0
        ):
            raise ValueError("max_seconds must be finite and positive")
        model_raw = value["model"]
        if (
            not isinstance(model_raw, dict)
            or not {"model_id", "endpoint", "api_key_env"} <= model_raw.keys()
            or not model_raw.keys()
            <= (
                set(_MODEL_DEFAULTS)
                | {
                    "model_id",
                    "endpoint",
                    "api_key_env",
                    "thinking",
                    "reasoning_effort",
                    "temperature",
                    "reasoning_split",
                    "output_token_field",
                }
            )
        ):
            raise ValueError(
                "model options must contain supported non-secret fields only"
            )
        model = {**_MODEL_DEFAULTS, **model_raw}
        if type(model["allow_local_http"]) is not bool:
            raise ValueError("allow_local_http must be a boolean")
        NarrativeHTTPModel(
            **model
        )  # Pure configuration validation; no key read or HTTP.
        pricing = value["pricing"]
        if (
            not isinstance(pricing, dict)
            or not {
                "version",
                "input_micro_usd_per_million_tokens",
                "output_micro_usd_per_million_tokens",
            }
            <= pricing.keys()
        ):
            raise ValueError("explicit versioned pricing is required")
        final_bytes = _integer(
            value.get("max_final_bytes", 2 * 1024 * 1024), "max_final_bytes"
        )
        if final_bytes > 2 * 1024 * 1024:
            raise ValueError("one final artifact cannot exceed the 2 MiB emergency cap")
        return cls(
            _text(value["run_id"], "run_id"),
            tuple(sources.values()),
            profile,
            float(seconds),
            _integer(value["max_tokens"], "max_tokens"),
            _money(value["max_cost_usd"]),
            canonical_json(model),
            _text(pricing["version"], "pricing.version"),
            _integer(
                pricing["input_micro_usd_per_million_tokens"],
                "input price",
                positive=False,
            ),
            _integer(
                pricing["output_micro_usd_per_million_tokens"],
                "output price",
                positive=False,
            ),
            final_bytes,
            _integer(
                value.get("max_persistent_bytes", 1024**3), "max_persistent_bytes"
            ),
            _integer(value.get("max_scratch_bytes", 2 * 1024**3), "max_scratch_bytes"),
            value.get("refresh", False),
            tuple(items.values()) if projected else (),
            value["schema_version"],
        )

    @property
    def work_items(self) -> tuple[NarrativeBatchItem, ...]:
        return self.items or tuple(
            NarrativeBatchItem("raw", source_ref=ref) for ref in self.sources
        )

    @property
    def model_options(self) -> dict[str, Any]:
        return json.loads(self.model_options_json)

    def to_dict(self) -> dict[str, Any]:
        return {
            **({"refresh": True} if self.refresh else {}),
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            **(
                {"items": [item.to_dict() for item in self.work_items]}
                if self.schema_version == PROJECTED_BATCH_REQUEST_SCHEMA
                else {"sources": [ref.to_dict() for ref in self.sources]}
            ),
            "profile": self.profile,
            "max_seconds": self.max_seconds,
            "max_tokens": self.max_tokens,
            "max_cost_usd": format(Decimal(self.max_micro_usd) / 1_000_000, "f"),
            "model": self.model_options,
            "pricing": {
                "version": self.pricing_version,
                "input_micro_usd_per_million_tokens": self.input_micro_usd_per_million_tokens,
                "output_micro_usd_per_million_tokens": self.output_micro_usd_per_million_tokens,
            },
            "max_final_bytes": self.max_final_bytes,
            "max_persistent_bytes": self.max_persistent_bytes,
            "max_scratch_bytes": self.max_scratch_bytes,
        }

    @property
    def request_sha256(self) -> str:
        """Exact normalized intent, independent of installed execution versions."""
        return canonical_json_hash(self.to_dict())

    @property
    def execution_versions(self) -> dict[str, str]:
        """Freeze these once on a new run; never substitute them on resume."""
        versions = {
            "adapter": NarrativeHTTPModel.adapter_id,
            "model_request_schema": MODEL_REQUEST_SCHEMA,
            "prompt": NARRATIVE_PROMPT_VERSION,
            "parser": NARRATIVE_PARSER_VERSION,
            "selector": NARRATIVE_SELECTOR_VERSION,
        }
        if any(source.mime_type in NORMALIZED_MIME_TYPES for source in self.sources):
            versions["document_normalization"] = NORMALIZATION_PARSER_VERSION
        if any(item.kind == "official_json" for item in self.work_items):
            from .narrative_model import PROJECTION_MODEL_REQUEST_SCHEMA, PROJECTION_NARRATIVE_PROMPT_VERSION
            from .narrative_official_json import NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION
            versions.update(projection_prompt=PROJECTION_NARRATIVE_PROMPT_VERSION,
                projection_model_request_schema=PROJECTION_MODEL_REQUEST_SCHEMA,
                official_json_adapter=NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION)
        return versions

    @property
    def input_hash(self) -> str:
        if self.schema_version == PROJECTED_BATCH_REQUEST_SCHEMA:
            return canonical_json_hash({"request": self.to_dict(), "execution_versions": self.execution_versions})
        identity = {
            "request": self.to_dict(),
            "adapter": NarrativeHTTPModel.adapter_id,
            "prompt": NARRATIVE_PROMPT_VERSION,
            "parser": NARRATIVE_PARSER_VERSION,
            "selector": NARRATIVE_SELECTOR_VERSION,
        }
        if any(source.mime_type in NORMALIZED_MIME_TYPES for source in self.sources):
            identity["document_normalization"] = NORMALIZATION_PARSER_VERSION
        return canonical_json_hash(identity)


__all__ = [
    "BATCH_REQUEST_SCHEMA",
    "PROJECTED_BATCH_REQUEST_SCHEMA",
    "NarrativeBatchRequest",
    "NarrativeBatchItem",
]
