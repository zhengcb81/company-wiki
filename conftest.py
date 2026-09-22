"""Product-side short-basetemp convention (card I-14-F).

WinError 206 (ERROR_FILENAME_EXCED_RANGE) kills the worker-bootstrap contract nodes when
the *resolved* ``--basetemp`` sits deep enough that the paths the suite generates under it
cross the classic Win32 260-character budget consumed by non-``\\\\?\\`` participants
(``powershell.exe``, ``os.mkdir`` on this platform).  Observed bands (I-14-C r5 §4a, frozen):
resolved basetemp 173/174 chars → 12/12 failures across two trees; 80/81 chars → 12/12
passes.  The convention therefore relocates an over-deep basetemp to a fresh short
directory instead of asking callers to move their cwd.

Criterion (judgable; constants per OWNER_DECISIONS.md §16 E-1 — verbatim ruling
「E-1: 150/60」, the conservative-reroute option that OVERRIDES the keep-86
recommendation; see this card's decision.md / oracle.md §0+§2):

    relocate  iff  len(resolved_basetemp) + GENERATION_RESERVE > WIN32_PATH_LIMIT
    resolved_basetemp = basetemp                (absolute)
                      = cwd / basetemp          (relative — cwd enters here)
    WIN32_PATH_LIMIT   = 210  (empirical: generated totals ≤ ~205 are repeatedly clean,
                               240 degrades (spawn degeneration after 3 attempts), 253/278
                               hard-fail; 210 sits just above the clean envelope)
    GENERATION_RESERVE = 150  (the LONGEST suffix either bootstrap node builds under
                               basetemp: the LOGON node's launcher redirect log, measured
                               by the I-14-F independent reviewer on two PASSING unrouted
                               runs (basetemps 74 and 81):
                                 31   test dir "test_logon_wrapper_detaches_a_0"
                               + 24   "\\project path with spaces"   (logon-only level)
                               + 12   "\\fake-project"
                               + 15   "\\.source_catalog"
                               + 63   "\\worker_stdout-<32hex>-attempt-0001.log"
                               +  5   separators                                    = 150
                               The CHILD node's measured suffix is 125 (basetemps 75/116/174),
                               NOT the previously documented 124: the old arithmetic
                               "31 + 13 + 79" was internally wrong (it sums to 123 ≠ 124) and
                               it described only the child node, omitting the logon node's
                               deeper project root — the exact omission that made the old
                               "unrouted max 210" claim false (logon actually reached
                               86 + 150 = 236 unrouted). 150 ≥ 125 covers BOTH nodes.)
    ⇒ BASETEMP_MAX_CHARS = 60  (relocate iff len > 60).
    Calibration history: the first frozen guess (260/100 ⇒ 160) was FALSIFIED by attempt
    evidence — basetemp 155/156 placements failed with literal WinError 206 / dead launcher
    spawns; the second guess (240/124 ⇒ 116) failed its boundary probe (basetemp 116
    unrouted: child spawn degeneration after 3 of 19 attempts, oracle Addendum C); the third
    (210/124 ⇒ 86) under-reserved the LOGON node (reviewer R-1: real unrouted max 236).
    FINAL: owner §16 E-1 chose 150/60 — relocate iff len > 60, so every UNRELOCATED placement
    satisfies len ≤ 60 by construction and every generated total is ≤ 60 + 150 = 210 for the
    logon node (≤ 60 + 125 = 185 for the child): the margin is STRUCTURAL, not nominal.
    Boundary pair (pinned by unit tests + integration sweep): 60 ⇒ 210 unrelocated,
    61 ⇒ 211 relocated; basetemps 61–86 relocate (I-14-F's recorded 69/68, 76/75, 82/81
    no-reroute controls are superseded — written reason wherever recorded: "owner §16 E-1
    chose 150/60; this control's unrouted expectation is superseded").

Fallback: a fresh empty ``%TEMP%/cw-pytest-basetemp/<UTCstamp>-<8hex>`` per relocating
session (never an attempt/evidence root, never reused), removed in ``pytest_unconfigure``.
No pytest.ini option is loosened; sessions with a within-budget basetemp are untouched
apart from one decision record.

Machine-readable evidence: each session appends JSON lines (``event=decision`` /
``event=cleanup``) to ``$CW_BASETEMP_DECISION_FILE`` when that env var is set, and prints
``CW-BASETEMP-DECISION {...}`` / ``CW-BASETEMP-CLEANUP {...}`` lines to stdout.
``CW_SHORT_BASETEMP_DISABLE=1`` opts out (A/B testing); ``CW_BASETEMP_FALLBACK_ROOT``
overrides the fallback parent (tests only).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

WIN32_PATH_LIMIT = 210
GENERATION_RESERVE = 150  # owner §16 E-1; logon node's measured suffix (child: 125)
BASETEMP_MAX_CHARS = WIN32_PATH_LIMIT - GENERATION_RESERVE  # 60; relocate iff len > 60
FALLBACK_ROOT_NAME = "cw-pytest-basetemp"
DISABLE_ENV = "CW_SHORT_BASETEMP_DISABLE"
FALLBACK_ROOT_ENV = "CW_BASETEMP_FALLBACK_ROOT"
DECISION_FILE_ENV = "CW_BASETEMP_DECISION_FILE"
DECISION_PREFIX = "CW-BASETEMP-DECISION "
CLEANUP_PREFIX = "CW-BASETEMP-CLEANUP "


def resolve_basetemp(cwd, requested) -> Path:
    """Absolute path the suite will actually use; a relative basetemp resolves vs cwd."""
    requested_path = Path(requested)
    if requested_path.is_absolute():
        return requested_path
    return Path(cwd) / requested_path


def needs_short_path_fallback(
    cwd,
    requested,
    *,
    win32_path_limit: int = WIN32_PATH_LIMIT,
    generation_reserve: int = GENERATION_RESERVE,
) -> bool:
    return len(str(resolve_basetemp(cwd, requested))) + generation_reserve > win32_path_limit


def decide(cwd, requested, *, disabled: bool = False) -> dict:
    """Frozen judgement for one session; pure apart from reading the filesystem length."""
    if requested is None:
        return {
            "event": "decision",
            "relocated": False,
            "reason": "no-explicit-basetemp",
            "detail": "pytest derives its default basetemp from %TEMP%; short by construction",
        }
    effective = resolve_basetemp(cwd, requested)
    info = {
        "event": "decision",
        "requested_basetemp": str(effective),
        "requested_basetemp_len": len(str(effective)),
        "cwd_len": len(str(cwd)),
        "threshold": BASETEMP_MAX_CHARS,
        "win32_path_limit": WIN32_PATH_LIMIT,
        "generation_reserve": GENERATION_RESERVE,
    }
    if disabled:
        info.update(relocated=False, reason="disabled-by-env")
        return info
    if needs_short_path_fallback(cwd, requested):
        info.update(relocated=True, reason="resolved-basetemp-exceeds-budget")
    else:
        info.update(relocated=False, reason="within-budget")
    return info


def fallback_root() -> Path:
    override = os.environ.get(FALLBACK_ROOT_ENV)
    root = Path(override) if override else Path(tempfile.gettempdir()) / FALLBACK_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def make_fallback_dir(root=None) -> Path:
    """Fresh, empty, session-unique directory; caller owns its removal."""
    base = Path(root) if root is not None else fallback_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    candidate = base / f"{stamp}-{uuid.uuid4().hex[:8]}"
    candidate.mkdir()
    return candidate


def _record(decision: dict) -> None:
    print(DECISION_PREFIX + json.dumps(decision, ensure_ascii=True), flush=True)
    path = os.environ.get(DECISION_FILE_ENV)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision, ensure_ascii=True) + "\n")


def pytest_configure(config) -> None:
    requested = getattr(config.option, "basetemp", None)
    cwd = os.getcwd()
    decision = decide(cwd, requested, disabled=bool(os.environ.get(DISABLE_ENV)))
    if not decision.get("relocated"):
        _record(decision)
        return
    fallback = make_fallback_dir()
    config.option.basetemp = str(fallback)
    config._cw_basetemp_requested = decision["requested_basetemp"]
    config._cw_basetemp_fallback = fallback
    decision["effective_basetemp"] = str(fallback)
    decision["effective_basetemp_len"] = len(str(fallback))
    _record(decision)


def pytest_unconfigure(config) -> None:
    fallback = getattr(config, "_cw_basetemp_fallback", None)
    if fallback is None:
        return
    fallback_path = Path(fallback)
    record = {
        "event": "cleanup",
        "dir": str(fallback_path),
        "existed": fallback_path.exists(),
    }
    shutil.rmtree(fallback_path, ignore_errors=True)
    record["removed"] = not fallback_path.exists()
    print(CLEANUP_PREFIX + json.dumps(record, ensure_ascii=True), flush=True)
    path = os.environ.get(DECISION_FILE_ENV)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
