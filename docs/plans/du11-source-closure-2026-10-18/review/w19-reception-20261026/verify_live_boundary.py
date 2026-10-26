"""Finite $0 public-provider acceptance in a fully removed private test root.

Uses real FF transport/CWP CLI/Sina provider; no fixture command injection.
Two requests reserve <=8MiB and <=90s total acquisition, below card limits.
Only existing configured identity records are copied to the test catalog.
"""
import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwp-root", type=Path, required=True)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("use a new receipt filename")
    control = Path(__file__).resolve().parents[5]
    cwp, ff = args.cwp_root.resolve(), args.ff_root.resolve()
    sys.path[:0] = [str(cwp / "src"), str(cwp / "tests"), str(ff / "scripts"), str(Path(__file__).parent)]
    import ff_financial_statements as client
    from financial_statements.test_offline_e2e_full import _wiki_root
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.security_identity import SecurityMasterStore, load_identity_master
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
    from verify_offline_boundary import snapshot, stable_files, database_content, require

    config = load_catalog_config(control / "config/source_catalog.yaml", project_root=control)
    master = load_identity_master(SecurityMasterStore(config.catalog_dir / "security_master"), market="CN")
    identities = tuple(r for r in master.records if r.market == "CN" and r.security_id in {"688012", "600036"})
    require(len(identities) == 2, "configured identity snapshots do not contain both companies")
    protected_paths = [control / "config/source_catalog.yaml", config.database_path]
    protected = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths}
    code_paths = [*sorted((cwp / "src/company_wiki/source_catalog/financial_statements").glob("*.py")),
                  ff / "scripts/ff_financial_statements.py"]
    binding = {str(p): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in code_paths}
    scratch = Path(tempfile.mkdtemp(prefix="r19l-", dir=control)).resolve()
    start = time.monotonic()
    receipt = {"schema_version": "w19-live-ff-cwp-sina/1", "passed": False, "companies": [],
        "source_binding": binding, "new_paid_calls": 0, "cost_usd": "0.00"}
    catalog = None
    try:
        wiki = _wiki_root(scratch)
        SecurityMasterStore(wiki / ".source_catalog/security_master").write_market("CN", identities,
            retrieved_at=master.snapshots["CN"]["retrieved_at"], sources=("existing-configured-snapshot",))
        connection = scratch / "connection.json"
        connection.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(wiki)}), encoding="utf-8")
        with patch.dict(os.environ, {"PYTHONPATH": str(cwp / "src"), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}):
            for code, statements in [("688012", ["income_statement", "balance_sheet", "cash_flow"]),
                                     ("600036", ["income_statement"])]:
                request = {"schema_version": "financial-statements-request/1", "company_query": code,
                    "market": "CN", "statements": statements, "report_types": ["annual"],
                    "period_end_from": "2025-01-01", "period_end_to": "2025-12-31",
                    "knowledge_mode": "current_snapshot", "as_of_date": "2026-10-26",
                    "intent": "fetch_if_missing", "acquisition_limits": {
                        "max_bytes": 4 * 1024 * 1024, "timeout_seconds": 45, "max_cost_usd": "0.00"}}
                response = client.fetch_statements(config_path=connection, request=request, timeout_seconds=65)
                observed = {"code": code, "status": response["status"], "usage": response["usage"], "statements": []}
                receipt["companies"].append(observed)
                require(response["status"] == "complete", "live provider did not provide complete sample; no retry")
                catalog = SourceCatalog(load_catalog_config(wiki / "config/source_catalog.yaml", project_root=wiki))
                reader = SourceVersionReader(catalog)
                for statement in response["statements"]:
                    reports = statement["reports"]
                    require(len(reports) == 1 and reports[0]["period_end"] == "2025-12-31", "annual period misalignment")
                    report = reports[0]
                    ref = SourceRef(**report["source_ref"])
                    raw = reader.open_version(ref, purpose="source_export").data
                    require(len(raw) == ref.byte_size, "invalid direct public ref")
                    observed["statements"].append({"statement_type": statement["statement_type"],
                        "source_ref": asdict(ref), "rows": len(report["rows"]), "currency": report["currency"],
                        "consolidation": report["consolidation"]})
                    if code == "688012":
                        expected = json.loads((Path(__file__).parent / "official-six-values-v1.json").read_text(encoding="utf-8"))
                        for check in expected["checks"]:
                            if check["statement_type"] == statement["statement_type"]:
                                actual = next(r for r in report["rows"] if r["provider_field"] == check["provider_field"])
                                require(Decimal(actual["value_decimal"]) == Decimal(check["expected_official"]), "live restatement differs from frozen official value")
                catalog.close()
                catalog = None
                database_before = database_content(wiki)
                before = snapshot(wiki)
                second = client.fetch_statements(config_path=connection, request=request, timeout_seconds=65)
                require(second["status"] == "complete" and second["usage"]["http_requests"] == 0, "repeat did not reuse")
                after = snapshot(wiki)
                require(stable_files(before) == stable_files(after) and database_before == database_content(wiki), "repeat changed stored content")
                observed["repeat_http"] = second["usage"]["http_requests"]
            actual_requests = sum(c["usage"]["http_requests"] for c in receipt["companies"])
            actual_bytes = sum(c["usage"]["response_bytes"] for c in receipt["companies"])
            require(actual_requests <= 50 and actual_bytes <= 8 * 1024 * 1024, "card budget exceeded")
            receipt.update(passed=True, http_requests=actual_requests, response_bytes=actual_bytes,
                max_acquisition_reservations_bytes=8*1024*1024, max_acquisition_seconds=90)
    finally:
        if catalog is not None:
            catalog.close()
        require(scratch.parent == control.resolve() and scratch.name.startswith("r19l-"), "unexpected cleanup target")
        shutil.rmtree(scratch)
        receipt.update(temporary_root_restored_absent=not scratch.exists(), elapsed_seconds=time.monotonic()-start,
            production_config_catalog_unchanged=protected == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths},
            source_binding_unchanged=binding == {str(p): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in code_paths})
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in {"source_binding", "companies"}}))


if __name__ == "__main__":
    main()
