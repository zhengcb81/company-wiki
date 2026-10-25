"""Independent classifier/range/dispatch probes; no pytest child or network."""
from pathlib import Path
from unittest.mock import patch
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())))
from tools import pre_push_gate as gate
from tools.changed_unit_tests import changed_paths, select_unit_tests

HERE = Path(__file__).resolve().parent
PRODUCT = ("tools/pre_push_gate.py", "tools/changed_unit_tests.py", "tests/unit/test_daily_push_policy.py", "tests/unit/test_ci_push_selection.py")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if len(sys.argv) != 2 or not sys.argv[1].replace("-", "").isalnum():
        raise SystemExit("usage: independent_probe.py NEW-REPORT-STEM")
    output = HERE / (sys.argv[1] + ".json")
    if output.exists():
        raise FileExistsError(output)
    actual_root = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
    before = {p: sha(actual_root / p) for p in PRODUCT}
    scratch = Path(tempfile.mkdtemp(prefix="owned-git-", dir=HERE)).resolve()
    env = dict(os.environ)
    for name in gate.GIT_REPOSITORY_CONTEXT:
        env.pop(name, None)
    commands = []
    def git(*args):
        result = subprocess.run(["git", *args], cwd=scratch, env=env, capture_output=True,
                                text=True, encoding="utf8", errors="replace", timeout=20)
        commands.append({"args": list(args), "exit_code": result.returncode})
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()
    def write(name, text):
        path = scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf8")
    def observe(push_input, args=None):
        dispatched = []
        def runner(command, label, env_extra=None):
            dispatched.append({"command": command, "label": label})
            return 7 if args is None else 0
        stream = io.StringIO()
        with patch.object(gate, "PROJECT_ROOT", scratch), patch.object(gate.sys, "stdin", io.StringIO(push_input)), patch.object(gate, "_dispatch_gate", runner), contextlib.redirect_stdout(stream):
            code = gate.main(["--push-checks"] if args is None else args)
        return {"exit_code": code, "dispatches": dispatched, "stdout": stream.getvalue()}
    try:
        git("init", "-q", "-b", "master")
        git("config", "user.name", "Independent Review Fixture")
        git("config", "user.email", "independent@example.invalid")
        git("config", "commit.gpgsign", "false")
        hooks = scratch / "empty-hooks"
        hooks.mkdir()
        git("config", "core.hooksPath", str(hooks))
        write("src/pkg/__init__.py", "")
        write("src/pkg/core.py", "value=1\n")
        write("tests/unit/test_core.py", "from pkg import core\ndef test_core(): assert core.value == 1\n")
        write("config.yaml", "value: 1\n")
        git("add", "src", "tests", "config.yaml")
        git("commit", "-qm", "neutral baseline")
        old = git("rev-parse", "HEAD")
        write("docs/plans/fixture/probe.py", "raise RuntimeError('archived only')\n")
        git("add", "docs")
        git("commit", "-qm", "archive only")
        docs_head = git("rev-parse", "HEAD")
        docs_input = f"refs/heads/master {docs_head} refs/heads/master {old}\n"
        docs_paths = changed_paths(scratch, docs_input)
        docs_result = observe(docs_input)
        write("src/pkg/core.py", "value=2\n")
        git("add", "src/pkg/core.py")
        git("commit", "-qm", "earlier code")
        write("docs/plans/fixture/probe.py", "# latest commit only touches archive\n")
        git("add", "docs")
        git("commit", "-qm", "last docs")
        final_head = git("rev-parse", "HEAD")
        mixed_input = f"refs/heads/master {final_head} refs/heads/master {docs_head}\n"
        mixed_paths = changed_paths(scratch, mixed_input)
        mixed_result = observe(mixed_input)
        classifier = []
        for name, changes, should_skip in (
            ("archive-py", {"docs/plans/fixture/probe.py"}, True),
            ("root-doc", {"README.md"}, True),
            ("root-runtime-config", {"config.yaml"}, False),
            ("docs-plus-runtime-config", {"README.md", "config.yaml"}, False),
            ("unknown-root-command", {"startup.ps1"}, False),
            ("unknown-resource", {"misc/runtime.json"}, False),
            ("configured-provider", {"config/models.yaml"}, False),
            ("unknown-range", None, False),
        ):
            selected, reason = select_unit_tests(scratch, changes)
            targets, _ = gate._push_targets(selected)
            classifier.append({"name": name, "changes": sorted(changes) if changes is not None else None,
                               "selected": selected, "reason": reason, "targets": targets,
                               "expected_skip": should_skip, "pass": (not targets) == should_skip})
        unknown = observe("")
        ci = observe("", ["--fast-contracts-only"])
        full = observe("", [])
        checks = {"docs_real_git_paths": docs_paths == {"docs/plans/fixture/probe.py"},
                  "docs_no_dispatch_and_honest": docs_result["exit_code"] == 0 and not docs_result["dispatches"] and "tests_not_run" in docs_result["stdout"] and "local_fast_pass" not in docs_result["stdout"] and "GREEN" not in docs_result["stdout"],
                  "entire_range_includes_earlier_code": mixed_paths == {"src/pkg/core.py", "docs/plans/fixture/probe.py"},
                  "mixed_dispatch_failure_not_skipped": mixed_result["exit_code"] == 7 and len(mixed_result["dispatches"]) == 1 and "tests/unit/test_core.py" in mixed_result["dispatches"][0]["command"],
                  "unknown_dispatches_existing_smoke": unknown["exit_code"] == 7 and len(unknown["dispatches"]) == 1,
                  "ci_still_dispatches_smoke": len(ci["dispatches"]) == 1 and ci["exit_code"] == 0,
                  "full_mode_still_all_six_stages": len(full["dispatches"]) == 6 and full["exit_code"] == 0,
                  "all_classifier_boundaries": all(x["pass"] for x in classifier)}
        result = {"schema_version": "docs-only-push-independent-probes/1", "checks": checks,
                  "classifier": classifier, "docs_real_range": {"paths": sorted(docs_paths), **docs_result},
                  "mixed_real_range": {"paths": sorted(mixed_paths), **mixed_result}, "unknown": unknown,
                  "ci": ci, "full": full, "git_commands": commands,
                  "scope": "Real local Git commit ranges and actual classifier/gate dispatch; runner intentionally intercepted. ROOT owns real hook/pytest push E2E.",
                  "external_calls": 0, "pytest_children": 0}
    finally:
        if scratch.parent != HERE.resolve() or not scratch.name.startswith("owned-git-"):
            raise RuntimeError("unexpected cleanup target")
        def clear_readonly(function, path, exc):
            if not isinstance(exc, PermissionError):
                raise exc
            Path(path).chmod(stat.S_IREAD | stat.S_IWRITE)
            function(path)
        shutil.rmtree(scratch, onexc=clear_readonly)
    after = {p: sha(actual_root / p) for p in PRODUCT}
    result["source_sha256"] = before
    result["source_stable"] = before == after
    result["owned_git_root_restored_absent"] = not scratch.exists()
    with output.open("x", encoding="utf8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"checks": result["checks"], "failed_classifier_cases": [x["name"] for x in classifier if not x["pass"]], "source_stable": before == after, "scratch_restored": not scratch.exists()}, ensure_ascii=False))
    return 0 if all(result["checks"].values()) and before == after and not scratch.exists() else 1

if __name__ == "__main__":
    raise SystemExit(main())
