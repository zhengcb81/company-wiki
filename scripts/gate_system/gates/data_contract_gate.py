#!/usr/bin/env python3
"""
gate_system/gates/data_contract_gate.py — Gate 2: 数据契约

检查 Stage 2 (结构化提取) 的输出：
- 必填字段是否存在
- 数值是否在合理范围
- 交叉字段公式验证（如 营收 >= 净利润）
"""

import json
from pathlib import Path
from typing import Dict, List

from gate_system.base import (
    Gate,
    GateResult,
    PipelineContext,
    create_passed_result,
    create_failed_result,
)


class DataContractGate(Gate):
    """
    Gate 2: 数据契约检查。

    验证 Stage 2 结构化 JSON 的数据完整性和一致性。
    """

    name = "gate_2_data_contract"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "验证结构化数据的必填字段、数值范围和交叉一致性"

    def run(self, context: PipelineContext) -> GateResult:
        # 1. 读取结构化JSON
        struct_path = context.structured_path
        if not struct_path or not Path(struct_path).exists():
            return create_failed_result(
                issues=["结构化JSON不存在"],
                diagnosis={
                    "root_cause": "missing_required_field",
                    "fixable": True,
                    "fix_method": "re_analyze_with_field_reminder",
                    "max_retries": 2,
                },
            )

        try:
            data = json.loads(Path(struct_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return create_failed_result(
                issues=["结构化JSON解析失败"],
                diagnosis={
                    "root_cause": "json_parse_error",
                    "fixable": True,
                    "fix_method": "json_repair",
                    "max_retries": 3,
                },
            )

        financial_data = data.get("financial_data", {})
        issues = []

        # 2. 检查必填字段
        required_fields = self.config.get("required_fields", [])
        missing_fields = [f for f in required_fields if f not in financial_data]
        if missing_fields:
            issues.append(f"缺少必填字段: {missing_fields}")

        # 3. 检查数值范围
        numeric_ranges = self.config.get("numeric_ranges", {})
        for field, range_config in numeric_ranges.items():
            if field not in financial_data:
                continue
            value = self._extract_numeric_value(financial_data[field])
            if value is None:
                continue

            min_val = range_config.get("min")
            max_val = range_config.get("max")

            if min_val is not None and value < min_val:
                issues.append(f"{field} 数值过低: {value} < {min_val}")
            if max_val is not None and value > max_val:
                issues.append(f"{field} 数值过高: {value} > {max_val}")

        # 4. 交叉验证
        cross_validations = self.config.get("cross_validations", [])
        for validation in cross_validations:
            formula = validation.get("formula", "")
            description = validation.get("description", "")
            if not self._check_formula(formula, financial_data):
                issues.append(f"交叉验证失败: {description} ({formula})")

        # 5. 投资者关系特殊检查
        if context.doc_type == "investor_relations":
            indicators = self.config.get("extract_indicators", [])
            text = data.get("text", "")
            for indicator in indicators:
                if not self._check_indicator_in_text(indicator, text):
                    issues.append(f"未提取关键指标: {indicator}")

        if not issues:
            return create_passed_result(score=5.0)

        # 6. 诊断
        root_cause = self._determine_root_cause(issues, missing_fields)
        diagnosis = {
            "root_cause": root_cause,
            "fixable": True,
            "fix_hint": "; ".join(issues),
            "financial_data_keys": list(financial_data.keys()),
        }

        if root_cause == "missing_required_field":
            diagnosis.update(
                {
                    "fix_method": "re_analyze_with_field_reminder",
                    "max_retries": 2,
                    "missing_fields": missing_fields,
                }
            )
        elif root_cause == "numeric_inconsistency":
            diagnosis.update(
                {
                    "fix_method": "re_analyze_with_correction",
                    "max_retries": 2,
                }
            )
        else:
            diagnosis.update(
                {
                    "fix_method": "re_analyze_with_correction",
                    "max_retries": 2,
                }
            )

        return create_failed_result(issues=issues, diagnosis=diagnosis)

    def _extract_numeric_value(self, field_data) -> float:
        """从字段数据中提取数值"""
        if isinstance(field_data, dict):
            value = field_data.get("value")
            if isinstance(value, (int, float)):
                return float(value)
        elif isinstance(field_data, (int, float)):
            return float(field_data)
        return None

    def _check_formula(self, formula: str, financial_data: Dict) -> bool:
        """
        检查简单公式是否成立。
        支持的格式: "field1 >= field2", "field1 > field2", etc.
        """
        # 解析公式
        for op in [">=", "<=", ">", "<", "=="]:
            if op in formula:
                left, right = formula.split(op, 1)
                left_val = self._get_field_value(left.strip(), financial_data)
                right_val = self._get_field_value(right.strip(), financial_data)

                if left_val is None or right_val is None:
                    return True  # 字段缺失，跳过验证

                if op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val
                elif op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == "==":
                    return abs(left_val - right_val) < 0.01

        return True

    def _get_field_value(self, field_name: str, financial_data: Dict) -> float:
        """获取字段数值"""
        if field_name not in financial_data:
            return None
        return self._extract_numeric_value(financial_data[field_name])

    def _check_indicator_in_text(self, indicator: str, text: str) -> bool:
        """检查文本中是否包含某指标关键词"""
        indicator_keywords = {
            "order_amount": ["订单", "合同金额", "中标", "签约"],
            "capacity_utilization": ["产能", "利用率", "满产", "达产"],
            "customer_names": ["客户", "主要客户", "大客户"],
            "management_guidance": ["指引", "预期", "预计", "目标"],
        }
        keywords = indicator_keywords.get(indicator, [indicator])
        return any(kw in text for kw in keywords)

    def _determine_root_cause(
        self, issues: List[str], missing_fields: List[str]
    ) -> str:
        """判断根因"""
        if missing_fields:
            return "missing_required_field"
        for issue in issues:
            if "数值" in issue and ("过低" in issue or "过高" in issue):
                return "numeric_inconsistency"
            if "交叉验证" in issue:
                return "numeric_inconsistency"
        return "schema_violation"
