"""Storage-only preparation: existing public CWP interfaces, no executor/provider/model/OCR."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
import yaml

MAIN = Path(__file__).resolve().parents[5]
PKG = Path(__file__).resolve().parent
PREP = PKG.parent / "fresh_sources_preparation"
FF = Path.home() / ".agents/skills/filing-fetch"
RF = Path.home() / ".agents/skills/revenue-forecast"
ET = (
    Path.home()
    / "Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py"
)
sys.path.insert(0, str(MAIN / "src"))
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader  # noqa: E402
from company_wiki.source_catalog.assertion_service import (  # noqa: E402
    SOURCE_FACT_FIELDS,
    get_verified_assertion,
)  # noqa: E402
from company_wiki.source_catalog.security_identity import (  # noqa: E402
    SecurityMasterStore,
    SecurityIdentityResolver,
)  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def file_inventory(root, *, hash_files=True):
    return [
        {
            "relative_path": p.relative_to(root).as_posix(),
            "byte_size": p.stat().st_size,
            **({"sha256": sha(p.read_bytes())} if hash_files else {}),
        }
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def main():
    if (PKG / "environment_manifest.json").exists():
        raise RuntimeError(
            "Existing prepared manifest; retain/reuse it rather than duplicate environments"
        )
    source_manifest = json.loads((PREP / "manifest.json").read_text(encoding="utf-8"))
    retained_locations = json.loads(
        (PREP / "registered_storage_locations.json").read_text(encoding="utf-8")
    )
    location_map = {
        x["source_ref"]["content_sha256"]: x["storage"]["registered_locations"]
        for x in retained_locations
    }
    base_temp = Path(tempfile.gettempdir()).resolve()
    owned = Path(tempfile.mkdtemp(prefix="mFresh-", dir=base_temp))
    if owned.parent != base_temp or not owned.name.startswith("mFresh-"):
        raise RuntimeError("Invalid owned temporary root")
    production_config = MAIN / "config/source_catalog.yaml"
    production = SourceCatalog(
        load_catalog_config(production_config, project_root=MAIN)
    )
    prod_reader = SourceVersionReader(production)
    master_store = SecurityMasterStore(
        production.config.catalog_dir / "security_master"
    )
    master = master_store.load()
    prod_roots = {r.root_id: r for r in production.config.roots}
    protected_configs = [
        production_config,
        MAIN / "config/source_acquisition.yaml",
        MAIN / "config/local_ocr.json",
    ]
    before_configs = {str(p): sha(p.read_bytes()) for p in protected_configs}
    originals = {}
    operations = []
    environments = []
    peak = {"total": 0}
    stop = threading.Event()
    runtime_guard = owned / "validation_guard"
    runtime_guard.mkdir()
    guard = runtime_guard / "sitecustomize.py"
    guard.write_text(
        "import os,socket\ndef refuse(*a,**k):\n p=os.environ.get('MFRESH_NETWORK_LOG')\n if p:\n  with open(p,'a',encoding='utf-8') as f:f.write('network_attempt\\n')\n raise RuntimeError('mFresh preparation prohibits network')\nsocket.socket.connect=refuse\nsocket.create_connection=refuse\n",
        encoding="utf-8",
    )
    write_json(
        PKG / "allocation.json",
        {
            "owned_root": str(owned),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retain_until": "fresh execution and all four reviews complete",
            "production_catalog_copied": False,
        },
    )

    def monitor():
        while not stop.wait(0.05):
            total = 0
            for env in environments:
                amount = sum(
                    p.stat().st_size
                    for p in Path(env["root"]).rglob("*")
                    if p.is_file()
                )
                peak[env["company"]] = max(peak.get(env["company"], 0), amount)
                total += amount
            peak["total"] = max(peak["total"], total)

    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()

    def execute(company, argv, payload=None, *, binary=False):
        e = next(x for x in environments if x["company"] == company)
        env = dict(os.environ)
        env.update(
            PYTHONUTF8="1",
            PYTHONDONTWRITEBYTECODE="1",
            TEMP=e["temp"],
            TMP=e["temp"],
            PYTHONPATH=str(runtime_guard) + os.pathsep + str(MAIN / "src"),
            MFRESH_NETWORK_LOG=str(owned / "network_attempts.log"),
        )
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(
            argv,
            input=json.dumps(payload).encode() if payload is not None else None,
            capture_output=True,
            cwd=e["root"],
            env=env,
            timeout=180,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stderr = result.stderr.decode("utf-8", errors="replace")
        out = (
            {"sha256": sha(result.stdout), "byte_size": len(result.stdout)}
            if binary
            else json.loads(result.stdout)
        )
        operation = {
            "company": company,
            "argv": list(map(str, argv)),
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": result.returncode,
            "stdout": out,
            "stderr": stderr[-12000:],
        }
        operations.append(operation)
        write_json(PKG / "prepare_operations.json", operations)
        if result.returncode:
            raise RuntimeError(
                "Public preparation failed; exact failure retained: " + repr(argv)
            )
        return out, stderr

    try:
        for company in source_manifest["companies"]:
            key = company["company"]
            identity = (
                SecurityIdentityResolver(master)
                .identify(
                    company["identity_payload"]["security_id"],
                    market=company["identity_payload"]["market"],
                )
                .resolved
            )
            if identity is None or not identity.verified or not identity.active:
                raise RuntimeError("Verified source identity missing")
            root = owned / key
            folders = {
                name: root / name
                for name in (
                    "config",
                    "companies",
                    "catalog",
                    "provider-state/dayu",
                    "state/ff",
                    "state/et",
                    "auto",
                    "work",
                    "rf/registry",
                    "rf/output",
                    "temp",
                )
            }
            for folder in folders.values():
                folder.mkdir(parents=True)
            for name in {
                identity.canonical_name,
                identity.ticker,
                identity.security_id,
                company["identity_payload"]["display_name"],
            }:
                (folders["companies"] / name / "raw").mkdir(parents=True, exist_ok=True)
            record = next(
                x
                for x in master.records
                if x.market == identity.market and x.security_id == identity.security_id
            )
            snapshot = master.snapshots[identity.market]
            SecurityMasterStore(folders["catalog"] / "security_master").write_market(
                identity.market,
                (record,),
                retrieved_at=snapshot["retrieved_at"],
                sources=tuple(snapshot["sources"]),
            )
            roots = [
                {
                    "root_id": "company_raw",
                    "kind": "company_raw",
                    "path": str(folders["companies"]),
                    "priority": 10,
                    "read_only": False,
                }
            ]
            for old in prod_roots.values():
                if old.root_id == "future_lake":
                    continue
                roots.append(
                    {
                        "root_id": "existing_" + old.root_id,
                        "kind": "dayu_portfolio"
                        if old.kind == "dayu_portfolio"
                        else "directory",
                        "path": str(old.path),
                        "priority": old.priority + 100,
                        "read_only": True,
                    }
                )
            catalog_config = {
                "schema_version": "1.0",
                "catalog_dir": str(folders["catalog"]),
                "reusable_root_kinds": ["company_raw", "directory", "dayu_portfolio"],
                "roots": roots,
            }
            config = folders["config"] / "source_catalog.yaml"
            config.write_text(
                yaml.safe_dump(catalog_config, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            acquisition = yaml.safe_load(
                (MAIN / "config/source_acquisition.yaml").read_text(encoding="utf-8")
            )
            acquisition["staging_root"] = str(folders["catalog"] / "staging")
            for adapter in acquisition["adapters"].values():
                adapter["project_root"] = str(adapter["project_root"]).replace(
                    "${PROJECT_ROOT}", str(MAIN)
                )
                adapter["command"] = [
                    str(x).replace("${PROJECT_ROOT}", str(MAIN))
                    for x in adapter["command"]
                ]
                if "--provider-state-root" in adapter["command"]:
                    adapter["command"][
                        adapter["command"].index("--provider-state-root") + 1
                    ] = str(folders["provider-state/dayu"])
            (folders["config"] / "source_acquisition.yaml").write_text(
                yaml.safe_dump(acquisition, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            ff_config = folders["config"] / "filing_fetch_company_wiki.json"
            write_json(
                ff_config, {"schema_version": "1.0", "company_wiki_root": str(root)}
            )
            environment = {
                "company": key,
                "root": str(root),
                "catalog_config": str(config),
                "ff_config": str(ff_config),
                "company_raw": str(folders["companies"]),
                "catalog": str(folders["catalog"]),
                "provider_state": str(folders["provider-state/dayu"]),
                "ff_state": str(folders["state/ff"]),
                "et_state": str(folders["state/et"]),
                "temp": str(folders["temp"]),
                "automation_db": str(folders["auto"] / "narrative.sqlite3"),
                "work_dir": str(folders["work"]),
                "rf_registry": str(folders["rf/registry"]),
                "rf_output": str(folders["rf/output"]),
                "identity": identity.to_dict(),
                "sources": [],
                "gaps": company["limitations"],
                "future_download_targets": company["required_real_FF_downloads"],
                "max_bytes": 256 * 1024 * 1024,
                "supplier_budget": "MAIN actual account/history allocation required; AUTO db not initialized",
                "default_read_receipt": "2.1",
            }
            environments.append(environment)
            cat = SourceCatalog(load_catalog_config(config, project_root=root))
            try:
                for number, item in enumerate(company["minimum_registration_group"]):
                    ref = item.get("source_ref")
                    storage = item.get("storage") or {}
                    output = {"role": item["role"], "source_ref": None, "status": "gap"}
                    if ref:
                        matching = [
                            x
                            for x in location_map.get(ref["content_sha256"], [])
                            if x["role"] == "original_primary"
                            and x["location_status"] == "active"
                            and x["root_id"] in prod_roots
                        ]
                        if not matching:
                            raise RuntimeError(
                                "No exact active registered original group"
                            )
                        loc = sorted(
                            matching, key=lambda x: prod_roots[x["root_id"]].priority
                        )[0]
                        path = prod_roots[loc["root_id"]].path / loc["relative_path"]
                        info = path.stat()
                        originals[str(path)] = {
                            "byte_size": info.st_size,
                            "mtime_ns": info.st_mtime_ns,
                            "expected_sha256": ref["content_sha256"],
                        }
                        execute(
                            key,
                            [
                                sys.executable,
                                "-B",
                                "-m",
                                "company_wiki.source_catalog.cli",
                                "--config",
                                str(config),
                                "register",
                                "--root-id",
                                "existing_" + loc["root_id"],
                                "--relative-path",
                                loc["relative_path"],
                            ],
                        )
                        actual_ref = prod_reader.query_ref(
                            ref["document_id"], ref["source_id"], ref["content_sha256"]
                        )
                        metadata = prod_reader.describe_version(actual_ref)
                        assertion = get_verified_assertion(
                            production.reader,
                            ref["source_id"],
                            ref["content_sha256"],
                            reader="steady",
                        )
                        facts = {f: metadata.get(f) for f in SOURCE_FACT_FIELDS}
                        facts["entity"] = (
                            metadata.get("display_name") or identity.canonical_name
                        )
                        original_evidence = (
                            json.loads(assertion["evidence_json"]) if assertion else {}
                        )
                        prior_field_evidence = (
                            original_evidence.get("source_fact_evidence") or {}
                        )
                        evidence = {
                            f: prior_field_evidence.get(f)
                            if f in prior_field_evidence
                            and prior_field_evidence[f].get("value") == value
                            else {
                                "locator": "existing-public-source-manifest:/" + f,
                                "value": value,
                                "content_sha256": ref["content_sha256"],
                                "prior_assertion_id": assertion["assertion_id"]
                                if assertion
                                else None,
                            }
                            for f, value in facts.items()
                        }
                        request_file = folders["temp"] / "source_facts.json"
                        write_json(
                            request_file,
                            {"source_ref": ref, "facts": facts, "evidence": evidence},
                        )
                        try:
                            execute(
                                key,
                                [
                                    sys.executable,
                                    "-B",
                                    "-m",
                                    "company_wiki.source_catalog.cli",
                                    "--config",
                                    str(config),
                                    "source-facts",
                                    "--request",
                                    str(request_file),
                                ],
                            )
                        finally:
                            request_file.unlink(missing_ok=True)
                        output.update(
                            source_ref=ref,
                            status="registered_existing_readonly",
                            prior_assertion_id=assertion["assertion_id"]
                            if assertion
                            else None,
                        )
                    elif storage.get("raw_path") and key == "US-MSFT":
                        path = Path(storage["raw_path"])
                        relative = path.relative_to(
                            prod_roots["dayu_portfolio"].path
                        ).as_posix()
                        originals[str(path)] = {
                            "byte_size": path.stat().st_size,
                            "mtime_ns": path.stat().st_mtime_ns,
                            "expected_sha256": item["raw"]["sha256"],
                        }
                        execute(
                            key,
                            [
                                sys.executable,
                                "-B",
                                "-m",
                                "company_wiki.source_catalog.cli",
                                "--config",
                                str(config),
                                "register",
                                "--root-id",
                                "existing_dayu_portfolio",
                                "--relative-path",
                                relative,
                            ],
                        )
                        request = {
                            "schema_version": "local-source-prepare-request/1",
                            "source_request": {
                                "entity": identity.canonical_name,
                                "market": identity.market,
                                "security_id": identity.security_id,
                                "document_kind": "regulatory_filing",
                                "fiscal_year": item["source_metadata"]["fiscal_year"],
                                "fiscal_period": item["source_metadata"][
                                    "fiscal_period"
                                ],
                                "as_of_date": source_manifest["as_of_date"],
                                "allow_download": False,
                                "schema_version": "1.0",
                            },
                            "limits": {
                                "max_candidates": 64,
                                "max_bytes": 128 * 1024 * 1024,
                                "timeout_seconds": 60,
                            },
                        }
                        result, _ = execute(
                            key,
                            [
                                sys.executable,
                                "-B",
                                "-m",
                                "company_wiki.source_catalog.local_prepare_cli",
                                "--config",
                                str(config),
                                "--request",
                                "-",
                            ],
                            request,
                        )
                        if (
                            result["status"] != "ready"
                            or result["download_events"] != 0
                        ):
                            raise RuntimeError("Existing SEC local facts unresolved")
                        output.update(
                            source_ref=result["source_ref"],
                            status="registered_existing_sec_facts_corrected",
                        )
                    elif storage.get("archive_path") and item.get("source_metadata"):
                        path = Path(storage["archive_path"])
                        raw = item["raw"]
                        originals[str(path)] = {
                            "byte_size": path.stat().st_size,
                            "mtime_ns": path.stat().st_mtime_ns,
                            "expected_sha256": raw["sha256"],
                        }
                        source = {
                            **item["source_metadata"],
                            "entity": identity.canonical_name,
                            "market": identity.market,
                            "security_id": identity.security_id,
                            "publisher": identity.canonical_name,
                        }
                        mime = source.pop("mime_type")
                        call_id = key + "-local-import-" + str(number)
                        request = {
                            "schema_version": "official-source-import-request/1",
                            "request_id": call_id,
                            "source": source,
                            "mime_type": mime,
                            "content_sha256": raw["sha256"],
                            "max_bytes": raw["byte_size"],
                            "capture_receipt": {
                                "capture_method": "local_document",
                                "tool_name": "CWP official_source_cli",
                                "tool_call_id": call_id,
                                "captured_at": datetime.now(timezone.utc).isoformat(),
                                "content_sha256": raw["sha256"],
                                "response_bytes": raw["byte_size"],
                            },
                        }
                        request_file = folders["temp"] / "official_import.json"
                        write_json(request_file, request)
                        try:
                            result, _ = execute(
                                key,
                                [
                                    sys.executable,
                                    "-B",
                                    "-m",
                                    "company_wiki.source_catalog.official_source_cli",
                                    "--config",
                                    str(config),
                                    "--request",
                                    str(request_file),
                                    "--input-file",
                                    str(path),
                                ],
                            )
                        finally:
                            request_file.unlink(missing_ok=True)
                        if result["download_events"] != 0:
                            raise RuntimeError("Unexpected download")
                        output.update(
                            source_ref=result["source_ref"],
                            status="local_official_import",
                            publication_proof=item.get("publication_proof"),
                        )
                    else:
                        output.update(
                            reason=item.get("limits") or item.get("action"),
                            storage_reference=storage,
                            raw_identity=item.get("raw"),
                        )
                    if output["source_ref"]:
                        source_ref = SourceRef(**output["source_ref"])
                        queried = SourceVersionReader(cat).query_ref(
                            source_ref.document_id,
                            source_ref.source_id,
                            source_ref.content_sha256,
                        )
                        output["manifest"] = SourceVersionReader(cat).describe_version(
                            queried
                        )
                    environment["sources"].append(output)
            finally:
                cat.close()
            for config_file in folders["config"].iterdir():
                destination = PKG / "configs" / key / config_file.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(config_file.read_bytes())
            environment["initial_files"] = file_inventory(root)
            environment["initial_bytes"] = sum(
                x["byte_size"] for x in environment["initial_files"]
            )
            write_json(PKG / "environments" / (key + ".json"), environment)
        representative = environments[0]
        ref = next(
            x["source_ref"] for x in representative["sources"] if x["source_ref"]
        )
        request = {
            "schema_version": "2.0",
            "company_query": representative["identity"]["security_id"],
            "market": "CN",
            "document_kind": "annual_report",
            "fiscal_year": 2025,
            "mode": "exact",
            "as_of_date": source_manifest["as_of_date"],
            "filing_intent": "reuse_only",
        }
        result, _ = execute(
            representative["company"],
            [
                sys.executable,
                "-B",
                str(FF / "scripts/fetch_filing.py"),
                "--config",
                representative["ff_config"],
                "--timeout-seconds",
                "90",
            ],
            request,
        )
        if result.get("downloads") != 0 or result["filing"]["source_ref"] != ref:
            raise RuntimeError("Public FF reuse representative mismatch")
        opened, receipt = execute(
            representative["company"],
            [
                sys.executable,
                "-B",
                "-m",
                "company_wiki.source_catalog.source_reader_cli",
                "--config",
                representative["catalog_config"],
                "--document-id",
                ref["document_id"],
                "--source-id",
                ref["source_id"],
                "--content-sha256",
                ref["content_sha256"],
            ],
            binary=True,
        )
        if opened != {"sha256": ref["content_sha256"], "byte_size": ref["byte_size"]}:
            raise RuntimeError("Public raw reader identity mismatch")
        proof = {
            "ff": result,
            "read": opened,
            "receipt": json.loads(receipt),
            "representative_only": True,
        }
        write_json(PKG / "public_representative_receipt.json", proof)
        network = owned / "network_attempts.log"
        if network.exists() and network.stat().st_size:
            raise RuntimeError("Unexpected network attempt")
        for path, before in originals.items():
            after = Path(path).stat()
            if (after.st_size, after.st_mtime_ns) != (
                before["byte_size"],
                before["mtime_ns"],
            ):
                raise RuntimeError("Readonly original changed")
        after_configs = {str(p): sha(p.read_bytes()) for p in protected_configs}
        if after_configs != before_configs:
            raise RuntimeError("Protected production configuration changed")
        for env in environments:
            env["observed_peak_bytes"] = max(
                peak.get(env["company"], 0), env["initial_bytes"]
            )
            largest_import = max(
                (
                    s["source_ref"]["byte_size"]
                    for s in env["sources"]
                    if s["status"] == "local_official_import"
                ),
                default=0,
            )
            env["conservative_prepare_peak_bound"] = (
                env["initial_bytes"] + 2 * largest_import
            )
            if env["conservative_prepare_peak_bound"] > env["max_bytes"]:
                raise RuntimeError("Environment byte cap exceeded")
            write_json(PKG / "environments" / (env["company"] + ".json"), env)
        total = sum(e["initial_bytes"] for e in environments)
        conservative = sum(e["conservative_prepare_peak_bound"] for e in environments)
        if conservative > 512 * 1024 * 1024:
            raise RuntimeError("Total byte cap exceeded")
        write_json(
            PKG / "environment_manifest.json",
            {
                "schema_version": "fresh-cohort-environment/1",
                "status": "storage_prepared_research_NOT_RUN",
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "owned_root": str(owned),
                "as_of_date": source_manifest["as_of_date"],
                "source_manifest_sha256": sha((PREP / "manifest.json").read_bytes()),
                "environments": environments,
                "initial_bytes": total,
                "observed_peak_bytes": max(peak["total"], total),
                "conservative_prepare_peak_bound": conservative,
                "max_total_bytes": 512 * 1024 * 1024,
                "source_inputs": originals,
                "protected_configs_sha256": after_configs,
                "production_catalog_copied": False,
                "activity": {
                    "provider_requests": 0,
                    "download_events": 0,
                    "model_requests": 0,
                    "OCR_inferences": 0,
                    "executor_runs": 0,
                },
                "retain_until": "fresh execution and all four reviews complete",
                "cleanup_scope": str(owned),
                "pending_MAIN": "actual current budget/history allocations; research launch; source clock gaps; four reviews then safe cleanup",
                "code_root": str(MAIN),
                "rf_skill": str(RF),
                "ff_skill": str(FF),
                "et_tool": str(ET),
                "auto_databases_initialized": False,
            },
        )
        print(
            json.dumps(
                {
                    "status": "storage_prepared",
                    "owned_root": str(owned),
                    "environments": len(environments),
                    "sources": sum(
                        bool(s["source_ref"])
                        for e in environments
                        for s in e["sources"]
                    ),
                    "initial_bytes": total,
                    "peak_bound": conservative,
                    "network_attempts": 0,
                }
            )
        )
    finally:
        stop.set()
        watcher.join(timeout=1)
        production.close()
        guard.unlink(missing_ok=True)
        runtime_guard.rmdir()
        write_json(
            PKG / "prepare_partial_state.json",
            {
                "owned_root": str(owned),
                "environments": [e["company"] for e in environments],
                "operations": len(operations),
                "environment_retained": True,
                "process_env_unchanged": True,
                "network_guard_removed": not runtime_guard.exists(),
            },
        )


if __name__ == "__main__":
    main()
