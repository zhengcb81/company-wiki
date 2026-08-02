#!/usr/bin/env python3
"""
llm_output_validator.py — LLM 输出验证模块

验证 LLM 输出的 JSON 格式、数字一致性、逻辑检查。
不依赖 LLM 调用，纯规则验证。

用法：
    from llm_output_validator import validate_llm_output, detect_hallucination

    # 验证 LLM 输出
    result = validate_llm_output(llm_json, original_text)

    # 幻觉检测
    hallucination = detect_hallucination(llm_json, original_text)
"""

import json
import re
from typing import Dict, List, Optional, Tuple


def validate_json_format(llm_output: str) -> Tuple[bool, Optional[Dict], str]:
    """
    验证 LLM 输出是否为有效 JSON。

    返回: (is_valid, parsed_json, error_message)
    """
    # 尝试直接解析
    try:
        parsed = json.loads(llm_output)
        return True, parsed, ""
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", llm_output, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            return True, parsed, ""
        except json.JSONDecodeError:
            pass

    # 尝试从文本中提取 JSON 对象
    json_match = re.search(r"\{[\s\S]*\}", llm_output)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return True, parsed, ""
        except json.JSONDecodeError:
            pass

    return False, None, "无法解析为有效JSON"


def validate_required_fields(parsed: Dict, doc_type: str) -> Tuple[bool, List[str]]:
    """
    验证必填字段。

    返回: (all_present, missing_fields)
    """
    # 通用必填字段（支持新旧两种格式）
    required = ["timeline_entries", "key_insights"]

    # 检查assessment字段（支持assessment_update和assessment两种）
    has_assessment = "assessment_update" in parsed or "assessment" in parsed
    if not has_assessment:
        required.append("assessment_update 或 assessment")

    # 检查是否有dimensions字段（新格式）
    has_dimensions = "dimensions" in parsed

    # 财报类型额外要求（如果有dimensions则不需要financial_highlights）
    if doc_type in ["annual_report", "semi_annual_report", "quarterly_report"]:
        if not has_dimensions:
            required.append("financial_highlights")

    # 非IR文档需要dimensions（新格式）
    if doc_type != "investor_relations":
        if not has_dimensions:
            required.append("dimensions")

    missing = [f for f in required if f not in parsed]
    return len(missing) == 0, missing


def validate_timeline_entries(entries: List[Dict]) -> Tuple[bool, List[str]]:
    """
    验证时间线条目格式。

    返回: (is_valid, issues)
    """
    issues = []

    if not isinstance(entries, list):
        return False, ["timeline_entries 不是数组"]

    for i, entry in enumerate(entries):
        prefix = f"timeline_entries[{i}]"

        # 必填字段
        if "date" not in entry:
            issues.append(f"{prefix}: 缺少 date")
        elif not re.match(r"\d{4}-\d{2}-\d{2}", str(entry.get("date", ""))):
            issues.append(f"{prefix}: date 格式错误")

        if "title" not in entry:
            issues.append(f"{prefix}: 缺少 title")
        elif len(str(entry.get("title", ""))) < 5:
            issues.append(f"{prefix}: title 过短")

        if "key_points" not in entry:
            issues.append(f"{prefix}: 缺少 key_points")
        elif not isinstance(entry.get("key_points"), list):
            issues.append(f"{prefix}: key_points 不是数组")
        elif len(entry.get("key_points", [])) == 0:
            issues.append(f"{prefix}: key_points 为空")

        # 检查 key_points 是否包含具体数字
        key_points = entry.get("key_points", [])
        has_numbers = any(re.search(r"\d+", str(p)) for p in key_points)
        if not has_numbers and key_points:
            issues.append(f"{prefix}: key_points 无具体数字（可能是空泛描述）")

    return len(issues) == 0, issues


def validate_financial_highlights(
    highlights: Dict, original_text: str
) -> Tuple[bool, List[str], Dict]:
    """
    验证财务数据亮点，并与原文对比。
    支持单位转换（元、万元、亿元）。

    返回: (is_valid, issues, validated_data)
    """
    issues = []
    validated = {}

    if not isinstance(highlights, dict):
        return False, ["financial_highlights 不是对象"], {}

    # 从原文中提取所有数字，并构建单位转换后的扩展集合
    original_numbers_expanded = set()
    for match in re.finditer(r"([\d,]+\.?\d*)", original_text):
        num_str = match.group(1).replace(",", "")
        try:
            num = float(num_str)
            if num == 0:
                continue
            original_numbers_expanded.add(num)
            # 元 → 万元
            if num >= 10000:
                original_numbers_expanded.add(num / 10000)
            # 元 → 亿元
            if num >= 100000000:
                original_numbers_expanded.add(num / 100000000)
            # 万元 → 亿元
            if num >= 10000:
                original_numbers_expanded.add(num / 10000)
        except ValueError:
            pass

    # 验证每个财务指标
    for key, value in highlights.items():
        if isinstance(value, str):
            # 提取字符串中的数字
            numbers_in_value = re.findall(r"([\d,]+\.?\d*)", value)
            for num_str in numbers_in_value:
                num_str_clean = num_str.replace(",", "")
                try:
                    num = float(num_str_clean)
                    # 检查数字是否在原文中出现（允许一定的四舍五入误差，考虑单位转换）
                    found = any(
                        abs(num - orig) / max(abs(orig), 1) < 0.02
                        for orig in original_numbers_expanded
                        if orig != 0
                    )
                    if not found and num > 1:  # 忽略小数字（可能是比率）
                        issues.append(f"{key}: 数字 {num} 未在原文中找到")
                    validated[key] = {"value": value, "verified": found}
                except ValueError:
                    pass
        elif isinstance(value, (int, float)):
            found = any(
                abs(value - orig) / max(abs(orig), 1) < 0.02
                for orig in original_numbers_expanded
                if orig != 0
            )
            if not found and value > 1:
                issues.append(f"{key}: 数字 {value} 未在原文中找到")
            validated[key] = {"value": value, "verified": found}

    return len(issues) == 0, issues, validated


def check_logic_consistency(parsed: Dict) -> Tuple[bool, List[str]]:
    """
    逻辑一致性检查。

    返回: (is_consistent, issues)
    """
    issues = []

    highlights = parsed.get("financial_highlights", {})
    entries = parsed.get("timeline_entries", [])

    # 检查1：如果营收增长但利润下降，应该有解释
    revenue_text = str(highlights.get("revenue", ""))
    profit_text = str(highlights.get("net_profit", ""))

    revenue_growth = re.search(r"增长\s*([\d.]+)%", revenue_text)
    profit_growth = re.search(r"(下降|减少)\s*([\d.]+)%", profit_text)

    if revenue_growth and profit_growth:
        # 营收增长但利润下降，检查是否有解释
        all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))
        explanation_keywords = [
            "原因",
            "因为",
            "由于",
            "费用增加",
            "成本上升",
            "研发投入",
        ]
        has_explanation = any(kw in all_text for kw in explanation_keywords)
        if not has_explanation:
            issues.append("营收增长但利润下降，缺少原因解释")

    # 检查2：毛利率变化应该有解释
    margin_text = str(highlights.get("gross_margin", ""))
    margin_change = re.search(r"(上升|下降|增加|减少)\s*([\d.]+)", margin_text)
    if margin_change:
        all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))
        # 扩展关键词以覆盖更多表达方式
        explanation_keywords = [
            "产品结构",
            "原材料",
            "价格",
            "成本",
            "毛利率",
            "附加值",
            "高利润",
            "产品",
            "收入结构",
            "业务结构",
            "海洋类",
            "海缆",
            "工程服务",
            "高附加值",
        ]
        has_explanation = any(kw in all_text for kw in explanation_keywords)
        if not has_explanation:
            issues.append("毛利率变化明显，缺少原因解释")

    # 检查3：sentiment 与 key_points 一致性
    for i, entry in enumerate(entries):
        sentiment = entry.get("sentiment", "neutral")
        key_points = entry.get("key_points", [])

        negative_keywords = ["下降", "减少", "亏损", "风险", "困难", "挑战"]
        positive_keywords = ["增长", "提升", "突破", "创新", "领先"]

        has_negative = any(
            any(kw in str(p) for kw in negative_keywords) for p in key_points
        )
        has_positive = any(
            any(kw in str(p) for kw in positive_keywords) for p in key_points
        )

        if sentiment == "positive" and has_negative and not has_positive:
            issues.append(f"timeline_entries[{i}]: sentiment=positive 但内容含负面词汇")
        elif sentiment == "negative" and has_positive and not has_negative:
            issues.append(f"timeline_entries[{i}]: sentiment=negative 但内容含正面词汇")

    return len(issues) == 0, issues


def detect_hallucination(
    parsed: Dict, original_text: str, doc_type: str = "unknown"
) -> Dict:
    """
    幻觉检测：检查 LLM 输出中的数字是否与原文一致。
    支持单位转换检测（元→万元→亿元）。

    对研究报告更宽松（允许分析师预测数字）。

    返回: {
        "has_hallucination": bool,
        "hallucinated_numbers": list,
        "verified_numbers": list,
        "uncertain_numbers": list
    }
    """
    hallucinated = []
    verified = []
    uncertain = []

    # 判断文档类型
    is_research = (
        doc_type in ["research_report", "research"] or "research" in doc_type.lower()
    )
    is_quarterly = doc_type in ["quarterly_report", "quarterly"]

    # 获取容差：研究报告和季度报告更宽松
    if is_research:
        tolerance = 0.05  # 5% - 研究报告有预测数据
        min_flag_value = 1000  # 只标记>1000的数字
    elif is_quarterly:
        tolerance = 0.03  # 3% - 季度报告较短，LLM可能自行计算
        min_flag_value = 500  # 只标记>500的数字
    else:
        tolerance = 0.01  # 1% - 年报/半年报更严格
        min_flag_value = 100

    # 从原文中提取所有数字（保留上下文）
    original_number_contexts = []
    for match in re.finditer(r"(?:[^\d]|^)([\d,]+\.?\d*)(?:[^\d]|$)", original_text):
        num_str = match.group(1).replace(",", "")
        try:
            num = float(num_str)
            if num == 0:
                continue
            original_number_contexts.append((num, match.group(0)))
        except ValueError:
            pass

    # 构建所有原始数字的集合（包括单位转换后的版本）
    original_numbers_expanded = set()
    for orig_num, _ in original_number_contexts:
        original_numbers_expanded.add(orig_num)
        # 万元 → 元
        original_numbers_expanded.add(orig_num * 10000)
        # 亿元 → 元
        original_numbers_expanded.add(orig_num * 100000000)
        # 元 → 万元
        if orig_num > 10000:
            original_numbers_expanded.add(orig_num / 10000)
        # 元 → 亿元
        if orig_num > 100000000:
            original_numbers_expanded.add(orig_num / 100000000)

    # 从 LLM 输出中提取所有数字
    llm_text = json.dumps(parsed, ensure_ascii=False)
    for match in re.finditer(r"([\d,]+\.?\d*)", llm_text):
        num_str = match.group(1).replace(",", "")
        try:
            num = float(num_str)
            if num < 1:  # 忽略小数字
                continue

            # 跳过年份
            if 2000 <= num <= 2030:
                continue

            # 检查是否在原文中出现（或单位转换后出现）
            found = False
            for orig_num in original_numbers_expanded:
                if orig_num == 0:
                    continue
                if abs(num - orig_num) / max(abs(orig_num), 1) < tolerance:
                    found = True
                    verified.append({"value": num})
                    break

            if not found:
                [n for n in original_numbers_expanded if 3900 <= n <= 4100]

            if not found:
                # 检查是否是合理的派生数字（如百分比、比率）
                if num <= 100:  # 可能是百分比
                    uncertain.append({"value": num, "reason": "可能是百分比或比率"})
                elif is_research and num < min_flag_value:
                    # 研究报告中小数字可能是合理预测
                    uncertain.append({"value": num, "reason": "研究报告中的预测数字"})
                else:
                    hallucinated.append({"value": num, "reason": "未在原文中找到"})
        except ValueError:
            pass

    return {
        "has_hallucination": len(hallucinated) > 0,
        "hallucinated_numbers": hallucinated,
        "verified_numbers": verified,
        "uncertain_numbers": uncertain,
    }


def validate_llm_output(
    llm_output: str, original_text: str, doc_type: str = "unknown"
) -> Dict:
    """
    完整的 LLM 输出验证。

    返回: {
        "status": "passed|failed|needs_review",
        "json_valid": bool,
        "parsed": dict or None,
        "field_check": {"passed": bool, "missing": list},
        "timeline_check": {"passed": bool, "issues": list},
        "financial_check": {"passed": bool, "issues": list, "validated": dict},
        "logic_check": {"passed": bool, "issues": list},
        "hallucination": {...},
        "all_issues": list
    }
    """
    all_issues = []

    # 步骤1：JSON格式验证
    json_valid, parsed, json_error = validate_json_format(llm_output)
    if not json_valid:
        return {
            "status": "failed",
            "json_valid": False,
            "parsed": None,
            "field_check": {"passed": False, "missing": []},
            "timeline_check": {"passed": False, "issues": [json_error]},
            "financial_check": {"passed": False, "issues": [], "validated": {}},
            "logic_check": {"passed": False, "issues": []},
            "hallucination": {
                "has_hallucination": False,
                "hallucinated_numbers": [],
                "verified_numbers": [],
                "uncertain_numbers": [],
            },
            "all_issues": [json_error],
        }

    # 步骤2：必填字段验证
    if parsed is None:
        parsed = {}
    fields_ok, missing = validate_required_fields(parsed, doc_type)
    if not fields_ok:
        all_issues.append(f"缺少必填字段: {missing}")

    # 步骤3：时间线条目验证
    timeline_ok, timeline_issues = validate_timeline_entries(
        parsed.get("timeline_entries", [])
    )
    all_issues.extend(timeline_issues)

    # 步骤4：财务数据验证
    financial_ok, financial_issues, validated_data = validate_financial_highlights(
        parsed.get("financial_highlights", {}), original_text
    )
    all_issues.extend(financial_issues)

    # 步骤5：逻辑一致性检查
    logic_ok, logic_issues = check_logic_consistency(parsed)
    all_issues.extend(logic_issues)

    # 步骤6：幻觉检测
    hallucination = detect_hallucination(parsed, original_text, doc_type)
    if hallucination["has_hallucination"]:
        for h in hallucination["hallucinated_numbers"]:
            all_issues.append(f"幻觉数字: {h['value']} - {h['reason']}")

    # 确定总体状态
    if not json_valid or not fields_ok:
        status = "failed"
    elif hallucination["has_hallucination"] or (
        not timeline_ok and len(timeline_issues) > 3
    ):
        status = "failed"
    elif not financial_ok or not logic_ok or not timeline_ok:
        status = "needs_review"
    else:
        status = "passed"

    return {
        "status": status,
        "json_valid": json_valid,
        "parsed": parsed,
        "field_check": {"passed": fields_ok, "missing": missing},
        "timeline_check": {"passed": timeline_ok, "issues": timeline_issues},
        "financial_check": {
            "passed": financial_ok,
            "issues": financial_issues,
            "validated": validated_data,
        },
        "logic_check": {"passed": logic_ok, "issues": logic_issues},
        "hallucination": hallucination,
        "all_issues": all_issues,
    }


# ── CLI 测试 ──────────────────────────────
if __name__ == "__main__":

    # 测试用例：正常输出
    test_output = """
    {
        "timeline_entries": [
            {
                "date": "2016-12-31",
                "title": "东方电缆2016年年报发布",
                "key_points": [
                    "营业收入17.42亿元，同比下降4.39%",
                    "净利润5185万元，同比增长2.92%",
                    "毛利率13.16%，同比增加2.14个百分点"
                ],
                "answered_questions": ["财务表现"],
                "importance": 0.8,
                "sentiment": "neutral",
                "source_type": "财报"
            }
        ],
        "financial_highlights": {
            "revenue": "17.42亿元，同比下降4.39%",
            "net_profit": "5185万元，同比增长2.92%",
            "gross_margin": "13.16%"
        },
        "assessment_update": "公司业绩平稳，海缆业务增长明显",
        "contradictions": [],
        "new_questions": ["海缆业务能否持续增长？"],
        "key_insights": ["海缆收入同比增长27.02%"]
    }
    """

    test_text = "公司实现营业收入174,158.79万元，净利润51,853,356.71元，毛利率13.16%"

    print("LLM 输出验证测试")
    print("=" * 60)

    result = validate_llm_output(test_output, test_text, "annual_report")

    print(f"状态: {result['status']}")
    print(f"JSON有效: {result['json_valid']}")
    print(f"字段检查: {result['field_check']['passed']}")
    print(f"时间线检查: {result['timeline_check']['passed']}")
    print(f"财务检查: {result['financial_check']['passed']}")
    print(f"逻辑检查: {result['logic_check']['passed']}")
    print(f"幻觉检测: {result['hallucination']['has_hallucination']}")

    if result["all_issues"]:
        print(f"\n问题 ({len(result['all_issues'])}):")
        for issue in result["all_issues"]:
            print(f"  - {issue}")
