"""File-sharing recovery spends only the existing absolute OCR deadline."""
import errno
from types import SimpleNamespace

import pytest

from company_wiki.document_normalization import isolated_ocr as boundary
from company_wiki.document_normalization.errors import NormalizationLimitError


class Clock:
    def __init__(self):
        self.now = 10.0
        self.sleeps = []
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        assert seconds > 0
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def windows_clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(boundary, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(boundary, "time", clock)
    return clock


def test_sharing_retry_keeps_exact_deadline_and_stops_without_another_attempt(windows_clock):
    calls = []
    def busy():
        calls.append(windows_clock.now)
        raise PermissionError(errno.EACCES, "owned handoff is busy")
    with pytest.raises(NormalizationLimitError, match="deadline"):
        boundary._retry_owned_io(busy, deadline=10.025)
    assert calls and all(instant < 10.025 for instant in calls)
    assert windows_clock.now == pytest.approx(10.025)
    assert max(windows_clock.sleeps) <= boundary._POLL_SECONDS


def test_sharing_retries_only_file_operation_not_native_call(windows_clock):
    calls = []
    def operation():
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError(errno.EACCES, "busy")
        return b"same immutable output"
    assert boundary._retry_owned_io(operation, deadline=11.0) == b"same immutable output"
    assert len(calls) == 2


@pytest.mark.parametrize("platform,error", [("posix", PermissionError(errno.EACCES, "ACL")),
    ("nt", FileNotFoundError(errno.ENOENT, "missing")), ("nt", OSError(errno.EIO, "I/O failure"))])
def test_nonsharing_or_nonwindows_errors_are_never_retried(monkeypatch, platform, error):
    clock = Clock()
    monkeypatch.setattr(boundary, "os", SimpleNamespace(name=platform))
    monkeypatch.setattr(boundary, "time", clock)
    def operation():
        raise error
    with pytest.raises(type(error)) as caught:
        boundary._retry_owned_io(operation, deadline=11.0)
    assert caught.value is error and clock.sleeps == []


def test_expired_deadline_does_not_attempt_file_io(windows_clock):
    def forbidden():
        raise AssertionError("expired operation ran")
    with pytest.raises(NormalizationLimitError, match="deadline"):
        boundary._retry_owned_io(forbidden, deadline=10.0)


@pytest.mark.parametrize("finished_at", [11.0, 12.0])
def test_successful_file_io_cannot_start_next_stage_after_deadline(windows_clock, finished_at):
    calls = []
    def operation():
        calls.append(1)
        windows_clock.now = finished_at
        return b"late result"
    with pytest.raises(NormalizationLimitError, match="deadline"):
        boundary._retry_owned_io(operation, deadline=11.0)
    assert calls == [1]
    assert windows_clock.sleeps == []
