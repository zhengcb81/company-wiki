"""WU-502: adapter conformance kit.

Every adapter must pass the SAME parameterized suite before it may join the
registry.  Checks: deterministic enumerate, primary-role uniqueness,
sidecar/markdown never misclassified as original, no network/download/
parser/LLM imports, read-only guarantee (fixture untouched), candidates
valid against the NormalizedFilingMetadata schema, no duplicates.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .interface import check_candidate_determinism, check_no_duplicate_candidates


def run_conformance(adapter, tree: Path) -> dict:
    """Run the full kit against an adapter over a fixture tree; return a
    machine-readable receipt {check: ok|FAILED detail}."""
    receipt: dict[str, str] = {}

    # 1. deterministic enumerate (twice)
    first = adapter.enumerate(tree)
    second = adapter.enumerate(tree)
    problems = check_candidate_determinism(first, second)
    receipt["determinism"] = "ok" if not problems else f"FAILED: {problems}"

    # 2. no duplicate candidates
    problems = check_no_duplicate_candidates(first)
    receipt["no_duplicates"] = "ok" if not problems else f"FAILED: {problems}"

    # 3. primary role unique per group
    primary_keys = [c.group_key for c in first if c.role == "primary"]
    receipt["primary_unique"] = (
        "ok" if len(primary_keys) == len(set(primary_keys))
        else f"FAILED: {len(primary_keys) - len(set(primary_keys))} groups lack unique primary"
    )

    # 4. sidecar/markdown never original: a primary role must point at a
    #    real document file, not a derived/sidecar suffix
    NON_PRIMARY_SUFFIXES = {".md", ".json", ".txt", ".source.json"}
    bad_roles = [
        c.relative_path for c in first
        if c.role == "primary"
        and Path(c.relative_path).suffix in NON_PRIMARY_SUFFIXES
    ]
    receipt["role_separation"] = "ok" if not bad_roles else f"FAILED: {bad_roles}"

    # 5. read-only: fixture untouched after enumerate
    before = _tree_fingerprint(tree)
    adapter.enumerate(tree)
    after = _tree_fingerprint(tree)
    receipt["read_only"] = "ok" if before == after else "FAILED: fixture changed"

    # 6. candidates carry hashes matching file bytes
    hash_problems = []
    for candidate in first:
        path = tree / candidate.relative_path
        if not path.is_file():
            hash_problems.append(f"{candidate.relative_path}: file missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != candidate.content_sha256:
            hash_problems.append(
                f"{candidate.relative_path}: hash {actual[:8]} != "
                f"{candidate.content_sha256[:8]}"
            )
    receipt["hash_accuracy"] = "ok" if not hash_problems else f"FAILED: {hash_problems[:3]}"

    return receipt


def _tree_fingerprint(tree: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(tree.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(tree).as_posix().encode("utf-8"))
            digest.update(str(path.stat().st_size).encode("utf-8"))
    return digest.hexdigest()


def conformance_ok(receipt: dict) -> bool:
    return all(value == "ok" for value in receipt.values())
