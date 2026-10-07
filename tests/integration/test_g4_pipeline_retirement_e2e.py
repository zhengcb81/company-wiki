"""G4-CWP-PIPELINE integration + E2E: retired entry, zero side effects.

A real child process runs the retired ``scripts/full_pipeline.py`` stub from
an isolated ``cw4p-<random>`` root under the system TEMP directory that holds
a sentinel original file, a small SQLite database, a config file, and a
directory snapshot taken before the run.  Both a trap harness (config /
network / model / subprocess / write traps) and the plain direct process
(including the card's exact ``python -S`` command) must exit 78 with the
retirement markers while leaving source bytes, database schema/rows, and the
directory state byte-identical.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
STUB = SCRIPTS / "full_pipeline.py"

EXIT_CODE = 78
BLOCKED_TAG = "LEGACY WRITER BLOCKED"
RETIRED_TAG = "LEGACY_PIPELINE_RETIRED"

OLD_AUTH_ENV: dict[str, str] = {
    "COMPANY_WIKI_WRITE_MODE": "legacy",
    "COMPANY_WIKI_LEGACY_WRITERS": "allow",
}

CARD_ARGS = ("--company", "示例", "--stage", "review", "--no-gates")

SENTINEL_BYTES = "G4 sentinel 原件 sentinel 原件 sentinel\n".encode("utf-8")
CONFIG_BYTES = "stage: shadow\nsource: sentinel\n".encode("utf-8")


HARNESS_SOURCE = r"""
import builtins
import os
import runpy
import socket
import sys
import urllib.request

script = sys.argv[1]
sys.argv = [script] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))


def emit(tag):
    print("G4-TRAP " + tag, flush=True)


class InitTrap(RuntimeError):
    pass


def _net(*args, **kwargs):
    emit("net")
    raise InitTrap("net")


socket.socket.connect = _net
socket.create_connection = _net
urllib.request.urlopen = _net

_orig_open = builtins.open


def _open(file, mode="r", *args, **kwargs):
    if any(ch in mode for ch in "wax+"):
        emit("write:open:%s" % file)
        raise InitTrap("write")
    return _orig_open(file, mode, *args, **kwargs)


builtins.open = _open

import pathlib
import shutil
import subprocess as _subprocess


def _emit_raise(kind, name):
    def inner(*args, **kwargs):
        emit("%s:%s" % (kind, name))
        raise InitTrap(kind)

    return inner


for _name in ("write_text", "write_bytes", "mkdir", "unlink", "touch"):
    setattr(pathlib.Path, _name, _emit_raise("write", "Path." + _name))
for _name in ("replace", "rename", "remove", "unlink", "mkdir", "rmdir"):
    setattr(os, _name, _emit_raise("os", _name))
for _name in ("move", "copy", "copytree", "rmtree"):
    setattr(shutil, _name, _emit_raise("shutil", _name))
for _name in ("run", "Popen", "call", "check_output"):
    setattr(_subprocess, _name, _emit_raise("subprocess", _name))

try:
    import yaml

    def _yaml_guard(*args, **kwargs):
        emit("config:yaml")
        raise InitTrap("config")

    yaml.safe_load = _yaml_guard
    yaml.load = _yaml_guard
except ImportError:
    pass

_orig_import = builtins.__import__
_llm_patched = [False]


def _import_guard(name, globals=None, locals=None, fromlist=(), level=0):
    module = _orig_import(name, globals, locals, fromlist, level)
    if level == 0 and name.split(".")[0] == "llm_client" and not _llm_patched[0]:
        _llm_patched[0] = True
        cls = getattr(module, "LLMClient", None)
        if cls is not None:
            init = cls.__init__

            def _init_guard(self, *args, **kwargs):
                emit("llm:LLMClient.__init__")
                return init(self, *args, **kwargs)

            cls.__init__ = _init_guard
        getter = getattr(module, "get_llm_client", None)
        if getter is not None:
            def _getter_guard(*args, **kwargs):
                emit("llm:get_llm_client")
                return getter(*args, **kwargs)

            try:
                module.get_llm_client = _getter_guard
            except AttributeError:
                pass
    return module


builtins.__import__ = _import_guard

try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    print("G4-EXIT %s" % code, flush=True)
    raise SystemExit(code)
except BaseException as exc:
    print("G4-ERROR %s: %s" % (type(exc).__name__, exc), flush=True)
    raise SystemExit(97)
else:
    print("G4-EXIT 0", flush=True)
"""


def _child_environment(**extra: str) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith("_API_KEY")
    }
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHON_DOTENV_DISABLED": "1",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
            "PYTHONPATH": str(ROOT / "src"),
        }
    )
    environment.update(extra)
    return environment


def _run_child(
    args: list[str],
    cwd: Path,
    extra_env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=_child_environment(**(extra_env or {})),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


# ── isolated owned root (unique cw4p-<random> under system TEMP) ──────────


def _temp_root() -> Path:
    return Path(tempfile.gettempdir()).resolve()


def _cleanup_owned_root(root: Path) -> None:
    assert root.is_absolute()
    assert not root.is_symlink(), root
    if hasattr(root, "is_junction"):
        assert not root.is_junction(), root
    if root.exists():
        resolved = root.resolve()
        assert str(resolved).startswith(str(_temp_root()) + os.sep), resolved
        shutil.rmtree(root)
    assert not root.exists(), root


@pytest.fixture(scope="module")
def owned_root() -> Iterator[Path]:
    temp_root = _temp_root()
    root = temp_root / f"cw4p-{uuid.uuid4().hex[:12]}"
    assert not root.exists(), f"unique root must start absent: {root}"
    assert str(root).startswith(str(temp_root) + os.sep)
    root.mkdir()
    try:
        yield root
    finally:
        _cleanup_owned_root(root)


def _seed(case_dir: Path) -> dict[str, str]:
    if case_dir.exists():
        shutil.rmtree(case_dir)
    raw_dir = case_dir / "companies" / "示例公司" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "sentinel.md").write_bytes(SENTINEL_BYTES)
    config_dir = case_dir / "config"
    config_dir.mkdir()
    (config_dir / "mini.yaml").write_bytes(CONFIG_BYTES)
    state_dir = case_dir / "state"
    state_dir.mkdir()
    database = state_dir / "state.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE kv (id INTEGER PRIMARY KEY, v TEXT NOT NULL)")
    connection.execute("INSERT INTO kv (v) VALUES ('sentinel')")
    connection.commit()
    connection.close()
    return _snapshot(case_dir)


def _snapshot(case_dir: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for item in sorted(case_dir.rglob("*")):
        relative = item.relative_to(case_dir).as_posix()
        if item.is_file():
            state[relative] = "file:" + hashlib.sha256(item.read_bytes()).hexdigest()
        elif item.is_dir():
            state[relative] = "dir"
        else:
            state[relative] = "other"
    return state


def _database_state(database: Path) -> tuple[tuple, ...]:
    connection = sqlite3.connect(str(database))
    try:
        connection.execute("PRAGMA query_only = ON")
        schema = tuple(
            connection.execute(
                "SELECT name, sql FROM sqlite_master ORDER BY name"
            ).fetchall()
        )
        rows = tuple(connection.execute("SELECT id, v FROM kv ORDER BY id").fetchall())
    finally:
        connection.close()
    return schema + rows


@pytest.fixture
def sandbox(owned_root: Path) -> Iterator[Path]:
    case_dir = owned_root / "sandbox"
    _seed(case_dir)
    yield case_dir
    if case_dir.exists():
        shutil.rmtree(case_dir)


def _assert_retired_output(completed: subprocess.CompletedProcess[str]) -> None:
    stdout = completed.stdout
    assert completed.returncode == EXIT_CODE, stdout + completed.stderr
    assert BLOCKED_TAG in stdout, stdout
    assert RETIRED_TAG in stdout, stdout
    assert "Traceback" not in completed.stderr, completed.stderr
    assert "G4-ERROR" not in stdout, stdout


def _seeded_bytes_ok(case_dir: Path) -> bool:
    sentinel = case_dir / "companies" / "示例公司" / "raw" / "sentinel.md"
    config = case_dir / "config" / "mini.yaml"
    return sentinel.read_bytes() == SENTINEL_BYTES and (
        config.read_bytes() == CONFIG_BYTES
    )


# ── trap harness: side-effect proof in a real child process ───────────────


@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "old-auth-env"])
@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
@pytest.mark.parametrize("argv", [(), CARD_ARGS], ids=["no-args", "card-args"])
def test_harness_run_has_zero_side_effects(
    sandbox: Path, mode: str, legacy_env: bool, argv: tuple[str, ...]
) -> None:
    harness = sandbox.parent / "trap_harness.py"
    if not harness.exists():
        harness.write_text(HARNESS_SOURCE, encoding="utf-8")
    before = _snapshot(sandbox)
    database = sandbox / "state" / "state.db"
    database_before = _database_state(database)

    args = [sys.executable, "-B"]
    if mode == "nosite":
        args.append("-S")
    args.extend((str(harness), str(STUB), *argv))
    completed = _run_child(args, sandbox, OLD_AUTH_ENV if legacy_env else None)

    _assert_retired_output(completed)
    assert "G4-EXIT 78" in completed.stdout, completed.stdout
    traps = [
        line.split("G4-TRAP ", 1)[1]
        for line in completed.stdout.splitlines()
        if line.startswith("G4-TRAP ")
    ]
    assert not traps, traps
    assert _snapshot(sandbox) == before, "sandbox bytes/structure changed"
    assert _database_state(database) == database_before, "database changed"
    assert _seeded_bytes_ok(sandbox)


# ── E2E: real direct process, including the card's exact command ──────────


@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "old-auth-env"])
@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
def test_direct_process_retires_with_state_intact(
    sandbox: Path, mode: str, legacy_env: bool
) -> None:
    before = _snapshot(sandbox)
    database = sandbox / "state" / "state.db"
    database_before = _database_state(database)

    args = [sys.executable, "-B"]
    if mode == "nosite":
        args.append("-S")
    args.extend((str(STUB), *CARD_ARGS))
    completed = _run_child(args, sandbox, OLD_AUTH_ENV if legacy_env else None)

    _assert_retired_output(completed)
    assert _snapshot(sandbox) == before, "sandbox bytes/structure changed"
    assert _database_state(database) == database_before, "database changed"
    assert _seeded_bytes_ok(sandbox)


def test_old_authorization_environment_changes_nothing(sandbox: Path) -> None:
    outputs: dict[tuple[str, str], tuple[int, str]] = {}
    for mode in ("plain", "nosite"):
        for env_name, environment in (("no-env", None), ("old-auth", OLD_AUTH_ENV)):
            args = [sys.executable, "-B"]
            if mode == "nosite":
                args.append("-S")
            args.extend((str(STUB), *CARD_ARGS))
            completed = _run_child(args, sandbox, environment)
            _assert_retired_output(completed)
            outputs[(mode, env_name)] = (
                completed.returncode,
                completed.stdout,
            )
    for mode in ("plain", "nosite"):
        assert outputs[(mode, "no-env")] == outputs[(mode, "old-auth")], mode
