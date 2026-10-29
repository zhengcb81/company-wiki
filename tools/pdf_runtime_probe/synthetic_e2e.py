"""One real-entry synthetic PDF E2E through the production paragraph runtime.

Generates a small synthetic PDF in an owned temp root, selects the enhancement
through the production ``configured_paragraph_runtime`` config entry, and runs
the real PdfReading -> real worker subprocess -> offline SDK -> existing
alignment path once. The receipt records only bounded, source-free
observations. No ROOT HK batch, no real-company documents, no model/env
mutation: the deployment env, model bytes and ROOT receipts stay read-only.
"""
from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import time

WORKTREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE / "src"))

from company_wiki.resource_budget import WorkBudget  # noqa: E402
from company_wiki.source_contract import source_id_for_sha256  # noqa: E402
from company_wiki.source_catalog import narrative_evidence as native  # noqa: E402
from company_wiki.source_catalog.narrative_pdf_enhancement import (  # noqa: E402
    configured_paragraph_runtime)
from company_wiki.source_catalog.narrative_pdf_reading import (  # noqa: E402
    PdfReading, PdfReadingRequest)

PROFILE_RELATIVE = "ROOT/.planning/c3-20261028/pdf-sdk-isolated/runtime-isolated.json"


def build_synthetic_pdf(folder: Path) -> bytes:
    import pymupdf as fitz

    # Each page carries one wrapped-prose fracture: the first line ends
    # mid-sentence without terminal punctuation, so the paragraph triage
    # observes an unproven boundary and demands enhancement.
    document = fitz.open()
    for index in range(2):
        page = document.new_page(width=600, height=800)
        page.insert_text((60, 100), f"报告期内，公司第{index + 1}季度的新型自动化产线已进入安装调试阶段，并在期末前完成联动试车并获得", fontsize=9, fontname="china-s")
        page.insert_text((83, 114), "客户的最终验收确认，但尚未转入大规模量产。", fontsize=9, fontname="china-s")
    data = document.tobytes()
    document.close()
    return data


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path,
        default=Path.home() / "Projects" / "company-wiki" / ".planning" / "c3-20261028"
                / "pdf-sdk-isolated" / "runtime-isolated.json")
    parser.add_argument("--receipts-dir", type=Path,
        default=WORKTREE / "docs" / "plans" / "w21-pdf-runtime-2026-10-29" / "receipts")
    parser.add_argument("--receipt-name", default="synthetic-e2e")
    parser.add_argument("--python", default=None,
        help="Deployment-path diagnostic override. The pinned docling-parse "
             "C++ layer cannot open its resources from a non-ASCII deployment "
             "path on an ACP=GBK machine, so the canonical run fails at page "
             "conversion; an ASCII alias of the same env proves the interface "
             "requirement. Canonical runs must omit this.")
    arguments = parser.parse_args()

    profile = json.loads(arguments.profile.read_text(encoding="utf-8-sig"))
    python_origin = "profile"
    if arguments.python is not None:
        profile["python"] = arguments.python
        python_origin = "ascii_alias_diagnostic"
    receipts = arguments.receipts_dir
    receipts.mkdir(parents=True, exist_ok=True)
    # Owned scratch inside the repo-local launch cache root: the deployed
    # interpreter runs at Low integrity and could not write a Medium %TEMP%.
    from company_wiki.source_catalog.narrative_pdf_enhancement import _child_bytecode_prefix
    prefix = _child_bytecode_prefix()
    scratch_root = str(Path(prefix) / "tmp") if prefix is not None else None
    if scratch_root:
        Path(scratch_root).mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="cw-w21-e2e-", dir=scratch_root))
    receipt: dict[str, object] = {
        "scope": "one synthetic two-page PDF through the real production entry",
        "profile_relative": PROFILE_RELATIVE,
        "profile_sha256": sha256(arguments.profile.read_bytes()).hexdigest(),
        "python_origin": python_origin,
        "worktree_companies_present": (WORKTREE / "companies").exists(),
        "worktree_raw_present": (WORKTREE / "companies_raw").exists(),
        "status": None, "seconds": None, "cleanup": {}}
    started = time.monotonic()
    try:
        data = build_synthetic_pdf(scratch)
        pdf_path = scratch / "synthetic.pdf"
        pdf_path.write_bytes(data)
        digest = sha256(data).hexdigest()
        config_path = scratch / "paragraph-runtime.json"
        config_path.write_text(json.dumps({**profile, "schema_version": "pdf-paragraph-runtime/2"}, ensure_ascii=False),
            encoding="utf-8")
        previous_config = os.environ.get("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG")
        os.environ["COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG"] = str(config_path)
        try:
            enhancement = configured_paragraph_runtime()
            assert enhancement is not None, "configured paragraph runtime must select"
            config = enhancement.config
            recipe = dict(enhancement.describe_recipe())
            native_parse = native.parse_pdf_bytes(data, source_id=source_id_for_sha256(digest),
                source_sha256=digest, language="zh")
            native_texts = [unit.raw_text for unit in native_parse.units]

            reading = PdfReading()  # Production composition: native parser plus
            # the enhancement selected from COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG.
            request = PdfReadingRequest(source_id_for_sha256(digest), digest, "zh", "合成验收样张", "annual_report")

            def selector(parsed, **kwargs):
                return native.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)

            selector.selector_version = "0.9.0"

            parsed, selected = reading.select(data, request, selector=selector,
                work_budget=WorkBudget(10_000_000), checkpoint=lambda: None)
            diagnostic = parsed.layout_diagnostics[-1]
            execution = dict(parsed.layout_coverage["reading_execution"])
            texts_preserved = [unit.raw_text for unit in parsed.units] == native_texts
            replay_verified, replay_failed = reading.replay(data, source_id=request.source_id,
                source_sha256=digest, evidence_spans=selected.evidence_spans, language="zh")
            receipt.update(
                status=diagnostic.get("status"), seconds=round(time.monotonic() - started, 3),
                pdf_bytes=len(data), pdf_sha256=digest, page_count=native_parse.page_count,
                diagnostic=json.loads(json.dumps({key: diagnostic.get(key) for key in (
                    "status", "pages", "gap_signals", "accepted_groups", "rejected_groups", "actual_engine",
                    "engine_version", "model_sha256", "converter_instances", "peak_job_commit_bytes", "seconds",
                    "reason", "last_stage", "worker_error", "worker_returncode", "temporary_root_restored_absent",
                    "completed_pages", "pending_pages", "stream_complete", "truncated_final_record",
                    "checkpoint_protocol")}, ensure_ascii=True)),
                reading_execution=execution,
                runtime_identity={"environment_sha256": config.environment_sha256,
                    "docling_version": config.docling_version,
                    "runtime_versions": dict(config.runtime_versions),
                    "recipe_keys": sorted(recipe)},
                source_preserved=texts_preserved,
                evidence_span_count=len(selected.evidence_spans),
                replay_verified=len(replay_verified), replay_failed=list(replay_failed),
                enhanced_claim_valid=diagnostic.get("status") in {"enhanced", "partial_enhanced"}
                                    and bool(diagnostic.get("accepted_groups")),
                alignment_scope=("aligned_paragraph_groups" if diagnostic.get("accepted_groups")
                                 else "no_aligned_groups_documented_honestly"))
        finally:
            if previous_config is None:
                os.environ.pop("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG", None)
            else:
                os.environ["COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG"] = previous_config
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        receipt["cleanup"] = {"scratch_restored_absent": not scratch.exists(),
                              "pdf_deleted": not (scratch / "synthetic.pdf").exists(),
                              "config_deleted": not (scratch / "paragraph-runtime.json").exists()}
    path = receipts / f"{arguments.receipt_name}.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
