"""Redacted local diagnostics with process-safe rotation."""

from contextlib import contextmanager
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from typing import Iterator

from .diagnostic_redaction import redact_text
from .file_mutex import FileMutexLockedError, os_file_mutex, win32_filesystem_path

__all__ = ["append_diagnostic", "diagnostic_log"]


class _Formatter(logging.Formatter):
    @staticmethod
    def converter(seconds: float | None) -> time.struct_time:
        return time.gmtime(seconds)

    def format(self, record: logging.LogRecord) -> str:
        return str(redact_text(super().format(record)))


class _LockedLog(RotatingFileHandler):
    def __init__(self, path: Path, *, warn_on_stderr: bool) -> None:
        path = win32_filesystem_path(path)
        super().__init__(path, maxBytes=2 * 1024 * 1024, backupCount=1, encoding="utf-8", delay=True)
        self.path = path
        self.warn_on_stderr = warn_on_stderr
        self.setFormatter(_Formatter("%(asctime)sZ %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S"))

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except OSError:
            # Preserve this entry if an external Windows reader prevents rename.
            pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with os_file_mutex(self.path.with_suffix(self.path.suffix + ".lock"), timeout_seconds=0.25):
                try:
                    super().emit(record)
                finally:
                    # No process holds the data file open across the next rotation.
                    if self.stream is not None:
                        try:
                            self.stream.close()
                        finally:
                            self.stream = None  # type: ignore[assignment]  # FileHandler reopens delayed streams.
        except (OSError, FileMutexLockedError):
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802
        if self.warn_on_stderr and sys.stderr is not None:
            try:
                error = sys.exc_info()[0]
                error_name = error.__name__ if error is not None else "OSError"
                print(f"company-wiki local diagnostic could not be written ({error_name})",
                      file=sys.stderr)
            except (OSError, ValueError):
                pass


@contextmanager
def diagnostic_log(logger: logging.Logger, path: Path, *, warn_on_stderr: bool = True) -> Iterator[None]:
    """Attach one local sink for the lifetime of the outer command."""
    handler = _LockedLog(path, warn_on_stderr=warn_on_stderr)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()


def append_diagnostic(path: Path, text: str, *, warn_on_stderr: bool = True) -> None:
    """Persist one redacted record without changing the calling logger."""
    handler = _LockedLog(path, warn_on_stderr=warn_on_stderr)
    try:
        handler.handle(logging.makeLogRecord({
            "name": "company_wiki.feedback_host", "levelno": logging.ERROR, "levelname": "ERROR", "msg": text,
        }))
    finally:
        handler.close()
