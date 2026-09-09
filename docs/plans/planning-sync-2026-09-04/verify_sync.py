"""Read-only consistency checks for the 2026-09-04 planning sync."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


WIKI = Path(__file__).resolve().parents[3]
PROJECTS = WIKI.parent
AUDIT = Path(__file__).resolve().parent

EXPECTED_IMMUTABLE = {
    WIKI / "TERMINAL_NOTICE.json": "b3f3ceb22f17e8a174bf5bd535bddef619132c9e6d72277eae3eea1e4eac9103",
    WIKI / "docs/plans/source-catalog-worker-recovery-v5-2026-09-03/import_manifest.v5.json": "da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a",
    PROJECTS / "filing-fetch/assurance/fc/FC-903/12_reviewer_receipt.json": "bcfb14e30b2f82ae1520b929f87a8fb732653f992eed35ef360a55c5589334d3",
    PROJECTS / "revenue-forecast/TERMINAL_NOTICE.json": "b3f3ceb22f17e8a174bf5bd535bddef619132c9e6d72277eae3eea1e4eac9103",
    PROJECTS / "revenue-forecast/assurance/unified_completion/manifests/plan_inputs.json": "9e43255e5e56102cbc49e04615d1a1adeb34dece918b976bb0d8867b282d85e4",
}

CURRENT_DOCS = (
    WIKI / "PLANNING_STATUS.md",
    WIKI / "docs/archive/CURRENT_STATUS.md",
    WIKI / "docs/plans/catalog-space-remediation/CURRENT_STATUS.md",
    WIKI / "docs/plans/core-section-extraction/CURRENT_STATUS.md",
    WIKI / "docs/plans/portfolio-reuse-automatic/CURRENT_STATUS.md",
    WIKI / "docs/plans/portfolio-reuse-fix/CURRENT_STATUS.md",
    PROJECTS / "filing-fetch/PLANNING_STATUS.md",
    PROJECTS / "filing-fetch/e2e/E2E_DESIGN.md",
    PROJECTS / "revenue-forecast/PLANNING_STATUS.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/task_plan.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/findings.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/progress.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/gp008_009_deployment_guide.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/gp010_cohort_cutover_request.md",
    PROJECTS / "revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/n1_r9_removal_request.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED_IMMUTABLE.items():
        if not path.is_file():
            errors.append(f"IMMUTABLE-MISSING {path}")
        elif digest(path) != expected:
            errors.append(f"IMMUTABLE-HASH {path}")

    link_re = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
    for document in CURRENT_DOCS:
        if not document.is_file():
            errors.append(f"CURRENT-MISSING {document}")
            continue
        text = document.read_text(encoding="utf-8")
        for raw in link_re.findall(text):
            target_text = raw.split("#", 1)[0]
            if not target_text or "://" in target_text:
                continue
            target = (document.parent / target_text).resolve()
            if not target.exists():
                errors.append(f"BROKEN-LINK {document}: {raw}")

    inventory_path = AUDIT / "company-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory_files = inventory.get("files", [])
    for entry in inventory_files:
        path = WIKI / entry["path"]
        if not path.is_file():
            errors.append(f"INVENTORY-MISSING {path}")
            continue
        if path.stat().st_size != entry["bytes"]:
            errors.append(f"INVENTORY-SIZE {path}")
        if digest(path) != entry["sha256"]:
            errors.append(f"INVENTORY-HASH {path}")
        if entry.get("read_status") != "full":
            errors.append(f"INVENTORY-READ-STATUS {path}: {entry.get('read_status')}")

    v5 = WIKI / "docs/plans/source-catalog-worker-recovery-v5-2026-09-03"
    if (v5 / "plan_manifest.v5.json").exists():
        errors.append("V5-STATE unexpected formal plan_manifest.v5.json")
    state = json.loads((PROJECTS / "revenue-forecast/assurance/unified_completion/state.json").read_text(encoding="utf-8"))
    if state.get("plan_status") != "completed" or state.get("implementation_status") != "completed":
        errors.append("UNIFIED-STATE expected historical completed ledger")

    if errors:
        print("FAIL planning sync")
        print(*errors, sep="\n")
        return 1
    print(
        f"PASS planning sync: {len(CURRENT_DOCS)} current docs; "
        f"{len(EXPECTED_IMMUTABLE)} immutable anchors; "
        f"{len(inventory_files)} company inventory entries"
    )
    print("READ_ONLY: no production, process, registry, network, or source mutation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
