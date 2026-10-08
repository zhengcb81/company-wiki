"""Manual cross-repository FF -> ET -> CWP contract acceptance.

Run from the company-wiki root with:

    python -B tests/e2e/run_ff_et_cwp_offline_acceptance.py \
      --ff-root C:/path/to/filing-fetch \
      --et-root C:/path/to/earnings-transcripts-s3-deadline

This is intentionally not named ``test_*.py``: it is an explicit offline
acceptance run, not part of the normal CI suite. It calls FF's real companion
transport, ET's real CLI/supervisor/worker/API/serializer, and CWP's real
import/query/open CLIs. Only provider HTTP is replaced through ET's private
worker-launcher seam. All writes stay inside one automatically removed temp
directory; no live provider, LLM, API key, production catalog or real company
document is used.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any


_CWP_ROOT = Path(__file__).resolve().parents[2]
_CWP_GOLDEN = _CWP_ROOT / "tests" / "fixtures" / "transcript_fmp" / "fmp_v2.fetched.json"
_FAKE_KEY = "offline-cross-repo-fake-key"


def _request(timeout_seconds: int) -> dict[str, Any]:
    return {
        "as_of_date": "2026-09-30",
        "companion_transcript": {
            "intent": "fetch_if_missing",
            "fiscal_year": 2026,
            "fiscal_quarter": 3,
            "provider": "fmp",
            "acquisition_limits": {
                "max_bytes": 1_000_000,
                "timeout_seconds": timeout_seconds,
                "max_cost_usd": "0.00",
            },
        },
    }


def _filing() -> dict[str, Any]:
    return {
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "urn:company-wiki:document:sha256:" + "a" * 64,
            "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
            "content_sha256": "a" * 64,
            "byte_size": 100,
            "mime_type": "application/pdf",
        },
        "company_identity": {
            "canonical_name": "Microsoft Corporation",
            "market": "US",
            "security_id": "MSFT",
            "ticker": "MSFT",
            "exchange": "NASDAQ",
            "verified": True,
            "active": True,
        },
    }


def _write_source_catalog(wiki_root: Path) -> None:
    (wiki_root / "companies").mkdir(parents=True)
    config = wiki_root / "config"
    config.mkdir()
    (config / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: .source_catalog\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    path: companies\n"
        "    kind: company_raw\n"
        "    priority: 10\n"
        "    adapter_id: company_raw_v1\n"
        "    read_only: false\n",
        encoding="utf-8",
    )


def _write_et_test_cli(scratch: Path) -> Path:
    """Wrap ET's actual CLI entry solely to inject fake worker HTTP."""
    fake_module = scratch / "fake_et_worker.py"
    fake_module.write_text(
        textwrap.dedent(
            '''\
            import json
            import os
            from pathlib import Path
            import time

            class Response:
                def __init__(self, payload):
                    self.url = "https://financialmodelingprep.com/stable/earning-call-transcript"
                    self.status_code = 200
                    self.headers = {"Content-Type": "application/json"}
                    self.payload = payload

                def iter_content(self, chunk_size):
                    for offset in range(0, len(self.payload), chunk_size):
                        yield self.payload[offset:offset + chunk_size]
                        if offset == 0:
                            time.sleep(float(os.environ.get("ET_DELAY_SECONDS", "0")))

                def close(self):
                    pass

            class Session:
                def __init__(self, spec):
                    self.headers = {}
                    self.spec = spec

                def get(self, url, **kwargs):
                    params = kwargs.get("params") or {}
                    assert params == {
                        "symbol": "MSFT", "year": 2026, "quarter": 3,
                        "apikey": os.environ["FMP_API_KEY"],
                    }, params
                    record = {
                        "event": "http_get", "pid": os.getpid(), "url": url,
                        "symbol": params["symbol"], "year": params["year"],
                        "quarter": params["quarter"],
                    }
                    with open(os.environ["ET_HTTP_LOG"], "a", encoding="utf-8") as stream:
                        stream.write(json.dumps(record) + "\\n")
                    return Response(Path(self.spec["payload_path"]).read_bytes())

                def close(self):
                    pass

            def make_session(spec, context):
                with open(os.environ["ET_HTTP_LOG"], "a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"event": "worker", "pid": os.getpid()}) + "\\n")
                return Session(spec)
            '''
        ),
        encoding="utf-8",
    )
    wrapper = scratch / "et_cli_wrapper.py"
    wrapper.write_text(
        textwrap.dedent(
            '''\
            import os
            from pathlib import Path
            import json
            import sys

            sys.path.insert(0, os.environ["ET_ROOT"])
            from transcript_api import ProviderSettings
            from transcript_tool import main

            raw_request = sys.stdin.read()
            request = json.loads(raw_request)
            safe_request = {
                key: request.get(key)
                for key in (
                    "schema_version", "request_id", "ticker", "exchange",
                    "fiscal_year", "fiscal_quarter", "provider",
                    "timeout_seconds", "max_body_bytes", "max_cost_usd",
                )
            }
            with open(os.environ["ET_CLI_LOG"], "a", encoding="utf-8") as stream:
                stream.write(json.dumps(safe_request) + "\\n")
            assert request["max_cost_usd"] == "0.00"
            sys.stdin = __import__("io").StringIO(raw_request)

            raise SystemExit(main(
                sys.argv[1:],
                _provider_settings=ProviderSettings(),
                _retrieval_launcher="fake_et_worker:make_session",
                _retrieval_spec={
                    "payload_path": os.environ["ET_PAYLOAD_PATH"],
                    "delay_seconds": float(os.environ.get("ET_DELAY_SECONDS", "0")),
                },
                _retrieval_temp_root=Path(os.environ["ET_WORKER_ROOT"]),
            ))
            '''
        ),
        encoding="utf-8",
    )
    return wrapper


class _Environment:
    """Temporarily expose only test paths/key to FF's subprocess transport."""

    def __init__(self, values: dict[str, str]):
        self.values = values
        self.original: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self.values.items():
            self.original[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, *exc: object) -> None:
        for key, value in self.original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _resolve(
    ff_scripts: Path,
    wiki_root: Path,
    tool: Path,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    sys.path.insert(0, str(ff_scripts))
    from transcript_companion import resolve_companion_transcript
    from transcript_tool_transport import EarningsTranscriptsTransport

    transport = EarningsTranscriptsTransport(
        wiki_root=wiki_root,
        transcript_tool=tool,
        deadline=time.monotonic() + timeout + 60,
    )
    result = resolve_companion_transcript(
        request=_request(timeout),
        filing_handle=_filing(),
        transport=transport,
    )
    return result, transport.company_wiki_calls


def _bootstrap_catalog(wiki_root: Path, env: dict[str, str]) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            str(wiki_root / "config" / "source_catalog.yaml"),
            "scan",
            "--root-id",
            "company_raw",
        ],
        cwd=wiki_root,
        env=env,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "CWP catalog bootstrap failed: "
            + completed.stderr.decode("utf-8", errors="replace")
        )


def _scenario(
    *,
    ff_scripts: Path,
    et_root: Path,
    payload: bytes,
    expected_sha: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cwpet-") as raw_scratch:
        scratch = Path(raw_scratch)
        wiki_root = scratch / "w"
        wiki_root.mkdir()
        _write_source_catalog(wiki_root)
        payload_path = scratch / "p.json"
        payload_path.write_bytes(payload)
        worker_root = scratch / "ew"
        worker_root.mkdir()
        http_log = scratch / "h.jsonl"
        tool = _write_et_test_cli(scratch)

        env = dict(os.environ)
        env.update(
            {
                "ET_ROOT": str(et_root),
                "ET_PAYLOAD_PATH": str(payload_path),
                "ET_WORKER_ROOT": str(worker_root),
                "ET_HTTP_LOG": str(http_log),
                "ET_CLI_LOG": str(scratch / "cli.jsonl"),
                "ET_DELAY_SECONDS": "0",
                "FMP_API_KEY": _FAKE_KEY,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
            }
        )
        paths = [str(scratch), str(et_root), str(_CWP_ROOT / "src")]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        _bootstrap_catalog(wiki_root, env)

        with _Environment(env):
            first, first_cwp_calls = _resolve(ff_scripts, wiki_root, tool, 30)
            assert first.get("status") == "downloaded", first
            assert first.get("provider_calls") == 1
            assert first["provider_requests"] == 1
            assert first["provider_response_bytes"] == len(payload)
            assert first["provider_usage_complete"] is True
            assert first.get("publication_date") is None
            assert first.get("as_of_cutoff_verified") is False
            ref = first.get("source_ref")
            assert isinstance(ref, dict)
            assert set(ref) == {
                "schema_version", "document_id", "source_id",
                "content_sha256", "byte_size", "mime_type",
            }
            assert ref["content_sha256"] == expected_sha
            assert ref["byte_size"] == len(payload)
            assert ref["mime_type"] == "application/json"

            raw_files = [
                path for path in (wiki_root / "companies").rglob("*")
                if path.is_file() and not path.name.endswith(".source.json")
            ]
            assert len(raw_files) == 1, raw_files
            assert raw_files[0].read_bytes() == payload
            assert hashlib.sha256(raw_files[0].read_bytes()).hexdigest() == expected_sha

            # FF's successful transport itself queried, imported and opened
            # through real CWP CLIs. Repeat on a fresh FF transport to verify
            # the CWP unknown-publication replay does not hit ET/provider again.
            second, second_cwp_calls = _resolve(ff_scripts, wiki_root, tool, 30)
            assert second.get("status") == "unknown_publication", second
            assert second.get("source_ref") == ref
            assert second.get("provider_calls") == 0
            assert second.get("as_of_cutoff_verified") is False
            assert len(list((wiki_root / "companies").rglob("*.source.json"))) == 1
            assert len(raw_files) == 1

            http_records = [
                json.loads(line)
                for line in http_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert [row["event"] for row in http_records].count("http_get") == 1
            assert [row["event"] for row in http_records].count("worker") == 1
            assert list(worker_root.iterdir()) == []
            cli_records = [
                json.loads(line)
                for line in Path(env["ET_CLI_LOG"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(cli_records) == 1, cli_records
            assert cli_records[0]["ticker"] == "MSFT"
            assert cli_records[0]["exchange"] == "nasdaq"
            assert cli_records[0]["fiscal_year"] == 2026
            assert cli_records[0]["fiscal_quarter"] == 3
            assert cli_records[0]["timeout_seconds"] == 30
            assert cli_records[0]["max_body_bytes"] == 1_000_000
            assert cli_records[0]["max_cost_usd"] == "0.00"
            assert _FAKE_KEY not in json.dumps(first)
            assert _FAKE_KEY not in http_log.read_text(encoding="utf-8")
            assert _FAKE_KEY not in Path(env["ET_CLI_LOG"]).read_text(encoding="utf-8")

            # A finite provider stall exercises the contract boundary between
            # FF's subprocess timeout and ET's worker deadline cleanup. The
            # fake provider eventually returns, so the test can safely inspect
            # any abandoned worker directory before the scratch root is removed.
            timeout_wiki = scratch / "tw"
            timeout_wiki.mkdir()
            _write_source_catalog(timeout_wiki)
            timeout_worker_root = scratch / "tw-worker"
            timeout_worker_root.mkdir()
            timeout_http_log = scratch / "th.jsonl"
            timeout_env = dict(env)
            timeout_env.update(
                {
                    "ET_WORKER_ROOT": str(timeout_worker_root),
                    "ET_HTTP_LOG": str(timeout_http_log),
                    "ET_CLI_LOG": str(scratch / "timeout-cli.jsonl"),
                    "ET_DELAY_SECONDS": "5",
                }
            )
            _bootstrap_catalog(timeout_wiki, timeout_env)
            with _Environment(timeout_env):
                timed_out, _ = _resolve(ff_scripts, timeout_wiki, tool, 2)
            assert timed_out.get("status") == "provider_unavailable", timed_out
            assert timed_out.get("reason") == "provider_deadline", timed_out
            timeout_cli = [
                json.loads(line)
                for line in Path(timeout_env["ET_CLI_LOG"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(timeout_cli) == 1
            assert timeout_cli[0]["timeout_seconds"] == 2
            assert timeout_cli[0]["max_body_bytes"] == 1_000_000
            timeout_leftovers = list(timeout_worker_root.iterdir())
            if timeout_leftovers:
                # On a regressed FF timeout the ET wrapper may have been killed
                # before its finite fake worker exits. Wait for that worker
                # before the temporary root's finally-cleanup removes files.
                time.sleep(7)
                timeout_leftovers = list(timeout_worker_root.iterdir())
            assert not timeout_leftovers, (
                "ET worker scratch survived FF timeout: "
                + ", ".join(path.name for path in timeout_leftovers)
            )
            assert not [
                path for path in (timeout_wiki / "companies").rglob("*")
                if path.is_file() and not path.name.endswith(".source.json")
            ], "timed out provider response must not be imported"
            result = {
                "source_ref": ref,
                "first_provider_calls": first["provider_calls"],
                "second_provider_calls": second["provider_calls"],
                "http_gets": 1,
                "max_cost_usd": "0.00",
                "provider_requests": first["provider_requests"],
                "provider_usage_complete": first["provider_usage_complete"],
                "worker_runs": 1,
                "cwp_calls": first_cwp_calls + second_cwp_calls,
                "timeout_provider_calls": timed_out.get("provider_calls"),
                "timeout_cleanup": "clean",
            }
    assert not Path(raw_scratch).exists(), "temporary E2E root was not removed"
    return result


def _run(args: argparse.Namespace) -> None:
    ff_root = args.ff_root.resolve(strict=True)
    et_root = args.et_root.resolve(strict=True)
    ff_scripts = ff_root / "scripts"
    et_tool = et_root / "transcript_tool.py"
    et_golden = et_root / "tests" / "golden" / "fmp_v2.fetched.json"
    if not ff_scripts.is_dir() or not et_tool.is_file() or not et_golden.is_file():
        raise SystemExit("FF scripts or ET CLI/FMP producer golden not found")
    et_payload = json.loads(et_golden.read_text(encoding="utf-8"))
    cwp_golden = json.loads(_CWP_GOLDEN.read_text(encoding="utf-8"))
    if et_payload != cwp_golden:
        raise AssertionError("CWP fixture differs from ET's producer golden")
    original = base64.b64decode(et_payload["provider_payload_base64"], validate=True)
    original_sha = hashlib.sha256(original).hexdigest()
    if et_payload.get("provider_payload_sha256") != original_sha:
        raise AssertionError("ET FMP golden's provider payload SHA is invalid")
    provider_rows = json.loads(original.decode("utf-8"))
    if not isinstance(provider_rows, list) or len(provider_rows) != 1:
        raise AssertionError("ET golden must contain one exact-period FMP row")
    provider_row = provider_rows[0]
    if (provider_row.get("symbol"), provider_row.get("year"), provider_row.get("period")) != (
        "MSFT", 2026, "Q3",
    ):
        raise AssertionError("ET FMP golden does not match the fixed MSFT FY/Q request")
    canonical_text = provider_row["content"].replace("\r\n", "\n").replace("\r", "\n").strip()
    canonical_bytes = canonical_text.encode("utf-8")
    if hashlib.sha256(canonical_bytes).hexdigest() != et_payload["canonical_content_sha256"]:
        raise AssertionError("ET golden's extracted untranslated text SHA is invalid")
    if len(canonical_bytes) != et_payload["content_bytes"]:
        raise AssertionError("ET golden's extracted untranslated text size is invalid")

    result = _scenario(
        ff_scripts=ff_scripts,
        et_root=et_root,
        payload=original,
        expected_sha=original_sha,
    )
    assert result["http_gets"] == 1 and result["worker_runs"] == 1
    print(
        "SUCCESS: FF companion -> ET production CLI/supervisor/worker/API -> "
        "CWP importer/query/verified SourceRef open; exact untranslated FMP "
        "JSON bytes and SHA/size verified; duplicate replay made zero provider "
        "calls; ET worker temp cleaned; all test data was confined to a temp root."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--et-root", type=Path, required=True)
    args = parser.parse_args()
    _run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
