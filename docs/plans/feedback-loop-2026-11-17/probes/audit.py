"""Offline public Audit failures, cold owner lookups and F4 import.

Pass either a revenue-forecast-audit checkout or an installed skill directory.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time


ROOT = Path(__file__).resolve().parents[4]
PYTHON = [sys.executable, "-B", "-X", "utf8"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    source = parser.parse_args().source.resolve()
    if (source / "skills").is_dir():
        source = source / "skills" / "revenue-forecast-audit"
    cli = [*PYTHON, str(source / "scripts" / "audit_run.py")]
    owner = [*PYTHON, str(source / "scripts" / "feedback_owner.py")]
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "SYSTEMDRIVE",
        "TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "COMSPEC",
    }}
    with TemporaryDirectory(prefix="f4-au-") as directory:
        temp = Path(directory).resolve()
        run = temp / "sample"
        checks = []

        def execute(args, output):
            return subprocess.run(args, cwd=temp, input=b"", capture_output=True,
                                  env={**env, "RESEARCH_FEEDBACK_OUT": str(output)}, timeout=15)

        def cold(name, status, output, **extra):
            planned = subprocess.run([*PYTHON, "-m", "tools.feedback_loop", "plan", str(output)],
                                     cwd=ROOT, env=env, capture_output=True, check=True, timeout=15)
            plan = json.loads(planned.stdout)
            checks.append({"case": name, "exit": status, "observations": [
                [row["check_id"], row["actual"], row["disposition"]] for row in plan["observations"]
            ], "diagnostics": [row["code"] for row in plan["diagnostics"]], **extra})

        opts = ["--run", str(run), "--role", "executor"]
        init = ["init", "--root", str(temp), "--company", "Fixture", "--as-of", "2026-01-02"]
        execute([*cli, *init, "--run-id", run.name], temp / "setup").check_returncode()
        for name, args in [
            ("init-existing", [*init, "--run-id", run.name]),
            ("early-cli", ["capture", *opts, "--timeout-seconds", "0", "--", *PYTHON, "-V"]),
            ("early-capture", ["capture", *opts, "--retention-mode", "cas", "--", *PYTHON, "-V"]),
            ("incomplete-check", ["check", "--run", str(run)]),
        ]:
            out = temp / (name + ".jsonl")
            proc = execute([*cli, *args], out)
            cold(name, proc.returncode, out)

        for mode in ("capture", "structured", "owner-sidecar"):
            out = temp / (mode + ".jsonl")
            child = [*PYTHON, "-c", "import sys; print('synthetic cause',file=sys.stderr); sys.exit(7)"]
            proc = execute([*cli, "capture", *opts, "--outcome-source", mode, "--", *child], out)
            result = json.loads(proc.stdout)
            lookup = execute([*owner, "--run", str(run), "get-capture", "--role", "executor",
                              "--capture-id", result["capture_id"]], temp / "unused")
            lookup.check_returncode()
            cold(mode, proc.returncode, out, owner_status=json.loads(lookup.stdout)["status"],
                 original_reason="synthetic cause" in Path(result["stderr_artifact"]).read_text("utf8"),
                 delegated_sidecar_exists=bool(result.get("owner_feedback_artifact")
                                               and Path(result["owner_feedback_artifact"]).exists()))

        for exit_code in (0, 7):
            name = "limited-output-" + str(exit_code)
            out = temp / (name + ".jsonl")
            body = ("import sys; print('prefix\\n'*40, file=sys.stderr); "
                    "print('synthetic tail', file=sys.stderr); sys.exit(" + str(exit_code) + ")")
            proc = execute([*cli, "capture", *opts, "--max-log-bytes", "64", "--", *PYTHON, "-c", body], out)
            result = json.loads(proc.stdout)
            lookup = execute([*owner, "--run", str(run), "get-capture", "--role", "executor",
                              "--capture-id", result["capture_id"]], temp / "unused")
            lookup.check_returncode()
            cold(name, proc.returncode, out, owner_status=json.loads(lookup.stdout)["status"],
                 output_complete=result["output_complete"],
                 retained_bytes=result["stderr_retained_bytes"], total_bytes=result["stderr_total_bytes"],
                 tail_retained="synthetic tail" in Path(result["stderr_artifact"]).read_text("utf8"))

        out = temp / "kill.jsonl"
        entered, release = temp / "entered", temp / "release"
        child_code = ("from pathlib import Path\nimport time,sys\n"
                      "Path(sys.argv[1]).touch()\n"
                      "end=time.monotonic()+3\n"
                      "while not Path(sys.argv[2]).exists() and time.monotonic()<end: time.sleep(.02)")
        proc = subprocess.Popen([*cli, "capture", *opts, "--", *PYTHON, "-c", child_code,
                                 str(entered), str(release)], cwd=temp,
                                env={**env, "RESEARCH_FEEDBACK_OUT": str(out)},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 8
            while not entered.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(.03)
            if not entered.is_file():
                raise RuntimeError("capture did not start the fixture")
            proc.kill()
            proc.wait(timeout=6)
        finally:
            release.touch()
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=6)
        start = json.loads(out.read_text(encoding="utf8"))
        lookup = execute([*owner, "--run", str(run), "get-capture", "--role", "executor",
                          "--capture-id", start["attempt_id"]], temp / "unused")
        lookup.check_returncode()
        cold("kill-capture", proc.returncode, out, owner_status=json.loads(lookup.stdout))
        print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
