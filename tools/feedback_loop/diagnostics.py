"""Persist redacted diagnostics for the feedback loop's own detached commands."""
from collections.abc import Callable
from contextlib import redirect_stderr
from io import TextIOBase
import logging
import os
from pathlib import Path
import re
import sys
from typing import TypeVar

# Source-checkout commands also run with a bare interpreter. Use the canonical
# package name so the scanner and its callers share the same module instance.
_SRC = Path(__file__).resolve().parents[2] / "src"
if (_SRC / "company_wiki").is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from company_wiki.diagnostic_logging import append_diagnostic, diagnostic_log  # noqa: E402
from company_wiki.diagnostic_redaction import (  # noqa: E402
    REDACT,
    credential_continues,
    format_diagnostic_exception,
    redact_text,
)


_LOG_PATH = "CWP_F4_ERROR_LOG"
_T = TypeVar("_T")
_TRACEBACK_LINE = re.compile(
    r"^(?:Traceback \(|[ \t]+File \"|(?:[A-Za-z_]\w*\.)*"
    r"[A-Za-z_]*?(?:Error|Exception|Warning|Interrupt|Exit):(?:\s|$))",
)

__all__ = ["append_diagnostic", "background_command", "background_environment",
           "format_diagnostic_exception", "redact_text", "run_background"]


def background_environment(path: Path) -> dict[str, str]:
    return {**os.environ, _LOG_PATH: str(path.resolve())}


def background_command(module: str, *arguments: str) -> list[str]:
    return [sys.executable, "-B", "-m", "tools.feedback_loop._background", module, *arguments]


class _DetachedStderr(TextIOBase):
    """Redact complete lines and persist them before a worker can be stopped."""

    encoding = "utf-8"
    _MAX_PENDING = 2 * 1024 * 1024

    def __init__(self, destination: Path) -> None:
        self._destination = destination
        self._pending = ""
        self._discard_line = False
        self._awaiting_credential = False
        self._folded_credential = False

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        parts = value.split("\n")
        records: list[str] = []
        for index, part in enumerate(parts):
            if not self._discard_line:
                if len(self._pending) + len(part) > self._MAX_PENDING:
                    records.append("[oversize stderr line omitted]")
                    self._pending = ""
                    self._discard_line = True
                    self._awaiting_credential = True
                else:
                    self._pending += part
            if index < len(parts) - 1:
                if not self._discard_line and self._pending.strip():
                    records.append(self._redacted_line())
                self._discard_line = False
                self._pending = ""
        if records:
            self._persist("\n".join(records))
        return len(value)

    def _redacted_line(self) -> str:
        line = self._pending.rstrip("\r")
        continuation = self._awaiting_credential or (
            self._folded_credential and line.startswith((" ", "\t"))
        )
        self._awaiting_credential = credential_continues(line)
        self._folded_credential = bool(continuation and not _TRACEBACK_LINE.match(line))
        return REDACT if self._folded_credential else str(redact_text(line))

    def _persist(self, text: str) -> None:
        append_diagnostic(
            self._destination, f"Background command stderr\n{text}", warn_on_stderr=False,
        )

    def finish(self) -> None:
        if self._pending.strip():
            self._persist(self._redacted_line())
            self._pending = ""


def run_background(run: Callable[[], _T]) -> _T:
    """Capture Python diagnostics in the existing child, without teeing raw stderr."""
    destination = os.environ.pop(_LOG_PATH, None)
    if not destination:
        return run()
    path = Path(destination)
    captured = _DetachedStderr(path)
    with diagnostic_log(logging.getLogger(), path, warn_on_stderr=False):
        try:
            with redirect_stderr(captured):
                return run()
        except Exception as exc:
            append_diagnostic(
                path, f"Background command failed\n{format_diagnostic_exception(exc)}",
                warn_on_stderr=False,
            )
            raise SystemExit(1) from None
        finally:
            captured.finish()
