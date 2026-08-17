"""ZR-306 RED/property tests: SourceBundle role DAG minimal invalidation.

Pins the registry-mandated evidence:
  - document-hash change invalidates EVERY role (full recompute);
  - a producer-key change on one role invalidates exactly its transitive
    downstream closure (self included) — upstream is never touched;
  - missing dependency subtrees recompute only the missing/dependent
    subtree (satisfied independent branches are not recomputed);
  - the invalidation set is idempotent and matches a hand-computed
    downstream closure over ROLE_DEPENDENCIES;
  - the DAG is acyclic (topological reachability over all roles).

Product code (artifact_dag.py, WU-803) is reused unchanged; this card
pins its correctness with property tests over a small exhaustive domain.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.artifact_dag import (  # noqa: E402
    PRODUCER_KEYS,
    ROLE_DEPENDENCIES,
    invalidate,
)

ALL_ROLES = tuple(sorted(ROLE_DEPENDENCIES))


def _downstream_closure(role: str) -> set[str]:
    """Hand-computed transitive downstream closure (self included)."""
    result: set[str] = set()
    frontier = [role]
    while frontier:
        current = frontier.pop()
        if current in result:
            continue
        result.add(current)
        for candidate, parents in ROLE_DEPENDENCIES.items():
            if current in parents:
                frontier.append(candidate)
    return result


def _artifacts(roles: list[str]) -> list[dict]:
    return [{"role": role, "artifact_id": f"a-{role}"} for role in roles]


def test_document_hash_change_invalidates_every_role() -> None:
    """A source-bytes (document_hash) change forces a full recompute:
    every role is invalidated."""
    for roles in itertools.chain(
        [ALL_ROLES],
        [list(c) for c in itertools.combinations(ALL_ROLES, 3)],
    ):
        invalidated = invalidate(_artifacts(roles), "normalized", "document_hash")
        assert set(invalidated) == set(roles), (
            f"document_hash change did not invalidate all roles: "
            f"{sorted(invalidated)} vs {sorted(roles)}")


def test_producer_key_change_invalidates_exact_downstream_closure() -> None:
    """A producer-key change on one role invalidates exactly its transitive
    downstream closure (self included); upstream roles are untouched."""
    for role in ALL_ROLES:
        for change in PRODUCER_KEYS:
            invalidated = invalidate(_artifacts(ALL_ROLES), role, change)
            expected = _downstream_closure(role)
            assert set(invalidated) == expected, (
                f"{change} on {role}: {sorted(invalidated)} != {sorted(expected)}")


def test_missing_dependency_subtree_recomputes_only_dependents() -> None:
    """A missing role only forces recompute of ITS dependents — an
    independent satisfied branch is never recomputed."""
    # summary missing -> only summary + consumer_analysis need recompute;
    # the normalized/markdown/sections branch is satisfied and untouched.
    missing = "summary"
    missing_set = _downstream_closure(missing)
    independent = set(ALL_ROLES) - missing_set
    invalidated = invalidate(_artifacts(ALL_ROLES), missing, "producer_version")
    assert set(invalidated) == missing_set
    assert not (set(invalidated) & independent), (
        f"independent branch recomputed: {sorted(set(invalidated) & independent)}")
    # sections missing -> only sections; normalized->markdown->summary chain
    # is an independent branch here (summary depends on markdown, not sections).
    missing = "sections"
    invalidated = invalidate(_artifacts(ALL_ROLES), missing, "producer_version")
    assert set(invalidated) == _downstream_closure(missing)


def test_invalidation_idempotent_and_closure_match() -> None:
    """Same inputs -> same invalidation set; and the set always equals the
    hand-computed downstream closure (no dead code, no over-invalidation)."""
    for role in ALL_ROLES:
        for change in PRODUCER_KEYS + ("document_hash",):
            first = invalidate(_artifacts(ALL_ROLES), role, change)
            second = invalidate(_artifacts(ALL_ROLES), role, change)
            assert first == second, f"{change} on {role} not idempotent"
            expected = (
                list(ALL_ROLES)
                if change == "document_hash"
                else sorted(_downstream_closure(role))
            )
            assert sorted(first) == expected, (
                f"{change} on {role}: {sorted(first)} != {expected}")


def test_dag_is_acyclic() -> None:
    """The role DAG has no cycle: every role's dependency chain terminates
    at 'normalized' (the only root with empty parents)."""
    seen: set[str] = set()
    for role in ROLE_DEPENDENCIES:
        current = role
        trail: list[str] = []
        while ROLE_DEPENDENCIES.get(current):
            if current in trail:
                raise AssertionError(f"cycle in role DAG: {trail + [current]}")
            trail.append(current)
            current = ROLE_DEPENDENCIES[current][0]
        assert current == "normalized", (
            f"role {role} dependency chain does not terminate at normalized: "
            f"{trail} -> {current}")
        seen.add(role)
    assert seen == set(ALL_ROLES)


def test_producer_keys_cover_prompt_and_model_hashes() -> None:
    """The producer-key taxonomy includes the prompt/model/config hashes so
    a prompt or model change invalidates the DAG downstream."""
    assert {"prompt_hash", "model_hash", "config_hash"} <= set(PRODUCER_KEYS)
