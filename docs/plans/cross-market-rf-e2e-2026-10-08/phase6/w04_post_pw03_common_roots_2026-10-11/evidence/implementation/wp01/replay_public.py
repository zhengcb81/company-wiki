"""Finite W04 replay from sealed PW03 originals; no provider/HTTP/model calls."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import quote

import yaml

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "src/company_wiki").is_dir())
sys.path.insert(0, str(REPO / "src"))
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_official_json import open_verified_projection
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeRef
from company_wiki.narrative_subject import NarrativeSubjectRef
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader, SourceRef
from company_wiki.source_catalog.resolver import SourceRequest

EVIDENCE = Path(__file__).resolve().parent
OLD_TEMP = Path("C:/Users/郑曾波/AppData/Local/Temp/mW03-ahg078jp")
RUNS = Path("C:/Users/郑曾波/Projects/revenue-forecast-audit/runs")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return canonical_json(value).encode("utf-8")


def readonly(path):
    conn = sqlite3.connect("file:" + quote(str(path).replace("\\", "/"), safe="/:") + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def clone_fixture(owned, market, refs, projection=None):
    config_path = OLD_TEMP / market / "config/source_catalog.yaml"
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    old_catalog = Path(config["catalog_dir"])
    original_db = old_catalog / "catalog.sqlite3"
    source = readonly(original_db)
    root = owned / market
    root.mkdir()
    new_catalog = root / "catalog"
    new_catalog.mkdir()
    with sqlite3.connect(new_catalog / "catalog.sqlite3") as target:
        source.backup(target)
    original_roots = {item["root_id"]: Path(item["path"]) for item in config["roots"]}
    config["catalog_dir"] = str(new_catalog)
    new_roots = {}
    for item in config["roots"]:
        new_path = root / "roots" / item["root_id"]
        new_path.mkdir(parents=True)
        new_roots[item["root_id"]] = new_path
        item["path"] = str(new_path)
    copied = []
    for ref in refs:
        locations = source.execute("SELECT * FROM locations WHERE document_id=? AND source_id=?",
            (ref["document_id"], ref["source_id"])).fetchall()
        for location in locations:
            original = original_roots[location["root_id"]] / location["relative_path"]
            if not original.is_file():
                continue
            data = original.read_bytes()
            assert len(data) == ref["byte_size"] and sha(data) == ref["content_sha256"]
            destination = new_roots[location["root_id"]] / location["relative_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            copied.append({"source_ref": ref, "original": str(original), "copied": str(destination),
                           "content_sha256": sha(data), "byte_size": len(data)})
            break
        else:
            raise AssertionError("no actual original for " + ref["content_sha256"])
    artifact = None
    if projection is not None:
        projection_sha = projection["projection_sha256"]
        (new_catalog / "projections").mkdir()
        old_projection = old_catalog / "projections" / (projection_sha + ".json")
        sealed = old_projection.read_bytes()
        assert json.loads(sealed) == projection
        (new_catalog / "projections" / old_projection.name).write_bytes(sealed)
        for row in source.execute("SELECT * FROM narrative_artifact_versions WHERE status='visible'"):
            metadata = json.loads(row["metadata_json"])
            if metadata.get("subject_binding", {}).get("subject_sha256") == projection_sha:
                artifact = {key: row[key] for key in ("artifact_version_id", "content_sha256", "byte_size", "object_key")}
                artifact["generation_sha256"] = metadata["generation_sha256"]
                original = old_catalog / row["object_key"]
                data = original.read_bytes()
                assert sha(data) == row["content_sha256"] and len(data) == row["byte_size"]
                destination = new_catalog / row["object_key"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                break
        assert artifact is not None
    source.close()
    new_config = root / "config.yaml"
    new_config.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert config_path.read_bytes() == config_bytes
    return new_config, copied, artifact


def invoke(config, operation, request, label, extra=()):
    request_bytes = encoded(request) + b"\n"
    assert len(request_bytes) <= 16384
    cmd = [sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
           "--config", str(config), "--operation", operation, *extra]
    result = subprocess.run(cmd, input=request_bytes, cwd=REPO, capture_output=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(REPO / "src"), "PYTHON_DOTENV_DISABLED": "1",
             "COMPANY_WIKI_NETWORK": "blocked", "COMPANY_WIKI_REAL_LLM": "0"})
    (EVIDENCE / (label + ".stdin.json")).write_bytes(request_bytes)
    (EVIDENCE / (label + ".stdout.json")).write_bytes(result.stdout)
    (EVIDENCE / (label + ".stderr.json")).write_bytes(result.stderr)
    assert len(result.stderr) <= 16384
    return result


def main():
    owned = Path(tempfile.mkdtemp(prefix="w4p1-"))
    print("OWNED_FIXTURE", str(owned), flush=True)
    index_path = RUNS / "pw03-20261011T010657Z-cn-688012/execution/sse/projections-index.json"
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    projection = next(item["result"]["projection"] for item in index if item["stream"] == "latest")
    all_records = [record for item in index for record in item["result"]["projection"]["records"]]
    issuers = {canonical_json(record["issuer_observed"]) for record in all_records}
    issuer_ids = {record["issuer_observed"]["provider_company_id"] for record in all_records
                  if record["issuer_observed"]["provider_company_id"] is not None}
    config, originals, artifact = clone_fixture(owned, "CN-688012", projection["parent_source_refs"], projection)
    subject_ref = {"schema_version": "narrative-subject-ref/1", "kind": "official_json",
                   "item_key": projection["projection_id"], "subject_sha256": projection["projection_sha256"]}
    reference_request = {"schema_version": "narrative-reference-request/3", "subject_ref": subject_ref,
                         "generation_sha256": artifact["generation_sha256"]}
    reference = invoke(config, "reference", reference_request, "real-reference3")
    assert reference.returncode == 0, reference.stderr
    assert len(reference.stdout) + 1 <= 16384
    ref = json.loads(reference.stdout)
    request = {"schema_version": "narrative-read-request/3", "narrative_ref": ref,
               "as_of_date": "2026-10-08", "expected_issuer": {"market": "CN", "security_id": "688012"}}
    read = invoke(config, "read", request, "real-read3")
    assert read.returncode == 0, read.stderr
    assert sha(read.stdout) == artifact["content_sha256"] and len(read.stdout) == artifact["byte_size"]
    bundle = json.loads(read.stdout)
    lineage = sha(encoded(bundle["subject_binding"]))
    assert json.loads(read.stderr)["parent_count"] == len(projection["parent_source_refs"])
    assert json.loads(read.stderr)["lineage_sha256"] == lineage
    evidence = invoke(config, "evidence-list", request, "real-evidence3", ("--limit", "1"))
    assert evidence.returncode == 0, evidence.stderr
    evidence_body = json.loads(evidence.stdout)
    assert evidence_body["subject_binding"] == bundle["subject_binding"]
    assert evidence_body["parent_source_refs"] == projection["parent_source_refs"]
    assert json.loads(evidence.stderr)["lineage_sha256"] == lineage
    failures = []
    for mutation in ("issuer", "asof", "generation", "subject", "artifact"):
        bad = deepcopy(request)
        if mutation == "issuer": bad["expected_issuer"]["security_id"] = "999999"
        elif mutation == "asof": bad["as_of_date"] = "2026-10-07"
        elif mutation == "generation": bad["narrative_ref"]["generation_sha256"] = "f" * 64
        elif mutation == "subject":
            bad["narrative_ref"]["subject_ref"]["subject_sha256"] = "f" * 64
            bad["narrative_ref"]["subject_ref"]["item_key"] = "urn:company-wiki:source-projection:sha256:" + "f" * 64
        else: bad["narrative_ref"]["artifact_sha256"] = "f" * 64
        result = invoke(config, "read", bad, "real-refusal-" + mutation)
        assert result.returncode == 2 and result.stdout == b""
        failures.append({"mutation": mutation, "receipt": json.loads(result.stderr)})
    us_path = RUNS / "pw03-20261011T010657Z-us-msft/handoffs/source-preparation.json"
    us_bytes = us_path.read_bytes()
    us = json.loads(us_bytes)
    items = [item for item in us["source_items"] if item["source_metadata"].get("fiscal_year") is None]
    us_config, us_originals, _ = clone_fixture(owned, "US-MSFT", [item["source_ref"] for item in items])
    us_results = []
    catalog = SourceCatalog(load_catalog_config(us_config))
    try:
        reader = SourceVersionReader(catalog)
        for item in items:
            ref = SourceRef(**item["source_ref"])
            candidate = reader.describe_candidate(ref)
            assert candidate["capture_ready"] is True and candidate["fiscal_year"] is None
            opened = reader.open_version(ref, purpose="source_export")
            assert sha(opened.data) == ref.content_sha256
            constraint = SourceRequest(entity=candidate["display_name"], market="US", security_id="MSFT",
                document_kind=candidate["document_kind"], fiscal_year=1900, as_of_date="2026-10-08")
            assert reader.query_local(constraint).matches == ()
            us_results.append(candidate)
    finally:
        catalog.close()
    # Count actual parent opens in a single read, using the same public source port.
    from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore, LocalNarrativeObjectStore
    catalog = SourceCatalog(load_catalog_config(config))
    artifacts = NarrativeArtifactStore.for_reading(catalog.config.database_path, LocalNarrativeObjectStore(catalog.config.catalog_dir))
    opens = []
    real_open = SourceVersionReader.open_version
    def counted(reader, ref, **kwargs):
        opens.append(ref.content_sha256)
        return real_open(reader, ref, **kwargs)
    SourceVersionReader.open_version = counted
    try:
        resolver = lambda compact: open_verified_projection(catalog, projection_id=compact.item_key,
            expected_projection_sha256=compact.subject_sha256)
        transport = NarrativeTransportReader(artifacts, SourceVersionReader(catalog), projection_ref_resolver=resolver)
        verified = transport.read(NarrativeReadRequest.from_dict(request))
        assert verified.data == read.stdout
        assert sorted(opens) == sorted(ref["content_sha256"] for ref in projection["parent_source_refs"])
    finally:
        SourceVersionReader.open_version = real_open
        artifacts.close()
        catalog.close()
    assert index_path.read_bytes() == index_bytes and us_path.read_bytes() == us_bytes
    report = {"schema_version": "w04-wp01-public-producer/1", "owned_fixture": str(owned),
              "config": str(config), "us_config": str(us_config), "reference_request": reference_request,
              "read_request": request, "selected_projection": {"sha256": projection["projection_sha256"],
              "parents": len(projection["parent_source_refs"]), "records": len(projection["records"])},
              "all_projection_records": len(all_records), "distinct_issuer_observations": len(issuers),
              "distinct_issuers_by_provider_company_id": len(issuer_ids), "distinct_provider_company_ids": sorted(issuer_ids),
              "bundle_sha256": sha(read.stdout), "bundle_bytes": len(read.stdout), "lineage_sha256": lineage,
              "source_opens_per_read": len(opens), "originals": originals + us_originals,
              "nonperiod_candidates": us_results, "failures": failures, "wire_bytes": {
                  "reference_stdin": len(encoded(reference_request))+1, "reference_stdout": len(reference.stdout),
                  "reference_stderr": len(reference.stderr), "read_stdin": len(encoded(request))+1,
                  "read_stderr": len(read.stderr), "evidence_stderr": len(evidence.stderr)},
              "provider_calls": 0, "http_calls": 0, "model_calls": 0, "cost_usd": 0,
              "pending": ["RF registered preparation and consumer integration owned by WP03", "ROOT final cross-repo G1"],
              "owned_fixture_cleanup": "retained for authorized WP03/ROOT integration; hash-verify before removal"}
    (EVIDENCE / "public-producer.json").write_bytes(encoded(report)+b"\n")
    print(json.dumps({key:report[key] for key in ("owned_fixture","config","us_config","selected_projection",
                     "all_projection_records","distinct_issuer_observations","bundle_sha256","bundle_bytes",
                     "source_opens_per_read","wire_bytes","provider_calls","http_calls","model_calls","cost_usd")},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
