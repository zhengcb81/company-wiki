"""Exercise the deployed owner commands and lost-reply recovery with real processes."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from tools.feedback_loop.coordinator import advance
from tools.feedback_loop.local_host import LocalHost
from tools.feedback_loop.observations import digest, read_batch


ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
OWNER = "meeting-converter"
_MC = """
import os
from pathlib import Path
import sys
from unittest.mock import Mock
from core import transcribe_one
from engines.base import Segment, TranscriptionResult
from exceptions import TranslationError

root = Path(sys.argv[1])
audio = root / "meeting.mp3"
audio.write_bytes(b"sample")

def count(port):
    with (root / "ports.txt").open("a", encoding="ascii") as handle:
        print(port, file=handle)

def transcribe(*args, **kwargs):
    count("transcribe")
    if sys.argv[2] == "stop":
        os._exit(17)
    return TranscriptionResult(
        language="en", language_probability=1.0, duration=3.0, segments=[Segment(0, 3, "fixture transcript")],
    )

def translate(*args, **kwargs):
    count("translate")
    raise TranslationError("injected timeout after send")

transcribe_one(Mock(transcribe=transcribe), audio, root, Mock(model="fixture", translate_paragraphs=translate), force=True)
"""
_COUNT_OWNER = """
from pathlib import Path
import subprocess
import sys
with Path(sys.argv[1]).open("a", encoding="ascii") as handle:
    print(sys.argv[-1], file=handle)
raise SystemExit(subprocess.run(sys.argv[2:], check=False).returncode)
"""
_LOSE_RESULT = """
import json
import os
from pathlib import Path
import subprocess
import sys
from tools.feedback_loop.local_host import LocalHost
run = subprocess.run
def kill_after_owner_commit(*args, **kwargs):
    result = run(*args, **kwargs)
    assert result.returncode == 0 and isinstance(json.loads(result.stdout).get("result"), dict)
    os._exit(19)
subprocess.run = kill_after_owner_commit
LocalHost(Path(sys.argv[1]))._owner_command(sys.argv[2])
"""


def test_mc_auto_repair_and_report_recover_original_action_ids(tmp_path, monkeypatch):
    checkout = os.environ.get("FEEDBACK_MC_CODE_ROOT")
    if not checkout:
        pytest.skip("set FEEDBACK_MC_CODE_ROOT to the MC owner-runtime checkout")
    owner_root = Path(checkout).resolve()
    owner_script = owner_root / "feedback_owner.py"
    assert owner_script.is_file()
    environment = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE"}
    }
    original, owner_db = tmp_path / "original.jsonl", tmp_path / "owner.sqlite"
    old = tmp_path / "meeting_翻译.txt"
    old.write_text("previous translation", encoding="utf-8")
    for scenario, exit_code in (("stale", 0), ("stop", 17)):
        completed = subprocess.run(
            [*PYTHON, "-c", _MC, str(tmp_path), scenario], cwd=owner_root, capture_output=True, timeout=25,
            env={**environment, "RESEARCH_FEEDBACK_OUT": str(original), "RESEARCH_FEEDBACK_RUN_ID": "mc-control",
                 "RESEARCH_FEEDBACK_ATTEMPT_ID": "same-caller-attempt"},
        )
        assert completed.returncode == exit_code, completed.stderr
    outputs = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.glob("meeting_*.txt")}
    assert old in outputs
    ports = tmp_path / "ports.txt"
    assert ports.read_text().splitlines() == ["transcribe", "translate", "transcribe"]

    author_input = read_batch([original])
    interrupted, = author_input.unfinished_starts()
    issue, = [key for key, row in author_input.observations.items() if row.get("issue_key") == "stale-output-success"]
    cost, = [key for key, row in author_input.observations.items() if row["check_id"] == "cost-receipt"]
    received = tmp_path / "received.jsonl"
    received.write_text("".join(json.dumps(author_input.observations[key]) + "\n" for key in (issue, interrupted, cost)),
                        encoding="utf-8")
    batch = read_batch([received])
    command = [*PYTHON, str(owner_script), "--db", str(owner_db), "--sidecar", str(original)]
    port_calls = tmp_path / "owner-calls.txt"
    actions = {
        kind: {"argv": [*PYTHON, "-c", _COUNT_OWNER, str(port_calls), *command, kind],
               "lookup_argv": [*command, "get-action"]}
        for kind in ("triage", "repair", "replay", "report")
    }
    actions["reconcile"] = [*command, "reconcile"]
    config = tmp_path / "settings.json"
    config.write_text(json.dumps({"state": "host.sqlite", "owners": {
        OWNER: {"cwd": str(owner_root), "timeout_seconds": 20, "actions": actions}
    }}), encoding="utf-8")
    host = LocalHost(config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)

    def receive(_owner, request):
        return host.handle(request)

    def queued(kind):
        with closing(sqlite3.connect(host.db)) as conn:
            key, = [key for key, raw in conn.execute("SELECT action_id, request FROM actions WHERE state = 'queued'")
                    if json.loads(raw)["kind"] == kind]
        return key

    def recover_lost_reply(key):
        outcome = subprocess.run([*PYTHON, "-c", _LOSE_RESULT, str(config), key], cwd=ROOT,
                                 capture_output=True, timeout=30)
        assert outcome.returncode == 19, (outcome.stdout, outcome.stderr)
        assert host._get(key)["state"] == "running"
        assert host._native_path(key).read_bytes() == b""
        receipt = json.loads(subprocess.check_output([*command, "get-action", key], timeout=15))["receipt"]
        cli = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(config), "recover"]
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda _: subprocess.check_output(cli, cwd=ROOT, timeout=25), range(2)))
        settled = host.handle({**receipt["request"], "method": "lookup"})
        assert settled["state"] == "done" and settled["action_id"] == key
        assert settled["result"] == receipt["result"]
        assert settled["native"] == {"receipt_source": "owner_action"}
        return receipt

    advance(batch, receive)
    triage = queued("triage")
    assert triage == digest(["triage", OWNER, issue])
    host.work(triage)
    advance(batch, receive)
    repair = queued("repair")
    assert json.loads(subprocess.check_output([*command, "get-publication", repair], timeout=15)) == {}
    restored = recover_lost_reply(repair)["result"]
    publication = json.loads(subprocess.check_output([*command, "get-publication", repair], timeout=15))["publication"]
    assert publication["occurrence_id"] == issue and set(publication["current"]) == {"original"}
    assert publication["retained"] == ["translated"]
    assert publication["current"]["original"]["sha256"] == sha256(outputs[tmp_path / "meeting_原文.txt"][0]).hexdigest()

    advance(batch, receive)
    host.work(queued("replay"))
    advance(batch, receive)
    report = recover_lost_reply(queued("report"))["request"]
    assert report["payload"]["original_occurrence_id"] == issue
    assert report["payload"]["fixed_version"] == restored["fixed_version"]
    finished = advance(batch, receive)
    assert finished == advance(read_batch([received, received]), receive)
    states = {row["occurrence_id"]: row for row in finished["observations"]}
    assert states[issue]["status"] == "verified"
    assert states[interrupted]["status"] == "unknown" and states[interrupted]["job_status"] == "unconfirmed"
    assert states[cost]["status"] == "unknown" and states[cost]["job_status"] == "succeeded"
    assert states[cost]["cost_state"] == "unknown"
    assert Counter(port_calls.read_text().splitlines()) == {"triage": 1, "repair": 1, "replay": 1, "report": 1}
    assert ports.read_text().splitlines() == ["transcribe", "translate", "transcribe"]
    assert all((path.read_bytes(), path.stat().st_mtime_ns) == saved for path, saved in outputs.items())
