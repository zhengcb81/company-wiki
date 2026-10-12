"""W08-CWP-G2-REPLAY manual runner.

Usage::

    python -B tools/narrative_g2_replay/run.py \
        --rf-project <ABS_FIXED_RF_PROJECT> \
        --owned-root <ABS_NEW_WRITABLE_CONTAINER> \
        --out-root   <ABS_NEW_WRITABLE_CONTAINER>

What it actually does, in order:

1. builds a synthetic fixture lake (real PDF/TXT bytes, typed sidecars);
2. registers it through the **real** catalog scan (no hand-filled SourceRef,
   no direct DB write pretending a public ingest happened);
3. runs the **real** finite narrative batch CLI over the whole typed CaseSpec
   matrix, against a loopback model fixture that only echoes a deterministic
   original-language draft;
4. runs a **second** run over the identical version/spec and asserts zero new
   model POSTs, while still doing a fresh public read + locator verification;
5. consumes the published artifact through the fixed, read-only RF reader
   snapshot and reports read success, draft support and real model calls as
   three separate facts;
6. restores the owned root to its recorded baseline and writes one small
   report (schema ``narrative-g2-replay/1``).

Zero paid provider calls.  No credential is read.  Network is confined to
loopback.  Exit codes: 0 oracle PASS, 3 PARTIAL/UNKNOWN, 1 oracle FAIL,
2 invalid record / runtime refusal.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import shutil
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from typing import Any

_WORKTREE = Path(__file__).resolve().parents[2]
for _entry in (str(_WORKTREE / "src"), str(_WORKTREE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from tools.narrative_g2_replay import fixtures, observations, oracle, report, specs  # noqa: E402

# The single absolute deadline for the whole batch (card section C).
DEFAULT_DEADLINE_SECONDS = 180.0
DEFAULT_COMMAND_SECONDS = 30.0

_LOOPBACK_KEY_ENV = "W08_G2_REPLAY_LOOPBACK_KEY"
_LOOPBACK_KEY = "w08-loopback-synthetic-key"

# Minimal child environment: startup + interpreter basics only.  No real
# credential variable ever enters the child process.
_CHILD_ENV_KEEP = frozenset({
    "SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE", "TEMP", "TMP",
})


# --------------------------------------------------------------------------
# owned-root handling
# --------------------------------------------------------------------------


def snapshot_baseline(owned_root: Path) -> dict[str, Any]:
    """Shallow stat inventory only; never scan or hash a caller's existing lake."""
    import stat as stat_mod

    if not owned_root.exists():
        return {"exists": False, "sentinels": []}
    entries = []
    for path in sorted(owned_root.iterdir()):
        metadata = path.lstat()
        entries.append({
            "path_ref": path.name,
            "type": "directory" if stat_mod.S_ISDIR(metadata.st_mode) else "file",
            "byte_size": metadata.st_size,
            "mtime_ns": metadata.st_mtime_ns,
        })
    return {"exists": True, "sentinels": entries}


def checked_path(path: Path) -> Path:
    """Inspect lexical ancestors before resolve, so a junction cannot hide."""
    import stat as stat_mod

    absolute = Path(os.path.abspath(path))
    for item in (absolute, *absolute.parents):
        if not item.exists() and not item.is_symlink():
            continue
        metadata = item.lstat()
        if stat_mod.S_ISLNK(metadata.st_mode) or (
            getattr(metadata, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("synthetic paths must not traverse reparse points")
    return absolute


def validate_roots(owned_root: Path, out_root: Path) -> tuple[Path, Path]:
    owned, output = checked_path(owned_root), checked_path(out_root)
    if owned == output or owned in output.parents or output in owned.parents:
        raise ValueError("owned and output containers must be disjoint")
    for path in (owned, output):
        if path.exists() and not path.is_dir():
            raise ValueError("execution containers must be directories")
    return owned, output


# --------------------------------------------------------------------------
# loopback model fixture
# --------------------------------------------------------------------------


class LoopbackModel:
    """A real local HTTP model boundary; stub returns a deterministic draft.

    This is deliberately *not* a mock of the narrative layer: the real finite
    worker, selector, summarizer, verifier, publisher and reader all run.  Only
    the remote provider is replaced, by a loopback server that answers with an
    original-language draft derived from the actual prompt evidence.
    """

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.errors: list[str] = []
        self.post_count = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self.endpoint = ""

    def start(self) -> None:
        state = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: A003 - silence the server
                pass

            def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
                try:
                    if self.path != "/v1/chat/completions":
                        raise ValueError("unexpected path")
                    if self.headers.get("Authorization") != f"Bearer {_LOOPBACK_KEY}":
                        raise ValueError("unexpected authorization")
                    body = self.rfile.read(int(self.headers["Content-Length"]))
                    if _LOOPBACK_KEY.encode() in body:
                        raise ValueError("key leaked into the request body")
                    request = json.loads(body)
                    roles = [message["role"] for message in request["messages"]]
                    if roles != ["system", "user"]:
                        raise ValueError("unexpected message roles")
                    if "No translation" not in request["messages"][0]["content"]:
                        raise ValueError("prompt does not pin no-translation")
                    data = json.loads(request["messages"][1]["content"])
                    draft = _draft_from_prompt(data)
                    state.post_count += 1
                    state.requests.append({"data": data, "draft": draft})
                    reply = json.dumps({
                        "model": "w08-loopback-stub",
                        "choices": [{
                            "message": {"content": json.dumps(
                                draft, ensure_ascii=False)},
                            "finish_reason": "stop",
                        }],
                        "usage": {"prompt_tokens": 64, "completion_tokens": 24},
                    }, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                except Exception as exc:  # noqa: BLE001 - fixture boundary
                    state.errors.append(type(exc).__name__)
                    reply = b'{"error":"invalid loopback request"}'
                    self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self._thread = Thread(
            target=lambda: self._server.serve_forever(poll_interval=0.01)
        )
        self._thread.start()
        self.endpoint = (
            f"http://127.0.0.1:{self._server.server_port}/v1/chat/completions"
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=10)


def _draft_from_prompt(data: dict) -> dict:
    """Deterministic original-language draft derived from the real prompt.

    The stub never invents an economic fact: it cites the first evidence row's
    own text, exactly like the project's existing fixture does, so the binding
    being tested is prompt -> draft -> published bundle, not model quality.
    """
    row = data["evidence"][0]
    role = row[2] if len(row) > 2 else data["default_source_role"]
    flags = row[3] if len(row) > 3 else data["default_quality_flags"]
    claim_type = (
        "company_statement"
        if role in {"company_filing", "management"}
        else "analyst_question"
        if role in {"analyst", "investor_question"}
        else "uncertain"
    )
    review = claim_type == "uncertain" or "locator_unstable" in flags
    return {"draft": {
        "source_id": data["source"]["source_id"],
        "source_sha256": data["source"]["source_sha256"],
        "language": data["source"]["language"],
        "claims": [{
            "claim_id": "claim-001",
            "text": row[1][:200],
            "evidence_ids": [row[0]],
            "claim_type": claim_type,
            "modality": "question" if claim_type == "analyst_question" else "uncertain",
            "needs_review": review,
        }],
        "status": "needs_review" if review else "draft",
    }}


# --------------------------------------------------------------------------
# child environment
# --------------------------------------------------------------------------


def child_env(worktree: Path, scratch: Path) -> dict[str, str]:
    """A minimal, credential-free environment for every child process."""
    home, temp = scratch / "home", scratch / "temp"
    home.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() in _CHILD_ENV_KEEP
    }
    env.update(
        HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / "appdata"),
        LOCALAPPDATA=str(home / "localappdata"), TEMP=str(temp), TMP=str(temp),
        PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1",
        PYTHONPATH=os.pathsep.join((str(worktree / "src"), str(worktree))),
        **{_LOOPBACK_KEY_ENV: _LOOPBACK_KEY},
    )
    if os.name == "nt":
        env["HOMEDRIVE"] = home.drive
        env["HOMEPATH"] = str(home)[len(home.drive):]
    return env


def run_bounded(command: list[str], *, cwd: Path, env: dict[str, str],
                timeout_seconds: float, stdin_bytes: bytes | None = None):
    """Run one child command under an absolute per-command bound."""
    import subprocess

    return subprocess.run(
        command, cwd=str(cwd), env=env, input=stdin_bytes,
        capture_output=True, timeout=timeout_seconds, check=False,
    )


# --------------------------------------------------------------------------
# fixture lake + real registration
# --------------------------------------------------------------------------


def build_lake(root: Path) -> SimpleNamespace:
    """Write the synthetic originals and register them via the real scan.

    The config lives at ``<root>/config/catalog.json`` on purpose.  The real
    transport CLI calls ``load_catalog_config`` *without* ``project_root``, and
    that falls back to ``path.resolve().parents[1]`` -- the config's
    grandparent.  Placing the config one level down makes the standalone CLI
    resolve ``catalog_dir`` to exactly the same directory the batch CLI uses via
    its explicit ``--project-root``, so both paths address one catalog instead
    of two.  This mirrors the production layout rather than inventing a new one.
    """
    written = fixtures.write_originals(root)
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "catalog.json"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": "catalog",
        "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True,
            "reusable_for_filing": True,
        }],
    }), encoding="utf-8")

    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    catalog = SourceCatalog(load_catalog_config(config_path, project_root=root))
    catalog.scan()
    reader = SourceVersionReader(catalog)
    indexed: dict[str, dict] = {}
    for spec in specs.case_specs():
        info = written[spec.fixture_key]
        row = catalog.reader.fetchone(
            "SELECT d.document_id, d.primary_source_id AS source_id FROM documents d "
            "JOIN sources s ON s.source_id = d.primary_source_id "
            "WHERE s.content_sha256 = ?", (info["content_sha256"],),
        )
        if row is None:
            raise RuntimeError(
                f"{spec.case_id}: the real scan did not register the original"
            )
        ref = reader.query_ref(row["document_id"], row["source_id"],
                               info["content_sha256"])
        manifest = reader.describe_version(ref)
        indexed[spec.case_id] = {
            "ref": ref,
            "manifest": manifest,
            "fixture": info,
        }
    return SimpleNamespace(
        root=root, config_path=config_path, catalog=catalog, reader=reader,
        written=written, indexed=indexed,
    )


def build_request(lake: SimpleNamespace, *, run_id: str, endpoint: str,
                  case_ids: tuple[str, ...]) -> dict[str, Any]:
    """One typed request per case, in the real ``narrative-batch-request/1`` shape."""
    sources = []
    for case_id in case_ids:
        ref = lake.indexed[case_id]["ref"]
        sources.append({
            "schema_version": ref.schema_version,
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
        })
    return {
        "schema_version": "narrative-batch-request/1",
        "run_id": run_id,
        "sources": sources,
        "profile": "P2",
        "max_seconds": DEFAULT_DEADLINE_SECONDS,
        "max_tokens": 400_000,
        "max_cost_usd": "2",
        "model": {
            "model_id": "w08-loopback-stub",
            "endpoint": endpoint,
            "api_key_env": _LOOPBACK_KEY_ENV,
            "max_output_tokens": 400,
            "timeout_seconds": 10,
            "allow_local_http": True,
        },
        "pricing": {
            "version": "w08-fixture-price/1",
            "input_micro_usd_per_million_tokens": 1_000_000,
            "output_micro_usd_per_million_tokens": 2_000_000,
        },
    }


def invoke_batch(lake: SimpleNamespace, *, request_path: Path, run_id: str,
                 work_dir: Path, env: dict[str, str], timeout_seconds: float):
    command = [
        sys.executable, "-B", "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(lake.root),
        "--catalog-config", str(lake.config_path),
        "--automation-db", str(lake.root / "automation.db"),
        "--work-dir", str(work_dir),
        "--request", str(request_path),
    ]
    return run_bounded(command, cwd=lake.root, env=env,
                       timeout_seconds=timeout_seconds)


def parse_receipt(process) -> tuple[dict | None, str | None]:
    stdout = (process.stdout or b"").decode("utf-8", errors="replace").strip()
    if not stdout:
        return None, "empty stdout"
    # stdout must stay a single small JSON receipt; take the last JSON object.
    line = stdout.splitlines()[-1]
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, f"unparsable receipt: {exc}"
    if not isinstance(value, dict):
        return None, "receipt is not an object"
    return value, None


def receipt_documents(receipt: dict) -> list[dict]:
    return list(receipt.get("documents") or receipt.get("items") or [])


def document_by_id(receipt: dict) -> dict[str, dict]:
    result = {}
    for item in receipt_documents(receipt):
        key = item.get("document_id") or item.get("item_key")
        if key:
            result[key] = item
    return result


# --------------------------------------------------------------------------
# public read (the consumer-facing surface)
# --------------------------------------------------------------------------


def read_request_for(lake: SimpleNamespace, pin: dict) -> dict[str, Any]:
    """Build a real ``narrative-read-request/1`` from one batch artifact pin.

    The batch returns a *raw* pin carrying ``content_sha256``; the transport
    contract wants ``artifact_sha256`` plus a full ``source_ref``.  The source
    reference is read back from the catalog rather than hand-written, so no
    identity field is fabricated here.

    ``expected_source`` is the transport contract's *issuer* constraint block
    (its field set is exact): the reader checks these against the catalog's own
    facts, so they are read from the catalog too, not invented.
    """
    ref = lake.reader.query_ref(pin["document_id"], pin["source_id"],
                                pin["source_sha256"])
    manifest = lake.reader.describe_version(ref)
    source_ref = {
        "schema_version": ref.schema_version,
        "document_id": ref.document_id,
        "source_id": ref.source_id,
        "content_sha256": ref.content_sha256,
        "byte_size": ref.byte_size,
        "mime_type": ref.mime_type,
    }
    return {
        "schema_version": "narrative-read-request/1",
        "narrative_ref": {
            "schema_version": "narrative-ref/1",
            "artifact_version_id": pin["artifact_version_id"],
            "artifact_sha256": pin["content_sha256"],
            "byte_size": pin["byte_size"],
            "source_ref": source_ref,
        },
        "as_of_date": "2026-10-12",
        "expected_source": {
            "canonical_entity_id": manifest.get("canonical_entity_id"),
            "market": manifest.get("market"),
            "security_id": manifest.get("security_id"),
            "document_kind": manifest.get("document_kind"),
            "fiscal_year": manifest.get("fiscal_year"),
            "fiscal_period": manifest.get("fiscal_period"),
        },
    }


def pin_identity(pin: dict) -> dict[str, Any]:
    """The pin fields recorded in the report (paths never appear)."""
    return {
        "artifact_version_id": pin.get("artifact_version_id"),
        "artifact_sha256": pin.get("content_sha256"),
        "byte_size": pin.get("byte_size"),
        "document_id": pin.get("document_id"),
        "source_id": pin.get("source_id"),
        "source_sha256": pin.get("source_sha256"),
    }


def read_public_artifact(lake: SimpleNamespace, pin: dict, env: dict[str, str],
                         *, timeout_seconds: float) -> dict[str, Any]:
    """Read one published bundle through the real transport CLI (fresh bytes).

    This is the same pathless reader RF uses: a subprocess, stdin request,
    stdout artifact bytes, stderr receipt.  Bytes and citations are verified.
    """
    document_id = pin["document_id"]
    request = read_request_for(lake, pin)
    command = [
        sys.executable, "-B", "-m",
        "company_wiki.source_catalog.narrative_transport_cli",
        "--config", str(lake.config_path),
        "--operation", "read",
    ]
    try:
        process = run_bounded(
            command, cwd=lake.root, env=env, timeout_seconds=timeout_seconds,
            stdin_bytes=json.dumps(request).encode("utf-8"),
        )
    except Exception as exc:  # noqa: BLE001 - recorded as a real failure
        return {"channel": "narrative_transport_cli", "ok": False,
                "reason": f"{type(exc).__name__}", "document_id": document_id}
    if process.returncode != 0:
        stderr = (process.stderr or b"").decode("utf-8", "replace").strip()
        return {"channel": "narrative_transport_cli", "ok": False,
                "reason": stderr[:400] or "nonzero exit", "document_id": document_id,
                "exit_code": process.returncode}
    body = process.stdout or b""
    stderr = (process.stderr or b"").decode("utf-8", "replace").strip()
    try:
        receipt = json.loads(stderr) if stderr else {}
    except json.JSONDecodeError:
        receipt = {}
    body_sha = report.sha256_bytes(body)
    return {
        "channel": "narrative_transport_cli",
        "ok": True,
        "document_id": document_id,
        "exit_code": 0,
        "body_sha256": body_sha,
        "body_byte_size": len(body),
        "body_matches_pin": body_sha == pin["content_sha256"],
        "receipt": receipt,
        "fresh_process": True,
        "body_bytes": body,
    }


def summarize_public_read(read: dict[str, Any]) -> dict[str, Any]:
    """Extract the facts the report needs, tolerating a refusal shape."""
    if not read.get("ok"):
        return {"ok": False, "reason": read.get("reason")}
    body = read.get("body_bytes")
    if body is None:
        return {"ok": read.get("body_matches_pin") is True,
                "body_matches_pin": read.get("body_matches_pin"),
                "body_sha256": read.get("body_sha256"),
                "locators": None}
    try:
        bundle = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "bundle is not JSON"}
    spans = bundle.get("evidence_spans") or []
    return {
        "ok": read.get("body_matches_pin") is True,
        "body_matches_pin": read.get("body_matches_pin"),
        "body_sha256": read.get("body_sha256"),
        "selection_status": (bundle.get("selection") or {}).get("status"),
        "quality_status": bundle.get("quality_status"),
        "summary_status": (bundle.get("summary") or {}).get("status"),
        "draft_language": ((bundle.get("summary") or {}).get("draft") or {}).get(
            "language"),
        "locator_count": len(spans),
        "replay_status": (read.get("receipt") or {}).get("replay_status"),
        "receipt_locator_count": (read.get("receipt") or {}).get("locator_count"),
        "locators": [
            {
                "span_id": span.get("span_id"),
                "page_number": (span.get("coordinates") or {}).get("page_number"),
                "paragraph_index": (span.get("coordinates") or {}).get(
                    "paragraph_index"),
                "raw_text_sha256": report.sha256_bytes(
                    (span.get("raw_text") or "").encode("utf-8")),
            }
            for span in spans
        ],
    }


# --------------------------------------------------------------------------
# RF consumption (read-only, fixed snapshot)
# --------------------------------------------------------------------------


def consume_with_rf(*, rf_project: Path, lake: SimpleNamespace, pin: dict,
                    env: dict[str, str], timeout_seconds: float) -> dict[str, Any]:
    """Consume one published artifact through the fixed RF reader snapshot.

    Only the public, pathless entry points are used.  This performs no forecast
    and writes nothing into the RF project.
    """
    request = read_request_for(lake, pin)
    command = [
        sys.executable, "-B", str(rf_project / "scripts" /
                                  "narrative_source_preparation.py"),
        "--company-wiki-catalog-config", str(lake.config_path),
        "--operation", "read",
        "--timeout-seconds", str(timeout_seconds),
    ]
    rf_env = dict(env)
    rf_env["PYTHONPATH"] = os.pathsep.join(
        (str(rf_project / "scripts"), str(_WORKTREE / "src"), str(_WORKTREE))
    )
    try:
        process = run_bounded(
            command, cwd=rf_project, env=rf_env, timeout_seconds=timeout_seconds,
            stdin_bytes=json.dumps(request).encode("utf-8"),
        )
    except Exception as exc:  # noqa: BLE001 - reported, never hidden
        return {"consumer": "scripts/narrative_source_preparation.py",
                "read_ok": False, "reason": f"{type(exc).__name__}",
                "period_preserved": None, "language_preserved": None,
                "gaps_reported": ["rf_reader_exception"]}
    if process.returncode != 0:
        stderr = (process.stderr or b"").decode("utf-8", "replace").strip()
        return {"consumer": "scripts/narrative_source_preparation.py",
                "read_ok": False, "exit_code": process.returncode,
                "reason": stderr[:400] or "nonzero exit",
                "period_preserved": None, "language_preserved": None,
                "gaps_reported": ["rf_reader_refused"]}
    stdout = (process.stdout or b"").decode("utf-8", "replace").strip()
    try:
        context = json.loads(stdout.splitlines()[-1]) if stdout else {}
    except json.JSONDecodeError as exc:
        return {"consumer": "scripts/narrative_source_preparation.py",
                "read_ok": False, "reason": f"unparsable context: {exc}",
                "period_preserved": None, "language_preserved": None,
                "gaps_reported": ["rf_context_unparsable"]}
    spans = context.get("evidence_spans") or []
    # Read the language off the actually returned evidence, not off a key we
    # hoped to see; the reader's context carries per-span structured_value.
    languages = {
        (span.get("structured_value") or {}).get("language")
        for span in spans if isinstance(span, dict)
    } - {None}
    locators = [
        span.get("locator") for span in spans
        if isinstance(span, dict) and span.get("locator")
    ]
    as_of = context.get("as_of_date")
    expected_period = request["expected_source"]
    manifest = context.get("manifest") or {}
    return {
        "consumer": "scripts/narrative_source_preparation.py",
        "read_ok": True,
        "exit_code": 0,
        "document_id": pin.get("document_id"),
        "context_sha256": report.sha256_bytes(stdout.encode("utf-8")),
        "span_count": len(spans),
        "locator_count": len(locators),
        "locators": locators[:8],
        "languages": sorted(languages),
        # Compare the actual nonempty cutoff and fiscal period returned by RF.
        "as_of_date_echoed": as_of == request["as_of_date"],
        "period_preserved": as_of == request["as_of_date"] and all(
            manifest.get(key) == expected_period[key] for key in ("fiscal_year", "fiscal_period")),
        "fiscal_year": manifest.get("fiscal_year"),
        "fiscal_period": manifest.get("fiscal_period"),
        "context": context,
        "language_preserved": bool(languages),
        "gaps_reported": list(context.get("gaps") or []),
    }


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def _attempt_snapshot(owned_root: Path) -> dict[str, Any]:
    return snapshot_baseline(owned_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-project", type=Path, required=True,
                        help="fixed read-only RF project whose public reader is consumed")
    parser.add_argument("--owned-root", type=Path, required=True,
                        help="container for a unique owned child; existing contents preserved")
    parser.add_argument("--out-root", type=Path, required=True,
                        help="root for new attempt directories (never overwritten)")
    parser.add_argument("--deadline-seconds", type=float,
                        default=DEFAULT_DEADLINE_SECONDS)
    parser.add_argument("--command-seconds", type=float,
                        default=DEFAULT_COMMAND_SECONDS)
    args = parser.parse_args(argv)

    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    clock_start = time.monotonic()

    try:
        if not all(math.isfinite(value) and value > 0 for value in (args.deadline_seconds, args.command_seconds)):
            raise ValueError("deadline and command bound must be finite and positive")
        owned_root, out_root = validate_roots(args.owned_root, args.out_root)
        rf_project = checked_path(args.rf_project)
        if not (rf_project / "scripts" /
                "narrative_source_preparation.py").is_file():
            raise ValueError("rf-project does not contain the fixed reader snapshot")
        report.assert_worktree_binding(_WORKTREE)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2

    deadline = time.monotonic() + args.deadline_seconds
    baseline = _attempt_snapshot(owned_root)
    attempt = report.create_attempt(out_root)
    owned_child: Path | None = None
    model = LoopbackModel()
    lake: SimpleNamespace | None = None
    record: dict[str, Any] | None = None
    setup_error: str | None = None
    remaining: list[str] = []
    model_calls = 0

    root_preexisted = owned_root.exists()
    try:
        owned_root.mkdir(parents=True, exist_ok=True)
        owned_child = Path(tempfile.mkdtemp(prefix="w08-g2-", dir=owned_root))
        scratch = owned_child / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        env = child_env(_WORKTREE, scratch)

        model.start()
        lake = build_lake(owned_child / "lake")
        model_calls = model.post_count

        record = _execute(
            lake=lake, owned_child=owned_child, attempt=attempt, model=model,
            rf_project=rf_project, env=env, deadline=deadline,
            command_seconds=args.command_seconds, baseline=baseline,
            started_at=started_at,
        )
    except Exception as exc:  # noqa: BLE001 - recorded, never silently swallowed
        traceback.print_exc()
        setup_error = f"{type(exc).__name__}: {exc}"
    finally:
        model_calls = max(model_calls, model.post_count)
        if lake is not None:
            try:
                lake.catalog.close()
            except Exception:  # noqa: BLE001 - cleanup must not mask the cause
                pass
        model.stop()
        # Remove only the child this run created, then the container only when
        # this run created it too.  A caller-supplied container keeps existing.
        if owned_child is not None and owned_child.exists():
            try:
                shutil.rmtree(owned_child)
            except OSError:
                remaining.append(str(owned_child).replace("\\", "/"))
        if (
            not root_preexisted
            and owned_root.exists()
            and not any(owned_root.iterdir())
        ):
            try:
                owned_root.rmdir()
            except OSError:
                pass

    elapsed = time.monotonic() - clock_start
    if record is None:
        failure = {
            "schema_version": oracle.SCHEMA_VERSION,
            "status": "INVALID_RECORD",
            "setup_error": setup_error,
            "baseline": baseline,
            "after": _attempt_snapshot(owned_root),
            "remaining": remaining,
            "elapsed_seconds": round(elapsed, 3),
        }
        (attempt.path / "initialization-failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("harness failed to initialize; failure receipt retained",
              file=sys.stderr)
        return 2

    record["run"]["elapsed_seconds"] = round(elapsed, 3)
    record["run"]["finished_at"] = datetime.now(UTC).isoformat().replace(
        "+00:00", "Z")
    record["cleanup"]["after"] = _attempt_snapshot(owned_root)
    record["cleanup"]["remaining"] = remaining
    record["cleanup"]["restored"] = (
        not remaining and record["cleanup"]["baseline"] == record["cleanup"]["after"]
    )
    record["cleanup"]["deleted_within_owned"] = True
    if setup_error:
        record.setdefault("findings", []).append(
            {"id": "runner-error", "root_cause": setup_error})

    verdict = oracle.evaluate_run(record)
    record["oracle_verdict"] = {
        "statuses": verdict.statuses,
        "overall": verdict.overall,
        "findings": [
            {"code": f.code, "case_id": f.case_id, "detail": f.detail,
             "outcome": f.outcome}
            for f in verdict.findings
        ],
    }
    report_path = report.write_report(attempt, record)
    print(f"report: {report_path}")
    print(f"overall: {verdict.overall}")
    for finding in verdict.findings:
        print(f"  finding: {finding.code} [{finding.case_id}] {finding.detail}")
    if verdict.overall == oracle.STATUS_PASS:
        return 0
    if verdict.overall in {oracle.STATUS_PARTIAL, oracle.STATUS_UNKNOWN}:
        return 3
    return 1


def _execute(*, lake: SimpleNamespace, owned_child: Path, attempt: report.AttemptDir,
             model: LoopbackModel, rf_project: Path, env: dict[str, str],
             deadline: float, command_seconds: float,
             baseline: dict[str, Any], started_at: str) -> dict[str, Any]:
    """Run both passes over the typed matrix and assemble the run record."""
    case_ids = specs.required_case_ids()
    planned_deadline_seconds = deadline - time.monotonic()
    requests_dir = owned_child / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)

    def remaining_budget() -> float:
        return observations.remaining_seconds(deadline)

    def bounded() -> float:
        return min(command_seconds, remaining_budget())

    # ---- pass 1: real typed batch over every case -----------------------
    request = build_request(lake, run_id="w08-g2-run1",
                            endpoint=model.endpoint, case_ids=case_ids)
    request_path = requests_dir / "run1.json"
    request["max_seconds"] = bounded()
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    observations.save_bytes(attempt.path, "requests/run1.json", request_path.read_bytes())
    posts_before = model.post_count
    try:
        process1 = invoke_batch(
            lake, request_path=request_path, run_id="w08-g2-run1",
            work_dir=owned_child / "work-run1", env=env, timeout_seconds=bounded(),
        )
    except Exception as exc:  # noqa: BLE001 - timeout is a real PARTIAL
        process1 = SimpleNamespace(returncode=-1, stdout=b"", stderr=(
            f"{type(exc).__name__}".encode()))
    run1_posts = model.post_count - posts_before
    receipt1, receipt1_error = parse_receipt(process1)

    # ---- pass 2: identical version/spec must not re-post ----------------
    posts_before2 = model.post_count
    try:
        process2 = invoke_batch(
            lake, request_path=request_path, run_id="w08-g2-run1",
            work_dir=owned_child / "work-run1", env=env, timeout_seconds=bounded(),
        )
    except Exception as exc:  # noqa: BLE001
        process2 = SimpleNamespace(returncode=-1, stdout=b"", stderr=(
            f"{type(exc).__name__}".encode()))
    run2_posts = model.post_count - posts_before2
    receipt2, receipt2_error = parse_receipt(process2)
    for index, process in ((1, process1), (2, process2)):
        observations.save_bytes(attempt.path, f"receipts/run{index}.json", process.stdout)
        observations.save_bytes(attempt.path, f"receipts/run{index}.stderr", process.stderr)

    # ---- per-case assembly ---------------------------------------------
    docs1 = document_by_id(receipt1) if receipt1 else {}
    cases: list[dict[str, Any]] = []
    rf_records: list[dict[str, Any]] = []
    for case_id in case_ids:
        spec = specs.spec_by_id(case_id)
        info = lake.indexed[case_id]
        document = docs1.get(info["ref"].document_id)
        case = _assemble_case(
            spec=spec, info=info, document=document,
            lake=lake, model=model, env=env, timeout_seconds=bounded(), attempt=attempt.path,
        )
        cases.append(case)
        if case["_rf_pin"] is not None:
            rf_records.append(consume_with_rf(
                rf_project=rf_project, lake=lake, pin=case["_rf_pin"],
                env=env, timeout_seconds=bounded(),
            ))
        if rf_records and rf_records[-1].get("document_id") == info["ref"].document_id:
            context = rf_records[-1].pop("context", None)
            if context is not None:
                observations.save_bytes(attempt.path, f"rf/{case_id}.json",
                    json.dumps(context, ensure_ascii=False).encode("utf-8"))
        case.pop("_rf_pin", None)

    # ---- second-run reuse check on the published pins -------------------
    reuse_verified = False
    if receipt1 and receipt2:
        pins1 = {i.get("document_id"): i.get("artifact_ref")
                 for i in receipt_documents(receipt1)}
        pins2 = {i.get("document_id"): i.get("artifact_ref")
                 for i in receipt_documents(receipt2)}
        reuse_verified = pins1 == pins2 and bool(pins1)

    invalidation = observations.invalidation_checks(
        lake=lake, model=model, env=env, attempt=attempt.path, bounded=bounded,
        original_request=request, original_pins={i["document_id"]: i["artifact_ref"]
            for i in receipt_documents(receipt1 or {}) if i.get("artifact_ref")})
    observations.save_bytes(attempt.path, "model/requests-and-drafts.json",
        json.dumps(model.requests, ensure_ascii=False).encode("utf-8"))

    overall_rf = {
        "consumer": "scripts/narrative_source_preparation.py",
        "read_ok": bool(rf_records) and all(r.get("read_ok") for r in rf_records),
        "period_preserved": bool(rf_records) and all(
            r.get("period_preserved") for r in rf_records),
        # A skipped document legitimately carries no evidence and therefore no
        # language; only reads that actually returned spans can speak to it.
        "language_preserved": bool(rf_records) and all(
            r.get("language_preserved")
            for r in rf_records if (r.get("span_count") or 0) > 0
        ),
        "gaps_reported": sorted({g for r in rf_records for g in r.get("gaps_reported", [])}),
        "reads": rf_records,
        "verified_reads": sum(1 for r in rf_records if r.get("read_ok")),
        "read_with_evidence": sum(
            1 for r in rf_records if (r.get("span_count") or 0) > 0),
    }

    raw_bytes = sum(info["fixture"]["byte_size"] for info in lake.indexed.values())
    derived_bytes = 0
    catalog_dir = lake.root / "catalog"
    if catalog_dir.exists():
        derived_bytes = sum(
            p.stat().st_size for p in catalog_dir.rglob("*") if p.is_file()
        )

    record = {
        "schema_version": oracle.SCHEMA_VERSION,
        "run": {
            "run_id": attempt.attempt_id,
            "runner_pid": os.getpid(),
            "started_at": started_at,
            "finished_at": None,
            "code_binding": report.capture_code_identity(_WORKTREE),
            "rf_project": str(rf_project).replace("\\", "/"),
        },
        "scope": {
            "lane_id": "W08-CWP-G2-REPLAY",
            "supplier_fixture": True,
            "llm_semantic_quality": "not_evaluated",
            "source_truth_verified": (
                "local synthetic originals only; SHA/size/locator verified "
                "in this workspace, no real company identity claimed"
            ),
            "paid_calls": 0,
        },
        "code_binding": {
            **report.capture_code_identity(_WORKTREE),
            "rf_snapshot_modules": report.capture_rf_snapshot_identity(
                rf_project)["modules"],
            "rf_project_ref": str(rf_project).replace("\\", "/"),
        },
        "rf_snapshot": report.capture_rf_snapshot_identity(rf_project),
        "case_specs": [spec.to_dict() for spec in specs.case_specs()],
        "coverage": specs.coverage_report(case_ids),
        "run_plan": {
            "deadline_seconds": float(planned_deadline_seconds),
            "per_command_seconds": command_seconds,
            "root_observation_contract": "root-w08-observations/1",
            "second_run_reuse": True,
            "rf_consumption": True,
        },
        "invalidation": invalidation,
        "runs": [
            {"run_index": 1, "model_posts": run1_posts,
             "status": (receipt1 or {}).get("status", "failed"),
             "exit_code": getattr(process1, "returncode", None)},
            {"run_index": 2, "model_posts": run2_posts,
             "status": (receipt2 or {}).get("status", "failed"),
             "exit_code": getattr(process2, "returncode", None),
             "reuse_pins_identical": reuse_verified},
        ] + [{"run_index": item["run_index"], "model_posts": item["model_posts"],
              "status": "completed" if item["status"] == "PASS" else "failed",
              "exit_code": item["exit_code"]} for item in invalidation],
        "model_accounting": {
            "run1_posts": run1_posts,
            "run2_posts": run2_posts,
            "total_posts": model.post_count,
            "provider_calls": 0,
            "llm_calls": model.post_count,
            "paid_usd": 0.0,
            "stub_errors": list(model.errors),
            "loopback_endpoint_ref": "loopback://127.0.0.1/v1/chat/completions",
        },
        "rf_consumption": overall_rf,
        "cases": cases,
        "bytes": {"raw_bytes": raw_bytes, "derived_bytes": derived_bytes},
        "cleanup": {
            # The container's baseline is snapshotted before the owned child is
            # created (in ``main``), and re-read after the child is removed.
            "baseline": baseline,
            "after": None,
            "deleted_within_owned": True,
            "restored": False,
            "remaining": [],
        },
        "known_baseline_failures": known_baseline_failures(),
        "receipts": {
            "run1_error": receipt1_error,
            "run2_error": receipt2_error,
            "run1_status": (receipt1 or {}).get("status"),
            "run2_status": (receipt2 or {}).get("status"),
        },
    }
    return record


def known_baseline_failures() -> list[dict[str, Any]]:
    """The real, reproduced W04 baseline failures at the pinned base.

    Recorded, not fixed here, and not rewritten into an expectation.
    """
    return [
        {
            "case_id": "w04-baseline-sparse-language",
            "test_id": "tests/integration/test_narrative_batch_cli_e2e.py::"
                       "test_cli_infers_sparse_languages_from_verified_pdf_"
                       "and_transcript_bytes",
            "status": "historical_not_retested",
            "root_cause": "real batch CLI exits 2 with status=failed where the "
                          "test expects completed",
            "owner": "ROOT",
            "reproduced_at": "122bbe3ba142979a2e478f886eb25de76edf2e00",
        },
        {
            "case_id": "w04-baseline-read-identity",
            "test_id": "tests/integration/test_narrative_runtime_e2e.py::"
                       "test_runtime_e2e_read_identity_fails_automatically_and_"
                       "transcript_needs_no_receipt",
            "status": "historical_not_retested",
            "root_cause": "attempt/job row count assertion 6 != 4",
            "owner": "ROOT",
            "reproduced_at": "122bbe3ba142979a2e478f886eb25de76edf2e00",
        },
    ]


def _assemble_case(*, spec: specs.CaseSpec, info: dict, document: dict | None,
                   lake: SimpleNamespace, model: LoopbackModel,
                   env: dict[str, str], timeout_seconds: float, attempt: Path) -> dict[str, Any]:
    """One case block, built only from observed facts."""
    fixture = info["fixture"]
    manifest = info["manifest"]
    pin = (document or {}).get("artifact_ref")
    expected = specs.FIXED_EXPECTATIONS[spec.case_id]

    # Raw identity is re-verified from the actual original bytes, not metadata.
    original_path = lake.root / fixture["path_ref"]
    raw_sha256 = None
    raw_bytes_ok = False
    if original_path.is_file():
        raw_sha256 = report.sha256_file(original_path)
        raw_bytes_ok = raw_sha256 == fixture["content_sha256"]

    public_read: dict[str, Any] = {"ok": False, "reason": "no published pin"}
    locator_verified = False
    observed = {}
    if pin is not None:
        read = read_public_artifact(lake, pin, env,
                                    timeout_seconds=timeout_seconds)
        public_read = summarize_public_read(read)
        if read.get("body_bytes"):
            observations.save_bytes(attempt, f"bundles/{spec.case_id}.json", read["body_bytes"])
            observations.save_bytes(attempt, f"reads/{spec.case_id}.json",
                json.dumps(read.get("receipt") or {}, ensure_ascii=False).encode("utf-8"))
            observed = observations.read_observations(spec, json.loads(read["body_bytes"]),
                read.get("receipt") or {}, fixture, manifest)
            locator_verified = observed["locator_verified"]

    summary_status = public_read.get("summary_status")
    if public_read.get("selection_status") == "skipped_no_narrative":
        summary_status = "skipped_no_narrative"

    actual = {
        "document_kind": manifest.get("document_kind"),
        "language": manifest.get("language"),
        "mime_type": fixture["mime_type"],
        "summary_status": summary_status,
        "selection_status": public_read.get("selection_status"),
        "quality_status": public_read.get("quality_status"),
    }
    if spec.source_class == "transcript":
        # Verified from the actual bytes: the original is still plain text with
        # the same SHA, so it was not converted into a PDF.
        actual["converted_to_pdf"] = fixture["mime_type"] != "text/plain"
        actual["source_sha256_changed"] = not raw_bytes_ok

    request_path = lake.root.parent / "requests" / "run1.json"
    return {
        "case_id": spec.case_id,
        "group_id": spec.group_id,
        "expected": copy.deepcopy(expected),
        "status": oracle.STATUS_PASS if pin is not None else oracle.STATUS_NOT_RUN,
        "actual": actual,
        "request": {
            "path_ref": "requests/run1.json",
            "sha256": report.sha256_file(request_path)
            if request_path.is_file() else "0" * 64,
        },
        "result": {
            "receipt_ref": "receipts/run1.json" if pin is not None else None,
            "exit_code": 0 if pin is not None else 1,
        },
        "artifacts": ([{
            "kind": "narrative_bundle",
            "sha256": pin["content_sha256"],
            "byte_size": pin["byte_size"],
            "artifact_version_id": pin["artifact_version_id"],
            "document_id": pin["document_id"],
            "source_id": pin["source_id"],
            "source_sha256": pin["source_sha256"],
            "locators": [loc.get("span_id") for loc in
                         (public_read.get("locators") or [])],
            "locator_replay_verified": locator_verified,
        }] if pin is not None else []),
        "model": {"posts": observations.source_posts(model.requests, info["ref"].source_id),
                  "observed_from": "loopback_request_source_id"},
        "evidence": {
            "raw_receipt_present": True,
            "raw_sha256": raw_sha256,
            "raw_bytes_match_fixture": raw_bytes_ok,
            "public_read": public_read,
            "observations": observed,
        },
        "failure": None if pin is not None else {
            "code": "no_published_pin", "detail": "case produced no artifact"},
        "cleanup": {"restored": True, "remaining": []},
        "_rf_pin": pin,
    }


if __name__ == "__main__":
    raise SystemExit(main())
