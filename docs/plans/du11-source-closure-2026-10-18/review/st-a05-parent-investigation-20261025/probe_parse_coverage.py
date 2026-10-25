"""Freeze actual parser dimensions for the next local-flow TDD node."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from replay_current import load

HERE = Path(__file__).resolve().parent


def main():
    output = HERE / "parser-dimensions-next-node.json"
    if output.exists():
        raise FileExistsError(output)
    previous = load("existing_source_locations", HERE / "probe_real_structure.py")
    ref = SourceRef(**json.loads(previous.SELECTION.read_text(encoding="utf-8"))["source_ref"])
    config = load_catalog_config(previous.CONFIG, project_root=previous.PROJECT)
    protected = [previous.CONFIG, config.database_path]
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    before = {str(path): sha(path) for path in protected}
    budget = new_document_work_budget()
    catalog = SourceCatalog(config)
    try:
        raw = SourceVersionReader(catalog).open_version(ref, purpose="preview")
        if hashlib.sha256(raw.data).hexdigest() != ref.content_sha256:
            raise RuntimeError("original SHA mismatch")
        parsed = parse_pdf_bytes(raw.data, source_id=ref.source_id,
            source_sha256=ref.content_sha256, language="zh", selector_version="0.9.0", work_budget=budget)
        if catalog._store is not None:
            raise RuntimeError("probe constructed mutable store")
    finally:
        catalog.close()
    if before != {str(path): sha(path) for path in protected}:
        raise RuntimeError("protected config/catalog changed")
    record = {"schema_version": "native-parser-dimensions-observation/1", "source_sha256": ref.content_sha256,
        "page_count": parsed.page_count, "pages_read": parsed.pages_read, "errors": list(parsed.errors),
        "opaque_pages": list(parsed.opaque_pages), "table_scan_pages": list(parsed.table_scan_pages),
        "deferred_table_pages": list(parsed.deferred_table_pages), "overall_coverage_complete": parsed.coverage_complete,
        "local_13_14_unit_count": sum(u.coordinates.page_number in (13, 14) for u in parsed.units),
        "local_13_14_column_values": sorted({str(u.metadata.get("reading_layout", {}).get("layout", {}).get("column"))
            for u in parsed.units if u.coordinates.page_number in (13, 14)}),
        "work_used": budget.used, "work_limit": budget.max_work_units,
        "protected_unchanged": True, "model_calls": 0, "downloads": 0, "raw_copies": 0,
        "meaning": "Observed parse dimensions only; does not prove local flow or a single-column lane"}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in record.items() if k not in {"table_scan_pages", "deferred_table_pages"}}, ensure_ascii=True))


if __name__ == "__main__":
    main()
