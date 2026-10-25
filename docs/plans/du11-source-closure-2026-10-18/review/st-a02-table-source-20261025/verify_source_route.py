"""Read a frozen SourceRef and compare old RF claims with verified PDF pages.

This investigation does not download, call a model, write the catalog, or
assert that a new RF attempt or summary passed. Output creation is exclusive.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pymupdf

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def normalized(text: str) -> str:
    return " ".join(text.split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--rf-input", type=Path, required=True)
    parser.add_argument("--rf-result", type=Path, required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--claim-ids", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    pages = sorted({int(value) for value in args.pages.split(",")})
    if not pages or len(pages) > 8 or min(pages) < 1:
        raise ValueError("one to eight explicit physical pages required")
    selection_bytes = args.selection.read_bytes()
    selection = json.loads(selection_bytes)
    ref = SourceRef(**selection["source_ref"])
    config = load_catalog_config(args.config, project_root=args.project_root)
    protected_paths = (args.config, config.database_path)
    before = {str(p): sha(p.read_bytes()) for p in protected_paths}
    catalog = SourceCatalog(config)
    try:
        reader = SourceVersionReader(catalog)
        description = reader.describe_version(ref)
        verified = reader.open_version(ref, purpose="preview")
        if sha(verified.data) != ref.content_sha256:
            raise RuntimeError("verified bytes do not match the frozen source")
        parsed = parse_pdf_bytes(
            verified.data, source_id=ref.source_id,
            source_sha256=ref.content_sha256, selector_version="0.9.0",
            table_pages=pages,
        )
        with pymupdf.open(stream=verified.data, filetype="pdf") as document:
            page_text = {page: document[page - 1].get_text() for page in pages}
        if catalog._store is not None:
            raise RuntimeError("investigation constructed a writable catalog store")
    finally:
        catalog.close()
    after = {str(p): sha(p.read_bytes()) for p in protected_paths}
    if before != after:
        raise RuntimeError("source config/catalog changed during read-only investigation")
    input_bytes, result_bytes = args.rf_input.read_bytes(), args.rf_result.read_bytes()
    rf_input, rf_result = json.loads(input_bytes), json.loads(result_bytes)
    canonical_input_sha = sha(json.dumps(
        rf_input, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))
    claims = {row["claim_id"]: row for row in rf_input["evidence_claims"]}
    requested_claims = []
    for claim_id in args.claim_ids.split(","):
        row = claims[claim_id]
        excerpt = row["excerpt"]
        matching_pages = [page for page, text in page_text.items()
                          if normalized(excerpt) in normalized(text)]
        requested_claims.append({
            "claim_id": claim_id, "source_id_matches": row["source_id"] == ref.source_id,
            "snapshot_sha_matches": row["content_sha256"] == ref.content_sha256,
            "excerpt_sha_matches": sha(excerpt.encode("utf-8")) == row["excerpt_sha256"],
            "complete_excerpt_found_on_verified_pages": matching_pages,
            "declared_locator": row["locator"],
            "declared_extracted_value": row.get("extracted_value"),
        })
    table_rows = [{
        "coordinates": asdict(unit.coordinates),
        "table_headers": unit.metadata.get("table_headers"),
        "row_cells": unit.metadata.get("row_cells"),
    } for unit in parsed.units
        if unit.unit_kind == "pdf_table_row" and unit.coordinates.page_number in pages]
    receipt = {
        "schema_version": "source-route-investigation/1",
        "status": "OBSERVED_OLD_RF_ONLY_CURRENT_ATTEMPT_STILL_OPEN",
        "selection_sha256": sha(selection_bytes), "source_ref": asdict(ref),
        "source_description": description, "verified_source_sha256": sha(verified.data),
        "pages": pages, "structured_table_rows": table_rows,
        "page_context": {str(p): page_text[p] for p in pages},
        "old_input_file_sha256": sha(input_bytes), "old_result_file_sha256": sha(result_bytes),
        "old_input_canonical_sha256": canonical_input_sha,
        "old_result_input_sha256": rf_result.get("input_sha256"),
        "old_result_input_binding_matches": canonical_input_sha == rf_result.get("input_sha256"),
        "old_history_output_matches_input": rf_result.get("historical_revenue") == rf_input.get("historical_revenue"),
        "old_base_revenue": rf_result.get("base_revenue"), "old_claim_observations": requested_claims,
        "config_catalog_unchanged": before == after, "catalog_writer_constructed": False,
        "new_model_requests": 0, "new_downloads": 0, "new_financial_api_requests": 0,
        "current_rf_attempt_validated": False, "summary_response_reviewed": False,
    }
    payload = json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    if len(payload) > 256 * 1024:
        raise RuntimeError("bounded investigation output exceeds 256 KiB")
    with args.out.open("xb") as stream:
        stream.write(payload)
    print(json.dumps({
        "receipt_sha256": sha(payload), "receipt_bytes": len(payload),
        "structured_rows": len(table_rows), "claims": requested_claims,
        "old_input_binding_matches": receipt["old_result_input_binding_matches"],
        "config_catalog_unchanged": True, "current_rf_attempt_validated": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
