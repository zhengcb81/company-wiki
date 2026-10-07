"""G5-CWP-CHECKS: the six legacy engineering gate/batch shells are retired.

Behaviour contract written before the implementation change:

* direct invocation of every retired CLI — legacy arguments and ``--help``,
  with and without ``python -S`` — reports ``LEGACY_ENGINEERING_TOOL_RETIRED``
  and exits 78 from an empty cwd, creating no file and opening no socket;
* importing any of them with the project dependency stack blocked still
  succeeds and initialises nothing;
* ``main()`` reports retirement without copying a tree, writing a receipt or
  constructing a model/Store/downloader;
* ``writer_policy`` classifies exactly these six names in their own retirement
  category and its banner carries the same marker;
* the migrated isolation helper still strips fake keys and disables dotenv
  without ever reading real credentials.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import writer_policy  # noqa: E402

RETIRED = (
    "architecture_gate.py",
    "batch_process.py",
    "clean_env_gate.py",
    "gold_gate.py",
    "semantic_gate.py",
    "test_framework.py",
)
MARKER = "LEGACY_ENGINEERING_TOOL_RETIRED"
BLOCKED_EXIT_CODE = 78

# Every argument spelling the old CLIs used to accept.  None of them may reach
# argparse: the retirement shell answers before it looks at argv.
LEGACY_ARGS: dict[str, list[str]] = {
    "architecture_gate.py": [
        "--root",
        ".",
        "--config",
        "control/architecture.json",
        "--receipt",
        "r.json",
    ],
    "batch_process.py": ["--tier", "1", "--limit", "5", "--dry-run"],
    "clean_env_gate.py": [
        "--source",
        ".",
        "--candidate",
        "candidate",
        "--receipt",
        "r.json",
        "--command-json",
        "[]",
        "--timeout-s",
        "1",
    ],
    "gold_gate.py": [
        "--corpus",
        "corpus",
        "--predictions",
        "pred.json",
        "--receipt",
        "r.json",
        "--as-of",
        "2026-01-01",
    ],
    "semantic_gate.py": [
        "--gold-root",
        "gold",
        "--min-sources",
        "30",
        "--receipt",
        "r.json",
    ],
    "test_framework.py": ["--suite", "all", "--company", "样例公司", "--report"],
}

# Modules the retired shells must never reach: the project package, the
# scripts-local helper layer, the model client and every third-party runtime.
BLOCKED_PROJECT_MODULES = frozenset(
    {
        "company_wiki",
        "common",
        "config",
        "graph",
        "llm_client",
        "writer_policy",
        "sitecustomize",
        "helpers",
        "yaml",
        "requests",
        "openai",
        "dotenv",
        "numpy",
        "pandas",
        "pytest",
    }
)

REMOVED_GATE_API = (
    "evaluate_gold_integrity",
    "evaluate_architecture",
    "materialize_candidate",
    "is_candidate_path",
    "sanitized_environment",
    "run_clean_gate",
    "load_gold",
    "evaluate",
    "_write_receipt",
    "run_unit_tests",
    "process_company",
    "get_companies_by_tier",
)


def _child_environment(**extra: str) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith("_API_KEY")
    }
    environment.pop("PYTHONPATH", None)
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONDOTENV_DISABLED": "1",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
        }
    )
    environment.update(extra)
    return environment


def _run(args: list[str], cwd: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=_child_environment(**extra),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def _assert_retired(completed: subprocess.CompletedProcess[str], script: str) -> None:
    assert completed.returncode == BLOCKED_EXIT_CODE, (
        script,
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    assert MARKER in completed.stdout, (script, completed.stdout)
    assert "unrecognized arguments" not in completed.stderr, completed.stderr
    assert "usage:" not in completed.stdout, completed.stdout


# ── direct invocation ──────────────────────────────────────────────────────


@pytest.mark.parametrize("argv_kind", ["legacy", "help"])
@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
@pytest.mark.parametrize("script", RETIRED)
def test_retired_cli_reports_marker_from_an_empty_cwd(
    script: str, mode: str, argv_kind: str, tmp_path: Path
) -> None:
    argv = ["--help"] if argv_kind == "help" else LEGACY_ARGS[script]
    args = [sys.executable]
    if mode == "nosite":
        args.append("-S")
    args.append(str(SCRIPTS / script))
    args.extend(argv)

    before = sorted(path.name for path in tmp_path.iterdir())
    completed = _run(args, tmp_path)
    after = sorted(path.name for path in tmp_path.iterdir())

    _assert_retired(completed, script)
    assert after == before, (script, before, after)


TRAP_HARNESS = r"""
import importlib.util
import os
import pathlib
import runpy
import shutil
import socket
import sys
import urllib.request

script, mode = sys.argv[1], sys.argv[2]
argv = sys.argv[3:]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))

traps = []


class Trap(RuntimeError):
    pass


def _net(*args, **kwargs):
    traps.append("net")
    raise Trap("net")


socket.socket.connect = _net
socket.create_connection = _net
urllib.request.urlopen = _net


def _blocked(name):
    def inner(*args, **kwargs):
        traps.append(name)
        raise Trap(name)

    return inner


for _name in ("write_text", "write_bytes", "mkdir", "unlink", "touch"):
    setattr(pathlib.Path, _name, _blocked("Path." + _name))
for _name in ("replace", "rename", "remove", "unlink", "mkdir", "rmdir"):
    setattr(os, _name, _blocked("os." + _name))
for _name in ("move", "copy", "copytree", "rmtree"):
    setattr(shutil, _name, _blocked("shutil." + _name))

sys.argv = [script] + argv
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException as exc:
    print("G5-ERROR %s: %s" % (type(exc).__name__, exc), flush=True)
    raise SystemExit(97)
else:
    code = 0
print("G5-TRAPS %s" % (traps,), flush=True)
print("G5-EXIT %s" % code, flush=True)
raise SystemExit(code)
"""


@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
@pytest.mark.parametrize("script", RETIRED)
def test_retired_cli_never_writes_or_opens_the_network(
    script: str, mode: str, tmp_path: Path
) -> None:
    harness = tmp_path / "g5_trap_harness.py"
    harness.write_text(TRAP_HARNESS, encoding="utf-8")
    args = [sys.executable, "-B"]
    if mode == "nosite":
        args.append("-S")
    args.extend((str(harness), str(SCRIPTS / script), mode, *LEGACY_ARGS[script]))

    completed = _run(args, tmp_path)
    stdout = completed.stdout

    _assert_retired(completed, script)
    assert "G5-ERROR" not in stdout, stdout
    assert "G5-TRAPS []" in stdout, stdout
    assert "G5-EXIT 78" in stdout, stdout
    assert sorted(path.name for path in tmp_path.iterdir()) == [harness.name]


# ── import / main ──────────────────────────────────────────────────────────


IMPORT_HARNESS = r"""
import importlib
import importlib.abc
import json
import os
import sys

scripts_dir = sys.argv[1]
modules = json.loads(sys.argv[2])
blocked = json.loads(sys.argv[3])
cwd = sys.argv[4]

sys.path.insert(0, scripts_dir)


class ProjectDependencyBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in blocked:
            raise ImportError("blocked project dependency: " + fullname)
        return None


sys.meta_path.insert(0, ProjectDependencyBlocker())

before = sorted(os.listdir(cwd))
imported = []
leaked = []
for name in modules:
    sys.modules.pop(name, None)
    module = importlib.import_module(name)
    imported.append(module.__name__)
    for api in json.loads(sys.argv[5]):
        if hasattr(module, api):
            leaked.append(module.__name__ + "." + api)
after = sorted(os.listdir(cwd))

print(
    json.dumps(
        {
            "imported": imported,
            "leaked": leaked,
            "files_before": before,
            "files_after": after,
        }
    ),
    flush=True,
)
"""


def test_import_succeeds_with_project_dependencies_blocked(tmp_path: Path) -> None:
    module_names = [name[: -len(".py")] for name in RETIRED]
    completed = _run(
        [
            sys.executable,
            "-c",
            IMPORT_HARNESS,
            str(SCRIPTS),
            json.dumps(module_names),
            json.dumps(sorted(BLOCKED_PROJECT_MODULES)),
            str(tmp_path),
            json.dumps(REMOVED_GATE_API),
        ],
        tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert sorted(report["imported"]) == sorted(module_names)
    assert report["leaked"] == [], report["leaked"]
    assert report["files_before"] == []
    assert report["files_after"] == []


MAIN_HARNESS = r"""
import importlib
import json
import os
import pathlib
import shutil
import socket
import sys
import urllib.request

scripts_dir, module_name = sys.argv[1], sys.argv[2]
cwd = sys.argv[3]
sys.path.insert(0, scripts_dir)

traps = []


class Trap(RuntimeError):
    pass


def _net(*args, **kwargs):
    traps.append("net")
    raise Trap("net")


socket.socket.connect = _net
socket.create_connection = _net
urllib.request.urlopen = _net


def _blocked(name):
    def inner(*args, **kwargs):
        traps.append(name)
        raise Trap(name)

    return inner


for _name in ("write_text", "write_bytes", "mkdir", "unlink", "touch"):
    setattr(pathlib.Path, _name, _blocked("Path." + _name))
for _name in ("replace", "rename", "remove", "unlink", "mkdir", "rmdir"):
    setattr(os, _name, _blocked("os." + _name))
for _name in ("move", "copy", "copytree", "rmtree"):
    setattr(shutil, _name, _blocked("shutil." + _name))

module = importlib.import_module(module_name)
before = sorted(os.listdir(cwd))
code = module.main()
after = sorted(os.listdir(cwd))
print(
    json.dumps({"code": code, "traps": traps, "before": before, "after": after}),
    flush=True,
)
"""


@pytest.mark.parametrize("script", RETIRED)
def test_main_reports_retirement_with_zero_initialisation(
    script: str, tmp_path: Path
) -> None:
    harness = tmp_path / "g5_main_harness.py"
    harness.write_text(MAIN_HARNESS, encoding="utf-8")
    completed = _run(
        [
            sys.executable,
            "-B",
            str(harness),
            str(SCRIPTS),
            script[: -len(".py")],
            str(tmp_path),
        ],
        tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report["code"] == BLOCKED_EXIT_CODE, report
    assert report["traps"] == [], report
    assert report["after"] == report["before"], report
    assert MARKER in completed.stdout, completed.stdout


# ── writer_policy classification ───────────────────────────────────────────


def test_writer_policy_gives_the_six_names_their_own_retirement_category() -> None:
    category = getattr(writer_policy, "RETIRED_ENGINEERING_TOOL_SCRIPTS", None)
    assert category is not None
    assert set(category) == set(RETIRED)
    assert not category & writer_policy.CONTROL_TOOL_ALLOWLIST
    assert not category & writer_policy.SOURCE_WORKFLOW_TOOL_ALLOWLIST


@pytest.mark.parametrize("script", RETIRED)
def test_retired_engineering_tool_is_never_allowed(script: str) -> None:
    environments = (
        {},
        {"COMPANY_WIKI_WRITE_MODE": "legacy", "COMPANY_WIKI_LEGACY_WRITERS": "allow"},
        {"COMPANY_WIKI_WRITE_MODE": "off", "COMPANY_WIKI_LEGACY_WRITERS": "deny"},
    )
    for environment in environments:
        assert (
            writer_policy.legacy_script_execution_allowed(script, environment) is False
        )
    assert writer_policy.is_legacy_script_cli(SCRIPTS / script) is True
    banner = writer_policy.blocked_message(script)
    assert MARKER in banner, banner


def test_writer_policy_still_freezes_the_research_writer_inventory() -> None:
    assert "batch_process.py" in writer_policy.PERMANENTLY_RETIRED_SCRIPTS
    assert writer_policy.BLOCKED_EXIT_CODE == BLOCKED_EXIT_CODE


# ── migrated isolation helper ──────────────────────────────────────────────


def test_isolated_environment_strips_fake_keys_and_disables_dotenv(
    monkeypatch,
) -> None:
    from support.isolated_environment import sanitized_environment

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek")
    monkeypatch.setenv("CUSTOM_API_KEY", "fake-custom")
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")

    environment = sanitized_environment()

    assert "DEEPSEEK_API_KEY" not in environment
    assert "CUSTOM_API_KEY" not in environment
    assert "COMPANY_WIKI_WRITE_MODE" not in environment
    assert "COMPANY_WIKI_LEGACY_WRITERS" not in environment
    assert environment["PYTHON_DOTENV_DISABLED"] == "1"
    assert environment["COMPANY_WIKI_NETWORK"] == "blocked"
    assert environment["COMPANY_WIKI_REAL_LLM"] == "0"
    assert environment["PIP_NO_INDEX"] == "1"
    for key, value in environment.items():
        if key.upper().endswith("_API_KEY"):
            assert value != "fake-deepseek", key


def test_isolated_environment_never_reads_repository_credentials() -> None:
    from support.isolated_environment import sanitized_environment

    environment = sanitized_environment()
    for key in list(environment):
        if key.upper().endswith("_API_KEY"):
            raise AssertionError(f"API key survived sanitisation: {key}")
    assert environment["PYTHON_DOTENV_DISABLED"] == "1"


# ── control/ directory ─────────────────────────────────────────────────────


def test_control_architecture_rules_config_has_no_surviving_consumer() -> None:
    assert not (ROOT / "control" / "architecture.json").exists()
    assert (ROOT / "control" / "README.md").is_file()
