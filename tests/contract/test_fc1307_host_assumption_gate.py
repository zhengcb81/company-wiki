"""FC-1307-a: the host-assumption gate, and the proof that it works.

Findings F-B01-9 recorded four CI failures that every local hook let through.  One
was a test class the local gate never runs; the others were HOST ASSUMPTIONS that
are green on the machine running the hook:

  * an absolute host path baked into a test (``C:\\Windows\\win.ini`` - on Linux a
    relative name, so the assertion inverts);
  * a host CAPABILITY used with no guard in the same function (symlink creation);
  * a machine-scoped value frozen as a constant (a payload hash that embeds each
    root's absolute path - it can only be asserted where it was produced).

HONEST SCOPE (B.VR-fc1307a review, 2026-09-13).  The first version of this file
claimed the capability rule covers "the case skips on Windows and really runs on
Linux" - that is FALSE for the historical failure it was written for: the blob that
failed Linux CI (`5ab0779:tests/contract/test_r4b03_stable_bytes.py`) already
carried ``pytest.skip``, which is exactly why it was green locally, and its real
defect was an assertion that assumed the wrong layer (it demanded a scanner match
where Linux legitimately returns none).  A syntax gate cannot see that class; it is
covered by running the contract suite before pushing.  What the capability rule
DOES cover: a new, unguarded capability call in a file the local gate never runs.

``scripts/host_assumption_guard.py`` catches those syntax-level classes; this file
makes CI enforce it AND regression-tests the guard itself, so a weakened rule fails
here rather than in production.  Every case below corresponds to a property the
first review either verified or found broken (B-VR1307-01/-02/-03/-04/-05/-06/-07).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import host_assumption_guard as guard  # noqa: E402

SHIPPED_BASELINE = REPO / "tests" / "contract" / "host_assumption_baseline.json"


def _abs(scheme: str, *parts: str) -> str:
    """Build a sample host path WITHOUT baking an absolute literal into THIS file.

    The guard scans shipped literals - including the ones in this test - so a
    hard-coded ``/Users/...`` here would show up as a new violation of the very rule
    under test.  The pieces are relative names, which no rule matches.
    """
    return scheme + "/".join(("", *parts))


def test_fc1307a_the_repository_has_no_new_host_assumptions():
    """The gate itself: any NEW violation fails this case (CI and the local hooks
    run the same script)."""
    exit_code = guard.main(["--roots", "tests", "src"])
    assert exit_code == 0, "new host assumptions found - run the guard for the list"


def _fake_repo(tmp_path, monkeypatch, case_body: str, baseline: list[str] | None = None,
               registry: str | None = None):
    """A throwaway repo whose paths look real (``tests/`` in the parts), with the
    guard's three module-level paths redirected into it.

    ``resolve()`` matters: the guard compares a resolved violation path against
    REPO, so a tmp root that is itself a symlink (macOS ``/tmp``) would otherwise
    make the comparison raise instead of report - a portability landmine inside the
    portability gate.
    """
    repo = (tmp_path / "repo").resolve()
    contract = repo / "tests" / "contract"
    contract.mkdir(parents=True)
    case = repo / "tests" / "baselined_case.py"
    case.write_text(case_body, encoding="utf-8")
    baseline_path = contract / "host_assumption_baseline.json"
    if baseline is not None:
        baseline_path.write_text(json.dumps({"baseline": baseline}), encoding="utf-8")
    registry_path = contract / "host_assumption_allowlist.json"
    if registry is not None:
        registry_path.write_text(registry, encoding="utf-8")
    monkeypatch.setattr(guard, "REPO", repo)
    monkeypatch.setattr(guard, "BASELINE", baseline_path)
    monkeypatch.setattr(guard, "REGISTRY", registry_path)
    return repo, case, baseline_path


def _rules(tmp_path, body: str) -> list[str]:
    case = tmp_path / "tests" / "case.py"
    case.parent.mkdir(parents=True, exist_ok=True)
    case.write_text(body, encoding="utf-8")
    return [item["rule"] for item in guard.scan_file(case)]


# ---------------------------------------------------------------------------
# Rule 1 - absolute host paths in tests
# ---------------------------------------------------------------------------


def test_fc1307a_an_absolute_host_path_in_a_test_is_flagged(tmp_path):
    """The defect that broke CI: a Windows path literal in a test file.  The scan
    must catch it, and comments/docstrings may still DISCUSS such paths."""
    assert guard.RULE_PATHS in _rules(tmp_path, 'HOST = "C:/Windows/win.ini"\n')

    discussed = tmp_path / "tests" / "doc_only.py"
    discussed.write_text(
        '"""Docstrings may discuss C:/Windows/win.ini without tripping rule 1."""\n\n'
        "def test_y():\n    assert True\n",
        encoding="utf-8",
    )
    assert guard.scan_file(discussed) == []


@pytest.mark.parametrize("literal", [
    _abs("", "Users", "alice", "Dropbox", "Stock", "a.pdf"),   # macOS home - B-VR1307-04
    _abs("", "Volumes", "Data", "stock", "a.pdf"),             # macOS volume
    _abs("", "srv", "data", "a.pdf"),                          # Linux service root
    _abs("", "github", "workspace", "a.pdf"),                  # CI container
    _abs("", "", "server", "share", "file.pdf"),               # //server/share (UNC)
])
def test_fc1307a_widened_posix_roots_are_flagged(tmp_path, literal):
    """The first POSIX list was 12 entries and missed every one of these; each is
    the same failure mode as ``C:\\Windows\\win.ini``: not absolute on Windows,
    absolute on Linux/macOS, so a Windows-green assertion inverts on CI."""
    assert guard.RULE_PATHS in _rules(tmp_path, f'HOST = "{literal}"\n')


# ---------------------------------------------------------------------------
# Rule 2 - host capabilities without a guard in the same function
# ---------------------------------------------------------------------------


def test_fc1307a_a_capability_use_without_a_skip_is_flagged(tmp_path):
    assert guard.RULE_CAPABILITY in _rules(
        tmp_path,
        "from pathlib import Path\n\n\ndef test_link(tmp_path):\n"
        "    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n",
    )


def test_fc1307a_a_guarded_capability_use_is_clean(tmp_path):
    safe = (
        "import pytest\nfrom pathlib import Path\n\n\ndef test_link(tmp_path):\n"
        "    try:\n        (tmp_path / 'a').symlink_to(tmp_path / 'b')\n"
        "    except OSError:\n        pytest.skip('no symlink support')\n"
    )
    assert guard.scan_file(_write(tmp_path, "guarded.py", safe)) == []


@pytest.mark.parametrize("guard_source", [
    # B-VR1307-02: an unrelated skip in a SIBLING function must not exempt this one
    "import pytest\nfrom pathlib import Path\n\n\n"
    "def test_other():\n    pytest.skip('unrelated')\n\n\n"
    "def test_link(tmp_path):\n    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n",
    # ... nor a comment ...
    "from pathlib import Path\n\n\ndef test_link(tmp_path):  # no skipif needed here\n"
    "    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n",
    # ... nor a variable that merely has the word in its name
    "from pathlib import Path\n\nskipif_note = 'not a gate'\n\n\n"
    "def test_link(tmp_path):\n    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n",
])
def test_fc1307a_an_unrelated_skip_marker_does_not_exempt(tmp_path, guard_source):
    rules = [item["rule"] for item in guard.scan_file(
        _write(tmp_path, "unguarded.py", guard_source))]
    assert guard.RULE_CAPABILITY in rules, rules


def test_fc1307a_a_function_level_skipif_decorator_does_exempt(tmp_path):
    source = (
        "import sys\nimport pytest\nfrom pathlib import Path\n\n\n"
        "@pytest.mark.skipif(sys.platform == 'win32', reason='no symlinks')\n"
        "def test_link(tmp_path):\n    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n"
    )
    assert guard.scan_file(_write(tmp_path, "decorated.py", source)) == []


def test_fc1307a_a_module_level_pytestmark_skipif_does_exempt(tmp_path):
    source = (
        "import sys\nimport pytest\nfrom pathlib import Path\n\n"
        "pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='no symlinks')\n"
        "\n\ndef test_link(tmp_path):\n    (tmp_path / 'a').symlink_to(tmp_path / 'b')\n"
    )
    assert guard.scan_file(_write(tmp_path, "module_marked.py", source)) == []


def test_fc1307a_a_unittest_skiptest_guard_does_exempt(tmp_path):
    """The false positive measured before extending the gate to filing-fetch: a
    unittest-style case guards its symlink call with
    ``try/except OSError: self.skipTest(...)`` and must therefore be clean."""
    source = (
        "import unittest\nfrom pathlib import Path\n\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_symlink_escape_rejected(self):\n"
        "        link = Path('a')\n"
        "        try:\n            link.symlink_to('b')\n"
        "        except (OSError, NotImplementedError) as exc:\n"
        "            self.skipTest(f'cannot create symlink: {exc}')\n"
    )
    assert guard.scan_file(_write(tmp_path, "unittest_style.py", source)) == []


def test_fc1307a_a_helper_called_link_is_not_a_capability(tmp_path):
    """B-VR1307-02's false positive: matching on the last dotted component flagged
    any ``link()`` helper.  Only the exact APIs count now."""
    source = (
        "from pathlib import Path\n\n\ndef link(a, b):\n    return a\n\n\n"
        "def test_helper(tmp_path):\n    link(tmp_path / 'a', tmp_path / 'b')\n"
    )
    assert guard.scan_file(_write(tmp_path, "helper.py", source)) == []


def _write(tmp_path: Path, name: str, body: str) -> Path:
    case = tmp_path / "tests" / name
    case.parent.mkdir(parents=True, exist_ok=True)
    case.write_text(body, encoding="utf-8")
    return case


# ---------------------------------------------------------------------------
# Rule 3 - frozen machine-scoped digests
# ---------------------------------------------------------------------------


def test_fc1307a_a_frozen_digest_without_a_rationale_is_flagged(tmp_path):
    rules = _rules(tmp_path, 'SHA = "' + "a" * 64 + '"\n')
    assert guard.RULE_FROZEN_HASH in rules, rules


def test_fc1307a_an_uppercase_digest_is_flagged_too(tmp_path):
    """B-VR1307-05: the URL rule used re.IGNORECASE and the digest rule did not, so
    an upper-case SHA (what many tools print) walked straight through."""
    assert guard.RULE_FROZEN_HASH in _rules(tmp_path, 'SHA = "' + "A" * 64 + '"\n')


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


# ---------------------------------------------------------------------------
# The ratchet: identity is the FULL value, not a prefix
# ---------------------------------------------------------------------------


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


def test_fc1307a_a_shared_prefix_does_not_inherit_a_baseline_entry(tmp_path, monkeypatch):
    """B-VR1307-03: the key used to be ``value[:40]``, so a brand-new path sharing a
    40-character prefix with a baselined one was reported as ``new=0`` and excused.
    10 entries of the shipped baseline were exactly 40 characters, i.e. live."""
    old_value = _abs("C:", "Users", "jane", "Dropbox", "Stock", "ACME",
                     "2025-04-30_annual.pdf")
    new_value = old_value[:40] + "_interim.pdf"
    assert new_value != old_value and new_value[:40] == old_value[:40]

    repo, case, _baseline = _fake_repo(
        tmp_path, monkeypatch, f'HOST = "{old_value}"\n',
        baseline=[f"host-absolute-path|tests/baselined_case.py|{old_value}"],
    )
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        assert guard.main(["--roots", "tests"]) == 0, "the recorded value is accepted"

    case.write_text(f'HOST = "{new_value}"\n', encoding="utf-8")
    assert guard.main(["--roots", "tests"]) == 1, (
        "a NEW value that merely shares the first 40 characters must fail"
    )
    assert repo.is_dir()


# ---------------------------------------------------------------------------
# Fail-closed paths and diagnostics (B-VR1307-06, B-VR1307-07)
# ---------------------------------------------------------------------------


def test_fc1307a_an_unparseable_file_is_reported_not_skipped(tmp_path):
    """The first version's comment said a file that does not parse "is not this
    gate's business" while the code made it red.  Fail-closed is the choice; the
    comment now says so, and this case pins it."""
    rules = _rules(tmp_path, "def broken(:\n")
    assert rules == [guard.RULE_SYNTAX], rules


def test_fc1307a_a_non_utf8_file_is_reported_not_a_traceback(tmp_path):
    case = tmp_path / "tests" / "latin1.py"
    case.parent.mkdir(parents=True)
    case.write_bytes(b'# caf\xe9\nX = 1\n')
    rules = [item["rule"] for item in guard.scan_file(case)]
    assert rules == [guard.RULE_UNREADABLE], rules


def test_fc1307a_a_root_outside_the_repository_is_refused(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    (outside / "tests").mkdir(parents=True)
    (outside / "tests" / "x.py").write_text('HOST = "C:/x/y"\n', encoding="utf-8")
    repo, _case, _baseline = _fake_repo(tmp_path, monkeypatch, "X = 1\n")
    with pytest.raises(SystemExit) as excinfo:
        guard.main(["--roots", "../outside/tests"])
    assert "outside the repository" in str(excinfo.value)
    assert repo.is_dir()


def test_fc1307a_a_malformed_registry_is_refused(tmp_path, monkeypatch):
    repo, _case, _baseline = _fake_repo(tmp_path, monkeypatch, "X = 1\n",
                                        registry="{not json")
    with pytest.raises(SystemExit) as excinfo:
        guard.main(["--roots", "tests"])
    assert "not readable JSON" in str(excinfo.value)
    assert repo.is_dir()


def test_fc1307a_the_shipped_baseline_is_well_formed_and_fully_keyed():
    """Structural guard on the ratchet file: three fields per entry, an existing
    file, a known rule, and a non-empty FULL value.

    Deliberately NOT asserted here: "no recorded value is a prefix of another in the
    same file" - real tests do contain prefix literals (``x.startswith("/home/...")``),
    so that property is false by design.  The property that matters - a NEW value
    does not inherit an entry by sharing a prefix - is covered behaviourally by
    ``test_fc1307a_a_shared_prefix_does_not_inherit_a_baseline_entry``.
    """
    entries = json.loads(SHIPPED_BASELINE.read_text(encoding="utf-8"))["baseline"]
    assert entries
    for entry in entries:
        parts = entry.split("|", 2)
        assert len(parts) == 3, entry
        rule, rel, value = parts
        assert rule in (guard.RULE_PATHS, guard.RULE_CAPABILITY), entry
        assert value, entry
        assert (REPO / rel).is_file(), f"{rel} does not exist (stale baseline entry)"
