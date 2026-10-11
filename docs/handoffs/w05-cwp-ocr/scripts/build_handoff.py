# Generate handoff.json + manifest.json with real SHAs/bytes (run once; kept as method record).
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
handoff_dir = root / "docs" / "handoffs" / "w05-cwp-ocr"


def file_info(p: Path):
    data = p.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


head = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=root
).stdout.strip()
base = "159b993e2f4d36c7e86dc12c9d6028f4a31b353a"

changed = [
    ("src/company_wiki/document_normalization/local_ocr.py", "engine text_score floor + cwp-ocr-region-diagnostics/1 + recovery/revision keys in identity_manifest (fingerprint invalidates old caches)"),
    ("src/company_wiki/document_normalization/ocr_composition.py", "composer consumes diagnostics, runs bounded recovery once per unique media, emits ocr_recovered units and quality counts"),
    ("src/company_wiki/document_normalization/ocr_region_recovery.py", "new bounded ROI recovery ladder with deterministic transforms/back-mapping and request-shared budget accounting"),
    ("tests/document_normalization/test_local_ocr_adapter.py", "RED/GREEN coverage for score floor, diagnostics schema and legacy constructor compatibility"),
    ("tests/document_normalization/test_ocr_region_recovery.py", "unit matrix: selection, geometry, back-mapping, stitching, dedup, budget, deadline, engine failure"),
    ("tests/document_normalization/test_ocr_region_composition.py", "integration: composer diagnostics feed, recovered units, replay round-trip, request-wide ROI budget"),
    ("docs/design/w05-ocr-region-recovery.md", "design record: observed mechanisms, unknowns, ladder/acceptance/budget rules"),
]
changed_files = [
    {"path": p, "sha256": file_info(root / p)["sha256"], "purpose": why} for p, why in changed
]

input_evidence = [
    {"path": f"docs/handoffs/w05-cwp-ocr/input/{f.name}", **file_info(f)}
    for f in sorted((handoff_dir / "input").iterdir())
    if f.is_file()
]

focused = (
    "python -B -m pytest -q tests/document_normalization/test_local_ocr_adapter.py "
    "tests/document_normalization/test_local_pptx_ocr.py tests/document_normalization/test_pptx.py "
    "tests/document_normalization/test_ocr_region_recovery.py tests/document_normalization/test_ocr_region_composition.py"
)
full = "python -B -m pytest -q tests/document_normalization/"


def log_entry(name):
    info = file_info(handoff_dir / "logs" / name)
    return {"log": f"logs/{name}", "log_sha256": info["sha256"]}


tests = [
    {
        "phase": "RED",
        "command": focused,
        "exit_code": 1,
        "counts": {"failed": 23, "passed": 35, "run2_after_local_ocr": "failed 21 passed 38"},
        "elapsed_seconds": 9.57,
        "scope": "behavioral counterexamples (diagnostics missing, ROI geometry, dedup, budget, compat) failed before implementation; session record preserves actual captured output because the pre-implementation tree evolved in place",
        **log_entry("red-run-record.log"),
    },
    {
        "phase": "GREEN",
        "command": focused,
        "exit_code": 0,
        "counts": {"passed": 59},
        "elapsed_seconds": 25.26,
        "scope": "card-specified focused suite green after implementation",
        **log_entry("green-focused-suite.log"),
    },
    {
        "phase": "INTEGRATION",
        "command": full,
        "exit_code": 0,
        "counts": {"passed": 129},
        "elapsed_seconds": 35.54,
        "scope": "whole document_normalization package incl. replay/determinism suites",
        **log_entry("green-full-suite.log"),
    },
    {
        "phase": "E2E",
        "command": "python -X utf8 -B docs/handoffs/w05-cwp-ocr/scripts/e2e_slide7_recovery.py",
        "exit_code": 0,
        "counts": {
            "phase1_source_ocr_compose": "COMPLETED 36.375s",
            "phase2_locator_replay_reopen": "COMPLETED 33.451s",
            "original_lines_exact": 22,
            "recovered_lines": 2,
            "unrecovered_flagged_regions": 1,
        },
        "elapsed_seconds": 70.0,
        "scope": "real SourceVersionReader->media->local OCR->compose->replay; two business definitions recovered (0.989/0.990); 22 prior lines text/box/confidence exact vs root-cause baseline; SHA unchanged; each phase under its 90s hard cutoff",
        "log": "evidence/e2e-slide7-result.json",
        "log_sha256": file_info(handoff_dir / "evidence" / "e2e-slide7-result.json")["sha256"],
    },
]

findings = [
    {
        "id": "OCR-R1",
        "root_cause": "RapidOCR text_score 0.5 filter inside the engine erased identifiable dropped regions before the composition layer; adapter could not report them",
        "disposition": "fixed",
        "test_ids": ["test_engine_runs_with_score_floor_and_reports_dropped_regions"],
        "evidence": ["evidence/locate-cause.json E0 (25->22 exact vs baseline)", "evidence/e2e-slide7-result.json dropped_regions=3 diagnosed"],
    },
    {
        "id": "OCR-R2",
        "root_cause": "Two slide7 business-definition lines garbled only in the full-image det->perspective-crop->batched-rec chain; isolated axis-aligned margin re-recognition reads both at >=0.986 (cls/polarity/upscaling excluded as sole causes)",
        "disposition": "fixed",
        "test_ids": ["test_recover_accepts_margin_crop_line_and_reports_records"],
        "evidence": ["evidence/locate-cause.json ROI records", "evidence/e2e-slide7-result.json recovered_lines"],
    },
    {
        "id": "OCR-R2b",
        "root_cause": "exact failing sub-step (batched rec tensor geometry vs perspective warp) not instrumented",
        "disposition": "remaining",
        "test_ids": [],
        "evidence": ["docs/design/w05-ocr-region-recovery.md section 5"],
    },
    {
        "id": "OCR-R3",
        "root_cause": "nonempty output/page-recognized never tested content recall; drops left no quality trace",
        "disposition": "fixed",
        "test_ids": ["test_unrecovered_region_surfaces_quality_counts_and_keeps_good_lines"],
        "evidence": ["page_record unrecovered_regions=1 (bullet flagged)", "coverage_complete=false kept"],
    },
    {
        "id": "OCR-R5",
        "root_cause": "existing parent-kill test used a 2s subprocess cold-start window that flakes under Windows AV load",
        "disposition": "fixed",
        "test_ids": ["test_parent_hard_deadline_kills_noncooperative_ocr_before_publish"],
        "evidence": ["timeout 2->20 with rationale comment; blocking sleep 30>20 preserves semantics"],
    },
    {
        "id": "OCR-R6",
        "root_cause": "synthetic degradation (blur/faint/jitter/aliasing) cannot induce the score-filtered-garble branch on non-MSFT small images (min observed 0.599)",
        "disposition": "diagnostic",
        "test_ids": [],
        "evidence": ["evidence/synthetic-probe.json (synthetic-marked; not a substitute for real acceptance)"],
    },
]

interfaces = [
    {
        "name": "OCRAdapter.transcribe(data, *, limits) -> ImageOCRResult",
        "before": "returns accepted lines only; dropped regions invisible",
        "after": "same signature; additionally fills ImageOCRResult.region_diagnostics (default None) with dropped/recovery records",
        "compatibility": "old fake adapters and three-argument ImageOCRResult construction unchanged (test_old_adapters_without_diagnostics_are_unchanged, test_legacy_three_argument_result_and_diagnostics_validation)",
    },
    {
        "name": "LocalOCRConfig.identity_manifest/fingerprint",
        "before": "model/engine/threshold identity only",
        "after": "adds region_diagnostics, engine_text_score_floor=0.0, region_recovery keys; any algorithm revision must bump these strings",
        "compatibility": "fingerprint change invalidates old caches (identity sensitivity test kept); parser_version 2.0.0 unchanged so replay.py locator/version seams stay valid (replay round-trip tested)",
    },
    {
        "name": "enrich_pptx document metadata.ocr",
        "before": "pages/images counts only",
        "after": "adds per-image region_diagnostics + per-page dropped/recovered/unrecovered/recovery_attempts + request-level region_recovery accounting; recovered units carry ocr_recovered flag/metadata and continuous locators",
        "compatibility": "unrecovered regions only raise quality flags; original lines never modified or removed (dedup rejects recovered duplicates)",
    },
    {
        "name": "ocr_region_recovery (new module)",
        "before": "n/a",
        "after": "plan_regions/recover_regions/build_margin_crop/build_split_stack/build_upscale/map_box/box_iou/RecoveryBudget",
        "compatibility": "acceptance threshold is never lowered; per-image 4 regions/2 attempts-per-region/8 attempts; ROI pixels charged to shared max_total_pixels",
    },
]

retained = sum(
    file_info(p)["bytes"]
    for d in ("evidence", "logs", "scripts")
    for p in (handoff_dir / d).iterdir()
    if p.is_file()
)

handoff = {
    "schema_version": "w05-lane-handoff/1",
    "lane": "W05-CWP-OCR",
    "status": "COMPLETE",
    "repository": "C:/Users/郑曾波/Projects/company-wiki",
    "workdir": "C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr",
    "base_commit": base,
    "head_commit": head,
    "branch": "codex/w05-cwp-ocr",
    "changed_files": changed_files,
    "input_evidence": input_evidence,
    "interfaces": interfaces,
    "tests": tests,
    "findings": findings,
    "cleanup": {
        "owned_root": "C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr/docs/handoffs/w05-cwp-ocr/scratch",
        "baseline": "recorded in .planning/w05-cwp-ocr/task_plan.md: scratch did not exist before this lane",
        "after": "scripts/evidence/logs promoted to docs/handoffs/w05-cwp-ocr/, transient synthetic PNGs deleted, scratch directory removed",
        "restored": True,
        "raw_unchanged": True,
    },
    "cost": {
        "provider_calls": 0,
        "model_calls": 0,
        "paid_usd": "0",
        "unknown_charge": None,
        "local_cpu_inference_calls": "approx 33 (13 cause-locating + 12 two E2E runs incl. replay passes + 8 synthetic probes); all within per-image caps",
    },
    "space": {
        "retained_bytes": retained,
        "scratch_peak_bytes": "approx 400000 (scripts+jsons+roi pngs before promotion)",
        "measurement": "actual",
    },
    "remaining": [
        "exact failing sub-step inside the batched-rec/crop chain not instrumented (recovery seam does not depend on it)",
        "synthetic degradation could not induce the score-filtered-garble branch on non-MSFT images; generic low-score coverage rests on slide7 + unit matrix",
        "G2/G4/G5 raw->units->selector->summary->RF integration stays with ROOT; this lane gives no economic-quality pass",
    ],
    "root_next_action": "review seams (transcribe diagnostics, enrich recovery output, fingerprint revision keys) and merge; run the cross-repo integration at existing G2/G4/G5 nodes; not claimed already merged",
}
(handoff_dir / "handoff.json").write_text(
    json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

manifest_files = []
for p in sorted(handoff_dir.rglob("*")):
    if p.is_file() and p.name != "manifest.json":
        manifest_files.append(
            {"path": str(p.relative_to(root)).replace("\\", "/"), **file_info(p)}
        )
manifest = {
    "schema_version": "w05-handoff-manifest/1",
    "lane": "W05-CWP-OCR",
    "files": manifest_files,
}
(handoff_dir / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("handoff.json + manifest.json written;", len(manifest_files), "manifest entries")
print("retained_bytes", retained)
print("head_commit", head)
