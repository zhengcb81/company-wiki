"""G4-CWP-PIPELINE: frozen unified-pipeline retirement contracts.

Frames the retirement behaviour before the implementation change:

* importing ``full_pipeline`` is silent in plain and ``python -S``
  startups, with no config / model / network / write initialization;
* ``main(argv)`` only prints the retirement notice and returns 78;
* direct execution of the entry (no args, ``--help``, old stage flags,
  ``--no-gates`` / ``--dry-run`` / ``--gate-log``, unknown flags) is
  retired with exit 78 in plain, ``-S``, and old authorization
  environments alike;
* the removed Gate family and ``config/pipeline_rules.yaml`` are no
  longer importable or present;
* the static freeze classification of the entry never flips.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import full_pipeline
import writer_policy

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

ARG_VARIANTS: tuple[tuple[str, ...], ...] = (
    (),
    ("--help",),
    ("--company", "示例", "--stage", "review", "--no-gates"),
    ("--company", "示例", "--dry-run"),
    ("--gate-log",),
    ("--unknown-flag",),
)

REPRESENTATIVE_ARGS = ("--company", "示例", "--stage", "review", "--no-gates")


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


def _run(
    args: list[str],
    *,
    extra_env: dict[str, str] | None = None,
    timeout: int = 40,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        env=_child_environment(**(extra_env or {})),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _direct(mode: str, argv: tuple[str, ...], extra_env: dict[str, str] | None = None):
    args = [sys.executable]
    if mode == "nosite":
        args.append("-S")
    args.append(str(STUB))
    args.extend(argv)
    return _run(args, extra_env=extra_env)


# ── import silence (plain and python -S) ──────────────────────────────────


IMPORT_HARNESS = r"""
import builtins
import os
import socket
import sys
import urllib.request

scripts = sys.argv[1]
sys.path.insert(0, scripts)


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

import full_pipeline  # noqa: E402

print("G4-IMPORT-OK", flush=True)
"""


def _run_import_harness(mode: str, tmp_path: Path):
    harness = tmp_path / "g4_import_harness.py"
    if not harness.exists():
        harness.write_text(IMPORT_HARNESS, encoding="utf-8")
    args = [sys.executable, "-B"]
    if mode == "nosite":
        args.append("-S")
    args.extend((str(harness), str(SCRIPTS)))
    return _run(args)


@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
def test_import_is_silent_without_any_initialization(mode: str, tmp_path: Path) -> None:
    completed = _run_import_harness(mode, tmp_path)
    stdout = completed.stdout
    assert completed.returncode == 0, stdout + completed.stderr
    assert "G4-IMPORT-OK" in stdout, stdout
    traps = [
        line.split("G4-TRAP ", 1)[1]
        for line in stdout.splitlines()
        if line.startswith("G4-TRAP ")
    ]
    assert not traps, traps
    assert "Traceback" not in completed.stderr, completed.stderr


def test_main_only_prints_retirement_notice_and_returns_78(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = full_pipeline.main(["--company", "示例", "--stage", "review"])
    captured = capsys.readouterr()
    assert result == EXIT_CODE
    assert BLOCKED_TAG in captured.out, captured.out
    assert RETIRED_TAG in captured.out, captured.out
    assert "source-catalog" in captured.out, captured.out
    assert "COMPANY_WIKI" not in captured.out, captured.out
    assert "review_queue" not in captured.out, captured.out
    assert "human_review" not in captured.out, captured.out


def test_main_result_does_not_depend_on_argv(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for argv in (None, [], ["--help"], ["--unknown"]):
        assert full_pipeline.main(argv) == EXIT_CODE, argv
        capsys.readouterr()


# ── direct CLI retirement (plain, -S, old authorization env) ──────────────


@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "old-auth-env"])
@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
def test_direct_cli_retires_representative_command(mode: str, legacy_env: bool) -> None:
    completed = _direct(mode, REPRESENTATIVE_ARGS, OLD_AUTH_ENV if legacy_env else None)
    stdout = completed.stdout
    assert completed.returncode == EXIT_CODE, stdout + completed.stderr
    assert BLOCKED_TAG in stdout, stdout
    assert RETIRED_TAG in stdout, stdout
    assert "Traceback" not in completed.stderr, completed.stderr
    assert "unrecognized arguments" not in completed.stderr, completed.stderr


@pytest.mark.parametrize("argv", ARG_VARIANTS, ids=lambda a: " ".join(a) or "no-args")
def test_direct_cli_retires_every_legacy_argument_form(argv: tuple[str, ...]) -> None:
    completed = _direct("plain", argv)
    stdout = completed.stdout
    assert completed.returncode == EXIT_CODE, stdout + completed.stderr
    assert BLOCKED_TAG in stdout, stdout
    assert RETIRED_TAG in stdout, stdout
    assert "Traceback" not in completed.stderr, completed.stderr


# ── removed family ────────────────────────────────────────────────────────


def _find_spec_or_none(name: str):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


def test_gate_family_is_no_longer_importable() -> None:
    assert _find_spec_or_none("gate_system") is None
    assert _find_spec_or_none("gate_system.registry") is None
    assert _find_spec_or_none("gate_system.gates.extraction_quality_gate") is None


def test_pipeline_rules_config_is_retired() -> None:
    assert not (ROOT / "config" / "pipeline_rules.yaml").exists()


def test_removed_family_is_not_referenced_by_the_stub() -> None:
    source = STUB.read_text(encoding="utf-8-sig")
    for token in ("gate_system", "pipeline_rules", "common", "llm_client", "yaml"):
        assert token not in source, token


# ── static freeze classification stays permanent ──────────────────────────


@pytest.mark.parametrize(
    "environment",
    [{}, OLD_AUTH_ENV, {"COMPANY_WIKI_WRITE_MODE": "off"}],
    ids=["none", "old-auth-env", "off"],
)
def test_entry_stays_permanently_retired_in_policy(environment: dict[str, str]) -> None:
    assert (
        writer_policy.legacy_script_execution_allowed("full_pipeline.py", environment)
        is False
    )
    assert "full_pipeline.py" in writer_policy.PERMANENTLY_RETIRED_SCRIPTS


def test_stub_keeps_the_shared_direct_cli_guard() -> None:
    source = STUB.read_text(encoding="utf-8-sig")
    assert "enforce_direct_cli" in source
