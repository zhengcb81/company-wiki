"""Subprocess E2E for transcript import without human or policy receipts."""

from __future__ import annotations

import base64
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.transcript_material import extract_transcript_material


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, object], bytes]:
    root = tmp_path / "company-wiki-fixture"
    (root / "companies").mkdir(parents=True)
    config = root / "config"
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
    now = datetime.now(timezone.utc).replace(microsecond=0)
    as_of = now.date().isoformat()
    published = (now.date() - timedelta(days=1)).isoformat()
    request = SourceRequest(
        entity="Acme Inc.",
        market="US",
        security_id="ACME",
        document_kind="investor_call_transcript",
        fiscal_year=2026,
        fiscal_period="Q2",
        language="en",
        provider="fixture_provider",
        provider_document_id="acme-2026-q2",
        as_of_date=as_of,
        allow_download=True,
    )
    url = "https://fixtures.invalid/transcripts/acme-2026-q2.html"
    candidate = DownloadCandidate(
        candidate_id="fixture:acme-2026-q2",
        provider="fixture_provider",
        provider_document_id="acme-2026-q2",
        market="US",
        entity=request.entity,
        title="Acme Inc. 2026 Q2 earnings call",
        source_url=url,
        document_kind="investor_call_transcript",
        filing_date=published,
        fiscal_year=2026,
        fiscal_period="Q2",
        language="en",
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "ACME", "exchange": "NASDAQ"},
            separators=(",", ":"),
        ),
    )
    body = (
        b"<html><body><main><h1>Acme Inc. 2026 Q2 Earnings Call</h1>"
        b"<p>CEO: Our second business expanded overseas.</p>"
        b"<p>Analyst: When will the new product scale?</p>"
        b"<p>CEO: The launch is planned for next year.</p>"
        b"</main></body></html>"
    )
    material = extract_transcript_material(body, mime_type="text/html")
    result = {
        "schema_version": "earnings-transcript-result/2",
        "request_id": request.request_id,
        "status": "fetched",
        "provider": candidate.provider,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_period": "2026-Q2",
        "as_of_date": as_of,
        "title": candidate.title,
        "source_url": url,
        "provider_document_id": candidate.provider_document_id,
        "published_date": published,
        "extraction_version": "fixture-extractor-v1",
        "provider_payload_sha256": _sha(body),
        "canonical_content_sha256": material.text_sha256,
        "content_bytes": material.text_byte_size,
        "provider_payload_encoding": "base64",
        "provider_payload_base64": base64.b64encode(body).decode("ascii"),
        "provider_payload_mime_type": "text/html",
        "effective_url": url,
        "http_status": 200,
        "retrieved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_name": "fixture-provider",
        "adapter_version": "1.0.0",
    }
    envelope = {
        "schema_version": "company-wiki-transcript-import-request/2",
        "source_request": request.to_dict(),
        "candidate": asdict(candidate),
        "transcript_result": result,
    }
    return root, envelope, body


def _run(root: Path, envelope: dict[str, object]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.transcript_import_cli",
            "--wiki-root",
            str(root),
        ],
        input=json.dumps(envelope, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=environment,
        check=False,
    )


def _remove_fixture(root: Path, parent: Path) -> None:
    if not root.exists():
        return
    resolved = root.resolve(strict=True)
    if resolved.parent != parent.resolve(strict=True):
        raise AssertionError("refusing to remove a fixture outside tmp_path")
    paths = (root, *root.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise AssertionError("refusing to remove a fixture containing symlinks")
    shutil.rmtree(root)


def test_cli_imports_original_without_policy_files_and_reuses_it(tmp_path: Path) -> None:
    root, envelope, body = _fixture(tmp_path)
    try:
        first = _run(root, envelope)
        assert first.returncode == 0, first.stderr
        response = json.loads(first.stdout)
        assert response["status"] == "imported"
        assert response["canonical_status"] == "imported_new"
        assert response["provider_payload_sha256"] == _sha(body)

        second = _run(root, envelope)
        assert second.returncode == 0, second.stderr
        replay = json.loads(second.stdout)
        assert replay["canonical_status"] == "deduplicated_after_download"
        assert replay["source_id"] == response["source_id"]

        originals = list((root / "companies").rglob("*.html"))
        assert len(originals) == 1
        assert originals[0].read_bytes() == body
        provenance = json.loads(
            originals[0].with_name(originals[0].name + ".source.json").read_text(
                encoding="utf-8"
            )
        )
        audit = provenance["provenance_extensions"]["transcript_acquisition"]
        assert audit["schema_version"] == "transcript-acquisition-audit/2"
        assert audit["provider_payload_sha256"] == _sha(body)
        assert "rights_policy_sha256" not in audit
        assert "download_authorization_hash" not in audit
        assert not (root / "config" / "provider_use_policy.json").exists()
        staging = root / ".source_catalog" / "staging"
        assert not staging.exists() or list(staging.iterdir()) == []
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_cli_rejects_wrong_company_period_or_hash_before_writing(tmp_path: Path) -> None:
    root, envelope, _ = _fixture(tmp_path)
    try:
        invalid = json.loads(json.dumps(envelope))
        invalid["transcript_result"]["ticker"] = "OTHER"

        process = _run(root, invalid)

        assert process.returncode != 0
        assert json.loads(process.stdout)["status"] == "rejected"
        assert not list((root / "companies").rglob("*.html"))
        assert not (root / ".source_catalog" / "staging").exists()
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()



def _fmp_fixture(tmp_path: Path) -> tuple[Path, dict[str, object], bytes]:
    golden = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "transcript_fmp" / "fmp_v2.fetched.json")
        .read_text(encoding="utf-8")
    )
    root = tmp_path / "company-wiki-fmp"
    (root / "companies").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "config" / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\ncatalog_dir: .source_catalog\nroots:\n"
        "  - root_id: company_raw\n    path: companies\n    kind: company_raw\n"
        "    priority: 10\n    adapter_id: company_raw_v1\n    read_only: false\n",
        encoding="utf-8",
    )
    request = SourceRequest(
        entity="Microsoft Corporation", market="US", security_id="MSFT",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q3", language="en", provider="fmp",
        provider_document_id=golden["provider_document_id"],
        as_of_date="2026-09-30", allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fmp:msft:2026-q3", provider="fmp",
        provider_document_id=golden["provider_document_id"], market="US",
        entity=request.entity, title=golden["title"], source_url=golden["source_url"],
        document_kind="investor_call_transcript", filing_date=None,
        fiscal_year=2026, fiscal_period="Q3", language="en",
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "MSFT", "exchange": "nasdaq"}
        ),
    )
    golden["request_id"] = request.request_id
    envelope = {
        "schema_version": "company-wiki-transcript-import-request/2",
        "source_request": request.to_dict(),
        "candidate": asdict(candidate),
        "transcript_result": golden,
    }
    original = base64.b64decode(golden["provider_payload_base64"], validate=True)
    return root, envelope, original


def test_fmp_unknown_publication_cli_stores_original_but_excludes_historical_cutoff(
    tmp_path: Path,
) -> None:
    from company_wiki.source_catalog import SourceCatalog, load_catalog_config
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    from company_wiki.source_catalog.transcript_material import extract_transcript_material

    root, envelope, original = _fmp_fixture(tmp_path)
    catalog = None
    try:
        first = _run(root, envelope)
        assert first.returncode == 0, first.stderr
        imported = json.loads(first.stdout)
        assert imported["status"] == "imported"
        assert imported["canonical_status"] == "imported_new"
        assert imported["provider_payload_sha256"] == _sha(original)
        files = [p for p in (root / "companies").rglob("*.json") if not p.name.endswith(".source.json")]
        assert len(files) == 1 and files[0].read_bytes() == original
        assert files[0].name.startswith("unknown-date_fmp_")
        sidecar = json.loads(files[0].with_name(files[0].name + ".source.json").read_text(encoding="utf-8"))
        audit = sidecar["provenance_extensions"]["transcript_acquisition"]
        assert audit["call_date"] == "2026-07-22"
        assert audit["publication_date"] is None
        assert audit["as_of_cutoff_verified"] is False
        assert audit["provider_canonical_content_sha256"] == envelope["transcript_result"]["canonical_content_sha256"]

        config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        docs = catalog.reader.query(text="MSFT 2026 Q3", document_kind="investor_call_transcript")
        assert len(docs) == 1 and docs[0]["published_date"] is None
        ref = reader.query_ref(docs[0]["document_id"], imported["source_id"], _sha(original))
        opened = reader.open_version(ref, purpose="preview")
        assert opened.data == original
        material = extract_transcript_material(opened.data, mime_type="application/json")
        material.verify(original)
        assert material.lines
        request = SourceRequest(**envelope["source_request"])
        assert reader.query_local(request).status == "not_found"

        second = _run(root, envelope)
        assert second.returncode == 0, second.stderr
        replay = json.loads(second.stdout)
        assert replay["canonical_status"] == "deduplicated_after_download"
        assert replay["source_id"] == imported["source_id"]
        assert len([p for p in (root / "companies").rglob("*.json") if not p.name.endswith(".source.json")]) == 1
        staging = root / ".source_catalog" / "staging"
        assert not staging.exists() or list(staging.iterdir()) == []
    finally:
        if catalog is not None:
            catalog.close()
        _remove_fixture(root, tmp_path)
    assert not root.exists()


@pytest.mark.parametrize("bad_field", ["provider_payload_sha256", "canonical_content_sha256"])
def test_fmp_cli_rejects_corrupt_original_evidence_without_files(
    tmp_path: Path, bad_field: str,
) -> None:
    root, envelope, _ = _fmp_fixture(tmp_path)
    try:
        envelope["transcript_result"][bad_field] = "0" * 64
        process = _run(root, envelope)
        assert process.returncode != 0
        assert json.loads(process.stdout)["status"] == "rejected"
        assert not list((root / "companies").rglob("*.json"))
        staging = root / ".source_catalog" / "staging"
        assert not staging.exists() or list(staging.iterdir()) == []
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()
