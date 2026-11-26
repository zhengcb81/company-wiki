"""Offline reproduction of the F4 supervisor's retained process evidence."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from unittest.mock import patch

from tools.feedback_loop import intake


OWNER = "audit-fixture-owner"


class WarningCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.warnings: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.warnings.append(record.name)


def write_config(root: Path) -> tuple[Path, Path]:
    settings = root / "settings.json"
    hosts = root / "hosts.json"
    settings.write_text(json.dumps({
        "state": "actions.sqlite",
        "owners": {OWNER: {"cwd": str(root), "observation_dir": "observations"}},
    }), encoding="utf-8")
    hosts.write_text(json.dumps({
        OWNER: [sys.executable, "-B", "-m", "tools.feedback_loop.local_host",
                "--config", str(settings), "rpc"],
    }), encoding="utf-8")
    return settings, hosts


def observations_in_db(database: Path) -> int:
    if not database.is_file():
        return 0
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM actions WHERE json_extract(request, '$.kind') = 'observe'"
        ).fetchone()[0]


def trial(root: Path, *, exit_code: int, block_primary: bool, block_fallback: bool) -> dict:
    root.mkdir()
    settings, hosts = write_config(root)
    primary, fallback = root / "observations", root / ".intake-recovery"
    if block_primary:
        primary.touch()
    if block_fallback:
        fallback.touch()
    child = (
        "from pathlib import Path; "
        "p=Path('invocations.txt'); "
        "p.write_text((p.read_text() if p.exists() else '')+'x'); "
        f"raise SystemExit({exit_code})"
    )
    handler = WarningCapture()
    logger = logging.getLogger("tools.feedback_loop.intake")
    logger.addHandler(handler)
    try:
        with patch.object(intake, "wake"):
            result = intake.run_observed(settings, hosts, OWNER, [sys.executable, "-B", "-c", child], 0)
    finally:
        logger.removeHandler(handler)
    processes = sum(len(list(path.glob("*.process"))) for path in (primary, fallback) if path.is_dir())
    ready_before = sum(len(list(path.glob("*.ready"))) for path in (primary, fallback) if path.is_dir())
    first = json.loads(subprocess.check_output([
        sys.executable, "-B", "-m", "tools.feedback_loop.intake", "--settings", str(settings),
        "--hosts", str(hosts), "--wait-seconds", "0", "drain", "--owner", OWNER,
    ], timeout=20))
    ready_after = sum(len(list(path.glob("*.ready"))) for path in (primary, fallback) if path.is_dir())
    return {
        "exit": result,
        "child_invocations": (root / "invocations.txt").read_text().count("x"),
        "supervisor_warnings": len(handler.warnings),
        "process_receipts": processes,
        "ready_before_drain": ready_before,
        "ready_after_drain": ready_after,
        "processed": first["processed"],
        "retained_observations": observations_in_db(root / "actions.sqlite"),
        "drain_diagnostics": [item["code"] for item in first["diagnostics"]],
    }


def main() -> None:
    scratch = Path.cwd() / ".planning"
    with tempfile.TemporaryDirectory(prefix="f4-reaudit-", dir=scratch) as temp:
        root = Path(temp)
        result = {
            "success_without_owner_sidecar": trial(root / "ok", exit_code=0, block_primary=False,
                                                   block_fallback=False),
            "failure_primary_blocked": trial(root / "one", exit_code=19, block_primary=True,
                                             block_fallback=False),
            "failure_both_blocked": trial(root / "both", exit_code=19, block_primary=True,
                                          block_fallback=True),
        }
    assert all(row["child_invocations"] == 1 for row in result.values())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
