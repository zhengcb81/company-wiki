"""Original transcript bytes remain canonical; extracted text is replayable."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from company_wiki.source_catalog import (
    CanonicalImportStatus,
    CanonicalSourceWriter,
    CatalogConfig,
    DownloadCandidate,
    RootSpec,
    SourceCatalog,
    SourceRequest,
)
from company_wiki.source_catalog.transcript_import import (
    TranscriptImportError,
    import_transcript_tool_result,
)
from company_wiki.source_catalog.transcript_material import (
    extract_transcript_material,
    load_transcript_material,
)
from company_wiki.source_catalog.resolver import SourceResolver


def _fixture(root: Path):
    companies = root / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=root,
            catalog_dir=root / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", companies, "company_raw", priority=10,
                    adapter_id="company_raw_v1",
                ),
            ),
        )
    )
    request = SourceRequest(
        entity="Acme Inc.", market="US", security_id="ACME",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q2", language="en", as_of_date="2026-09-27",
        provider="fixture_provider", provider_document_id="acme-2026-q2",
        allow_download=True,
    )
    body = (
        b"<html><body><p>Acme 2026 Q2 earnings call</p>"
        b"<p>CEO: Overseas growth is a priority.</p>"
        b"<p>Analyst: When will the new business scale?</p>"
        b"<p>CEO: We have a plan, not a result yet.</p></body></html>"
    )
    candidate = DownloadCandidate(
        candidate_id="fixture-provider-doc-1", provider="fixture_provider",
        provider_document_id="acme-2026-q2", market="US", entity=request.entity,
        title="Acme Inc. 2026 Q2 Earnings Call",
        source_url="https://fixtures.invalid/transcripts/2026/q2.html",
        document_kind="investor_call_transcript", filing_date="2026-09-20",
        fiscal_year=2026, fiscal_period="Q2", language="en",
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "ACME", "exchange": "NASDAQ"}
        ),
    )
    return catalog, request, candidate, body


def _result(request, candidate, body: bytes, **overrides) -> bytes:
    material = extract_transcript_material(body, mime_type="text/html")
    payload = {
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
        "retrieved_at": "2026-09-27T12:00:00Z",
        "adapter_name": "synthetic-transcript-adapter",
        "adapter_version": "1.0.0",
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_import_preserves_original_and_replays_text_without_permission_receipts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    catalog, request, candidate, body = _fixture(root)
    try:
        catalog.scan()
        writer = CanonicalSourceWriter(catalog)
        imported = import_transcript_tool_result(
            _result(request, candidate, body),
            request=request,
            candidate=candidate,
            writer=writer,
            now="2026-09-27T12:01:00Z",
        )
        assert imported.canonical_import.status is CanonicalImportStatus.IMPORTED_NEW
        original = Path(imported.canonical_import.canonical_path)
        assert original.suffix == ".html"
        assert original.read_bytes() == body
        assert imported.material.original_sha256 == hashlib.sha256(body).hexdigest()
        replay = load_transcript_material(
            imported.material.lineage_dict(),
            original=original.read_bytes(),
            text_utf8=imported.material.text_utf8.encode("utf-8"),
            expected_mime_type="text/html",
        )
        assert replay == imported.material
        assert "CEO: Overseas growth is a priority." in replay.text_utf8
        assert imported.provider_payload_sha256 == hashlib.sha256(body).hexdigest()

        provenance = json.loads(
            Path(imported.canonical_import.provenance_path).read_text(encoding="utf-8")
        )
        audit = provenance["provenance_extensions"]["transcript_acquisition"]
        assert audit["schema_version"] == "transcript-acquisition-audit/2"
        assert "rights_policy_sha256" not in audit
        assert "download_authorization_hash" not in audit
        assert list(writer.staging_root.iterdir()) == []
    finally:
        catalog.close()
        _remove_fixture(root, tmp_path)


def test_import_rejects_wrong_identity_and_hash_and_reuses_exact_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    catalog, request, candidate, body = _fixture(root)
    try:
        catalog.scan()
        writer = CanonicalSourceWriter(catalog)
        invalid = (
            _result(request, candidate, body, ticker="OTHER"),
            _result(request, candidate, body, provider_payload_sha256="0" * 64),
            _result(request, candidate, body, fiscal_period="2026-Q1"),
        )
        for result in invalid:
            with pytest.raises(TranscriptImportError):
                import_transcript_tool_result(
                    result, request=request, candidate=candidate, writer=writer,
                    now="2026-09-27T12:01:00Z",
                )
        assert not list((root / "companies").rglob("*.html"))
        assert not writer.staging_root.exists()

        raw = _result(request, candidate, body)
        first = import_transcript_tool_result(
            raw, request=request, candidate=candidate, writer=writer,
            now="2026-09-27T12:01:00Z",
        )
        second = import_transcript_tool_result(
            raw, request=request, candidate=candidate, writer=writer,
            now="2026-09-27T12:01:00Z",
        )
        assert second.canonical_import.status is CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD
        assert second.canonical_import.source_id == first.canonical_import.source_id
        assert len(list((root / "companies").rglob("*.html"))) == 1
        assert SourceResolver(catalog).resolve(request).matches[0].source_id == first.canonical_import.source_id
    finally:
        catalog.close()
        _remove_fixture(root, tmp_path)


def _remove_fixture(root: Path, parent: Path) -> None:
    if not root.exists():
        return
    if root.is_symlink() or root.resolve(strict=True).parent != parent.resolve(strict=True):
        raise AssertionError("refusing to remove fixture outside tmp_path")
    members = (root, *root.rglob("*"))
    if any(path.is_symlink() for path in members):
        raise AssertionError("refusing to remove fixture containing symlinks")
    shutil.rmtree(root)
    assert not root.exists()
