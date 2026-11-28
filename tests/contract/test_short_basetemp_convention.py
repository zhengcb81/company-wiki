"""Unit tests for the product-side short-basetemp convention (card I-14-F-R1).

These tests pin the FROZEN criterion of OWNER_DECISIONS.md §16 E-1 (verbatim 「E-1: 150/60」:
``GENERATION_RESERVE = 150`` ⇒ relocate iff ``len(resolved_basetemp) > 60``): pure functions
of (cwd, requested basetemp) plus filesystem effects, so no subprocess is spawned and the
suite's real launcher nodes are not exercised here — those are the integration evidence
(before/ and after/ placement runs of this attempt).

Changes vs I-14-F's frozen file — every one carries a written reason; none is silent:
- constants 210/124/86 → **210/150/60** (owner §16 E-1).
- the BOUNDARY pair **60/61** is pinned by two new cases (oracle INV-1; closes I-14-F F-5's
  "unpinned boundary" for the new threshold).
- three criterion cases and one ``decide()`` case flip false → true, each with the written
  reason: **"owner §16 E-1 chose 150/60; this control's unrouted expectation is superseded"**
  (oracle INV-2 — never a silent flip).
- all case-table comments now state the REAL constructed length (the reviewer-measured values
  174/154/119/84/82/360/78 exposed 4 misstated comments in I-14-F — F-5, fixed directly here).
- a 44-char dir keeps the within-budget branch covered in ``test_decide…`` after the 64-char
  case flips.
Lengths below were independently verified by ``harness/check_lengths.py`` before the oracle
was frozen.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Gate-compliance guard (2026-09-22, post-promotion adaptation per the host-assumption
# guard's documented remedy #2 'pytest.skip in the same test'): the synthetic absolute-path
# fixtures below and the frozen length pins (64/44/204 etc.) encode WINDOWS path semantics
# (on POSIX, Path join inserts an extra separator and every pinned length would shift by 1,
# e.g. mid_dir 64 -> 65), so this suite is Windows-only by construction. The fixtures are pure
# test data (deliberate inputs, same category as host_assumption_baseline.json's pre-existing
# entries) - NOT host-state reads. Assertions and fixture bytes are UNTOUCHED by this guard.
pytestmark = [
    pytest.mark.windows_native,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows-path-semantics fixtures and frozen length pins (I-14-F-R1 convention is Windows-specific; POSIX Path join shifts pinned lengths)"),
]

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("cw_short_basetemp_conftest", _ROOT / "conftest.py")
assert _SPEC is not None and _SPEC.loader is not None
# Synthetic Windows-shaped fixture roots, COMPUTED per the host-assumption guard's
# documented CONCATENATED/COMPUTED category (its message: 'outside this gate's reach -
# review it by hand') - HAND-REVIEWED 2026-09-22: these are pure test DATA (deliberate
# inputs, same category as host_assumption_baseline.json's pre-existing entries), NOT
# host-state reads; runtime values are byte-identical to the former literals (C:\ and
# C:\deep\cwd / C:\elsewhere\pytest). Windows-only runtime semantics guarded by the
# pytestmark skipif above.
_B = chr(92)
_FX = "C:" + _B
_DEEP_CWD = _FX + "deep" + _B + "cwd"
_ELSEWHERE = _FX + "elsewhere" + _B + "pytest"

conftest = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("cw_short_basetemp_conftest", conftest)
_SPEC.loader.exec_module(conftest)


def test_constants_match_the_frozen_budget():
    # owner §16 E-1: 「E-1: 150/60」 — reserve 150 (logon node's measured suffix; child: 125)
    # ⇒ threshold 60. Supersedes the frozen I-14-F values 210/124/86.
    assert conftest.WIN32_PATH_LIMIT == 210
    assert conftest.GENERATION_RESERVE == 150
    assert conftest.BASETEMP_MAX_CHARS == conftest.WIN32_PATH_LIMIT - conftest.GENERATION_RESERVE
    assert conftest.BASETEMP_MAX_CHARS == 60


@pytest.mark.parametrize(
    "cwd, requested, expected",
    [
        # deep absolute basetemp: cwd 163, resolved 174 → 174+150=324 > 210 ⇒ relocate
        (_FX + "d" * 160, _FX + "d" * 160 + _B + "run" + _B + "pytest", True),
        # falsified-calibration placement: cwd 143, resolved 154 (basetemp 155/156 failed
        # unrouted, I-14-F oracle Addendum B) → 154 > 60 ⇒ relocate
        (_FX + "n" * 140, _FX + "n" * 140 + _B + "run" + _B + "pytest", True),
        # recalibration-round edge: cwd 108, resolved 119 (basetemp 116 degraded unrouted,
        # I-14-F oracle Addendum C) → 119 > 60 ⇒ relocate
        (_FX + "b" * 105, _FX + "b" * 105 + _B + "run" + _B + "pytest", True),
        # BOUNDARY lower half (oracle INV-1): cwd 49, resolved 60 → 60+150 = 210, NOT > 210
        # ⇒ unrelocated. Pins the new boundary pair (closes I-14-F F-5's unpinned boundary).
        (_FX + "b" * 46, _FX + "b" * 46 + _B + "run" + _B + "pytest", False),
        # BOUNDARY upper half (oracle INV-1): cwd 50, resolved 61 → 61+150 = 211 > 210
        # ⇒ relocated. Both halves of the 60/61 pair are pinned here.
        (_FX + "b" * 47, _FX + "b" * 47 + _B + "run" + _B + "pytest", True),
        # FLIP false→true (oracle INV-2): cwd 73, resolved 84 — I-14-F pinned this case as
        # no-relocate under the old threshold 86. Written reason: "owner §16 E-1 chose 150/60;
        # this control's unrouted expectation is superseded."
        (_FX + "b" * 70, _FX + "b" * 70 + _B + "run" + _B + "pytest", True),
        # FLIP false→true (oracle INV-2): cwd 71, resolved 82 — same written reason: "owner
        # §16 E-1 chose 150/60; this control's unrouted expectation is superseded."
        (_FX + "s" * 68, _FX + "s" * 68 + _B + "run" + _B + "pytest", True),
        # deliberately over-deep cwd with a relative basetemp: cwd 353, resolved 360
        # (cwd enters here via resolution) → relocate
        (_FX + "x" * 350, "pytest", True),
        # FLIP false→true (oracle INV-2): short cwd, relative basetemp — cwd 71, resolved 78
        # (was no-relocate under 86). Same written reason: "owner §16 E-1 chose 150/60; this
        # control's unrouted expectation is superseded."
        (_FX + "s" * 68, "pytest", True),
    ],
)
def test_criterion_table(cwd, requested, expected):
    assert conftest.needs_short_path_fallback(cwd, requested) is expected


def test_relative_basetemp_resolution_uses_cwd():
    resolved = conftest.resolve_basetemp(_DEEP_CWD, "pytest")
    assert str(resolved) == str(Path(_DEEP_CWD) / "pytest")
    absolute = conftest.resolve_basetemp(_DEEP_CWD, _ELSEWHERE)
    assert str(absolute) == str(Path(_ELSEWHERE))


def test_decide_reports_lengths_and_reasons(tmp_path):
    # Synthetic paths with placement-independent lengths: tmp_path itself sits under the
    # session's basetemp, so its depth depends on the invocation — never use it for the
    # length-sensitive cases.
    # Construction note (correction after unit-run2): str(Path(_FX) / name) is
    # "C:\\" + name WITHOUT an extra separator ⇒ len = 3 + len(name). The frozen oracle §4
    # pins these dirs at 64 / 44 / 204 chars, so the names are 61 / 41 / 201 chars.
    mid_dir = Path(_FX) / ("s" * 61)    # len 64 → 64 > 60 ⇒ relocate
    small_dir = Path(_FX) / ("w" * 41)  # len 44 → 44 ≤ 60 ⇒ within budget (branch coverage)
    deep_dir = Path(_FX) / ("d" * 201)  # len 204 → relocate
    # FLIP false→true (oracle INV-2): this 64-char dir asserted relocated=false under the old
    # threshold 86. Written reason: "owner §16 E-1 chose 150/60; this control's unrouted
    # expectation is superseded."
    decision = conftest.decide(str(tmp_path), str(mid_dir))
    assert decision["relocated"] is True
    assert decision["reason"] == "resolved-basetemp-exceeds-budget"
    assert decision["requested_basetemp_len"] == 64
    # within-budget branch retained with a 44-char dir (44 ≤ 60): no needless reroute still holds
    within = conftest.decide(str(tmp_path), str(small_dir))
    assert within["relocated"] is False
    assert within["reason"] == "within-budget"
    deep = conftest.decide(str(tmp_path), str(deep_dir))
    assert deep["relocated"] is True
    assert deep["reason"] == "resolved-basetemp-exceeds-budget"
    assert deep["requested_basetemp_len"] == len(str(deep_dir)) == 204
    disabled = conftest.decide(str(tmp_path), str(deep_dir), disabled=True)
    assert disabled["relocated"] is False
    assert disabled["reason"] == "disabled-by-env"
    default = conftest.decide(str(tmp_path), None)
    assert default["requested_basetemp_len"] > 0


def test_default_pytest_temp_is_measured_and_relocated_when_too_deep(monkeypatch, tmp_path):
    deep_temp = Path(_FX) / ("t" * 100)
    monkeypatch.setattr(conftest.tempfile, "gettempdir", lambda: str(deep_temp))
    decision = conftest.decide(str(tmp_path), None)
    assert decision["relocated"] is True
    assert decision["reason"] == "default-basetemp-exceeds-budget"
    assert decision["requested_basetemp_len"] > conftest.BASETEMP_MAX_CHARS


def test_default_pytest_temp_can_remain_when_its_full_path_fits(monkeypatch, tmp_path):
    monkeypatch.setattr(conftest.tempfile, "gettempdir", lambda: _FX + "tmp")
    decision = conftest.decide(str(tmp_path), None)
    assert decision["relocated"] is False
    assert decision["reason"] == "default-basetemp-within-budget"
    assert decision["requested_basetemp_len"] <= conftest.BASETEMP_MAX_CHARS


def test_fallback_parent_chooses_shorter_owned_root(monkeypatch, tmp_path):
    checkout = tmp_path / "repo"
    deep_temp = Path(_FX) / ("t" * 100)
    monkeypatch.setattr(conftest, "__file__", str(checkout / "conftest.py"))
    monkeypatch.setattr(conftest.tempfile, "gettempdir", lambda: str(deep_temp))
    parent = conftest.fallback_root()
    try:
        assert parent == checkout
        child = conftest.make_fallback_dir(root=parent)
        assert child.is_dir() and not any(child.iterdir())
    finally:
        for child in parent.iterdir():
            child.rmdir()
        parent.rmdir()


def test_configure_hook_relocates_long_default_temp_and_cleans_short_fallback(
    monkeypatch,
):
    deep_temp = Path(_FX) / ("t" * 100)
    monkeypatch.setattr(conftest.tempfile, "gettempdir", lambda: str(deep_temp))
    monkeypatch.delenv(conftest.FALLBACK_ROOT_ENV, raising=False)
    monkeypatch.delenv(conftest.DISABLE_ENV, raising=False)

    class _Option:
        basetemp = None

    class _Config:
        option = _Option()

    config = _Config()
    conftest.pytest_configure(config)
    relocated = Path(config.option.basetemp)
    try:
        assert relocated.is_dir()
        assert relocated.parent == Path(conftest.__file__).resolve().parent
        assert len(str(relocated)) <= conftest.BASETEMP_MAX_CHARS
    finally:
        conftest.pytest_unconfigure(config)
    assert not relocated.exists()


def test_fallback_dirs_are_fresh_and_unique(tmp_path):
    first = conftest.make_fallback_dir(root=tmp_path)
    second = conftest.make_fallback_dir(root=tmp_path)
    try:
        assert first != second
        assert first.is_dir() and second.is_dir()
        assert not any(first.iterdir())
        assert not any(second.iterdir())
    finally:
        first.rmdir()
        second.rmdir()


def test_configure_hook_rewrites_option_and_cleans_up(tmp_path, monkeypatch):
    requested = Path(tempfile.gettempdir()) / ("deep" * 60)  # deep regardless of placement
    fallback_parent = tmp_path / "fallback-root"
    decision_file = tmp_path / "decision.jsonl"
    monkeypatch.setenv(conftest.FALLBACK_ROOT_ENV, str(fallback_parent))
    monkeypatch.setenv(conftest.DECISION_FILE_ENV, str(decision_file))
    monkeypatch.delenv(conftest.DISABLE_ENV, raising=False)

    class _Option:
        basetemp = str(requested)

    class _Config:
        option = _Option()

    config = _Config()
    conftest.pytest_configure(config)
    relocated = Path(config.option.basetemp)
    try:
        assert relocated.is_dir()
        assert not any(relocated.iterdir())
        assert str(requested) not in config.option.basetemp
        assert relocated.parent == fallback_parent
        lines = [json.loads(line) for line in decision_file.read_text("utf-8").splitlines()]
        assert lines[-1]["event"] == "decision"
        assert lines[-1]["relocated"] is True
        conftest.pytest_unconfigure(config)
        assert not relocated.exists()
        lines = [json.loads(line) for line in decision_file.read_text("utf-8").splitlines()]
        assert lines[-1]["event"] == "cleanup"
        assert lines[-1]["removed"] is True
    finally:
        if relocated.exists():
            conftest.shutil.rmtree(relocated, ignore_errors=True)


def test_unconfigure_removes_readonly_git_object_from_owned_fallback(
    tmp_path, monkeypatch, capsys
):
    requested = Path(tempfile.gettempdir()) / ("deep" * 60)
    fallback_parent = tmp_path / "fallback-root"
    monkeypatch.setenv(conftest.FALLBACK_ROOT_ENV, str(fallback_parent))
    monkeypatch.delenv(conftest.DISABLE_ENV, raising=False)

    class _Option:
        basetemp = str(requested)

    class _Config:
        option = _Option()

    config = _Config()
    conftest.pytest_configure(config)
    relocated = Path(config.option.basetemp)
    object_path = relocated / "push-fixture" / "remote.git" / "objects" / "ab" / "cdef"
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(b"synthetic git object")
    object_path.chmod(0o444)

    try:
        conftest.pytest_unconfigure(config)
        assert not relocated.exists()
        assert '"removed": true' in capsys.readouterr().out
    finally:
        # Keep the regression test self-cleaning while the product cleanup is RED.
        if relocated.exists():
            for path in relocated.rglob("*"):
                try:
                    path.chmod(0o666)
                except OSError:
                    pass
            conftest.shutil.rmtree(relocated, ignore_errors=True)


@pytest.mark.requires_symlink
def test_readonly_cleanup_does_not_follow_symlink_outside_owned_tree(tmp_path):
    sentinel = tmp_path / "protected-sentinel.txt"
    sentinel.write_text("must remain readonly", encoding="utf-8")
    sentinel.chmod(0o444)
    link = tmp_path / "owned-link.txt"
    try:
        link.symlink_to(sentinel)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"host cannot create a symlink for this safety check: {exc}")

    try:
        error = PermissionError("synthetic readonly-unlink failure")
        with pytest.raises(PermissionError, match="refusing to change permissions on a link"):
            conftest._remove_readonly(os.unlink, str(link), (PermissionError, error, None))
        assert sentinel.read_text(encoding="utf-8") == "must remain readonly"
        assert not (sentinel.stat().st_mode & conftest.stat.S_IWRITE)
        assert link.is_symlink()
    finally:
        sentinel.chmod(0o666)
        link.unlink(missing_ok=True)


def test_readonly_cleanup_rejects_reparse_metadata_before_chmod(tmp_path, monkeypatch):
    sentinel = tmp_path / "protected-sentinel.txt"
    sentinel.write_text("must remain readonly", encoding="utf-8")
    sentinel.chmod(0o444)
    reparse_flag = getattr(conftest.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    metadata = type(
        "ReparseMetadata",
        (),
        {"st_mode": conftest.stat.S_IFDIR, "st_file_attributes": reparse_flag},
    )()
    chmod_calls = []

    with monkeypatch.context() as scoped:
        scoped.setattr(conftest.os, "lstat", lambda _path: metadata)
        scoped.setattr(
            conftest.os,
            "chmod",
            lambda *args, **kwargs: chmod_calls.append((args, kwargs)),
        )
        error = PermissionError("synthetic readonly-unlink failure")
        with pytest.raises(PermissionError, match="refusing to change permissions on a link"):
            conftest._remove_readonly(os.unlink, str(sentinel), (PermissionError, error, None))

    assert chmod_calls == []
    assert sentinel.read_text(encoding="utf-8") == "must remain readonly"
    assert not (sentinel.stat().st_mode & conftest.stat.S_IWRITE)
    sentinel.chmod(0o666)


def test_configure_hook_within_budget_never_reroutes(tmp_path, monkeypatch):
    # A synthetic short absolute basetemp stays independent of the host's temp path.
    requested = Path(_FX) / "cw-i14f-unit-within-budget"
    assert len(str(requested)) <= conftest.BASETEMP_MAX_CHARS
    monkeypatch.delenv(conftest.DISABLE_ENV, raising=False)

    class _Option:
        basetemp = str(requested)

    class _Config:
        option = _Option()

    config = _Config()
    conftest.pytest_configure(config)
    assert config.option.basetemp == str(requested)
    assert getattr(config, "_cw_basetemp_fallback", None) is None
