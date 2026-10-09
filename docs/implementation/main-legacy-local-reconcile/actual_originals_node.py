"""Read four actual originals; write only an owned isolated catalog and evidence receipt."""

from __future__ import annotations
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import yaml
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityIdentityResolver,
)
from company_wiki.source_catalog.store import retire_document
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits

PACKAGE = Path(__file__).resolve().parent
SOURCE = PACKAGE.parents[2] / "src"
MAIN = Path("C:/Users/郑曾波/Projects/company-wiki")
OBSERVATIONS = (
    MAIN
    / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/legacy_local_reuse_diagnosis/actual_raw_readonly_observations.json"
)
FF = Path(
    "C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/ff-diagnostics/scripts/fetch_filing.py"
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            h.update(data)
    return h.hexdigest()


def main():
    start = time.monotonic()
    observed = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))["observations"]
    protected = {Path(x["raw_path"]): digest(Path(x["raw_path"])) for x in observed}
    for item in observed:
        path = Path(item["raw_path"])
        for side in [
            path.parent / "meta.json",
            path.with_name(path.name + ".source.json"),
        ]:
            if side.is_file():
                protected[side] = digest(side)
    for name in [
        "config/source_catalog.yaml",
        "config/source_acquisition.yaml",
        "config/local_ocr.json",
    ]:
        path = MAIN / name
        if path.exists():
            protected[path] = digest(path)
    parent = Path(tempfile.gettempdir()).resolve()
    owned = Path(tempfile.mkdtemp(prefix="cwplocal-", dir=parent)).resolve()
    old_temp = os.environ.get("TEMP")
    old_tmp = os.environ.get("TMP")
    old_pythonpath = os.environ.get("PYTHONPATH")
    catalog = None
    result = {
        "schema_version": "actual-local-reconcile-node/1",
        "base": "a40eb065da1bb21d231d2644449e2ecd8a2f98d6",
        "ff_script": str(FF),
        "ff_script_sha256": digest(FF),
        "supplier_requests": 0,
        "model_requests": 0,
        "download_events": 0,
        "cases": [],
        "owned_temp": str(owned),
        "mode": "real originals read only; isolated historical catalog",
    }
    try:
        os.environ["TEMP"] = str(owned)
        os.environ["TMP"] = str(owned)
        (owned / "config").mkdir()
        (owned / "companies").mkdir()
        (owned / "guard").mkdir()
        (owned / "guard/sitecustomize.py").write_text(
            "import os,socket\nfrom pathlib import Path\ndef deny(*args,**kwargs):\n p=Path(os.environ['LOCAL_NODE_NETWORK_LOG']);p.open('a').write('attempt\\n');raise RuntimeError('LOCAL_NODE_NO_NETWORK')\nsocket.socket.connect=deny\nsocket.create_connection=deny\n",
            encoding="utf-8",
        )
        config = {
            "schema_version": "1.0",
            "catalog_dir": str(owned / "catalog"),
            "reusable_root_kinds": ["company_raw", "dayu_portfolio", "directory"],
            "roots": [
                {
                    "root_id": "company_raw",
                    "kind": "company_raw",
                    "path": str(owned / "companies"),
                    "priority": 10,
                },
                {
                    "root_id": "dayu_portfolio",
                    "kind": "dayu_portfolio",
                    "path": str(MAIN.parent / "dayu-agent/workspace/portfolio"),
                    "priority": 20,
                },
                {
                    "root_id": "dropbox_stock",
                    "kind": "directory",
                    "path": str(Path(observed[0]["raw_path"]).parents[3]),
                    "priority": 30,
                },
            ],
        }
        config_path = owned / "config/source_catalog.yaml"
        config_path.write_text(
            yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
        )
        ff_config = owned / "ff.json"
        ff_config.write_text(
            json.dumps({"schema_version": "1.0", "company_wiki_root": str(owned)}),
            encoding="utf-8",
        )
        catalog = SourceCatalog(load_catalog_config(config_path, project_root=owned))
        master_dir = catalog.config.catalog_dir / "security_master"
        master = SecurityMasterStore(MAIN / ".source_catalog/security_master").load()
        for market in ("US", "CN"):
            snapshot = master.snapshots[market]
            records = [
                x
                for x in master.records
                if x.market == market and x.security_id in {"MSFT", "688012"}
            ]
            SecurityMasterStore(master_dir).write_market(
                market,
                records,
                retrieved_at=snapshot["retrieved_at"],
                sources=tuple(snapshot["sources"]),
            )
        identity = SecurityIdentityResolver(SecurityMasterStore(master_dir).load())
        for record in master.records:
            if record.security_id in {"MSFT", "688012"}:
                (owned / "companies" / record.canonical_name / "raw").mkdir(
                    parents=True, exist_ok=True
                )

        environment = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONPATH": str(owned / "guard") + os.pathsep + str(SOURCE),
            "LOCAL_NODE_NETWORK_LOG": str(owned / "network.log"),
        }
        refs = []
        for item in observed:
            path = Path(item["raw_path"])
            root_id = (
                "dropbox_stock" if path.suffix.lower() == ".pdf" else "dayu_portfolio"
            )
            root = next(x for x in catalog.config.roots if x.root_id == root_id)
            catalog.register_sources(
                root_id=root_id, relative_paths={path.relative_to(root.path).as_posix()}
            )
            row = catalog.reader.fetchone(
                "SELECT document_id,primary_source_id FROM documents WHERE primary_source_id=?",
                ("urn:company-wiki:source:sha256:" + item["sha256"],),
            )
            assert row is not None
            for audit in item["retire_audit"]:
                retire_document(
                    catalog.store,
                    document_id=row["document_id"],
                    reason=audit["reason"],
                    created_by=audit["created_by"],
                )
            refs.append((item, row["document_id"]))

        def ff_call(request):
            call = subprocess.run(
                [
                    sys.executable,
                    str(FF),
                    "--config",
                    str(ff_config),
                    "--timeout-seconds",
                    "120",
                    "--no-pause-worker",
                ],
                input=json.dumps(request, ensure_ascii=False).encode(),
                capture_output=True,
                env=environment,
                cwd=owned,
                timeout=125,
            )
            value = json.loads(call.stdout)
            assert (
                value.get("downloads", value.get("transport", {}).get("downloads", 0))
                == 0
            )
            return call.returncode, value

        for item, document_id in refs:
            sec = item.get("actual_primary_DEI")
            market = "US" if sec else "CN"
            code = "MSFT" if sec else "688012"
            resolved = identity.identify(code, market=market).resolved
            assert resolved
            request = {
                "schema_version": "2.0",
                "company_query": code,
                "market": market,
                "document_kind": item["document"]["document_kind"],
                "fiscal_year": sec["fiscal_year"] if sec else 2024,
                "fiscal_period": sec["fiscal_period"] if sec else "FY",
                "as_of_date": "2026-10-09",
                "mode": "exact",
                "filing_intent": "reuse_only",
            }
            exit_code, payload = ff_call(request)
            case = {
                "sha256": item["sha256"],
                "byte_size": item["byte_size"],
                "request": request,
                "ff_exit": exit_code,
                "ff": payload,
                "source_status": catalog.reader.exact_source_version(document_id)[
                    "source_status"
                ],
            }
            if sec:
                assert exit_code == 0, (exit_code, payload)
                filing = payload["filing"]
                ref = filing["source_ref"]
                assert (
                    ref["content_sha256"] == item["sha256"]
                    and ref["document_id"] == document_id
                )
                opened = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "company_wiki.source_catalog.source_reader_cli",
                        "--config",
                        str(config_path),
                        "--document-id",
                        ref["document_id"],
                        "--source-id",
                        ref["source_id"],
                        "--content-sha256",
                        ref["content_sha256"],
                        "--purpose",
                        "filing_reuse",
                    ],
                    capture_output=True,
                    env=environment,
                    cwd=owned,
                    timeout=45,
                )
                assert (
                    opened.returncode == 0
                    and hashlib.sha256(opened.stdout).hexdigest() == item["sha256"]
                    and len(opened.stdout) == item["byte_size"]
                )
                receipt = json.loads(opened.stderr)
                assert (
                    receipt["manifest"]["fiscal_year"] == 2026
                    and receipt["manifest"]["market"] == "US"
                )
                case["public_read_receipt"] = receipt
                case["actual_read_sha256"] = hashlib.sha256(opened.stdout).hexdigest()
                before = [
                    catalog.store.fetchone("SELECT COUNT(*) FROM " + table)[0]
                    for table in [
                        "source_metadata_assertions",
                        "document_restore_audit",
                    ]
                ]
                again_exit, again = ff_call(request)
                assert again_exit == 0 and again["filing"]["source_ref"] == ref
                assert before == [
                    catalog.store.fetchone("SELECT COUNT(*) FROM " + table)[0]
                    for table in [
                        "source_metadata_assertions",
                        "document_restore_audit",
                    ]
                ]
                case["repeat_ff"] = again
                case["repeat_counts_unchanged"] = True
                day_before = (
                    date.fromisoformat(receipt["manifest"]["published_date"])
                    - timedelta(days=1)
                ).isoformat()
                outside_exit, outside = ff_call({**request, "as_of_date": day_before})
                assert outside_exit != 0
                case["outside_as_of"] = {
                    "as_of_date": day_before,
                    "exit": outside_exit,
                    "ff": outside,
                }
            else:
                assert exit_code != 0 and case["source_status"] == "retired", (
                    exit_code,
                    payload,
                )
                local = prepare_local_source(
                    catalog,
                    SourceRequest(
                        entity=resolved.canonical_name,
                        market=market,
                        security_id=code,
                        document_kind=request["document_kind"],
                        fiscal_year=2024,
                        fiscal_period="FY",
                        as_of_date=request["as_of_date"],
                    ),
                    limits=LocalPrepareLimits(timeout_seconds=45),
                )
                case["local_prepare"] = local
                if not local["blocks_download"]:
                    case["inventory_debug"] = [
                        {"document_id": x["document_id"], "entities": x["entities"]}
                        for x in catalog.query_filing_candidates(
                            document_kind=request["document_kind"],
                            source_statuses=("retired",),
                            limit=10,
                        )
                    ]
                    result["cases"].append(case)
                assert local["status"] != "ready" and local["blocks_download"]
                case["local_prepare"] = local
                case["honest_publication_gap"] = True
            result["cases"].append(case)
        network = owned / "network.log"
        result["network_attempts"] = (
            len(network.read_text().splitlines()) if network.exists() else 0
        )
        assert result["network_attempts"] == 0
        result["checks_complete"] = True
    except Exception as exc:
        result["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
        raise
    finally:
        if catalog:
            catalog.close()
        for key, value in [
            ("TEMP", old_temp),
            ("TMP", old_tmp),
            ("PYTHONPATH", old_pythonpath),
        ]:
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        result["protected_sources_after"] = {
            str(path): digest(path) for path in protected
        }
        result["protected_sources_unchanged"] = all(
            result["protected_sources_after"][str(path)] == sha
            for path, sha in protected.items()
        )
        assert (
            owned.parent == parent
            and owned.name.startswith("cwplocal-")
            and not owned.is_symlink()
        )
        shutil.rmtree(owned)
        result["temp_absent"] = not owned.exists()
        result["temp_environment_restored"] = (
            os.environ.get("TEMP") == old_temp and os.environ.get("TMP") == old_tmp
        )
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        PACKAGE.joinpath("actual_originals_receipt.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "checks_complete": result["checks_complete"],
                "cases": len(result["cases"]),
                "elapsed_seconds": result["elapsed_seconds"],
                "network_attempts": result["network_attempts"],
                "temp_absent": result["temp_absent"],
                "protected_sources_unchanged": result["protected_sources_unchanged"],
            }
        )
    )


if __name__ == "__main__":
    main()
