"""Exercise the public F4 launcher with a fresh local inbox and no provider."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing


ROOT = Path(__file__).resolve().parents[4]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
OWNER = "company-wiki"


def inspect(directory):
    with closing(sqlite3.connect((directory / "actions.sqlite").as_uri() + "?mode=ro", uri=True)) as db:
        return [
            {"kind": row[0], "status": row[1], "check": row[2], "actual": row[3]}
            for row in db.execute(
                "SELECT json_extract(request,'$.kind'),state,"
                "json_extract(request,'$.payload.observation.check_id'),"
                "json_extract(request,'$.payload.observation.actual') FROM actions ORDER BY action_id"
            )
        ]


def exercise(root, name, original):
    directory = root / name
    directory.mkdir()
    if name == "inbox-unavailable":
        (directory / "inbox").write_text("occupied by an ordinary file", encoding="utf8")
    settings, hosts = directory / "settings.json", directory / "hosts.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {
        OWNER: {"cwd": str(ROOT), "observation_dir": "inbox"}
    }}), encoding="utf8")
    hosts.write_text(json.dumps({OWNER: [*PYTHON, "-m", "tools.feedback_loop.local_host",
                                         "--config", str(settings), "rpc"]}), encoding="utf8")
    cli = [*PYTHON, "-m", "tools.feedback_loop.intake", "--settings", str(settings),
           "--hosts", str(hosts), "--wait-seconds", "0"]
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "USERPROFILE", "HOME",
                              "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "COMSPEC", "SYSTEMDRIVE"}}
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in (ROOT, ROOT / "src"))

    def run(command):
        return subprocess.run(command, cwd=ROOT, env=env, input=b"", capture_output=True, timeout=30)

    result = run([*cli, "run", "--owner", OWNER, "--", *original])
    drained = run([*cli, "drain"])
    drained.check_returncode()
    cold = run([*PYTHON, str(Path(__file__).resolve()), "--inspect", str(directory)])
    cold.check_returncode()
    return {"case": name, "native_exit": result.returncode, "native_stderr": result.stderr.decode().strip(),
            "drain": json.loads(drained.stdout), "cold_actions": json.loads(cold.stdout)}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--inspect":
        return inspect(Path(sys.argv[2]))
    with tempfile.TemporaryDirectory(prefix="f4-cold-") as scratch:
        root = Path(scratch).resolve()
        reader = [*PYTHON, "-m", "company_wiki.source_catalog.source_reader_cli", "--config",
                  str(root / "intentionally-missing.yaml"), "--source-id", "s", "--document-id", "d",
                  "--content-sha256", "a" * 64]
        return [exercise(root, name, argv) for name, argv in (
            ("success", [*PYTHON, "-c", "pass"]),
            ("nonzero", [*PYTHON, "-c", "raise SystemExit(17)"]),
            ("never-started", [str(root / "absent-f4-executable")]),
            ("native-read", reader),
            ("inbox-unavailable", [*PYTHON, "-c", "raise SystemExit(33)"]),
        )]


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=True, indent=2))
