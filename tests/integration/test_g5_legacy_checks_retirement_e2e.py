"""G5-CWP-CHECKS end-to-end: the six real retired scripts against a sentinel cwd.

The sentinel root stands in for a working tree that still holds production
material.  Every retired entry is launched for real — direct invocation, with
and without ``python -S``, ``import`` and ``main()`` — and must report
``LEGACY_ENGINEERING_TOOL_RETIRED`` / exit 78 without touching a byte, copying
a candidate tree, opening a socket or constructing a model/Store/downloader.
The isolation counterexample runs in a subprocess with fake keys only; no
test changes the user's real LLM configuration.
"""

from __future__ import annotations

import hashlib
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
    ],
    "gold_gate.py": [
        "--corpus",
        "corpus",
        "--perfect",
        "--receipt",
        "r.json",
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

SENTINEL_FILES: dict[str, str] = {
    ".env": (
        "DEEPSEEK_API_KEY=fake-deepseek-sentinel\n"
        "MINIMAX_API_KEY=fake-minimax-sentinel\n"
    ),
    "log.md": "# sentinel log\n",
    "config.yaml": "sentinel: true\n",
    "companies/样例公司/raw/sentinel.md": "原始资料哨兵\n",
    "sectors/半导体设备/wiki/sentinel.md": "行业哨兵\n",
    "artifacts/gates/existing-receipt.json": '{"sentinel": true}\n',
    "docs/sentinel.md": "文档哨兵\n",
}

BLOCKED_PROJECT_MODULES = sorted(
    {
        "company_wiki",
        "common",
        "config",
        "graph",
        "llm_client",
        "writer_policy",
        "sitecustomize",
        "helpers",
        "support",
        "yaml",
        "requests",
        "openai",
        "dotenv",
        "numpy",
        "pandas",
        "pytest",
    }
)

REMOVED_GATE_API = [
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
]


@pytest.fixture()
def sentinel_root(tmp_path: Path) -> Path:
    for relative, content in SENTINEL_FILES.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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
            "PYTHON_DOTENV_DISABLED": "1",
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
        timeout=90,
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


def _assert_no_candidate_tree(root: Path) -> None:
    for relative in ("candidate", "candidate-manifest.json", "scripts", ".gate-venv"):
        assert not (root / relative).exists(), relative
    assert not (root / "r.json").exists()
    assert not (root / "receipt.json").exists()


@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
@pytest.mark.parametrize("script", RETIRED)
def test_real_script_leaves_the_sentinel_cwd_untouched(
    script: str, mode: str, sentinel_root: Path
) -> None:
    before = _snapshot(sentinel_root)
    args = [sys.executable]
    if mode == "nosite":
        args.append("-S")
    args.append(str(SCRIPTS / script))
    args.extend(LEGACY_ARGS[script])

    completed = _run(args, sentinel_root)

    _assert_retired(completed, script)
    assert _snapshot(sentinel_root) == before, script
    _assert_no_candidate_tree(sentinel_root)


@pytest.mark.parametrize("script", RETIRED)
def test_real_script_help_is_retired_too(script: str, sentinel_root: Path) -> None:
    before = _snapshot(sentinel_root)
    completed = _run(
        [sys.executable, "-S", str(SCRIPTS / script), "--help"], sentinel_root
    )

    _assert_retired(completed, script)
    assert "usage:" not in completed.stdout, completed.stdout
    assert _snapshot(sentinel_root) == before, script


TRAP_HARNESS = r"""
import importlib
import importlib.abc
import json
import os
import pathlib
import shutil
import socket
import sys
import urllib.request

scripts_dir = sys.argv[1]
cwd = sys.argv[2]
argv_by_script = json.loads(sys.argv[3])
scripts = json.loads(sys.argv[4])
blocked = json.loads(sys.argv[5])
api_list = json.loads(sys.argv[6])
sys.path.insert(0, scripts_dir)


class ProjectDependencyBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in blocked:
            raise ImportError("blocked project dependency: " + fullname)
        return None


sys.meta_path.insert(0, ProjectDependencyBlocker())

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

os.chdir(cwd)


def _snapshot(root):
    result = {}
    for base, _, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                result[os.path.relpath(path, root)] = handle.read()
    return result


before = sorted(_snapshot(cwd))
report = {}
for script in scripts:
    module_name = script[:-3]
    sys.modules.pop(module_name, None)
    try:
        module = importlib.import_module(module_name)
    except BaseException as exc:
        report[script] = {"error": "%s: %s" % (type(exc).__name__, exc)}
        continue
    leaked = [api for api in api_list if hasattr(module, api)]
    sys.argv = [script] + list(argv_by_script[script])
    try:
        code = module.main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException as exc:
        report[script] = {
            "error": "%s: %s" % (type(exc).__name__, exc),
            "leaked": leaked,
        }
        continue
    report[script] = {"code": code, "leaked": leaked}
after = sorted(_snapshot(cwd))
print(
    json.dumps({"report": report, "traps": traps, "before": before, "after": after},
               ensure_ascii=False),
    flush=True,
)
"""


def test_import_and_main_never_touch_the_sentinel_cwd(sentinel_root: Path) -> None:
    harness = sentinel_root / "_g5_e2e_harness.py"
    harness.write_text(TRAP_HARNESS, encoding="utf-8")
    before = _snapshot(sentinel_root)

    completed = _run(
        [
            sys.executable,
            "-B",
            str(harness),
            str(SCRIPTS),
            str(sentinel_root),
            json.dumps(LEGACY_ARGS, ensure_ascii=False),
            json.dumps(list(RETIRED)),
            json.dumps(BLOCKED_PROJECT_MODULES),
            json.dumps(REMOVED_GATE_API),
        ],
        sentinel_root,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout.strip().splitlines()[-1])

    assert report["traps"] == [], report["traps"]
    assert report["before"] == report["after"], report
    for script in RETIRED:
        entry = report["report"][script]
        assert "error" not in entry, (script, entry)
        assert entry["code"] == BLOCKED_EXIT_CODE, (script, entry)
        assert entry["leaked"] == [], (script, entry)
    assert MARKER in completed.stdout, completed.stdout
    assert _snapshot(sentinel_root) == before, "sentinel cwd changed"
    _assert_no_candidate_tree(sentinel_root)


def test_isolation_helper_subprocess_counterexample_uses_only_fake_keys() -> None:
    from support.isolated_environment import sanitized_environment

    child_environment = sanitized_environment()
    child_environment.update(
        {
            "DEEPSEEK_API_KEY": "fake-deepseek-counterexample",
            "CUSTOM_API_KEY": "fake-custom-counterexample",
            "PYTHONPATH": str(TESTS),
        }
    )
    code = (
        "from support.isolated_environment import sanitized_environment as s; "
        "env = s(); "
        "print(int('DEEPSEEK_API_KEY' in env), int('CUSTOM_API_KEY' in env), "
        "env['PYTHON_DOTENV_DISABLED'], env['COMPANY_WIKI_NETWORK'], "
        "env['COMPANY_WIKI_REAL_LLM'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=child_environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0 0 1 blocked 0"


def test_retired_scripts_never_copy_the_source_tree(sentinel_root: Path) -> None:
    before = _snapshot(sentinel_root)
    completed = _run(
        [
            sys.executable,
            "-S",
            str(SCRIPTS / "clean_env_gate.py"),
            "--source",
            str(ROOT),
            "--candidate",
            str(sentinel_root / "candidate"),
            "--receipt",
            str(sentinel_root / "r.json"),
        ],
        sentinel_root,
    )
    _assert_retired(completed, "clean_env_gate.py")
    assert _snapshot(sentinel_root) == before
    assert not (sentinel_root / "candidate").exists()
    assert not (sentinel_root / "candidate-manifest.json").exists()
