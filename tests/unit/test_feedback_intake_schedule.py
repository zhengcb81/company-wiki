from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from threading import Event
import time

import pytest

from company_wiki.file_mutex import FileMutexLockedError
from tools.feedback_loop import intake, local_host
from tools.feedback_loop.process_launch import BACKGROUND_CREATION_FLAGS


def _configuration(tmp_path):
    settings = tmp_path / "settings.json"
    hosts = tmp_path / "hosts.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {}}), encoding="utf-8")
    hosts.write_text("{}", encoding="utf-8")
    return settings, hosts


def test_parallel_owner_completions_start_one_inbox_reader(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    launches = []

    def launch(command, **kwargs):
        launches.append(command)

    monkeypatch.setattr(intake.subprocess, "Popen", launch)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: intake.wake(settings, hosts, owners=["filing-fetch", "stockwiki"]), range(38)))

    assert len(launches) == 1


def test_active_scan_defers_other_owner_and_keeps_last_formal_receipt(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    second_config = settings.with_name("other.json")
    second_config.write_bytes(settings.read_bytes())
    previous_receipt = settings.with_name("last-native-recovery.json")
    previous_receipt.write_bytes(b'{"processed":99}')
    calls = []
    starts = []
    entered, release = Event(), Event()

    def scan(config, registry, *, owner, wait_seconds, database):
        calls.append((config, registry, owner, wait_seconds))
        if owner == "company-wiki":
            entered.set()
            assert release.wait(10)
        return {"processed": 1}

    monkeypatch.setattr(intake, "_drain_once", scan)
    monkeypatch.setattr(intake, "_launch_pending", lambda *args: starts.append(args))

    with ThreadPoolExecutor(1) as pool:
        leader = pool.submit(intake.drain, settings, hosts, owner="company-wiki", wait_seconds=0)
        try:
            assert entered.wait(10)
            args = ["--config", str(second_config), "recover", "--hosts", str(hosts), "--owner", "filing-fetch",
                    "--save-result"]
            assert local_host.main(args) == 0
            for _ in range(10):
                intake.wake(second_config, hosts, owner="filing-fetch")
            assert previous_receipt.read_bytes() == b'{"processed":99}'
            assert not starts
        finally:
            release.set()
        assert leader.result(timeout=10) == {"processed": 1}

    assert starts == [(settings, hosts, tmp_path / "actions.sqlite")]
    assert intake._drain_pending(settings, hosts) == {"completed_scopes": 1}
    assert calls == [(settings, hosts, "company-wiki", 0), (second_config, hosts, ["filing-fetch"], 0)]
    assert json.loads(previous_receipt.read_bytes())["processed"] == 1


def test_failed_launch_and_interrupted_scan_leave_scope_for_cold_recovery(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    attempted = []

    def failed_launch(*args):
        raise OSError("fixture launch failure")

    monkeypatch.setattr(intake, "_launch_pending", failed_launch)
    with pytest.raises(OSError, match="fixture launch failure"):
        intake.wake(settings, hosts, owner="filing-fetch", wait_seconds=2)

    def scan(config, registry, *, owner, wait_seconds, database):
        attempted.append((config, registry, owner, wait_seconds))
        if len(attempted) == 1:
            raise RuntimeError("fixture abrupt exit")
        return {"processed": 1}

    monkeypatch.setattr(intake, "_drain_once", scan)
    with pytest.raises(RuntimeError, match="fixture abrupt exit"):
        intake._drain_pending(settings, hosts)
    assert intake._drain_pending(settings, hosts) == {"completed_scopes": 1}
    assert intake._drain_pending(settings, hosts) == {"completed_scopes": 0}
    assert attempted == [(settings, hosts, ["filing-fetch"], 2)] * 2


def test_same_scope_arriving_during_scan_is_processed_in_the_same_worker(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    launches = []
    calls = []

    def scan(config, registry, *, owner, wait_seconds, database):
        calls.append(owner)
        if len(calls) == 1:
            for _ in range(6):
                intake.wake(settings, hosts, owners=["filing-fetch", "stockwiki"])
        return {"processed": 1}

    monkeypatch.setattr(intake, "_launch_pending", lambda *args: launches.append(args))
    monkeypatch.setattr(intake, "_drain_once", scan)
    intake.wake(settings, hosts, owners=["stockwiki", "filing-fetch"])

    assert intake._drain_pending(settings, hosts) == {"completed_scopes": 2}
    assert calls == [["filing-fetch", "stockwiki"]] * 2
    assert launches == [(settings, hosts, tmp_path / "actions.sqlite")]


def test_process_kill_releases_scan_ownership_and_retains_wake(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    ready = tmp_path / "held"
    program = """
from pathlib import Path
import sys
import time
from tools.feedback_loop.intake_schedule import IntakeSchedule
with IntakeSchedule(Path(sys.argv[1])).scan() as locked:
    assert locked
    Path(sys.argv[2]).touch()
    time.sleep(30)
"""
    # The child cannot inherit pytest's added paths or a developer's editable install.
    process = subprocess.Popen(
        [sys.executable, "-B", "-E", "-S", "-c", program, str(settings), str(ready)],
        cwd=Path(__file__).resolve().parents[2],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=BACKGROUND_CREATION_FLAGS,
    )
    launches = []
    try:
        until = time.monotonic() + 15
        while not ready.exists() and process.poll() is None and time.monotonic() < until:
            time.sleep(0.05)
        assert ready.exists()
        monkeypatch.setattr(intake, "_launch_pending", lambda *args: launches.append(args))
        intake.wake(settings, hosts, owner="stockwiki")
        assert not launches
    finally:
        if process.poll() is None:
            process.kill()
        _, stderr = process.communicate(timeout=10)
        assert not stderr, stderr.decode(errors="replace")

    calls = []
    monkeypatch.setattr(intake, "_drain_once", lambda *args, **kwargs: calls.append(kwargs["owner"]))
    assert intake._drain_pending(settings, hosts) == {"completed_scopes": 1}
    assert calls == [["stockwiki"]]


@pytest.mark.parametrize("failure", ["missing-registry", "database-rebound"])
def test_invalid_pending_scope_does_not_starve_others_or_start_a_retry_loop(tmp_path, monkeypatch, failure):
    settings, hosts = _configuration(tmp_path)
    other = settings.with_name("other.json")
    other.write_bytes(settings.read_bytes())
    registry = hosts.with_name("other-hosts.json")
    registry.write_bytes(hosts.read_bytes())
    attempts = []
    monkeypatch.setattr(intake, "_launch_pending", lambda *args: attempts.append(args))
    intake.wake(other, registry, owner="filing-fetch")
    intake.wake(settings, hosts, owner="stockwiki")
    if failure == "missing-registry":
        registry.unlink()
    else:
        other.write_text(json.dumps({"state": "unrelated.sqlite", "owners": {}}), encoding="utf-8")

    assert intake._drain_pending(other, registry, database=tmp_path / "actions.sqlite") == {
        "completed_scopes": 1, "deferred_scopes": 1,
    }
    assert (tmp_path / "actions.sqlite").exists()
    assert not (tmp_path / "unrelated.sqlite").exists()
    assert attempts == [(other, registry, tmp_path / "actions.sqlite")]


def test_wake_contention_stays_in_the_existing_optional_notification_boundary(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)

    def busy(*args, **kwargs):
        raise FileMutexLockedError("busy")

    monkeypatch.setattr(intake.IntakeSchedule, "request", busy)
    with pytest.raises(OSError) as failed:
        intake.wake(settings, hosts, owner="stockwiki")
    assert isinstance(failed.value.__cause__, FileMutexLockedError)


def test_defer_path_hint_failure_cannot_overwrite_a_previous_formal_result(tmp_path, monkeypatch):
    settings, hosts = _configuration(tmp_path)
    receipt = tmp_path / "last-native-recovery.json"
    receipt.write_bytes(b'{"processed":99}')

    def busy(*args, **kwargs):
        raise FileMutexLockedError("fixture busy signal")

    monkeypatch.setattr(intake.IntakeSchedule, "request", busy)
    with intake.IntakeSchedule(settings).scan() as owns:
        assert owns
        assert local_host.main(["--config", str(settings), "recover", "--hosts", str(hosts), "--save-result"]) == 0

    assert receipt.read_bytes() == b'{"processed":99}'
