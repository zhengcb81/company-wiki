"""Normal Git publication of the owned W05 reception; retain raw command logs."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
BASE = "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11"
OUT = PROJECT / BASE / "evidence/root-audit-loop-acceptance"


def main():
    assert not (OUT / "publication-A.json").exists()
    def git(args, log_name=None):
        result = subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, timeout=180)
        if log_name:
            (OUT / log_name).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            print((result.stdout + result.stderr).decode("utf-8", errors="replace"))
            raise RuntimeError(f"git {args[0]} exit {result.returncode}")
        return result.stdout.decode("utf-8", errors="replace").strip()
    assert git(["rev-parse", "HEAD"]) == "35a9a64591169bf217f05e87aba633dc4204033a"
    assert not git(["diff", "--cached", "--name-only"])
    for relative, expected in {
        "config.yaml": "2f4df37c3d39ef380caf476b6b678949a1e4b7604bdb95b73b0033804209c589",
        "config/source_catalog.yaml": "3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968",
    }.items():
        assert hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest() == expected
    paths = [".planning/w05-audit-loop-reception", BASE + "/evidence/root-audit-loop-acceptance"]
    for family in ("cross-market-rf-e2e-2026-10-08", "narrative-evidence-pilot-2026-09-26"):
        paths.extend(f"docs/plans/{family}/{name}.md" for name in ("task_plan", "findings", "progress"))
    paths.extend(BASE + f"/{name}.md" for name in ("task_plan", "findings", "progress"))
    git(["add", "--", *paths])
    staged = git(["diff", "--cached", "--name-only"]).splitlines()
    assert all(any(name == path or name.startswith(path + "/") for path in paths) for name in staged)
    git(["diff", "--cached", "--check"])
    git(["commit", "-m", "docs(w05): accept audit loop with causal recovery fixes"], "publication-A-commit.log")
    head = git(["rev-parse", "HEAD"])
    git(["push", "origin", "master"], "publication-A-push.log")
    remote = git(["ls-remote", "origin", "refs/heads/master"]).split()[0]
    assert remote == head
    record = {"generated_at": datetime.now(timezone.utc).isoformat(), "commit": head,
              "remote_head": remote, "commit_exit": 0, "push_exit": 0,
              "normal_hooks": True, "staged_files": len(staged), "status": "PASS",
              "ci": "Not yet observed for this exact commit; no CI success claim.",
              "audit_main": "321d4c165575e81add3b4aa1ee9ba0a047ca6082"}
    (OUT / "publication-A.json").write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps(record))


if __name__ == "__main__":
    main()
