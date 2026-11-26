"""Host-owned process history in the configured F4 database."""

from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from stat import S_ISREG

from .local_host import host_path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS intake_processes (
    step_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    entry TEXT NOT NULL,
    pending_observation TEXT
)
"""
_INDEX = """
CREATE INDEX IF NOT EXISTS intake_process_run ON intake_processes (run_id, owner, attempt_id)
"""
_OUTBOX_INDEX = """
CREATE INDEX IF NOT EXISTS intake_process_pending ON intake_processes (owner)
WHERE pending_observation IS NOT NULL
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def implementation() -> str:
    digest = sha256()
    try:
        for name in ("intake.py", "process_history.py"):
            digest.update(Path(__file__).with_name(name).read_bytes())
    except OSError:
        return "feedback-intake/1"
    return f"feedback-intake/1/{digest.hexdigest()}"


class ProcessHistory:
    """Store what the host knows, independently of observation delivery."""

    def __init__(self, database: Path) -> None:
        self.database = database.absolute()

    def save(self, entry: dict, pending: dict | None = None) -> None:
        with closing(sqlite3.connect(host_path(self.database), timeout=0.25)) as conn, conn:
            conn.execute(_SCHEMA)
            conn.execute(_INDEX)
            conn.execute(_OUTBOX_INDEX)
            conn.execute(
                "INSERT INTO intake_processes VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(step_id) DO UPDATE SET entry = excluded.entry, "
                "pending_observation = excluded.pending_observation "
                "WHERE json_extract(intake_processes.entry, '$.finished_at') IS NULL",
                (entry["step_id"], entry["owner"], entry["run_id"], entry["attempt_id"],
                 entry["started_at"], json.dumps(entry, ensure_ascii=True),
                 json.dumps(pending, ensure_ascii=True) if pending is not None else None),
            )

    def observations(self, owners: set[str]) -> list[tuple[str, bytes]]:
        with self._read_connection() as conn:
            if not self._has_table(conn):
                return []
            return [
                (step_id, raw.encode("utf-8"))
                for owner in sorted(owners)
                for step_id, raw in conn.execute(
                    "SELECT step_id, pending_observation FROM intake_processes "
                    "WHERE owner = ? AND pending_observation IS NOT NULL ORDER BY started_at, step_id", (owner,),
                )
            ]

    def delivered(self, step_id: str) -> None:
        with closing(sqlite3.connect(host_path(self.database), timeout=0.25)) as conn, conn:
            conn.execute(
                "UPDATE intake_processes SET pending_observation = NULL WHERE step_id = ?", (step_id,),
            )

    def completed(self, context: dict) -> bool:
        with self._read_connection() as conn:
            if not self._has_table(conn):
                return False
            return conn.execute(
                "SELECT 1 FROM intake_processes WHERE step_id = ? AND owner = ? AND run_id = ? "
                "AND attempt_id = ? AND json_extract(entry, '$.finished_at') IS NOT NULL",
                tuple(context[key] for key in ("step_id", "owner", "run_id", "attempt_id")),
            ).fetchone() is not None

    def _read_connection(self):
        return closing(sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True, timeout=0.25))

    @staticmethod
    def _has_table(conn: sqlite3.Connection) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'intake_processes' AND type = 'table'",
        ).fetchone() is not None

    def read(self, run_id: str, *, owner: str | None, attempt_id: str | None) -> list[dict]:
        try:
            if not S_ISREG(host_path(self.database).stat().st_mode):
                raise IsADirectoryError("process history is not a regular file")
        except FileNotFoundError:
            return []
        with self._read_connection() as conn:
            if not self._has_table(conn):
                return []
            return [json.loads(entry) for (entry,) in conn.execute(
                "SELECT entry FROM intake_processes WHERE run_id = ? "
                "AND (? IS NULL OR owner = ?) AND (? IS NULL OR attempt_id = ?) "
                "ORDER BY started_at, step_id",
                (run_id, owner, owner, attempt_id, attempt_id),
            )]
