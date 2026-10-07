"""G1-LEGACY: entry-policy consolidation and one-off ops-tool retirement.

Frames the card's behaviour contract before the implementation change:

* supported control/source-pilot entries run without any environment
  permission, in both plain and ``PYTHONPATH=scripts`` startups;
* environment permission values never change any execution result;
* permanently retired research/Wiki writers stay frozen (78) before config,
  LLM, network or write initialization, with or without ``python -S``;
* the six completed one-off retirement tools and their dedicated test chain
  are gone from the tree, with no remaining import chain;

The one-off card's Git write-set/deletion audit belongs in its delivery
receipt. It must not constrain unrelated work or a user's dirty checkout.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

import common
import writer_policy
from helpers.fixture_files import snapshot_files
from writer_policy import (
    BLOCKED_EXIT_CODE,
    CONTROL_TOOL_ALLOWLIST,
    PERMANENTLY_RETIRED_SCRIPTS,
    SOURCE_WORKFLOW_TOOL_ALLOWLIST,
    enforce_direct_cli,
    is_legacy_script_cli,
    legacy_script_execution_allowed,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

# Every environment permutation the old two-factor gate used to distinguish.
ENV_VARIANTS: tuple[dict[str, str], ...] = (
    {},
    {"COMPANY_WIKI_WRITE_MODE": "legacy", "COMPANY_WIKI_LEGACY_WRITERS": "allow"},
    {"COMPANY_WIKI_WRITE_MODE": "legacy"},
    {"COMPANY_WIKI_LEGACY_WRITERS": "allow"},
    {"COMPANY_WIKI_WRITE_MODE": "LEGACY", "COMPANY_WIKI_LEGACY_WRITERS": "ALLOW"},
    {"COMPANY_WIKI_WRITE_MODE": "off", "COMPANY_WIKI_LEGACY_WRITERS": "deny"},
)

# Mixed legacy entries: not on the support list, not permanently retired.
# They must not become executable merely because the env gate disappears.
# G5-CWP-CHECKS moved test_framework.py into the engineering retirement
# category, so it is covered by test_g5_legacy_checks_retirement.py instead.
MIXED_SAMPLES = (
    "collect_reports.py",
    "source_catalog_pilot_check.py",
    "graph.py",
)

SUPPORTED_SAMPLES = (
    "config_doctor.py",
    "narrative_evidence_pilot.py",
    "narrative_summary_review_pilot.py",
)

# One-off retirement tool chain removed by this card (code + dedicated tests).
REMOVED_PATHS = (
    "scripts/retire_source_catalog_db.py",
    "scripts/cutover_source_catalog_db.py",
    "scripts/audit_catalog_retirement.py",
    "scripts/audit_catalog_consumers.py",
    "scripts/retire_catalog_snapshot.py",
    "scripts/retire_derived_archives.py",
    "tests/unit/test_retire_source_catalog_db.py",
    "tests/unit/test_retire_catalog_snapshot.py",
    "tests/unit/test_retire_derived_archives.py",
    "tests/integration/test_retire_catalog_snapshot_e2e.py",
    "tests/integration/test_retire_derived_archives_e2e.py",
    "tests/support/derived_archive_fixture.py",
)
REMOVED_MODULE_TOKENS = (
    "retire_source_catalog_db",
    "cutover_source_catalog_db",
    "audit_catalog_retirement",
    "audit_catalog_consumers",
    "retire_catalog_snapshot",
    "retire_derived_archives",
    "derived_archive_fixture",
)

# Pre-existing defects outside this card's write set: the guard is
# unreachable because module-level third-party imports fail first.  The
# process still exits before config, LLM, network or write initialization.
# Reported to MAIN in the handoff; not silently accepted for other entries.
PRE_GUARD_CRASH = {
    ("refine.py", "plain"): "missing scripts/extract.py",
    ("refine.py", "nosite"): "missing scripts/extract.py",
    ("build_links.py", "nosite"): "module-level import yaml under -S",
    ("generate_index.py", "nosite"): "module-level import yaml under -S",
    ("generate_slides.py", "nosite"): "module-level import yaml under -S",
    ("stage3_analyze.py", "nosite"): "module-level from config import Config under -S",
}

# auto_discover.py:324 reads config_rules.yaml at module level before its
# guard; the script is outside this card's write set (reported to MAIN).
CONFIG_PRE_GUARD = {("auto_discover.py", "plain")}


HARNESS_SOURCE = r"""
import builtins
import os
import runpy
import socket
import sys
import urllib.request

script = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))


def emit(tag):
    print("G1-TRAP " + tag, flush=True)


class InitTrap(RuntimeError):
    pass


def _net(*args, **kwargs):
    emit("net:connect")
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


def _blocked_path(name):
    def inner(self, *args, **kwargs):
        emit("write:%s:%s" % (name, self))
        raise InitTrap("write")

    return inner


def _blocked_os(name):
    def inner(*args, **kwargs):
        emit("os:%s:%s" % (name, args))
        raise InitTrap("write")

    return inner


def _blocked_shutil(name):
    def inner(*args, **kwargs):
        emit("shutil:%s:%s" % (name, args))
        raise InitTrap("write")

    return inner


for _name in ("write_text", "write_bytes", "mkdir", "unlink", "touch"):
    setattr(pathlib.Path, _name, _blocked_path("Path." + _name))
for _name in ("replace", "rename", "remove", "unlink", "mkdir", "rmdir"):
    setattr(os, _name, _blocked_os("os." + _name))
for _name in ("move", "copy", "copytree", "rmtree"):
    setattr(shutil, _name, _blocked_shutil("shutil." + _name))

try:
    import yaml

    _safe_load = yaml.safe_load
    _load = yaml.load

    def _safe_load_guard(stream, *args, **kwargs):
        emit("config:yaml.safe_load")
        return _safe_load(stream, *args, **kwargs)

    def _load_guard(stream, *args, **kwargs):
        emit("config:yaml.load")
        return _load(stream, *args, **kwargs)

    yaml.safe_load = _safe_load_guard
    yaml.load = _load_guard
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
            _init = cls.__init__

            def _init_guard(self, *args, **kwargs):
                emit("llm:LLMClient.__init__")
                return _init(self, *args, **kwargs)

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

sys.argv = [script, "--help"]
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    print("G1-EXIT %s" % code, flush=True)
    raise SystemExit(code)
except BaseException as exc:
    print("G1-ERROR %s: %s" % (type(exc).__name__, exc), flush=True)
    raise SystemExit(97)
else:
    print("G1-EXIT 0", flush=True)
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
    *,
    pythonpath_scripts: bool = False,
    extra_env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int = 40,
) -> subprocess.CompletedProcess[str]:
    env_extra: dict[str, str] = dict(extra_env or {})
    if pythonpath_scripts:
        env_extra["PYTHONPATH"] = os.pathsep.join((str(SCRIPTS), str(ROOT / "src")))
    return subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        env=_child_environment(**env_extra),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _legacy_pair() -> dict[str, str]:
    return {
        "COMPANY_WIKI_WRITE_MODE": "legacy",
        "COMPANY_WIKI_LEGACY_WRITERS": "allow",
    }


# ── static policy contract ────────────────────────────────────────────────


def test_support_set_contains_read_only_config_doctor_and_source_pilots() -> None:
    assert "config_doctor.py" in CONTROL_TOOL_ALLOWLIST
    retired_tools = {
        "audit_catalog_consumers.py",
        "audit_catalog_retirement.py",
        "cutover_source_catalog_db.py",
        "retire_source_catalog_db.py",
        "retire_catalog_snapshot.py",
        "retire_derived_archives.py",
    }
    assert not SOURCE_WORKFLOW_TOOL_ALLOWLIST & retired_tools
    assert {
        "narrative_evidence_pilot.py",
        "narrative_summary_review_pilot.py",
    } <= SOURCE_WORKFLOW_TOOL_ALLOWLIST
    assert not (CONTROL_TOOL_ALLOWLIST | SOURCE_WORKFLOW_TOOL_ALLOWLIST) & set(
        PERMANENTLY_RETIRED_SCRIPTS
    )


def test_supported_tools_need_no_environment_permission() -> None:
    supported = sorted(CONTROL_TOOL_ALLOWLIST | SOURCE_WORKFLOW_TOOL_ALLOWLIST)
    assert supported, "support set must not be empty"
    for name in supported:
        for environment in ENV_VARIANTS:
            assert legacy_script_execution_allowed(name, environment) is True, (
                name,
                environment,
            )
        assert legacy_script_execution_allowed(name) is True, name


def test_permanently_retired_scripts_are_never_allowed() -> None:
    for name in sorted(PERMANENTLY_RETIRED_SCRIPTS):
        for environment in ENV_VARIANTS:
            assert legacy_script_execution_allowed(name, environment) is False, (
                name,
                environment,
            )
        assert legacy_script_execution_allowed(name) is False, name


def test_mixed_legacy_entries_are_not_auto_allowed() -> None:
    for name in MIXED_SAMPLES:
        for environment in ENV_VARIANTS:
            assert legacy_script_execution_allowed(name, environment) is False, (
                name,
                environment,
            )


def test_environment_values_never_change_execution_result() -> None:
    samples = (
        sorted(CONTROL_TOOL_ALLOWLIST | SOURCE_WORKFLOW_TOOL_ALLOWLIST)
        + list(MIXED_SAMPLES)
        + sorted(PERMANENTLY_RETIRED_SCRIPTS)
    )
    for name in samples:
        results = {
            legacy_script_execution_allowed(name, environment)
            for environment in ENV_VARIANTS
        }
        results.add(legacy_script_execution_allowed(name))
        assert len(results) == 1, (name, results)


def test_public_entry_policy_signatures_are_preserved() -> None:
    assert list(inspect.signature(enforce_direct_cli).parameters) == [
        "module_name",
        "script_path",
        "environment",
    ]
    assert list(inspect.signature(legacy_script_execution_allowed).parameters) == [
        "script_path",
        "environment",
    ]
    assert list(
        inspect.signature(common.require_legacy_writer_permission).parameters
    ) == [
        "script_name",
    ]


def test_legacy_writer_authorization_helper_is_removed() -> None:
    assert not hasattr(writer_policy, "legacy_writer_authorized")


def test_is_legacy_script_cli_separates_supported_and_retired_entries() -> None:
    for name in SUPPORTED_SAMPLES:
        assert not is_legacy_script_cli(SCRIPTS / name), name
    assert is_legacy_script_cli(SCRIPTS / "scheduler.py")
    assert is_legacy_script_cli(SCRIPTS / "collect_reports.py")
    assert not is_legacy_script_cli(SCRIPTS / "sitecustomize.py")
    assert not is_legacy_script_cli(SCRIPTS / "writer_policy.py")
    assert not is_legacy_script_cli(ROOT / "not-a-script.txt")


def test_blocked_message_no_longer_promotes_environment_overrides() -> None:
    mixed_message = writer_policy.blocked_message("collect_reports.py")
    assert "LEGACY WRITER BLOCKED" in mixed_message
    assert "COMPANY_WIKI_WRITE_MODE" not in mixed_message
    assert "COMPANY_WIKI_LEGACY_WRITERS" not in mixed_message
    permanent_message = writer_policy.blocked_message("query.py")
    assert "PERMANENTLY RETIRED" in permanent_message
    assert "Environment overrides cannot re-enable" in permanent_message


# ── startup-mode consistency (plain vs sitecustomize) ─────────────────────


@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "legacy-pair"])
@pytest.mark.parametrize(
    "pythonpath_scripts", [False, True], ids=["plain", "scripts-on-pythonpath"]
)
def test_config_doctor_help_is_startup_mode_independent(
    pythonpath_scripts: bool, legacy_env: bool
) -> None:
    extra = _legacy_pair() if legacy_env else {}
    completed = _run_child(
        [sys.executable, str(SCRIPTS / "config_doctor.py"), "--help"],
        pythonpath_scripts=pythonpath_scripts,
        extra_env=extra,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "LEGACY WRITER BLOCKED" not in completed.stdout
    assert "--structure-only" in completed.stdout


@pytest.mark.parametrize(
    "script_name",
    ["narrative_evidence_pilot.py", "narrative_summary_review_pilot.py"],
)
@pytest.mark.parametrize(
    "pythonpath_scripts", [False, True], ids=["plain", "scripts-on-pythonpath"]
)
def test_supported_source_pilot_help_runs_in_both_startup_modes(
    script_name: str, pythonpath_scripts: bool
) -> None:
    completed = _run_child(
        [sys.executable, str(SCRIPTS / script_name), "--help"],
        pythonpath_scripts=pythonpath_scripts,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "LEGACY WRITER BLOCKED" not in completed.stdout


@pytest.mark.parametrize(
    "script_name", ["scheduler.py", "query.py", "maintenance.py", "ingest_v2.py"]
)
@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "legacy-pair"])
def test_permanently_retired_entry_is_blocked_with_sitecustomize_active(
    script_name: str, legacy_env: bool
) -> None:
    extra = _legacy_pair() if legacy_env else {}
    completed = _run_child(
        [sys.executable, str(SCRIPTS / script_name), "--help"],
        pythonpath_scripts=True,
        extra_env=extra,
    )
    assert completed.returncode == BLOCKED_EXIT_CODE, completed.stdout
    assert "PERMANENTLY RETIRED" in completed.stdout


@pytest.mark.parametrize(
    "script_name",
    ["collect_reports.py", "source_catalog_pilot_check.py"],
)
@pytest.mark.parametrize(
    "pythonpath_scripts", [False, True], ids=["plain", "scripts-on-pythonpath"]
)
@pytest.mark.parametrize("legacy_env", [False, True], ids=["no-env", "legacy-pair"])
def test_mixed_guarded_entry_is_blocked_in_both_startup_modes(
    script_name: str, pythonpath_scripts: bool, legacy_env: bool
) -> None:
    extra = _legacy_pair() if legacy_env else {}
    completed = _run_child(
        [sys.executable, str(SCRIPTS / script_name), "--help"],
        pythonpath_scripts=pythonpath_scripts,
        extra_env=extra,
    )
    assert completed.returncode == BLOCKED_EXIT_CODE, completed.stdout
    assert "LEGACY WRITER BLOCKED" in completed.stdout


# ── one-off tool retirement ───────────────────────────────────────────────


def test_one_off_retirement_tools_are_removed_from_the_tree() -> None:
    for relative in REMOVED_PATHS:
        assert not (ROOT / relative).exists(), relative


def test_one_off_retirement_tools_left_no_import_chain() -> None:
    for token in REMOVED_MODULE_TOKENS:
        assert importlib.util.find_spec(token) is None, token
        assert importlib.util.find_spec(f"scripts.{token}") is None, token

    self_path = Path(__file__).resolve()
    hits: list[str] = []
    for base in (SCRIPTS, ROOT / "tests"):
        for path in sorted(base.rglob("*.py")):
            if path.resolve() == self_path:
                continue
            source = path.read_text(encoding="utf-8-sig")
            for token in REMOVED_MODULE_TOKENS:
                if token in source:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}:{token}")
    assert not hits, hits


# ── dynamic exit contract (plain and python -S) ───────────────────────────


def _run_harness(script_name: str, mode: str, tmp_path: Path):
    harness = tmp_path / "g1_trap_harness.py"
    if not harness.exists():
        harness.write_text(HARNESS_SOURCE, encoding="utf-8")
    args = [sys.executable, "-B"]
    if mode == "nosite":
        args.append("-S")
    args.extend((str(harness), str(SCRIPTS / script_name)))
    return _run_child(args)


@pytest.mark.parametrize("mode", ["plain", "nosite"], ids=["plain", "no-site"])
@pytest.mark.parametrize("script_name", sorted(PERMANENTLY_RETIRED_SCRIPTS))
def test_permanently_retired_entry_exits_before_initialization(
    script_name: str, mode: str, tmp_path: Path
) -> None:
    completed = _run_harness(script_name, mode, tmp_path)
    stdout = completed.stdout
    traps = [
        line.split("G1-TRAP ", 1)[1]
        for line in stdout.splitlines()
        if line.startswith("G1-TRAP ")
    ]
    key = (script_name, mode)
    if key in PRE_GUARD_CRASH:
        # Documented pre-existing defect outside the write set: the guard is
        # unreachable, but the process still dies before any initialization.
        assert not traps, (script_name, mode, traps, stdout)
        assert "G1-ERROR" in stdout, stdout
        assert completed.returncode != 0
        assert "G1-EXIT 0" not in stdout
        return

    assert completed.returncode == BLOCKED_EXIT_CODE, stdout + completed.stderr
    assert "G1-EXIT 78" in stdout, stdout
    # G5-CWP-CHECKS: batch_process.py also belongs to the engineering
    # retirement family, so both startup paths report that marker instead of
    # the research-writer banner.  The exit contract is unchanged.
    expected_marker = (
        "LEGACY_ENGINEERING_TOOL_RETIRED"
        if script_name in writer_policy.RETIRED_ENGINEERING_TOOL_SCRIPTS
        else "PERMANENTLY RETIRED"
    )
    assert expected_marker in stdout, stdout
    assert "unrecognized arguments" not in completed.stderr

    forbidden = [
        tag
        for tag in traps
        if tag.startswith(("write:", "os:", "shutil:", "net:", "llm:"))
    ]
    assert not forbidden, (script_name, mode, traps)
    allowed_config = (
        {"config:yaml.safe_load", "config:yaml.load"}
        if key in CONFIG_PRE_GUARD
        else set()
    )
    unexpected_config = [
        tag for tag in traps if tag.startswith("config:") and tag not in allowed_config
    ]
    assert not unexpected_config, (script_name, mode, traps)


def test_blocked_entry_leaves_isolated_fixture_untouched(tmp_path: Path) -> None:
    raw = tmp_path / "companies" / "样例公司" / "raw" / "source.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("原始资料", encoding="utf-8")
    state = tmp_path / ".state" / "state.db"
    state.parent.mkdir()
    state.write_bytes(b"state")
    (tmp_path / "log.md").write_text("# log\n", encoding="utf-8")
    before = snapshot_files(tmp_path)

    for script_name in ("ingest_v2.py", "collect_reports.py"):
        completed = _run_child(
            [sys.executable, str(SCRIPTS / script_name), "--help"],
            extra_env=_legacy_pair(),
            cwd=tmp_path,
        )
        assert completed.returncode == BLOCKED_EXIT_CODE, (
            script_name,
            completed.stdout,
            completed.stderr,
        )
        assert "LEGACY WRITER BLOCKED" in completed.stdout

    assert snapshot_files(tmp_path) == before
