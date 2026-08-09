"""WU-803: artifact DAG — ported from the frozen Phase-2 contract
(ADR WU-204) for the resolver→bundle join.

Invalidation rules, deterministic selection and snapshot consistency are
identical to the contract tests (test_artifact_dag.py in the plan tools).
"""

from __future__ import annotations

ROLE_DEPENDENCIES: dict[str, list[str]] = {
    "normalized": [],
    "markdown": ["normalized"],
    "summary": ["markdown"],
    "sections": ["normalized"],
    "consumer_analysis": ["summary"],
}

PRODUCER_KEYS = ("producer_name", "producer_version", "schema_version",
                 "prompt_hash", "model_hash", "config_hash")


def _downstream(role: str) -> list[str]:
    """All roles transitively depending on `role` (including role itself)."""
    result: list[str] = []
    frontier = [role]
    while frontier:
        current = frontier.pop()
        if current in result:
            continue
        result.append(current)
        for candidate, parents in ROLE_DEPENDENCIES.items():
            if current in parents:
                frontier.append(candidate)
    return result


def invalidate(artifacts: list[dict], role: str, change: str) -> list[str]:
    """Minimal deterministic recompute set for a change on `role`.

    change: document_hash (original file changed) or a producer-key change
    on a specific artifact role.  If the change is a document-hash change
    every artifact is invalidated.
    """
    if change == "document_hash":
        return [a["role"] for a in artifacts]
    return sorted(_downstream(role))


def select_artifacts(
    artifacts: list[dict],
    *,
    document_hash: str,
    filing_status: str = "active",
) -> tuple[list[str], list[str]]:
    """Return (selected_roles, rejected_roles) deterministically."""
    selected: list[str] = []
    rejected: list[str] = []
    if filing_status in {"retired", "quarantined", "missing"}:
        return [], [a["role"] for a in artifacts]
    for artifact in sorted(artifacts, key=lambda a: a["role"]):
        role = artifact["role"]
        reasons = []
        if artifact.get("status") != "completed":
            reasons.append("status-not-completed")
        if artifact.get("input_document_hash") != document_hash:
            reasons.append("input-hash-mismatch")
        if artifact.get("schema_version") not in {"1.0", "2.0"}:
            reasons.append("unknown-schema")
        if reasons:
            rejected.append(role)
        else:
            selected.append(role)
    return selected, rejected


def bundle_snapshot_match(*, filing_snapshot: str, artifact_snapshot: str) -> bool:
    return filing_snapshot == artifact_snapshot
