"""Read-only real MSFT original -> selected index -> query -> exact raw replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sys

from company_wiki.automation.narrative_formats import parser_component
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_SELECTOR_NAME, NARRATIVE_SELECTOR_VERSION,
    parse_transcript_text, select_narrative_evidence, verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION, NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
    NarrativeEvidenceSearch, NarrativeEvidenceResolver,
)
from company_wiki.source_catalog.transcript_text_extract import extract_transcript_material


EXPECTED_SHA = "bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656"


def main() -> None:
    # Editable installations may point to MAIN; this check requires the caller
    # to bind PYTHONPATH to this exact worktree's src before any replay.
    worktree = Path(__file__).resolve().parents[3]
    assert Path(sys.modules[NarrativeEvidenceResolver.__module__].__file__).resolve().is_relative_to(worktree / "src")
    args = argparse.ArgumentParser()
    args.add_argument("--raw", type=Path, required=True)
    args.add_argument("--output", type=Path, required=True)
    options = args.parse_args()
    raw = options.raw.resolve(strict=True)
    before_stat = raw.stat()
    original = raw.read_bytes()
    assert len(original) == 273436
    assert hashlib.sha256(original).hexdigest() == EXPECTED_SHA
    env_before = {key: os.environ.get(key) for key in ("TEMP", "TMP")}
    with tempfile.TemporaryDirectory(prefix="cwW05CompatReal-") as tmp:
        owned_temp = Path(tmp)
        try:
            os.environ["TEMP"] = str(owned_temp)
            os.environ["TMP"] = str(owned_temp)
            material = extract_transcript_material(original, mime_type="text/html")
            material.verify(original)
            parser_name, version = parser_component("text/html", "transcript")
            assert version == "0.2.0"
            parsed = parse_transcript_text(
                material.text_utf8, source_id=material.original_source_id,
                source_sha256=material.original_sha256, parser_version=version,
                language="en",
            )
            assert parsed.coverage_complete and not parsed.errors
            first_line = min(unit.metadata["line_start"] for unit in parsed.units)
            last_line = max(unit.metadata["line_end"] for unit in parsed.units)
            assert (first_line, last_line) == (90, 414)
            assert len(parsed.units) == 515
            for unit in parsed.units:
                lines = material.lines[unit.metadata["line_start"] - 1 : unit.metadata["line_end"]]
                assert lines and all(0 <= line.source_byte_start < line.source_byte_end <= len(original) for line in lines)
            selected = select_narrative_evidence(
                parsed, title="MICROSOFT CORP official earnings call",
                existing_kind="investor_call_transcript",
            )
            assert len(selected.evidence_spans) == 41
            verified, failed = verify_transcript_evidence_spans(
                material.text_utf8, source_id=material.original_source_id,
                source_sha256=material.original_sha256, evidence_spans=selected.evidence_spans,
                language="en",
            )
            assert len(verified) == 41 and not failed
            record = {
                "title": "MICROSOFT CORP official earnings call",
                "selection_status": selected.status,
                "coverage_complete": selected.coverage_complete,
                "summary_input": selected.summary_input(),
                "replay_contract": {
                    "schema_version": NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
                    "source_format": "transcript_html", "language": "en",
                    "existing_kind": "investor_call_transcript",
                    "parser_name": parser_name, "parser_version": version,
                    "parser_options": {}, "selector_name": NARRATIVE_SELECTOR_NAME,
                    "selector_version": NARRATIVE_SELECTOR_VERSION,
                    "max_selected": selected.selection_limit,
                },
            }
            bundle = {"schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION, "sources": [record]}
            search = NarrativeEvidenceSearch(bundle)
            hits = search.search("models")
            assert hits
            resolver = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={material.original_source_id: raw})
            for hit in hits:
                replayed_hit = resolver.resolve(hit)
                assert replayed_hit.locators == hit.locators
                assert "model" in replayed_hit.raw_text.casefold()
            span_ids = set()
            group_count = 0
            for row in record["summary_input"]["evidence"]:
                resolved = resolver.resolve_group(source_id=material.original_source_id,
                                                 evidence_group_id=row.get("context_group_id") or row["evidence_id"])
                assert resolved.raw_text == row["raw_text"]
                assert resolved.raw_text_sha256 == row["raw_text_sha256"]
                assert resolved.parser_version == version
                assert resolved.locators == tuple(row["locators"])
                span_ids.update(resolved.evidence_ids)
                group_count += 1
            assert span_ids == {span.span_id for span in selected.evidence_spans}
            report = {
                "status": "pass", "raw_sha256": EXPECTED_SHA,
                "raw_bytes": len(original), "extracted_lines": len(material.lines),
                "body_first_line": first_line, "body_last_line": last_line,
                "parsed_units": len(parsed.units), "selected_spans": len(selected.evidence_spans),
                "verified_spans": len(verified), "replayed_spans": len(span_ids),
                "replayed_groups": group_count, "indexed_groups": search.indexed_group_count,
                "query": "models", "query_hits_resolved": len(hits),
                "parser_version": version, "selector_version": NARRATIVE_SELECTOR_VERSION,
                "external_provider_calls": 0, "model_calls": 0, "model_cost_usd": 0,
            }
            (owned_temp / "verification.json").write_text(json.dumps(report), encoding="utf-8")
        finally:
            for key, value in env_before.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    assert not owned_temp.exists()
    assert env_before == {key: os.environ.get(key) for key in env_before}
    assert raw.stat().st_mtime_ns == before_stat.st_mtime_ns
    assert raw.read_bytes() == original
    report.update(raw_sha_unchanged=True, raw_mtime_unchanged=True,
                  owned_temp_restored=True, temp_environment_restored=True)
    options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
