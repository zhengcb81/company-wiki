"""Original HTML is canonical source; English TXT is derived lineage only."""

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
    DownloadReceipt,
    RootSpec,
    SourceCatalog,
    SourceRequest,
)
from company_wiki.source_catalog.authorization import build_download_authorization
from company_wiki.source_catalog.provider_use_policy import (
    ACTIONS,
    ProviderUsePolicy,
    authorize_transcript_fetch,
    validate_transcript_fetch_result,
)
from company_wiki.source_catalog.transcript_import import (
    TranscriptImportError,
    import_transcript_tool_result,
)
from company_wiki.source_catalog.transcript_material import (
    extract_transcript_material,
    load_transcript_material,
)
from company_wiki.source_catalog.store import canonical_json
from company_wiki.source_catalog.resolver import SourceResolver


class _FakeTranscriptProvider:
    name = "fixture_transcript_provider"
    version = "1.0.0"

    def __init__(self, body: bytes, *, final_url: str):
        self.body = body
        self.final_url = final_url
        self.fetch_calls = 0

    def discover(self, request: SourceRequest):
        return ()

    def fetch(self, candidate: DownloadCandidate, staging_dir: Path) -> DownloadReceipt:
        self.fetch_calls += 1
        staging_dir.mkdir(parents=True, exist_ok=True)
        staged = staging_dir / f"fake-{self.fetch_calls}.html"
        staged.write_bytes(self.body)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(staged),
            content_sha256=hashlib.sha256(self.body).hexdigest(),
            byte_size=len(self.body),
            mime_type="text/html",
            retrieved_at="2026-09-27T12:00:00Z",
            http_status=200,
            adapter_name=self.name,
            adapter_version=self.version,
        )


def _fixture_rights_policy() -> ProviderUsePolicy:
    payload = {
        "schema_version": "provider-use-policy/1",
        "policy_id": "offline-e2e-fixture-v1",
        "rules": [
            {
                "provider_id": "fixture_provider",
                "origin_host": "fixtures.invalid",
                "path_prefix": "/transcripts",
                "content_class": "earnings_call_transcript",
                "rights_evidence_ref": "synthetic test policy only",
                "rights_evidence_sha256": hashlib.sha256(b"test only").hexdigest(),
                "reviewer": "contract-test",
                "reviewed_at": "2026-09-01",
                "valid_from": "2026-09-01",
                "valid_until": "2026-09-30",
                "permitted_actions": sorted(ACTIONS),
                "retention_scope": "company_wiki_local",
                "export_scope": "none",
                "revoked": False,
            }
        ],
    }
    payload["policy_sha256"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return ProviderUsePolicy.from_dict(payload)


def _transcript_result_v2(request, candidate, body: bytes, **overrides) -> bytes:
    result = {
        "schema_version": "earnings-transcript-result/2",
        "request_id": request.request_id,
        "status": "fetched",
        "provider": candidate.provider,
        "ticker": "ACME",
        "exchange": "NASDAQ",
        "fiscal_period": "2026-Q2",
        "as_of_date": request.as_of_date,
        "title": "Acme Inc. 2026 Q2 Earnings Call",
        "source_url": candidate.source_url,
        "provider_document_id": candidate.provider_document_id,
        "published_date": candidate.filing_date,
        "extraction_version": "synthetic-html-extractor/1",
        "provider_payload_sha256": hashlib.sha256(body).hexdigest(),
        "canonical_content_sha256": hashlib.sha256(b"fixture extracted text").hexdigest(),
        "content_bytes": len(b"fixture extracted text"),
        "provider_payload_encoding": "base64",
        "provider_payload_base64": base64.b64encode(body).decode("ascii"),
        "provider_payload_mime_type": "text/html",
        "effective_url": candidate.source_url,
        "http_status": 200,
        "retrieved_at": "2026-09-27T12:00:00Z",
        "adapter_name": "synthetic-transcript-adapter",
        "adapter_version": "1.0.0",
    }
    result.update(overrides)
    return json.dumps(result, separators=(",", ":")).encode("utf-8")


def test_synthetic_original_html_writer_and_derived_text_lineage(tmp_path: Path):
    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", companies, "company_raw", priority=10,
                    adapter_id="company_raw_v1",
                ),
            ),
        )
    )
    try:
        catalog.scan()
        writer = CanonicalSourceWriter(catalog)
        source = (
            "<html><body><h1>Earnings Call Transcript</h1>"
            "<p>CEO: Our second business expanded overseas.</p>"
            "<p>Analyst: When does production begin?</p>"
            "<p>CEO: Next year is our plan.</p></body></html>"
        ).encode("utf-8")
        staged = writer.staging_root / "synthetic-original.html"
        staged.parent.mkdir(parents=True)
        staged.write_bytes(source)
        request = SourceRequest(
            entity="Acme Inc.", market="US", security_id="ACME",
            document_kind="investor_call_transcript", fiscal_year=2026,
            fiscal_period="Q2", as_of_date="2026-09-27", allow_download=True,
        )
        candidate = DownloadCandidate(
            candidate_id="fixture:doc-1", provider="fixture_provider",
            provider_document_id="doc-1", market="US", entity=request.entity,
            title="Acme earnings call transcript from synthetic issuer exhibit",
            source_url="https://fixtures.invalid/transcripts/doc-1.html",
            document_kind="investor_call_transcript", filing_date="2026-09-20",
            fiscal_year=2026, fiscal_period="Q2", remote_size=len(source),
        )
        receipt = DownloadReceipt(
            candidate_id=candidate.candidate_id, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url, staged_path=str(staged),
            content_sha256=hashlib.sha256(source).hexdigest(), byte_size=len(source),
            mime_type="text/html", retrieved_at="2026-09-27T12:00:00Z",
            http_status=200, adapter_name="synthetic-fixture", adapter_version="1.0.0",
        )
        imported = writer.import_staged(request, candidate, receipt)
        assert imported.status is CanonicalImportStatus.IMPORTED_NEW
        original_path = Path(imported.canonical_path)
        assert original_path.suffix == ".html"
        assert original_path.parent.parts[-3:] == ("raw", "investor_relations", "transcripts")
        assert original_path.read_bytes() == source
        assert json.loads(Path(imported.provenance_path).read_text(encoding="utf-8"))[
            "content_sha256"
        ] == receipt.content_sha256
        assert not staged.exists()

        material = extract_transcript_material(original_path.read_bytes(), mime_type="text/html")
        assert material.original_source_id == imported.source_id
        assert material.text_utf8.splitlines()[1].startswith("CEO:")
        replay = load_transcript_material(
            material.lineage_dict(),
            original=original_path.read_bytes(),
            text_utf8=material.text_utf8.encode("utf-8"),
            expected_mime_type="text/html",
        )
        assert replay == material
        assert material.original_sha256 != material.text_sha256
    finally:
        catalog.close()


def test_v2_tool_result_is_bound_revalidated_and_imported(tmp_path: Path):
    run_root = tmp_path / "e"
    assert not run_root.exists()
    run_root.mkdir()
    project = run_root / "p"
    companies = project / "c"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", companies, "company_raw", priority=10,
                    adapter_id="company_raw_v1",
                ),
            ),
        )
    )
    body = (
        b"<html><body><main><h1>Acme Inc. 2026 Q2 Earnings Call</h1>"
        b"<p>CEO: Overseas growth is a priority.</p>"
        b"<p>Analyst: When will the new business scale?</p>"
        b"<p>CEO: We have a plan, not a result yet.</p></main></body></html>"
    )
    source_url = "https://fixtures.invalid/transcripts/2026/q2.html"
    request = SourceRequest(
        entity="Acme Inc.", market="US", security_id="ACME",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q2", as_of_date="2026-09-27", provider="fixture_provider",
        provider_document_id="acme-2026-q2", allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fixture-provider-doc-1", provider="fixture_provider",
        provider_document_id="acme-2026-q2", market="US", entity=request.entity,
        title="Acme Inc. 2026 Q2 Earnings Call", source_url=source_url,
        document_kind="investor_call_transcript", filing_date="2026-09-20",
        fiscal_year=2026, fiscal_period="Q2", remote_size=None,
        adapter_payload_json=json.dumps(
            {"market": "US", "security_id": "ACME", "exchange": "NASDAQ"}
        ),
    )
    plan_hash = "a" * 64
    runtime_policy_hash = "b" * 64
    authorization = build_download_authorization(
        request_id=request.request_id,
        gap_plan_hash=plan_hash,
        policy_hash=runtime_policy_hash,
        provider=candidate.provider,
        allowed_accessions=(candidate.provider_document_id,),
        max_items=1,
        max_bytes=64 * 1024,
        expires_at="2026-09-27T23:00:00Z",
    )
    rights_policy = _fixture_rights_policy()
    now = "2026-09-27T12:00:00Z"
    try:
        catalog.scan()
        writer = CanonicalSourceWriter(catalog)
        admission = authorize_transcript_fetch(
            request=request, candidate=candidate, authorization=authorization,
            plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
            rights_policy=rights_policy, now=now,
        )
        assert admission.allowed

        invalid_results = [
            _transcript_result_v2(
                request, candidate, body, provider_payload_sha256="0" * 64
            ),
            _transcript_result_v2(request, candidate, body, request_id="other-request"),
            _transcript_result_v2(
                request, candidate, body,
                effective_url="https://other.invalid/transcripts/2026/q2.html",
            ),
            _transcript_result_v2(
                request, candidate, body, provider_document_id="other-document"
            ),
            _transcript_result_v2(request, candidate, body, exchange="NYSE"),
            _transcript_result_v2(request, candidate, body, fiscal_period="2026-Q1"),
        ]
        duplicate_key = _transcript_result_v2(request, candidate, body).replace(
            b'"status":"fetched"', b'"status":"failed","status":"fetched"', 1
        )
        invalid_results.append(duplicate_key)
        for invalid_result in invalid_results:
            with pytest.raises(TranscriptImportError):
                import_transcript_tool_result(
                    invalid_result, request=request, candidate=candidate,
                    authorization=authorization, preflight_admission=admission,
                    plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
                    current_rights_policy=rights_policy, writer=writer, now=now,
                )
        assert not any(companies.rglob("*.html"))
        assert not writer.staging_root.exists()

        denied_request = SourceRequest(
            entity=request.entity, market=request.market, security_id=request.security_id,
            document_kind=request.document_kind, fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period, as_of_date=request.as_of_date,
            provider=request.provider, provider_document_id=request.provider_document_id,
            allow_download=False,
        )
        denied_admission = authorize_transcript_fetch(
            request=denied_request, candidate=candidate, authorization=authorization,
            plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
            rights_policy=rights_policy, now=now,
        )
        with pytest.raises(TranscriptImportError, match="pre-fetch authorization"):
            import_transcript_tool_result(
                _transcript_result_v2(request, candidate, body),
                request=denied_request, candidate=candidate,
                authorization=authorization, preflight_admission=denied_admission,
                plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
                current_rights_policy=rights_policy, writer=writer, now=now,
            )
        assert not writer.staging_root.exists()

        imported = import_transcript_tool_result(
            _transcript_result_v2(request, candidate, body),
            request=request, candidate=candidate, authorization=authorization,
            preflight_admission=admission, plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            current_rights_policy=rights_policy, writer=writer, now=now,
        )
        assert imported.canonical_import.status is CanonicalImportStatus.IMPORTED_NEW
        original_path = Path(imported.canonical_import.canonical_path)
        assert original_path.read_bytes() == body
        assert imported.material.original_source_id == imported.canonical_import.source_id
        assert imported.provider_payload_sha256 == hashlib.sha256(body).hexdigest()
        assert imported.rights_policy_sha256 == rights_policy.policy_sha256
        assert imported.download_authorization_hash == authorization.receipt_hash
        assert "CEO: Overseas growth is a priority." in imported.material.text_utf8
        assert list(writer.staging_root.iterdir()) == []
        provenance = json.loads(
            Path(imported.canonical_import.provenance_path).read_text(encoding="utf-8")
        )
        assert provenance["source_url"] == source_url
        assert provenance["content_sha256"] == hashlib.sha256(body).hexdigest()
        audit = provenance["provenance_extensions"]["transcript_acquisition"]
        assert audit["schema_version"] == "transcript-acquisition-audit/1"
        assert audit["rights_policy_sha256"] == rights_policy.policy_sha256
        assert audit["download_authorization_hash"] == authorization.receipt_hash
        assert audit["effective_url"] == source_url
    finally:
        catalog.close()
        if run_root.exists():
            if run_root.is_symlink() or run_root.resolve(strict=True).parent != tmp_path.resolve(strict=True):
                raise AssertionError("refusing to remove test run root outside tmp_path")
            members = (run_root, *run_root.rglob("*"))
            if any(
                path.is_symlink() or getattr(path, "is_junction", lambda: False)()
                for path in members
            ):
                raise AssertionError("refusing to remove test run root containing a reparse path")
            shutil.rmtree(run_root)
    assert not run_root.exists()


def test_fake_provider_rechecks_then_imports_and_replays_transcript(tmp_path: Path):
    run_root = tmp_path / "e"
    assert not run_root.exists()
    run_root.mkdir()
    project = run_root / "p"
    companies = project / "c"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", companies, "company_raw", priority=10,
                    adapter_id="company_raw_v1",
                ),
            ),
        )
    )
    body = (
        b"<html><body><p>Acme 2026 Q2 earnings call</p>"
        b"<p>CEO: Overseas growth is a priority.</p>"
        b"<p>Analyst: When will the new business scale?</p>"
        b"<p>CEO: We have a plan, not a result yet.</p></body></html>"
    )
    source_url = "https://fixtures.invalid/transcripts/2026/q2.html"
    request = SourceRequest(
        entity="Acme Inc.", market="US", security_id="ACME",
        document_kind="investor_call_transcript", fiscal_year=2026,
        fiscal_period="Q2", as_of_date="2026-09-27", provider="fixture_provider",
        provider_document_id="acme-2026-q2", allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fixture-provider-doc-1", provider="fixture_provider",
        provider_document_id="acme-2026-q2", market="US", entity=request.entity,
        title="Acme Inc. 2026 Q2 Earnings Call", source_url=source_url,
        document_kind="investor_call_transcript", filing_date="2026-09-20",
        fiscal_year=2026, fiscal_period="Q2", remote_size=len(body),
        adapter_payload_json=json.dumps({"market": "US", "security_id": "ACME"}),
    )
    policy = _fixture_rights_policy()
    plan_hash = "a" * 64
    runtime_policy_hash = "b" * 64
    authorization = build_download_authorization(
        request_id=request.request_id,
        gap_plan_hash=plan_hash,
        policy_hash=runtime_policy_hash,
        provider=candidate.provider,
        allowed_accessions=(candidate.provider_document_id,),
        max_items=1,
        max_bytes=len(body),
        expires_at="2026-09-27T23:00:00Z",
    )
    run_time = "2026-09-27T12:00:00Z"
    try:
        catalog.scan()
        writer = CanonicalSourceWriter(catalog)

        denied_request = SourceRequest(
            entity=request.entity, market=request.market, security_id=request.security_id,
            document_kind=request.document_kind, fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period, as_of_date=request.as_of_date,
            provider=request.provider, provider_document_id=request.provider_document_id,
            allow_download=False,
        )
        denied_provider = _FakeTranscriptProvider(body, final_url=source_url)
        denied = authorize_transcript_fetch(
            request=denied_request, candidate=candidate, authorization=authorization,
            plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
            rights_policy=policy, now=run_time,
        )
        assert not denied.allowed
        assert denied_provider.fetch_calls == 0

        redirect_provider = _FakeTranscriptProvider(
            body, final_url="https://unapproved.invalid/transcripts/2026/q2.html"
        )
        admission = authorize_transcript_fetch(
            request=request, candidate=candidate, authorization=authorization,
            plan_hash=plan_hash, runtime_policy_hash=runtime_policy_hash,
            rights_policy=policy, now=run_time,
        )
        assert admission.allowed
        rejected_receipt = redirect_provider.fetch(candidate, writer.staging_root)
        rejected = validate_transcript_fetch_result(
            request=request, candidate=candidate, receipt=rejected_receipt,
            authorization=authorization, plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            pinned_rights_policy_sha256=admission.rights_policy_sha256,
            current_rights_policy=policy, final_url=redirect_provider.final_url,
            staging_root=writer.staging_root, now=run_time,
        )
        assert not rejected.allowed
        assert rejected.reason.startswith("final_url_rights_automated_fetch_")
        Path(rejected_receipt.staged_path).unlink()
        assert list(writer.staging_root.iterdir()) == []
        assert not any(companies.rglob("*.html"))

        provider = _FakeTranscriptProvider(body, final_url=source_url)
        receipt = provider.fetch(candidate, writer.staging_root)
        validation = validate_transcript_fetch_result(
            request=request, candidate=candidate, receipt=receipt,
            authorization=authorization, plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            pinned_rights_policy_sha256=admission.rights_policy_sha256,
            current_rights_policy=policy, final_url=provider.final_url,
            staging_root=writer.staging_root, now=run_time,
        )
        assert validation.allowed
        imported = writer.import_staged(request, candidate, receipt)
        assert imported.status is CanonicalImportStatus.IMPORTED_NEW
        original_path = Path(imported.canonical_path)
        assert original_path.read_bytes() == body
        assert not Path(receipt.staged_path).exists()

        material = extract_transcript_material(
            original_path.read_bytes(), mime_type=validation.mime_type
        )
        derived_root = run_root / "derived"
        derived_root.mkdir()
        derived_path = derived_root / f"{material.original_sha256}.txt"
        lineage_path = derived_root / f"{material.original_sha256}.lineage.json"
        derived_path.write_bytes(material.text_utf8.encode("utf-8"))
        lineage_path.write_text(
            json.dumps(material.lineage_dict(), sort_keys=True), encoding="utf-8"
        )
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        replay = load_transcript_material(
            lineage, original=original_path.read_bytes(),
            text_utf8=derived_path.read_bytes(), expected_mime_type=validation.mime_type,
        )
        assert replay == material
        assert replay.original_source_id == imported.source_id
        assert replay.original_sha256 == receipt.content_sha256
        assert "lines" not in lineage
        assert "CEO: Overseas growth is a priority." in replay.text_utf8
        assert "plan, not a result" in replay.text_utf8
        assert json.loads(Path(imported.provenance_path).read_text(encoding="utf-8"))[
            "source_url"
        ] == source_url

        reused = SourceResolver(catalog).resolve(request)
        assert any(handle.source_id == imported.source_id for handle in reused.matches)
    finally:
        catalog.close()
        if run_root.exists():
            if run_root.is_symlink() or run_root.resolve(strict=True).parent != tmp_path.resolve(strict=True):
                raise AssertionError("refusing to remove test run root outside tmp_path")
            members = (run_root, *run_root.rglob("*"))
            if any(
                path.is_symlink() or getattr(path, "is_junction", lambda: False)()
                for path in members
            ):
                raise AssertionError("refusing to remove test run root containing a reparse path")
            shutil.rmtree(run_root)
    assert not run_root.exists()
