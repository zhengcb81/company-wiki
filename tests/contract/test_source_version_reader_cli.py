"""Cross-process contract for the path-independent source-version reader."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.prompt_injection import (  # noqa: E402
    record_prompt_injection_review,
)
from company_wiki.source_catalog.source_read_policy import (  # noqa: E402
    source_read_policy_sha256,
)


BODY = b"%PDF-1.4\nFILING-SENTINEL-DONT-LEAK\x00\xff\n"
SHA = hashlib.sha256(BODY).hexdigest()


def _sidecar() -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-cli-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": SHA,
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    raw_root = tmp_path / "lake"
    raw_root.mkdir()
    raw_path = raw_root / "2025.pdf"
    raw_path.write_bytes(BODY)
    (raw_root / "2025.pdf.source.json").write_text(
        json.dumps(_sidecar()), encoding="utf-8"
    )
    catalog_dir = tmp_path / ".source_catalog"
    root = RootSpec(
        "future_lake", raw_root, "directory", priority=10,
        adapter_id="sidecar_filing_v1", read_only=True,
        reusable_for_filing=True,
    )
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=catalog_dir,
        roots=(root,), reusable_root_kinds=("directory",),
    ))
    catalog.scan()
    row = catalog.reader.fetchone(
        """SELECT d.document_id, d.primary_source_id AS source_id,
                  s.content_sha256
           FROM documents d JOIN sources s
             ON s.source_id=d.primary_source_id
           WHERE d.source_status='active' AND s.content_sha256=?""",
        (SHA,),
    )
    assert row is not None
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(catalog_dir),
        "roots": [{
            "root_id": "future_lake", "path": str(raw_root),
            "kind": "directory", "priority": 10,
            "adapter_id": "sidecar_filing_v1", "read_only": True,
            "reusable_for_filing": True,
        }],
        "reusable_root_kinds": ["directory"],
    }), encoding="utf-8")
    return config_path, raw_path, dict(row)


def _snapshot(directory: Path) -> dict[str, tuple]:
    """Detect created, removed, or content-modified fixture files.

    SQLite may touch the mtime of an unchanged ``-shm`` file while opening a
    read-only connection.  Path membership plus file size/content hash is the
    durable-state assertion this suite needs; directory mtimes are likewise
    runtime metadata rather than source content.
    """
    result = {}
    for path in directory.rglob("*"):
        key = path.relative_to(directory).as_posix()
        if path.is_file():
            result[key] = (
                "file", hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
            )
        else:
            result[key] = ("directory",)
    return result


def _contains_physical_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            any(token in str(key).lower() for token in ("path", "root", "location", "bundle"))
            or _contains_physical_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_physical_key(child) for child in value)
    return False


def _run_cli(
    config_path: Path, ids: dict[str, str], cwd: Path,
    *, expected_read_policy_sha256: str | None = None,
    include_availability_evidence: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
            sys.executable, "-m", "company_wiki.source_catalog.source_reader_cli",
            "--config", str(config_path),
            "--document-id", ids["document_id"],
            "--source-id", ids["source_id"],
            "--content-sha256", ids["content_sha256"],
    ]
    if expected_read_policy_sha256 is not None:
        command.extend(("--expected-read-policy-sha256", expected_read_policy_sha256))
    if include_availability_evidence:
        command.append("--include-availability-evidence")
    return subprocess.run(
        command,
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )


def test_optional_availability_receipt_keeps_default_and_unknown_dates(tmp_path: Path):
    config_path, _, ids = _fixture(tmp_path)
    before = _snapshot(tmp_path)
    default = _run_cli(config_path, ids, tmp_path)
    extended = _run_cli(config_path, ids, tmp_path, include_availability_evidence=True)
    assert default.returncode == extended.returncode == 0
    assert default.stdout == extended.stdout == BODY
    old = _json_stderr(default, tmp_path)
    new = _json_stderr(extended, tmp_path)
    assert old["schema_version"] == "2.1"
    assert new["schema_version"] == "2.2"
    assert set(new) == set(old) | {"availability_evidence"}
    assert new["availability_evidence"] is None  # bare collector time is not proof
    assert new["manifest"] == old["manifest"]
    assert _snapshot(tmp_path) == before


def test_optional_availability_receipt_opens_existing_capture_without_writes(tmp_path: Path):
    config_path, raw, ids = _fixture(tmp_path)
    sidecar = raw.with_name(raw.name + ".source.json")
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload.update({"byte_size": len(BODY), "mime_type": "application/pdf",
                    "adapter_name": "sec-reader", "adapter_version": "1.0.0"})
    payload["candidate"] = {k: payload[k] for k in ("provider", "provider_document_id", "source_url")}
    payload["receipt"] = {
        **{k: payload[k] for k in ("provider", "provider_document_id", "source_url",
                                  "content_sha256", "byte_size", "mime_type",
                                  "retrieved_at", "adapter_name", "adapter_version")},
        "schema_version": "1.0", "candidate_id": "doc-cli-1",
        "staged_path": "staging/2025.pdf", "http_status": 200,
    }
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    before = _snapshot(tmp_path)
    proc = _run_cli(config_path, ids, tmp_path, include_availability_evidence=True)
    assert proc.returncode == 0, proc.stderr
    receipt = _json_stderr(proc, tmp_path)
    proof = receipt["availability_evidence"]
    assert proc.stdout == BODY
    assert proof["source_sha256"] == SHA
    assert proof["available_by"] == "2026-02-21"
    assert receipt["manifest"]["published_date"] == "2026-02-20"
    assert str(tmp_path) not in proc.stderr.decode("utf-8")
    assert _snapshot(tmp_path) == before


def _run_query_cli(config_path: Path, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    request = {
        "entity": "Acme", "document_kind": "annual_report",
        "as_of_date": "2026-08-10", "market": "US", "security_id": "ACME",
        "form_type": "10-K", "fiscal_year": 2025,
        "provider": "sec", "provider_document_id": "doc-cli-1",
        "mode": "exact",
    }
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.source_query_cli",
         "--config", str(config_path)],
        input=json.dumps(request).encode("utf-8"), cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
    )



def _run_ensure_cli(
    config_path: Path,
    cwd: Path,
    *,
    source_ref_v2: bool,
    mode: str = "exact",
    market: str = "US",
    form_type: str = "10-K",
    entity: str = "Acme",
    security_id: str = "ACME",
    acquisition_config: Path | None = None,
    worker_config: Path | None = None,
    max_download_bytes: int | None = None,
    max_download_seconds: int | None = None,
    max_download_cost_usd: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable, "-m", "company_wiki.source_catalog.cli",
        "--config", str(config_path), "ensure",
        "--entity", entity, "--document-kind", "annual_report",
        "--as-of-date", "2026-08-10", "--market", market,
        "--security-id", security_id, "--form-type", form_type,
        "--fiscal-year", "2025", "--mode", mode,
    ]
    if acquisition_config is not None:
        command.extend(("--acquisition-config", str(acquisition_config)))
    if worker_config is not None:
        command.extend(("--worker-config", str(worker_config)))
    if max_download_bytes is not None:
        command.extend(("--max-download-bytes", str(max_download_bytes)))
    if max_download_seconds is not None:
        command.extend(("--max-download-seconds", str(max_download_seconds)))
    if max_download_cost_usd is not None:
        command.extend(("--max-download-cost-usd", max_download_cost_usd))
    if source_ref_v2:
        command.append("--source-ref-v2")
    return subprocess.run(
        command, cwd=cwd, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=30,
    )


def _fake_latest_as_of_configs(
    tmp_path: Path,
    config_path: Path,
    *,
    provider_unavailable: bool = False,
) -> tuple[Path, Path, Path]:
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    cli_config = config_dir / "source_catalog.yaml"
    catalog_config = json.loads(config_path.read_text(encoding="utf-8"))
    canonical_raw = tmp_path / "canonical-raw"
    canonical_raw.mkdir()
    catalog_config["roots"].append({
        "root_id": "company_raw",
        "path": str(canonical_raw),
        "kind": "company_raw",
        "priority": 5,
        "adapter_id": "sidecar_filing_v1",
        "read_only": False,
    })
    cli_config.write_text(json.dumps(catalog_config), encoding="utf-8")
    (tmp_path / "config.yaml").write_text("{}\n", encoding="utf-8")
    worker_config = config_dir / "source_catalog_worker.yaml"
    worker_config.write_text(json.dumps({
        "schema_version": "1.0",
        "runtime_config": "${PROJECT_ROOT}/config.yaml",
        "scan_interval_minutes": 60,
        "export_interval_minutes": 60,
        "poll_interval_seconds": 30,
        "idle_seconds_required": 600,
        "normalize_batch_size": 1,
        "llm_summary_batch_size": 1,
        "llm_max_input_chars": 1000,
        "llm_max_output_tokens": 100,
        "llm_retry_backoff_minutes": 1,
        "allow_processing_on_battery": False,
    }), encoding="utf-8")

    fake_adapter = tmp_path / "fake_adapter.py"
    fake_adapter.write_text(
        """from __future__ import annotations
import json
from pathlib import Path
import sys

action = sys.argv[1]
with Path(__file__).with_name('adapter-actions.jsonl').open('a', encoding='utf-8') as log:
    log.write(json.dumps({'action': action}) + '\\n')
if action == 'fetch':
    raise SystemExit('fetch must not run during latest_as_of discovery')
if Path(__file__).with_name('provider-unavailable').exists():
    raise SystemExit('simulated provider outage')
request = json.load(sys.stdin)
response = {
    'schema_version': '1.0',
    'status': 'ok',
    'adapter': {'name': 'fake-cn', 'version': '1.0'},
    'candidates': [{
        'candidate_id': 'candidate-2025',
        'provider': 'cninfo',
        'provider_document_id': 'announcement-2025',
        'market': 'CN',
        'title': 'Acme 2025 annual report',
        'source_url': 'https://example.test/acme-2025.pdf',
        'document_kind': request['document_kind'],
        'form_type': request.get('form_type'),
        'filing_date': '2026-04-15',
        'fiscal_year': 2025,
        'language': 'zh',
    }],
}
response['acquisition_usage'] = {
    'schema_version': '1.0', 'response_bytes': 0, 'cost_usd': '0'
}
for _ in range(4):
    encoded = json.dumps(response).encode('utf-8')
    response['acquisition_usage']['response_bytes'] = len(encoded)
print(json.dumps(response))
""",
        encoding="utf-8",
    )
    if provider_unavailable:
        (tmp_path / "provider-unavailable").write_text("1\n", encoding="utf-8")
    acquisition_config = config_dir / "source_acquisition.yaml"
    acquisition_config.write_text(json.dumps({
        "schema_version": "1.1",
        "staging_root": "${PROJECT_ROOT}/staging",
        "timeout_seconds": 30,
        "adapters": {
            "cn": {
                "name": "fake-cn", "version": "1.0",
                "interface": "json_command_v1",
                "supports_acquisition_budget": True,
                "project_root": "${PROJECT_ROOT}", "config_root": None,
                "command": [str(Path(sys.executable).resolve()), str(fake_adapter)],
            },
            "hk": {
                "name": "unused-hk", "version": "1.0",
                "interface": "dayu_cli_v1",
                "project_root": "${PROJECT_ROOT}",
                "config_root": "${PROJECT_ROOT}/config",
                "command": [str(Path(sys.executable).resolve()), str(fake_adapter)],
            },
            "us": {
                "name": "unused-us", "version": "1.0",
                "interface": "dayu_cli_v1",
                "project_root": "${PROJECT_ROOT}",
                "config_root": "${PROJECT_ROOT}/config",
                "command": [str(Path(sys.executable).resolve()), str(fake_adapter)],
            },
        },
    }), encoding="utf-8")
    return cli_config, acquisition_config, worker_config


def test_query_cli_returns_db_only_pathless_reviewed_candidate(tmp_path: Path):
    config_path, raw_path, ids = _fixture(tmp_path)
    catalog = SourceCatalog(load_catalog_config(config_path))
    with catalog.store.transaction() as connection:
        record_prompt_injection_review(
            connection, ids["document_id"], status="not_detected",
            reviewer="test-query-candidate", evidence_sha256=SHA,
            evidence_payload=BODY, now="2026-02-21T12:00:00Z",
            source_sha256=SHA, policy_hash="c" * 64,
        )
    catalog.close()
    raw_path.write_bytes(b"corrupted after indexing")

    queried = _run_query_cli(config_path, tmp_path)
    assert queried.returncode == 0, queried.stderr
    result = json.loads(queried.stdout)
    assert result["status"] == "found"
    assert result["request_id"].startswith("urn:company-wiki:source-request:sha256:")
    candidate = result["candidates"][0]
    assert candidate["source_ref"] == result["matches"][0]
    assert candidate["source_id"] == ids["source_id"]
    assert candidate["snapshot_sha256"] == SHA
    assert candidate["prompt_injection_status"] == "not_detected"
    assert candidate["capture_ready"] is True
    assert candidate["retrieved_at"] == "2026-02-21T00:00:00Z"
    assert candidate["collector_name"] == "filesystem-catalog-future_lake"
    assert candidate["capture_provenance"] == "indexed_location_manifest"
    assert candidate["https_url"] == "https://sec.gov/x/2025"
    assert str(tmp_path) not in queried.stdout.decode("utf-8")
    assert all(
        not any(token in key.lower() for token in ("path", "root", "location"))
        for key in candidate
    )
    refused = _run_cli(config_path, ids, tmp_path)
    assert refused.returncode == 2
    assert refused.stdout == b""


def test_query_cli_reports_unreviewed_candidate_with_capture_readiness(
    tmp_path: Path,
):
    config_path, _, _ = _fixture(tmp_path)
    queried = _run_query_cli(config_path, tmp_path)
    assert queried.returncode == 0, queried.stderr
    result = json.loads(queried.stdout)
    assert result["status"] == "found"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["prompt_injection_status"] == "not_reviewed"
    assert result["candidates"][0]["capture_ready"] is True
    opened = _run_cli(config_path, result["matches"][0], tmp_path)
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == BODY



def test_ensure_cli_v2_is_pathless_and_legacy_output_stays_compatible(
    tmp_path: Path,
):
    config_path, _, ids = _fixture(tmp_path)
    catalog = SourceCatalog(load_catalog_config(config_path))
    with catalog.store.transaction() as connection:
        record_prompt_injection_review(
            connection, ids["document_id"], status="not_detected",
            reviewer="test-operation-v2", evidence_sha256=SHA,
            evidence_payload=BODY, now="2026-02-21T12:00:00Z",
            source_sha256=SHA, policy_hash="d" * 64,
        )
    catalog.close()
    before = _snapshot(tmp_path / "lake")

    projected = _run_ensure_cli(config_path, tmp_path, source_ref_v2=True)
    assert projected.returncode == 0, projected.stderr
    result = json.loads(projected.stdout)
    assert result["operation_schema_version"] == "1.0"
    assert result["operation"] == "ensure"
    assert result["status"] == "completed"
    assert result["download_events"] == 0
    assert result["source_ref"]["content_sha256"] == SHA
    assert result["candidate"]["source_ref"] == result["source_ref"]
    assert result["candidate"]["prompt_injection_status"] == "not_detected"
    assert str(tmp_path) not in projected.stdout.decode("utf-8")
    assert all(
        not any(token in key.lower() for token in ("path", "root", "location", "bundle"))
        for key in result
    )

    legacy = _run_ensure_cli(config_path, tmp_path, source_ref_v2=False)
    assert legacy.returncode == 0, legacy.stderr
    legacy_payload = json.loads(legacy.stdout)
    assert "operation_schema_version" not in legacy_payload
    assert "canonical_path" in legacy.stdout.decode("utf-8")
    assert _snapshot(tmp_path / "lake") == before


def test_ensure_cli_latest_as_of_projects_gap_without_fetch_or_raw_change(
    tmp_path: Path,
):
    config_path, raw_path, _ = _fixture(tmp_path)
    cli_config, acquisition_config, worker_config = _fake_latest_as_of_configs(
        tmp_path, config_path
    )
    raw_before = _snapshot(tmp_path / "lake")
    raw_sha_before = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    projected = _run_ensure_cli(
        cli_config,
        tmp_path,
        source_ref_v2=True,
        mode="latest_as_of",
        market="CN",
        form_type="annual_report",
        entity="Beta",
        security_id="BETA",
        acquisition_config=acquisition_config,
        worker_config=worker_config,
        max_download_bytes=5_000_000,
        max_download_seconds=90,
        max_download_cost_usd="0",
    )

    assert projected.returncode == 0, projected.stderr
    result = json.loads(projected.stdout)
    assert result["operation_schema_version"] == "1.0"
    assert result["operation"] == "ensure"
    assert result["status"] == "gap", result
    assert result["request_id"].startswith("urn:company-wiki:source-request:sha256:")
    assert result["download_events"] == 0
    assert result["source_ref"] is None
    assert result["candidate"] is None
    assert result["gap_plan"]["request_id"] == result["request_id"]
    assert result["gap_plan"]["missing"] == [{
        "provider": "cninfo",
        "provider_document_id": "announcement-2025",
        "source_url": "https://example.test/acme-2025.pdf",
        "filing_date": "2026-04-15",
        "form_type": "annual_report",
        "fiscal_year": 2025,
        "fiscal_period": None,
    }]
    assert not _contains_physical_key(result)
    assert str(tmp_path) not in projected.stdout.decode("utf-8")
    actions = [
        json.loads(line)["action"]
        for line in (tmp_path / "adapter-actions.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert actions == ["discover"]
    assert not (tmp_path / "staging").exists()
    assert _snapshot(tmp_path / "lake") == raw_before
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_sha_before


def test_ensure_cli_latest_as_of_preserves_provider_unavailable_gap(
    tmp_path: Path,
):
    config_path, raw_path, _ = _fixture(tmp_path)
    cli_config, acquisition_config, worker_config = _fake_latest_as_of_configs(
        tmp_path, config_path, provider_unavailable=True
    )
    raw_before = _snapshot(tmp_path / "lake")
    raw_sha_before = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    projected = _run_ensure_cli(
        cli_config,
        tmp_path,
        source_ref_v2=True,
        mode="latest_as_of",
        market="CN",
        form_type="annual_report",
        entity="Beta",
        security_id="BETA",
        acquisition_config=acquisition_config,
        worker_config=worker_config,
        max_download_bytes=5_000_000,
        max_download_seconds=90,
        max_download_cost_usd="0",
    )

    assert projected.returncode == 0, projected.stderr
    result = json.loads(projected.stdout)
    assert result["status"] == "gap", result
    assert result["download_events"] == 0
    assert result["source_ref"] is None
    assert result["candidate"] is None
    assert result["gap_plan"]["provider_unavailable"] is True
    # Raw adapter exceptions may contain local paths or process details.  The
    # stable cross-process operation contract exposes the availability fact,
    # while keeping the diagnostic inside the producer/journal boundary.
    assert "provider_reason" not in result["gap_plan"]
    assert result["gap_plan"]["missing"] == []
    assert not _contains_physical_key(result)
    assert str(tmp_path) not in projected.stdout.decode("utf-8")
    actions = [
        json.loads(line)["action"]
        for line in (tmp_path / "adapter-actions.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert actions == ["discover"]
    assert not (tmp_path / "staging").exists()
    assert _snapshot(tmp_path / "lake") == raw_before
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_sha_before


def test_final_reader_receipt_reflects_review_removed_after_candidate_query(
    tmp_path: Path,
):
    config_path, _, ids = _fixture(tmp_path)
    catalog = SourceCatalog(load_catalog_config(config_path))
    with catalog.store.transaction() as connection:
        record_prompt_injection_review(
            connection, ids["document_id"], status="not_detected",
            reviewer="test-final-review", evidence_sha256=SHA,
            evidence_payload=BODY, now="2026-02-21T12:00:00Z",
            source_sha256=SHA, policy_hash="c" * 64,
        )
    catalog.close()
    candidate = json.loads(_run_query_cli(config_path, tmp_path).stdout)["candidates"][0]
    assert candidate["capture_ready"] is True

    catalog = SourceCatalog(load_catalog_config(config_path))
    with catalog.store.transaction() as connection:
        row = connection.execute(
            "SELECT metadata_json FROM documents WHERE document_id=?",
            (ids["document_id"],),
        ).fetchone()
        metadata = json.loads(row[0])
        metadata.pop("prompt_injection_review", None)
        connection.execute(
            "UPDATE documents SET metadata_json=? WHERE document_id=?",
            (json.dumps(metadata), ids["document_id"]),
        )
    catalog.close()

    opened = _run_cli(config_path, ids, tmp_path)
    assert opened.returncode == 0
    assert opened.stdout == BODY
    receipt = _json_stderr(opened, tmp_path)
    assert receipt["review"]["status"] == "not_reviewed"


def test_cli_reports_current_fingerprint_and_reads_bytes_despite_old_lineage(tmp_path: Path):
    config_path, _, ids = _fixture(tmp_path)
    cwd = tmp_path / "caller"
    cwd.mkdir()
    pin = source_read_policy_sha256(load_catalog_config(config_path), None)
    opened = _run_cli(config_path, ids, cwd, expected_read_policy_sha256=pin)
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == BODY
    assert _json_stderr(opened, tmp_path)["source_read_policy_sha256"] == pin

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["roots"][0]["max_file_size"] = 1024 * 1024
    config_path.write_text(json.dumps(config), encoding="utf-8")
    before = _snapshot(tmp_path)
    current = _run_cli(config_path, ids, cwd, expected_read_policy_sha256=pin)
    assert current.returncode == 0 and current.stdout == BODY
    assert _json_stderr(current, tmp_path)["source_read_policy_sha256"] != pin
    assert _snapshot(tmp_path) == before


def test_resolve_cli_advertises_separate_read_policy_pin(tmp_path: Path):
    original_config, _, _ = _fixture(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "source_catalog.yaml"
    config_path.write_bytes(original_config.read_bytes())
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [
            sys.executable, "-m", "company_wiki.source_catalog.cli",
            "--config", str(config_path), "resolve", "--entity", "Acme",
            "--document-kind", "annual_report", "--as-of-date", "2026-08-10",
            "--market", "US", "--security-id", "ACME",
            "--form-type", "10-K", "--fiscal-year", "2025",
            "--provider", "sec", "--provider-document-id", "doc-cli-1",
            "--mode", "exact",
        ],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    resolution = json.loads(proc.stdout)
    assert resolution["source_read_policy_sha256"] == source_read_policy_sha256(
        load_catalog_config(config_path, project_root=tmp_path), None
    )
    assert resolution["policy_export"]["policy_hash"] != resolution[
        "source_read_policy_sha256"
    ]


def _json_stderr(proc: subprocess.CompletedProcess[bytes], forbidden_root: Path) -> dict:
    assert proc.stderr.endswith(b"\n"), proc.stderr
    lines = proc.stderr.decode("utf-8").splitlines()
    assert len(lines) == 1, proc.stderr

    def reject_non_json_constant(value: str):
        raise AssertionError(f"non-JSON constant: {value}")

    payload = json.loads(lines[0], parse_constant=reject_non_json_constant)
    assert isinstance(payload, dict)
    assert not any(
        token in key.lower()
        for key in payload
        for token in ("path", "root", "location")
    )
    receipt_text = json.dumps(payload, ensure_ascii=False).replace("\\\\", "\\")
    assert str(forbidden_root).lower() not in receipt_text.lower()
    assert forbidden_root.as_posix().lower() not in receipt_text.lower()
    return payload


def test_cli_streams_verified_raw_bytes_and_json_receipts_without_catalog_writes(tmp_path: Path):
    config_path, raw_path, ids = _fixture(tmp_path)
    cwd = tmp_path / "caller"
    cwd.mkdir()
    before = _snapshot(tmp_path)

    opened = _run_cli(config_path, ids, cwd)
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == BODY  # Includes NUL and non-UTF-8: no text encoding.
    receipt = _json_stderr(opened, tmp_path)
    assert receipt["status"] == "ok"
    assert receipt["schema_version"] == "2.1"
    for key in ("document_id", "source_id", "content_sha256"):
        assert receipt[key] == ids[key]
    assert receipt["byte_size"] == len(BODY)
    manifest = receipt["manifest"]
    assert manifest["document_id"] == ids["document_id"]
    assert manifest["source_id"] == ids["source_id"]
    assert manifest["content_sha256"] == ids["content_sha256"]
    assert manifest["byte_size"] == len(BODY)
    assert manifest["mime_type"] == "application/pdf"
    assert manifest["fiscal_year"] == 2025
    assert manifest["form_type"] == "10-K"
    assert manifest["provider_document_id"] == "doc-cli-1"
    assert manifest["source_url"] == "https://sec.gov/x/2025"
    assert _snapshot(tmp_path) == before

    # The catalog still claims SHA, but the physical file now has different
    # bytes of the same size. The CLI must hash what it actually opened.
    raw_path.write_bytes(BODY[:-1] + b"X")
    before_refusal = _snapshot(tmp_path)
    refused = _run_cli(config_path, ids, cwd)
    assert refused.returncode != 0
    assert refused.stdout == b""
    error = _json_stderr(refused, tmp_path)
    assert error["status"] == "unavailable"
    assert error["reason"] == "no_verified_location"
    assert b"FILING-SENTINEL-DONT-LEAK" not in refused.stderr
    assert _snapshot(tmp_path) == before_refusal

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["company-wiki-source-read"] == (
        "company_wiki.source_catalog.source_reader_cli:main"
    )


def test_query_cli_returns_only_pathless_local_refs_without_download(tmp_path: Path):
    config_path, _, ids = _fixture(tmp_path)
    cwd = tmp_path / "caller"
    cwd.mkdir()
    before = _snapshot(tmp_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    request = {
        "entity": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "form_type": "10-K",
        "fiscal_year": 2025,
        "provider": "sec",
        "provider_document_id": "doc-cli-1",
        "as_of_date": "2026-08-10",
        "mode": "exact",
        "allow_download": True,
    }
    proc = subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.source_query_cli",
         "--config", str(config_path)],
        input=json.dumps(request).encode("utf-8"),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == b""
    assert proc.stdout.endswith(b"\n")
    assert len(proc.stdout.splitlines()) == 1
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "2.0"
    assert payload["status"] == "found"
    assert payload["source_read_policy_sha256"] == source_read_policy_sha256(
        load_catalog_config(config_path), None
    )
    assert len(payload["matches"]) == 1
    match = payload["matches"][0]
    assert match["document_id"] == ids["document_id"]
    assert match["source_id"] == ids["source_id"]
    assert match["content_sha256"] == ids["content_sha256"]
    assert not any(
        token in key.lower()
        for key in match
        for token in ("path", "root", "location")
    )
    assert str(tmp_path) not in proc.stdout.decode("utf-8")
    assert _snapshot(tmp_path) == before

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["company-wiki-source-query"] == (
        "company_wiki.source_catalog.source_query_cli:main"
    )


def test_both_clis_resolve_project_root_from_production_config_layout(tmp_path: Path):
    _, _, ids = _fixture(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [{
            "root_id": "future_lake",
            "path": "${PROJECT_ROOT}/lake",
            "kind": "directory",
            "priority": 10,
            "adapter_id": "sidecar_filing_v1",
            "read_only": True,
            "reusable_for_filing": True,
        }],
        "reusable_root_kinds": ["directory"],
    }), encoding="utf-8")
    cwd = tmp_path / "caller"
    cwd.mkdir()

    opened = _run_cli(config_path, ids, cwd)
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == BODY

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    query = subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.source_query_cli",
         "--config", str(config_path)],
        input=json.dumps({
            "entity": "Acme", "market": "US", "security_id": "ACME",
            "document_kind": "annual_report", "form_type": "10-K",
            "fiscal_year": 2025, "provider": "sec",
            "provider_document_id": "doc-cli-1",
            "as_of_date": "2026-08-10", "mode": "exact",
        }).encode("utf-8"),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )
    assert query.returncode == 0, query.stderr
    assert json.loads(query.stdout)["matches"][0]["source_id"] == ids["source_id"]
