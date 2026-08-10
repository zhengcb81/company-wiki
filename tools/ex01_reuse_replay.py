"""FC-601 replay: EX-01 companies-only exact reuse on real CN/HK/US samples.

Resolves the three real strong-identity company_raw samples (CN 紫金矿业
601899 FY2025 cninfo, HK 美团 03690 FY2024 hkexnews, US Apple AAPL FY2025
sec) against the LIVE catalog read-only and asserts REUSED_EXACT with no
download path — provider discover/fetch and canonical write stay at zero
by construction (the resolver returns before any acquisition step).
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    ResolutionStatus,
    RootSpec,
    SourceCatalog,
    SourceRequest,
    SourceResolver,
)

SAMPLES = [
    {
        "name": "CN-601899-紫金矿业-FY2025",
        "entity": "紫金矿业",
        "market": "CN", "security_id": "601899",
        "fiscal_year": 2025, "provider": "cninfo",
        "provider_document_id": "1225023658",
    },
    {
        "name": "HK-03690-美團Ｗ-FY2024",
        "entity": "美團－Ｗ",
        "market": "HK", "security_id": "03690",
        "fiscal_year": 2024, "provider": "hkexnews",
        "form_type": "FY",
        "provider_document_id": "11645024",
    },
    {
        "name": "US-AAPL-Apple-FY2025",
        "entity": "Apple Inc",
        "market": "US", "security_id": "AAPL",
        "fiscal_year": 2025, "provider": "sec",
        "provider_document_id": "0000320193-25-000079",
    },
]


def main() -> int:
    project = PROJECT_ROOT
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw"),),
        )
    )
    resolver = SourceResolver(catalog)
    results = []
    for sample in SAMPLES:
        request = SourceRequest(
            entity=sample["entity"],
            market=sample["market"],
            security_id=sample["security_id"],
            document_kind="annual_report",
            form_type=sample.get("form_type"),
            fiscal_year=sample["fiscal_year"],
            provider=sample["provider"],
            provider_document_id=sample.get("provider_document_id"),
            as_of_date="2026-08-10",
        )
        result = resolver.resolve(request)
        if result.status is not ResolutionStatus.REUSED_EXACT:
            raise SystemExit(
                f"FAIL: {sample['name']} -> {result.status.value} "
                f"({result.reason}); matches={len(result.matches)}"
            )
        if result.download_required or result.download_allowed:
            raise SystemExit(f"FAIL: {sample['name']} download path opened")
        handle = result.matches[0]
        results.append({
            "sample": sample["name"],
            "status": result.status.value,
            "download_required": result.download_required,
            "canonical_path": handle.canonical_path,
            "provider": handle.provider,
            "provider_document_id": handle.provider_document_id,
            "fiscal_year": handle.fiscal_year,
            "capture_ready": handle.capture_ready,
        })
    print(json.dumps({"result": "EX-01 passed (3/3 REUSED_EXACT)", "samples": results},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
