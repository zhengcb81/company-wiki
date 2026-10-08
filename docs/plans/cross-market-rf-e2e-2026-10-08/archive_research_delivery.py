"""Preserve audit deliverables once by SHA; never overwrite inputs or raw sources.

Original TEMP paths are historical identifiers. archive_index.json maps them to
retained bytes, or to the already-verified immutable CWP SourceRef. This is a
delivery archive for these three companies, not a company-wiki backup/restore.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PLAN = Path(__file__).resolve().parent
TEMP = Path("C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008").resolve()
DEST = Path("C:/Users/郑曾波/Projects/revenue-forecast/output/cross-market-rf-e2e-2026-10-08").resolve()
COMPANIES = ("CN-688012", "HK-00700", "US-MSFT")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_identical_or_new(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"Refuse to overwrite a different delivery: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def main():
    # MAIN writes this only after independent change-closure reviews finish.
    selection = json.loads((PLAN / "delivery_selection.json").read_text(encoding="utf-8"))
    assert selection["status"] == "independent_reviews_sealed", "Wait for final independent change-closure reviews."
    for company, review_path in selection["independent_review_references"].items():
        assert sha(Path(review_path).read_bytes()) == selection["independent_review_sha256"][company]
    selected = selection["companies"]
    assert set(selected) == set(COMPANIES)
    for artifacts in selected.values():
        assert set(artifacts) == {"input.json", "forecast.json", "forecast.md", "snapshot.json"}
        assert all(Path(path).resolve().is_relative_to(TEMP) for path in artifacts.values())
    cwp_refs = {}
    original_source_hashes = set()
    # Scan every frozen input too: a source omitted from the latest forecast is
    # still an original. Unknown files are retained, never discarded by suffix.
    for path in TEMP.rglob("*.json"):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            continue
        if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
            continue
        for source in document["sources"]:
            if not isinstance(source, dict):
                continue
            digest = source.get("capture", {}).get("snapshot_sha256")
            if digest:
                original_source_hashes.add(digest)
    intermediate_record = json.loads((PLAN / "intermediate_selection.json").read_text(encoding="utf-8"))
    intermediates = {row["relative_path"]: row for row in intermediate_record["files"]}
    for company in COMPANIES:
        document = json.loads(Path(selected[company]["input.json"]).read_text(encoding="utf-8"))
        for source in document["sources"]:
            captured_hash = source.get("capture", {}).get("snapshot_sha256")
            if captured_hash:
                original_source_hashes.add(captured_hash)
            ref = source.get("company_wiki_trace", {}).get("source_ref")
            if isinstance(ref, dict):
                cwp_refs[ref["content_sha256"]] = ref
    producer_verification = []
    cwp = PLAN.parents[2]
    env = dict(os.environ,
               PYTHONPATH=os.pathsep.join((str(PLAN / "process_trace"), str(cwp / "src"))),
               CWP_AUDIT_PROCESS_DIR=str(PLAN / "main_processes"), PYTHONDONTWRITEBYTECODE="1")
    for digest, ref in cwp_refs.items():
        command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli",
                   "--config", str(cwp / "config/source_catalog.yaml"),
                   "--document-id", ref["document_id"], "--source-id", ref["source_id"],
                   "--content-sha256", digest, "--purpose", "filing_reuse"]
        opened = subprocess.run(command, cwd=cwp, env=env, capture_output=True, check=False, timeout=60)
        assert opened.returncode == 0, opened.stderr.decode("utf-8", errors="replace")
        assert sha(opened.stdout) == digest and len(opened.stdout) == ref["byte_size"]
        producer_verification.append({"source_ref": ref, "command": command, "returncode": 0,
                                      "verified_sha256": digest, "verified_byte_size": len(opened.stdout),
                                      "producer_receipt": json.loads(opened.stderr)})
    latest = []
    latest_paths = {}
    sys.path.insert(0, "C:/Users/郑曾波/.agents/skills/revenue-forecast/scripts")
    from revenue_backtest import validate_snapshot
    from revenue_report import validate_published_forecast
    for company in COMPANIES:
        input_document = json.loads(Path(selected[company]["input.json"]).read_text(encoding="utf-8"))
        forecast = json.loads(Path(selected[company]["forecast.json"]).read_text(encoding="utf-8"))
        snapshot = json.loads(Path(selected[company]["snapshot.json"]).read_text(encoding="utf-8"))
        # Snapshot fingerprints its full embedded result, including publication
        # metadata. result_sha256 is the forecast's economic payload fingerprint.
        # Use the actual public validators; these two different hashes must not
        # be equated by this delivery helper.
        validate_snapshot(snapshot)
        validate_published_forecast(forecast, input_document)
        assert snapshot["input_document"] == input_document
        assert snapshot["forecast_result"]["result_sha256"] == forecast["result_sha256"]
        pairs = [(Path(original), filename) for filename, original in selected[company].items()]
        for original, filename in pairs:
            data = original.read_bytes()
            digest = sha(data)
            destination = DEST / company / filename
            write_identical_or_new(destination, data)
            latest_paths[digest] = destination
            latest.append({"company": company, "file": filename, "path": str(destination),
                           "sha256": digest, "original_path": str(original)})
    rows, objects = [], {}
    for path in sorted(TEMP.rglob("*")):
        if not path.is_file():
            continue
        assert path.resolve().is_relative_to(TEMP)
        data = path.read_bytes()
        digest = sha(data)
        row = {"original_path": str(path), "relative_path": path.relative_to(TEMP).as_posix(),
               "sha256": digest, "byte_size": len(data)}
        if digest in cwp_refs:
            ref = cwp_refs[digest]
            assert len(data) == ref["byte_size"]
            row.update(storage="company_wiki_verified_raw", source_ref=ref)
        elif row["relative_path"] in intermediates and digest not in original_source_hashes:
            classification = intermediates[row["relative_path"]]
            assert classification["sha256"] == digest and classification["byte_size"] == len(data)
            row.update(storage="regenerable_intermediate_not_retained",
                       reason=classification["reason"])
        else:
            # No copies by filename: one byte-identical object serves all paths.
            target = latest_paths.get(digest, DEST / "objects" / digest[:2] / digest)
            write_identical_or_new(target, data)
            assert sha(target.read_bytes()) == digest
            row.update(storage="retained_object", archive_path=str(target))
            objects[digest] = len(data)
        rows.append(row)
    record = {"schema_version": "1.0", "task": PLAN.name, "original_temp_root": str(TEMP),
              "durable_output_root": str(DEST), "artifacts": rows, "latest_deliverables": latest,
              "unique_object_bytes": sum(objects.values()), "unique_object_count": len(objects),
              "temp_logical_bytes": sum(row["byte_size"] for row in rows),
              "cwp_raw_bytes_not_duplicated": sum(row["byte_size"] for row in rows if row["storage"] == "company_wiki_verified_raw"),
              "regenerable_intermediate_bytes_not_retained": sum(row["byte_size"] for row in rows if row["storage"] == "regenerable_intermediate_not_retained"),
              "raw_cwp_refs": list(cwp_refs.values()), "source_originals_deleted": False,
              "current_producer_verification": producer_verification,
              "temp_cleanup": "not_performed_by_this_script",
              "historical_path_resolution": "Use this index. Never rewrite historical input, snapshot, receipt or execution manifest bytes."}
    encoded = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_identical_or_new(DEST / "archive_index.json", encoded)
    write_identical_or_new(PLAN / "delivery_archive_index.json", encoded)
    print(json.dumps({key: record[key] for key in ("durable_output_root", "unique_object_bytes", "unique_object_count", "temp_logical_bytes", "cwp_raw_bytes_not_duplicated")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
