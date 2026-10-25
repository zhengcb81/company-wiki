"""Read-only local coverage/geometry probe; no model, download or raw copy."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.document_understanding.narrative_continuity import NativeSourceContext
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.narrative_reading import _understand
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    label = sys.argv[1]
    if not label.isalnum():
        raise ValueError("fresh alphanumeric label required")
    output = HERE / (label + ".json")
    if output.exists():
        raise FileExistsError(output)
    selected = json.loads((HERE.parent / "st-a05-parent-investigation-20261025/attempt02/selection.json").read_text(encoding="utf-8"))
    ref = SourceRef(**selected["source_ref"])
    project = ROOT / ".planning/shared-reading-production/r1-holdout-20261021/CN-603259/wiki"
    config_file = project / "config/source_catalog.yaml"
    config = load_catalog_config(config_file, project_root=project)
    protected = {str(p): digest(p) for p in [config_file, config.database_path]}
    source = {str(p.relative_to(ROOT)): digest(p) for p in (ROOT / "src/company_wiki").rglob("*.py")}
    catalog = SourceCatalog(config)
    budget = new_document_work_budget()
    physical_calls = []
    original_page = NativeSourceContext.page_neighbour

    def page(context, left, right, **kwargs):
        result = original_page(context, left, right, **kwargs)
        a, b = context.observations.get(left), context.observations.get(right)
        if a is not None and b is not None and a.page == 13 and b.page == 14:
            physical_calls.append({"left": left, "right": right, "proof": result,
                "endpoint_frames": [a.frame, b.frame], "endpoint_columns": [a.column, b.column]})
        return result

    try:
        verified = SourceVersionReader(catalog).open_version(ref, purpose="preview")
        if sha256(verified.data).hexdigest() != ref.content_sha256:
            raise ValueError("immutable original SHA mismatch")
        parsed = parse_pdf_bytes(verified.data, source_id=ref.source_id,
            source_sha256=ref.content_sha256, language="zh", selector_version="0.9.0", work_budget=budget)
        parse_work = budget.used
        contexts = {}
        NativeSourceContext.page_neighbour = page
        pipeline = _understand(parsed, title="药明康德2025年度报告", kind="annual_report",
            mime_type="application/pdf", work_budget=budget, _native_contexts=contexts)
        context = contexts[ref.source_id]
        units = [u for u in pipeline["observation"]["units"] if u["page"] in (13, 14)]
        ids = {u["unit_id"] for u in units}
        result = {"schema_version": "local-native-source-probe/1", "source_ref": selected["source_ref"],
            "coverage_complete": parsed.coverage_complete,
            "native_text_coverage": dict(parsed.native_text_coverage or {}),
            "geometry_deferred_count": len(parsed.deferred_table_pages),
            "context_positive_pages": sorted(context.native_text_pages),
            "context_diagnostics": dict(context.diagnostics),
            "physical_calls_13_14": physical_calls,
            "local_units": [{"unit_id": u["unit_id"], "page": u["page"], "ordinal": u["ordinal"],
                "kind": u["kind"], "text_prefix": u["text"][:60], "layout": u["layout"],
                "table_region": u["hints"].get("table_region")} for u in units],
            "local_layout_hints": [h for h in pipeline["layout_hints"]["unit_hints"] if h["unit_id"] in ids],
            "parse_work": parse_work, "work_used": budget.used, "work_limit": budget.max_work_units,
            "work_exhausted": budget.exhausted, "product_source_sha256": source,
            "model_calls": 0, "downloads": 0, "raw_copies": 0}
        if catalog._store is not None:
            raise RuntimeError("read-only probe constructed store")
    finally:
        NativeSourceContext.page_neighbour = original_page
        catalog.close()
    if protected != {str(p): digest(p) for p in [config_file, config.database_path]}:
        raise RuntimeError("config/catalog changed")
    if source != {str(p.relative_to(ROOT)): digest(p) for p in (ROOT / "src/company_wiki").rglob("*.py")}:
        raise RuntimeError("product changed during probe")
    result["protected_unchanged"] = True
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": output.name, "diagnostics": result["context_diagnostics"],
        "positive_pages": len(context.native_text_pages), "work": budget.used}))


if __name__ == "__main__":
    main()
