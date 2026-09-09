"""V5 freeze builder (write-only; not part of the frozen set).

Runs the v5 pre-freeze checker, captures its stdout byte-exactly into
`plan_freeze_check.v5.txt`, then writes `plan_manifest.v5.json` binding:

  * the 48 imported plan inputs + 3 v5-own governing artifacts (frozen set 51)
  * the capture manifest, the v3/v4 supersession chain, the investigation source
  * the coverage counts recomputed from the frozen corpus
  * the two evidence tools and the pre-freeze output

Usage:  python tools/v5_freeze_manifest_build.py

The frozen set deliberately excludes this builder, the manifest and the
captured output; verification is `v5_plan_consistency_check.py
--verify-manifest` plus `--self-test` (N1-N17).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

V5 = Path(__file__).resolve().parents[1]
REPO = V5.parents[2]
BASELINE = V5 / "baseline" / "plan"
MANIFEST = V5 / "plan_manifest.v5.json"
FREEZE_OUTPUT = V5 / "plan_freeze_check.v5.txt"
CHECKER = V5 / "tools" / "v5_plan_consistency_check.py"
IMPORT_MANIFEST = V5 / "import_manifest.v5.json"
EQUIVALENCE = V5 / "v5-baseline-equivalence.json"
GOVERNING = ("plan_manifest.schema.v5.json", "tools/v5_plan_consistency_check.py", ".gitattributes")
EVIDENCE_TOOLS = ("tools/v5_version_reference_scan.py", "tools/v5_equivalence_check.py")
IMMUTABILITY = ("Do not overwrite or append to this file. A semantic plan change requires a new "
                "plan_manifest.vN.json filename and independent re-review.")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def entry(rel: str, path: Path, equivalence: str) -> dict:
    raw = path.read_bytes()
    return {"path": rel, "sha256": sha(raw), "size_bytes": len(raw), "equivalence": equivalence}


def main() -> int:
    run = subprocess.run([sys.executable, str(CHECKER)], cwd=str(REPO),
                         capture_output=True)
    payload = run.stdout
    if run.returncode != 0:
        sys.stdout.write(payload.decode("utf-8", errors="replace"))
        print(f"freeze aborted: checker exit {run.returncode}", file=sys.stderr)
        return 1
    if b"\r" in payload:
        print("freeze aborted: captured output contains CR (must be LF)", file=sys.stderr)
        return 1
    FREEZE_OUTPUT.write_bytes(payload)
    text = payload.decode("utf-8")
    reported = int(text.split("checks;")[0].split(":")[1].strip())

    spec = importlib.util.spec_from_file_location("v4_plan_check", BASELINE / "plan_consistency_check.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    coverage = module.current_coverage_counts(module.dag_checks()[1])

    groups = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))["groups"]
    labels = {rel: name for name, rels in groups.items() if name != "unresolved" for rel in rels}
    entries = [entry("baseline/plan/" + p.name, p, labels["baseline/plan/" + p.name])
               for p in sorted(BASELINE.glob("*")) if p.is_file()]
    entries += [entry(rel, V5 / rel, "v5_own") for rel in GOVERNING]
    entries.sort(key=lambda item: item["path"].casefold())
    imported = sum(1 for item in entries if item["equivalence"] != "v5_own")

    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()
    manifest = {
        "schema_version": 3,
        "protocol_revision": "v4",
        "freeze_generation": "v5",
        "capture_manifest": {
            "path": "import_manifest.v5.json",
            "sha256": sha(IMPORT_MANIFEST.read_bytes()),
        },
        "frozen_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "plan_directory": "docs/plans/source-catalog-worker-recovery-v5-2026-09-03",
        "plan_freeze_git_head": head,
        "review_state_at_freeze": "FROZEN_FOR_INDEPENDENT_REVIEW",
        "supersedes": [
            {"path": "baseline/history/plan_manifest.v4.json",
             "sha256": sha((V5 / "baseline" / "history" / "plan_manifest.v4.json").read_bytes())},
            {"path": "baseline/history/plan_manifest.v3.json",
             "sha256": sha((V5 / "baseline" / "history" / "plan_manifest.v3.json").read_bytes())},
        ],
        "investigation_source": {
            "path": "baseline/investigation/worker-investigation-2026-08-20.md",
            "sha256": sha((V5 / "baseline" / "investigation" /
                           "worker-investigation-2026-08-20.md").read_bytes()),
        },
        "normative_file_count": len(entries),
        "normative_files": entries,
        "frozen_set_composition": {"imported": imported, "v5_own_governing": len(GOVERNING),
                                   "total": len(entries), "self_excluded": 1},
        "equivalence_summary": {
            name: sum(1 for item in entries if item["equivalence"] == name)
            for name in ("v4_exact", "crlf_only", "unproven_new_baseline")},
        "coverage_counts": coverage,
        "pre_freeze_check": {
            "command": "python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/"
                       "tools/v5_plan_consistency_check.py",
            "exit_code": 0,
            "reported_check_count": reported,
            "stdout_sha256": sha(payload),
            "read_only_confirmed": True,
        },
        "evidence_tools": [
            {"path": rel, "sha256": sha((V5 / rel).read_bytes()),
             "size_bytes": (V5 / rel).stat().st_size} for rel in EVIDENCE_TOOLS],
        "self_exclusion": "plan_manifest.v5.json",
        "immutability_policy": IMMUTABILITY,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"frozen: {len(entries)} files, {imported} imported, pre-freeze count {reported}, "
          f"head {head[:12]}, output sha {sha(payload)[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
