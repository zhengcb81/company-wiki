"""Set the final verification numbers in the handoff and plan docs.

The counts move while a second writer keeps adding tests, so the wording records both the
command and the figure measured at this point rather than leaving a bare number that rots.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

COUNTS = {
    "profiles": 150,
    "structure": 47,
    "root": 118,
    "benchmark": 112,  # 105 passed when run alone + 7 real-data opt-ins
    "combined_default": "420 passed, 7 skipped",
    "combined_real_data": "427 passed, 0 skipped",
}

# --- handoff.json ---------------------------------------------------------------------
handoff = ROOT / ".planning" / "du-root" / "handoff.json"
data = json.loads(handoff.read_text(encoding="utf-8"))
data["tests_passed"] = 427
data["test_counts_by_suite"] = {
    **COUNTS,
    "note": (
        "Same four suites in ONE pytest invocation. Default: 420 passed / 7 skipped "
        "(the benchmark's real-data replays are opt-in). With DU_BENCH_ALLOW_REAL_DATA=1 "
        "and bindings present: 427 passed / 0 skipped."
    ),
}
handoff.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("handoff.json updated")

# --- handoff.md -----------------------------------------------------------------------
handoff_md = ROOT / ".planning" / "du-root" / "handoff.md"
text = handoff_md.read_text(encoding="utf-8")
text = text.replace(
    "| **拉满（`DU_BENCH_ALLOW_REAL_DATA=1` + bindings）** | **383 passed / 0 skipped** |",
    "| **拉满（`DU_BENCH_ALLOW_REAL_DATA=1` + bindings）** | **427 passed / 0 skipped** |",
)
text = text.replace(
    "| 默认跑（真实数据 opt-in 关闭） | 371 passed / 5 skipped |",
    "| 默认跑（真实数据 opt-in 关闭） | 420 passed / 7 skipped |",
)
text = text.replace(
    "| profiles / structure / root / benchmark | 150 / 47 / 116 / 70 |",
    "| profiles / structure / root / benchmark | 150 / 47 / 118 / 112 |",
)
text = text.replace(
    "| root | 116 |\n| benchmark | 70 |\n| **同一调用合计（真实数据开启）** | **383 passed / 0 skipped** |\n| 同一调用合计（opt-in 关闭） | 371 passed / 5 skipped |",
    "| root | 118 |\n| benchmark | 112 |\n| **同一调用合计（真实数据开启）** | **427 passed / 0 skipped** |\n| 同一调用合计（opt-in 关闭） | 420 passed / 7 skipped |",
)
handoff_md.write_text(text, encoding="utf-8")
print("handoff.md updated")

# --- task_plan.md ---------------------------------------------------------------------
plan = ROOT / "docs" / "plans" / "document-understanding-2026-10-13" / "task_plan.md"
text = plan.read_text(encoding="utf-8")
text = text.replace(
    "| `src/company_wiki/document_understanding/{observation_adapter,orchestration,selection_bridge,pipeline,summary_input}.py` | 116 | 否 |",
    "| `src/company_wiki/document_understanding/{observation_adapter,orchestration,selection_bridge,pipeline,summary_input}.py` | 118 | 否 |",
)
text = text.replace("| 70 | 工具，非生产路径 |", "| 112 | 工具，非生产路径 |")
text = re.sub(
    r"同一调用下合计：\*\*\d+ passed / \d+ skipped\*\*（开启 benchmark 真实数据 opt-in 与 ROOT bindings）；\n关闭 opt-in 时为 \d+ passed / \d+ skipped。",
    "同一调用下合计：**427 passed / 0 skipped**（开启 benchmark 真实数据 opt-in 与 ROOT bindings）；\n"
    "关闭 opt-in 时为 420 passed / 7 skipped。",
    text,
)
plan.write_text(text, encoding="utf-8")
print("task_plan.md updated")
