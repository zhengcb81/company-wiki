"""ROOT acceptance: real FF bounded transport -> CWP CLI -> immutable rows.

The test composition adds CWP's existing fixture-provider option to its child
command. It neither replaces FF transport nor fabricates a CWP response.
No production API/config/catalog/original is touched. Run with --help.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob("*") if p.is_file()}


def stable_files(files):
    # SQLite pages/WAL/SHM are mutable storage, not immutable originals. A
    # checkpoint may change physical hashes without changing a single row.
    return {key: value for key, value in files.items()
            if key not in {".source_catalog/catalog.sqlite3", ".source_catalog/catalog.sqlite3-wal",
                           ".source_catalog/catalog.sqlite3-shm"}}


def database_content(wiki):
    database = wiki / ".source_catalog/catalog.sqlite3"
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        return hashlib.sha256("\n".join(connection.iterdump()).encode()).hexdigest()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwp-root", type=Path, required=True)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("use a new output filename; previous receipts are immutable")
    control = Path(__file__).resolve().parents[5]
    cwp, ff = args.cwp_root.resolve(), args.ff_root.resolve()
    sys.path[:0] = [str(cwp / "src"), str(cwp / "tests"), str(ff / "scripts")]
    import ff_financial_statements as client
    from financial_statements import test_offline_e2e_full as fixture
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

    source_files = [*sorted((cwp / "src/company_wiki/source_catalog/financial_statements").glob("*.py")),
        cwp / "src/company_wiki/source_catalog/canonical_writer.py",
        cwp / "src/company_wiki/source_catalog/service.py",
        ff / "scripts/ff_financial_statements.py", ff / "scripts/fetch_statements.py"]
    binding = {str(p): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in source_files}
    scratch = Path(tempfile.mkdtemp(prefix="r19-", dir=control)).resolve()
    started = time.monotonic()
    receipt = {"schema_version": "w19-ff-cwp-offline-acceptance/1", "passed": False,
               "test_provider": "frozen real Sina bytes via CWP fixture port",
               "real_network_requests": 0, "new_paid_calls": 0, "source_binding": binding}
    catalog = None
    try:
        wiki = fixture._wiki_root(scratch)
        fixtures = fixture._fixture_root(scratch)
        connection = scratch / "connection.json"
        connection.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(wiki)}), encoding="utf-8")
        original_command = client.build_cwp_command
        def command(root):
            return original_command(root) + ["--fixture-root", str(fixtures)]
        env = {"PYTHONPATH": str(cwp / "src"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
        request = {**fixture.REQUEST, "as_of_date": "2026-10-26"}
        # Omitted lists must be defaulted by the authoritative CWP endpoint,
        # not refused or filled in by the FF client.
        request.pop("statements")
        request.pop("report_types")
        with patch.object(client, "build_cwp_command", command), patch.dict(os.environ, env):
            response = client.fetch_statements(config_path=connection, request=request, timeout_seconds=120)
            require(response["status"] == "complete", "initial capture incomplete")
            require(response["usage"]["http_requests"] == 15, "unexpected fixture exchange count")
            counts = {s["statement_type"]: len(s["reports"]) for s in response["statements"]}
            require(counts == fixture.PAGE_COUNTS, "three-table coverage mismatch")
            catalog = SourceCatalog(load_catalog_config(wiki / "config/source_catalog.yaml", project_root=wiki))
            reader = SourceVersionReader(catalog)
            originals = {}
            numeric_rows = 0
            total_rows = 0
            for statement in response["statements"]:
                for report in statement["reports"]:
                    ref = SourceRef(**report["source_ref"])
                    if ref.source_id not in originals:
                        opened = reader.open_version(ref, purpose="source_export")
                        require(len(opened.data) == ref.byte_size, "public source byte size mismatch")
                        require(asdict(ref) == report["source_ref"], "reconstructed source reference differs")
                        originals[ref.source_id] = json.loads(opened.data)
                    for row in report["rows"]:
                        total_rows += 1
                        if row["value_kind"] != "numeric":
                            continue
                        raw = originals[ref.source_id]
                        for segment in row["json_pointer"].strip("/").split("/"):
                            segment = segment.replace("~1", "/").replace("~0", "~")
                            raw = raw[int(segment)] if isinstance(raw, list) else raw[segment]
                        require(Decimal(str(raw)) == Decimal(row["value_decimal"]), "numeric row not equal to original pointer")
                        numeric_rows += 1
            require(total_rows == 9729 and len(originals) == 12, "unexpected rows/original count")
            catalog.close()
            catalog = None
            database_before = database_content(wiki)
            before = snapshot(wiki)
            size = sum(item[0] for item in before.values())
            require(size <= 16 * 1024 * 1024, "test data footprint exceeded 16MiB")
            reused = client.fetch_statements(config_path=connection, request=request, timeout_seconds=120)
            require(reused["status"] == "complete" and reused["usage"]["http_requests"] == 0, "second request refetched data")
            after = snapshot(wiki)
            if stable_files(after) != stable_files(before):
                receipt["repeat_changed_files"] = [{"path": key, "before": before.get(key), "after": after.get(key)}
                    for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)]
            require(stable_files(after) == stable_files(before), "second fetch changed immutable originals/config")
            require(database_content(wiki) == database_before, "second fetch changed catalog rows")
            local = {**request, "intent": "reuse_only"}
            local.pop("acquisition_limits")
            reused = client.fetch_statements(config_path=connection, request=local, timeout_seconds=120)
            require(reused["status"] == "complete" and reused["usage"]["http_requests"] == 0, "readonly reuse incomplete")
            final = snapshot(wiki)
            require(stable_files(final) == stable_files(before), "readonly query changed immutable originals/config")
            require(database_content(wiki) == database_before, "readonly query changed catalog rows")
            growth = sum(item[0] for item in final.values()) - size
            require(growth <= 0, "repeat grew stored data")
            receipt.update(passed=True, periods=counts, rows=total_rows, numeric_pointer_checks=numeric_rows,
                unique_public_sources=len(originals), initial_stored_bytes=size, repeat_growth_bytes=growth,
                immutable_original_growth_bytes=0, catalog_logical_content_unchanged=True,
                fetch_if_missing_repeat_http=0, readonly_repeat_http=0)
    finally:
        if catalog is not None:
            catalog.close()
        require(scratch.parent == control.resolve() and scratch.name.startswith("r19-"), "unexpected cleanup target")
        shutil.rmtree(scratch)
        receipt["temporary_root_restored_absent"] = not scratch.exists()
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt["source_binding_unchanged"] = binding == {str(p): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in source_files}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # A new filename is required for another attempt; old receipts stay immutable.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "source_binding"}))


if __name__ == "__main__":
    main()
