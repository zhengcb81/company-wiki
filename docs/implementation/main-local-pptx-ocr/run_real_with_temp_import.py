"""One owned TEMP catalog, public MAIN import, isolated parser check, finally cleanup."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import yaml

SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def invoke(command, *, cwd, env, timeout):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "child_failed")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-project", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--object-root", type=Path, required=True)
    parser.add_argument("--ocr-config", type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    worktree = package.parents[2]
    original = args.object_root / "objects" / "c0" / SHA
    before = original.stat()
    assert (
        hashlib.sha256(original.read_bytes()).hexdigest() == SHA
        and before.st_size == 4016522
    )
    main_env = dict(os.environ)
    main_env["PYTHONPATH"] = str(args.main_project / "src")
    work_env = dict(os.environ)
    work_env["PYTHONPATH"] = str(worktree / "src")
    receipt_file = package / "real_import_receipt.json"
    output = package / "real_22_page_statistics.json"
    root = None
    status = "failed"
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="cwocr-source-") as folder:
            root = Path(folder).resolve()
            (root / "companies").mkdir()
            config = root / "catalog.yaml"
            config.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "1.0",
                        "catalog_dir": str(root / "catalog"),
                        "roots": [
                            {
                                "root_id": "company_raw",
                                "path": str(root / "companies"),
                                "kind": "company_raw",
                            }
                        ],
                    },
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            request = root / "request.json"
            request.write_text(
                json.dumps(
                    {
                        "schema_version": "official-source-import-request/1",
                        "request_id": "main-local-pptx-ocr-20261009-local-import",
                        "source": {
                            "entity": "MICROSOFT CORP",
                            "market": "US",
                            "security_id": "MSFT",
                            "document_kind": "investor_relations",
                            "title": "FY27 Segments and Investor Metrics",
                            "publisher": "Microsoft",
                            "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/FY27ExternalKPIs.pptx",
                            "published_date": None,
                            "fiscal_year": None,
                            "fiscal_period": None,
                            "language": "en",
                        },
                        "content_sha256": SHA,
                        "mime_type": MIME,
                        "max_bytes": 8 * 1024 * 1024,
                        "capture_receipt": {
                            "capture_method": "local_document",
                            "tool_name": "official_source_cli",
                            "tool_call_id": "main-local-pptx-ocr-20261009-local-import",
                            "captured_at": datetime.now(timezone.utc).isoformat(),
                            "response_bytes": before.st_size,
                            "content_sha256": SHA,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            stdout = invoke(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-B",
                    "-m",
                    "company_wiki.source_catalog.official_source_cli",
                    "--config",
                    str(config),
                    "--project-root",
                    str(root),
                    "--request",
                    str(request),
                    "--input-file",
                    str(original.resolve()),
                ],
                cwd=args.main_project,
                env=main_env,
                timeout=30,
            )
            receipt = json.loads(stdout)
            assert receipt["download_events"] == 0
            receipt_file.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            read_script = """
import hashlib,json,sys
from pathlib import Path
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader
catalog=SourceCatalog(load_catalog_config(Path(sys.argv[1]),project_root=Path(sys.argv[2])))
try:
    imported=json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    ref=imported["source_ref"]
    reader=SourceVersionReader(catalog)
    exact=reader.query_ref(ref["document_id"],ref["source_id"],ref["content_sha256"])
    opened=reader.open_version(exact,purpose="source_export")
    print(json.dumps({"sha256":hashlib.sha256(opened.data).hexdigest(),"bytes":len(opened.data),"source_id":exact.source_id}))
finally:catalog.close()
"""
            checked = json.loads(
                invoke(
                    [
                        sys.executable,
                        "-X",
                        "utf8",
                        "-B",
                        "-c",
                        read_script,
                        str(config),
                        str(root),
                        str(receipt_file),
                    ],
                    cwd=args.main_project,
                    env=main_env,
                    timeout=30,
                )
            )
            assert checked["sha256"] == SHA and checked["bytes"] == before.st_size
            print("official local import and SourceVersionReader verified", flush=True)
            result = invoke(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-B",
                    str(package / "run_real_local_ocr.py"),
                    "--suite",
                    str(args.suite),
                    "--object-root",
                    str(args.object_root),
                    "--ocr-config",
                    str(args.ocr_config),
                    "--output",
                    str(output),
                    "--import-receipt",
                    str(receipt_file),
                    "--timeout",
                    "240",
                ],
                cwd=worktree,
                env=work_env,
                timeout=250,
            )
            print(result.strip(), flush=True)
            status = "completed"
    finally:
        after = original.stat()
        record = {
            "schema_version": "cwp-local-ocr-environment-restoration/1",
            "status": status,
            "owned_catalog_root": str(root),
            "owned_catalog_root_exists_after": root.exists() if root else None,
            "original_sha256_after": hashlib.sha256(original.read_bytes()).hexdigest(),
            "original_size_unchanged": before.st_size == after.st_size,
            "original_mtime_ns_unchanged": before.st_mtime_ns == after.st_mtime_ns,
            "subprocess_environment_only": True,
            "production_config_written": False,
            "installed_models_written": False,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
        (package / "environment_restoration.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        assert (
            record["owned_catalog_root_exists_after"] is False
            and record["original_sha256_after"] == SHA
        )


if __name__ == "__main__":
    main()
