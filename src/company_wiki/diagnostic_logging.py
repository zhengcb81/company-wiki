"""Redacted local diagnostics with process-safe rotation."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time

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
        self.failed = False
        self.setFormatter(_Formatter("%(asctime)sZ %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S"))

    def doRollover(self) -> None:
        if self.stream is not None:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]  # The delayed handler reopens on append.
        try:
            self.path.replace(self.path.with_name(self.path.name + ".1"))
        except OSError:
            # A sharing violation must preserve the older backup as well as
            # the active file. The handler can still append the new event.
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
        self.failed = True
        if self.warn_on_stderr and sys.stderr is not None:
            try:
                error = sys.exc_info()[0]
                error_name = error.__name__ if error is not None else "OSError"
                print(f"company-wiki local diagnostic could not be written ({error_name})",
                      file=sys.stderr)
            except (OSError, ValueError):
                pass


def _write_record(path: Path, record: logging.LogRecord, *, warn_on_stderr: bool) -> bool:
    writer = _LockedLog(path, warn_on_stderr=warn_on_stderr)
    try:
        writer.handle(record)
    finally:
        writer.close()
    return not writer.failed


class _LogRoute(logging.Handler):
    def __init__(self, paths: Callable[[], tuple[Path, ...]], on_loss: Callable[[], None] | None) -> None:
        super().__init__()
        self._paths = paths
        self._on_loss = on_loss
        self._loss_recorded = False

    def emit(self, record: logging.LogRecord) -> None:
        for path in self._paths():
            if _write_record(path, record, warn_on_stderr=False):
                return
        if self._on_loss is not None and not self._loss_recorded:
            self._loss_recorded = True
            self._on_loss()


@contextmanager
def diagnostic_log(
    logger: logging.Logger, path: Path | Callable[[], tuple[Path, ...]], *, warn_on_stderr: bool = True,
    in_scope: Callable[[], bool] | None = None, on_loss: Callable[[], None] | None = None,
) -> Iterator[None]:
    """Route a scoped logger to the owner destinations without retaining open files."""
    handler: logging.Handler = (_LogRoute(path, on_loss) if callable(path)
                                else _LockedLog(path, warn_on_stderr=warn_on_stderr))
    if in_scope is not None:
        handler.addFilter(lambda _record: in_scope())
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()


def append_diagnostic(path: Path, text: str, *, warn_on_stderr: bool = True) -> bool:
    """Attempt one redacted record without changing the calling logger."""
    record = logging.makeLogRecord({
        "name": "company_wiki.feedback_host", "levelno": logging.ERROR, "levelname": "ERROR", "msg": text,
    })
    return _write_record(path, record, warn_on_stderr=warn_on_stderr)
