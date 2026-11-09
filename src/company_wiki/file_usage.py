"""Read-only measurements of filesystem storage owned by a service."""

from pathlib import Path
import stat


def file_tree_bytes(path: Path) -> int:
    """Count regular files, including a single file at the root if present."""
    try:
        info = path.stat()
    except FileNotFoundError:
        return 0
    if stat.S_ISREG(info.st_mode):
        return info.st_size
    total = 0
    for item in path.rglob("*"):
        try:
            info = item.stat()
        except FileNotFoundError:
            # SQLite sidecars and temporary objects can disappear while sampled.
            continue
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


def database_file_sizes(path: Path) -> tuple[int, int, int]:
    """Measure a SQLite file and its WAL/SHM sidecars in baseline order."""
    return (
        file_tree_bytes(path),
        file_tree_bytes(path.with_name(path.name + "-wal")),
        file_tree_bytes(path.with_name(path.name + "-shm")),
    )


__all__ = ["database_file_sizes", "file_tree_bytes"]
