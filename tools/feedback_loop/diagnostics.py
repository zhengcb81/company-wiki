"""Persist redacted diagnostics for the feedback loop's own detached commands."""
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, redirect_stderr
import logging
import os
from pathlib import Path
import sys
from typing import BinaryIO, TypeVar

from company_wiki.diagnostic_logging import append_diagnostic, diagnostic_log
from company_wiki.diagnostic_redaction import format_diagnostic_exception, redact_text
from company_wiki.diagnostic_stream import RedactedTextStream
from company_wiki.runtime_journal import diagnostic_paths

from .process_launch import background_argv


_LOG_PATH = "CWP_F4_ERROR_LOG"
_T = TypeVar("_T")

__all__ = ["append_diagnostic", "background_command", "background_environment",
           "background_stderr", "format_diagnostic_exception", "redact_text", "run_background"]


def background_environment(path: Path, environment: Mapping[str, str] | None = None) -> dict[str, str]:
    return {**(os.environ if environment is None else environment), _LOG_PATH: str(path.resolve())}


def background_command(module: str, *arguments: str) -> list[str]:
    return background_argv([sys.executable, "-B", "-m", "tools.feedback_loop._background", module, *arguments])


@contextmanager
def background_stderr(destination: Path) -> Iterator[BinaryIO]:
    """Detach from the caller's request pipes while retaining pre-wrapper errors."""
    bootstrap = destination.with_name(destination.name + ".bootstrap")
    for path in dict.fromkeys((bootstrap, *diagnostic_paths(bootstrap.name))):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            stream = path.open("ab", buffering=0)
        except (OSError, ValueError):
            continue
        with stream:
            yield stream
        return
    terminal = sys.stderr
    if terminal is not None:
        try:
            print("company-wiki background diagnostic could not be retained", file=terminal)
        except (OSError, ValueError):
            pass
    with open(os.devnull, "wb", buffering=0) as unavailable:
        yield unavailable


def run_background(run: Callable[[], _T]) -> _T:
    """Capture Python diagnostics in the existing child, without teeing raw stderr."""
    destination = os.environ.pop(_LOG_PATH, None)
    terminal = sys.stderr
    if not destination:
        try:
            return run()
        except Exception as exc:
            if terminal is not None:
                try:
                    print(format_diagnostic_exception(exc), file=terminal)
                except (OSError, ValueError):
                    # The business exit is still the original failure.
                    pass
            raise SystemExit(1) from exc
    path = Path(destination)

    def destinations() -> tuple[Path, ...]:
        return tuple(dict.fromkeys((path, *diagnostic_paths("runtime_errors.log"))))

    loss_notified = False

    def unavailable() -> None:
        nonlocal loss_notified
        if loss_notified or terminal is None:
            return
        loss_notified = True
        try:
            print("company-wiki background diagnostic could not be retained", file=terminal)
        except (OSError, ValueError):
            pass

    def persist(text: str) -> None:
        if text.strip() and not any(
            append_diagnostic(candidate, text, warn_on_stderr=False) for candidate in destinations()
        ):
            unavailable()

    def persist_stderr(text: str) -> None:
        if text.strip():
            persist("Background command stderr\n" + text.removesuffix("\n"))

    captured = RedactedTextStream(persist_stderr)
    with diagnostic_log(logging.getLogger(), destinations, on_loss=unavailable):
        try:
            with redirect_stderr(captured):
                return run()
        except Exception as exc:
            persist(f"Background command failed\n{format_diagnostic_exception(exc)}")
            raise SystemExit(1) from exc
        finally:
            captured.finish()
