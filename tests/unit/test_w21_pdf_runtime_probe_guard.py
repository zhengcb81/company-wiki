"""Probe write guard: the standard discard device passes, lookalikes do not.

The guard exists only inside the cold-start probe; production PDF runtime code
carries no manual write gate. The audit hook observes Python-level events and
is never claimed to intercept native syscalls exhaustively.
"""
import os
from pathlib import Path

import pytest

from tools.pdf_runtime_probe.cold_runtime_probe import classify_open, make_audit_hook


def owned_temp(tmp_path):
    temp = tmp_path / "owned-temp"
    temp.mkdir()
    return temp


def test_true_devnull_device_is_allowed_in_any_write_mode(tmp_path):
    temp = owned_temp(tmp_path)
    for mode in ("r+b", "w", "wb+", "a"):
        assert classify_open(os.devnull, mode, 0, temp) is None


def test_devnull_with_integer_write_flags_is_allowed(tmp_path):
    assert classify_open(os.devnull, None, os.O_RDWR | os.O_CREAT, owned_temp(tmp_path)) is None


def test_devnull_reads_and_case_variants_of_the_exact_device_pass(tmp_path):
    temp = owned_temp(tmp_path)
    raw = os.devnull.upper() if os.name == "nt" else os.devnull
    assert classify_open(raw, "r+b", 0, temp) is None


@pytest.mark.parametrize("raw", ["NUL.txt", "nul_backup", "devnull", "sub/NUL", "./nul", "NUL ".strip() + "_copy"])
def test_lookalike_names_and_paths_never_borrow_the_device(tmp_path, raw):
    assert classify_open(raw, "w", 0, owned_temp(tmp_path)) == "persistent_write"


@pytest.mark.skipif(os.name != "nt", reason="Windows resolves device names in subpaths")
def test_windows_subpath_device_name_is_still_rejected(tmp_path):
    assert classify_open("sub/NUL", "r+b", 0, owned_temp(tmp_path)) == "persistent_write"


def test_temp_writes_are_allowed_and_originals_or_secrets_rejected(tmp_path):
    temp = owned_temp(tmp_path)
    assert classify_open(temp / "page.png", "wb", 0, temp) is None
    assert classify_open("annual.pdf", "r", 0, temp) == "original_or_secret"
    assert classify_open("credentials/.env", "r", 0, temp) == "original_or_secret"
    assert classify_open("outside.txt", "w", 0, temp) == "persistent_write"


def test_launch_bytecode_prefix_is_a_write_root_but_stays_bounded(tmp_path):
    temp = owned_temp(tmp_path)
    prefix = tmp_path / "cache-prefix"
    nested = prefix / "mirror" / "torch"
    nested.mkdir(parents=True)
    assert classify_open(prefix / "module.pyc", "wb", 0, temp, (prefix,)) is None
    assert classify_open(nested / "other.cpython-313.pyc", None, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, temp, (prefix,)) is None
    assert classify_open(prefix / "module.pyc", "wb", 0, temp) == "persistent_write"
    assert classify_open(temp.parent / "escape.pyc", "wb", 0, temp, (prefix,)) == "persistent_write"
    assert classify_open(str(prefix) + "-sibling/inside.pyc", "wb", 0, temp, (prefix,)) == "persistent_write"


def test_non_path_and_fd_opens_are_outside_the_file_rules(tmp_path):
    temp = owned_temp(tmp_path)
    assert classify_open(3, "r+b", 0, temp) is None
    assert classify_open(None, "r", 0, temp) is None


def test_audit_hook_raises_permission_error_and_reports_events(tmp_path):
    temp = owned_temp(tmp_path)
    prefix = tmp_path / "cache-prefix"
    prefix.mkdir()
    events = []
    hook = make_audit_hook(temp, lambda stage, **extra: events.append((stage, extra)), (prefix,))
    with pytest.raises(PermissionError, match="owned TEMP"):
        hook("open", ("outside.txt", "w", 0))
    with pytest.raises(PermissionError, match="networking"):
        hook("socket.connect", ("10.0.0.1", 443))
    hook("open", (os.devnull, "r+b", 0))
    hook("open", (temp / "fine.bin", "wb", 0))
    hook("open", (prefix / "mod.cpython-313.pyc", "wb", 0))
    hook("os.mkdir", (prefix / "mirror",))
    assert [stage for stage, _ in events] == ["GUARD_REJECTED", "GUARD_REJECTED"]
    assert events[0][1]["operation"] == "persistent_write"


def test_previous_revision_guard_replica_had_the_devnull_false_positive(tmp_path):
    """Replicates the ROOT c3-20261028 probe rule verbatim as revision evidence."""
    temp = owned_temp(tmp_path)
    mode = "r+b"
    write = isinstance(mode, str) and any(char in mode for char in "wax+")
    assert write and not Path(os.devnull).resolve().is_relative_to(temp.resolve()), (
        "historical guard rejected the standard discard device: torch->dill "
        "open(os.devnull, 'r+b') was misread as a persistent write")
