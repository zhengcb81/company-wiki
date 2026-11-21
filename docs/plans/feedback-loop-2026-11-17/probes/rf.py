"""Offline ordinary RF entry points, stage failure and independent F4 readback.

Run with the RF source checkout path, optionally followed by its deployed runtime
and the installed skill path. The owner test tree supplies synthetic input only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--skill", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    runtime = (args.runtime or repo / ".worktrees/f4-runtime").resolve()
    skill = (args.skill or Path.home() / ".agents/skills/revenue-forecast").resolve()
    control = Path(__file__).resolve().parents[4]
    python = [sys.executable, "-B", "-X", "utf8"]
    # Import only the owner's synthetic input and isolated FF/CWP test ports.
    sys.path.insert(0, str(repo / "tests"))
    from test_rf_job_facade_cli import _deployment, _request

    def call(argv, cwd, env, data=None):
        return subprocess.run([*python, *map(str, argv)], cwd=cwd, env=env,
                              input=data, encoding="utf-8", capture_output=True, timeout=45)

    # The deployed RF job tree has several nested components. Use the existing
    # short test root on Windows when available, to exercise the intended fault.
    short_root = control / ".tmp"
    with TemporaryDirectory(prefix="f4rf-", dir=short_root if short_root.is_dir() else None) as temp:
        root = Path(temp)
        owner = root / "owner"
        owner.mkdir()
        deployment, body = _deployment(root)
        body.write_bytes(b"X" * body.stat().st_size)
        invalid = root / "invalid.json"
        invalid.write_text("{", encoding="utf-8")
        job = [runtime / "scripts/rf_job_cli.py", "--owner-root", owner]
        env = {k: os.environ[k] for k in (
            "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
            "USERPROFILE", "HOME", "SYSTEMDRIVE", "LOCALAPPDATA", "APPDATA",
        ) if k in os.environ}
        env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
        cases = {
            "installed_forecast": ([skill / "scripts/revenue_forecast.py", invalid, "--validate-only"], None),
            "public_source": ([runtime / "scripts/source_preparation.py", "--request-file", invalid], None),
            "catalog": ([runtime / "scripts/report_catalog_cli.py", "--owner-root", owner,
                         "get-report", "--report-id", "absent"], None),
            "invalid_submit": ([*job, "submit"], "{"),
            "bad_source_bytes": ([*job, "--deployment-config", deployment, "submit"], json.dumps(_request())),
        }
        output = {}
        for name, (argv, payload) in cases.items():
            sidecar = root / (name + ".jsonl")
            observed_env = {**env, "RESEARCH_FEEDBACK_OUT": str(sidecar),
                            "RESEARCH_FEEDBACK_RUN_ID": name, "RESEARCH_FEEDBACK_ATTEMPT_ID": "a1"}
            result = call(argv, root, observed_env, payload)
            read = call(["-m", "tools.feedback_loop", "plan", sidecar], control, observed_env)
            read.check_returncode()
            data = json.loads(read.stdout)
            row = {"exit": result.returncode, "stderr_nonempty": bool(result.stderr),
                   "readback_diagnostics": [d["code"] for d in data["diagnostics"]], "checks": [
                       [item["check_id"], item["actual"], item["disposition"]]
                       for item in data.get("observations", [])
                   ]}
            if result.stderr.startswith("{"):
                error = json.loads(result.stderr)
                row["code"] = (error.get("error", {}).get("code") if isinstance(error.get("error"), dict)
                               else error.get("error_code"))
            if name == "bad_source_bytes":
                if result.returncode:
                    raise ValueError(f"fixture did not reach RF source stage: {row}")
                job_id = json.loads(result.stdout)["owner_job_id"]
                resumed = call([*job, "get-status", "--job-id", job_id], root, env)
                resumed.check_returncode()
                view = json.loads(resumed.stdout)["job_view"]
                row.update(cold_status=view["status"], cost_state=view["cost_state"],
                           stages={stage["stage"]: stage["status"] for stage in view["stages"]},
                           attempts=sum(len(stage["attempts"]) for stage in view["stages"]))
            output[name] = row
        print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
