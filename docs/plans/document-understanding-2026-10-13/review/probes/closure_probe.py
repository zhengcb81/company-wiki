"""Read-only regression probe; exit 1 means a required context was falsely complete."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys


def main() -> int:
    checkout = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(checkout / "src"))
    build = importlib.import_module(
        "company_wiki.document_understanding.summary_input"
    ).build_summary_input
    specs = [("p1", ["c", "d"], ["d"]), ("p2", ["b", "c"], ["c"]),
             ("p3", ["a", "b"], ["b"])]
    source = {"source_id": "test-source", "source_sha256": "test-sha"}
    packages = {"schema_version": "du-packages/1", "source_ref": source,
                "packages": [{"package_id": name, "kind": "project",
                              "section_ids": [], "section_role": "fundraising",
                              "member_unit_ids": members, "anchor_unit_ids": [members[0]],
                              "required_context_unit_ids": required,
                              "completeness": "complete", "truncated": False,
                              "diagnostics": []} for name, members, required in specs]}
    units = [{"unit_id": uid, "ordinal": i, "locator": f"loc-{uid}", "page": 1,
              "text": f"evidence-{uid}", "kind": "paragraph", "role": "company_filing",
              "hints": {}} for i, uid in enumerate("abcd")]
    result = build({"schema_version": "du-pipeline/1", "source_ref": source,
                    "observation": {"units": units}, "route": {}, "profile": {},
                    "structure": {}, "packages": packages}, selected_unit_ids=["a"])
    required = {name: set(deps) for name, _, deps in specs}
    rows = []
    for package in result["evidence_packages"]:
        present = {member["unit_id"] for member in package["members"]}
        rows.append({"package_id": package["package_id"], "members": sorted(present),
                     "completeness": package["completeness"],
                     "missing_required": sorted(required[package["package_id"]] - present)})
    bad = [row for row in rows if row["missing_required"] and row["completeness"] == "complete"]
    print(json.dumps({"emitted": rows, "closure_added": result["closure"]["added_unit_ids"],
                      "deferred": result["deferred"], "complete_with_missing_required": bad},
                     ensure_ascii=False, indent=2))
    return int(bool(bad))


if __name__ == "__main__":
    raise SystemExit(main())
