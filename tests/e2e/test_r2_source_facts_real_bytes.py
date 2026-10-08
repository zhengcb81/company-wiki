"""Opt-in R2 public writes on isolated copies of the frozen nine originals.

The legacy catalog declarations/status are fixtures copied from the read-only
observation. This proves the current repair/registration path, not production
application, provider HTTP receipts, parsing quality or paid model quality.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_catalog.store import retire_document, restore_document


REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs/plans/narrative-evidence-pilot-2026-09-26"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@pytest.mark.real_data
@pytest.mark.e2e
def test_nine_originals_restore_facts_cli_register_and_repeat(tmp_path, record_property):
    source_root = os.environ.get("CWP_R2_SOURCE_ROOT")
    transcript_root = os.environ.get("CWP_R2_TRANSCRIPT_ROOT")
    if not source_root or not transcript_root:
        pytest.skip("explicit CWP_R2_SOURCE_ROOT and CWP_R2_TRANSCRIPT_ROOT required")
    source_root, transcript_root = Path(source_root), Path(transcript_root)
    samples = _json(REPO / "benchmarks/narrative_document_types/samples.json")["samples"]
    proposals = {x["sample_id"]: x for x in _json(REPO / "docs/implementation/g3-source-facts/metadata_proposals.json")["items"]}
    observed = {x["sample_id"]: x for x in _json(PLAN / "harness_lanes/results/r2_current_source_observation_2026-10-08.json")["sources"]}
    originals = {s["sample_id"]: (source_root if s["root_key"] == "company_raw" else transcript_root) / s["relative_path"] for s in samples}
    for sample in samples:
        original = originals[sample["sample_id"]]
        assert not getattr(original.stat(), "st_file_attributes", 0) & (0x1000 | 0x40000 | 0x400000), "do not hydrate offline originals"
        assert original.stat().st_size == sample["byte_size"]
        assert _sha(original) == sample["sha256"]
    protected = [source_root / "config/source_catalog.yaml", source_root / ".source_catalog/catalog.sqlite3"]
    protected_stat = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in protected}
    work = tmp_path / "lake"
    assert not work.exists()
    work.mkdir()
    catalog = None
    results = []
    copied_bytes = 0
    try:
        companies, unrelated = work / "companies", work / "unrelated"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("unselected original", encoding="utf-8")
        selected = {}
        for sample in samples:
            sid = sample["sample_id"]
            relative = Path(sample["relative_path"])
            destination = work / relative if sid != "S09" else companies / "Microsoft/raw/transcripts" / relative.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(originals[sid], destination)
            copied_bytes += destination.stat().st_size
            selected[sid] = destination
            if sid != "S09":
                declaration = dict(observed[sid]["declarations"]["acquisition"])
            else:
                declaration = {"company_name": "Microsoft", "market": "US", "security_id": "MSFT",
                               "document_kind": "investor_call_transcript", "fiscal_year": 2026,
                               "fiscal_period": "Q4", "language": "en", "published_date": None,
                               "provenance_status": "legacy_unverified", "provider_receipt": None}
            destination.with_name(destination.name + ".source.json").write_text(json.dumps(declaration, ensure_ascii=False), encoding="utf-8")
        config = CatalogConfig(project_root=work, catalog_dir=work / ".source_catalog",
                               roots=(RootSpec("company_raw", companies, "company_raw"),
                                      RootSpec("unselected", unrelated, "directory")))
        catalog = SourceCatalog(config)
        # Register the unrelated root once, then only the eight selected PDF groups.
        catalog.scan(root_ids={"unselected"})
        untouched = [dict(x) for x in catalog.reader.fetchall("SELECT * FROM documents")]
        untouched_root = dict(catalog.reader.fetchone("SELECT * FROM roots WHERE root_id='unselected'"))
        register_paths = {p.relative_to(companies).as_posix() for sid, p in selected.items() if sid != "S09"}
        assert catalog.register_sources(root_id="company_raw", relative_paths=register_paths).errors == 0
        reader = SourceVersionReader(catalog)
        config_path = work / "catalog.yaml"
        config_path.write_text(yaml.safe_dump({"schema_version": "1.0", "catalog_dir": str(config.catalog_dir),
                                              "roots": [{"root_id": r.root_id, "kind": r.kind, "path": str(r.path)} for r in config.roots]}), encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONIOENCODING="utf-8")
        command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(config_path)]
        for sample in samples:
            sid, sha = sample["sample_id"], sample["sha256"]
            doc_id, source_id = "urn:company-wiki:document:sha256:" + sha, "urn:company-wiki:source:sha256:" + sha
            if sid == "S09":
                relative = selected[sid].relative_to(companies).as_posix()
                assert catalog.register_sources(root_id="company_raw", relative_paths={relative}).errors == 0
                register_paths.add(relative)
            else:
                # Precisely emulate legacy row projections in this fixture only.
                old = observed[sid]["document"]
                with catalog.store.transaction() as connection:
                    connection.execute("UPDATE documents SET document_kind=?,source_type=?,published_date=? WHERE document_id=?",
                                       (old["document_kind"], old["source_type"], old["published_date"], doc_id))
            if sid in {"S01", "S02", "S03", "S04"}:
                ref = reader.query_ref(doc_id, source_id, sha)
                for audit in observed[sid]["retire_audit"]:
                    retire_document(catalog.store, document_id=doc_id, reason=audit["reason"], created_by="isolated-legacy-fixture")
                with pytest.raises(SourceReadError, match="source_not_active"):
                    reader.describe_version(ref)
                restore_reason = "actual original hash verified; legacy missing-URL control retired"
                if sid == "S01":
                    restored = subprocess.run(command + ["documents", "restore", "--document-id", doc_id, "--reason", restore_reason], env=env, capture_output=True, text=True, timeout=25)
                    assert restored.returncode == 0, restored.stderr
                else:
                    restore_document(catalog.store, document_id=doc_id, reason=restore_reason, created_by="automated-source-quality")
            ref = reader.query_ref(doc_id, source_id, sha)
            proposal = proposals[sid]
            facts = {"document_kind": sample["doc_type"] if sid not in {"S07", "S08"} else "investor_relations",
                     "market": "US" if sid == "S09" else "CN", "language": sample["language"]}
            evidence = {key: {"locator": f"source:{sid}:cover-or-body", "value": value} for key, value in facts.items()}
            for field in ("security_id", "published_date", "source_url"):
                proof = next((x for x in proposal["evidence"] if x["field"] == field and x["status"] == "verified"), None)
                if proof:
                    facts[field] = proof["observed_value"]
                    evidence[field] = {"locator": proof["locator"], "value": proof["observed_value"], "url": proof["url"]}
            if sid in {"S07", "S08", "S09"}:
                facts["published_date"] = None
                evidence["published_date"] = {"locator": f"g3:{sid}:publication-unknown", "value": None}
            if sid == "S09":
                facts.update(entity="Microsoft", security_id="MSFT", fiscal_year=2026, fiscal_period="Q4")
                for key in ("entity", "security_id", "fiscal_year", "fiscal_period"):
                    evidence[key] = {"locator": "txt:header", "value": facts[key]}
            metadata_before = catalog.reader.fetchone("SELECT metadata_json FROM documents WHERE document_id=?", (doc_id,))["metadata_json"]
            if sid == "S05":
                request = work / "facts.json"
                request.write_text(json.dumps({"source_ref": asdict(ref), "facts": facts, "evidence": evidence}), encoding="utf-8")
                outcome = subprocess.run(command + ["source-facts", "--request", str(request)], env=env, text=True, capture_output=True, timeout=25)
                assert outcome.returncode == 0, outcome.stderr
                first = json.loads(outcome.stdout)
            else:
                first = catalog.record_source_facts(ref=ref, facts=facts, evidence=evidence)
            assert first["status"] == "recorded"
            repeated = catalog.record_source_facts(ref=ref, facts=facts, evidence=evidence)
            assert repeated["status"] == "unchanged" and repeated["assertion_id"] == first["assertion_id"]
            metadata = reader.describe_version(ref)
            assert all(metadata[key] == value for key, value in facts.items() if key != "entity")
            assert catalog.reader.fetchone("SELECT metadata_json FROM documents WHERE document_id=?", (doc_id,))["metadata_json"] == metadata_before
            assert _sha(selected[sid]) == sha
            assert hashlib.sha256(reader.open_version(ref, purpose="preview").data).hexdigest() == sha
            if sid in {"S07", "S08", "S09"}:
                request = SourceRequest(entity="Microsoft" if sid == "S09" else Path(sample["relative_path"]).parts[1],
                                        market=facts["market"], security_id=facts["security_id"],
                                        document_kind=facts["document_kind"], as_of_date="2026-10-08")
                assert reader.query_local(request).matches == ()
            results.append({"sample_id": sid, "source_ref": asdict(ref), "document_kind": metadata["document_kind"],
                            "security_id": metadata["security_id"], "published_date": metadata["published_date"]})
        assert len(catalog.reader.fetchall("SELECT * FROM source_metadata_assertions")) == 9
        assert len(catalog.reader.fetchall("SELECT * FROM document_retire_audit")) == sum(len(observed[x]["retire_audit"]) for x in ("S01", "S02", "S03", "S04"))
        assert len(catalog.reader.fetchall("SELECT * FROM document_restore_audit")) == 4
        assert catalog.register_sources(root_id="company_raw", relative_paths=register_paths).errors == 0
        for result in results:
            ref = reader.query_ref(result["source_ref"]["document_id"], result["source_ref"]["source_id"], result["source_ref"]["content_sha256"])
            metadata = reader.describe_version(ref)
            assert asdict(ref) == result["source_ref"]
            assert metadata["document_kind"] == result["document_kind"]
            assert metadata["published_date"] == result["published_date"]
        assert len(catalog.reader.fetchall("SELECT * FROM source_metadata_assertions")) == 9
        assert [dict(catalog.reader.fetchone("SELECT * FROM documents WHERE document_id=?", (x["document_id"],))) for x in untouched] == untouched
        assert dict(catalog.reader.fetchone("SELECT * FROM roots WHERE root_id='unselected'")) == untouched_root
    finally:
        if catalog:
            catalog.close()
        assert work.resolve().is_relative_to(tmp_path.resolve()) and not work.is_symlink()
        shutil.rmtree(work)
        assert not work.exists()
        for sample in samples:
            assert _sha(originals[sample["sample_id"]]) == sample["sha256"]
        assert {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in protected} == protected_stat
    record_property("r2_receipt", json.dumps({"results": results, "copied_raw_bytes": copied_bytes,
                                              "assertions": 9, "tmp_restored_absent": True,
                                              "production_writes": 0, "provider_posts": 0}, ensure_ascii=True))
