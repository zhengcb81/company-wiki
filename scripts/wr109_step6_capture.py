"""WR-10.9 Step 6 post-login evidence capture.

Captures, right after a real Windows logon:
  1. Run-item command (HKCU Run CompanyWikiSourceCatalog)
  2. launcher event timeline (starting -> child_started -> exited/restarting)
  3. worker/supervisor process inventory + PID/start time
  4. control first-paint evidence (control_center.log first entry after boot)
  5. worker runtime (stage, heartbeat, code fingerprint match)
  6. 30/60/120 second snapshots of the above

Usage:
  python scripts/wr109_step6_capture.py --json-out artifacts/gates/source-catalog-bg/wr-10-9-step6-login-20260802.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]


def _run_cmd(
    args: list[str], timeout: int = 30, truncate: int = 3000
) -> dict[str, Any]:
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=timeout,
            cwd=str(PROJECT),
        )
        return {
            "exit": r.returncode,
            "stdout": r.stdout[:truncate] if truncate else r.stdout,
            "stderr": r.stderr[:1000],
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def _registry_run_item() -> dict[str, Any]:
    ps = (
        "$p='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run';"
        "$v=(Get-ItemProperty -Path $p -ErrorAction SilentlyContinue).CompanyWikiSourceCatalog;"
        "[pscustomobject]@{present=($null -ne $v); value=$v} | ConvertTo-Json -Compress"
    )
    return _run_cmd(["powershell", "-NoProfile", "-Command", ps])


def _launcher_events_tail(n: int = 12) -> list[dict[str, Any]]:
    path = PROJECT / ".source_catalog" / "worker_launcher_events.jsonl"
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-n:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"unparsed": line[:200]})
    except OSError as exc:
        events.append({"error": str(exc)})
    return events


def _process_events_tail(n: int = 8) -> list[dict[str, Any]]:
    path = PROJECT / ".source_catalog" / "worker_process_events.jsonl"
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-n:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"unparsed": line[:200]})
    except OSError as exc:
        events.append({"error": str(exc)})
    return events


def _control_log_tail(n: int = 15) -> list[str]:
    path = PROJECT / ".source_catalog" / "control_center.log"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-n:]
    except OSError:
        return []


def _worker_status() -> dict[str, Any]:
    return _run_cmd(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            str(PROJECT / "config" / "source_catalog.yaml"),
            "worker-status",
            "--worker-config",
            str(PROJECT / "config" / "source_catalog_worker.yaml"),
        ],
        timeout=30,
        truncate=0,
    )


def _snapshot(tag: str) -> dict[str, Any]:
    status = _worker_status()
    parsed = None
    try:
        parsed = json.loads(status.get("stdout") or "{}")
    except json.JSONDecodeError:
        pass
    return {
        "tag": tag,
        "taken_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "worker_status_exit": status.get("exit"),
        "worker_status_error": status.get("error"),
        "worker_status": parsed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--snapshots", nargs="*", default=["30", "60", "120"])
    args = ap.parse_args()

    boot_time = datetime.datetime.now(datetime.timezone.utc)
    evidence: dict[str, Any] = {
        "schema_version": "1.0",
        "work_unit": "WR-10.9 Step 6",
        "title": "next-login real Windows logon evidence",
        "capture_started_at": boot_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_item": _registry_run_item(),
        "launcher_events_tail": _launcher_events_tail(),
        "process_events_tail": _process_events_tail(),
        "control_log_tail": _control_log_tail(),
        "snapshots": [],
    }

    for tag in args.snapshots:
        seconds = int(tag)
        wait = seconds - 1  # crude spacing; caller can start immediately after logon
        if wait > 0:
            time.sleep(wait)
        evidence["snapshots"].append(_snapshot(tag))

    evidence["capture_ended_at"] = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    try:
        print(json.dumps(evidence, ensure_ascii=False, indent=2, default=str)[:4000])
    except UnicodeEncodeError:
        sys.stdout.buffer.write(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str)[
                :4000
            ].encode("utf-8")
        )
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
