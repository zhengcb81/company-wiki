#!/usr/bin/env python3
"""
stage4_review.py — 阶段4 Pipeline：分析师审查

从 companies/{name}/extracts/ 读取 LLM 分析结果，
进行金融分析师视角的内容审查。

用法：
    python scripts/stage4_review.py                    # 审查所有已分析文件
    python scripts/stage4_review.py --company 北方华创  # 只审查指定公司
    python scripts/stage4_review.py --check             # 列出待审查文件
    python scripts/stage4_review.py --dry-run           # 预览
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT


# ── 5维度评分系统 ──────────────────────────


def score_information_gain(entries: list) -> tuple:
    """
    信息增量评分（1-5分）
    检查时间线条目是否提供了新信息，而不是重复已知事实。
    """
    if not entries:
        return 1, "无时间线条目"

    scores = []
    for entry in entries:
        key_points = entry.get("key_points", [])

        # 检查是否有具体数字
        has_numbers = any(re.search(r"\d+", str(p)) for p in key_points)

        # 检查是否有新信息（不是空泛描述）
        vague_keywords = ["良好", "稳定", "持续", "不断", "进一步"]
        is_vague = all(any(kw in str(p) for kw in vague_keywords) for p in key_points)

        if has_numbers and not is_vague:
            scores.append(5)
        elif has_numbers:
            scores.append(4)
        elif not is_vague:
            scores.append(3)
        else:
            scores.append(2)

    avg_score = sum(scores) / len(scores) if scores else 1
    return round(avg_score), f"平均分{avg_score:.1f}，共{len(entries)}条"


def score_data_support(entries: list) -> tuple:
    """
    数据支撑评分（1-5分）
    检查关键观点是否有具体数字支撑。
    """
    if not entries:
        return 1, "无时间线条目"

    total_points = 0
    points_with_numbers = 0

    for entry in entries:
        key_points = entry.get("key_points", [])
        total_points += len(key_points)
        points_with_numbers += sum(1 for p in key_points if re.search(r"\d+", str(p)))

    if total_points == 0:
        return 1, "无关键要点"

    ratio = points_with_numbers / total_points

    if ratio >= 0.8:
        return 5, f"{ratio:.0%}要点含数字"
    elif ratio >= 0.6:
        return 4, f"{ratio:.0%}要点含数字"
    elif ratio >= 0.4:
        return 3, f"{ratio:.0%}要点含数字"
    elif ratio >= 0.2:
        return 2, f"{ratio:.0%}要点含数字"
    else:
        return 1, f"{ratio:.0%}要点含数字"


def score_logical_consistency(entries: list, contradictions: list) -> tuple:
    """
    逻辑自洽评分（1-5分）
    检查结论是否与数据一致，是否有明显矛盾。
    """
    issues = []

    # 检查矛盾
    if contradictions:
        issues.append(f"{len(contradictions)}个矛盾")

    # 检查 sentiment 与内容一致性
    for i, entry in enumerate(entries):
        sentiment = entry.get("sentiment", "neutral")
        key_points = entry.get("key_points", [])

        negative_keywords = ["下降", "减少", "亏损", "风险", "困难"]
        positive_keywords = ["增长", "提升", "突破", "创新"]

        has_negative = any(
            any(kw in str(p) for kw in negative_keywords) for p in key_points
        )
        has_positive = any(
            any(kw in str(p) for kw in positive_keywords) for p in key_points
        )

        if sentiment == "positive" and has_negative and not has_positive:
            issues.append(f"条目{i}情绪与内容不符")
        elif sentiment == "negative" and has_positive and not has_negative:
            issues.append(f"条目{i}情绪与内容不符")

    if not issues:
        return 5, "无矛盾"
    elif len(issues) <= 2:
        return 4, f"{len(issues)}个小问题"
    elif len(issues) <= 4:
        return 3, f"{len(issues)}个问题"
    else:
        return 2, f"{len(issues)}个问题"


def score_investment_relevance(entries: list, key_insights: list) -> tuple:
    """
    投资相关性评分（1-5分）
    检查信息对投资决策是否有影响。
    """
    # 检查是否有投资相关关键词
    investment_keywords = [
        "营收",
        "利润",
        "增长",
        "下降",
        "毛利率",
        "现金流",
        "订单",
        "产能",
        "市场份额",
        "竞争",
        "技术",
        "研发",
        "并购",
        "投资",
        "分红",
        "估值",
    ]

    all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))
    all_text += " ".join(str(i) for i in key_insights)

    found_keywords = [kw for kw in investment_keywords if kw in all_text]

    if len(found_keywords) >= 8:
        return 5, f"包含{len(found_keywords)}个投资关键词"
    elif len(found_keywords) >= 5:
        return 4, f"包含{len(found_keywords)}个投资关键词"
    elif len(found_keywords) >= 3:
        return 3, f"包含{len(found_keywords)}个投资关键词"
    else:
        return 2, f"仅包含{len(found_keywords)}个投资关键词"


def score_risk_identification(entries: list, key_insights: list) -> tuple:
    """
    风险识别评分（1-5分）
    检查是否识别了负面信息和风险。
    增强关键词覆盖：集中度、季节性、补贴依赖、资本支出等。
    """
    risk_keywords = [
        # 基础风险
        "风险",
        "下降",
        "减少",
        "亏损",
        "困难",
        "挑战",
        "不确定",
        "压力",
        "下滑",
        "恶化",
        "负债",
        "应收",
        # 集中度风险
        "客户集中",
        "供应商集中",
        "集中度",
        "大客户",
        "前五",
        "前五大",
        "依赖",
        "单一客户",
        "核心客户",
        # 季节性/周期性风险
        "季度",
        "季节性",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "回款",
        "账期",
        "周期",
        "淡季",
        "旺季",
        # 补贴/政策依赖
        "补贴",
        "政府补助",
        "非经常性",
        "政策性",
        "补助",
        "税收优惠",
        # 资本支出/现金流风险
        "资本支出",
        "投资活动",
        "在建工程",
        "扩产",
        "产能建设",
        "现金流出",
        "现金流为负",
        "资金压力",
        # 原材料/成本风险
        "原材料",
        "铜价",
        "价格波动",
        "成本上升",
        "通胀",
        # 竞争风险
        "竞争",
        "价格战",
        "市场份额",
        "替代品",
    ]

    all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))
    all_text += " ".join(str(i) for i in key_insights)

    found_risks = [kw for kw in risk_keywords if kw in all_text]
    unique_risk_categories = set()
    for kw in found_risks:
        if kw in [
            "风险",
            "下降",
            "减少",
            "亏损",
            "困难",
            "挑战",
            "不确定",
            "压力",
            "下滑",
            "恶化",
            "负债",
            "应收",
        ]:
            unique_risk_categories.add("基础")
        elif kw in [
            "客户集中",
            "供应商集中",
            "集中度",
            "大客户",
            "前五",
            "前五大",
            "依赖",
            "单一客户",
            "核心客户",
        ]:
            unique_risk_categories.add("集中度")
        elif kw in [
            "季度",
            "季节性",
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "回款",
            "账期",
            "周期",
            "淡季",
            "旺季",
        ]:
            unique_risk_categories.add("季节性")
        elif kw in ["补贴", "政府补助", "非经常性", "政策性", "补助", "税收优惠"]:
            unique_risk_categories.add("补贴依赖")
        elif kw in [
            "资本支出",
            "投资活动",
            "在建工程",
            "扩产",
            "产能建设",
            "现金流出",
            "现金流为负",
            "资金压力",
        ]:
            unique_risk_categories.add("资本支出")
        elif kw in ["原材料", "铜价", "价格波动", "成本上升", "通胀"]:
            unique_risk_categories.add("原材料")
        elif kw in ["竞争", "价格战", "市场份额", "替代品"]:
            unique_risk_categories.add("竞争")

    risk_count = len(unique_risk_categories)

    if risk_count >= 4:
        return 5, f"识别了{risk_count}类风险因素（{', '.join(unique_risk_categories)}）"
    elif risk_count >= 3:
        return 4, f"识别了{risk_count}类风险因素"
    elif risk_count >= 2:
        return 3, f"识别了{risk_count}类风险因素"
    elif risk_count >= 1:
        return 2, f"识别了{risk_count}类风险因素"
    else:
        return 1, "未识别风险因素"


def calculate_quality_score(parsed: dict) -> dict:
    """
    计算5维度质量评分。

    返回: {
        "total_score": float,
        "dimensions": {
            "information_gain": {"score": int, "reason": str},
            "data_support": {"score": int, "reason": str},
            "logical_consistency": {"score": int, "reason": str},
            "investment_relevance": {"score": int, "reason": str},
            "risk_identification": {"score": int, "reason": str},
        },
        "status": "approved|needs_revision|rejected"
    }
    """
    entries = parsed.get("timeline_entries", [])
    contradictions = parsed.get("contradictions", [])
    key_insights = parsed.get("key_insights", [])

    # 计算各维度分数
    ig_score, ig_reason = score_information_gain(entries)
    ds_score, ds_reason = score_data_support(entries)
    lc_score, lc_reason = score_logical_consistency(entries, contradictions)
    ir_score, ir_reason = score_investment_relevance(entries, key_insights)
    ri_score, ri_reason = score_risk_identification(entries, key_insights)

    # 加权平均（权重可调）
    weights = {
        "information_gain": 0.30,
        "data_support": 0.25,
        "logical_consistency": 0.20,
        "investment_relevance": 0.15,
        "risk_identification": 0.10,
    }

    total = (
        ig_score * weights["information_gain"]
        + ds_score * weights["data_support"]
        + lc_score * weights["logical_consistency"]
        + ir_score * weights["investment_relevance"]
        + ri_score * weights["risk_identification"]
    )

    # 确定状态
    if total >= 4.0:
        status = "approved"
    elif total >= 3.0:
        status = "needs_revision"
    else:
        status = "rejected"

    return {
        "total_score": round(total, 2),
        "dimensions": {
            "information_gain": {"score": ig_score, "reason": ig_reason},
            "data_support": {"score": ds_score, "reason": ds_reason},
            "logical_consistency": {"score": lc_score, "reason": lc_reason},
            "investment_relevance": {"score": ir_score, "reason": ir_reason},
            "risk_identification": {"score": ri_score, "reason": ri_reason},
        },
        "status": status,
    }


# ── 财务逻辑检查 ──────────────────────────


def check_financial_logic(parsed: dict, metadata: dict) -> dict:
    """
    财务逻辑检查。

    返回: {
        "passed": bool,
        "checks": {
            "growth_consistency": {"passed": bool, "notes": str},
            "margin_reasonableness": {"passed": bool, "notes": str},
            "cashflow_health": {"passed": bool, "notes": str},
            "balance_sheet": {"passed": bool, "notes": str},
        },
        "issues": list
    }
    """
    issues = []
    checks = {}

    highlights = parsed.get("financial_highlights", {})
    entries = parsed.get("timeline_entries", [])
    all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))

    # 检查1：增长一致性
    revenue_text = str(highlights.get("revenue", ""))
    profit_text = str(highlights.get("net_profit", ""))

    revenue_growth = re.search(r"([\d.]+)%", revenue_text)
    profit_growth = re.search(r"([\d.]+)%", profit_text)

    if revenue_growth and profit_growth:
        float(revenue_growth.group(1))
        float(profit_growth.group(1))

        # 如果营收增长但利润下降，需要解释
        if "下降" in profit_text and "增长" in revenue_text:
            if "原因" not in all_text and "由于" not in all_text:
                issues.append("营收增长但利润下降，缺少原因解释")
                checks["growth_consistency"] = {
                    "passed": False,
                    "notes": "缺少原因解释",
                }
            else:
                checks["growth_consistency"] = {"passed": True, "notes": "有原因解释"}
        else:
            checks["growth_consistency"] = {"passed": True, "notes": "增长方向一致"}
    else:
        checks["growth_consistency"] = {"passed": True, "notes": "无法判断"}

    # 检查2：毛利率合理性
    margin_text = str(highlights.get("gross_margin", ""))
    margin_match = re.search(r"([\d.]+)%", margin_text)

    if margin_match:
        margin_val = float(margin_match.group(1))
        if margin_val > 80:
            issues.append(f"毛利率异常高({margin_val}%)")
            checks["margin_reasonableness"] = {
                "passed": False,
                "notes": f"毛利率{margin_val}%异常",
            }
        elif margin_val < 0:
            issues.append(f"毛利率为负({margin_val}%)")
            checks["margin_reasonableness"] = {
                "passed": False,
                "notes": f"毛利率{margin_val}%异常",
            }
        else:
            checks["margin_reasonableness"] = {
                "passed": True,
                "notes": f"毛利率{margin_val}%正常",
            }
    else:
        checks["margin_reasonableness"] = {"passed": True, "notes": "无法判断"}

    # 检查3：现金流健康度
    cashflow_text = str(highlights.get("operating_cashflow", ""))
    if "负" in cashflow_text or "下降" in cashflow_text:
        issues.append("经营现金流为负或下降")
        checks["cashflow_health"] = {"passed": False, "notes": "现金流承压"}
    else:
        checks["cashflow_health"] = {"passed": True, "notes": "现金流正常"}

    # 检查4：资产负债（简单检查）
    if "资产负债率" in all_text:
        debt_match = re.search(r"资产负债率[^\d]*([\d.]+)%", all_text)
        if debt_match:
            debt_ratio = float(debt_match.group(1))
            if debt_ratio > 70:
                issues.append(f"资产负债率偏高({debt_ratio}%)")
                checks["balance_sheet"] = {
                    "passed": False,
                    "notes": f"资产负债率{debt_ratio}%",
                }
            else:
                checks["balance_sheet"] = {
                    "passed": True,
                    "notes": f"资产负债率{debt_ratio}%",
                }
        else:
            checks["balance_sheet"] = {"passed": True, "notes": "无法判断"}
    else:
        checks["balance_sheet"] = {"passed": True, "notes": "未提及"}

    return {
        "passed": len(issues) == 0,
        "checks": checks,
        "issues": issues,
    }


# ── 主流程 ──────────────────────────────


def review_single_file(analysis_path: Path, dry_run=False) -> dict:
    """审查单个分析结果"""
    try:
        content = analysis_path.read_text(encoding="utf-8")
        analysis = json.loads(content)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # 获取 LLM 输出
    llm_output = analysis.get("llm_output", "")
    metadata = analysis.get("metadata", {})

    # 解析 LLM 输出
    try:
        parsed = json.loads(llm_output)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", llm_output, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                return {"status": "error", "error": "无法解析LLM输出"}
        else:
            return {"status": "error", "error": "无法解析LLM输出"}

    # 计算质量评分
    quality = calculate_quality_score(parsed)

    # 财务逻辑检查
    financial = check_financial_logic(parsed, metadata)

    # 合并结果
    result = {
        "metadata": metadata,
        "quality_score": quality,
        "financial_checks": financial,
        "review_status": quality["status"],
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if dry_run:
        return {
            "status": "dry_run",
            "result": result,
        }

    # 保存审查结果
    review_path = analysis_path.with_suffix(".review.json")
    review_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "status": "success",
        "review_status": quality["status"],
        "total_score": quality["total_score"],
        "financial_passed": financial["passed"],
        "issues": financial["issues"],
        "review_path": str(review_path),
    }


def main():
    parser = argparse.ArgumentParser(description="阶段4：分析师审查")
    parser.add_argument("--company", type=str, help="只审查指定公司")
    parser.add_argument("--check", action="store_true", help="列出待审查文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="最多审查 N 个文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  阶段4：分析师审查")
    print("=" * 60)

    # 扫描待审查文件
    analysis_files = []
    companies_dir = WIKI_ROOT / "companies"

    if args.company:
        company_dirs = [companies_dir / args.company]
    else:
        company_dirs = list(companies_dir.iterdir())

    for company_dir in company_dirs:
        if not company_dir.is_dir():
            continue
        extracts_dir = company_dir / "extracts"
        if not extracts_dir.exists():
            continue
        for analysis_file in extracts_dir.rglob("*.analysis.json"):
            review_file = analysis_file.with_suffix(".review.json")
            if not review_file.exists():
                analysis_files.append(analysis_file)

    print(f"找到 {len(analysis_files)} 个待审查文件")

    if args.check:
        for f in analysis_files[:20]:
            print(f"  {f.relative_to(WIKI_ROOT)}")
        if len(analysis_files) > 20:
            print(f"  ... 还有 {len(analysis_files) - 20} 个")
        return 0

    if not analysis_files:
        print("没有待审查的文件")
        return 0

    if args.limit > 0:
        analysis_files = analysis_files[: args.limit]
        print(f"限制审查 {len(analysis_files)} 个文件")

    approved = 0
    needs_revision = 0
    rejected = 0
    errors = 0

    for i, analysis_path in enumerate(analysis_files, 1):
        print(f"\n[{i}/{len(analysis_files)}] {analysis_path.relative_to(WIKI_ROOT)}")
        result = review_single_file(analysis_path, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            review_status = result["review_status"]
            if review_status == "approved":
                approved += 1
                print(
                    f"  -> approved | score: {result['total_score']} | financial: {'passed' if result['financial_passed'] else 'failed'}"
                )
            elif review_status == "needs_revision":
                needs_revision += 1
                print(
                    f"  -> needs_revision | score: {result['total_score']} | financial: {'passed' if result['financial_passed'] else 'failed'}"
                )
                for issue in result.get("issues", [])[:2]:
                    print(f"     - {issue}")
            else:
                rejected += 1
                print(
                    f"  -> rejected | score: {result['total_score']} | financial: {'passed' if result['financial_passed'] else 'failed'}"
                )
                for issue in result.get("issues", [])[:2]:
                    print(f"     - {issue}")
        elif status == "dry_run":
            r = result["result"]
            print(
                f"  -> DRY-RUN | score: {r['quality_score']['total_score']} | {r['review_status']}"
            )
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print(
            f"完成: {approved} 通过, {needs_revision} 待修订, {rejected} 拒绝, {errors} 错误"
        )
        print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
