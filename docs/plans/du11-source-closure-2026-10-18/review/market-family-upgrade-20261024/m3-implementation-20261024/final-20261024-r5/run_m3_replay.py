"""Reproduce source selection and the existing summary-card compiler on M3 originals.

The script stores canonical selected spans and task bindings only. It never copies
original documents, changes production data, downloads a source, or calls a model.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").is_file())
sys.path.insert(0, str(ROOT))

from company_wiki.document_understanding.source_cards import source_cards
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog import narrative_evidence as engine
from tools.document_understanding_benchmark.observer import _parse

REVIEW = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024"
SOURCE_BINDINGS = REVIEW / "m1-source-checkpoints/source-bindings.json"
OUTPUT = Path(__file__).resolve().parent / "real-replay-multi-market"
SAMPLES = (
    "du5-us-msft-ex991",
    "du5-hk-kingsoft-interim",
    "du5-cn-proya-q1",
    "du5-cn-gbits-call",
    "cn-ipo",
)
LOCAL_PATHS = {
    "cn-ipo": ROOT / "companies/中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
}
EXPECTED_SHA = {
    "du5-us-msft-ex991": "47a0a4a1d6a335fffab571789aba597eca0637d2650f0f62371afa10e205b987",
    "du5-hk-kingsoft-interim": "4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36",
    "du5-cn-proya-q1": "873df9697b20c8c8882f9f16f60bdf755bc6b1b27022f2cd491ebc94c012a49e",
    "du5-cn-gbits-call": "63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a",
    "cn-ipo": "19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67",
}
SELECTOR_VERSION = "0.9.0"
MAX_CLAIMS = 40


def plain(value):
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def producer_snapshot() -> dict[str, str]:
    paths = list((ROOT / "src/company_wiki").rglob("*.py"))
    paths.append(ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json")
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def diagnostic_summary(entries):
    keys = ("code", "count", "phase", "external_model_cost", "dimension", "used", "limit",
            "targets_limited")
    return [{key: entry[key] for key in keys if key in entry} for entry in entries]


def main() -> None:
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise FileExistsError(f"immutable replay output already exists: {OUTPUT}")
    bindings = json.loads(SOURCE_BINDINGS.read_text(encoding="utf-8"))
    before_tree = producer_snapshot()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []

    for sample_id in SAMPLES:
        original = LOCAL_PATHS.get(sample_id) or Path(bindings[sample_id]["original_path"])
        source_before = sha256(original.read_bytes()).hexdigest()
        if source_before != EXPECTED_SHA[sample_id]:
            raise AssertionError(f"original SHA mismatch: {sample_id}")
        started = time.monotonic()
        source_id = "urn:company-wiki:source:sha256:" + source_before
        if original.suffix.lower() == ".pdf":
            parsed = engine.parse_pdf_bytes(
                original.read_bytes(), source_id=source_id, source_sha256=source_before,
                language="zh", selector_version=SELECTOR_VERSION,
                reading_context=PdfReadingContext(original.name, "unknown", "zh"),
                work_budget=new_document_work_budget(),
            )
            parser_entry = "parse_pdf_bytes(selector=0.9.0)"
        else:
            parsed, parser_entry = _parse(engine, original, source_id, source_before)
        package = engine.select_narrative_evidence(
            parsed, title=original.name, existing_kind="unknown",
            selector_version=SELECTOR_VERSION,
        )
        spans = tuple(package.evidence_spans)
        context = plain(package.reading_context or {})
        plan = build_summary_task_plan(spans, reading_context=context, max_claims=MAX_CLAIMS)
        card_rows = []
        for card in source_cards(plan, {span.span_id: span for span in spans}):
            text = card.text or ""
            card_rows.append({
                "task": card.task.to_binding(),
                "available": card.available,
                "reason": card.reason,
                "support_span_ids": [span.span_id for span in card.support],
                "text_sha256": sha256(text.encode("utf-8")).hexdigest() if card.available else None,
                "text_chars": len(text) if card.available else 0,
            })
        source_after = sha256(original.read_bytes()).hexdigest()
        if source_after != source_before:
            raise AssertionError(f"original changed during replay: {sample_id}")
        rows.append({
            "sample_id": sample_id,
            "original_path": str(original),
            "original_sha256_before": source_before,
            "original_sha256_after": source_after,
            "original_unchanged": True,
            "source_id": source_id,
            "parser_entry": parser_entry,
            "selector_version": SELECTOR_VERSION,
            "selection": {
                "status": package.status,
                "coverage_complete": package.coverage_complete,
                "selection_limit": package.selection_limit,
                "candidate_count": package.candidate_count,
                "omitted_candidate_count": package.omitted_candidate_count,
                "dropped_financial_count": package.dropped_financial_count,
                "selected_span_count": len(spans),
                "selected_chars": sum(len(span.raw_text or "") for span in spans),
                "diagnostics": diagnostic_summary(plain(package.selection_diagnostics)),
            },
            "reading_context": context,
            "canonical_spans": [span.to_dict() for span in spans],
            "task_plan": plan.to_binding(),
            "task_plan_binding_sha256": plan.binding_sha256,
            "source_cards": card_rows,
            "external_model_calls": 0,
            "downloads": 0,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        })
        row = rows[-1]
        print(json.dumps({key: row[key] for key in (
            "sample_id", "original_sha256_before", "parser_entry", "selector_version",
            "selection", "task_plan_binding_sha256", "external_model_calls", "downloads",
            "elapsed_seconds")}, ensure_ascii=False), flush=True)

    after_tree = producer_snapshot()
    if after_tree != before_tree:
        raise AssertionError("producer source changed during real-source replay")
    receipt = {
        "schema_version": "m3-real-source-replay/1",
        "scope": "source selection and existing task/card compilation; not model-summary or RF acceptance",
        "git_head_before_replay": head,
        "git_head_after_replay": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "selector_version": SELECTOR_VERSION,
        "production_default_selector_version": engine.NARRATIVE_SELECTOR_VERSION,
        "summary_task_max_claims": MAX_CLAIMS,
        "producer_snapshot": before_tree,
        "producer_tree_sha256": sha256(json.dumps(before_tree, sort_keys=True).encode()).hexdigest(),
        "producer_unchanged": True,
        "external_model_calls": 0,
        "downloads": 0,
        "sources": rows,
    }
    output = OUTPUT / "receipt.json"
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(output), "samples": len(rows),
                      "receipt_sha256": sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
