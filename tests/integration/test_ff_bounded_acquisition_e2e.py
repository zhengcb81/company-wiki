"""Opt-in FF → CWP composition with isolated state and a local provider fixture."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord
from support.acquisition_cli_fixture import RAW_BODY, fixture_root


pytestmark = [pytest.mark.public_owner]


@pytest.fixture
def ff_entrypoint() -> Path:
    entrypoint = os.environ.get("CWP_TEST_FF_ENTRYPOINT")
    if entrypoint is None:
        pytest.skip("Set CWP_TEST_FF_ENTRYPOINT to the reviewed public FF CLI")
    path = Path(entrypoint)
    assert path.is_absolute() and path.is_file()
    return path


@pytest.fixture
def isolated_wiki_root(tmp_path):
    assert not list(tmp_path.iterdir())
    with TemporaryDirectory(prefix="ff-", dir=tmp_path) as workspace:
        yield Path(workspace)
    assert not list(tmp_path.iterdir())


class FilingRoundTrip:
    def __init__(self, root: Path, ff: Path, identity: SecurityRecord):
        self.root = root
        self.catalog, acquisition, self.log = fixture_root(root, "ok")
        self.env = dict(
            os.environ,
            PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
            PYTHONUTF8="1",
            PYTHONDONTWRITEBYTECODE="1",
        )
        snapshots = SecurityMasterStore(root / "catalog" / "security_master")
        snapshots.write_market(
            identity.market, (identity,), retrieved_at="2026-10-09T12:00:00Z",
            sources=(identity.source_url,),
        )
        config = root / "ff.json"
        config.write_text(json.dumps({
            "schema_version": "1.0",
            "connection": {
                "cwd": str(root),
                "acquisition_config": str(acquisition),
                "commands": {
                    "catalog": self.cwp_command("cli"),
                    "query": self.cwp_command("source_query_cli"),
                    "local_prepare": self.cwp_command("local_prepare_cli"),
                    "open": self.cwp_command("source_reader_cli"),
                },
            },
        }), encoding="utf-8")
        self.ff_command = [sys.executable, "-B", str(ff), "--config", str(config), "--timeout-seconds", "45"]

    def cwp_command(self, module: str) -> list[str]:
        return [
            sys.executable, "-B", "-m", f"company_wiki.source_catalog.{module}",
            "--config", str(self.catalog),
        ]

    def run(self, command: list[str], *, stdin: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            command, input=stdin, capture_output=True, cwd=self.root,
            env=self.env, timeout=55, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def fetch(self, request: dict[str, Any], *, download: bool = False) -> tuple[int, dict]:
        args = [*self.ff_command, "--allow-download"] if download else self.ff_command
        result = self.run(args, stdin=json.dumps(request, ensure_ascii=False).encode("utf-8"))
        assert result.stdout, result.stderr
        return result.returncode, json.loads(result.stdout)

    def open_original(self, source_ref: dict) -> subprocess.CompletedProcess:
        return self.run([
            *self.cwp_command("source_reader_cli"),
            "--document-id", source_ref["document_id"],
            "--source-id", source_ref["source_id"],
            "--content-sha256", source_ref["content_sha256"],
        ])

    def provider_calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


@pytest.mark.parametrize("market,exchange,code,provider,domain,year", [
    ("CN", "SZSE", "300750", "cninfo", "www.cninfo.com.cn", 2024),
    ("HK", "HKEX", "00700", "hkexnews", "www.hkexnews.hk", 2025),
    ("US", "NASDAQ", "FIXTURE", "sec", "www.sec.gov", 2025),
], ids=["CN", "HK", "US"])
def test_bounded_import_reuse_and_verified_read(
    isolated_wiki_root, ff_entrypoint, market, exchange, code, provider, domain, year,
):
    root = isolated_wiki_root
    endpoint = FilingRoundTrip(root, ff_entrypoint, SecurityRecord(
        canonical_name=f"Fixture {market}", market=market, exchange=exchange,
        ticker=code, security_id=code, aliases=(), active=True,
        source_name=provider, source_url=f"https://{domain}/identity",
        source_record_id=f"fixture-{market}", identifiers={},
    ))
    request = {
        "schema_version": "1.1", "company_query": code, "market": market,
        "document_kind": "annual_report", "fiscal_year": year, "as_of_date": "2026-10-09",
    }
    rc, no_budget = endpoint.fetch(request, download=True)
    assert rc != 0 and no_budget["downloads"] == 0
    assert no_budget["upstream_cause"]["operation"] == "ensure"
    assert not endpoint.provider_calls()

    bounded = dict(request, acquisition_limits={
        "max_bytes": 10_000, "timeout_seconds": 40, "max_cost_usd": "0.05",
    })
    rc, payload = endpoint.fetch(bounded, download=True)
    assert rc == 0 and payload["status"] == "capture_ready", payload
    assert payload["downloads"] == 1
    assert endpoint.provider_calls() == ["discover", "fetch"]
    original = Path(payload["handle"]["canonical_path"]).resolve(strict=True)
    assert original.is_relative_to((root / "companies").resolve())
    before = (original.stat().st_mtime_ns, hashlib.sha256(original.read_bytes()).hexdigest())

    rc, reused = endpoint.fetch(bounded, download=True)
    assert rc == 0 and reused["status"] == "capture_ready", reused
    assert reused["downloads"] == 0
    assert reused["handle"]["source_id"] == payload["handle"]["source_id"]
    assert (original.stat().st_mtime_ns, hashlib.sha256(original.read_bytes()).hexdigest()) == before

    rc, candidate = endpoint.fetch(dict(
        request, schema_version="2.0", filing_intent="reuse_only", mode="exact",
    ))
    assert rc == 0 and candidate["status"] == "source_candidate", candidate
    assert candidate["downloads"] == 0 and "canonical_path" not in json.dumps(candidate)
    ref = candidate["filing"]["source_ref"]
    assert ref["source_id"] == payload["handle"]["source_id"]
    assert ref["content_sha256"] == before[1]
    opened = endpoint.open_original(ref)
    assert opened.returncode == 0 and opened.stdout == RAW_BODY, opened.stderr
    assert endpoint.provider_calls() == ["discover", "fetch"]

    if market == "CN":
        damaged = b"X" + RAW_BODY[1:]
        original.write_bytes(damaged)
        for with_download_intent in (False, True):
            rc, error = endpoint.fetch(bounded if with_download_intent else request, download=with_download_intent)
            assert rc != 0 and error["downloads"] == 0, error
        refused = endpoint.open_original(ref)
        assert refused.returncode == 2 and refused.stdout == b"", refused.stderr
        assert original.read_bytes() == damaged
        assert endpoint.provider_calls() == ["discover", "fetch"]
    assert not (root / "catalog" / "operation.lock").exists()
    assert not any(path.is_file() for path in (root / "staging").rglob("*"))
