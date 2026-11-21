"""Exercise the real FF schedule and Windows host against the prepared pilot."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


# This wrapper runs the original public command. It holds one real return
# after CWP has published an original, giving the test a precise crash boundary.
IMPORT_BARRIER = r"""
import json, os, pathlib, subprocess, sys, time

folder = pathlib.Path(__file__).parent
marker = folder / "after-import.json"
original = folder / "cwp_entry.py"
arguments = [sys.executable, "-B", "-X", "utf8", str(original), *sys.argv[1:]]
journal = folder / ".source_catalog" / "acquisition_attempts.jsonl"
if "ensure" in sys.argv:
    with (folder / "ensure-calls.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid()}) + "\n")
if os.environ.get("SR_ACCEPTANCE_INTERRUPT") == "1" and "ensure" in sys.argv and not marker.exists():
    previous = journal.stat().st_size if journal.is_file() else 0
    result = subprocess.run(arguments, input=sys.stdin.buffer.read(), capture_output=True)
    if result.returncode == 0 and journal.is_file():
        with journal.open("rb") as stream:
            stream.seek(previous)
            lines = [json.loads(line) for line in stream if line.strip()]
        imported = next((line for line in lines if line.get("outcome") == "downloaded_new"), None)
        if imported is not None:
            marker.write_text(json.dumps({key: imported[key] for key in (
                "provider", "provider_document_id", "content_sha256", "attempt_id",
            )}))
            until = time.monotonic() + 35
            while not (folder / "release-import").exists() and time.monotonic() < until:
                time.sleep(0.1)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    sys.exit(result.returncode)
sys.exit(subprocess.run(arguments).returncode)
"""


def json_command(arguments: list[str], body: dict | None = None) -> dict:
    process = subprocess.run(arguments, input=json.dumps(body) if body is not None else None,
                             capture_output=True, encoding="utf-8", timeout=360)
    if process.returncode:
        raise RuntimeError(f"{Path(arguments[4]).name} failed ({process.returncode}): {process.stderr[-1000:]}")
    return json.loads(process.stdout)


def windows_command(*arguments: str) -> bytes:
    process = subprocess.run(["schtasks.exe", *arguments], capture_output=True, timeout=30)
    if process.returncode:
        raise RuntimeError(f"Windows task operation {arguments[0]} failed ({process.returncode})")
    return process.stdout


def wait_for(check, *, seconds: float, timeout_message: str):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(1)
    raise TimeoutError(timeout_message)


def downloads(root: Path) -> list[dict]:
    journal = root / ".source_catalog/acquisition_attempts.jsonl"
    if not journal.exists():
        return []
    with journal.open(encoding="utf-8") as stream:
        return [row for line in stream if line.strip() and (
            row := json.loads(line)
        ).get("outcome") in ("downloaded_new", "deduplicated_after_download")]


def task_exists(name: str) -> bool:
    return subprocess.run(["schtasks.exe", "/Query", "/TN", name],
                          capture_output=True, timeout=30).returncode == 0


def receipts_for_pilot(root: Path, reader: list[str], after: dict) -> dict:
    rows = downloads(root)
    expected = {row["provider"]: row["content_sha256"] for row in rows}
    seeds = json.loads((root / "pilot-inputs.json").read_text(encoding="utf-8"))["seed_sha256"]
    expected.update({Path(name).suffix: value for name, value in seeds.items()})
    by_hash = {}
    for owner_run_id in after["usage"]["reading_runs"]:
        native = json_command([*reader, "read-incremental-status", "--request-stdin"], {
            "schema_version": "cwp-incremental-read-status-request/1", "run_id": owner_run_id,
        })
        assert native["usage"]["model_requests"] == native["usage"]["model_attempts"] == 0
        assert native["usage"]["cost_state"] == "settled"
        for item in native["items"]:
            if item["state"] != "read":
                continue
            result = json_command([*reader, "read-incremental-result", "--request-stdin"], {
                "schema_version": "cwp-incremental-read-result-request/1",
                "result_ref": item["result_ref"],
            })
            by_hash[item["source_ref"]["content_sha256"]] = {
                "source_ref": item["source_ref"], "result_ref": item["result_ref"],
                "evidence_spans": len(result["evidence_spans"]),
                "parser": result.get("parser"), "source_metadata": result["source_metadata"],
            }
    return {name: by_hash.get(expected.get(key))
            for name, key in (("CN", "cninfo"), ("HK", ".pdf"), ("US", "sec"), ("US_TXT", ".txt"))}


def run(args: argparse.Namespace) -> dict:
    root = args.scratch.resolve(strict=True)
    if not (root / "pilot-inputs.json").is_file():
        raise ValueError("run prepare_real_pilot.py on an independent catalog first")
    if task_exists(args.task_name):
        raise ValueError("the acceptance task name is already occupied")
    ff = args.filing_fetch.resolve(strict=True)
    connection = root / "config/company_wiki.json"
    connect = json.loads(connection.read_text(encoding="utf-8"))
    barrier = root / "import_barrier.py"
    barrier.write_text(IMPORT_BARRIER, encoding="utf-8")
    commands = connect["connection"]["commands"]
    commands["catalog"][4] = str(barrier)
    connection.write_text(json.dumps(connect, ensure_ascii=False), encoding="utf-8")

    base = [sys.executable, "-B", "-X", "utf8"]
    jobs = root / "jobs"
    schedule_args = [
        "--config", str(connection), "--jobs-dir", str(jobs),
        "--refresh-config", str(root / "config/scheduled_refresh.json"),
    ]
    ff_cli = [*base, str(ff / "scripts/ff_scheduled_refresh.py"), *schedule_args]
    reader = [*base, str(root / "cwp_entry.py"), "cli", "--config",
              str(root / "config/source_catalog.yaml")]
    task_cli = [*base, str(ff / "scripts/ff_scheduled_windows.py")]
    task_args = ["--task-name", args.task_name, "--python", sys.executable, *schedule_args]
    job_cli = [*base, str(ff / "scripts/ff_job.py"), "--jobs-dir", str(jobs)]
    now = datetime.now(timezone.utc)
    due = now - timedelta(days=2)
    settings = {
        "enabled": True,
        "cadence": {"frequency": "weekly", "weekday": due.isoweekday(),
                    "local_time": "07:30", "time_zone": "UTC"},
        "roster": {"mode": "pinned", "roster_ref": "three-market-pilot"},
        "document_kinds": ["annual_report"],
        "transcripts_enabled": True, "backlog_enabled": True, "reading_level": "local",
    }
    configure = {"schema_version": "ff-scheduled-refresh-config/1", "settings": settings}
    initial = json_command([*ff_cli, "configure", "--request-stdin"], configure)
    assert initial["last_run"] is None and not downloads(root)
    assert datetime.fromisoformat(initial["next_due_at"].replace("Z", "+00:00")) < now
    evidence = {"due_slot": due.date().isoformat(), "enabled_at": now.isoformat()}
    logger = (root / "interrupted-tick.log").open("wb")
    first = subprocess.Popen([*ff_cli, "tick"], stdout=logger, stderr=logger,
                             env=dict(os.environ, SR_ACCEPTANCE_INTERRUPT="1"))
    try:
        marker = root / "after-import.json"

        def import_completed():
            if marker.is_file():
                return True
            if first.poll() is not None:
                raise RuntimeError("first tick ended before importing an original")
            return False

        wait_for(import_completed, seconds=300, timeout_message="no real import to interrupt")
        first.kill()
        first.wait(timeout=15)
        (root / "release-import").touch()
        interrupted = json_command([*ff_cli, "status"])["current_run"]
        assert interrupted["active_action"]["stage"] == "acquisition"
        imported = json.loads(marker.read_text(encoding="utf-8"))
        evidence["interrupted"] = interrupted
        evidence["interrupted_import"] = imported
        evidence["interrupted_downloads"] = len(downloads(root))
        old_job, = [job for job in json_command([*job_cli, "list_jobs"])["items"]
                    if job["idempotency_key"] == interrupted["active_action"]["reference"]]
        evidence["interrupted_job"] = old_job

        host = json_command([*task_cli, "install", *task_args])
        assert host["registered"] and host["task_name"] == args.task_name
        evidence["host"] = host
        windows_command("/Run", "/TN", args.task_name)

        def recovered():
            status = json_command([*ff_cli, "status"])
            previous = status.get("last_run")
            if previous and previous["run_id"] == interrupted["run_id"]:
                return status
            return None

        after = wait_for(recovered, seconds=680, timeout_message="native host did not finish the interrupted slot")
        evidence["resumed"] = after["last_run"]
        resumed_jobs = json_command([*job_cli, "list_jobs"])["items"]
        recovered_job, = [job for job in resumed_jobs
                          if job["idempotency_key"] == old_job["idempotency_key"]]
        evidence["recovered_job"] = recovered_job
        evidence["resumed_downloads"] = len(downloads(root))
        assert after["last_run"]["slot_id"] == interrupted["slot_id"]
        assert recovered_job["owner_job_id"] == old_job["owner_job_id"]
        assert recovered_job["execution_count"] == old_job["execution_count"]
        assert recovered_job["status"] == "succeeded"
        assert recovered_job["result"]["source_ref"]["content_sha256"] == imported["content_sha256"]
        assert sum(row["content_sha256"] == imported["content_sha256"] for row in downloads(root)) == 1
        evidence["verified_products"] = receipts_for_pilot(root, reader, after["last_run"])
        assert all(evidence["verified_products"].values()), "one or more pilot originals were not read"

        # Manual and Windows triggers use the same durable schedule state.
        again = json_command([*ff_cli, "tick"])
        evidence["repeated_downloads"] = len(downloads(root))
        assert again["last_run"]["run_id"] == interrupted["run_id"]
        assert evidence["resumed_downloads"] == evidence["repeated_downloads"]
        history = json_command([*ff_cli, "runs"])
        assert len(history["items"]) == 1
        evidence["history"] = history
        return evidence
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=15)
        (root / "release-import").touch()
        logger.close()
        # Retain concise proof in isolation even when a timed step failed.
        try:
            if task_exists(args.task_name):
                subprocess.run(["schtasks.exe", "/End", "/TN", args.task_name],
                               capture_output=True, timeout=30)
                json_command([*task_cli, "remove", *task_args])
                assert not task_exists(args.task_name)
                evidence["temporary_task_removed"] = True
        finally:
            (root / "runtime-evidence.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            settings["enabled"] = False
            json_command([*ff_cli, "configure", "--request-stdin"], configure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--filing-fetch", type=Path, required=True)
    parser.add_argument("--task-name", required=True)
    args = parser.parse_args()
    if not args.task_name.startswith("FilingFetch-SR-Acceptance-"):
        parser.error("acceptance uses a dedicated Windows task name")
    receipt = run(args)
    print(json.dumps({key: receipt[key] for key in (
        "due_slot", "host", "resumed", "interrupted_downloads", "resumed_downloads", "repeated_downloads",
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
