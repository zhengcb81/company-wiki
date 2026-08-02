#!/usr/bin/env python3
"""
gate_system/diagnostics.py — 失败诊断引擎

分析 Gate 失败原因，输出结构化诊断信息供 RetryOrchestrator 决策。
"""

from typing import Any, Dict, List, Optional

from .base import GateResult


# ── 诊断规则库 ──────────────────────────────

DIAGNOSIS_RULES = {
    # 单位不匹配
    "unit_mismatch": {
        "root_cause": "unit_mismatch",
        "fixable": True,
        "fix_method": "re_analyze_with_unit_hint",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "数值正确但单位不匹配（元/万元/亿元）",
    },
    # 事实幻觉
    "fact_hallucination": {
        "root_cause": "fact_hallucination",
        "fixable": True,
        "fix_method": "re_analyze_with_fact_correction",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "LLM 输出包含原文中不存在的数字或事实",
    },
    # JSON 解析错误
    "json_parse_error": {
        "root_cause": "json_parse_error",
        "fixable": True,
        "fix_method": "json_repair",
        "max_retries": 3,
        "escalation": "human_review",
        "description": "LLM 输出不是有效 JSON",
    },
    # 缺少必填字段
    "missing_required_field": {
        "root_cause": "missing_required_field",
        "fixable": True,
        "fix_method": "re_analyze_with_field_reminder",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "LLM 输出缺少必填字段",
    },
    # Schema 违规
    "schema_violation": {
        "root_cause": "schema_violation",
        "fixable": False,
        "fix_method": None,
        "max_retries": 0,
        "escalation": "human_review",
        "description": "数据结构不符合预期，无法自动修复",
    },
    # 提取太短
    "extraction_too_short": {
        "root_cause": "extraction_too_short",
        "fixable": True,
        "fix_method": "retry_with_different_strategy",
        "max_retries": 1,
        "escalation": "human_review",
        "description": "提取文本长度不足，可能是扫描PDF或提取失败",
    },
    # 质量分太低
    "quality_score_too_low": {
        "root_cause": "quality_score_too_low",
        "fixable": True,
        "fix_method": "retry_with_higher_quality_settings",
        "max_retries": 1,
        "escalation": "human_review",
        "description": "PDF提取质量分低于阈值",
    },
    # 扫描PDF检测
    "scanned_pdf_detected": {
        "root_cause": "scanned_pdf_detected",
        "fixable": True,
        "fix_method": "retry_with_ocr",
        "max_retries": 1,
        "escalation": "human_review",
        "description": "检测到扫描PDF，需要OCR提取",
    },
    # 数值不一致
    "numeric_inconsistency": {
        "root_cause": "numeric_inconsistency",
        "fixable": True,
        "fix_method": "re_analyze_with_correction",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "交叉验证发现数值矛盾（如营收<净利润）",
    },
    # 逻辑矛盾
    "logic_inconsistency": {
        "root_cause": "logic_inconsistency",
        "fixable": True,
        "fix_method": "re_analyze_with_logic_hint",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "分析逻辑存在矛盾（如营收下降但利润上升无解释）",
    },
    # 分析师审查未通过
    "analyst_review_failed": {
        "root_cause": "analyst_review_failed",
        "fixable": True,
        "fix_method": "re_analyze_with_reviewer_feedback",
        "max_retries": 2,
        "escalation": "human_review",
        "description": "LLM金融分析师审查未通过，需按修改意见修正",
    },
    # 执行异常
    "execution_error": {
        "root_cause": "execution_error",
        "fixable": False,
        "fix_method": None,
        "max_retries": 0,
        "escalation": "human_review",
        "description": "Gate 执行过程中发生异常",
    },
    # 未知失败
    "unknown_failure": {
        "root_cause": "unknown_failure",
        "fixable": False,
        "fix_method": None,
        "max_retries": 0,
        "escalation": "human_review",
        "description": "无法识别的失败原因",
    },
}


class DiagnosticsEngine:
    """
    失败诊断引擎。

    根据 Gate 失败信息，识别根因并返回诊断方案。
    """

    def __init__(self, custom_rules: Dict[str, Dict] = None):
        """
        Args:
            custom_rules: 自定义诊断规则，覆盖默认规则
        """
        self.rules = DIAGNOSIS_RULES.copy()
        if custom_rules:
            self.rules.update(custom_rules)

    def analyze(self, gate_name: str, result: GateResult) -> Optional[Dict[str, Any]]:
        """
        分析 Gate 失败原因。

        Args:
            gate_name: Gate 名称
            result: Gate 执行结果

        Returns:
            诊断信息字典，None 表示无需诊断（passed/skipped）
        """
        if result.passed or result.status == "skipped":
            return None

        # 优先使用 result 中已有的诊断信息
        if result.diagnosis and result.diagnosis.get("root_cause"):
            root_cause = result.diagnosis["root_cause"]
            if root_cause in self.rules:
                diagnosis = self.rules[root_cause].copy()
                diagnosis.update(result.diagnosis)
                return diagnosis
            else:
                # 未知根因，包装为通用诊断
                return {
                    **self.rules["unknown_failure"],
                    "custom_diagnosis": result.diagnosis,
                    "gate_name": gate_name,
                }

        # 根据 issues 内容推断根因
        root_cause = self._infer_root_cause(gate_name, result)
        diagnosis = self.rules.get(root_cause, self.rules["unknown_failure"]).copy()
        diagnosis["gate_name"] = gate_name
        diagnosis["issues"] = result.issues
        diagnosis["score"] = result.score

        # 生成修复提示
        diagnosis["fix_hint"] = self._generate_fix_hint(diagnosis, result)

        return diagnosis

    def _infer_root_cause(self, gate_name: str, result: GateResult) -> str:
        """
        根据 Gate 名称和 issues 推断根因。
        """
        issues_text = " ".join(result.issues).lower()

        # 关键词匹配
        if "json" in issues_text or "解析" in issues_text:
            return "json_parse_error"

        if "单位" in issues_text or "unit" in issues_text:
            return "unit_mismatch"

        if (
            "幻觉" in issues_text
            or "hallucination" in issues_text
            or "未找到" in issues_text
        ):
            return "fact_hallucination"

        if "缺少" in issues_text and "字段" in issues_text:
            return "missing_required_field"

        if "太短" in issues_text or "长度" in issues_text or "chars" in issues_text:
            return "extraction_too_short"

        if "质量" in issues_text and "低" in issues_text:
            return "quality_score_too_low"

        if "扫描" in issues_text or "scanned" in issues_text or "ocr" in issues_text:
            return "scanned_pdf_detected"

        if "矛盾" in issues_text or "不一致" in issues_text:
            if "营收" in issues_text or "利润" in issues_text:
                return "numeric_inconsistency"
            return "logic_inconsistency"

        if "审查" in issues_text or "review" in issues_text or "修改" in issues_text:
            return "analyst_review_failed"

        if (
            "异常" in issues_text
            or "error" in issues_text
            or "exception" in issues_text
        ):
            return "execution_error"

        # 根据 gate 名称推断
        if "extraction" in gate_name.lower():
            return "extraction_too_short"
        elif "hallucination" in gate_name.lower():
            return "fact_hallucination"
        elif "logic" in gate_name.lower():
            return "logic_inconsistency"
        elif "analyst" in gate_name.lower():
            return "analyst_review_failed"

        return "unknown_failure"

    def _generate_fix_hint(self, diagnosis: Dict, result: GateResult) -> str:
        """
        根据诊断生成修复提示。
        """
        root_cause = diagnosis.get("root_cause", "unknown")
        issues = result.issues

        hints = {
            "unit_mismatch": "注意：原文中的数字单位可能是'元'、'万元'或'亿元'，请仔细核对并统一使用与原文一致的单位。",
            "fact_hallucination": f"注意：以下数字或事实在原文中未找到，请核对：{issues[:2]}。请只使用原文中出现的具体数字。",
            "json_parse_error": "注意：请严格输出标准JSON格式，确保所有字符串使用双引号，无多余逗号。",
            "missing_required_field": f"注意：缺少必填字段，请补充：{issues}。",
            "extraction_too_short": "注意：提取文本过短，可能是扫描PDF。如果确认是扫描件，请使用OCR提取完整文本。",
            "quality_score_too_low": "注意：PDF提取质量较低，尝试调整提取参数或使用备用提取策略。",
            "scanned_pdf_detected": "注意：检测到扫描PDF，已启用OCR提取。请确认OCR结果完整性。",
            "numeric_inconsistency": f"注意：数值存在矛盾：{issues[:2]}。请仔细核对原始数据的一致性。",
            "logic_inconsistency": f"注意：分析逻辑存在矛盾：{issues[:2]}。请解释异常背后的业务原因。",
            "analyst_review_failed": f"审查意见：{issues[:3]}。请按修改意见修正分析内容。",
            "execution_error": "注意：执行过程中发生异常，请检查输入数据和系统状态。",
            "unknown_failure": f"注意：发生未预期的失败：{issues[:2]}。请检查输出内容。",
        }

        return hints.get(root_cause, f"未知错误，请检查：{issues[:2]}")

    def list_rules(self) -> List[str]:
        """列出所有诊断规则"""
        return list(self.rules.keys())

    def get_rule(self, root_cause: str) -> Optional[Dict[str, Any]]:
        """获取指定根因的诊断规则"""
        return self.rules.get(root_cause)
