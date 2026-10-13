"""The shared write boundary handles transient Windows rename contention."""
import os

import pytest

from company_wiki._atomic_file import atomic_output


@pytest.mark.parametrize("winerror", [5, 32, 33])
def test_windows_busy_replace_retries_same_closed_owned_stage(tmp_path, monkeypatch, winerror):
    target = tmp_path / "export"
    target.write_bytes(b"old")
    calls = []
    replace = os.replace

    def busy_once(source, destination):
        calls.append(source)
        assert target.read_bytes() == b"old"
        if len(calls) == 1:
            error = PermissionError("Windows destination temporarily busy")
            error.winerror = winerror
            raise error
        replace(source, destination)

    monkeypatch.setattr(os, "replace", busy_once)
    with atomic_output(target) as stream:
        stream.write(b"new complete")
    assert len(calls) == 2 and calls[0] == calls[1]
    assert target.read_bytes() == b"new complete"
    assert set(tmp_path.iterdir()) == {target}


def test_persistent_busy_replace_is_bounded_and_preserves_other_files(tmp_path, monkeypatch):
    target = tmp_path / "export"
    target.write_bytes(b"old")
    foreign = tmp_path / "export.foreign.tmp"
    foreign.write_bytes(b"foreign")
    calls = []
    delays = []

    def always_busy(source, destination):
        calls.append(source)
        error = PermissionError("Windows destination stays busy")
        error.winerror = 32
        raise error

    monkeypatch.setattr(os, "replace", always_busy)
    monkeypatch.setattr("company_wiki._atomic_file.time.sleep", delays.append)
    with pytest.raises(PermissionError, match="stays busy"):
        with atomic_output(target) as stream:
            stream.write(b"new")
    assert 1 < len(calls) <= 5
    assert 0 < sum(delays) <= 0.1
    assert len(set(calls)) == 1
    assert target.read_bytes() == b"old" and foreign.read_bytes() == b"foreign"
    assert set(tmp_path.iterdir()) == {target, foreign}


@pytest.mark.parametrize("error_type", [PermissionError, FileNotFoundError])
def test_ordinary_filesystem_error_is_not_retried(tmp_path, monkeypatch, error_type):
    calls = []

    def forbidden(source, destination):
        calls.append(source)
        raise error_type("permanent filesystem error")

    monkeypatch.setattr(os, "replace", forbidden)
    with pytest.raises(error_type, match="permanent filesystem error"):
        with atomic_output(tmp_path / "export") as stream:
            stream.write(b"new")
    assert len(calls) == 1 and list(tmp_path.iterdir()) == []
