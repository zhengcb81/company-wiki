"""Persist redacted diagnostics for the feedback loop's own detached commands."""
import codecs
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, nullcontext, redirect_stderr, suppress
import logging
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock, Thread
from typing import BinaryIO, TypeVar

from company_wiki.diagnostic_logging import append_diagnostic, diagnostic_log
from company_wiki.diagnostic_redaction import format_diagnostic_exception, redact_text
from company_wiki.diagnostic_stream import RedactedTextStream
from company_wiki.file_mutex import win32_filesystem_path
from company_wiki.runtime_journal import diagnostic_paths

from .process_launch import BACKGROUND_CREATION_FLAGS, background_argv


_LOG_PATH = "CWP_F4_ERROR_LOG"
_BOOTSTRAP = (
    "import runpy, site, sys, traceback\n"
    "sys.argv[0] = '-m'\n"
    "try:\n"
    "    site.main()\n"
    "except BaseException:\n"
    "    traceback.print_exc()\n"
    "    raise SystemExit(1)\n"
    "runpy.run_module('tools.feedback_loop._background', run_name='__main__', alter_sys=True)\n"
)
_HANDOFF_SECONDS = 2.0
_T = TypeVar("_T")

__all__ = ["append_diagnostic", "launch_background", "format_diagnostic_exception", "redact_text", "run_background"]


def _runtime_destinations(destination: Path) -> tuple[Path, ...]:
    return tuple(dict.fromkeys((destination, *diagnostic_paths("runtime_errors.log"))))


def _report_loss() -> None:
    terminal = sys.stderr
    if terminal is not None:
        try:
            print("company-wiki background diagnostic could not be retained", file=terminal)
        except (OSError, ValueError):
            return


def _check_destination(path: Path) -> bool:
    try:
        path = win32_filesystem_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab"):
            return True
    except (OSError, ValueError):
        return False


def _drain(source: BinaryIO, captured: RedactedTextStream, on_loss: Callable[[], None]) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    try:
        with source:
            while data := source.read(8192):
                captured.write(decoder.decode(data))
        captured.write(decoder.decode(b"", final=True))
    except (OSError, ValueError):
        on_loss()
    finally:
        captured.finish()


def launch_background(
    module: str, destination: Path, *arguments: str, cwd: Path,
    stdout: BinaryIO | int = subprocess.DEVNULL, environment: Mapping[str, str] | None = None,
) -> subprocess.Popen:
    """Observe the interpreter's startup pipe until the child owns its diagnostic stream."""
    bootstrap = destination.with_name(destination.name + ".bootstrap")
    paths = tuple(dict.fromkeys((bootstrap, *diagnostic_paths(bootstrap.name), *_runtime_destinations(destination))))
    env = {**(os.environ if environment is None else environment), _LOG_PATH: str(destination.resolve())}
    lock = Lock()
    loss_notified = False

    def unavailable() -> None:
        nonlocal loss_notified
        with lock:
            if not loss_notified:
                loss_notified = True
                _report_loss()

    def persist(text: str) -> None:
        if text.strip() and not any(append_diagnostic(path, text, warn_on_stderr=False) for path in paths):
            unavailable()

    if not any(_check_destination(path) for path in paths):
        unavailable()
    child = subprocess.Popen(
        background_argv([sys.executable, "-B", "-S", "-c", _BOOTSTRAP, module, *arguments]),
        cwd=cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.PIPE, env=env,
        start_new_session=os.name != "nt", creationflags=BACKGROUND_CREATION_FLAGS,
    )
    assert child.stderr is not None
    reader = Thread(target=_drain, args=(child.stderr, RedactedTextStream(persist), unavailable),
                    name="feedback-bootstrap-stderr", daemon=True)
    try:
        reader.start()
    except RuntimeError:
        child.stderr.close()
        unavailable()
        return child
    reader.join(_HANDOFF_SECONDS)
    if reader.is_alive():
        unavailable()
    return child


@contextmanager
def _own_stderr(persist: Callable[[str], None], unavailable: Callable[[], None]) -> Iterator[None]:
    """Release the startup pipe and keep native descriptor writes inside this worker."""
    terminal = sys.__stderr__
    if terminal is not None:
        with suppress(OSError, ValueError):
            terminal.flush()
    try:
        reader = _replace_stderr(persist, unavailable)
    except (OSError, RuntimeError, ValueError):
        # The startup reader can still redact its own pipe. An unavailable
        # private pipe cannot stop the work or hold the original RPC streams.
        _report_loss()
        yield
        return
    try:
        yield
    finally:
        if terminal is not None:
            with suppress(OSError, ValueError):
                terminal.flush()
        with suppress(OSError):
            os.close(2)
        reader.join(_HANDOFF_SECONDS)


def _replace_stderr(persist: Callable[[str], None], unavailable: Callable[[], None]) -> Thread:
    read_fd, write_fd = os.pipe()
    source = os.fdopen(read_fd, "rb", buffering=0)
    reader = Thread(target=_drain, args=(source, RedactedTextStream(persist), unavailable),
                    name="feedback-native-stderr", daemon=True)
    try:
        reader.start()
    except RuntimeError:
        source.close()
        os.close(write_fd)
        raise
    try:
        # The replacement closes the inherited bootstrap writer. The private
        # writer must not be retained by the worker's owner subprocesses.
        os.dup2(write_fd, 2, inheritable=False)
    finally:
        os.close(write_fd)
    return reader


def run_background(run: Callable[[], _T], *, detached: bool = False) -> _T:
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
        return _runtime_destinations(path)

    loss_notified = False

    def unavailable() -> None:
        nonlocal loss_notified
        if loss_notified or terminal is None or detached:
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
    native_stderr = _own_stderr(persist_stderr, unavailable) if detached else nullcontext()
    with native_stderr, diagnostic_log(logging.getLogger(), destinations, on_loss=unavailable):
        try:
            with redirect_stderr(captured):
                return run()
        except Exception as exc:
            persist(f"Background command failed\n{format_diagnostic_exception(exc)}")
            raise SystemExit(1) from exc
        finally:
            captured.finish()
