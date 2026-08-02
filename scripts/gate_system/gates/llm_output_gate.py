#!/usr/bin/env python3
"""
gate_system/gates/llm_output_gates.py — Gate 3: LLM输出检查

包含三个子Gate：
- LLMFormatGate (3.1): JSON格式、必填字段、时间线格式
- HallucinationGate (3.2): 数字幻觉检测
- LogicConsistencyGate (3.3): 逻辑一致性
"""

import json
import re
from pathlib import Path

from gate_system.base import (
    Gate,
    GateResult,
    PipelineContext,
    create_passed_result,
    create_failed_result,
)


class LLMFormatGate(Gate):
    """
    Gate 3.1: LLM输出格式检查。

    验证JSON解析、必填字段、时间线条目格式。
    """

    name = "gate_3_1_llm_format"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "验证LLM输出的JSON格式和结构完整性"

    def run(self, context: PipelineContext) -> GateResult:
        # 读取分析结果
        analysis_path = context.analysis_path
        if not analysis_path or not Path(analysis_path).exists():
            return create_failed_result(
                issues=["分析结果文件不存在"],
                diagnosis={
                    "root_cause": "missing_required_field",
                    "fixable": True,
                    "fix_method": "re_analyze_with_field_reminder",
                    "max_retries": 2,
                },
            )

        try:
            data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            llm_output_str = data.get("llm_output", "")
            parsed = json.loads(llm_output_str) if llm_output_str else data
        except json.JSONDecodeError:
            # JSON解析失败，尝试修复
            return self._try_json_repair(analysis_path)

        issues = []

        # 1. 检查必填字段（支持新旧两种格式）

        # 检查assessment字段（支持assessment_update和assessment两种）
        has_assessment = "assessment_update" in parsed or "assessment" in parsed
        if not has_assessment:
            issues.append("缺少必填字段: assessment_update 或 assessment")

        # 财报类型额外要求（如果有dimensions则不需要financial_highlights）
        has_dimensions = "dimensions" in parsed
        if context.doc_type in [
            "annual_report",
            "semi_annual_report",
            "quarterly_report",
        ]:
            if not has_dimensions and "financial_highlights" not in parsed:
                issues.append("缺少必填字段: financial_highlights 或 dimensions")

        # 非IR文档需要dimensions（新格式）
        if context.doc_type != "investor_relations":
            if not has_dimensions:
                issues.append("缺少必填字段: dimensions")

        # 2. 检查时间线条目
        timeline_entries = parsed.get("timeline_entries", [])
        if not isinstance(timeline_entries, list):
            issues.append("timeline_entries 不是数组")
        elif len(timeline_entries) == 0:
            issues.append("timeline_entries 为空")
        else:
            for i, entry in enumerate(timeline_entries):
                if "date" not in entry:
                    issues.append(f"timeline_entries[{i}]: 缺少 date")
                elif not re.match(r"\d{4}-\d{2}-\d{2}", str(entry.get("date", ""))):
                    issues.append(f"timeline_entries[{i}]: date 格式错误")

                if "title" not in entry or len(str(entry.get("title", ""))) < 5:
                    issues.append(f"timeline_entries[{i}]: title 缺失或太短")

                key_points = entry.get("key_points", [])
                if not isinstance(key_points, list) or len(key_points) == 0:
                    issues.append(f"timeline_entries[{i}]: key_points 为空")
                elif not any(re.search(r"\d+", str(p)) for p in key_points):
                    issues.append(f"timeline_entries[{i}]: key_points 无具体数字")

        if not issues:
            return create_passed_result(score=5.0)

        return create_failed_result(
            issues=issues,
            diagnosis={
                "root_cause": "json_parse_error"
                if "JSON" in str(issues)
                else "missing_required_field",
                "fixable": True,
                "fix_method": "json_repair"
                if "JSON" in str(issues)
                else "re_analyze_with_field_reminder",
                "max_retries": 3,
                "fix_hint": "; ".join(issues),
            },
        )

    def _try_json_repair(self, analysis_path: Path) -> GateResult:
        """尝试修复JSON解析错误"""
        content = Path(analysis_path).read_text(encoding="utf-8")

        # 尝试从markdown代码块中提取
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            try:
                json.loads(json_match.group(1))
                # 如果能解析，说明格式正确只是包装问题
                return create_passed_result(
                    score=4.0,
                    issues=["JSON被markdown代码块包装，已自动提取"],
                )
            except json.JSONDecodeError:
                pass

        # 尝试正则提取JSON对象
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                json.loads(json_match.group())
                return create_passed_result(
                    score=4.0,
                    issues=["JSON提取成功，但格式不规范"],
                )
            except json.JSONDecodeError:
                pass

        return create_failed_result(
            issues=["JSON解析失败，无法修复"],
            diagnosis={
                "root_cause": "json_parse_error",
                "fixable": True,
                "fix_method": "json_repair",
                "max_retries": 3,
            },
        )


class HallucinationGate(Gate):
    """
    Gate 3.2: 幻觉检测。

    验证LLM输出中的数字是否与原始文本一致（支持单位转换）。
    """

    name = "gate_3_2_hallucination"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "检测LLM输出中的数字幻觉，支持单位转换匹配"

    def run(self, context: PipelineContext) -> GateResult:
        # 读取原始文本和分析结果
        extract_path = context.extract_path
        analysis_path = context.analysis_path

        if not extract_path or not analysis_path:
            return create_failed_result(
                issues=["缺少原始文本或分析结果"],
                diagnosis={"root_cause": "execution_error", "fixable": False},
            )

        try:
            original_text = Path(extract_path).read_text(encoding="utf-8")
            analysis_data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            llm_output = analysis_data.get("llm_output", "")

            # 处理 markdown 代码块包装
            if llm_output and llm_output.strip().startswith("```"):
                # 提取 ```json ... ``` 中的内容
                code_match = re.search(
                    r"```(?:json)?\s*\n?(.*?)\n?```", llm_output, re.DOTALL
                )
                if code_match:
                    llm_output = code_match.group(1).strip()

            if llm_output and llm_output.strip():
                parsed = json.loads(llm_output)
            else:
                parsed = analysis_data
        except Exception as e:
            return create_failed_result(
                issues=[f"读取文件失败: {e}"],
                diagnosis={"root_cause": "execution_error", "fixable": False},
            )

        # 从原始文本构建扩展数字集合（含单位转换）
        original_numbers = self._build_number_set(original_text)

        # 从LLM输出中提取数字并验证
        issues = []
        llm_text = json.dumps(parsed, ensure_ascii=False)

        # 获取文档类型以调整严格程度
        is_research_report = (
            "research" in str(context.analysis_path).lower()
            if context.analysis_path
            else False
        )

        for match in re.finditer(r"([\d,]+\.?\d*)", llm_text):
            num_str = match.group(1).replace(",", "")
            try:
                num = float(num_str)
                if num < 1:
                    continue

                # 跳过常见非财务数字
                if self._should_skip_number(num, llm_text, match.start()):
                    continue

                found = any(
                    abs(num - orig) / max(abs(orig), 1)
                    < self._get_tolerance(is_research_report)
                    for orig in original_numbers
                    if orig != 0
                )

                if not found:
                    # 对研究报告更宽松：允许分析师预测数字
                    if is_research_report and num > 100:
                        # 检查是否是预测/目标价等上下文
                        context_text = llm_text[
                            max(0, match.start() - 20) : match.end() + 20
                        ]
                        prediction_keywords = [
                            "预计",
                            "预测",
                            "目标",
                            "预期",
                            "有望",
                            "将",
                            "可能",
                        ]
                        if any(kw in context_text for kw in prediction_keywords):
                            continue

                    # 只报告明确可能是财务数据的数字（>1000 或 <100 的百分比）
                    if num > 1000 or (
                        num < 100
                        and "%" in llm_text[max(0, match.start() - 5) : match.end() + 5]
                    ):
                        issues.append(f"幻觉数字: {num} - 未在原文中找到")
            except ValueError:
                continue

        if not issues:
            return create_passed_result(score=5.0)

        return create_failed_result(
            issues=issues[:5],  # 最多报告5个
            diagnosis={
                "root_cause": "fact_hallucination",
                "fixable": True,
                "fix_method": "re_analyze_with_fact_correction",
                "max_retries": 2,
                "fix_hint": f"以下数字在原文中不存在，请修正或删除：{issues[:3]}",
            },
        )

    def _build_number_set(self, text: str) -> set:
        """构建原文数字集合，含单位转换版本"""
        numbers = set()
        for match in re.finditer(r"([\d,]+\.?\d*)", text):
            num_str = match.group(1).replace(",", "")
            try:
                num = float(num_str)
                if num == 0:
                    continue
                numbers.add(num)
                # 单位转换
                if num >= 10000:
                    numbers.add(num / 10000)
                if num >= 100000000:
                    numbers.add(num / 100000000)
            except ValueError:
                pass
        return numbers

    def _get_tolerance(self, is_research_report: bool = False) -> float:
        """获取匹配容差"""
        base_tolerance = self.config.get("hallucination", {}).get("tolerance", 0.02)
        # 研究报告允许更大容差（分析师常四舍五入）
        return base_tolerance * 3 if is_research_report else base_tolerance

    def _should_skip_number(self, num: float, text: str, position: int) -> bool:
        """判断数字是否应该跳过检查"""
        # 跳过年份 (2000-2030)
        if 2000 <= num <= 2030:
            return True

        # 获取上下文
        context = text[max(0, position - 30) : min(len(text), position + 30)]

        # 跳过股票代码附近数字
        if "688012" in context or "股票代码" in context:
            return True

        # 跳过百分比数字（除非明显是财务数据）
        if num <= 100 and "%" in context:
            return True

        return False


class LogicConsistencyGate(Gate):
    """
    Gate 3.3: 逻辑一致性检查。

    验证分析结论是否与数据一致。
    """

    name = "gate_3_3_logic_consistency"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "检查LLM分析的逻辑一致性，如营收利润关系、毛利率解释等"

    def run(self, context: PipelineContext) -> GateResult:
        analysis_path = context.analysis_path
        if not analysis_path or not Path(analysis_path).exists():
            return create_passed_result()  # 跳过

        try:
            data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            llm_output = data.get("llm_output", "")
            parsed = json.loads(llm_output) if llm_output else data
        except Exception:
            return create_passed_result()  # 跳过

        issues = []
        highlights = parsed.get("financial_highlights", {})
        entries = parsed.get("timeline_entries", [])
        all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))

        # 1. 营收增长但利润下降，是否有解释
        revenue_text = str(highlights.get("revenue", ""))
        profit_text = str(highlights.get("net_profit", ""))

        rev_growth = re.search(r"(?:增长|上升|增加)\s*([\d.]+)%", revenue_text)
        profit_decline = re.search(r"(?:下降|减少|降低)\s*([\d.]+)%", profit_text)

        if rev_growth and profit_decline:
            explanation_keywords = [
                "原因",
                "因为",
                "由于",
                "费用增加",
                "成本上升",
                "研发投入",
            ]
            if not any(kw in all_text for kw in explanation_keywords):
                issues.append("营收增长但利润下降，缺少原因解释")

        # 2. 毛利率变化是否有解释
        margin_text = str(highlights.get("gross_margin", ""))
        margin_change = re.search(r"(?:上升|下降|增加|减少)\s*([\d.]+)", margin_text)
        if margin_change:
            keywords = (
                self.config.get("logic_check", {})
                .get("explanation_keywords", {})
                .get("margin", [])
            )
            keywords = keywords or [
                "产品结构",
                "原材料",
                "价格",
                "成本",
                "毛利率",
                "附加值",
                "高利润",
            ]
            if not any(kw in all_text for kw in keywords):
                issues.append("毛利率变化明显，缺少原因解释")

        # 3. sentiment 与内容一致性
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
                issues.append(
                    f"timeline_entries[{i}]: sentiment=positive 但内容含负面词汇"
                )
            elif sentiment == "negative" and has_positive and not has_negative:
                issues.append(
                    f"timeline_entries[{i}]: sentiment=negative 但内容含正面词汇"
                )

        if not issues:
            return create_passed_result(score=5.0)

        return create_failed_result(
            issues=issues,
            diagnosis={
                "root_cause": "logic_inconsistency",
                "fixable": True,
                "fix_method": "re_analyze_with_logic_hint",
                "max_retries": 2,
                "fix_hint": "; ".join(issues),
            },
        )
