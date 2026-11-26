"""Redact fragmented diagnostic text before crossing a durable boundary."""
from __future__ import annotations

import codecs
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stderr, redirect_stdout
from io import TextIOBase
import os
import re
import sys
from threading import Lock, Thread
from typing import TextIO

from .diagnostic_redaction import REDACT, authorization_header, credential_continues, redact_text

__all__ = ["RedactedTextStream", "capture_diagnostic_streams"]

_TRACEBACK_LINE = re.compile(
    r"^(?:Traceback \(|[ \t]+File \"|(?:[A-Za-z_]\w*\.)*"
    r"[A-Za-z_]*?(?:Error|Exception|Warning|Interrupt|Exit):(?:\s|$))",
)


class RedactedTextStream(TextIOBase):
    """Send complete redacted lines to a sink, without teeing incoming bytes."""

    encoding = "utf-8"

    def __init__(self, persist: Callable[[str], None], *, max_pending_chars: int = 2 * 1024 * 1024) -> None:
        self._persist = persist
        self._max_pending_chars = max_pending_chars
        self._lock = Lock()
        self._pending = ""
        self._discard_line = False
        self._awaiting_credential = False
        self._folded_credential = False

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeError("diagnostic value must be text")
        with self._lock:
            parts = value.split("\n")
            records: list[str] = []
            for index, part in enumerate(parts):
                self._append(part, records)
                if index < len(parts) - 1:
                    self._end_line(records)
            if records:
                self._persist("".join(records))
        return len(value)

    def _append(self, part: str, records: list[str]) -> None:
        if self._discard_line:
            return
        if len(self._pending) + len(part) > self._max_pending_chars:
            records.append("[oversize diagnostic line omitted]\n")
            self._pending = ""
            self._discard_line = True
            self._awaiting_credential = True
        else:
            self._pending += part

    def _end_line(self, records: list[str]) -> None:
        if not self._discard_line:
            content = self._redacted_line() if self._pending.strip() else self._pending
            records.append(content + "\n")
        self._pending = ""
        self._discard_line = False

    def _redacted_line(self) -> str:
        line = self._pending.removesuffix("\r")
        continuation = self._awaiting_credential or (
            self._folded_credential and line.startswith((" ", "\t"))
        )
        self._awaiting_credential = credential_continues(line)
        folded = bool(continuation and not _TRACEBACK_LINE.match(line))
        self._folded_credential = folded or authorization_header(line)
        return REDACT if folded else str(redact_text(line))

    def finish(self) -> None:
        """End capture without allowing a normal stream flush to split a credential."""
        with self._lock:
            if self._pending and not self._discard_line:
                self._persist(self._redacted_line())
            self._pending = ""


def _drain_pipe(descriptor: int, stream: RedactedTextStream) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    with os.fdopen(descriptor, "rb", buffering=0) as source:
        while data := source.read(8192):
            stream.write(decoder.decode(data))
    stream.write(decoder.decode(b"", final=True))
    stream.finish()


@contextmanager
def _capture_descriptor(descriptor: int, stream: RedactedTextStream) -> Iterator[None]:
    with ExitStack() as closes:
        saved = os.dup(descriptor)
        closes.callback(os.close, saved)
        inheritable = os.get_inheritable(descriptor)
        read_fd, write_fd = os.pipe()
        thread = Thread(target=_drain_pipe, args=(read_fd, stream), name="diagnostic-pipe", daemon=True)
        try:
            thread.start()
        except RuntimeError:
            os.close(read_fd)
            os.close(write_fd)
            raise
        closes.callback(thread.join, 2.0)
        try:
            # CLI descendants must not retain a pipe the caller is trying to drain.
            os.dup2(write_fd, descriptor, inheritable=False)
        finally:
            os.close(write_fd)
        closes.callback(os.dup2, saved, descriptor, inheritable=inheritable)
        yield


def _uses_descriptor(stream: TextIOBase | TextIO, descriptor: int) -> bool:
    try:
        return stream.fileno() == descriptor
    except (AttributeError, OSError, ValueError):
        return False


@contextmanager
def capture_diagnostic_streams(persist: Callable[[str, str], None]) -> Iterator[None]:
    """Reserve both machine streams while capturing native and Python diagnostics."""
    sys.stdout.flush()
    sys.stderr.flush()
    stdout = RedactedTextStream(lambda text: persist("stdout", text))
    stderr = RedactedTextStream(lambda text: persist("stderr", text))
    native_out = RedactedTextStream(lambda text: persist("native stdout", text))
    native_err = RedactedTextStream(lambda text: persist("native stderr", text))
    python_out = nullcontext() if _uses_descriptor(sys.stdout, 1) else redirect_stdout(stdout)
    python_err = nullcontext() if _uses_descriptor(sys.stderr, 2) else redirect_stderr(stderr)
    try:
        with (_capture_descriptor(1, native_out), _capture_descriptor(2, native_err),
              python_out, python_err):
            try:
                yield
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
    finally:
        stdout.finish()
        stderr.finish()
