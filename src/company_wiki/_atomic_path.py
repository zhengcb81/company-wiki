"""Path forms the shared atomic writer can open; no I/O lives here.

Windows rejects plain paths beyond the native limit with a path-not-found
error even when the target itself is valid, so every path the shared writer
opens goes through this leaf. Paths inside the limit come back verbatim and
non-Windows paths always do, which keeps the common case byte-identical and
keeps extended-length representations private to the writer. Measured NTFS
facts this encodes (LongPathsEnabled=0 host, tools/w22_atomic_probe.py):
plain file creation works up to 259 characters and fails from 260; plain
directory creation stops at 247; extended-length forms and mixed
extended-to-plain replacements work regardless.
"""
from __future__ import annotations

import os
from pathlib import Path

# CreateFileW accepts at most 259 usable characters without an
# extended-length prefix; a longer plain path fails before the file system is
# consulted, regardless of whether the destination itself exists.
NATIVE_PATH_LIMIT = 259

# One path separator plus the writer's bounded stage name
# (".atomic-" + 8 random characters + ".tmp" = 20 characters).
STAGE_NAME_RESERVE = 21


def _extended_form(absolute: str) -> str:
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute


def _needs_extension(absolute: str, required: int) -> bool:
    return os.name == "nt" and len(absolute) + required > NATIVE_PATH_LIMIT


def openable(path: Path | str) -> str:
    """Return a string form this process can open for one existing path.

    Short paths are returned exactly as given, preserving relative and caller
    representations. On Windows, a longer path is re-expressed with the
    extended-length prefix: drive paths as ``\\?\\C:\\...`` and UNC paths as
    ``\\?\\UNC\\server\\share\\...``. Long relative paths are made absolute
    first because the prefix has no relative form; already prefixed input is
    returned unchanged, so the function is idempotent.
    """
    given = os.fspath(path)
    if os.name != "nt" or len(given) <= NATIVE_PATH_LIMIT:
        return given
    if given.startswith("\\\\?\\"):
        return given
    return _extended_form(os.path.abspath(given))


def stage_dir(parent: Path | str) -> str:
    """Return a directory form in which a bounded random stage file fits.

    The writer creates its stage with a fixed-shape 20-character name inside
    parent, so the deciding length is parent plus STAGE_NAME_RESERVE, not the
    destination basename. When that would cross the native limit the parent
    is returned in extended-length form; the stage is then created, replaced
    and removed entirely through prefixed names while the caller's own path
    representation stays untouched.
    """
    given = os.fspath(parent)
    if os.name != "nt":
        return given
    if given.startswith("\\\\?\\"):
        return given
    absolute = given if os.path.isabs(given) else os.path.abspath(given)
    if not _needs_extension(absolute, STAGE_NAME_RESERVE):
        return given
    return _extended_form(absolute)


__all__ = ["NATIVE_PATH_LIMIT", "STAGE_NAME_RESERVE", "openable", "stage_dir"]
