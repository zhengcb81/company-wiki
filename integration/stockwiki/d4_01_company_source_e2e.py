"""Cross-repo end-to-end check for D4-01 (temporary roots, no production data).

Builds an isolated CWP catalog over two temporary physical roots, then drives
the real StockWiki CLI entries through the configured provider using the
DEPLOYED module form (``-m company_wiki...`` + PYTHONPATH), which is different
from the explicit-command form used in the committed unit tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CWP = Path(os.environ.get("D401_CWP_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
SW = Path(os.environ.get("D401_STOCKWIKI_ROOT", str(CWP.parent / "StockWiki"))).resolve()
# The delivery worktree's venv python may carry a Low integrity label on
# Windows and then cannot mkdir under %TEMP% (see AGENTS.md, Windows runtime
# section).  Default to the interpreter running this script; override with
# D401_PYTHON when a specific interpreter is required.
PYTHON = Path(os.environ.get("D401_PYTHON") or sys.executable)
ENTITY = "AMEC"
SECURITY = "688012.SH"
MARKET = "SSE"

sys.path.insert(0, str(CWP / "src"))


def _sidecar(kind, year, period, period_end, published, body, doc_id, market=MARKET, sec=SECURITY):
    return {
        "schema_version": "1.0", "ingest_complete": True,
        "canonical_entity_id": "ent-amec", "display_name": ENTITY,
        "company_name": ENTITY, "market": market, "security_id": sec,
        "document_kind": kind, "fiscal_year": year, "fiscal_period": period,
        "period_end": period_end, "filing_date": published, "language": "zh",
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "source_url": f"https://example.invalid/{doc_id}",
        "provider": "fixture", "provider_document_id": doc_id,
        "retrieved_at": "2026-06-01T00:00:00Z",
        "collector_name": "fixture", "collector_version": "1.0",
    }


def _write(root: Path, name: str, body: bytes, **kwargs) -> None:
    (root / name).write_bytes(body)
    (root / (name + ".source.json")).write_text(
        json.dumps(_sidecar(body=body, **kwargs), ensure_ascii=False), encoding="utf-8"
    )


def build_catalog(tmp: Path) -> tuple[Path, Path, Path]:
    root_a = tmp / "lake_a"
    root_b = tmp / "lake_b"
    root_a.mkdir()
    root_b.mkdir()
    annual = "年度报告：营业收入同比增长 34.13%，刻蚀设备收入创新高。\n".encode()
    _write(root_a, "2026-03-20_annual.md", annual,
           kind="annual_report", year=2025, period="FY",
           period_end="2025-12-31", published="2026-03-20", doc_id="amec-fy2025")
    _write(root_b, "copy_2026-03-20_annual.md", annual,
           kind="annual_report", year=2025, period="FY",
           period_end="2025-12-31", published="2026-03-20", doc_id="amec-fy2025")
    _write(root_a, "2026-04-28_q1.md",
           "第一季度报告：研发支出占营业收入比例约为 31.14%。\n".encode(),
           kind="quarterly_report", year=2026, period="Q1",
           period_end="2026-03-31", published="2026-04-28", doc_id="amec-q1-2026")
    _write(root_b, "2026-05-10_research.md", "券商研报：维持增持评级。\n".encode(),
           kind="broker_research", year=2026, period="",
           period_end="2026-05-10", published="2026-05-10", doc_id="amec-research")

    catalog_dir = tmp / ".catalog"
    config_path = tmp / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(catalog_dir),
        "roots": [
            {"root_id": "lake_a", "path": str(root_a), "kind": "directory",
             "priority": 10, "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True},
            {"root_id": "lake_b", "path": str(root_b), "kind": "directory",
             "priority": 20, "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True},
        ],
        "reusable_root_kinds": ["directory"],
    }), encoding="utf-8")

    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp, catalog_dir=catalog_dir,
        roots=(
            RootSpec("lake_a", root_a, "directory", priority=10,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
            RootSpec("lake_b", root_b, "directory", priority=20,
                     adapter_id="sidecar_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
        reusable_root_kinds=("directory",),
    ))
    catalog.scan()
    catalog.close()
    return config_path, root_a, root_b


def build_workspace(tmp: Path, catalog_config: Path) -> Path:
    root = tmp / "sw"
    config = root / "config"
    config.mkdir(parents=True)
    (config / "companies.yaml").write_text(
        "companies:\n"
        "- ticker: 688012.SH\n"
        "  name: AMEC\n"
        "  exchange: SSE\n"
        "  industry: semiconductor_equipment\n"
        "  aliases: []\n"
        "  doc_root: ''\n"
        "  source_provider: cwp\n"
        "  news_keywords: []\n"
        "  tags: []\n",
        encoding="utf-8",
    )
    (config / "source_providers.yaml").write_text(
        "schema_version: '1.0'\nproviders:\n  cwp:\n"
        "    kind: company_source_index\n"
        "    transport_config: config/cwp_source_index.transport.json\n"
        "    page_size: 2\n    max_pages: 50\n",
        encoding="utf-8",
    )
    (config / "cwp_source_index.transport.json").write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_config": [str(catalog_config)],
        "env": {"PYTHONPATH": str(CWP / "src")},
        "timeout_s": 120,
        "max_index_stdout_bytes": 8388608,
        "max_source_bytes": 67108864,
        "max_stderr_bytes": 262144,
    }), encoding="utf-8")
    (config / "extraction_policy.yaml").write_text(
        "default_mode: chunk\nsource_types:\n  filing:\n    mode: chunk\n",
        encoding="utf-8",
    )
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if not k.endswith("API_KEY")}
    env["PYTHONPATH"] = str(SW)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(PYTHON), "-m", "stockwiki.cli", "--root", str(root), *args],
        cwd=str(SW), env=env, capture_output=True, timeout=300,
    )


def main() -> int:
    requested_tmp = os.environ.get("D401_TEMP_ROOT")
    if requested_tmp:
        tmp = Path(requested_tmp).resolve()
        tmp.mkdir(parents=True, exist_ok=False)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="d401-e2e-"))
    config_path, root_a, root_b = build_catalog(tmp)
    workspace = build_workspace(tmp, config_path)
    failures: list[str] = []

    listing = run(workspace, "company-sources", "--ticker", "688012.SH")
    print("== company-sources rc", listing.returncode)
    payload = json.loads(listing.stdout.decode("utf-8") or "{}")
    print("   status", payload.get("status"), "count", payload.get("source_count"),
          "pages", payload.get("pages"))
    if payload.get("status") != "ok" or payload.get("source_count") != 3:
        failures.append("listing did not return 3 source versions")
    annual = [s for s in payload.get("sources", [])
              if s["document_kind"] == "annual_report"]
    if len(annual) != 1 or annual[0]["copies"] != 2:
        failures.append("duplicate copies were not collapsed into one version")
    for blob in (listing.stdout, listing.stderr):
        text = blob.decode("utf-8", "replace")
        for physical in (str(root_a), str(root_b), "lake_a", "lake_b"):
            if physical in text:
                failures.append(f"listing leaked {physical}")

    pipeline = run(workspace, "run-company", "--ticker", "688012.SH", "--name", "AMEC")
    print("== run-company rc", pipeline.returncode)
    if pipeline.returncode != 0:
        print(pipeline.stdout.decode("utf-8", "replace")[-2000:])
        print(pipeline.stderr.decode("utf-8", "replace")[-2000:])
        failures.append("run-company failed")
    manifest_path = workspace / "data" / "companies" / "688012.SH" / "external_sources.yaml"
    manifest = manifest_path.read_text(encoding="utf-8")
    if "company_source_provider" not in manifest:
        failures.append("manifest did not record the provider protocol")
    import yaml

    parsed = yaml.safe_load(manifest)
    if "doc_root" in parsed:
        failures.append("manifest still records a top-level doc_root")
    if "doc_root" in parsed.get("source_protocol", {}):
        failures.append("source protocol still records a doc_root")
    for physical in (str(root_a), str(root_b)):
        if physical.replace("\\", "/") in manifest.replace("\\", "/"):
            failures.append("manifest leaked a physical root")

    enrich = run(workspace, "enrich-evidence", "--ticker", "688012.SH",
                 "--no-refresh-reviews")
    print("== enrich-evidence rc", enrich.returncode)
    if enrich.returncode != 0:
        print(enrich.stderr.decode("utf-8", "replace")[-2000:])
        failures.append("enrich-evidence failed")

    signals = run(workspace, "extract-document-signals", "--ticker", "688012.SH",
                  "--no-refresh-reviews")
    print("== extract-document-signals rc", signals.returncode)
    if signals.returncode != 0:
        print(signals.stderr.decode("utf-8", "replace")[-2000:])
        failures.append("extract-document-signals failed")

    # A withdrawn original must be reported, not silently dropped.
    (root_a / "2026-04-28_q1.md").unlink()
    after = run(workspace, "company-sources", "--ticker", "688012.SH")
    after_payload = json.loads(after.stdout.decode("utf-8") or "{}")
    q1 = [s for s in after_payload.get("sources", [])
          if s["document_kind"] == "quarterly_report"]
    print("== after withdrawal", q1[0]["availability"] if q1 else "missing")
    if not q1 or q1[0]["availability"] != "unreadable":
        failures.append("withdrawn original was not reported as unreadable")

    print("\nRESULT", "PASS" if not failures else "FAIL")
    for item in failures:
        print(" -", item)
    print("TMP", tmp)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
