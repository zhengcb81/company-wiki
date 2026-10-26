"""One-source, no-LLM diagnosis through the production PDF reading facade.

Records actual configured reader execution and selected material separately from
content quality. No SDK selection, source copies, production writes or network.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main():
    from company_wiki.automation.narrative_selector_binding import bind_narrative_selector
    from company_wiki.resource_budget import new_document_work_budget
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, PdfReadingRequest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gold", type=Path,
        help="Optional frozen source checkpoints; scores source selection, not model output")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    ref = SourceRef(**json.loads(args.source_ref.read_text(encoding="utf-8")))
    gold = None if args.gold is None else json.loads(args.gold.read_text(encoding="utf-8"))
    if gold is not None and gold.get("source_sha256") != ref.content_sha256:
        raise ValueError("gold source differs from the requested immutable source")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    sample = next(s for s in metadata["samples"] if s["sample_id"] == args.sample)
    descriptor = sample["source_metadata_observation"]
    catalog = SourceCatalog(load_catalog_config(ROOT / "config/source_catalog.yaml", project_root=ROOT))
    protected = [ROOT / "config/source_catalog.yaml", ROOT / "config/resource_budget.yaml", catalog.config.database_path]
    fingerprints = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    reading = PdfReading()
    budget = new_document_work_budget()
    started = time.monotonic()
    try:
        data = SourceVersionReader(catalog).open_version(ref, purpose="narrative_derivation").data
        recipe = reading.describe_recipe()
        parsed = reading.read(data, PdfReadingRequest(ref.source_id, ref.content_sha256,
            descriptor.get("language") or "unknown", descriptor["title"], descriptor["document_kind"]),
            selector_version="0.9.0", work_budget=budget, deadline=started + 180)
        after_read = budget.used
        selector = bind_narrative_selector(None, selector_version="0.9.0")
        selected = selector(parsed, title=descriptor["title"], existing_kind=descriptor["document_kind"], work_budget=budget)
        reading.verify_material(parsed, selected.evidence_spans)
        result = {"schema_version": "c3-material-diagnosis/1", "sample": args.sample,
            "source_ref": json.loads(args.source_ref.read_text(encoding="utf-8")),
            "reader_recipe": recipe, "parsed_unit_count": len(parsed.units),
            "parsed_layout_coverage": parsed.layout_coverage,
            "parsed_layout_diagnostics": list(parsed.layout_diagnostics),
            "work_after_read": after_read, "work_after_selection": budget.used,
            "work_limit": budget.max_work_units, "work_exhausted": budget.exhausted,
            "selected_spans": [s.to_dict() for s in selected.evidence_spans],
            "reading_context": selected.reading_context,
            "model_calls": 0, "new_raw_copies": 0,
            "elapsed_seconds": round(time.monotonic() - started, 3)}
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == fingerprints[str(p)] for p in protected)
        result["production_config_catalog_unchanged"] = True
        if gold is not None:
            from tools.document_understanding_benchmark.closed_group_support import score_facts
            from tools.document_understanding_benchmark.phase_c_observer import _oracle_reading_context

            # Caller is the actual typed selector plus the source-owned replay
            # above. Never score unvalidated third-party group declarations.
            required = [fact for fact in gold["facts"]
                        if fact.get("target_kind") == "required_business"]
            facts = score_facts(required, evidence_spans=selected.evidence_spans,
                reading_context=_oracle_reading_context(selected.reading_context),
                source_id=ref.source_id)
            result["gold_observation"] = {
                "gold_sha256": hashlib.sha256(args.gold.read_bytes()).hexdigest(),
                "facts": facts, "required_count": len(facts),
                "supported_count": sum(fact["supported"] for fact in facts),
                "missing_ids": [fact["id"] for fact in facts if not fact["supported"]],
                "scope": "source_selection_only_not_model_request_or_summary_acceptance",
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(gzip.compress(json.dumps(result, ensure_ascii=False).encode("utf-8"), mtime=0))
        print(json.dumps({"output": str(args.output), "sample": args.sample,
            "parsed_units": len(parsed.units), "selected_spans": len(selected.evidence_spans),
            "work_used": budget.used, "work_limit": budget.max_work_units,
            "elapsed_seconds": result["elapsed_seconds"], "model_calls": 0,
            "production_config_catalog_unchanged": True,
            "gold_observation": result.get("gold_observation")}, ensure_ascii=True))
    finally:
        catalog.close()


if __name__ == "__main__":
    main()
