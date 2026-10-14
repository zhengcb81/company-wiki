"""Fixture builders for the decision-dependency lane (du-decision-trace/1).

These helpers only assemble legal wire inputs and their mutations. They carry no
expectations, so the A-node tests can state the expected comparison outcome
independently of any implementation detail.

Nothing here reads the catalog, a file, the clock, or the network: every digest is a
caller-supplied full SHA-256 produced from an in-memory payload by
:func:`content_digest`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

TRACE_SCHEMA = "du-decision-trace/1"
FROZEN_SCHEMA = "du-decision-dependencies/1"
COMPARISON_SCHEMA = "du-decision-comparison/1"


def content_digest(payload: Any) -> str:
    """Full SHA-256 over a canonical JSON encoding of an in-memory payload.

    This is the digest the caller is expected to compute over the *complete* content
    of a component (matcher/policy/registry record), never over a display version.
    """
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def scope(
    scope_id: str,
    *,
    regime: str = "cn_exchange",
    family: str = "cn_annual",
    form_type: str | None = "annual_report",
    purpose: str = "periodic_report",
) -> dict[str, Any]:
    return {
        "scope_id": scope_id,
        "regime": regime,
        "family": family,
        "form_type": form_type,
        "purpose": purpose,
    }


def component(
    component_id: str,
    *,
    version: str = "1.0.0",
    content: Any = None,
    matcher: Any = None,
    content_digest_value: str | None = None,
    matcher_digest: str | None = None,
    scope_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """One decision component.

    ``content``/``matcher`` are *payloads* the caller would hash; passing them here
    computes the full digest. ``content_digest_value``/``matcher_digest`` override
    that so tests can also construct raw wire mappings directly.
    """
    return {
        "component_id": component_id,
        "version": version,
        "content_digest": content_digest_value
        if content_digest_value is not None
        else content_digest({"id": component_id, "content": content}),
        "matcher_digest": matcher_digest
        if matcher_digest is not None
        else content_digest({"id": component_id, "matcher": matcher}),
        "scope_ids": list(scope_ids),
    }


def candidate(
    candidate_id: str,
    *,
    scope_id: str,
    component_ids: Sequence[str] = (),
    eligible: bool = True,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "scope_id": scope_id,
        "component_ids": list(component_ids),
        "eligible": eligible,
    }


def trace(
    *,
    scopes: Iterable[Mapping[str, Any]] = (),
    components: Iterable[Mapping[str, Any]] = (),
    candidates: Iterable[Mapping[str, Any]] = (),
    versions: Mapping[str, Any] | None = None,
    schema_version: str = TRACE_SCHEMA,
    inventory_complete: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "scopes": [dict(item) for item in scopes],
        "components": [dict(item) for item in components],
        "candidates": [dict(item) for item in candidates],
        "versions": dict(versions if versions is not None else {"router": "0.8.0", "selector": "1.0.0"}),
        "inventory_complete": inventory_complete,
    }


# --- a small legal decision domain ------------------------------------------------

VERSIONS: dict[str, Any] = {
    "router": "0.8.0",
    "selector": "1.0.0",
    "structure": "du-structure/1",
}


def base_trace() -> dict[str, Any]:
    """Parent scope plus one child scope, four matched components and four candidates.

    ``c1`` is the deciding component for ``cand_a``; ``c2`` participates in the same
    scope but never wins (the "败选者" the card cares about). ``c3`` only ever touches
    ``cand_c``, and ``c4`` is the child scope's component.
    """
    return trace(
        scopes=[
            scope("scope_parent"),
            scope(
                "scope_child",
                family="cn_annual",
                form_type="annual_report",
                purpose="business_review",
            ),
        ],
        components=[
            component(
                "c1",
                version="1.0.0",
                content={"policy": "core_business", "priority": 1},
                matcher={"signals": ["经营情况", "主营业务"]},
                scope_ids=["scope_parent"],
            ),
            component(
                "c2",
                version="1.0.0",
                content={"policy": "financial_notes", "priority": 3},
                matcher={"signals": ["财务报表附注"]},
                scope_ids=["scope_parent"],
            ),
            component(
                "c3",
                version="1.0.0",
                content={"policy": "risk", "priority": 2},
                matcher={"signals": ["风险因素"]},
                scope_ids=["scope_parent"],
            ),
            component(
                "c4",
                version="1.0.0",
                content={"policy": "child_scope", "priority": 2},
                matcher={"signals": ["项目进展"]},
                scope_ids=["scope_child"],
            ),
        ],
        candidates=[
            candidate("cand_a", scope_id="scope_parent", component_ids=["c1", "c2"]),
            candidate("cand_b", scope_id="scope_parent", component_ids=["c1"]),
            candidate("cand_c", scope_id="scope_parent", component_ids=["c3"]),
            candidate("cand_d", scope_id="scope_child", component_ids=["c4"]),
        ],
        versions=VERSIONS,
    )


def with_component(trace_value: Mapping[str, Any], replacement: Mapping[str, Any]) -> dict[str, Any]:
    """Replace a component by id; every other field stays byte-identical."""
    updated = json.loads(json.dumps(trace_value, ensure_ascii=False))
    updated["components"] = [
        dict(replacement) if item["component_id"] == replacement["component_id"] else item
        for item in updated["components"]
    ]
    return updated


def bump_loser_priority(
    trace_value: Mapping[str, Any], component_id: str = "c2", priority: int = 1
) -> dict[str, Any]:
    """The classic miss: a component that never won changes its ranking/priority."""
    current = next(
        item for item in trace_value["components"] if item["component_id"] == component_id
    )
    content = {"policy": "financial_notes", "priority": priority}
    return with_component(
        trace_value,
        component(
            component_id,
            version=current["version"],
            content=content,
            matcher={"signals": ["财务报表附注"]},
            scope_ids=current["scope_ids"],
        ),
    )


__all__ = [
    "COMPARISON_SCHEMA",
    "FROZEN_SCHEMA",
    "TRACE_SCHEMA",
    "VERSIONS",
    "base_trace",
    "bump_loser_priority",
    "candidate",
    "component",
    "content_digest",
    "scope",
    "trace",
    "with_component",
]
