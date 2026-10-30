"""One local replacement boundary for derived files and validated metadata.

Callers own immutable-content checks and concurrency scope. This primitive only
owns its exclusive same-directory staging file, closes it before replacement,
and cleans that file on failure; it never deletes another operation's staging.
The staging name is short, random and independent of the destination basename,
and Windows paths beyond the native limit are opened through
_atomic_path.openable, so neither the staging shape nor any extended-length
form is visible to callers.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import IO, Iterator, Literal

from company_wiki._atomic_path import openable, stage_dir


def _replace_closed_stage(source: str, destination: Path) -> None:
    """Windows can reject simultaneous renames even when all files are closed.

    Retry only known Windows contention codes, on this same owned staging file.
    Four attempts and 35ms total backoff bound persistent access/sharing errors;
    ordinary permission failures propagate immediately. This does not arbitrate
    immutable writes or change a caller's transaction/lock responsibility.
    """
    delays = (0.0, 0.005, 0.010, 0.020)
    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        try:
            os.replace(openable(source), openable(destination))
            return
        except OSError as exc:
            if getattr(exc, "winerror", None) not in {5, 32, 33} or attempt == len(delays) - 1:
                raise


@contextmanager
def atomic_output(
    path: Path, *, mode: Literal["w", "wb"] = "wb",
    encoding: str | None = None, newline: str | None = None, sync: bool = False,
) -> Iterator[IO]:
    """Write one complete replacement; the caller must create the parent.

    No new lock or default fsync: a higher-level immutable writer keeps its
    existing transaction/lock and requests sync where it already required it.
    """
    if mode not in {"w", "wb"}:
        raise ValueError("atomic output mode must be w or wb")
    stage: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode=mode, encoding=encoding, newline=newline,
            dir=stage_dir(path.parent), prefix=".atomic-", suffix=".tmp", delete=False,
        ) as stream:
            stage = stream.name
            yield stream
            stream.flush()
            if sync:
                os.fsync(stream.fileno())
        _replace_closed_stage(stage, path)
    finally:
        if stage is not None:
            # A stage that another handle keeps open must not replace the
            # fault that got us here: the inert leftover file stays visible,
            # the original failure stays raised, and the cleanup problem is
            # attached as a note. Only a genuinely unexpected cleanup failure
            # with nothing in flight propagates on its own.
            original = sys.exc_info()[1]
            try:
                os.unlink(openable(stage))
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                if original is None:
                    raise
                original.add_note(
                    f"atomic stage cleanup failed "
                    f"({type(cleanup_error).__name__}: {cleanup_error})")


__all__ = ["atomic_output"]
