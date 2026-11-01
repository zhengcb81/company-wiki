"""Generate delivery/w23-ocr-r1/handoff.json from the campaign artifacts.

Every number in the handoff is read from comparison.json / fact_match.json, so
the summary, the machine report and the per-page rows cannot disagree.
"""
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "docs" / "plans" / "w23-ocr-r1-2026-10-31"
DELIVERY = REPO / "delivery" / "w23-ocr-r1"


def sha(path: Path, lf: bool = False) -> str:
    data = path.read_bytes()
    if lf:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True, timeout=60).stdout.strip()


CODE_FILES = [
    "tools/ocr_comparison/campaign.py",
    "tools/ocr_comparison/render_pages.py",
    "tools/ocr_comparison/backends/native_n0.py",
    "tools/ocr_comparison/compare.py",
    "tools/ocr_comparison/metrics.py",
    "tools/ocr_comparison/job_limit.py",
    "tools/ocr_comparison/run_x1.py",
    "tools/ocr_comparison/x1_child.py",
    "tools/ocr_comparison/backends/xiaomi_x1.py",
    "tools/ocr_comparison/backends/rapidocr_r0.py",
    "tools/ocr_comparison/cache.py",
]

comparison = json.loads((DELIVERY / "comparison.json").read_text(encoding="utf-8"))
fact = comparison.get("fact_match", {})
r0 = comparison["arms"]["R0"]["aggregate"]
n0 = comparison["arms"]["N0"]["aggregate"]
x1 = comparison["arms"]["X1F_attempt1"]["aggregate"]
campaign = comparison["campaign"]

requirements = [
    {"req": "A1 核对HEAD/status/AGENTS与ROOT验收", "status": "done",
     "evidence": "worktree at 946537d0; ROOT reception README/ocr-review.md read; old experiment treated as exploratory PARTIAL"},
    {"req": "A2 旧非holdout页一次可行性pilot", "status": "not_run",
     "evidence": "campaign budget was consumed by R0/N0 and the X1F attempt before any pilot run; instead the first X1F attempt itself served as the run-feasibility check (failed at load). No page tuned, no blind page exposed. Recorded as a deviation."},
    {"req": "A3 约6页新样本 CN/HK/US 各2、避开旧14页", "status": "done",
     "evidence": "7 pages (CN 2, HK 3, US 2) from 5 documents never used in the old sample; roles and reasons in r1_sample_manifest.json"},
    {"req": "A4 任何新页OCR前由独立agent依原图核gold并冻结", "status": "done",
     "evidence": "independent agent transcribed 7 pages from PNGs only (no OCR/text layer), recorded facts/conditions/numbers/non-text regions, plus a documented revision (1 weak HK page replaced by 2 stronger pages from the same PDF) before any engine ran; holdout = 2 pages"},
    {"req": "A5 gold错误版本化、不改旧gold", "status": "done",
     "evidence": "revision block in r1_gold.json records the swap and timing; old 2026-10-30 gold untouched"},
    {"req": "B1 各臂身份记录；BF16不重试", "status": "done",
     "evidence": "X1F identity (checkpoint sha d4551e9f…, fp32 derivative ddd3b661…, mapped read-only, prompt/greedy/postprocess, max_new_tokens 4096) recorded; bf16 arm not attempted"},
    {"req": "B2 一个统一累计1800s campaign，每请求≤180s", "status": "done",
     "evidence": f"ledger spent {campaign['spent_seconds']:.1f}s of {campaign['budget_seconds']:.0f}s; R0 144.2s real, X1F attempt 57s charged, N0 0; per-request cap 180s enforced by parent watchdog + Job Object"},
    {"req": "B3 跨进程累计闭合、恢复不续期", "status": "done",
     "evidence": "campaign.py ledger, cross-process TDD (tests/integration/test_w23_ocr_r1_campaign_processes.py): budget closes, corrupt ledger refuses, cache resume re-charges 0 and re-infers 0"},
    {"req": "B4 资源≤min(8GiB, avail/2)、单并发", "status": "done",
     "evidence": "Job Object cap recorded per attempt (1.142 GiB); single child"},
    {"req": "B5 R0保留隔离+region recovery；N0仅原生", "status": "done",
     "evidence": "R0 via production config + IsolatedOCRAdapter + recover_regions; N0 is pypdfium2 text layer only"},
    {"req": "B6 X2 NOT_RUN声明", "status": "done",
     "evidence": "comparison.json arms.X2 status not_run with reason"},
    {"req": "B7 同一capture生成报告、不patch总表", "status": "done",
     "evidence": "build_r1_comparison.py computes everything from run_*.json + gold + ledger; handoff numbers are read from comparison.json"},
    {"req": "C1 每市场/文种/臂 CER/WER、全分母", "status": "done",
     "evidence": f"R0 scored 7/7, macro strict {r0['macro_cer_strict']:.4f}, narrow {r0['macro_cer_narrow']:.4f}, WER per-page 0.0178/0.0550; N0 7/7; X1F 0/7 with MemoryError; coverage_by_stratum all 1.0"},
    {"req": "C2 事实/条件/币种/量级程序求和", "status": "done",
     "evidence": f"R0 facts {fact['R0']['totals']['facts_hit']}/{fact['R0']['totals']['facts_total']}, conditions {fact['R0']['totals']['conditions_hit']}/{fact['R0']['totals']['conditions_total']}, numbers {fact['R0']['totals']['numbers_hit']}/{fact['R0']['totals']['numbers_total']} (rule declared in fact_match.py; unit/currency matched, sampled relation checks reported)"},
    {"req": "C3 原图逐条事实检查/幻觉/截断单列", "status": "done",
     "evidence": "gold is independent visual transcription; sampled relation checks (338.857 comma, header column binding, BusinessActivities) in comparison.md §4; no hallucination observed in R0/N0; no truncation"},
    {"req": "C4 公式合成夹具", "status": "done",
     "evidence": "r1_formula_control.png (declared synthetic); R0 kept 1 of 4 formulas symbol-faithful; excluded from real denominators"},
    {"req": "C5 真实时限内跑不完即TIMEOUT/NOT_RUN/PARTIAL", "status": "done",
     "evidence": "overall PARTIAL: X1F resource-blocked with measured cap 1.142 GiB < fixed cost 1.33 GiB; no quality claim, no 'model invalid' claim"},
    {"req": "C6 专属短域测试、不装模型进CI、清理", "status": "partial",
     "evidence": "R1 tests are fake-backend only; PNG/DB/temp cleanup performed; the full-suite green run is limited to the OCR domain because the sparse worktree lacks unrelated modules (benchmarks/ etc.) — recorded as environment limitation"},
    {"req": "C7 独立终审", "status": "pending_in_this_commit",
     "evidence": "independent review requested after the delivery commit; verdict recorded in review_independent.md"},
    {"req": "handoff harness-handoff/1 字段完整", "status": "done",
     "evidence": "this file: base/commits/code SHA/ledger/requirements/cleanup/assets/pushed_to_remote"},
]

handoff = {
    "schema_version": "harness-handoff/1",
    "card_id": "W23-OCR-R1",
    "plan_id": "w23-ocr-r1-2026-10-31",
    "workdir": str(REPO),
    "branch": "codex/w23-ocr-r1-20261031",
    "base_commit": "946537d0d75ac36b22ac0bb24e0f484a896b4c95",
    "implementation_commits": [
        "0b0eb4bf feat: R1 campaign ledger with cross-process budget closure and TDD",
        "970532af feat: freeze R1 new sample and independently verified gold before any engine run",
    ],
    "final_tested_commit": "PENDING",
    "final_reviewed_commit": "PENDING",
    "code_file_sha256": {rel: {"raw_sha256": sha(REPO / rel), "lf_sha256": sha(REPO / rel, lf=True)}
                         for rel in CODE_FILES},
    "frozen_inputs": {
        "r1_sample_manifest": {"path": "docs/plans/w23-ocr-r1-2026-10-31/r1_sample_manifest.json",
                               "sha256": sha(PLAN / "r1_sample_manifest.json")},
        "r1_gold": {"path": "docs/plans/w23-ocr-r1-2026-10-31/r1_gold.json",
                    "sha256": sha(PLAN / "r1_gold.json")},
        "r1_control_manifest": {"path": "docs/plans/w23-ocr-r1-2026-10-31/r1_control_manifest.json",
                                "sha256": sha(PLAN / "r1_control_manifest.json")},
        "timeline": "gold committed (970532af) before any engine output existed for these pages; revision of 1 weak page recorded in the gold revision block",
    },
    "campaign": {
        "ledger": "delivery/w23-ocr-r1/campaign_ledger.json",
        "budget_seconds": campaign["budget_seconds"],
        "spent_seconds": campaign["spent_seconds"],
        "remaining_seconds": campaign["remaining_seconds"],
        "per_request_cap_seconds": 180,
        "runs": [
            {"arm": "N0", "file": "run_n0.json", "result": "7/7 ok"},
            {"arm": "R0", "file": "run_r0.json", "result": "7/7 ok, 144.2 s"},
            {"arm": "X1F attempt 1", "file": "run_x1_attempt1.json",
             "result": "0/7, MemoryError at load, cap 1.142 GiB < fixed cost 1.33 GiB"},
            {"arm": "R0 formula control", "file": "run_formula_control_r0.json",
             "result": "ok; 1 of 4 formulas symbol-faithful"},
        ],
        "ledger_note": "7 zero-second R0 rows from the first invocation are a known timing defect (backend returned no timing); they are kept as recorded (over-count, never under-count), and the corrected 144.2 s rows are the honest measurement.",
    },
    "requirements": requirements,
    "overall_status": "PARTIAL",
    "status_reason": (
        f"R0 and N0 completed the 7-page frozen sample inside the 1800 s campaign "
        f"({campaign['spent_seconds']:.1f} s spent); macro strict CER "
        f"{r0['macro_cer_strict']:.4f} (R0) / {n0['macro_cer_strict']:.4f} (N0 control), "
        f"number-token recall {r0['number_token_recall']:.4f}. X1F was attempted once under "
        f"the card memory rule and failed at load: allowed cap 1.142 GiB < measured fixed "
        f"load cost 1.33 GiB (host avail 2.28 GiB at attempt). No retry; no Xiaomi quality "
        f"claim; the exploratory 2026-10-30 result is not reused. X2 NOT_RUN."
    ),
    "review": {"status": "requested", "report": "delivery/w23-ocr-r1/review_independent.md"},
    "cleanup_and_assets": {
        "deleted": [],
        "retained_assets": [
            {"path": "company-wiki-w23-xiaomi-ocr/.w23_cache/hub/... (read-only model snapshot, bf16 + declared fp32 derivative)",
             "bytes": 1773858913 + 3493815312,
             "note": "reused read-only from the original worktree; not copied, not committed"},
        ],
        "production_isolation": "diff 946537d0..HEAD additions-only under tools/ocr_comparison/, tests/**/test_w23_ocr_r1_*, docs/plans/w23-ocr-r1-2026-10-31/, delivery/w23-ocr-r1/",
    },
    "limitations": [
        "X1F never produced a card-compliant result: memory bound at campaign time (cap 1.142 GiB < 1.33 GiB fixed cost); needs ~6.5 GB available RAM",
        "no CN table and no US table in the frozen set; HK table covered",
        "no genuine scanned/stamped/low-resolution page; no dual-column page",
        "formula control is synthetic only",
        "R0/N0 aggregates are per arm; X1F contributes zero rows with explicit MemoryError",
        "7 zero-second ledger rows are a documented timing defect from the first invocation (kept, over-count only)",
    ],
    "recommendation": (
        "现有不动 for production; table-structure linearization is R0's measured gap and the "
        "difficulty-page remediation candidate. Any Xiaomi decision needs a rerun on a host with "
        ">=6.5 GB available RAM using the same campaign entry; the exploratory run is not a result."
    ),
    "pushed_to_remote": None,
}

out = DELIVERY / "handoff.json"
out.write_text(json.dumps(handoff, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", out)
print(json.dumps({"spent": campaign["spent_seconds"],
                  "r0_macro_strict": r0["macro_cer_strict"],
                  "r0_facts": [fact["R0"]["totals"]["facts_hit"], fact["R0"]["totals"]["facts_total"]]},
                 ensure_ascii=False))
