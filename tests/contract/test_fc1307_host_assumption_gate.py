"""FC-1307-a: the host-assumption gate, and the proof that it works.

Findings F-B01-9 recorded four CI failures that every local hook let through.  One
was a test class the local gate never runs; the other three were HOST ASSUMPTIONS
that are green on the machine running the hook:

  * an absolute host path baked into a test (``C:\\Windows\\win.ini`` - on Linux a
    relative name, so the assertion inverts);
  * a host capability used without a skip (symlink creation: skipped on Windows,
    really runs on Linux);
  * a machine-scoped value frozen as a constant (a payload hash that embeds each
    root's absolute path - it can only be asserted where it was produced).

``scripts/host_assumption_guard.py`` catches those three classes; this file makes
CI enforce it AND regression-tests the guard itself, so a weakened rule fails
here rather than in production.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import host_assumption_guard as guard  # noqa: E402


def test_fc1307a_the_repository_has_no_new_host_assumptions():
    """The gate itself: any NEW violation fails this case (CI and the local hooks
    run the same script)."""
    exit_code = guard.main(["--roots", "tests", "src"])
    assert exit_code == 0, "new host assumptions found - run the guard for the list"


def test_fc1307a_an_absolute_host_path_in_a_test_is_flagged(tmp_path):
    """The defect that broke CI: a Windows path literal in a test file.  The scan
    must catch it, and comments/docstrings may still DISCUSS such paths."""
    fake = tmp_path / "tests" / "fake_case.py"  # "tests" in the path is what scopes rule A
    fake.parent.mkdir(parents=True)
    # forward slashes on purpose: the same defect without a Python escape warning
    fake.write_text(
        'HOST = "C:/Windows/win.ini"\n\n\ndef test_x():\n    assert HOST\n',
        encoding="utf-8",
    )
    rules = [item["rule"] for item in guard.scan_file(fake)]
    assert guard.RULE_PATHS in rules, rules

    discussed = tmp_path / "tests" / "doc_only.py"
    discussed.write_text(
        '"""Docstrings may discuss C:/Windows/win.ini without tripping rule A."""\n\n'
        "def test_y():\n    assert True\n",
        encoding="utf-8",
    )
    assert guard.scan_file(discussed) == []


def test_fc1307a_a_capability_use_without_a_skip_is_flagged(tmp_path):
    """The symlink case: a test that creates symlinks but never skips on a host
    that cannot is exactly what skips here and fails on Linux."""
    unsafe = tmp_path / "tests" / "capability.py"
    unsafe.parent.mkdir(parents=True)
    unsafe.write_text(
        "from pathlib import Path\n\n\ndef test_link(tmp_path):\n"
        "    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n",
        encoding="utf-8",
    )
    rules = [item["rule"] for item in guard.scan_file(unsafe)]
    assert guard.RULE_CAPABILITY in rules, rules

    safe = tmp_path / "tests" / "capability_safe.py"
    safe.write_text(
        "import pytest\nfrom pathlib import Path\n\n\ndef test_link(tmp_path):\n"
        "    try:\n        (tmp_path / 'a').symlink_to(tmp_path / 'b')\n"
        "    except OSError:\n        pytest.skip('no symlink support')\n",
        encoding="utf-8",
    )
    assert guard.scan_file(safe) == []


def test_fc1307a_a_frozen_digest_without_a_rationale_is_flagged(tmp_path):
    """The machine-scoped constant: an unregistered 64-hex literal is refused, so
    freezing a host-dependent value requires a deliberate, written rationale."""
    fake = tmp_path / "tests" / "frozen.py"
    fake.parent.mkdir(parents=True)
    fake.write_text(
        'SHA = "' + "a" * 64 + '"\n\n\ndef test_z():\n    assert SHA\n', encoding="utf-8"
    )
    rules = [item["rule"] for item in guard.scan_file(fake)]
    assert guard.RULE_FROZEN_HASH in rules, rules


def test_fc1307a_every_registered_digest_carries_a_rationale():
    """A registry entry without a reason is how a wrong freeze gets blessed; the
    registry therefore has to say WHERE it is and WHY it is host-independent."""
    registry = json.loads(
        (REPO / "tests" / "contract" / "host_assumption_allowlist.json").read_text(
            encoding="utf-8"
        )
    )
    entries = registry["registered_hashes"]
    assert entries, "an empty registry would mean the rule never fires"
    for digest, entry in entries.items():
        assert len(digest) == 64 and digest == digest.lower(), digest
        assert entry.get("where"), digest
        assert len(entry.get("rationale", "")) > 40, digest


def test_fc1307a_product_code_may_branch_on_the_host(tmp_path):
    """Rule A judges TESTS only, on purpose: product code legitimately detects the
    host (``lock.py`` reads ``/proc/stat``, ``startup.py`` probes ``C:/Windows``).
    Widening the scan to ``src/`` would drown the gate in deliberate platform
    branches, so that decision is pinned here."""
    src = tmp_path / "src" / "platform_probe.py"
    src.parent.mkdir(parents=True)
    src.write_text(
        'PROC = "/proc/stat"\nWIN = "C:/Windows"\nUNC = "\\\\\\\\?\\\\C:"\n',
        encoding="utf-8",
    )
    rules = [item["rule"] for item in guard.scan_file(src)]
    assert guard.RULE_PATHS not in rules, rules


def _fake_repo(tmp_path, monkeypatch, case_body: str):
    """A throwaway repo whose paths look real (``tests/`` in the parts), with the
    guard's three module-level paths redirected into it.

    ``resolve()`` matters: the guard compares a resolved violation path against
    REPO, so a tmp root that is itself a symlink (macOS ``/tmp``) would otherwise
    make the comparison raise instead of report - a portability landmine inside
    the portability gate.
    """
    repo = (tmp_path / "repo").resolve()
    contract = repo / "tests" / "contract"
    contract.mkdir(parents=True)
    case = repo / "tests" / "baselined_case.py"
    case.write_text(case_body, encoding="utf-8")
    baseline = contract / "host_assumption_baseline.json"
    registry = contract / "host_assumption_allowlist.json"
    monkeypatch.setattr(guard, "REPO", repo)
    monkeypatch.setattr(guard, "BASELINE", baseline)
    monkeypatch.setattr(guard, "REGISTRY", registry)
    return repo, case, baseline


def test_fc1307a_the_ratchet_is_value_level_not_file_level(tmp_path, monkeypatch, capsys):
    """The baseline must excuse the EXACT recorded offender only.  A file-keyed
    baseline would let a fresh defect hide in an already-baselined file - which is
    how a ratchet silently becomes a rubber stamp."""
    repo, case, baseline = _fake_repo(
        tmp_path, monkeypatch, 'HOST = "C:/Windows/win.ini"\n'
    )
    assert guard.main(["--roots", "tests"]) == 1, "an unbaselined path must fail"
    capsys.readouterr()  # drain the violation report: only the NEXT call's stdout is JSON

    assert guard.main(["--emit-baseline", "--roots", "tests"]) == 0
    baseline.write_text(capsys.readouterr().out, encoding="utf-8")
    assert guard.main(["--roots", "tests"]) == 0, "the recorded offender is accepted"

    case.write_text(
        'HOST = "C:/Windows/win.ini"\nOTHER = "/etc/passwd"\n', encoding="utf-8"
    )
    assert guard.main(["--roots", "tests"]) == 1, (
        "a SECOND, different absolute path in the same file is a new violation"
    )
    assert repo.is_dir()


def test_fc1307a_emit_baseline_only_prints_and_never_writes(tmp_path, monkeypatch, capsys):
    """Regression test for the defect that made the gate itself fail CI: the guard
    used to have a mode that WROTE the baseline, which put it under the frozen
    writer-CLI inventory.  A checker must not write into the tree it checks, so the
    emitting mode prints and leaves every byte (and the file list) alone."""
    repo, _case, baseline = _fake_repo(
        tmp_path, monkeypatch, 'HOST = "C:/Windows/win.ini"\n'
    )
    baseline.write_text('{"baseline": []}\n', encoding="utf-8")
    before_files = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*"))
    before_bytes = baseline.read_bytes()

    assert guard.main(["--emit-baseline", "--roots", "tests"]) == 0

    assert baseline.read_bytes() == before_bytes, "the emitting mode modified the tree"
    assert sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")) == before_files
    payload = json.loads(capsys.readouterr().out)
    assert payload["baseline"], "the emitted baseline must contain the offender"

