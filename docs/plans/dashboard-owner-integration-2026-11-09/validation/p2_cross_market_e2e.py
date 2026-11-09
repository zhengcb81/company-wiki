"""Offline real-document P2 market/period integration check.

The caller supplies official source PDFs and a read-only copy of the verified
CWP security-master cache. All catalog/config/sidecar data are built inside a
TemporaryDirectory and removed on success or failure. No network/provider/model
call is allowed; an in-test provider writes a marker and fails if invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


SAMPLES = (
    {
        "key": "alibaba",
        "company_query": "BABA",
        "us_security_id": "BABA",
        "source_security_id": "09988",
        "fiscal_year": 2025,
        "period_end": "2025-03-31",
        "published_date": "2025-06-26",
        "title": "Alibaba Group FY2025 Annual Report",
        "filename": "2025-06-26_Alibaba_2025_annual_report.pdf",
        "official_url": "https://www.hkexnews.hk/listedco/listconews/sehk/2025/0626/2025062601064.pdf",
        "provider_document_id": "hkex-2025062601064",
        "expected_sha256": "c7806bf5da28032e1b15dbe9a334011d65f5d69efe3bf11a9d212f64f07ca9b2",
    },
    {
        "key": "bilibili",
        "company_query": "BILIBILI",
        "us_security_id": "BILI",
        "source_security_id": "09626",
        "fiscal_year": 2022,
        "period_end": "2022-12-31",
        "published_date": "2023-04-27",
        "title": "Bilibili Inc. FY2022 Annual Report",
        "filename": "2023-04-27_Bilibili_2022_annual_report.pdf",
        "official_url": "https://www.hkexnews.hk/listedco/listconews/sehk/2023/0427/2023042703073.pdf",
        "provider_document_id": "hkex-2023042703073",
        "expected_sha256": "712e23dc04fb7efa3a4d31b839b08eaf6ff92ea1d4c89f6458ace095b8bd24cf",
    },
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_process(
    command: list[str], *, env: dict[str, str], value: object | None = None,
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    payload = None if value is None else json.dumps(value, ensure_ascii=False).encode("utf-8")
    try:
        completed = subprocess.run(
            command, input=payload, capture_output=True, env=env, check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"command timed out after {timeout_seconds}s: {command!r}; "
            f"stdout={exc.stdout!r}; stderr={exc.stderr!r}"
        ) from exc
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f"command exited {completed.returncode}: {command!r}\n"
            f"stdout={stdout[-3000:]}\nstderr={stderr[-3000:]}"
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not return JSON: {command!r}\n{stdout[-3000:]}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"command JSON must be an object: {command!r}")
    return result


def _write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _load_frozen_json(evidence_dir: Path, evidence: object, label: str) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise ValueError(f"{label} evidence is missing")
    filename = evidence.get("file")
    expected_sha = str(evidence.get("sha256") or "").lower()
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or len(expected_sha) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha)
    ):
        raise ValueError(f"{label} evidence reference is malformed")
    path = evidence_dir / filename
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(f"{label} evidence hash differs from the frozen fixture")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} evidence must contain a JSON object")
    return value


def _validate_official_link_evidence(sample: dict[str, Any], evidence_dir: Path) -> dict[str, str]:
    lei = str(sample.get("lei") or "").strip().upper()
    legal_name = str(sample.get("legal_name") or "").strip()
    record_ref = sample.get("gleif_record")
    isin_ref = sample.get("gleif_isins")
    record_url = str(record_ref.get("url") or "") if isinstance(record_ref, dict) else ""
    isins_url = str(isin_ref.get("url") or "") if isinstance(isin_ref, dict) else ""
    if record_url != f"https://api.gleif.org/api/v1/lei-records/{lei}":
        raise ValueError(f"GLEIF record URL does not identify {sample.get('key')}")
    if isins_url != f"{record_url}/isins?page%5Bsize%5D=100":
        raise ValueError(f"GLEIF ISIN URL does not identify {sample.get('key')}")
    record = _load_frozen_json(evidence_dir, record_ref, f"{sample.get('key')} GLEIF record")
    isin_payload = _load_frozen_json(evidence_dir, isin_ref, f"{sample.get('key')} GLEIF ISIN map")
    attributes = record.get("data", {}).get("attributes", {})
    entity = attributes.get("entity", {})
    registration = attributes.get("registration", {})
    record_meta = record.get("meta", {}).get("goldenCopy", {})
    isin_meta = isin_payload.get("meta", {}).get("goldenCopy", {})
    if (
        record.get("data", {}).get("id") != lei
        or attributes.get("lei") != lei
        or entity.get("legalName", {}).get("name") != legal_name
        or entity.get("status") != "ACTIVE"
        or entity.get("jurisdiction") != "KY"
        or registration.get("status") != "ISSUED"
        or record_meta.get("publishDate") != sample.get("gleif_publish_date")
        or isin_meta.get("publishDate") != sample.get("gleif_publish_date")
    ):
        raise ValueError(f"GLEIF legal-entity record differs from the frozen {sample.get('key')} facts")
    isin_rows = isin_payload.get("data")
    if not isinstance(isin_rows, list):
        raise ValueError(f"GLEIF ISIN mapping is malformed for {sample.get('key')}")
    mapped_isins = {
        str(row.get("attributes", {}).get("isin") or "").strip().upper()
        for row in isin_rows
        if isinstance(row, dict)
        and row.get("type") == "isins"
        and str(row.get("attributes", {}).get("lei") or "").strip().upper() == lei
    }
    listings = sample.get("listings")
    cross_listing = sample.get("cross_listing")
    if not isinstance(listings, list) or not isinstance(cross_listing, dict):
        raise ValueError(f"listing relationship evidence is missing for {sample.get('key')}")
    by_market = {str(row.get("market") or "").upper(): row for row in listings if isinstance(row, dict)}
    if len(by_market) != 2 or set(by_market) != {"US", "HK"}:
        raise ValueError(f"expected one US and one HK listing for {sample.get('key')}")
    for market in ("US", "HK"):
        relation = cross_listing.get(market.lower())
        listing = by_market[market]
        if (
            not isinstance(relation, dict)
            or relation.get("market") != market
            or relation.get("security_id") != listing.get("security_id")
            or relation.get("isin") != listing.get("instrument_isin")
            or str(relation.get("isin") or "").upper() not in mapped_isins
        ):
            raise ValueError(f"cross-listing instrument mapping is not supported by GLEIF for {sample.get('key')}:{market}")
    if not str(sample.get("cross_listing_evidence_url") or "").startswith("https://"):
        raise ValueError(f"depositary cross-listing source is missing for {sample.get('key')}")
    return {
        "lei": lei,
        "legal_name": legal_name,
        "gleif_publish_date": str(sample["gleif_publish_date"]),
        "record_sha256": str(record_ref["sha256"]).lower(),
        "isins_sha256": str(isin_ref["sha256"]).lower(),
    }


def _metadata(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "company_name": sample["company_name"],
        "source_title": sample["title"],
        "market": "HK",
        "security_id": sample["source_security_id"],
        "ticker": sample["source_security_id"],
        "source_url": sample["official_url"],
        "provider": "hkex",
        "provider_document_id": sample["provider_document_id"],
        "document_kind": "annual_report",
        "form_type": "annual_report",
        "fiscal_year": sample["fiscal_year"],
        "fiscal_period": "FY",
        "period_end": sample["period_end"],
        "published_date": sample["published_date"],
    }


def _apply_sourced_lei_links(master_dir: Path, evidence_path: Path) -> list[dict[str, Any]]:
    """Enrich only the disposable master copy from frozen official link evidence."""
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict) or evidence.get("schema_version") != "p2-official-issuer-link-samples/2":
        raise ValueError("issuer-link evidence schema is unsupported")
    samples = evidence.get("samples")
    if not isinstance(samples, list):
        raise ValueError("issuer-link evidence samples are missing")
    snapshots = {
        path.stem.upper(): json.loads(path.read_text(encoding="utf-8"))
        for path in master_dir.glob("*.json")
    }
    result: list[dict[str, Any]] = []
    for sample in samples:
        lei = str(sample.get("lei") or "").strip().upper()
        verified_evidence = _validate_official_link_evidence(sample, evidence_path.parent / "evidence")
        link_url = str(sample.get("cross_listing_evidence_url") or "")
        listings = sample.get("listings")
        if (
            len(lei) != 20
            or not link_url.startswith("https://")
            or not isinstance(listings, list)
            or len({str(item.get("market", "")).upper() for item in listings}) < 2
        ):
            raise ValueError(f"issuer-link evidence is incomplete for {sample.get('key')}")
        applied = []
        for listing in listings:
            market = str(listing.get("market") or "").upper()
            snapshot = snapshots.get(market)
            rows = snapshot.get("records") if isinstance(snapshot, dict) else None
            if not isinstance(rows, list):
                raise ValueError(f"security master is missing {market} snapshot")
            security_id = str(listing.get("security_id") or "").strip().upper()
            matching = [
                row for row in rows
                if isinstance(row, dict)
                and str(row.get("security_id") or "").strip().upper() == security_id
            ]
            if len(matching) != 1:
                raise ValueError(f"expected one {market}:{security_id} security-master record")
            record = matching[0]
            expected_identity = (
                listing.get("source_name"), listing.get("source_url"), listing.get("source_record_id"),
            )
            observed_identity = (record.get("source_name"), record.get("source_url"), record.get("source_record_id"))
            if expected_identity != observed_identity:
                raise ValueError(f"{market}:{security_id} listing source differs from frozen evidence")
            identifiers = record.get("identifiers")
            if not isinstance(identifiers, dict):
                raise ValueError(f"{market}:{security_id} identifiers are malformed")
            existing = identifiers.get("lei")
            if existing not in (None, lei):
                raise ValueError(f"{market}:{security_id} already has a conflicting LEI")
            identifiers["lei"] = lei
            applied.append(f"{market}:{security_id}")
        for market in {str(item["market"]).upper() for item in listings}:
            path = master_dir / f"{market.lower()}.json"
            path.write_text(
                json.dumps(snapshots[market], ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
        result.append({
            "sample": sample.get("key"),
            "lei": lei,
            "listings": sorted(applied),
            "cross_listing_evidence_url": link_url,
            "gleif_record_url": sample["gleif_record"]["url"],
            "gleif_isins_url": sample["gleif_isins"]["url"],
            "gleif_evidence": verified_evidence,
        })
    return result


def _assert_source_query(
    command: list[str], env: dict[str, str], request: dict[str, Any], expected: bool,
) -> dict[str, Any]:
    result = _json_process(command, env=env, value=request)
    if expected:
        assert result["status"] == "found", result
        assert len(result["matches"]) == len(result["candidates"]) == 1, result
    else:
        assert result["status"] == "not_found", result
        assert result["matches"] == [] and result["candidates"] == [], result
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company-wiki-root", type=Path, required=True)
    parser.add_argument("--filing-fetch-root", type=Path, required=True)
    parser.add_argument("--security-master-dir", type=Path, required=True)
    parser.add_argument("--alibaba-pdf", type=Path, required=True)
    parser.add_argument("--bilibili-pdf", type=Path, required=True)
    parser.add_argument("--issuer-link-evidence", type=Path)
    parser.add_argument("--temp-parent", type=Path, required=True)
    args = parser.parse_args()

    cwp_root = args.company_wiki_root.resolve(strict=True)
    ff_root = args.filing_fetch_root.resolve(strict=True)
    master_root = args.security_master_dir.resolve(strict=True)
    issuer_link_evidence = (
        args.issuer_link_evidence.resolve(strict=True)
        if args.issuer_link_evidence is not None
        else Path(__file__).with_name("p2_issuer_link_samples.json").resolve(strict=True)
    )
    temp_parent = args.temp_parent.resolve(strict=True)
    sample_paths = {
        "alibaba": args.alibaba_pdf.resolve(strict=True),
        "bilibili": args.bilibili_pdf.resolve(strict=True),
    }
    for sample in SAMPLES:
        digest = _sha(sample_paths[sample["key"]])
        if digest != sample["expected_sha256"]:
            raise ValueError(f"{sample['key']} source bytes differ from the frozen official sample: {digest}")

    scripts = ff_root / "scripts"
    if not (scripts / "fetch_filing.py").is_file():
        raise ValueError("filing-fetch root must contain scripts/fetch_filing.py")
    if not list(master_root.glob("*.json")):
        raise ValueError("security-master directory has no snapshots")

    src = str(cwp_root / "src")
    prior_pythonpath = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = src + (os.pathsep + prior_pythonpath if prior_pythonpath else "")
    os.environ["PYTHONUTF8"] = "1"
    child_env = dict(os.environ)
    sys.path.insert(0, str(scripts))
    from fetch_filing import resolve_filing
    from ff_company_wiki_connection import WikiConnection

    with tempfile.TemporaryDirectory(prefix="p2-cross-market-", dir=temp_parent) as temporary:
        print("building temporary catalog", file=sys.stderr, flush=True)
        wiki = Path(temporary) / "wiki"
        config_dir = wiki / "config"
        security_master = wiki / ".source_catalog" / "security_master"
        companies = wiki / "companies"
        config_dir.mkdir(parents=True)
        security_master.mkdir(parents=True)
        for source in master_root.glob("*.json"):
            shutil.copy2(source, security_master / source.name)
        enriched_links = _apply_sourced_lei_links(security_master, issuer_link_evidence)

        cases: list[dict[str, Any]] = []
        for source_sample in SAMPLES:
            sample = dict(source_sample)
            sample["company_name"] = "Alibaba Group Holding Limited" if sample["key"] == "alibaba" else "Bilibili Inc."
            company_dir = companies / sample["key"] / "raw" / "financial_reports" / "annual"
            company_dir.mkdir(parents=True)
            source_pdf = sample_paths[sample["key"]]
            target_pdf = company_dir / sample["filename"]
            shutil.copy2(source_pdf, target_pdf)
            sidecar = target_pdf.with_name(target_pdf.name + ".source.json")
            sidecar.write_text(json.dumps(_metadata(sample), ensure_ascii=False), encoding="utf-8")
            cases.append(sample)

        source_config = config_dir / "source_catalog.yaml"
        _write_yaml(source_config, """schema_version: '1.0'
catalog_dir: '${PROJECT_ROOT}/.source_catalog'
roots:
  - root_id: company_raw
    path: '${PROJECT_ROOT}/companies'
    kind: company_raw
    priority: 10
""")

        marker = wiki / "provider_called"
        blocker = config_dir / "blocked_provider.py"
        blocker.write_text(
            "from pathlib import Path\nimport sys\n"
            f"Path({str(marker)!r}).write_text('called', encoding='utf-8')\n"
            "sys.stdout.write('{}')\nsys.exit(97)\n",
            encoding="utf-8",
        )
        acquisition_config = config_dir / "source_acquisition.yaml"
        command_text = "\n    command:\n      - '${PYTHON_EXECUTABLE}'\n      - '${PROJECT_ROOT}/config/blocked_provider.py'"
        _write_yaml(acquisition_config, """schema_version: '1.1'
staging_root: '${PROJECT_ROOT}/staging'
timeout_seconds: 30
adapters:
  cn:
    name: offline-test-blocker
    version: '1.0'
    interface: json_command_v1
    project_root: '${PROJECT_ROOT}'
    config_root: null""" + command_text + "\n  hk:\n    name: offline-test-blocker\n    version: '1.0'\n    interface: dayu_sdk_bounded_v1\n    project_root: '${PROJECT_ROOT}'\n    config_root: null\n    supports_acquisition_budget: true" + command_text + "\n  us:\n    name: offline-test-blocker\n    version: '1.0'\n    interface: dayu_sdk_bounded_v1\n    project_root: '${PROJECT_ROOT}'\n    config_root: null\n    supports_acquisition_budget: true" + command_text + "\n")

        python = str(Path(sys.executable).resolve())
        catalog_command = [python, "-m", "company_wiki.source_catalog.cli", "--config", str(source_config)]
        query_command = [python, "-m", "company_wiki.source_catalog.source_query_cli", "--config", str(source_config)]
        scan = _json_process([*catalog_command, "scan"], env=child_env)
        print("temporary catalog scan complete", file=sys.stderr, flush=True)
        assert scan["errors"] == 0 and scan["files_hashed"] >= 4, scan
        connection = WikiConnection(
            workdir=wiki,
            commands={
                "catalog": tuple(catalog_command),
                "query": tuple(query_command),
                "local_prepare": tuple([
                    python, "-m", "company_wiki.source_catalog.local_prepare_cli",
                    "--config", str(source_config),
                ]),
            },
            acquisition_config=acquisition_config,
        )

        report: list[dict[str, Any]] = []
        for sample in cases:
            print(f"checking {sample['key']}", file=sys.stderr, flush=True)
            request = {
                "schema_version": "2.0",
                "filing_intent": "reuse_only",
                "company_query": sample["company_query"],
                "market": "US",
                "source_market": "HK",
                "document_kind": "annual_report",
                "fiscal_year": sample["fiscal_year"],
                "form_type": "annual_report",
                "fiscal_period": "FY",
                "as_of_date": "2026-11-09",
            }
            query_stats = {"calls": 0, "downloads": 0}
            queried = resolve_filing(
                request=request, company_wiki_root=connection, source_ref_v2=True, stats=query_stats,
            )
            assert queried["company_identity"]["market"] == "US", queried
            assert queried["company_identity"]["security_id"] == sample["us_security_id"], queried
            assert queried["source_identity"]["market"] == "HK", queried
            assert queried["source_identity"]["security_id"] == sample["source_security_id"], queried
            listing_link = queried["company_identity"].get("issuer_link_id")
            source_link = queried["source_identity"].get("issuer_link_id")
            assert listing_link and listing_link == source_link, queried
            assert queried["market"] == "HK" and queried["security_id"] == sample["source_security_id"], queried
            assert queried["fiscal_year"] == sample["fiscal_year"]
            assert queried["fiscal_period"] == "FY" and queried["form_type"] == "annual_report"
            assert queried["source_ref"]["content_sha256"] == sample["expected_sha256"]
            assert queried["resolution_outcome"] == "reused_existing"
            assert query_stats["downloads"] == queried["download_events"] == 0

            source_request = {
                "entity": queried["source_identity"]["canonical_name"],
                "market": "HK",
                "security_id": sample["source_security_id"],
                "document_kind": "annual_report",
                "form_type": "annual_report",
                "fiscal_year": sample["fiscal_year"],
                "fiscal_period": "FY",
                "as_of_date": "2026-11-09",
            }
            local_payload = {
                "schema_version": "local-source-prepare-request/1",
                "source_request": source_request,
            }
            local = _json_process(
                [python, "-m", "company_wiki.source_catalog.local_prepare_cli", "--config", str(source_config), "--request", "-"],
                env=child_env, value=local_payload,
            )
            assert local["status"] == "ready" and local["download_events"] == 0, local
            assert local["source_ref"] == queried["source_ref"], local

            ensured = _json_process(
                [
                    *catalog_command, "ensure", "--entity", source_request["entity"],
                    "--market", "HK", "--security-id", sample["source_security_id"],
                    "--document-kind", "annual_report", "--form-type", "annual_report",
                    "--fiscal-year", str(sample["fiscal_year"]), "--fiscal-period", "FY",
                    "--as-of-date", "2026-11-09", "--source-ref-v2", "--allow-download",
                    "--max-download-bytes", "10000000", "--max-download-seconds", "60",
                    "--max-download-cost-usd", "0", "--acquisition-config", str(acquisition_config),
                ],
                env=child_env,
            )
            assert ensured["status"] == "completed" and ensured["outcome"] == "reused_existing", ensured
            assert ensured["download_events"] == 0 and ensured["source_ref"] == queried["source_ref"], ensured
            assert ensured["acquisition_observation"]["outcome"] == "reused_before_download", ensured

            ensure_request = {
                **request,
                "filing_intent": "fetch_if_missing",
                "acquisition_limits": {
                    "max_bytes": 10_000_000,
                    "timeout_seconds": 60,
                    "max_cost_usd": "0.00",
                },
            }
            ensure_stats = {"calls": 0, "downloads": 0}
            ensured_by_ff = resolve_filing(
                request=ensure_request, company_wiki_root=connection,
                source_ref_v2=True, stats=ensure_stats,
            )
            assert ensured_by_ff["source_ref"] == queried["source_ref"]
            assert ensured_by_ff["resolution_outcome"] == "reused_existing"
            assert ensure_stats["downloads"] == ensured_by_ff["download_events"] == 0
            report.append({
                "company": sample["key"],
                "listing": f"US:{sample['us_security_id']}",
                "source": f"HK:{sample['source_security_id']}",
                "issuer_link_id": listing_link,
                "issuer_link_evidence": next(
                    item["cross_listing_evidence_url"]
                    for item in enriched_links if item["sample"] == sample["key"]
                ),
                "fiscal_year": sample["fiscal_year"],
                "fiscal_period": "FY",
                "sha256": sample["expected_sha256"],
                "query_downloads": query_stats["downloads"],
                "ensure_downloads": ensure_stats["downloads"],
                "local_prepare_sha_matches": True,
            })

        sample = cases[0]
        good = {
            "entity": "阿里巴巴－Ｗ", "market": "HK", "security_id": "09988",
            "document_kind": "annual_report", "form_type": "annual_report",
            "fiscal_year": 2025, "fiscal_period": "FY", "as_of_date": "2026-11-09",
        }
        negatives = {
            "wrong_fiscal_year": {**good, "fiscal_year": 2024},
            "wrong_form_type": {**good, "form_type": "20-F"},
            "wrong_fiscal_period": {**good, "fiscal_period": "H1"},
            "wrong_source_security": {**good, "security_id": "00001"},
            "wrong_source_market": {**good, "entity": "Alibaba Group Holding Ltd", "market": "US", "security_id": "BABA"},
            "published_after_as_of": {**good, "as_of_date": "2025-06-25"},
        }
        for name, bad_request in negatives.items():
            _assert_source_query(query_command, child_env, bad_request, expected=False)
            report.append({"negative_case": name, "result": "not_found"})

        assert not marker.exists(), "provider unexpectedly ran during local reuse"
        print(json.dumps({
            "status": "passed",
            "samples": report,
            "sourced_issuer_links": enriched_links,
            "provider_started": False,
            "production_security_master_modified": False,
        }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
