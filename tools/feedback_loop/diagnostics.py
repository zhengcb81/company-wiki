"""Persist redacted diagnostics for the feedback loop's own detached commands."""
from collections.abc import Callable
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from typing import TypeVar

from company_wiki.diagnostic_redaction import format_diagnostic_exception, redact_text


_LOG_PATH = "CWP_F4_ERROR_LOG"
_T = TypeVar("_T")
_logger = logging.getLogger(__name__)


def background_environment(path: Path) -> dict[str, str]:
    return {**os.environ, _LOG_PATH: str(path.resolve())}


class _RedactedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return str(redact_text(super().format(record)))


class _DiagnosticFileHandler(RotatingFileHandler):
    def doRollover(self) -> None:
        try:
            super().doRollover()
        except OSError:
            # Other Windows readers may hold the log open. Keep the original
            # diagnostic and let a later write retry the rotation.
            pass


def run_background(run: Callable[[], _T]) -> _T:
    """Capture Python diagnostics in the existing child, without teeing raw stderr."""
    destination = os.environ.pop(_LOG_PATH, None)
    if not destination:
        return run()
    path = Path(destination)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = _DiagnosticFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=1, encoding="utf-8")
    except OSError as exc:
        _logger.warning("Cannot open background diagnostics\n%s", format_diagnostic_exception(exc))
        return run()

    root = logging.getLogger()
    handler.setFormatter(_RedactedFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    try:
        return run()
    except Exception as exc:
        _logger.error("Background command failed\n%s", format_diagnostic_exception(exc))
        raise SystemExit(1) from None
    finally:
        root.removeHandler(handler)
        handler.close()
