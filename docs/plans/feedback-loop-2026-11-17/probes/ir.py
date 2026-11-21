"""Offline IR failure census. Pass the industry-research checkout and optionally a skill directory."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CWP = Path(__file__).resolve().parents[4]
PY = [sys.executable, "-B", "-X", "utf8"]
WINDOWS_ENV = ("PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "PATHEXT", "TEMP", "TMP")


def inspect(sidecar, artifact):
    result = subprocess.run([*PY, "-m", "tools.feedback_loop", "plan", str(sidecar)],
                            cwd=CWP, capture_output=True, timeout=15, check=True)
    plan = json.loads(result.stdout)
    outcome = {"observations": dict(Counter(row["disposition"] for row in plan["observations"])),
               "checks": [row["check_id"] for row in plan["observations"]],
               "diagnostics": [row["code"] for row in plan["diagnostics"]]}
    if artifact.is_file():
        if artifact.suffix == ".json":
            data = json.loads(artifact.read_text(encoding="utf8"))
            outcome["native_status"] = data.get("status", data.get("availability"))
            outcome["native_reason"] = data.get("error_code")
        else:
            lines = artifact.read_text(encoding="utf8").splitlines()
            outcome["report_sources"] = next((line for line in lines if line.startswith("sources_count:")), None)
    return outcome


def census(repo, installed, home):
    work = Path(home).resolve()
    owner = work / "stub-owner"
    iqs = work / "stub-iqs"
    fake = work / "transport"
    for path in (owner, iqs, fake):
        path.mkdir()
    # The subprocess fixture is the only importable StockWiki. It sends no data.
    package = fake / "stockwiki"
    package.mkdir()
    (package / "__init__.py").touch()
    (package / "quick_scan_query_v2_cli.py").write_text(
        "import sys\nprint('controlled-owner-offline', file=sys.stderr)\nraise SystemExit(43)\n", encoding="utf8")
    (fake / "requests.py").write_text(
        "from types import SimpleNamespace\nfrom pathlib import Path\n"
        "exceptions = SimpleNamespace(Timeout=TimeoutError, RequestException=OSError)\n"
        "def post(*args, **kwargs):\n    Path('http-stub-only').touch()\n"
        "    return SimpleNamespace(status_code=401)\n", encoding="utf8")
    env = {key: os.environ[key] for key in WINDOWS_ENV if key in os.environ}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(fake),
               DEEPSEEK_API_KEY="local-test-fixture", IR_FEEDBACK_WORK_ROOT=str(work))
    config = work / "quick.json"
    config.write_text(json.dumps({"owner_root": str(owner), "iqs_code_root": str(iqs),
        "capture_root": str(work / "captures"), "python_executable": sys.executable}), encoding="utf8")
    invalid = work / "broken.json"
    invalid.write_text("{", encoding="utf8")
    (work / "input.md").write_text("offline synthetic input", encoding="utf8")
    # The historical report generator looks for a config relative to its cwd.
    (work / "config.yaml").write_text("fixture:\n", encoding="utf8")
    runs = []

    def cold_read(sidecar, output):
        done = subprocess.run([*PY, str(Path(__file__).resolve()), "--cold", str(sidecar), str(output)],
                              env=env, cwd=work, capture_output=True, check=True, timeout=15)
        return json.loads(done.stdout)

    def exercise(name, source, argv, artifact=None):
        output = artifact or work / (name + ".json")
        sidecar = work / (name + ".jsonl")
        scoped = dict(env, RESEARCH_FEEDBACK_OUT=str(sidecar), RESEARCH_FEEDBACK_RUN_ID=name,
                      RESEARCH_FEEDBACK_ATTEMPT_ID="1")
        p = subprocess.run([*PY, str(source), *map(str, argv), "--output", str(output)],
                           cwd=work, env=scoped, capture_output=True, timeout=15)
        runs.append({"case": name, "exit": p.returncode, **cold_read(sidecar, output)})

    quick = repo / "tools/quick_scan_client.py"
    selector = ["--entity-id", "ent-sample", "--field-id", "fact_business_segment",
                "--mode", "explore", "--label", "synthetic"]
    for action in ("collect", "export", "capabilities"):
        exercise("owner-offline-" + action, quick, ["--config", config, action,
                 *(selector if action != "capabilities" else [])])
    exercise("config-malformed", quick, ["--config", invalid, "collect", *selector])
    exercise("summary-malformed", quick, ["--config", config, "summarize", "--input", invalid])
    exercise("render-source-missing", quick, ["--config", config, "render-section", "--input", "absent.json"])
    report_args = ["--sector", "Fixture", "--framework", "absent.json", "--questions", "absent.json",
                   "--companies", "absent.json"]
    exercise("repo-report-missing", repo / "tools/report_generator.py", report_args, work / "repo.md")
    exercise("repo-model-401", repo / "tools/deepseek_client.py",
             ["--mode", "extract_framework", "--sector", "Fixture", "--input", "input.md"])
    if installed:
        exercise("skill-report-missing", installed / "tools/report_generator.py", report_args, work / "installed.md")
        exercise("skill-model-401", installed / "tools/deepseek_client.py",
                 ["--mode", "extract_framework", "--sector", "Fixture", "--input", "input.md"])
    positive = work / "known-bad-report"
    p = subprocess.run([*PY, str(repo / "tests/test_feedback_owner.py"), "--fixture-root", str(positive)],
                       env=env, cwd=work, capture_output=True, check=True, timeout=20)
    example = json.loads(p.stdout)
    runs.append({"case": "known-stale-section", "exit": p.returncode,
                 **cold_read(Path(example["sidecar"]), positive / "audit.json")})
    assert (work / "http-stub-only").is_file(), "HTTP fixture was not invoked"
    return runs


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--cold":
        print(json.dumps(inspect(Path(sys.argv[2]), Path(sys.argv[3]))))
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("installed", type=Path, nargs="?")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="ir-f4-") as home:
        print(json.dumps(census(args.repo.resolve(), args.installed.resolve() if args.installed else None, home),
                         ensure_ascii=True, indent=2))
