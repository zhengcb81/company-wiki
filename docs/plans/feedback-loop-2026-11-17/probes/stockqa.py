"""Compare ordinary StockQA failures with cold F4 readback and paid recovery controls.

The default replays the reported release. Use --revision HEAD for the latest
commit, or --working-tree for a disposable copy of a specified owner checkout.
"""

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


CWP = Path(__file__).resolve().parents[4]
BASELINE = "2f649c8ee06040383603934dec24bbf15d2c84bc"
PYTHON = [sys.executable, "-B", "-X", "utf8"]
TEST = "tests/unit/test_quick_scan_feedback_observation.py"
SCOPE = ["main_with_llm.py", "src", "tests/__init__.py", "tests/conftest.py",
         "tests/unit/__init__.py", TEST, "tests/unit/test_quick_scan_feedback_owner.py",
         "tests/unit/test_quick_scan_work_store.py", "tests/unit/test_quick_scan_budget.py"]
CASES = {
    "bad_pack_size": ["--question-pack-size", "0"],
    "missing_batch_file": ["--batch", "absent.txt"],
    "missing_entity": ["--company", "Synthetic", "--require-search"],
}


def snapshot(repo, destination, revision, working):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo)

    commit = git("rev-parse", "--verify", "--end-of-options",
                 ("HEAD" if working else revision) + "^{commit}").decode().strip()
    if working:
        for name in git("ls-files", "-coz", "--exclude-standard", "--", *SCOPE).split(b"\0"):
            if name:
                source = repo / os.fsdecode(name)
                if source.is_file():
                    target = destination / source.relative_to(repo)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    else:
        with zipfile.ZipFile(io.BytesIO(git("archive", "--format=zip", commit, *SCOPE))) as archive:
            archive.extractall(destination)
    return commit


def isolated_environment(root):
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATHEXT",
    }}
    env.update({k: str(root) for k in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                                        "TEMP", "TMP", "TMPDIR", "XDG_STATE_HOME")})
    env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHON_DOTENV_DISABLED="1")
    (root / "sitecustomize.py").write_text(
        "import sys\ndef offline(event, args):\n"
        "    if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):\n"
        "        raise RuntimeError('offline StockQA failure probe')\n"
        "sys.addaudithook(offline)\n", encoding="ascii")
    return env


def measure(name, args, root, source, env):
    case = root / name
    case.mkdir()
    sidecar = case / "events.jsonl"
    ids = dict(RESEARCH_FEEDBACK_OUT=str(sidecar), RESEARCH_FEEDBACK_RUN_ID=name,
               RESEARCH_FEEDBACK_ATTEMPT_ID="attempt-one")
    business = subprocess.run([*PYTHON, str(source / "main_with_llm.py"), *args,
                               "--output", str(case / "result.json")], cwd=case, env={**env, **ids},
                              capture_output=True, timeout=45)
    read = subprocess.check_output([*PYTHON, "-m", "tools.feedback_loop", "plan", str(sidecar)],
                                   cwd=CWP, env=env, timeout=30)
    cold = json.loads(read)
    console = (business.stdout + business.stderr).decode("utf8", "replace")
    native = "".join(path.read_text(encoding="utf8") for path in (case / "logs").glob("*.log"))
    # Confirm we actually reached the selected business branch, rather than
    # counting an absent interpreter/dependency as the intended failure.
    marker = {"bad_pack_size": "--question-pack-size", "missing_batch_file": "absent.txt",
              "missing_entity": "--entity-id"}[name]
    reached = business.returncode != 0 and marker in (console + native)
    return {"case": name, "exit": business.returncode, "reached": reached,
            "native_log_bytes": len(native.encode("utf8")), "native_traceback": "Traceback" in native,
            "checks": [[row["check_id"], row["actual"], row["disposition"]]
                       for row in cold["observations"]],
            "readback_diagnostics": [row["code"] for row in cold["diagnostics"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, nargs="?", default=CWP.parent / "StockQAbyLLM")
    versions = parser.add_mutually_exclusive_group()
    versions.add_argument("--revision", default=BASELINE)
    versions.add_argument("--working-tree", action="store_true")
    args = parser.parse_args()
    short = CWP / ".tmp"
    with tempfile.TemporaryDirectory(prefix="f4qa-", dir=short if short.is_dir() else None) as tmp:
        root = Path(tmp)
        source = root / "source"
        commit = snapshot(args.checkout.resolve(), source, args.revision, args.working_tree)
        env = isolated_environment(root)
        results = [measure(name, argv, root, source, env) for name, argv in CASES.items()]
        ini = root / "pytest.ini"
        ini.write_text("[pytest]\n", encoding="ascii")
        controls = subprocess.run([*PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   "-c", str(ini), "--basetemp", str(root / "control"),
                                   "tests/unit/test_quick_scan_feedback_owner.py",
                                   TEST + "::test_unknown_send_is_reported_as_send_unknown_not_as_settled",
                                   TEST + "::test_blocked_outbox_is_reported_without_blaming_the_settlement"],
                                  cwd=source, env=env, capture_output=True, timeout=240)
        summary = controls.stdout.decode("utf8", "replace").splitlines()
        print(json.dumps({"commit": commit, "working_tree": args.working_tree, "cases": results,
                          "controls_exit": controls.returncode,
                          "controls_summary": summary[-1] if summary else None}, indent=2))
        return int(bool(controls.returncode) or not all(case["reached"] for case in results))


if __name__ == "__main__":
    raise SystemExit(main())
