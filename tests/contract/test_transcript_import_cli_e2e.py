"""Offline subprocess E2E for the transcript stdin importer."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.authorization import build_download_authorization
from company_wiki.source_catalog.flags import FLAGS
from company_wiki.source_catalog.provider_use_policy import (
    ACTIONS,
    ProviderUsePolicy,
)
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.runtime_policy import build_snapshot
from company_wiki.source_catalog.store import canonical_json
from company_wiki.source_catalog.transcript_fetch_admission import (
    authorize_transcript_fetch,
)
from company_wiki.source_catalog.transcript_material import extract_transcript_material


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_provider_policy(
    path: Path, *, revoked: bool = False, permitted_actions: set[str] | None = None
) -> dict:
    payload = {
        "schema_version": "provider-use-policy/1",
        "policy_id": "transcript-import-cli-e2e",
        "rules": [
            {
                "provider_id": "fixture_provider",
                "origin_host": "fixtures.invalid",
                "path_prefix": "/transcripts",
                "content_class": "earnings_call_transcript",
                "rights_evidence_ref": "synthetic fixture only",
                "rights_evidence_sha256": hashlib.sha256(b"fixture only").hexdigest(),
                "reviewer": "contract-test",
                "reviewed_at": "2026-01-01",
                "valid_from": "2026-01-01",
                "valid_until": "2035-12-31",
                "permitted_actions": sorted(permitted_actions if permitted_actions is not None else ACTIONS),
                "retention_scope": "company_wiki_local",
                "export_scope": "none",
                "revoked": revoked,
            }
        ],
    }
    payload["policy_sha256"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def _fixture_wiki(
    root: Path, *, permitted_actions: set[str] | None = None
) -> tuple[Path, dict, ProviderUsePolicy]:
    (root / "companies").mkdir(parents=True)
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "source_catalog.yaml").write_text(
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
    now = _now()
    runtime_payload = {
        "schema_version": "1.0",
        "flags": {name: False for name in FLAGS},
        "policy_hash": hashlib.sha256(b"runtime policy fixture").hexdigest(),
        "current_epoch": "transcript-import-e2e",
        "active_cohorts": [],
        "updated_at": now,
    }
    catalog_dir = root / ".source_catalog"
    catalog_dir.mkdir()
    (catalog_dir / "runtime_policy.json").write_text(
        json.dumps(build_snapshot(runtime_payload), ensure_ascii=False),
        encoding="utf-8",
    )
    policy_payload = _write_provider_policy(
        config_dir / "provider_use_policy.json", permitted_actions=permitted_actions
    )
    return root, policy_payload, ProviderUsePolicy.from_dict(policy_payload)


def _envelope(root: Path, policy: ProviderUsePolicy) -> tuple[dict, bytes]:
    now = datetime.now(timezone.utc)
    now_text = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    as_of_date = now.date().isoformat()
    request = SourceRequest(
        entity="Acme Inc.",
        market="US",
        security_id="ACME",
        document_kind="investor_call_transcript",
        fiscal_year=2026,
        fiscal_period="Q2",
        as_of_date=as_of_date,
        allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fixture:acme-2026-q2",
        provider="fixture_provider",
        provider_document_id="acme-2026-q2",
        market="US",
        entity=request.entity,
        title="Acme Inc. 2026 Q2 earnings call",
        source_url="https://fixtures.invalid/transcripts/acme-2026-q2.html",
        document_kind="investor_call_transcript",
        filing_date=(now.date() - timedelta(days=1)).isoformat(),
        fiscal_year=2026,
        fiscal_period="Q2",
        language="en",
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "ACME", "exchange": "NASDAQ"},
            separators=(",", ":"),
        ),
    )
    runtime = json.loads((root / ".source_catalog" / "runtime_policy.json").read_text("utf-8"))
    runtime_hash = runtime["snapshot_sha256"]
    plan_hash = hashlib.sha256(b"synthetic exact transcript plan").hexdigest()
    authorization = build_download_authorization(
        request_id=request.request_id,
        gap_plan_hash=plan_hash,
        policy_hash=runtime_hash,
        provider=candidate.provider,
        allowed_accessions=(candidate.provider_document_id,),
        max_items=1,
        max_bytes=4 * 1024 * 1024,
        expires_at=(now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    admission = authorize_transcript_fetch(
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_hash,
        rights_policy=policy,
        now=now_text,
    )
    assert admission.allowed

    body = (
        b"<html><body><main><h1>Acme Inc. 2026 Q2 Earnings Call</h1>"
        b"<p>CEO: Our second business expanded overseas.</p>"
        b"<p>Analyst: When will the new product scale?</p>"
        b"<p>CEO: The launch is planned for next year.</p>"
        b"</main></body></html>"
    )
    material = extract_transcript_material(body, mime_type="text/html")
    transcript_result = {
        "schema_version": "earnings-transcript-result/2",
        "request_id": request.request_id,
        "status": "fetched",
        "provider": candidate.provider,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_period": "2026-Q2",
        "as_of_date": request.as_of_date,
        "title": candidate.title,
        "source_url": candidate.source_url,
        "provider_document_id": candidate.provider_document_id,
        "published_date": candidate.filing_date,
        "extraction_version": "synthetic-html-extractor/1",
        "provider_payload_sha256": hashlib.sha256(body).hexdigest(),
        "canonical_content_sha256": material.text_sha256,
        "content_bytes": material.text_byte_size,
        "provider_payload_encoding": "base64",
        "provider_payload_base64": base64.b64encode(body).decode("ascii"),
        "provider_payload_mime_type": "text/html",
        "effective_url": candidate.source_url,
        "http_status": 200,
        "retrieved_at": now_text,
        "adapter_name": "synthetic-provider-adapter",
        "adapter_version": "1.0.0",
    }
    envelope = {
        "schema_version": "company-wiki-transcript-import-request/1",
        "source_request": request.to_dict(),
        "candidate": candidate.to_dict(),
        "download_authorization": authorization.to_dict(),
        "preflight_admission": {
            "allowed": admission.allowed,
            "reason": admission.reason,
            "rights_policy_sha256": admission.rights_policy_sha256,
            "download_authorization_hash": admission.download_authorization_hash,
            "request_id": admission.request_id,
            "candidate_id": admission.candidate_id,
        },
        "plan_hash": plan_hash,
        "transcript_result": transcript_result,
    }
    return envelope, body


def _run_cli(
    root: Path, envelope: dict, *, operation: str = "import"
) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
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
        env=environment,
        input=json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        capture_output=True,
        timeout=45,
        check=False,
    )


def _remove_fixture_root(root: Path, tmp_path: Path) -> None:
    assert root.resolve(strict=True).parent == tmp_path.resolve(strict=True)
    assert not root.is_symlink()
    shutil.rmtree(root)
    assert not root.exists()


def test_stdin_import_cli_commits_one_original_and_no_transcript_stdout(tmp_path: Path):
    root = tmp_path / "wiki-fixture"
    _, _, policy = _fixture_wiki(root)
    envelope, body = _envelope(root, policy)
    try:
        process = _run_cli(root, envelope)
        assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
        response = json.loads(process.stdout)
        assert response["status"] == "imported"
        assert response["source_id"]
        assert response["provider_payload_sha256"] == hashlib.sha256(body).hexdigest()
        assert response["line_count"] >= 2
        assert body.decode("utf-8") not in process.stdout.decode("utf-8")
        assert envelope["transcript_result"]["provider_payload_base64"] not in process.stdout.decode("utf-8")

        company_root = root / "companies"
        originals = [
            path for path in company_root.rglob("*")
            if path.is_file() and not path.name.endswith(".source.json")
        ]
        sidecars = list(company_root.rglob("*.source.json"))
        assert len(originals) == len(sidecars) == 1
        assert originals[0].read_bytes() == body
        provenance = json.loads(sidecars[0].read_text("utf-8"))
        serialized_provenance = json.dumps(provenance, ensure_ascii=False)
        assert envelope["preflight_admission"]["rights_policy_sha256"] in serialized_provenance
        assert "provider_payload_base64" not in serialized_provenance
        assert "Our second business expanded overseas." not in serialized_provenance
        staging = root / ".source_catalog" / "staging"
        assert list(staging.iterdir()) == []
    finally:
        _remove_fixture_root(root, tmp_path)


def test_stdin_import_cli_rejects_revoked_policy_without_raw_or_staging(tmp_path: Path):
    root = tmp_path / "wiki-fixture"
    _, _, policy = _fixture_wiki(root)
    envelope, _ = _envelope(root, policy)
    try:
        _write_provider_policy(root / "config" / "provider_use_policy.json", revoked=True)
        process = _run_cli(root, envelope)
        assert process.returncode == 2
        response = json.loads(process.stdout)
        assert response["status"] == "rejected"
        assert list((root / "companies").iterdir()) == []
        assert not (root / ".source_catalog" / "staging").exists()
        assert {path.name for path in (root / ".source_catalog").iterdir()} == {
            "runtime_policy.json"
        }
    finally:
        _remove_fixture_root(root, tmp_path)


def test_discovery_preflight_is_read_only_and_hard_denies_motley_fool(tmp_path: Path):
    root = tmp_path / "wiki-fixture"
    _fixture_wiki(root)
    try:
        common = {
            "schema_version": "company-wiki-transcript-discovery-preflight-request/1",
            "request_id": "fixture-request-1",
            "market": "US",
            "ticker": "ACME",
            "exchange": "NASDAQ",
            "fiscal_year": 2026,
            "fiscal_quarter": 2,
            "as_of_date": "2026-09-27",
        }
        allowed_input = {
            **common,
            "provider": "fixture_provider",
            "source_url": "https://fixtures.invalid/transcripts/acme/",
        }
        allowed_process = _run_cli(root, allowed_input, operation="preflight-discovery")
        assert allowed_process.returncode == 0
        allowed = json.loads(allowed_process.stdout)
        assert allowed["status"] == "allowed"
        assert allowed["allowed"] is True
        assert allowed["request_id"] == common["request_id"]

        denied_input = {
            **common,
            "provider": "motley_fool",
            "source_url": "https://www.fool.com/quote/nasdaq/acme/",
        }
        denied_process = _run_cli(root, denied_input, operation="preflight-discovery")
        assert denied_process.returncode == 0
        denied = json.loads(denied_process.stdout)
        assert denied["status"] == "denied"
        assert denied["allowed"] is False
        assert denied["reason"] == "provider_site_automation_blocked"
        assert not (root / ".source_catalog" / "catalog.sqlite3").exists()
        assert list((root / "companies").iterdir()) == []
    finally:
        _remove_fixture_root(root, tmp_path)


def test_candidate_preflight_authorizes_only_fetch_retain_and_derive_actions(tmp_path: Path):
    root = tmp_path / "wiki-fixture"
    _, _, policy = _fixture_wiki(root)
    envelope, body = _envelope(root, policy)
    try:
        preflight_input = {
            "schema_version": "company-wiki-transcript-candidate-preflight-request/1",
            "source_request": envelope["source_request"],
            "candidate": envelope["candidate"],
            "max_bytes": envelope["download_authorization"]["max_bytes"],
            "expires_at": envelope["download_authorization"]["expires_at"],
        }
        preflight_process = _run_cli(root, preflight_input, operation="preflight-candidate")
        assert preflight_process.returncode == 0
        preflight = json.loads(preflight_process.stdout)
        assert preflight["status"] == "allowed"
        assert preflight["allowed"] is True
        assert preflight["candidate"]["candidate_id"] == envelope["candidate"]["candidate_id"]
        assert not (root / ".source_catalog" / "catalog.sqlite3").exists()
        assert list((root / "companies").iterdir()) == []

        import_envelope = {
            "schema_version": "company-wiki-transcript-import-request/1",
            "source_request": preflight["source_request"],
            "candidate": preflight["candidate"],
            "download_authorization": preflight["download_authorization"],
            "preflight_admission": preflight["preflight_admission"],
            "plan_hash": preflight["plan_hash"],
            "transcript_result": envelope["transcript_result"],
        }
        import_process = _run_cli(root, import_envelope)
        assert import_process.returncode == 0, import_process.stderr.decode("utf-8", errors="replace")
        imported = json.loads(import_process.stdout)
        assert imported["status"] == "imported"
        assert imported["provider_payload_sha256"] == hashlib.sha256(body).hexdigest()

        company_root = root / "companies"
        originals = [
            path for path in company_root.rglob("*")
            if path.is_file() and not path.name.endswith(".source.json")
        ]
        assert len(originals) == 1 and originals[0].read_bytes() == body
    finally:
        _remove_fixture_root(root, tmp_path)


def test_candidate_preflight_denies_missing_derive_right_without_creating_catalog(tmp_path: Path):
    root = tmp_path / "wiki-fixture"
    _, _, policy = _fixture_wiki(root)
    envelope, _ = _envelope(root, policy)
    _write_provider_policy(
        root / "config" / "provider_use_policy.json",
        permitted_actions=set(ACTIONS) - {"derive_text"},
    )
    try:
        preflight_input = {
            "schema_version": "company-wiki-transcript-candidate-preflight-request/1",
            "source_request": envelope["source_request"],
            "candidate": envelope["candidate"],
            "max_bytes": envelope["download_authorization"]["max_bytes"],
            "expires_at": envelope["download_authorization"]["expires_at"],
        }
        process = _run_cli(root, preflight_input, operation="preflight-candidate")
        assert process.returncode == 0
        response = json.loads(process.stdout)
        assert response["status"] == "denied"
        assert response["allowed"] is False
        assert response["reason"] == "provider_rights_derive_text_action_not_permitted"
        assert not (root / ".source_catalog" / "catalog.sqlite3").exists()
        assert list((root / "companies").iterdir()) == []
    finally:
        _remove_fixture_root(root, tmp_path)
