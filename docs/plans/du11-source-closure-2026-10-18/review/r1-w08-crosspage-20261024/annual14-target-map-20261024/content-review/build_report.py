"""Bind an independent manual 14-target content assessment to frozen evidence.

No product import, PDF parse, automatic quality oracle, or model request occurs.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CURRENT = HERE.parent
BASE = CURRENT.parent


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Each status and explanation below was manually assessed from all 96 spans,
# every task member set, and the unchanged original checklist. Task references
# do not grant permission to combine a missing owner/qualifier across tasks.
ASSESSMENTS = [
    ("ST-A01", "partial", ["t21", "t10", "t13", "t18"],
     "已选主要业务概览及 Chemistry、Testing、Biology 的具名业务/收入片段。",
     "完整四类业务划分（含 Others）未选；Chemistry 发现至商业化、寡核苷酸/多肽/偶联物/制剂完整范围未选。TIDES 子 task 无 Chemistry 父范围，不能借另一 task 的总额补出父子关系。"),
    ("ST-A02", "partial", ["t36", "t19"],
     "t36 的成本解释直接提到收入增速15.84%；t19 仅有一般处置组政策的一部分。",
     "无实际合计/持续/终止经营收入精确值、持续经营21.40%及本期处置导致对比期间重述的实际注释。一般处置规则不能充当本期处置事实。"),
    ("ST-A03", "missing", [],
     "未找到目标客户地区收入金额/增长及客户母公司所在地统计定义的已选支持。",
     "t2 境内外毛利率不同和 t38/其他生产基地材料均不能替代客户地区收入，更不能补出客户母公司所在地定义。"),
    ("ST-A04", "missing", [],
     "未选持续经营集团580.0亿元订单、28.8%、精确RPO及2026确认金额。",
     "TIDES订单20.2%是子业务增长，不能替代集团订单存量。一般履约义务政策不是本期RPO余额/确认计划。"),
    ("ST-A05", "partial", ["t10", "t27", "t28"],
     "Chemistry364.7亿元/25.5%、D&M199.2亿元/11.4%、TIDES113.7亿元/96.0%均在具名业务片段中。",
     "各子 task 只有管理层讨论/主要经营情况等宽标题，没有 Chemistry 父业务范围或完整子项结构。不能跨 task 将三项并列数字自动解释为父子，亦不能把差额命名纯R。"),
    ("ST-A06", "pass", ["t27"],
     "同一片段保留2025新增839、年末3452以及83/91/377/2901和全年增加22；小分子D&M主体、年度流量与年末存量明确。",
     "内容可见性通过；尚未发生模型摘要或RF实际采用，不能据此证明模型不会混用分母。"),
    ("ST-A07", "pass", ["t26"],
     "同一R发现片段保留2025交付超过42万个新化合物、R到D转化310个分子，主体、单位及不同指标均完整。",
     "内容可见性通过；尚未审实际摘要/预测。"),
    ("ST-A08", "pass", ["t11", "t28"],
     "t28独立明确TIDES2025年末在手订单增长20.2%；t11独立明确TIDES D&M客户25%及分子数量45%。每个子事实的业务与分母在自身片段内，不靠另一task补主体。",
     "各子事实内容通过，不证明后续模型采用正确；不得把45%改成收入增长。"),
    ("ST-A09", "partial", ["t22", "t23", "t24", "t29", "t30"],
     "t22独立保留2025年底小分子反应釜超过4000kL。2025年9月泰兴多肽完成建设与超过100000L两项均已选。",
     "多肽完成日期在t23/t29，体积在t24/t30；每个体积task成员均缺完成日期，每个日期task均缺体积，不能拼接为同一有日期的产能状态。物理容量仍不得自动换算收入。"),
    ("ST-A10", "pass", ["t13", "t31", "t35"],
     "t13含Testing40.4亿元/4.7%及安全评价4.6%；t31本地Testing父收入明确新分子超30%；t35自身明示Testing毛利率下降6.32个百分点及价格因素随订单转化。",
     "这些子事实分别局部完整，不借其他task补业务主体。通过仅限来源内容，非毛利率正式研究验收。"),
    ("ST-A11", "pass", ["t18", "t32"],
     "t18本地Biology收入26.8亿元/5.2%标题限定新分子收入超30%；t32本地同一Biology父标题限定集团新客户超过20%，两个分母明确分开。",
     "内容可见性通过；后续采用不能混淆新客户与新分子收入分母。"),
    ("ST-A12", "pass", ["t33"],
     "同一t33含2026总收入513–530亿元、持续经营增长18%–22%及在手订单/行业/国际贸易/监管稳定前提、非承诺和不确定性。",
     "仅年报时点前瞻指引可见性通过，不是后续更新指引或真实预测已通过。"),
    ("ST-A13", "partial", ["t17", "t51", "t52", "t53"],
     "t17含部分Chemistry及其他业务按时点确认；t51/52保留一般控制权、时段/时点标准；t53完整保留预收款先负债、履约转收入。",
     "无本期12,125,518,838.35及31,295,304,900.48元数额，也无Testing/Biology明确按时段分类。一般标准不能替代公司业务适用归属。"),
    ("ST-A14", "pass", ["t37", "t43", "t44", "t45", "t46", "t47", "t48", "t49"],
     "48.11%前五客户年度销售、美元结算/人民币升值使折算收入减少、客户研发支出和外包比例、监管/竞争及建设延误风险均有本地完整已选片段。",
     "各独立风险事实自身具备主体与条件，不将其拼成已实现结果；全文绑定FY2025年报，尚无实际摘要/预测审查。"),
]


def main():
    selection = read(CURRENT / "selection.json")
    model = read(CURRENT / "model-view.json")
    receipt = read(CURRENT / "replay-receipt.json")
    trace = read(CURRENT / "trace.json")
    checklist = read(BASE / "annual14/review.json")
    old = read(BASE / "annual14-v5/selection.json")
    pages = read(BASE / "annual14/audit-original-eight-pages.json")
    spans = {v["span_id"]: v for v in selection["selected_spans"]}
    tasks = {t["task_key"]: t for t in model["tasks"]}
    assert sha(CURRENT / "selection.json") == model["selection_sha256"] == receipt["selection_sha256"]
    assert sha(CURRENT / "trace.json") == receipt["trace_sha256"]
    assert sha(BASE / "annual14/review.json") == receipt["checklist_sha256"]
    assert model["source_sha256"] == selection["source_ref"]["content_sha256"]
    assert all(set(t["member_span_ids"]) <= spans.keys() for t in tasks.values())
    assert all(hashlib.sha256(p["text"].encode()).hexdigest() == p["text_sha256"] for p in pages["pages"])
    exact_checks = []
    for v in spans.values():
        if "chars:" not in v["locator"]:
            continue
        p = next((p for p in pages["pages"] if p["pdf_page"] == v["page_number"]), None)
        if p is None:
            continue
        match = re.search(r"chars:(\d+)-(\d+)", v["locator"])
        assert match
        start, end = map(int, match.groups())
        assert p["text"][start:end] == v["raw_text"]
        exact_checks.append(v["span_id"])
    rows = []
    for target, status, task_keys, support, gap in ASSESSMENTS:
        original = next(row for row in checklist["rows"] if row["target_id"] == target)
        local = []
        for task_key in task_keys:
            t = tasks[task_key]
            local.append({"task_key": task_key, "kind": t["kind"],
                          "member_span_ids": t["member_span_ids"],
                          "support_span_ids": t["support_span_ids"],
                          "context_span_ids": t["context_span_ids"],
                          "local_members": [{"span_id": k, "locator": spans[k]["locator"],
                                             "quote": spans[k]["raw_text"]} for k in t["member_span_ids"]]})
        rows.append({"target_id": target, "status": status, "original_gold": original["original_gold"],
                     "task_keys": task_keys,
                     "selected_span_ids": list(dict.fromkeys(k for t in local for k in t["member_span_ids"])),
                     "local_support": support, "remaining_gap_or_scope": gap, "tasks": local,
                     "fallback_counted_as_selected": False})
    oldsp = {v["span_id"]: v for v in old["selected_spans"]}
    exact_deferred = [{"locator": d["locator"], "reason": d["reason"], "used": d["used"],
                       "requested": d["requested"], "limit": d["limit"]}
                      for d in trace["budget_target_diagnostics"]]
    report = {
        "schema_version": "w08-annual14-independent-content-review/1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "/root/w08_reporting_selection_content",
        "verdict": "CONTENT_PARTIAL_UNCHANGED_7_PASS_5_PARTIAL_2_MISSING",
        "scope": "Frozen 14-target source selection and per-task content visibility only; no summary/RF adoption signoff.",
        "binding": {"selection_sha256": sha(CURRENT / "selection.json"),
                    "model_view_sha256": sha(CURRENT / "model-view.json"),
                    "replay_receipt_sha256": sha(CURRENT / "replay-receipt.json"),
                    "trace_sha256": sha(CURRENT / "trace.json"),
                    "checklist_sha256": sha(BASE / "annual14/review.json"),
                    "original_eight_pages_sha256": sha(BASE / "annual14/audit-original-eight-pages.json"),
                    "source_ref": selection["source_ref"],
                    "producer_source_digest": receipt["source_digest"],
                    "producer_changed_source_sha256": receipt["changed_source_sha256"]},
        "verification": {"all_receipt_hashes_match": True, "all_task_members_exist": True,
                         "all_eight_page_text_hashes_match": True,
                         "exact_selected_page_offset_matches": len(exact_checks),
                         "unavailable_page_offsets_not_claimed_verified": True,
                         "all_96_selected_spans_and_55_task_member_sets_read": True},
        "counts": {**Counter(row["status"] for row in rows), "targets": 14},
        "observed": {"pages": selection["physical_pages"], "candidates": selection["candidate_count"],
                     "spans": selection["selected_count"], "chars": selection["selected_chars"],
                     "tasks": model["compiled_task_count"], "work_budget": selection["work_budget"],
                     "trace_last_callback_candidate_count": trace["candidate_count"],
                     "trace_last_callback_count_is_total": False},
        "targets": rows,
        "selection_delta_from_v5": {
            "removed": [{"span_id": k, "locator": oldsp[k]["locator"], "quote": oldsp[k]["raw_text"]}
                        for k in sorted(oldsp.keys() - spans.keys())],
            "added": [{"span_id": k, "locator": spans[k]["locator"], "quote": spans[k]["raw_text"]}
                      for k in sorted(spans.keys() - oldsp.keys())],
            "interpretation": "Seven template/context spans removed and seven other spans admitted, including governance/generic strategy; no frozen target count improves. No inference that every short context span is waste."},
        "exact_target_budget_deferrals": exact_deferred,
        "next_shared_root_recommendations": [
            "Audit budget allocation by local semantic bundle value and actual marginal closure cost, not section blacklist or company gold labels. Scope/owner/current-state/qualification bundles should compete coherently with generic policy/governance and repeated wide headings within unchanged limits.",
            "Preserve explicit business parent-child ownership and adjacent dated state relationships in the task-local dependency closure. Regression cases should use unknown companies/alternate formatting; do not increase all context globally or insert Chemistry/TIDES literals into ranking.",
            "For exact reporting amounts use a scoped SourceRef/API retrieval obligation with identity/period/unit/definition and actual-use proof. Keep narrative business recognition and comparable-scope/restatement definitions. Do not demand entire financial-table slicing or count unexecuted fallback/API calls as success.",
            "Use the unchanged fourteen targets and seven positive controls after the common fix; classify missing local links separately from missing originals, selection deferral and model failures."],
        "limitations": ["No LLM request or response was produced or judged.",
                        "No PDF was reparsed or original bytes newly downloaded by reviewer.",
                        "Frozen source quotes are known originals, not selected/model-used evidence.",
                        "Reporting classifier independent tests are separate engineering evidence, not content pass.",
                        "Trace last-callback count470 is not the1526 total; unobserved stages remain unknown."],
        "writes": "Only this content-review directory.",
        "external_model_calls": 0, "downloads": 0, "raw_copies": 0,
    }
    (HERE / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# W08 年报14项独立内容复审", "", "## 结论", "",
             "**7 pass / 5 partial / 2 missing，与V5相同；不构成正式摘要或RF采用验收通过。**", "",
             "本轮96片段、55个真实任务完整读取。249页、1526候选、7689字符，工作量8,845,814/16,000,000。",
             "reporting规则修正实际移除了7个模板/上下文片段，但新增的7个片段含治理、通用战略等，尚未提升冻结gold内容覆盖。不能将分类测试通过等同于业务内容通过。", "",
             "## 版本与范围", "",
             f"- Selection SHA: `{report['binding']['selection_sha256']}`",
             f"- Model view SHA: `{report['binding']['model_view_sha256']}`",
             f"- Source SHA: `{model['source_sha256']}`",
             f"- 本地原文页所覆盖的 {len(exact_checks)} 个已选字符区间逐字匹配；其余页未宣称独立字节复验。",
             "- 原文fallback只作检查清单的已知事实，不当成已选材料。不跨task补缺失主体、日期或前提。",
             "- trace470是最后回调记录的候选数，全流程1526，不能混淆。", "",
             "## 逐项结果", "", "| 目标 | 状态 | 本轮task | 剩余事项/边界 |", "|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['target_id']} | {row['status']} | {', '.join(row['task_keys']) or '无'} | {row['remaining_gap_or_scope']} |")
    lines += ["", "各task真实成员ID、locator、完整局部片段、已知支持和未满足的gold见同目录 `report.json`。", "",
              "## 下一步共用根因", "",
              "1. **预算的语义包竞争顺序仍未解决。** 第11页完整四业务scope、集团在手订单/地区收入，第119页Chemistry完整scope，本期收入/重述、RPO确认计划及业务确认分类等有逐项 `budget_full` 留证。不要继续只删几个模板，需比较所需上下文闭包的边际成本、重复宽标题与事实覆盖价值，修共享分配逻辑；不提高96上限，不按公司gold硬排。",
              "2. **局部依赖不完整。** Chemistry父范围与子业务、日期与物理容量要通过通用结构/相邻句语义关系带入各task；不能依赖模型看另一task或扩大所有上下文。",
              "3. **财务精确值走按需证据路径。** 数字可从SourceRef/API按需拿，保留经营范围、重述、单位与时点定义。未真实调用/采用不能算完成；不要求全表切片。",
              "4. **复验需留正控制。** 7条pass须继续保留，用原14项清单回归并加其他公司的同类正反例；本次不新造公司特判。", "",
              "## 审查边界", "",
              "只写本审查目录；未改代码、gold、PWF总文档、外包区或生产资料；无新下载、模型调用、密钥读取和PDF重解析。"]
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "offset_matches": len(exact_checks),
                      "report_bytes": (HERE / "report.json").stat().st_size,
                      "selection_sha256": report["binding"]["selection_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
