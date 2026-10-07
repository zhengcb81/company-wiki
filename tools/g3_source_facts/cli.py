#!/usr/bin/env python3
"""G3-SOURCE-FACTS read-only report CLI.

Two subcommands, both of which only read an already-collected evidence file or
an existing RAW-DUP report and write one JSON report:

  proposals  evidence input  -> metadata_proposals.json
  raw-space  RAW-DUP report  -> raw_space_decision.json

There is deliberately no apply/delete/update/hash-catalog/overwrite switch:
applying anything is MAIN's formal entrance, not this lane's.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import UTC, datetime
from typing import Any, Sequence

PACKAGE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = PACKAGE_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
for _path in (REPO_ROOT / "src", TOOLS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from g3_source_facts.budget import ReadBudget  # noqa: E402
from g3_source_facts.proposals import ProposalItem, build_report  # noqa: E402
from g3_source_facts.raw_space import build_raw_space_decision  # noqa: E402
from g3_source_facts.report import write_json_report  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="g3_source_facts",
        description="Read-only metadata and raw-space proposal reports (G3).",
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    proposals = subparsers.add_parser(
        "proposals", help="turn collected evidence into metadata_proposals.json"
    )
    proposals.add_argument("--input", required=True, help="evidence input JSON")
    proposals.add_argument("--output", required=True, help="report path")
    proposals.add_argument(
        "--observation-time", default=None, help="actual UTC ISO-8601"
    )

    raw_space = subparsers.add_parser(
        "raw-space", help="turn an existing RAW-DUP report into raw_space_decision.json"
    )
    raw_space.add_argument("--input", required=True, help="RAW-DUP report JSON")
    raw_space.add_argument("--output", required=True, help="report path")
    raw_space.add_argument(
        "--command", required=True, choices=("scan", "verify"), help="RAW-DUP mode used"
    )
    raw_space.add_argument("--input-version", required=True, help="input report schema")
    raw_space.add_argument(
        "--actual-command", default=None, help="exact CLI invocation"
    )
    raw_space.add_argument(
        "--limits-hit", action="append", default=None, help="repeatable limit marker"
    )
    raw_space.add_argument("--followup", default=None, help="follow-up note for MAIN")
    raw_space.add_argument(
        "--metadata",
        default=None,
        help="catalog metadata aggregation JSON supplying the registered bound",
    )
    return parser


def _read_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} is not a JSON object")
    return payload


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_proposals(args: argparse.Namespace) -> int:
    source = _read_json(args.input)
    observation_time = args.observation_time or datetime.now(UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    budget = ReadBudget()
    for entry in source.get("budget_charges", []):
        budget.charge(
            int(entry.get("bytes", 0)), label=str(entry.get("label", "input"))
        )
    items = [ProposalItem.from_dict(entry) for entry in source.get("items", [])]
    payload = build_report(
        items,
        catalog_observation=source.get("catalog_observation") or {},
        observation_time=observation_time,
        budget_summary=budget.summary(),
    )
    write_json_report(args.output, payload)
    print(
        json.dumps(
            {
                "output": Path(args.output).name,
                "items": len(payload["items"]),
                "actions": {
                    action: sum(1 for i in payload["items"] if i["action"] == action)
                    for action in sorted({i["action"] for i in payload["items"]})
                },
                "unknowns": len(payload["unknowns"]),
                "conflicts": len(payload["conflicts"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _run_raw_space(args: argparse.Namespace) -> int:
    report = _read_json(args.input)
    metadata = _read_json(args.metadata) if args.metadata else None
    registered_bound = None
    registered_groups = None
    bound_source = None
    if metadata is not None:
        registered_bound = metadata.get("registered_upper_bound_bytes")
        registered_groups = metadata.get("content_hashes_with_internal_copies")
        bound_source = str(metadata.get("source") or "catalog_metadata")
    payload = build_raw_space_decision(
        report,
        command=args.command,
        input_version=args.input_version,
        limits_hit=args.limits_hit or [],
        actual_command=args.actual_command,
        followup=args.followup,
        registered_internal_upper_bound_bytes=registered_bound,
        registered_internal_groups=registered_groups,
        registered_bound_source=bound_source,
        metadata=metadata,
        input_report_sha256=_sha256(args.input),
    )
    write_json_report(args.output, payload)
    print(
        json.dumps(
            {
                "output": Path(args.output).name,
                "decision": payload["decision"],
                "candidate_groups": payload["candidate_groups"],
                "verified_groups": payload["verified_groups"],
                "incomplete_groups": payload["incomplete_groups"],
                "registered_upper_bound_bytes": payload["registered_upper_bound_bytes"],
                "verified_distinct_copy_bytes": payload["verified_distinct_copy_bytes"],
                "allocated_bytes": payload["allocated_bytes"],
                "releasable_bytes": payload["releasable_bytes"],
                "deleted_bytes": payload["deleted_bytes"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command_name == "proposals":
        return _run_proposals(args)
    if args.command_name == "raw-space":
        return _run_raw_space(args)
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
