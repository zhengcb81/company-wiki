"""Bounded local diagnosis only; offline provider port never supplies a download."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import socket
import tempfile
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator,
    AdapterRegistry,
    DownloadCandidate,
)
from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.official_source_flow import import_official_source
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
from company_wiki.source_catalog.source_reader import (
    SourceVersionReader,
    SourceReadError,
)
from company_wiki.source_catalog.store import retire_document, restore_document

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[4]


class OfflineFetchReached(RuntimeError):
    pass


class OfflineAdapter:
    name = "offline-diagnosis-port"
    version = "1.0.0"

    def __init__(self):
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        return (
            DownloadCandidate(
                candidate_id="offline-1",
                provider="official",
                provider_document_id="original-1",
                market="US",
                entity=request.entity,
                title="Acme FY2026 Q2",
                source_url="https://official.example/filing",
                document_kind="regulatory_filing",
                filing_date="2026-01-28",
                fiscal_year=2026,
                fiscal_period="Q2",
                form_type="10-Q",
                language="en",
            ),
        )

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        raise OfflineFetchReached("OFFLINE_FETCH_REACHED_NO_BYTES_DOWNLOADED")


def main():
    parent = Path(tempfile.gettempdir()).resolve()
    owned = Path(tempfile.mkdtemp(prefix="legacy-local-", dir=parent)).resolve()
    original_connect = socket.socket.connect
    network_attempts = []

    def blocked_connect(*args, **kwargs):
        network_attempts.append(True)
        raise AssertionError("diagnosis must not access network")

    socket.socket.connect = blocked_connect
    catalog = None
    result = {
        "schema_version": "legacy-local-counterexample/1",
        "mode": "offline local fixture; no successful simulated download",
        "code_head": "979792e0a4105b18aed06dc7053f7bc239de6865",
        "temp_root": str(owned),
        "checks": {},
        "supplier_requests": 0,
        "model_requests": 0,
        "download_events": 0,
    }
    protected = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "config/source_catalog.yaml",
            "config/source_acquisition.yaml",
            "config/local_ocr.json",
        )
        if (ROOT / name).exists()
    }
    result["protected_before"] = protected
    try:
        (owned / "companies").mkdir()
        catalog = SourceCatalog(
            CatalogConfig(
                project_root=owned,
                catalog_dir=owned / "catalog",
                roots=(RootSpec("company_raw", owned / "companies", "company_raw"),),
            )
        )
        original = b"<html><h1>Acme FY2026 Q2 filing</h1><p>Original issuer filing content.</p></html>"
        sha = hashlib.sha256(original).hexdigest()
        source = {
            "entity": "Acme",
            "market": "US",
            "security_id": "ACME",
            "document_kind": "regulatory_filing",
            "title": "Acme FY2026 Q2 filing",
            "publisher": "Acme",
            "source_url": "https://official.example/filing",
            "published_date": "2026-01-28",
            "filing_date": "2026-01-28",
            "fiscal_year": 2026,
            "fiscal_period": "Q2",
            "period_end": "2025-12-31",
            "language": "en",
        }
        request = {
            "schema_version": "official-source-import-request/1",
            "request_id": "local-diagnosis-1",
            "source": source,
            "content_sha256": sha,
            "mime_type": "text/html",
            "max_bytes": 4096,
            "capture_receipt": {
                "capture_method": "local_document",
                "tool_name": "offline-diagnosis",
                "tool_call_id": "fixture-1",
                "captured_at": "2026-10-09T00:00:00Z",
                "response_bytes": len(original),
                "content_sha256": sha,
            },
        }
        imported = import_official_source(catalog, original=original, request=request)
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(
            imported["source_ref"]["document_id"],
            imported["source_ref"]["source_id"],
            sha,
        )
        business = SourceRequest(
            entity="Acme",
            market="US",
            security_id="ACME",
            document_kind="regulatory_filing",
            fiscal_year=2026,
            fiscal_period="Q2",
            as_of_date="2026-10-09",
        )

        def facts(patch):
            return catalog.record_source_facts(
                ref=ref,
                facts=patch,
                evidence={
                    key: {"locator": "owned-fixture:/" + key, "value": value}
                    for key, value in patch.items()
                },
            )

        facts({"source_url": None})
        sparse = SourceResolver(catalog).resolve(business)
        assert (
            sparse.status.value == "reused_equivalent"
            and sparse.matches[0].https_url is None
        )
        assert reader.query_local(business).status == "found"
        result["checks"]["active_unknown_url_reuses"] = {
            "resolver": sparse.status.value,
            "source_query": "found",
            "capture_ready": sparse.matches[0].capture_ready,
            "missing_fields": list(sparse.matches[0].missing_capture_fields),
        }
        retire_document(
            catalog.store,
            document_id=ref.document_id,
            reason="legacy sidecar lacks source_url; metadata governance",
            created_by="offline-fixture",
        )
        exact = None
        try:
            reader.query_ref(ref.document_id, ref.source_id, sha)
        except SourceReadError as exc:
            exact = {"status": exc.status, "reason": exc.reason}
        assert exact == {"status": "blocked", "reason": "source_not_active"}
        assert SourceResolver(catalog).resolve(business).status.value == "missing"
        assert reader.query_local(business).status == "not_found"
        catalog.register_sources(
            root_id="company_raw",
            relative_paths={
                str(p.relative_to(owned / "companies")).replace(chr(92), "/")
                for p in (owned / "companies").rglob("*.html")
            },
        )
        row = catalog.reader.exact_source_version(ref.document_id)
        assert row["source_status"] == "retired"
        result["checks"]["retired_complete_raw_stays_missing_after_registration"] = {
            "exact_query": exact,
            "resolver": "missing",
            "source_query": "not_found",
            "source_status_after_scoped_register": "retired",
        }
        adapter = OfflineAdapter()
        coordinator = AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(adapter, adapter, adapter),
            staging_root=owned / "stage",
        )
        no_download = coordinator.select(business)
        assert no_download.status.value == "missing" and adapter.discover_calls == 0
        service = SourceAcquisitionService(
            coordinator=coordinator,
            writer=CanonicalSourceWriter(catalog, staging_root=owned / "stage"),
            journal=AcquisitionJournal(owned / "catalog"),
        )
        try:
            service.ensure(replace(business, allow_download=True))
        except OfflineFetchReached:
            pass
        else:
            raise AssertionError("offline fetch seam should be reached")
        assert adapter.discover_calls == adapter.fetch_calls == 1
        assert (
            catalog.reader.exact_source_version(ref.document_id)["source_status"]
            == "retired"
        )
        result["checks"]["fetch_if_missing_reaches_fetch_before_dedup"] = {
            "offline_discover_invocations": adapter.discover_calls,
            "offline_fetch_invocations": adapter.fetch_calls,
            "download_events": 0,
            "network_requests": 0,
            "success": False,
        }
        restored = restore_document(
            catalog.store,
            document_id=ref.document_id,
            reason="owned-fixture verified local bytes; metadata-only retirement",
            created_by="offline-diagnosis",
        )
        assert (
            SourceResolver(catalog).resolve(business).status.value
            == "reused_equivalent"
        )
        result["checks"]["existing_audited_restore_primitive"] = {
            "source_status": restored["source_status"],
            "restore_audit_rows": len(
                catalog.store.fetchall("SELECT audit_id FROM document_restore_audit")
            ),
            "source_url": reader.describe_version(ref)["source_url"],
        }
        facts({"market": "HK", "fiscal_year": 2025})
        assert reader.query_local(business).status == "not_found"
        retire_document(
            catalog.store,
            document_id=ref.document_id,
            reason="metadata-only fixture wrong market/period",
            created_by="offline-fixture",
        )
        imported_again = import_official_source(
            catalog,
            original=original,
            request={**request, "request_id": "local-diagnosis-2"},
        )
        manifest = reader.describe_version(ref)
        assert (
            imported_again["status"] == "deduplicated"
            and imported_again["download_events"] == 0
        )
        assert manifest["market"] == "HK" and manifest["fiscal_year"] == 2025
        assert reader.query_local(business).status == "not_found"
        result["checks"][
            "existing_canonical_local_import_reactivates_but_does_not_correct_facts"
        ] = {
            "import_status": imported_again["status"],
            "source_status": catalog.reader.exact_source_version(ref.document_id)[
                "source_status"
            ],
            "market": manifest["market"],
            "fiscal_year": manifest["fiscal_year"],
            "correct_business_query": "not_found",
            "download_events": 0,
        }
        facts(
            {
                "market": "US",
                "fiscal_year": 2026,
                "fiscal_period": "Q2",
                "source_url": None,
            }
        )
        assert reader.query_local(business).status == "found"
        assert reader.open_version(ref, purpose="source_export").data == original
        assert (
            SourceResolver(catalog).resolve(business).status.value
            == "reused_equivalent"
        )
        result["checks"][
            "existing_source_fact_correction_primitive_reuses_without_url_guess"
        ] = {
            "source_query": "found",
            "resolver": "reused_equivalent",
            "verified_bytes_sha256": sha,
            "source_url": reader.describe_version(ref)["source_url"],
            "download_events": 0,
        }
        assert not network_attempts
        result["exit_code"] = 0
    except Exception as exc:
        result.update(exit_code=1, error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        if catalog is not None:
            catalog.close()
        socket.socket.connect = original_connect
        assert (
            owned.parent == parent
            and owned.name.startswith("legacy-local-")
            and not owned.is_symlink()
        )
        assert not any(path.is_symlink() for path in owned.rglob("*"))
        shutil.rmtree(owned)
        result["temp_final"] = "absent" if not owned.exists() else "cleanup_failed"
        result["network_attempts"] = len(network_attempts)
        result["protected_after"] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in protected
        }
        assert result["protected_after"] == protected
        (PACKAGE / "local_counterexample_receipt.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
