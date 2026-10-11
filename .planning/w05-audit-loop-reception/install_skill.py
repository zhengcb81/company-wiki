"""Install exactly the accepted four differences in this one skill."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
AUDIT = Path("C:/Users/郑曾波/Projects/revenue-forecast-audit")
OUT = PROJECT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance"
EXPECTED = {"SKILL.md", "references/company-pool-loop.md", "references/pool-progress-contract.md", "scripts/pool_progress.py"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    assert not (OUT / "installation.json").exists()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=AUDIT).decode().strip()
    assert head == "321d4c165575e81add3b4aa1ee9ba0a047ca6082"
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=AUDIT).strip()
    spec = importlib.util.spec_from_file_location("w05_single_skill_sync", AUDIT / "tools/sync_skill.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    source = AUDIT / "skills/revenue-forecast-audit"
    files = tool.package_files(source)
    assert len(files) == 24
    accepted = json.loads((OUT / "acceptance.json").read_bytes())
    assert all(hashlib.sha256(data).hexdigest() == accepted["source_sha256"]["skills/revenue-forecast-audit/" + name] for name, data in files.items())
    preflight = [tool.synchronize(source, dest, check=True) for dest in tool.DEFAULT_DESTINATIONS]
    assert all(set(r["mismatches"]) == EXPECTED for r in preflight), preflight
    unaffected = {str(dest): {p.relative_to(dest).as_posix(): sha(p) for p in dest.rglob("*")
                             if p.is_file() and p.relative_to(dest).as_posix() not in EXPECTED | {".skill-install-manifest.json"}}
                  for dest in tool.DEFAULT_DESTINATIONS}
    def call(args, log_name):
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", *args], cwd=AUDIT,
                                capture_output=True, timeout=60)
        (OUT / log_name).write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0, (log_name, result.returncode)
        return result.stdout
    installed = json.loads(call(["tools/sync_skill.py"], "installation.log"))
    checked = json.loads(call(["tools/sync_skill.py", "--check"], "installation-check.log"))
    assert all(r["status"] == "MATCH" and r["files"] == 24 for r in checked["installations"])
    assert all(set(r["changed"]) == EXPECTED for r in installed["installations"])
    help_results = []
    for index, dest in enumerate(tool.DEFAULT_DESTINATIONS):
        assert all(sha(dest / name) == digest for name, digest in unaffected[str(dest)].items())
        output = call([str(dest / "scripts/pool_progress.py"), "--help"], f"installed-help-{index}.log")
        assert b"migrate-preview" in output and b"apply" in output
        help_results.append({"destination": str(dest), "exit_code": 0, "source_sha256": sha(dest / "scripts/pool_progress.py"), "unaffected_files_unchanged": len(unaffected[str(dest)])})
    record = {"generated_at": datetime.now(timezone.utc).isoformat(), "main_head": head,
              "preflight": preflight, "install": installed, "check": checked,
              "native_help": help_results, "scope": "one skill; four differing files per destination and install manifests only",
              "http_calls": 0, "llm_calls": 0, "status": "PASS"}
    (OUT / "installation.json").write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"status": "PASS", "main_head": head, "package_files": 24, "changed_files": 8}))


if __name__ == "__main__":
    main()
