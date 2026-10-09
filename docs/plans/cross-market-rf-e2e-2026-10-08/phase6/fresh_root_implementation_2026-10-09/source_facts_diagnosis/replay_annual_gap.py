"""Offline W06 diagnostic; real originals are read, only own TEMP catalog is written."""

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(PROJECT / "src"))

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.dayu_fiscal_metadata import _inline_date
import company_wiki.source_catalog.dayu_fiscal_metadata as fiscal
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.service import SourceCatalog


def identity(path):
    status = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "byte_size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
    }


def main():
    sealed = Path("C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/US-MSFT")
    original_config = load_catalog_config(
        sealed / "config/source_catalog.yaml", project_root=sealed
    )
    protected = [
        original_config.database_path,
        sealed / "config/source_catalog.yaml",
        PROJECT / "config/source_catalog.yaml",
    ]
    replay = json.loads((Path(__file__).parent / "us_annual_candidate_replay.json").read_text(encoding="utf-8"))
    protected.extend(Path(path) for row in replay["candidate_observations"] for path in row.get("locations", []))
    before = {str(path): identity(path) for path in protected}
    results = []
    temp_roots = []
    for label, legacy_alias, candidate_limit in (
        ("current_product", False, 16),
        ("diagnostic_legacy_alias_only", True, 16),
        ("diagnostic_alias_and_separate_discovery_headroom", True, 64),
    ):
        with tempfile.TemporaryDirectory(prefix="w06-annual-proof-") as task_root:
            owned = Path(task_root).resolve()
            temp_roots.append(str(owned))
            catalog_dir = owned / "catalog"
            catalog_dir.mkdir()
            source = sqlite3.connect(original_config.database_path.resolve().as_uri() + "?mode=ro", uri=True)
            destination = sqlite3.connect(catalog_dir / "catalog.sqlite3")
            source.backup(destination)
            destination.close()
            source.close()
            shutil.copytree(sealed / "catalog/security_master", catalog_dir / "security_master")
            config = replace(
                original_config, project_root=owned, catalog_dir=catalog_dir,
                roots=tuple(replace(root, read_only=True) for root in original_config.roots),
            )
            catalog = SourceCatalog(config)
            request = SourceRequest(
                entity="MICROSOFT CORP", market="US", security_id="MSFT",
                document_kind="annual_report", fiscal_year=2026, form_type="10-K",
                as_of_date="2026-10-08", mode="exact", allow_download=False,
            )
            if legacy_alias:
                def counterfactual_inline_date(text, transform):
                    mapped = "date-monthname-day-year-en" if transform.split(":")[-1] == "datemonthdayyearen" else transform
                    return _inline_date(text, mapped)
                fiscal._inline_date = counterfactual_inline_date
            started = time.monotonic()
            try:
                outcome = prepare_local_source(
                    catalog, request,
                    limits=LocalPrepareLimits(max_candidates=candidate_limit, timeout_seconds=90),
                )
                results.append({"label": label, "production_code_changed": False,
                                "counterfactual": legacy_alias, "max_candidates": candidate_limit,
                                "elapsed_seconds": round(time.monotonic()-started, 3), "result": outcome})
            finally:
                fiscal._inline_date = _inline_date
                catalog.close()
                if catalog._store is not None:
                    catalog._store.connection.close()
            if owned.parent != Path(tempfile.gettempdir()).resolve() or not owned.name.startswith("w06-annual-proof-") or owned.is_symlink():
                raise RuntimeError("owned TEMP boundary mismatch")
    after = {str(path): identity(path) for path in protected}
    receipt = {
        "schema_version": "w06-actual-annual-gap-replay/1", "results": results,
        "protected_unchanged": before == after,
        "protected_before": before, "protected_after": after,
        "temp_roots": temp_roots, "temp_absent_after": all(not Path(path).exists() for path in temp_roots),
        "production_code_changed": False, "model_requests": 0, "network_requests": 0,
        "download_events": 0, "original_writes": 0,
        "interpretation": "Counterfactual cases diagnose causal stages; they are not an implemented or accepted GREEN fix.",
    }
    (Path(__file__).parent / "annual_gap_replay.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key not in ("protected_before", "protected_after")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
