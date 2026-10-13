"""One local replacement boundary for derived files and validated metadata.

Callers own immutable-content checks and concurrency scope. This primitive only
owns its exclusive same-directory staging file, closes it before replacement,
and cleans that file on failure; it never deletes another operation's staging.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import time
from typing import IO, Iterator, Literal


def _replace_closed_stage(source: Path, destination: Path) -> None:
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
            os.replace(source, destination)
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
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode=mode, encoding=encoding, newline=newline,
            dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            yield stream
            stream.flush()
            if sync:
                os.fsync(stream.fileno())
        _replace_closed_stage(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


__all__ = ["atomic_output"]
