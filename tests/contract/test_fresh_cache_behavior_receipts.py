"""W12 synthetic receipts from the existing finite engine and public byte replay.

This intentionally observes whole-source generation reuse. It does not create
a cache, replace handlers, or claim real provider/company (M3) acceptance.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
import time

from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.official_source_flow import prepare_official_narrative_request
from integration import test_official_source_flow as official
from support.narrative_model_request_fixture import response_draft


REPO = Path(__file__).resolve().parents[2]
KEY_ENV = "W12_SYNTHETIC_MODEL_KEY"
KEY = "synthetic-w12-loopback-only"
# Owned interpreter-start instrumentation applies to the actual parent and its
# spawned workers. The version scenarios consistently pin producer/consumer
# declarations; they are synthetic upgrade identities, not released versions.
BOOTSTRAP = r'''
import atexit, importlib, json, os, pathlib, socket, sys, time
import company_wiki.automation.narrative_batch
import company_wiki.automation.narrative_worker_factory
import company_wiki.automation.narrative_transport
import company_wiki.source_catalog.narrative_evidence as evidence
pins = json.loads(os.environ["W12_SYNTHETIC_PINS"])
if "prompt" in pins:
    import company_wiki.automation.narrative_model as prompt_module
    prompt_module._INSTRUCTION += "\nSynthetic W12 prompt revision: prioritize current business updates."
if "parser" in pins:
    evidence.transcript_parser_contract(pins["parser"])
    evidence.TRANSCRIPT_PARSER_VERSION = pins["parser"]
    evidence.parse_transcript_text.__kwdefaults__["parser_version"] = pins["parser"]
for module_name, module in tuple(sys.modules.items()):
    if module_name.startswith("company_wiki.") and module is not None:
        for field, key in (("NARRATIVE_SELECTOR_VERSION", "selector"),
                           ("NARRATIVE_PROMPT_VERSION", "prompt")):
            if key in pins and hasattr(module, field):
                setattr(module, field, pins[key])
trace = pathlib.Path(os.environ["W12_TRACE_DIR"]) / (str(os.getpid()) + ".jsonl")
phase = os.environ["W12_PHASE"]
events, started = [], {}
def record(kind, **fields):
    events.append(dict(kind=kind, phase=phase, **fields))
def profile(frame, event, arg):
    if event not in ("call", "return"):
        return
    name = frame.f_code.co_name
    if name not in {"__call__", "generate", "parse_transcript_text",
                    "parse_pdf_bytes", "normalize_document",
                    "replay_narrative_evidence", "transcribe",
                    "fetch_official_indexes", "acquire"}:
        return
    module = frame.f_globals.get("__name__", "")
    if not module.startswith("company_wiki."):
        return
    label = None
    if name == "__call__" and module.endswith(("narrative_select", "narrative_summarize", "narrative_verify")):
        label = module.rsplit("_", 1)[1]
    elif name == "generate" and module.endswith("narrative_http_model"):
        label = "model"
    elif name in ("parse_transcript_text", "parse_pdf_bytes", "normalize_document"):
        label = "parse"
    elif name == "replay_narrative_evidence":
        label = "replay"
    elif name == "transcribe":
        label = "ocr"
    elif name in ("fetch_official_indexes", "acquire"):
        label = "source_provider"
    if label is None:
        return
    token = id(frame)
    if event == "call":
        started[token] = time.monotonic()
        record(label, function=module + "." + name)
    else:
        began = started.pop(token, None)
        if began is not None:
            record(label + "_duration", seconds=time.monotonic() - began)
def audit(event, args):
    if event == "socket.connect":
        address = args[1]
        local = isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1")
        record("network_connect", local=local)
        if not local:
            raise RuntimeError("W12 external network forbidden")
sys.addaudithook(audit)
sys.setprofile(profile)
def save():
    sys.setprofile(None)
    trace.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in events), encoding="utf-8")
atexit.register(save)
'''


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _public_identity(proof):
    """Exact artifact identity/bytes/version, excluding receipt read_at."""
    return {key: proof[key] for key in ("reference", "bundle_sha256", "versions")}


def _same_public(left, right):
    return {key: _public_identity(value) for key, value in left.items()} == {
        key: _public_identity(value) for key, value in right.items()}


def _file_facts(directory):
    return {
        str(path.relative_to(directory)): (_sha(path.read_bytes()), path.stat().st_mtime_ns)
        for path in directory.rglob("*") if path.is_file()
    }


def _tree_bytes(directory):
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


class _SyntheticPorts:
    """Fixture acquisition stub plus real loopback HTTP model transport."""
    def __init__(self):
        self.source_calls = 0
        self.posts = []
        self.errors = []
        self.mode = "valid"

    def original(self, value):
        self.source_calls += 1
        return value

    def __enter__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                try:
                    assert self.path == "/v1/chat/completions"
                    assert self.headers["Authorization"] == f"Bearer {KEY}"
                    body = self.rfile.read(int(self.headers["Content-Length"]))
                    assert KEY.encode() not in body
                    wire = json.loads(body)
                    data = json.loads(wire["messages"][1]["content"])
                    owner.posts.append((wire, data))
                    reply = {"model": wire["model"], "choices": []}
                    if owner.mode != "unknown":
                        reply["usage"] = {"prompt_tokens": 73, "completion_tokens": 19}
                    if owner.mode == "valid":
                        reply["choices"] = [{"message": {"content": json.dumps(response_draft(data))},
                                             "finish_reason": "stop"}]
                    content = json.dumps(reply).encode()
                    self.send_response(200)
                except Exception as exc:
                    owner.errors.append(type(exc).__name__)
                    content = b'{"error":"invalid synthetic request"}'
                    self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=lambda: self.server.serve_forever(poll_interval=0.01))
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()


class _Engine:
    def __init__(self, root, config, ports):
        self.root, self.config, self.ports = root, config, ports
        self.boot = root / "instrumentation"
        self.boot.mkdir()
        (self.boot / "sitecustomize.py").write_text(BOOTSTRAP, encoding="utf-8")
        self.receipts = []

    def env(self, phase, pins, trace):
        # Parent environment remains untouched, including TEMP/TMP/credentials.
        return {
            **os.environ, KEY_ENV: KEY, "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHON_DOTENV_DISABLED": "1", "W12_PHASE": phase,
            "W12_SYNTHETIC_PINS": json.dumps(pins), "W12_TRACE_DIR": str(trace),
            "PYTHONPATH": os.pathsep.join([str(self.boot), str(REPO / "src")]),
        }

    def call(self, module, argv, *, phase, pins, trace, request=None):
        command = [sys.executable, "-X", "utf8", "-B", "-m", module, *map(str, argv)]
        process = subprocess.run(
            command, cwd=self.root, env=self.env(phase, pins, trace),
            input=None if request is None else json.dumps(request).encode(),
            capture_output=True, timeout=60,
        )
        assert KEY.encode() not in process.stdout + process.stderr
        return process

    def public(self, imported, pin, *, phase, pins, trace):
        process = self.call(
            "company_wiki.source_catalog.narrative_transport_cli",
            ["--config", self.config, "--operation", "reference"],
            phase=phase, pins=pins, trace=trace,
            request={"schema_version": "narrative-reference-request/1",
                     "source_ref": imported["source_ref"]},
        )
        assert process.returncode == 0, process.stderr
        current_reference = json.loads(process.stdout)
        reference = {
            "schema_version": "narrative-ref/1", "artifact_version_id": pin["artifact_version_id"],
            "artifact_sha256": pin["content_sha256"], "byte_size": pin["byte_size"],
            "source_ref": imported["source_ref"],
        }
        process = self.call(
            "company_wiki.source_catalog.narrative_transport_cli",
            ["--config", self.config, "--operation", "read"],
            phase=phase, pins=pins, trace=trace,
            request={"schema_version": "narrative-read-request/1",
                     "narrative_ref": reference, "as_of_date": "2026-10-09",
                     "expected_source": {
                         "canonical_entity_id": None, "market": "US", "security_id": "ACME",
                         "document_kind": imported["fixture_document_kind"],
                         "fiscal_year": None, "fiscal_period": None}},
        )
        assert process.returncode == 0, process.stderr
        receipt = json.loads(process.stderr)
        bundle = json.loads(process.stdout)
        assert receipt["replay_status"] == "verified" and receipt["locator_count"] > 0
        assert len(process.stdout) == reference["byte_size"]
        assert _sha(process.stdout) == reference["artifact_sha256"]
        assert receipt["narrative_ref"] == reference
        assert bundle["source_ref"] == imported["source_ref"]
        return ({"reference": reference, "bundle_sha256": _sha(process.stdout),
                 "versions": bundle["versions"], "replay_receipt": receipt},
                current_reference)

    def run(self, name, imported, *, pins=None, model=None, refresh=False, expected_posts=0,
            failed=False):
        pins = pins or {}
        trace = self.root / ("trace-" + name)
        trace.mkdir()
        post_start, provider_start = len(self.ports.posts), self.ports.source_calls
        before = _tree_bytes(self.root)
        template = {
            "schema_version": "narrative-batch-request/1", "run_id": name, "profile": "P2",
            "max_seconds": 40, "max_tokens": 100000, "max_cost_usd": "1",
            "refresh": refresh,
            "model": {"model_id": "stub-model", "endpoint": self.ports.endpoint,
                      "api_key_env": KEY_ENV, "max_output_tokens": 400, "timeout_seconds": 5,
                      "allow_local_http": True, **(model or {})},
            "pricing": {"version": "fixture-price/1",
                        "input_micro_usd_per_million_tokens": 1000000,
                        "output_micro_usd_per_million_tokens": 2000000},
        }
        request = prepare_official_narrative_request(imported, batch_template=template).to_dict()
        path = self.root / (name + ".json")
        path.write_text(json.dumps(request), encoding="utf-8")
        start = time.monotonic()
        process = self.call(
            "company_wiki.automation.narrative_batch_cli",
            ["--project-root", self.root, "--catalog-config", self.config,
             "--automation-db", self.root / "AUTO.sqlite", "--work-dir", self.root / ("work-" + name),
             "--request", path],
            phase="batch", pins=pins, trace=trace,
        )
        wall = time.monotonic() - start
        result = json.loads(process.stdout)
        receipt = {"run_id": name, "fixture_kind": "synthetic", "pins": pins,
                   "request": request, "batch": result, "wall_seconds": wall}
        self.receipts.append(receipt)
        assert (process.returncode, result["status"]) == ((2, "failed") if failed else (0, "completed")), (
            name, result, process.stderr.decode())
        public_start = time.monotonic()
        pins_by_document = {row["document_id"]: row["artifact_ref"] for row in result["documents"]}
        proofs = {} if failed else {
            row["source_ref"]["document_id"]: self.public(
                row, pins_by_document[row["source_ref"]["document_id"]],
                phase="public_read", pins=pins, trace=trace)
            for row in imported
        }
        public = {key: value[0] for key, value in proofs.items()}
        current_public_refs = {key: value[1] for key, value in proofs.items()}
        public_wall = time.monotonic() - public_start
        records = [json.loads(line) for file in trace.glob("*.jsonl")
                   for line in file.read_text(encoding="utf-8").splitlines()]
        receipt["trace"] = records
        batch_calls = Counter(row["kind"] for row in records if row["phase"] == "batch"
                              and not row["kind"].endswith("_duration"))
        public_calls = Counter(row["kind"] for row in records if row["phase"] == "public_read"
                               and not row["kind"].endswith("_duration"))
        assert len(self.ports.posts) - post_start == expected_posts
        assert batch_calls["model"] == expected_posts
        assert self.ports.source_calls == provider_start
        assert batch_calls["source_provider"] == batch_calls["ocr"] == 0
        assert public_calls["source_provider"] == public_calls["ocr"] == public_calls["model"] == 0
        assert not any(row["kind"] == "network_connect" and not row["local"] for row in records)
        runs = NarrativeRunStore(self.root / "AUTO.sqlite")
        run = runs.get_run(name)
        assert run is not None
        reservations = [asdict(row) for row in runs.reservations_for_run(name)]
        store = AutomationStore(self.root / "AUTO.sqlite")
        jobs = store.list_jobs(job_ids=run.job_ids)
        assert len(jobs) == 3 * expected_posts
        assert batch_calls["select"] == batch_calls["summarize"] == expected_posts
        assert batch_calls["verify"] == (0 if failed else expected_posts)
        if not expected_posts:
            assert not reservations and not run.job_ids
            assert result["budget"] == {"tokens": 0, "estimated_micro_usd": 0,
                                       "unknown_reservations": 0, "unsettled_reservations": 0}
        elif not failed:
            assert len(reservations) == expected_posts
            assert result["budget"]["tokens"] == 92 * expected_posts
            assert result["budget"]["estimated_micro_usd"] == 111 * expected_posts
        receipt.update({
            "run_id": name, "fixture_kind": "synthetic", "pins": pins, "batch": result,
            "wall_seconds": wall, "public_read_wall_seconds": public_wall,
            "batch_calls": {key: batch_calls[key] for key in
                            ("select", "summarize", "verify", "model", "parse", "replay",
                             "ocr", "source_provider", "network_connect")},
            "public_read_calls": {key: public_calls[key] for key in
                                  ("parse", "replay", "ocr", "model", "source_provider", "network_connect")},
            "duration_seconds": {
                phase: {kind: sum(row["seconds"] for row in records
                                   if row["phase"] == phase and row["kind"] == kind)
                        for kind in sorted({row["kind"] for row in records
                                            if row["kind"].endswith("_duration")})}
                for phase in ("batch", "public_read")},
            "model_http_posts": len(self.ports.posts) - post_start,
            "source_provider_calls": batch_calls["source_provider"] + public_calls["source_provider"],
            "external_connections": sum(row["kind"] == "network_connect" and not row["local"] for row in records),
            "measurement_semantics": "function-entry counts; non-exclusive durations can overlap nested calls",
            "model_wire": [{"model": wire["model"], "temperature": wire.get("temperature"),
                            "max_tokens": wire.get("max_tokens"),
                            "system_instruction_sha256": _sha(wire["messages"][0]["content"].encode()),
                            "model_data_sha256": _sha(wire["messages"][1]["content"].encode())}
                           for wire, data in self.ports.posts[post_start:]],
            "reservations": reservations, "snapshot": {
                "input_hash": run.input_hash, "job_ids": list(run.job_ids),
                "binding": json.loads(run.binding_json),
                "jobs": [{"type": job.job_type, "status": job.status.value,
                          "error": job.last_error_code, "attempts": len(store.list_attempts(job.job_id))}
                         for job in jobs]},
            "public": public, "current_public_refs": current_public_refs, "owned_tree_before_bytes": before,
            "owned_tree_after_bytes": _tree_bytes(self.root),
        })
        return receipt


def test_existing_engine_cache_behavior_receipts(tmp_path):
    """Real AUTO/worker/outbox/public transport; all supplier output synthetic."""
    env_before = dict(os.environ)
    keep = tmp_path / "keep.bin"
    keep.write_bytes(b"pre-existing fixture parent")
    parent_before = _file_facts(tmp_path)
    root = tmp_path / "w12-owned"
    root.mkdir()
    report = {"schema_version": "fresh-cache-behavior-receipts/1",
              "classification": "synthetic engineering observation; not real M3",
              "source_baseline": "2350077ac31655d358e67390c6fbda129d80d7dc",
              "test_sha256": _sha(Path(__file__).read_bytes()),
              "production_source_sha256": {
                  str(path.relative_to(REPO)): _sha(path.read_bytes())
                  for path in (
                      REPO / "src/company_wiki/automation/narrative_batch.py",
                      REPO / "src/company_wiki/automation/narrative_generation.py",
                      REPO / "src/company_wiki/automation/narrative_formats.py",
                      REPO / "src/company_wiki/automation/narrative_worker_factory.py",
                      REPO / "src/company_wiki/automation/narrative_http_model.py",
                      REPO / "src/company_wiki/automation/narrative_run_store.py",
                      REPO / "src/company_wiki/automation/narrative_transport.py",
                      REPO / "src/company_wiki/source_catalog/narrative_evidence.py",
                  )}, "runs": []}
    primary_failure = None
    try:
        with _SyntheticPorts() as ports:
            (root / "companies").mkdir()
            (root / "config").mkdir()
            config = root / "config/catalog.json"
            config.write_text(json.dumps({
                "schema_version": "1.0", "catalog_dir": "catalog",
                "roots": [{"root_id": "company_raw", "path": "companies", "kind": "company_raw"}],
            }), encoding="utf-8")

            def imported(data, mime, kind):
                result = official._public_official_import(
                    root, config, ports.original(data), mime=mime, kind=kind, language="en")
                result["fixture_document_kind"] = kind
                return result

            call = imported(
                b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity.\n",
                "text/plain", "investor_call_transcript")
            html = imported(
                b"<html><p>We expanded our distribution network and launched a new product for customers.</p></html>",
                "text/html", "investor_relations")
            originals = _file_facts(root / "companies")
            report["originals_before"] = originals
            engine = _Engine(root, config, ports)
            report["runs"] = engine.receipts
            sources = [call, html]
            baseline = engine.run("baseline", sources, expected_posts=2)
            origin_reservations = baseline["reservations"]
            repeat = engine.run("same-spec-new-run", sources)
            assert _same_public(repeat["public"], baseline["public"])
            assert repeat["current_public_refs"] == baseline["current_public_refs"]
            assert [asdict(row) for row in NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run("baseline")] == origin_reservations

            changed = imported(
                b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity with a new production line.\n",
                "text/plain", "investor_call_transcript")
            changed_result = engine.run("new-source-bytes", [changed, html], expected_posts=1)
            html_id = html["source_ref"]["document_id"]
            call_id = call["source_ref"]["document_id"]
            assert _public_identity(changed_result["public"][html_id]) == _public_identity(baseline["public"][html_id])
            assert changed["source_ref"]["content_sha256"] != call["source_ref"]["content_sha256"]
            assert all(_file_facts(root / "companies")[key] == value for key, value in originals.items())

            legacy = engine.run("parser-version", sources, pins={"parser": "0.1.1"}, expected_posts=1)
            assert _public_identity(legacy["public"][html_id]) == _public_identity(baseline["public"][html_id])
            assert legacy["public"][call_id]["versions"]["parser"] == "0.1.1"
            assert baseline["public"][call_id]["versions"]["parser"] == "0.2.0"
            assert legacy["public"][call_id]["reference"] != baseline["public"][call_id]["reference"]
            for name, pins, model in (
                ("selector-version", {"selector": "0.6.1"}, None),
                ("prompt-version", {"prompt": "1.7.1"}, None),
                ("model-identity", {}, {"model_id": "stub-model-v2"}),
                ("model-settings", {}, {"temperature": 0.9, "max_output_tokens": 500}),
            ):
                variant = engine.run(name, sources, pins=pins, model=model, expected_posts=2)
                assert all(variant["public"][key]["reference"] != baseline["public"][key]["reference"]
                           for key in baseline["public"])
                if pins:
                    field = next(iter(pins))
                    if field == "prompt":
                        assert {row["system_instruction_sha256"] for row in variant["model_wire"]}.isdisjoint(
                            row["system_instruction_sha256"] for row in baseline["model_wire"])
                    assert all(row["versions"][field] == pins[field] for row in variant["public"].values())
                if model:
                    assert all(row["model"] == model.get("model_id", "stub-model") for row in variant["model_wire"])
                    if "temperature" in model:
                        assert all(row["temperature"] == 0.9 and row["max_tokens"] == 500
                                   for row in variant["model_wire"])
            restored = engine.run("original-spec-recovered", sources)
            assert _same_public(restored["public"], baseline["public"])

            ports.mode = "known_failure"
            known = engine.run("known-failure", [call], refresh=True, expected_posts=1, failed=True)
            assert known["batch"]["budget"]["tokens"] == 92
            assert known["batch"]["budget"]["unknown_reservations"] == 0
            assert known["reservations"][0]["usage_status"] == "known"
            ports.mode = "unknown"
            unknown = engine.run("unknown-failure", [html], refresh=True, expected_posts=1, failed=True)
            assert unknown["batch"]["budget"]["tokens"] > 0
            assert unknown["batch"]["budget"]["unknown_reservations"] == 1
            assert unknown["reservations"][0]["usage_status"] == "unknown"
            ports.mode = "valid"
            after_failures = engine.run("after-failures-reuse", sources)
            assert _same_public(after_failures["public"], baseline["public"])
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            assert [asdict(row) for row in runs.reservations_for_run("known-failure")] == known["reservations"]
            assert [asdict(row) for row in runs.reservations_for_run("unknown-failure")] == unknown["reservations"]
            assert not ports.errors
            report["originals_after"] = _file_facts(root / "companies")
            assert all(report["originals_after"][key] == value for key, value in originals.items())
            report["fixture_acquisition_calls"] = ports.source_calls
            report["total_synthetic_model_http_posts"] = len(ports.posts)
            report["status"] = "passed"
    except BaseException as exc:
        primary_failure = exc
        report["status"] = "failed"
        report["failure_type"] = type(exc).__name__
        raise
    finally:
        try:
            assert root.resolve().parent == tmp_path.resolve() and root.name == "w12-owned"
            shutil.rmtree(root)
            report["cleanup"] = {
                "owned_temp_removed": not root.exists(), "parent_files_restored": _file_facts(tmp_path) == parent_before,
                "environment_unchanged": dict(os.environ) == env_before,
                "temp_environment_unchanged": all(os.environ.get(key) == env_before.get(key) for key in ("TEMP", "TMP")),
            }
            destination = os.environ.get("W12_RECEIPT_FILE")
            if destination:
                output = Path(destination).resolve()
                owned_plan = (REPO / "docs/plans/fresh-cache-receipts-2026-10-09").resolve()
                assert owned_plan in output.parents, "receipt output must stay in owned W12 plan"
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            assert all(report["cleanup"].values())
        except BaseException as cleanup_error:
            if primary_failure is None:
                raise
            primary_failure.add_note("W12 cleanup/receipt error: " + type(cleanup_error).__name__)
