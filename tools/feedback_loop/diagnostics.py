"""Persist redacted diagnostics for the feedback loop's own detached commands."""
from collections.abc import Callable, Mapping
from contextlib import redirect_stderr
import logging
import os
from pathlib import Path
import sys
from typing import TypeVar

from .process_launch import background_argv

# Source-checkout commands also run with a bare interpreter. Use the canonical
# package name so the scanner and its callers share the same module instance.
_SRC = Path(__file__).resolve().parents[2] / "src"
if (_SRC / "company_wiki").is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from company_wiki.diagnostic_logging import append_diagnostic, diagnostic_log  # noqa: E402
from company_wiki.diagnostic_redaction import format_diagnostic_exception, redact_text  # noqa: E402
from company_wiki.diagnostic_stream import RedactedTextStream  # noqa: E402


_LOG_PATH = "CWP_F4_ERROR_LOG"
_T = TypeVar("_T")

__all__ = ["append_diagnostic", "background_command", "background_environment",
           "format_diagnostic_exception", "redact_text", "run_background"]


def background_environment(path: Path, environment: Mapping[str, str] | None = None) -> dict[str, str]:
    return {**(os.environ if environment is None else environment), _LOG_PATH: str(path.resolve())}


def background_command(module: str, *arguments: str) -> list[str]:
    return background_argv([sys.executable, "-B", "-m", "tools.feedback_loop._background", module, *arguments])


def run_background(run: Callable[[], _T]) -> _T:
    """Capture Python diagnostics in the existing child, without teeing raw stderr."""
    destination = os.environ.pop(_LOG_PATH, None)
    if not destination:
        return run()
    path = Path(destination)

    def persist(text: str) -> None:
        if text.strip():
            message = "Background command stderr\n" + text.removesuffix("\n")
            append_diagnostic(path, message, warn_on_stderr=False)

    captured = RedactedTextStream(persist)
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
