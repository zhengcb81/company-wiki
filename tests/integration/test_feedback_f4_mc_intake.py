"""Receive real MeetingConverter publication observations through the F4 boundary."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from tools.feedback_loop.coordinator import advance
from tools.feedback_loop.local_host import LocalHost
from tools.feedback_loop.observations import read_batch


pytestmark = [pytest.mark.public_owner]


_TRANSCRIBE = """
import os
from pathlib import Path
import sys
from unittest.mock import Mock

from core import transcribe_one
from engines.base import Segment, TranscriptionResult
from exceptions import TranslationError

root = Path(sys.argv[1])
root.mkdir()
audio = root / "private-fixture-name.mp3"
audio.write_bytes(b"synthetic audio fixture")
transcription = TranscriptionResult(
    language="en", language_probability=0.99, duration=10,
    segments=[Segment(0, 3, "private-transcript-fixture"), Segment(7, 9, "Second paragraph")],
)
engine = Mock()
engine.transcribe.return_value = transcription
translator = Mock(model="fixture-model")
translator.translate_paragraphs.return_value = ["第一段", "第二段"]
if sys.argv[2] == "interrupt":
    engine.transcribe.side_effect = lambda *args, **kwargs: os._exit(17)
    transcribe_one(engine, audio, root, translator_obj=translator)
    raise AssertionError("expected hard exit")

assert transcribe_one(engine, audio, root, translator_obj=translator) is not None
outputs = {path: path.read_bytes() for path in root.glob("*.txt")}
assert len(outputs) == 3
assert transcribe_one(engine, audio, root, translator_obj=translator) is None
assert (engine.transcribe.call_count, translator.translate_paragraphs.call_count) == (1, 1)
assert all(path.read_bytes() == content for path, content in outputs.items())
translator.translate_paragraphs.side_effect = TranslationError("fixture-only-secret private-transcript-fixture")
assert transcribe_one(engine, audio, root, translator_obj=translator, force=True) is not None
assert (engine.transcribe.call_count, translator.translate_paragraphs.call_count) == (2, 2)
assert all(path.read_bytes() == content for path, content in outputs.items() if "原文" not in path.stem)
"""


def test_mc_publication_and_replay_keep_the_original_invocation(tmp_path):
    checkout = os.environ.get("FEEDBACK_MC_CODE_ROOT")
    if not checkout:
        pytest.skip("set FEEDBACK_MC_CODE_ROOT to the F2-MC-OUTPUT checkout")
    mc = Path(checkout)
    assert (mc / "core/__init__.py").is_file()
    executed, interrupted = tmp_path / "publication.jsonl", tmp_path / "interrupted.jsonl"
    environment = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE"}
    }
    for scenario, output, exit_code in (("publication", executed, 0), ("interrupt", interrupted, 17)):
        run = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", _TRANSCRIBE, str(tmp_path / scenario), scenario],
            cwd=mc, env={
                **environment, "RESEARCH_FEEDBACK_OUT": str(output),
                "RESEARCH_FEEDBACK_RUN_ID": "mc-f4", "RESEARCH_FEEDBACK_ATTEMPT_ID": "dispatch-1",
            }, capture_output=True, check=False, timeout=30,
        )
        assert run.returncode == exit_code, run.stderr

    inputs = [executed, interrupted]
    batch = read_batch(inputs)
    assert batch.diagnostics == []
    entries = batch.observations
    terminal = [row for row in entries.values() if row["check_id"] == "publication-outcome"]
    assert {row["actual"] for row in terminal} == {"published_current", "reused_existing", "published_incomplete"}
    assert len({row["step_id"] for row in terminal}) == 3
    assert len({row["evidence_ref"] for row in terminal}) == 1
    unfinished, = batch.unfinished_starts()
    assert entries[unfinished]["evidence_ref"] != terminal[0]["evidence_ref"]
    stale, = (row for row in entries.values() if row.get("issue_key") == "stale-output-success")
    assert stale["actual"] == "previous_translations_only"

    details_path = executed.with_name(executed.name + ".details.jsonl")
    details_text = details_path.read_text(encoding="utf-8")
    details = {row["details_id"]: row for row in map(json.loads, details_text.splitlines())}
    failure = details[stale["details_ref"]]
    assert failure["step_id"] == stale["step_id"]
    assert {"stage": "translation", "role": None, "error_type": "TranslationError"} in failure["errors"]
    for private in ("fixture-only-secret", "private-transcript-fixture", "private-fixture-name", str(tmp_path)):
        assert private not in details_text

    samples = sorted((mc / "docs/plans/f2-mc-output/receipts").glob("sample-*.jsonl"))
    assert len(samples) == 4
    authored = read_batch(samples)
    assert authored.diagnostics == [] and len(authored.unfinished_starts()) == 1
    replay = read_batch(inputs + inputs)
    assert replay.plan() == batch.plan()

    settings = tmp_path / "host.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {"meeting-converter": {
        "cwd": str(tmp_path),
    }}}), encoding="utf-8")
    host = LocalHost(settings)

    def receive(_owner, request):
        assert request["kind"] in {"observe", "triage", "reconcile"}
        if request["kind"] == "reconcile":
            assert request["method"] == "lookup"
        return host.handle(request)

    processed = advance(batch, receive)
    assert processed == advance(replay, receive)
    observed = {row["occurrence_id"]: row for row in processed["observations"]}
    assert observed[unfinished]["status"] == "unknown" and observed[unfinished]["step"] == "reconcile"
    for occurrence, row in entries.items():
        if row["check_id"] == "cost-receipt":
            assert observed[occurrence]["status"] == "unknown"
        if row.get("issue_key") == "stale-output-success":
            assert observed[occurrence]["status"] == "unknown" and observed[occurrence]["step"] == "triage"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM actions").fetchone() == (len(entries),)
