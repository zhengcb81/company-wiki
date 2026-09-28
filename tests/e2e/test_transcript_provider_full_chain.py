"""Full offline transcript provider -> canonical reader -> evidence E2E."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import uuid

import pytest

from company_wiki.source_catalog import SourceCatalog, load_catalog_config
from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.flags import FLAGS
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text,
    select_narrative_evidence,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.provider_use_policy import ACTIONS
from company_wiki.source_catalog.policy_2x import export_policy_2x
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.runtime_policy import build_snapshot
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_catalog.store import canonical_json
from company_wiki.source_catalog.transcript_material import extract_transcript_material


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FAKE_TOOL = Path(__file__).parent / "fixtures" / "fake_earnings_transcript_tool.py"
PROVIDER_STDOUT_LIMIT = 256 * 1024


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _policy_payload(actions: set[str] | None = None, *, revoked: bool = False) -> dict:
    payload = {
        "schema_version": "provider-use-policy/1",
        "policy_id": "full-provider-e2e",
        "rules": [{
            "provider_id": "fixture_provider",
            "origin_host": "fixtures.invalid",
            "path_prefix": "/transcripts",
            "content_class": "earnings_call_transcript",
            "rights_evidence_ref": "synthetic fixture only",
            "rights_evidence_sha256": hashlib.sha256(b"fixture only").hexdigest(),
            "reviewer": "e2e-test",
            "reviewed_at": "2026-01-01",
            "valid_from": "2026-01-01",
            "valid_until": "2035-12-31",
            "permitted_actions": sorted(ACTIONS if actions is None else actions),
            "retention_scope": "company_wiki_local",
            "export_scope": "none",
            "revoked": revoked,
        }],
    }
    payload["policy_sha256"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return payload


def _write_policy(root: Path, actions: set[str] | None = None, *, revoked: bool = False) -> None:
    path = root / "config" / "provider_use_policy.json"
    path.write_text(
        json.dumps(_policy_payload(actions, revoked=revoked), ensure_ascii=False),
        encoding="utf-8",
    )


def _wiki_root(tmp_path: Path) -> Path:
    root = tmp_path / f"m2p-{uuid.uuid4().hex}"
    assert not root.exists()
    (root / "companies").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "config" / "source_catalog.yaml").write_text(
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
    catalog_dir = root / ".source_catalog"
    catalog_dir.mkdir()
    now_text = _now().strftime("%Y-%m-%dT%H:%M:%SZ")
    config = load_catalog_config(
        root / "config" / "source_catalog.yaml", project_root=root
    )
    runtime = {
        "schema_version": "1.0",
        "flags": {name: name == "legacy_bridge_enabled" for name in FLAGS},
        "policy_hash": export_policy_2x(config)[0],
        "current_epoch": "full-provider-e2e",
        "active_cohorts": [],
        "updated_at": now_text,
    }
    (catalog_dir / "runtime_policy.json").write_text(
        json.dumps(build_snapshot(runtime), ensure_ascii=False), encoding="utf-8"
    )
    _write_policy(root)
    return root


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _run_cwp(root: Path, operation: str, payload: dict) -> tuple[subprocess.CompletedProcess, dict]:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.transcript_import_cli",
            "--wiki-root",
            str(root),
            "--operation",
            operation,
        ],
        cwd=REPO_ROOT,
        env=_environment(),
        input=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        capture_output=True,
        timeout=45,
        check=False,
    )
    return process, json.loads(process.stdout)


def _run_provider(
    root: Path,
    operation: str,
    payload: dict,
    *,
    fixture: str = "html",
    fault: str = "ok",
    timeout: float = 5,
) -> dict:
    process = subprocess.Popen(
        [
            sys.executable,
            str(FAKE_TOOL),
            "--operation",
            operation,
            "--state-dir",
            str(root / "provider-state"),
            "--fixture",
            fixture,
            "--fault",
            fault,
        ],
        cwd=REPO_ROOT,
        env=_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    request_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    try:
        stdout, stderr = process.communicate(request_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)
        raise
    assert process.returncode == 0, stderr.decode("utf-8", errors="replace")
    if len(stdout) > PROVIDER_STDOUT_LIMIT:
        raise ValueError("provider stdout exceeds limit")
    return json.loads(stdout.decode("utf-8", errors="strict"))


def _provider_request() -> dict:
    source_request = _source_request()
    return {
        "schema_version": "earnings-transcript-request/1",
        "request_id": source_request.request_id,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "as_of_date": "2026-09-27",
        "provider": "fixture_provider",
        "download_authorized": True,
        "timeout_seconds": 5,
        "max_body_bytes": 1024 * 1024,
    }


def _source_request() -> SourceRequest:
    return SourceRequest(
        entity="Acme Inc.",
        market="US",
        security_id="ACME",
        document_kind="investor_call_transcript",
        fiscal_year=2026,
        fiscal_period="Q2",
        as_of_date="2026-09-27",
        allow_download=True,
    )


def _candidate(discovery: dict) -> DownloadCandidate:
    item = discovery["candidates"][0]
    return DownloadCandidate(
        candidate_id="fixture:acme-2026-q2",
        provider=item["provider"],
        provider_document_id=item["provider_document_id"],
        market="US",
        entity="Acme Inc.",
        title="Acme 2026 Q2 Earnings Call Transcript",
        source_url=item["source_url"],
        document_kind="investor_call_transcript",
        filing_date=item["published_date"],
        fiscal_year=2026,
        fiscal_period="Q2",
        language="en",
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "ACME", "exchange": "NASDAQ"},
            separators=(",", ":"),
        ),
    )


def _discovery_preflight(root: Path, candidate: DownloadCandidate) -> dict:
    request = _provider_request()
    payload = {
        "schema_version": "company-wiki-transcript-discovery-preflight-request/1",
        "request_id": request["request_id"],
        "provider": candidate.provider,
        "source_url": candidate.source_url,
        "market": "US",
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "as_of_date": "2026-09-27",
    }
    process, decision = _run_cwp(root, "preflight-discovery", payload)
    assert process.returncode == 0
    return decision


def _candidate_preflight(root: Path, request: SourceRequest, candidate: DownloadCandidate) -> dict:
    payload = {
        "schema_version": "company-wiki-transcript-candidate-preflight-request/1",
        "source_request": request.to_dict(),
        "candidate": candidate.to_dict(),
        "max_bytes": 1024 * 1024,
        "expires_at": (_now() + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    process, decision = _run_cwp(root, "preflight-candidate", payload)
    assert process.returncode == 0
    return decision


def _fetch_request(candidate: DownloadCandidate) -> dict:
    request = _provider_request()
    return {
        **{key: value for key, value in request.items() if key != "schema_version"},
        "schema_version": "earnings-transcript-candidate-fetch-request/1",
        "candidate": {
            "provider_document_id": candidate.provider_document_id,
            "source_url": candidate.source_url,
            "published_date": candidate.filing_date,
        },
    }


def _import_payload(preflight: dict, transcript_result: dict) -> dict:
    return {
        "schema_version": "company-wiki-transcript-import-request/1",
        "source_request": preflight["source_request"],
        "candidate": preflight["candidate"],
        "download_authorization": preflight["download_authorization"],
        "preflight_admission": preflight["preflight_admission"],
        "plan_hash": preflight["plan_hash"],
        "transcript_result": transcript_result,
    }


def _count(root: Path, operation: str) -> int:
    path = root / "provider-state" / f"{operation}-count.txt"
    return int(path.read_text(encoding="ascii")) if path.exists() else 0


def _raw_and_sidecars(root: Path) -> tuple[list[Path], list[Path]]:
    files = [path for path in (root / "companies").rglob("*") if path.is_file()]
    sidecars = [path for path in files if path.name.endswith(".source.json")]
    raw = [path for path in files if not path.name.endswith(".source.json")]
    return raw, sidecars


def _catalog_source_count(root: Path) -> int:
    database = root / ".source_catalog" / "catalog.sqlite3"
    if not database.exists():
        return 0
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT COUNT(*) FROM sources").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        connection.close()


def _assert_zero_persistence(root: Path) -> None:
    raw, sidecars = _raw_and_sidecars(root)
    assert raw == [] and sidecars == []
    staging = root / ".source_catalog" / "staging"
    assert not staging.exists() or list(staging.iterdir()) == []
    assert _catalog_source_count(root) == 0


def _authorized_chain(
    root: Path, *, fixture: str = "html"
) -> tuple[SourceRequest, DownloadCandidate, dict]:
    discovery = _run_provider(root, "discover", _provider_request(), fixture=fixture)
    candidate = _candidate(discovery)
    assert _discovery_preflight(root, candidate)["allowed"] is True
    request = _source_request()
    preflight = _candidate_preflight(root, request, candidate)
    assert preflight["allowed"] is True
    return request, candidate, preflight


def _remove_run(root: Path, tmp_path: Path) -> None:
    resolved = root.resolve(strict=True)
    assert resolved.parent == tmp_path.resolve(strict=True)
    assert root.name.startswith("m2p-") and not root.is_symlink()
    shutil.rmtree(root)
    assert not root.exists()


@pytest.mark.parametrize("fixture", ["html", "txt"])
def test_full_provider_import_reader_selector_and_reuse(tmp_path: Path, fixture: str) -> None:
    root = _wiki_root(tmp_path)
    catalog = None
    try:
        provider_request = _provider_request()
        discovery = _run_provider(root, "discover", provider_request, fixture=fixture)
        assert discovery["schema_version"] == "earnings-transcript-discovery-result/1"
        assert discovery["status"] == "discovered" and discovery["candidate_count"] == 1
        assert "provider_payload_base64" not in json.dumps(discovery)
        candidate = _candidate(discovery)

        discovery_decision = _discovery_preflight(root, candidate)
        assert discovery_decision["allowed"] is True
        request = _source_request()
        preflight = _candidate_preflight(root, request, candidate)
        assert preflight["allowed"] is True

        transcript_result = _run_provider(
            root, "fetch-candidate", _fetch_request(candidate), fixture=fixture
        )
        import_process, imported = _run_cwp(
            root, "import", _import_payload(preflight, transcript_result)
        )
        assert import_process.returncode == 0, import_process.stderr.decode("utf-8", errors="replace")
        serialized_response = import_process.stdout.decode("utf-8")
        assert imported["status"] == "imported"
        assert transcript_result["provider_payload_base64"] not in serialized_response
        assert "Full Conference Call Transcript" not in serialized_response
        assert str(root) not in serialized_response

        config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        resolved = reader.query_local(request)
        assert resolved.status == "found" and len(resolved.matches) == 1
        ref = resolved.matches[0]
        assert ref.source_id == imported["source_id"]
        assert ref.content_sha256 == imported["content_sha256"]
        opened = reader.open_version(ref, purpose="preview")
        expected_raw = base64.b64decode(transcript_result["provider_payload_base64"], validate=True)
        assert opened.data == expected_raw
        assert hashlib.sha256(opened.data).hexdigest() == ref.content_sha256

        material = extract_transcript_material(
            opened.data, mime_type=transcript_result["provider_payload_mime_type"]
        )
        parsed = parse_transcript_text(
            material.text_utf8,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
        )
        package = select_narrative_evidence(
            parsed,
            title=candidate.title,
            existing_kind="investor_call_transcript",
        )
        assert len(package.evidence_spans) >= 2
        verified, failed = verify_transcript_evidence_spans(
            material.text_utf8,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
            evidence_spans=package.evidence_spans,
        )
        assert len(verified) == len(package.evidence_spans) and failed == ()
        selected_text = " ".join(span.raw_text or "" for span in package.evidence_spans)
        assert "expanded overseas" in selected_text
        assert "customer validation continues" in selected_text

        raw, sidecars = _raw_and_sidecars(root)
        assert len(raw) == len(sidecars) == 1
        before = (raw[0], hashlib.sha256(raw[0].read_bytes()).hexdigest(), _count(root, "fetch-candidate"))
        second = reader.query_local(request)
        assert second.status == "found" and second.matches == (ref,)
        assert _count(root, "fetch-candidate") == before[2] == 1
        raw_after, sidecars_after = _raw_and_sidecars(root)
        assert raw_after == raw and sidecars_after == sidecars
        assert hashlib.sha256(raw_after[0].read_bytes()).hexdigest() == before[1]

        selected_bytes = len(json.dumps(
            [span.to_dict() for span in package.evidence_spans],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"))
        receipt = {
            "fixture": fixture,
            "raw_bytes": raw[0].stat().st_size,
            "sidecar_bytes": sidecars[0].stat().st_size,
            "catalog_bytes": (root / ".source_catalog" / "catalog.sqlite3").stat().st_size,
            "selected_bytes": selected_bytes,
            "selected_to_raw_ratio": selected_bytes / raw[0].stat().st_size,
            "fetch_calls": _count(root, "fetch-candidate"),
        }
        assert receipt["raw_bytes"] == len(expected_raw)
        print("M2P_SPACE_RECEIPT " + json.dumps(receipt, sort_keys=True))
    finally:
        if catalog is not None:
            catalog.close()
        _remove_run(root, tmp_path)


def test_discovery_denial_never_calls_candidate_fetch(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    try:
        _write_policy(root, set(ACTIONS) - {"discover_metadata"})
        discovery = _run_provider(root, "discover", _provider_request())
        candidate = _candidate(discovery)
        decision = _discovery_preflight(root, candidate)
        assert decision["allowed"] is False
        assert _count(root, "discover") == 1
        assert _count(root, "fetch-candidate") == 0
        _assert_zero_persistence(root)
    finally:
        _remove_run(root, tmp_path)


def test_candidate_action_denial_never_calls_candidate_fetch(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    try:
        discovery = _run_provider(root, "discover", _provider_request())
        candidate = _candidate(discovery)
        assert _discovery_preflight(root, candidate)["allowed"] is True
        _write_policy(root, set(ACTIONS) - {"derive_text"})
        decision = _candidate_preflight(root, _source_request(), candidate)
        assert decision["allowed"] is False
        assert decision["reason"] == "provider_rights_derive_text_action_not_permitted"
        assert _count(root, "fetch-candidate") == 0
        _assert_zero_persistence(root)
    finally:
        _remove_run(root, tmp_path)


@pytest.mark.parametrize(
    ("fault", "error"),
    [
        ("timeout", subprocess.TimeoutExpired),
        ("bad-json", json.JSONDecodeError),
        ("oversized", ValueError),
    ],
)
def test_provider_transport_failure_leaves_no_partial_import(
    tmp_path: Path, fault: str, error: type[Exception]
) -> None:
    root = _wiki_root(tmp_path)
    try:
        _, candidate, _ = _authorized_chain(root)
        timeout = 0.2 if fault == "timeout" else 5
        with pytest.raises(error):
            _run_provider(
                root,
                "fetch-candidate",
                _fetch_request(candidate),
                fault=fault,
                timeout=timeout,
            )
        assert _count(root, "fetch-candidate") == 1
        _assert_zero_persistence(root)
    finally:
        _remove_run(root, tmp_path)


def test_redirect_drift_is_rejected_without_canonical_residue(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    try:
        _, candidate, preflight = _authorized_chain(root)
        result = _run_provider(
            root, "fetch-candidate", _fetch_request(candidate), fault="redirect"
        )
        process, response = _run_cwp(root, "import", _import_payload(preflight, result))
        assert process.returncode == 2 and response["status"] == "rejected"
        assert result["provider_payload_base64"] not in process.stdout.decode("utf-8")
        _assert_zero_persistence(root)
    finally:
        _remove_run(root, tmp_path)


def test_policy_change_after_fetch_is_rejected_without_canonical_residue(
    tmp_path: Path,
) -> None:
    root = _wiki_root(tmp_path)
    try:
        _, candidate, preflight = _authorized_chain(root)
        result = _run_provider(root, "fetch-candidate", _fetch_request(candidate))
        _write_policy(root, revoked=True)
        process, response = _run_cwp(root, "import", _import_payload(preflight, result))
        assert process.returncode == 2 and response["status"] == "rejected"
        _assert_zero_persistence(root)
    finally:
        _remove_run(root, tmp_path)


def test_reader_fails_closed_after_canonical_byte_drift(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    catalog = None
    try:
        request, candidate, preflight = _authorized_chain(root, fixture="txt")
        result = _run_provider(
            root, "fetch-candidate", _fetch_request(candidate), fixture="txt"
        )
        process, response = _run_cwp(root, "import", _import_payload(preflight, result))
        assert process.returncode == 0 and response["status"] == "imported"
        config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        resolved = reader.query_local(request)
        assert resolved.status == "found" and len(resolved.matches) == 1
        ref = resolved.matches[0]
        assert reader.open_version(ref, purpose="preview").content_sha256 == ref.content_sha256

        raw, _ = _raw_and_sidecars(root)
        assert len(raw) == 1
        changed = bytearray(raw[0].read_bytes())
        changed[0] ^= 1
        raw[0].write_bytes(bytes(changed))
        with pytest.raises(SourceReadError) as failure:
            reader.open_version(ref, purpose="preview")
        assert failure.value.status in {"blocked", "unavailable"}
        assert _count(root, "fetch-candidate") == 1
    finally:
        if catalog is not None:
            catalog.close()
        _remove_run(root, tmp_path)
