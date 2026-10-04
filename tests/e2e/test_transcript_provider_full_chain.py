"""Provider -> canonical raw -> reader -> selected evidence, with no review gates."""

from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest

from company_wiki.source_catalog import SourceCatalog, load_catalog_config
from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text,
    select_narrative_evidence,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_catalog.transcript_material import extract_transcript_material


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FAKE_TOOL = Path(__file__).parent / "fixtures" / "fake_earnings_transcript_tool.py"
PROVIDER_STDOUT_LIMIT = 256 * 1024


def _wiki_root(tmp_path: Path) -> Path:
    # Keep the final canonical path below Win32 MAX_PATH.  The source name
    # already carries date/provider/hash, so a short unique test-root is enough.
    root = tmp_path / f"e2e-{uuid.uuid4().hex[:12]}"
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
    return root


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _run_provider(
    root: Path,
    operation: str,
    request: dict,
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
    request_bytes = json.dumps(
        request, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
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


def _provider_request(request: SourceRequest) -> dict:
    return {
        "schema_version": "earnings-transcript-request/1",
        "request_id": request.request_id,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "as_of_date": request.as_of_date,
        "provider": "fixture_provider",
        "timeout_seconds": 5,
        "max_body_bytes": 1024 * 1024,
    }


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


def _fetch_request(request: SourceRequest, candidate: DownloadCandidate) -> dict:
    return {
        "schema_version": "earnings-transcript-candidate-fetch-request/1",
        "request_id": request.request_id,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "as_of_date": request.as_of_date,
        "provider": candidate.provider,
        "timeout_seconds": 5,
        "max_body_bytes": 1024 * 1024,
        "candidate": {
            "provider_document_id": candidate.provider_document_id,
            "source_url": candidate.source_url,
            "published_date": candidate.filing_date,
        },
    }


def _import_payload(
    request: SourceRequest, candidate: DownloadCandidate, transcript_result: dict
) -> dict:
    return {
        "schema_version": "company-wiki-transcript-import-request/2",
        "source_request": request.to_dict(),
        "candidate": asdict(candidate),
        "transcript_result": transcript_result,
    }


def _run_cwp(root: Path, payload: dict) -> tuple[subprocess.CompletedProcess, dict]:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.transcript_import_cli",
            "--wiki-root",
            str(root),
        ],
        cwd=REPO_ROOT,
        env=_environment(),
        input=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        capture_output=True,
        timeout=45,
        check=False,
    )
    return process, json.loads(process.stdout)


def _count(root: Path, operation: str) -> int:
    path = root / "provider-state" / f"{operation}-count.txt"
    return int(path.read_text(encoding="ascii")) if path.exists() else 0


def _raw_and_sidecars(root: Path) -> tuple[list[Path], list[Path]]:
    files = [path for path in (root / "companies").rglob("*") if path.is_file()]
    sidecars = [path for path in files if path.name.endswith(".source.json")]
    raw = [path for path in files if not path.name.endswith(".source.json")]
    return raw, sidecars


def _assert_no_import(root: Path) -> None:
    raw, sidecars = _raw_and_sidecars(root)
    assert raw == [] and sidecars == []
    staging = root / ".source_catalog" / "staging"
    assert not staging.exists() or list(staging.iterdir()) == []


def _remove_run(root: Path, tmp_path: Path) -> None:
    if not root.exists():
        return
    resolved = root.resolve(strict=True)
    assert resolved.parent == tmp_path.resolve(strict=True)
    assert root.name.startswith("e2e-") and not root.is_symlink()
    members = (root, *root.rglob("*"))
    assert not any(path.is_symlink() for path in members)
    shutil.rmtree(root)
    assert not root.exists()


@pytest.mark.parametrize("fixture", ["html", "txt"])
def test_provider_import_reader_selector_and_idempotent_retry(
    tmp_path: Path, fixture: str
) -> None:
    root = _wiki_root(tmp_path)
    catalog = None
    try:
        request = _source_request()
        provider_request = _provider_request(request)
        discovery = _run_provider(root, "discover", provider_request, fixture=fixture)
        assert discovery["status"] == "discovered"
        assert discovery["candidate_count"] == 1
        candidate = _candidate(discovery)
        fetch_request = _fetch_request(request, candidate)
        transcript_result = _run_provider(
            root, "fetch-candidate", fetch_request, fixture=fixture
        )
        envelope = _import_payload(request, candidate, transcript_result)

        process, imported = _run_cwp(root, envelope)

        assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
        assert imported["status"] == "imported"
        assert transcript_result["provider_payload_base64"] not in process.stdout.decode("utf-8")
        assert str(root) not in process.stdout.decode("utf-8")
        assert not (root / "config" / "provider_use_policy.json").exists()
        assert not (root / ".source_catalog" / "runtime_policy.json").exists()

        catalog = SourceCatalog(
            load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
        )
        reader = SourceVersionReader(catalog)
        resolved = reader.query_local(request)
        assert resolved.status == "found" and len(resolved.matches) == 1
        ref = resolved.matches[0]
        assert ref.source_id == imported["source_id"]
        opened = reader.open_version(ref, purpose="preview")
        original = base64.b64decode(transcript_result["provider_payload_base64"], validate=True)
        assert opened.data == original
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
            parsed, title=candidate.title, existing_kind="investor_call_transcript"
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
        digest_before = hashlib.sha256(raw[0].read_bytes()).hexdigest()
        replay_process, replay = _run_cwp(root, envelope)
        assert replay_process.returncode == 0, replay_process.stderr.decode("utf-8", errors="replace")
        assert replay["canonical_status"] == "deduplicated_after_download"
        raw_after, sidecars_after = _raw_and_sidecars(root)
        assert raw_after == raw and sidecars_after == sidecars
        assert hashlib.sha256(raw_after[0].read_bytes()).hexdigest() == digest_before
        assert _count(root, "fetch-candidate") == 1
    finally:
        if catalog is not None:
            catalog.close()
        _remove_run(root, tmp_path)


@pytest.mark.parametrize("fault", ["timeout", "bad-json", "oversized", "redirect"])
def test_provider_failure_or_source_mismatch_leaves_no_raw_file(
    tmp_path: Path, fault: str
) -> None:
    root = _wiki_root(tmp_path)
    try:
        request = _source_request()
        discovery = _run_provider(root, "discover", _provider_request(request))
        candidate = _candidate(discovery)
        timeout = 0.2 if fault == "timeout" else 5
        if fault in {"timeout", "bad-json", "oversized"}:
            expected_error = {
                "timeout": subprocess.TimeoutExpired,
                "bad-json": json.JSONDecodeError,
                "oversized": ValueError,
            }[fault]
            with pytest.raises(expected_error):
                _run_provider(
                    root,
                    "fetch-candidate",
                    _fetch_request(request, candidate),
                    fault=fault,
                    timeout=timeout,
                )
        else:
            transcript_result = _run_provider(
                root, "fetch-candidate", _fetch_request(request, candidate), fault=fault
            )
            process, response = _run_cwp(
                root, _import_payload(request, candidate, transcript_result)
            )
            assert process.returncode == 2
            assert response["status"] == "rejected"
        count = _count(root, "fetch-candidate")
        # A timeout may terminate Python before the provider body runs. Both
        # paths must leave no import; non-timeout failures reach the body once.
        if fault == "timeout":
            assert count in {0, 1}
        else:
            assert count == 1
        _assert_no_import(root)
    finally:
        _remove_run(root, tmp_path)


def test_reader_still_detects_raw_byte_drift_automatically(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    catalog = None
    try:
        request = _source_request()
        discovery = _run_provider(root, "discover", _provider_request(request), fixture="txt")
        candidate = _candidate(discovery)
        result = _run_provider(
            root, "fetch-candidate", _fetch_request(request, candidate), fixture="txt"
        )
        process, imported = _run_cwp(root, _import_payload(request, candidate, result))
        assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
        catalog = SourceCatalog(
            load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
        )
        reader = SourceVersionReader(catalog)
        resolution = reader.query_local(request)
        assert resolution.status == "found" and len(resolution.matches) == 1
        ref = resolution.matches[0]
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
