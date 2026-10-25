"""Finite source-exact regression replay; originals/config remain read-only.

Usage: python -X utf8 THIS.py --mode frozen|live --output NAME
Live additionally requires --runtime-config pointing to local deployment JSON.
This is exposed regression evidence, not a newly blinded holdout or LLM summary.
"""
import argparse
from dataclasses import asdict, replace
import gzip
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
NODE = Path(__file__).resolve().parent
FROZEN = NODE.parent / "pdf-parser-reuse-pilot-20261025"

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, PdfReadingRequest
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement, ParagraphRuntimeConfig
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan


def read(name):
    return json.loads(gzip.decompress((FROZEN / name).read_bytes()))


def compact(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--mode", choices=("frozen", "live"), required=True)
    args.add_argument("--output", required=True)
    args.add_argument("--runtime-config")
    args.add_argument("--limit-sources", type=int, default=3)
    opts = args.parse_args()
    frozen_runtime = read("current-reading-bounded-baseline.json.gz")["pymupdf"]
    if version("pymupdf") != frozen_runtime:
        raise ValueError("frozen native replay requires PyMuPDF " + frozen_runtime + "; runtime changes are not exact-span replay")
    target = NODE / (opts.output + ".json")
    if target.exists():
        raise FileExistsError(target)
    samples = read("business-pages-source.json.gz")["samples"]
    converted = read("business-comparison-v2-raw.json.gz")["runs"]
    checkpoints = json.loads((FROZEN / "business-checkpoints.json").read_text("utf-8"))["checks"]
    config = load_catalog_config(ROOT / "config/source_catalog.yaml", project_root=ROOT)
    catalog = SourceCatalog(config)
    protected = [ROOT / "config/source_catalog.yaml", config.database_path, ROOT / "config/resource_budget.yaml"]
    before = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in protected}
    runs, checkpoints_out = [], []
    tick = time.monotonic()
    try:
        for digest in list(dict.fromkeys(s["source_ref"]["content_sha256"] for s in samples))[:opts.limit_sources]:
            cases = [s for s in samples if s["source_ref"]["content_sha256"] == digest]
            ref = SourceRef(**cases[0]["source_ref"])
            hk = cases[0]["case_id"].startswith("hk")
            kind = "semi_annual_report" if hk else "prospectus" if "ipo" in cases[0]["case_id"] else "annual_report"
            title = {"semi_annual_report": "2025 中期報告", "prospectus": "招股说明书", "annual_report": "2025年年度报告"}[kind]
            language = "zh-hant" if hk else "zh"
            data = SourceVersionReader(catalog).open_version(ref, purpose="preview").data
            assert sha256(data).hexdigest() == digest
            budget = new_document_work_budget()
            reading = PdfReading()
            parsed = reading.read(data, PdfReadingRequest(ref.source_id, digest, language, title, kind),
                                  selector_version="0.9.0", work_budget=budget, deadline=time.monotonic() + 90)
            pages = {c["page"] for c in cases}
            view = replace(parsed, units=tuple(u for u in parsed.units if u.coordinates.page_number in pages),
                pages_read=len(pages), opaque_pages=tuple(p for p in range(1, parsed.page_count+1) if p not in pages))
            row = {"cases": [c["case_id"] for c in cases], "source_ref": asdict(ref), "analysis_pages": sorted(pages),
                   "native_full_parse_pages": parsed.page_count, "partial_analysis": True}
            for phase in ("native", "enhanced"):
                material = view
                if phase == "enhanced":
                    if opts.mode == "live" and hk:
                        settings = json.loads(Path(opts.runtime_config).read_text("utf-8"))
                        settings.pop("schema_version")
                        from company_wiki._bounded_process import run_bounded
                        def observed_runner(*args, **kwargs):
                            try:
                                return run_bounded(*args, **kwargs)
                            except Exception as exc:
                                # Private bounded diagnostics, never source or deployment data in the public receipt.
                                log = ROOT / ".planning/pdf-c2-enhancement-20261025" / (opts.output+"-worker.stderr")
                                log.write_bytes(getattr(exc, "stderr", b"")[:65536])
                                raise
                        enhancer = ParagraphEnhancement(ParagraphRuntimeConfig(**settings), runner=observed_runner)
                    else:
                        def runner(command, **kw):
                            req = json.loads(kw["input_bytes"])
                            items = [i for c in cases if c["page"] in req["pages"] for r in converted
                                     if r["engine"] == "docling-default" and r["case_id"] == c["case_id"] for i in r["items"]]
                            return {"stdout": json.dumps({"schema_version": "pdf-paragraph-response/1", "source_sha256": digest,
                                "pages": req["pages"], "docling_version": "2.96.0", "model_sha256": "b"*64,
                                "model_config_sha256": "c"*64,
                                "runtime_versions": req["runtime_versions"],
                                "environment_sha256": req["environment_sha256"],
                                "items": items, "converter_instances": 1}).encode()}
                        enhancer = ParagraphEnhancement(ParagraphRuntimeConfig("unused", "unused", "b"*64, "2.96.0", "c"*64,
                            {k:"1" for k in ("python", "docling-core", "docling-ibm-models", "torch", "pymupdf", "pypdfium2")}, "d"*64), runner=runner)
                    enhanced_full = enhancer.enhance(data, parsed, work_budget=budget, deadline=time.monotonic()+120)
                    material = replace(view, units=tuple(u for u in enhanced_full.units if u.coordinates.page_number in pages),
                                       layout_diagnostics=enhanced_full.layout_diagnostics)
                    row["enhancement"] = material.layout_diagnostics[-1]
                    row["enhancement_input"] = "whole_original_native_observation"
                    row["enhancement_transport"] = "live_docling" if opts.mode == "live" and hk else "frozen_docling_observation_replay"
                selected = select_narrative_evidence(material, title=title, existing_kind=kind,
                    selector_version="0.9.0", work_budget=budget)
                reading.verify_material(material, selected.evidence_spans)
                task_plan = build_summary_task_plan(selected.evidence_spans, reading_context=selected.reading_context, max_claims=256)
                spans = {s.span_id: s for s in selected.evidence_spans}
                tasks = [{"key": t.key, "span_ids": list(t.member_ids), "support_ids": list(t.support_ids),
                          "text": "\n".join(spans[s].raw_text for s in t.member_ids),
                          "locators": [spans[s].coordinates.locator() for s in t.member_ids]} for t in task_plan.tasks]
                row[phase] = {"tasks": tasks, "task_binding_sha256": task_plan.binding_sha256,
                              "spans": [s.to_dict() for s in selected.evidence_spans], "work_used": budget.used}
                for check in checkpoints:
                    if check["case_id"] not in row["cases"] or check.get("requires_cell_relationship"):
                        continue
                    matching = [t for t in tasks if all(compact(a) in compact(t["text"]) for a in check["atoms"])
                                and not any(compact(a) in compact(t["text"]) for a in check["exclude"])]
                    checkpoints_out.append({"id": check["id"], "phase": phase, "pass": bool(matching),
                                            "tasks": [t["key"] for t in matching]})
                if kind == "prospectus":
                    for name, atoms in (("etch-application", ["从65纳米到14纳米、7纳米和5纳米", "具体应用"]),
                                        ("mocvd-production", ["MOCVD设备", "大规模投入量产", "国内占领先地位"])):
                        matches = [t for t in tasks if all(compact(a) in compact(t["text"]) for a in atoms)]
                        checkpoints_out.append({"id": "ipo-fact-v2-"+name, "phase": phase, "pass": bool(matches),
                                                "tasks": [t["key"] for t in matches]})
            row["shared_work_limit"] = budget.max_work_units
            assert not budget.exhausted
            runs.append(row)
            print("DONE", kind, row["enhancement"]["status"], flush=True)
        assert catalog._store is None
        assert all(sha256(p.read_bytes()).hexdigest() == before[str(p.relative_to(ROOT))] for p in protected)
    finally:
        catalog.close()
    payload = {"schema_version": "pdf-c2-paragraph-real-replay/1", "mode": opts.mode, "runs": runs,
               "checkpoints": checkpoints_out, "protected_sha256": before, "protected_unchanged": True,
               "seconds": round(time.monotonic()-tick, 3), "downloads": 0, "paid_calls": 0, "raw_copies": 0,
               "scope": "Exposed finite five-page regression; tasks/citations only; not LLM semantics or fresh holdout"}
    wire = json.dumps(payload, ensure_ascii=False, indent=2).encode()
    (NODE / (opts.output+".json.gz")).write_bytes(gzip.compress(wire, mtime=0))
    target.write_text(json.dumps({k:v for k,v in payload.items() if k != "runs"}, ensure_ascii=False, indent=2)+"\n", "utf-8")
    print(json.dumps(payload["checkpoints"], ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
