"""Shared SQLite connection behavior used by catalog read and write owners."""

from __future__ import annotations

import sqlite3


def configure_tolerant_sqlite_text_decoding(connection: sqlite3.Connection) -> None:
    """Decode malformed TEXT visibly instead of letting fetch operations crash.

    SQLite may contain historical TEXT values with invalid UTF-8 bytes. The
    replacement character preserves the fact that content was malformed while
    allowing the owning reader to report the row-level metadata state.
    """
    connection.text_factory = lambda raw: raw.decode("utf-8", "replace")
