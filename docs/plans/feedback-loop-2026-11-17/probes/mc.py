"""Exercise MeetingConverter's ordinary CLI against local, non-paying engine doubles."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time


PY = [sys.executable, "-B", "-X", "utf8"]
CONTROLLER = Path(__file__).resolve().parents[4]
MARKER = "fixture-provider-fault-23"


def process_audio(checkout, root, scenario):
    # Only business sources are imported. No deployed configuration is opened.
    sys.path.insert(0, str(checkout))
    import transcribe
    from engines.base import Segment, TranscriptionResult
    from engines.fallback import FallbackEngine

    class Engine:
        def transcribe(self, *args, **kwargs):
            signal = root / "engine-calls"
            with signal.open("a", encoding="utf8") as stream:
                stream.write("called\n")
            if scenario == "kill":
                time.sleep(60)
            return TranscriptionResult("en", 0.99, 1.0, [Segment(0, 1, "Fixture sentence.")])

    class FailedEngine:
        def transcribe(self, *args, **kwargs):
            try:
                raise TimeoutError(110, MARKER)
            except TimeoutError as error:
                raise RuntimeError("fixture upstream failed") from error

    transcribe.load_config = lambda: {"isolated_fixture": True}
    transcribe.extract_company_from_filename = lambda _name: ""
    engine = Engine()
    if scenario == "fallback":
        engine = FallbackEngine(FailedEngine(), Engine)
    if scenario == "provider":
        engine = FailedEngine()
    if scenario != "engine-init":
        transcribe.create_engine = lambda *args, **kwargs: engine

    source = root / "audio.wav"
    output = root / "out"
    if scenario != "no-input":
        source.write_bytes(b"stub audio for local engine")
    if scenario == "output-dir":
        output.write_bytes(b"not a directory")
    if scenario == "reuse":
        output.mkdir()
        (output / "audio_原文.txt").write_text("saved original", encoding="utf8")
    if scenario == "writer":
        output.mkdir()
        (output / "audio_原文.txt").mkdir()
    sys.argv = ["transcribe.py", str(source), "-o", str(output)]
    if scenario == "invalid-cli":
        sys.argv.append("--unknown-fixture-option")
    if scenario != "translator-init":
        sys.argv.append("--no-translate")
    if scenario == "engine-init":
        sys.argv.extend(["--engine", "mimo"])
    if scenario == "writer":
        sys.argv.append("--force")
    transcribe.main()


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def probe(checkout, root, scenario):
    sidecar = root / "observations.jsonl"
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE",
        "SYSTEMDRIVE", "COMSPEC", "APPDATA", "LOCALAPPDATA"}}
    env.update(RESEARCH_FEEDBACK_OUT=str(sidecar), RESEARCH_FEEDBACK_RUN_ID="mc-probe",
               RESEARCH_FEEDBACK_ATTEMPT_ID=scenario, PYTHONUTF8="1")
    command = [*PY, str(Path(__file__).resolve()), "--child", str(checkout), str(root), scenario]
    with subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
        try:
            if scenario == "kill":
                until = time.monotonic() + 12
                while not (root / "engine-calls").exists():
                    if child.poll() is not None or time.monotonic() > until:
                        raise RuntimeError("Isolated worker did not enter the fixture engine")
                    time.sleep(.02)
                child.kill()
            stdout, stderr = child.communicate(timeout=20)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)

    plan = subprocess.check_output([*PY, "-m", "tools.feedback_loop", "plan", str(sidecar)],
                                   cwd=CONTROLLER, env=env, timeout=12)
    rows = json.loads(plan)["observations"]
    details_path = sidecar.with_name(sidecar.name + ".details.jsonl")
    details = details_path.read_text(encoding="utf8") if details_path.exists() else ""
    result = {
        "exit": child.returncode, "observations": len(rows),
        "deviations": [row["check_id"] for row in rows if row["disposition"] == "deviation"],
        "terminal": [row["actual"] for row in rows if row["check_id"] == "publication-outcome"],
        "errors": [err for line in details.splitlines() for err in json.loads(line).get("errors", [])],
        "root_cause_type_in_details": "TimeoutError" in details,
        "root_cause_type_in_stdio": b"TimeoutError" in stdout + stderr,
        "model_calls": 0,
    }
    if scenario == "kill":
        start, = rows
        occurrence = start.pop("occurrence_id")
        body = {"occurrence_id": occurrence, "observation": start}
        key = digest(["reconcile", "meeting-converter", occurrence])
        req = {"schema_version": "feedback-action/1", "kind": "reconcile", "owner": "meeting-converter",
               "action_id": key, "method": "lookup", "payload": body,
               "request_digest": digest(["meeting-converter", "reconcile", key, body])}
        reply = subprocess.check_output([*PY, str(checkout / "feedback_owner.py"), "--db", str(root / "action.db"),
                                         "--sidecar", str(sidecar), "reconcile"], env=env, cwd=root,
                                        input=json.dumps(req).encode(), timeout=12)
        result["reconcile"] = json.loads(reply)
        result["engine_calls_after_reconcile"] = len((root / "engine-calls").read_text().splitlines())
    return result


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        process_audio(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    else:
        checkout = Path(sys.argv[1]).resolve(strict=True)
        with TemporaryDirectory(prefix="mc-f4-audit-") as directory:
            results = {}
            for name in ("no-input", "invalid-cli", "output-dir", "engine-init", "translator-init",
                         "fallback", "provider", "writer", "reuse", "kill"):
                root = Path(directory) / name
                root.mkdir()
                results[name] = probe(checkout, root, name)
            print(json.dumps(results, indent=2))
