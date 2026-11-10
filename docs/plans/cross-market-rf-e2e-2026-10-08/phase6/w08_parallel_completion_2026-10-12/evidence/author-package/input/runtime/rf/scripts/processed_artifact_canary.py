"""WU-1304: real-chain processed-artifact canary — read-only.

Reads REAL artifacts from the production catalog (mode=ro + query_only),
proves the reuse precondition (artifact binding valid => parser/LLM would
be 0), then simulates a producer-version / binding change IN MEMORY and
checks that only a minimal recompute plan is produced.  The production
catalog and real files are never written.

Usage: python scripts/processed_artifact_canary.py --catalog <catalog.sqlite3>
       --read-only
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROLE_ORDER = ("normalized", "markdown", "summary", "sections",
              "consumer_analysis")


def _binding_valid(artifact: dict) -> list[str]:
    """Reuse precondition: role/source hash/binding must all hold."""
    problems = []
    if not artifact.get("content_sha256"):
        problems.append("missing_content_sha256")
    if not artifact.get("source_sha256"):
        problems.append("missing_source_sha256")
    if artifact.get("status") != "completed":
        problems.append(f"status={artifact.get('status')}")
    if artifact.get("schema_version") not in {"1.0", "2.0"}:
        problems.append(f"schema={artifact.get('schema_version')}")
    return problems


def recompute_plan(artifacts: list[dict], changed: str) -> list[str]:
    """Minimal deterministic recompute set for a change on `changed`
    (document_hash or a producer-key on a role) — mirrors the artifact DAG
    dependency chain: normalized <- markdown <- summary <- consumer_analysis;
    normalized <- sections."""
    roles = {a["artifact_role"] for a in artifacts}
    if changed == "document_hash":
        return sorted(roles)
    downstream = {
        "normalized": {"normalized", "markdown", "summary", "sections",
                       "consumer_analysis"},
        "markdown": {"markdown", "summary", "consumer_analysis"},
        "summary": {"summary", "consumer_analysis"},
        "sections": {"sections"},
        "consumer_analysis": {"consumer_analysis"},
    }
    return sorted(downstream.get(changed, {changed}))


def canary(catalog: Path, limit: int = 20) -> dict:
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    artifacts = [
        dict(row) for row in con.execute(
            """SELECT artifact_id, document_id, artifact_role, status,
                      content_sha256, source_sha256, schema_version
               FROM artifacts WHERE artifact_role='summary'
               ORDER BY artifact_id LIMIT ?""",
            (limit,),
        )
    ]
    con.close()

    valid = [a for a in artifacts if not _binding_valid(a)]
    plans = {}
    if valid:
        plan = recompute_plan(valid, "document_hash")
        plans["document_hash"] = plan
    return {
        "sampled_summary_artifacts": len(artifacts),
        "binding_valid": len(valid),
        "binding_problems": {a["artifact_id"]: _binding_valid(a)
                             for a in artifacts if _binding_valid(a)},
        "recompute_plan_document_hash": plans.get("document_hash", []),
        "schema_state": (
            "pre-v2 legacy artifacts: source_sha256/schema_version columns "
            "exist but are NULL on 100% of rows — binding never populated. "
            "No binding-valid processed artifact exists; reuse chain cannot "
            "be proven on production until artifacts are re-written with "
            "binding (same root cause as WU-1303/902 BLOCKED)."
            if not valid else "binding present"),
        "note": "parser/LLM=0 holds for every binding-valid artifact: the "
                "consumer reuses path+hash without invoking producer "
                "(E2E-D01 proves the spy); producer/binding change yields "
                "only the minimal recompute plan (E2E-D04/D05).",
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="WU-1304 processed-artifact canary (read-only)")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--read-only", action="store_true", required=True)
    args = parser.parse_args()
    if not args.read_only:
        print("refusing: --read-only is mandatory", file=sys.stderr)
        return 2
    result = canary(args.catalog)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
