"""Render the independent manual 14-target judgement from frozen evidence."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
REVIEW = HERE.parent
ATTEMPT = REVIEW / "st-a05-local-flow-20261025/attempt05"
OLD_PATH = REVIEW / "annual14-current-source-review-20261025/independent/report.json"
GOLD_PATH = REVIEW / "r1-w08-material-value-20261024/content-review/report.json"
HEAD = "06c1a5839302f4e297d70a13267a8aa490eef719"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Manual content judgements after reading the complete current source quotes,
# task-local support/context, and the original pages. These are not word-hit scores.
ASSESSMENTS = {
    "ST-A01": {
        "status": "PASS", "tasks": ["t12", "t13", "t21", "t27", "t28", "t29", "t30", "t31", "t52"],
        "visible": "四业务分类在t21，Chemistry从发现到商业化及小分子/寡核苷酸/多肽/偶联物/制剂范围在t52。D&M t28、TIDES收入订单t29、客户分子t13各自在自己的context拥有p13/21 Chemistry父级及p13/22报告期引导；不再依靠另一个task的词命中补父级。",
        "remaining": "原命题所需来源/输入已齐；不得将TIDES与Chemistry全额相加。此PASS不证明模型将正确保留层级。",
        "subchecks": [("四业务分类", "PASS"), ("Chemistry完整业务范围", "PASS"), ("D&M/TIDES各自task内Chemistry父级与期间", "PASS")],
    },
    "ST-A02": {
        "status": "PARTIAL", "tasks": ["t22", "t37", "t62"],
        "visible": "t22给持续经营收入434.2亿元；t37给收入同比15.84%；t62给终止经营业务名称/范围及带歧义的数字片段。",
        "remaining": "合计45,456,165,774.18元、持续经营43,420,823,738.83元、持续经营同比21.40%及终止经营可比期重述未在当前scoped输入完整提供。2,035,342,035.35虽出现在t62，但同片段缺收入列头及币种单位，不能凭裸值绑定为精确终止经营收入。旧p15/7有单位的财务叙述不再被选，当前信息量较旧PARTIAL有所减少；不能把它称为旧裸表行。",
        "subchecks": [("持续经营约数及合计收入同比", "PASS"), ("三项精确元值与各自合并范围", "PARTIAL"), ("持续经营21.40%", "MISSING_IN_CURRENT_INPUT"), ("终止经营可比期重述", "MISSING_IN_CURRENT_INPUT")],
        "financial_route": "p7/p13/p183/p184完整来源可提供精确金额、单位、持续/终止范围、同比及重述。此次已只读验真其存在；当前RF采用和金融API调用仍OPEN/未执行，不能据存在代签。",
    },
    "ST-A03": {
        "status": "PASS", "tasks": ["t3", "t22"],
        "visible": "t22明确持续经营客户地区收入312.5/48.2/54.7/18.8亿元及各自34.3%/-4.0%/-3.5%/4.1%同比；t3保留客户母公司所在地、对比期间已调整的完整定义。",
        "remaining": "无原命题来源/输入缺项。旧混合表尾已替换成干净p16/20定义；不能把客户所在地改成生产基地所在地，也不能据此推断模型已正确采用。",
        "subchecks": [("四地区持续经营金额与同比", "PASS"), ("客户母公司所在地定义", "PASS"), ("可比期调整说明", "PASS")],
    },
    "ST-A04": {
        "status": "PASS", "tasks": ["t22", "t59"],
        "visible": "t22有2025年末持续经营在手订单580.0亿元/+28.8%；t59同一正文明确持续经营RPO 5,800,478.75万元及4,220,706.46万元预计2026确认。",
        "remaining": "无原命题来源/输入缺项；年末存量、预计下一年确认与当年收入/新增订单流量必须区分。",
        "subchecks": [("期末在手订单范围/时点/增速", "PASS"), ("精确RPO与2026确认预计", "PASS")],
    },
    "ST-A05": {
        "status": "PASS", "tasks": ["t12", "t28", "t29"],
        "visible": "t12给Chemistry364.7亿元；t28给小分子D&M199.2亿元/+11.4%，t29给TIDES113.7亿元/+96.0%，两项局部任务均带Chemistry父级与报告期引导。",
        "remaining": "原跨页父级缺口已闭合；剩余差额不能无依据命名为纯R收入，当前源也未提供这种命名。",
        "subchecks": [("三项收入及两个同比", "PASS"), ("子业务到Chemistry的任务内父级", "PASS"), ("FY2025报告期", "PASS")],
    },
    "ST-A06": {
        "status": "PASS", "tasks": ["t28"],
        "visible": "t28同一support保留2025新增839个分子、年末3452个管线及83/91/377/2901阶段结构、全年增加22个商业化及III期项目，context具名小分子D&M及Chemistry。",
        "remaining": "无原命题来源/输入缺项；新增流量、期末存量和两个阶段项目合计增量不相互替换。",
        "subchecks": [("年度新增流量", "PASS"), ("期末存量及阶段结构", "PASS"), ("商业化及III期全年增加22", "PASS")],
    },
    "ST-A07": {
        "status": "PASS", "tasks": ["t27"],
        "visible": "t27同一support明确2025年R合成交付超过42万新化合物及R到D转化310个分子，context含Chemistry父级和期间。",
        "remaining": "无原命题来源/输入缺项；化合物交付数量与转化分子数量不是同一分母或收入。",
        "subchecks": [("R交付及转化两个指标", "PASS"), ("主体/期间/单位", "PASS")],
    },
    "ST-A08": {
        "status": "PASS", "tasks": ["t13", "t29"],
        "visible": "t29同正文说明2025年末TIDES在手订单同比20.2%；t13给TIDES D&M服务客户数25%及服务分子数量45%，本地context具TIDES及Chemistry父级。",
        "remaining": "无原命题来源/输入缺项；45%是服务分子数量同比，不能改写为收入增速。",
        "subchecks": [("TIDES订单期末增速", "PASS"), ("客户与分子增速的不同指标", "PASS"), ("业务父级", "PASS")],
    },
    "ST-A09": {
        "status": "PASS", "tasks": ["t23", "t24", "t25", "t30", "t31"],
        "visible": "t23完整给2025年底小分子API反应釜超过4000kL；t24/t25与t30/t31分别把2025-09泰兴多肽建设提前完成和超过100000L体积互作support/context，14页版本带TIDES与Chemistry父级。",
        "remaining": "无原命题来源/输入缺项；这只证明时点、项目和容量在同一局部输入可见，不增添未披露的额外产能量、因果、利用率或收入换算。",
        "subchecks": [("小分子时点/物理体积/kL", "PASS"), ("多肽项目/日期/完成状态与L容量的一跳关联", "PASS")],
    },
    "ST-A10": {
        "status": "PASS", "tasks": ["t14", "t15", "t32", "t36"],
        "visible": "t14给Testing40.4亿元/+4.7%；t15带Testing父项给药物安全评价+4.6%；t32带Testing父项给新分子收入占比超30%；t36各业务具名，Testing毛利率下降6.32个百分点、市场影响/价格随订单转化体现保持完整。",
        "remaining": "无原命题来源/输入缺项；该新分子占比不能串到Biology，百分点不能改成百分比。",
        "subchecks": [("Testing收入与药物安全评价", "PASS"), ("新分子占比的Testing归属", "PASS"), ("毛利率百分点及价格原因", "PASS")],
    },
    "ST-A11": {
        "status": "PASS", "tasks": ["t16", "t20", "t33"],
        "visible": "t16给Biology26.8亿元/+5.2%；t33带Biology父项给集团超20%新客户；t20带Biology父项给本业务新分子收入超30%。",
        "remaining": "无原命题来源/输入缺项；新客户占集团新客户与新分子占本业务收入的分母不同。",
        "subchecks": [("Biology收入及同比", "PASS"), ("集团新客户与本业务新分子收入两种分母", "PASS")],
    },
    "ST-A12": {
        "status": "PASS", "tasks": ["t5", "t34"],
        "visible": "t5/t34各自把2026总收入513–530亿元、持续经营收入增长18%–22%和订单/行业/贸易监管环境前提、不构成实质承诺及不确定性放在同一局部任务。",
        "remaining": "无原命题来源/输入缺项；仅是年报披露时点的条件性早期指引，不代表已实现或后续指引更新。",
        "subchecks": [("两种口径指引及单位", "PASS"), ("前提与不确定性同任务", "PASS")],
    },
    "ST-A13": {
        "status": "PARTIAL", "tasks": ["t17", "t18", "t19", "t53", "t54", "t55", "t56", "t58"],
        "visible": "t58实际support为p184/8 chars269–473：具名本集团部分Chemistry、Testing、Biology及部分Others，并通过完整履约/收款条件及明确回指绑定时段确认，context有时段标题；t19保留部分Chemistry/部分Others时点确认；t55预收先负债、履约后转收入，t53/t54为通用控制权/时段时点规则。",
        "remaining": "持续经营按时段12,125,518,838.35元、按时点31,295,304,900.48元仍不在当前实际模型输入；原金标精确金额和分母不删除。具体Testing/Biology的叙述归属已修复，不能再记为缺；通用政策也不能冒充这两个金额。",
        "subchecks": [("Testing/Biology具名时段确认及闭合条件", "PASS"), ("部分Chemistry时点确认", "PASS"), ("预收负债到收入", "PASS"), ("两项持续经营精确元金额", "MISSING_IN_CURRENT_INPUT")],
        "financial_route": "p183完整收入确认分解表带单位、持续经营小计及两项精确元值；可按需读完整表/结构化金融来源，不应为精确三表值强塞叙述切片。此次仅验真原文，尚无当前RF采用或新金融API调用证据。",
    },
    "ST-A14": {
        "status": "PASS", "tasks": ["t38", "t43", "t44", "t45", "t46", "t49", "t50"],
        "visible": "t38前五客户销售占年度销售48.11%；t43研发预算/外包需求；t44监管；t45/t46竞争；t49建设及监管延误；t50美元结算为主、人民币升值可能降低折算收入。主体及风险条件均可见。",
        "remaining": "无原命题来源/输入缺项；条件风险不能改写成已发生事件，也不据此产生投资结论。",
        "subchecks": [("客户集中度", "PASS"), ("FX结算及条件方向", "PASS"), ("需求/竞争/监管/建设风险", "PASS")],
    },
}


def main():
    verification = load(HERE / "verification.json")
    old, selection, model, receipt = [load(p) for p in [OLD_PATH, ATTEMPT / "selection.json", ATTEMPT / "model-view.json", ATTEMPT / "replay-receipt.json"]]
    if verification["head"] != HEAD or old["counts"] != {"PASS": 10, "PARTIAL": 4, "MISSING": 0}:
        raise ValueError("Unexpected baseline")
    if sha(GOLD_PATH) != "4b68ac829e0c53e2416cac5558fb3f3ed48d6fdb5ec0c02421f6a2d74b673926":
        raise ValueError("Original gold changed")
    if not verification["all_selected_quotes_match_source"] or not verification["all_original_gold_quotes_match_source"]:
        raise ValueError("Source verification failed")
    actual = {t["task_key"]: t for t in verification["actual_task_views"]}
    evidence_by_id = {s["span_id"]: s for s in selection["selected_evidence"]}
    targets = []
    previous_pass_retention = []
    for original in old["targets"]:
        ident = original["target_id"]
        decision = ASSESSMENTS[ident]
        target_tasks = [actual[k] for k in decision["tasks"]]
        evidence = {}
        for task in target_tasks:
            for member in task["members"]:
                sid = member["span_id"]
                if sid not in evidence:
                    evidence[sid] = {k: v for k, v in member.items() if k not in ("part_key", "role")}
                    evidence[sid]["quote_sha256"] = hashlib.sha256(member["full_quote"].encode()).hexdigest()
                    evidence[sid]["actual_task_roles"] = []
                evidence[sid]["actual_task_roles"].append({"task_key": task["task_key"], "part_key": member["part_key"], "role": member["role"]})
        missing_old = [x for x in original["evidence"] if x["span_id"] not in evidence_by_id]
        identity_changes = []
        for missing in missing_old:
            exact = [x for x in selection["selected_evidence"] if x["raw_text"] == missing["full_quote"]]
            identity_changes.append({"old_span_id": missing["span_id"], "old_locator": missing["locator"],
                "old_full_quote": missing["full_quote"],
                "exact_quote_replacements": [{"span_id": x["span_id"], "locator": x["locator"]} for x in exact]})
        target = {"target_id": ident, "original_gold": original["original_gold"],
            "previous_source_input_status": original["source_input_status"],
            "source_input_status": decision["status"], "what_is_visible": decision["visible"],
            "remaining_gap_or_caution": decision["remaining"],
            "subchecks": [{"item": label, "status": status} for label, status in decision["subchecks"]],
            "current_task_keys": decision["tasks"], "evidence": list(evidence.values()),
            "prior_evidence_identity_changes": identity_changes,
            "financial_lookup_needed_for_original_gold": ident in ("ST-A02", "ST-A13"),
            "financial_lookup_scope": decision.get("financial_route"),
            "model_response_semantics": "NOT_REVIEWED", "current_rf_consumption": "OPEN"}
        targets.append(target)
        if original["source_input_status"] == "PASS":
            previous_pass_retention.append({"target_id": ident, "current_status": decision["status"],
                "semantic_coverage_retained": decision["status"] == "PASS",
                "old_missing_span_ids": [x["span_id"] for x in missing_old],
                "replacement_note": "A03's old ambiguous table tail is replaced by a clean standalone customer-parent-location note in t3." if ident == "ST-A03" else "Original evidence bodies remain present and task-local relations reviewed."})
    counts = Counter(t["source_input_status"] for t in targets)
    if len(targets) != 14 or dict(counts) != {"PASS": 12, "PARTIAL": 2} or not all(x["semantic_coverage_retained"] for x in previous_pass_retention):
        raise ValueError("Judgement or denominator mismatch")
    binding_files = [GOLD_PATH, OLD_PATH, HERE / "verification.json", HERE / "verify_current_input.py", Path(__file__),
        REVIEW / "st-a05-local-flow-20261025/independent/final-review.json",
        REVIEW / "st-a05-local-flow-20261025/independent/final-review.md",
        REVIEW / "st-a05-local-flow-20261025/verification.json",
        *(ATTEMPT / x for x in ("selection.json", "model-view.json", "trace.json", "replay-receipt.json", "parent-input-check.json")),
        REVIEW / "st-a02-table-source-20261025/source-route-receipt.json"]
    report = {"schema_version": "annual14-local-flow-independent-source-input-regrade/1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "/root/annual14_current_source_review",
        "verdict": "SOURCE_INPUT_12_PASS_2_PARTIAL_0_MISSING; MODEL_RESPONSE_NOT_REVIEWED; CURRENT_RF_OPEN",
        "scope": "Original frozen 14 annual-report propositions, current attempt05 selection and independently recompiled actual task-local model input. Not overall engineering/CI or model/RF approval.",
        "binding": {"review_commit": HEAD, "historical_replay_receipt_head": receipt["head"],
            "source_ref": verification["source_ref"], "source_original_sha_verified_via_SourceVersionReader": True,
            "product_test_sha256_at_verification": verification["product_test_sha256"],
            "actual_recompiled_model_payload_sha256": verification["actual_recompiled_model_payload_sha256"],
            "actual_recompiled_model_binding_sha256": verification["actual_recompiled_model_binding_sha256"],
            "evidence_sha256": {str(p.relative_to(ROOT)): sha(p) for p in binding_files}},
        "counts": {"PASS": 12, "PARTIAL": 2, "MISSING": 0, "targets": 14},
        "prior_source_input_counts_unchanged": old["counts"],
        "original_earliest_frozen_report_counts_unchanged": old["previous_frozen_counts_unchanged"],
        "changes_from_prior_source_input_review": {"upgraded_to_PASS": ["ST-A01", "ST-A05"],
            "remain_PARTIAL": ["ST-A02", "ST-A13"], "all_previous_10_PASS_semantically_retained": previous_pass_retention,
            "A13_narrative_scope_fixed_but_precise_financial_values_still_missing": True,
            "A02_previous_clear_financial_prose_no_longer_selected": "p15/7 chars800-970 included 4,545,616.58 CNY ten-thousands total and precise segment values; removed current selection, not mistaken for an unlabelled table row."},
        "verification": {k: verification[k] for k in ["selected_span_count", "actual_task_count", "original_block_member_checks",
            "all_selected_quotes_match_source", "all_original_gold_quotes_match_source", "all_stored_task_members_equal_current_compiler",
            "all_actual_payload_support_context_full_quotes_verified", "direct_original_pages_read", "protected_sha256", "protected_unchanged", "write_store_constructed"]},
        "bounded_replay": {"selected_chars": selection["selected_chars"], "coverage_complete": selection["coverage_complete"],
            "work_budget": receipt["work_budget"], "model_request_sent": False, "external_model_calls": 0, "downloads": 0, "raw_copies": 0},
        "targets": targets,
        "remaining_owners": [
            {"owner": "RF financial basis/source preparation using existing immutable full-source/table reader", "targets": ["ST-A02", "ST-A13"],
             "need": "Actually consume the exact table values with unit, period, continuous/discontinued scope, comparable restatement; no new API presumed or signed off."},
            {"owner": "Configured formal-summary response and paid-cache recovery acceptance", "targets": "all 14", "status": "NOT_REVIEWED"},
            {"owner": "Current RF execution/model-data adoption and investment-quality reviews", "targets": "all 14", "status": "OPEN"}],
        "ci_followup_outside_this_source_input_review": {"reviewed_commit": HEAD, "run_id": "40190090649", "reported_state": "6 failures; ROOT diagnosing product/test responsibilities",
            "root_reported_classes": ["old zero-work text-read assertions", "layout-bridge fake engine missing groups", "catalog compiler drift", "old parent material count"],
            "subsequent_source_changes": "NOT_REVIEWED; do not automatically apply this report or frozen attempt05 evidence to a later code version",
            "impact_boundary": "Source/input coverage of this frozen actual attempt is reviewed; engineering publication/CI acceptance is not approved by this report."},
        "limits": [
            "No original gold target, exact value, denominator or old report changed.",
            "PASS means the original proposition's source information and required task-local context are available, not that a model correctly summarized or RF used them.",
            "Exact financial tables remain original gold subchecks and PARTIAL targets. An available full-source route is not evidence of current financial API or RF consumption.",
            "Some structured financial detail is deliberately handled by an on-demand full-table/financial reader instead of requiring every value in narrative slices.",
            "Global parsing/geometry coverage remains partial; 112 selected spans do not establish exhaustive recall of all useful company facts.",
            "No new selection run, full suite, model response, network, paid API, download, raw copy, write Store, production/config or external-worktree modification.",
            "No temporary directories were created; only new review artifacts were written within this assigned review directory."],
        "external_model_calls": 0, "downloads": 0, "raw_copies": 0, "product_writes": 0,
        "model_response_semantics": "NOT_REVIEWED", "current_rf_consumption": "OPEN"}
    output = HERE / "report.json"
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "targets": len(targets), "report_sha256": sha(output), "bytes": output.stat().st_size}))


if __name__ == "__main__":
    main()
