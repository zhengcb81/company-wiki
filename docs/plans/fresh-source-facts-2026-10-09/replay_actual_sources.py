"""Offline W06 replay; preexisting catalogs/config/originals are read-only."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "src"))

DIAG = Path(
    "C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/fresh_root_implementation_2026-10-09/source_facts_diagnosis"
)
SEALED = Path("C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/US-MSFT")
network = []


def no_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        network.append(event)
        raise RuntimeError("W06 offline replay forbids network")


sys.addaudithook(no_network)


def snapshot(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    return {
        "sha256": digest.hexdigest(),
        "bytes": after.st_size,
        "mtime_ns": after.st_mtime_ns,
    }


def main(receipt_name="actual_source_receipt.json"):
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.dayu_fiscal_metadata import extract_sec_primary
    from company_wiki.source_catalog.local_inventory import (
        LocalPrepareLimits,
        LocalReadBudget,
    )
    from company_wiki.source_catalog.resolver import SourceRequest
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceVersionReader, SourceRef

    config = load_catalog_config(
        SEALED / "config/source_catalog.yaml", project_root=SEALED
    )
    annual = json.loads(
        (DIAG / "us_annual_candidate_replay.json").read_text(encoding="utf-8")
    )
    titles = json.loads(
        (DIAG / "sec_title_observations.json").read_text(encoding="utf-8")
    )
    paths = {
        config.database_path,
        SEALED / "config/source_catalog.yaml",
        Path("C:/Users/郑曾波/Projects/company-wiki/config/source_catalog.yaml"),
    }
    paths.update(
        Path(path)
        for row in annual["candidate_observations"]
        for path in row["locations"]
    )
    # Include all original/title test locations and their cache facts in the protected receipt.
    with sqlite3.connect(config.database_path.as_uri() + "?mode=ro", uri=True) as db:
        roots = {r.root_id: r.path for r in config.roots}
        for record in titles:
            for root_id, relative in db.execute(
                "SELECT root_id,relative_path FROM locations WHERE source_id=?",
                (record["source_ref"]["source_id"],),
            ):
                path = roots[root_id] / relative
                if path.exists():
                    paths.add(path)
    for path in tuple(paths):
        metadata = path.with_name("meta.json")
        if metadata.is_file():
            paths.add(metadata)
    before = {str(path): snapshot(path) for path in sorted(paths)}
    roots = []
    title_results = []
    with tempfile.TemporaryDirectory(prefix="w06-actual-green-") as folder:
        owned = Path(folder).resolve()
        roots.append(str(owned))
        catalog_dir = owned / "catalog"
        catalog_dir.mkdir()
        assert (
            owned.parent == Path(tempfile.gettempdir()).resolve()
            and owned.name.startswith("w06-actual-green-")
            and not owned.is_symlink()
        )
        src = sqlite3.connect(config.database_path.as_uri() + "?mode=ro", uri=True)
        dst = sqlite3.connect(catalog_dir / "catalog.sqlite3")
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        shutil.copytree(
            SEALED / "catalog/security_master", catalog_dir / "security_master"
        )
        cat = SourceCatalog(
            replace(
                config,
                project_root=owned,
                catalog_dir=catalog_dir,
                roots=tuple(replace(r, read_only=True) for r in config.roots),
            )
        )
        try:
            request = SourceRequest(
                entity="MICROSOFT CORP",
                market="US",
                security_id="MSFT",
                document_kind="annual_report",
                fiscal_year=2026,
                form_type="10-K",
                as_of_date="2026-10-08",
                mode="exact",
                allow_download=False,
            )
            limits = LocalPrepareLimits()
            budget = LocalReadBudget(limits)
            start = time.monotonic()
            from company_wiki.source_catalog.local_reconcile import (
                _prepare_local_source,
            )

            result = _prepare_local_source(cat, request, _budget=budget)
            elapsed = time.monotonic() - start
            assert (
                result["status"] == "not_found"
                and result["reason"] == "no_matching_local_period"
                and not result["blocks_download"]
            ), result
            assert result["download_events"] == 0 and budget.discovery_groups > 16
            legacy = []
            for record in annual["candidate_observations"]:
                if record["source_ref"]["content_sha256"] in {
                    "d8c69513cd820ecdfa3b22decf2672591ced88996188c218d3ffa1439b6b528f",
                    "0cdddd9409d55b933bb5b9d3f8cc3fbb3c7f3390a531406aea2b1a0ba4bbf999",
                }:
                    facts = extract_sec_primary(
                        Path(record["locations"][0]).read_bytes()
                    )
                    assert (
                        facts["fiscal_year"] in {2021, 2022}
                        and facts["report_date"] == f"{facts['fiscal_year']}-06-30"
                    )
                    legacy.append(
                        {
                            "sha256": record["source_ref"]["content_sha256"],
                            "facts": facts,
                        }
                    )
            reader = SourceVersionReader(cat)
            for record in titles:
                ref = SourceRef(**record["source_ref"])
                raw = reader.open_version(ref, purpose="source_export").data
                facts = extract_sec_primary(raw)
                patch = {"title": facts["title"], "form_type": facts["form_type"]}
                assert patch == {"title": "10-Q", "form_type": "10-Q"}
                capture = cat.reader.fetchone(
                    "SELECT metadata_json FROM documents WHERE document_id=?",
                    (ref.document_id,),
                )[0]
                evidence = {
                    k: {
                        "locator": "html:/html/head/title"
                        if k == "title"
                        else "primary-dei:/DocumentType",
                        "value": v,
                        "content_sha256": ref.content_sha256,
                    }
                    for k, v in patch.items()
                }
                first = cat.record_source_facts(ref=ref, facts=patch, evidence=evidence)
                second = cat.record_source_facts(
                    ref=ref, facts=patch, evidence=evidence
                )
                manifest = reader.describe_version(ref)
                assert (manifest["title"], manifest["form_type"]) == (
                    "10-Q",
                    "10-Q",
                ) and second["status"] == "unchanged"
                assert (
                    cat.reader.fetchone(
                        "SELECT metadata_json FROM documents WHERE document_id=?",
                        (ref.document_id,),
                    )[0]
                    == capture
                )
                title_results.append(
                    {
                        "source_ref": record["source_ref"],
                        "before_title": record["manifest"]["title"],
                        "after_title": manifest["title"],
                        "capture_unchanged": True,
                        "idempotent": True,
                        "assertion_id": first["assertion_id"],
                    }
                )
        finally:
            cat.close()
    after = {str(path): snapshot(path) for path in sorted(paths)}
    receipt = {
        "schema_version": "w06-actual-green/1",
        "annual_result": result,
        "elapsed_seconds": round(elapsed, 3),
        "limits": {
            "max_candidates": limits.max_candidates,
            "max_discovery_groups": limits.max_discovery_groups,
            "max_discovery_entries": limits.max_discovery_entries,
            "max_bytes": limits.max_bytes,
            "timeout_seconds": limits.timeout_seconds,
        },
        "observed": {
            "raw_candidate_reads": budget.candidates,
            "read_bytes": budget.bytes_read,
            "metadata_groups": budget.discovery_groups,
            "directory_entries": budget.discovery_entries,
        },
        "legacy_dei": legacy,
        "title_results": title_results,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        "owned_temps": roots,
        "temps_absent_after": all(not Path(x).exists() for x in roots),
        "network_attempts": network,
        "network_requests": 0,
        "model_requests": 0,
        "download_events": 0,
        "original_writes": 0,
        "scope": "Known registered MSFT originals and finite configured issuer directories; not universal arbitrary Dropbox absence.",
    }
    assert (
        receipt["protected_unchanged"] and receipt["temps_absent_after"] and not network
    )
    if Path(receipt_name).name != receipt_name:
        raise ValueError("receipt_name must remain in this independent PWF")
    out = Path(__file__).with_name(receipt_name)
    out.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in receipt.items()
                if k
                not in {
                    "protected_before",
                    "protected_after",
                    "legacy_dei",
                    "title_results",
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-name", default="actual_source_receipt.json")
    main(parser.parse_args().receipt_name)
