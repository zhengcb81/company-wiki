#!/usr/bin/env python3
"""
gate_system/retry.py — 重试调度器

根据 DiagnosticsEngine 的诊断结果，决定：重试、升级人工、或跳过。
实现"搞清原因再重试，不修复就重试是浪费"的原则。
"""

from typing import Any, Dict
from pathlib import Path

from .base import PipelineContext


class RetryOrchestrator:
    """
    重试调度器。

    核心逻辑：
    1. 只有 fixable=True 的才重试
    2. 超过 max_retries 后转人工
    3. 每次重试附带 fix_hint 提示LLM
    4. 记录重试历史，防无限循环
    """

    def __init__(self, review_queue_path: Path = None):
        """
        Args:
            review_queue_path: 人工审核队列文件路径
        """
        self.review_queue_path = (
            review_queue_path or Path.home() / "company-wiki" / "review_queue.md"
        )
        self._retry_history: Dict[str, list] = {}  # doc_key -> [retry_records]

    def decide(
        self, diagnosis: Dict[str, Any], context: PipelineContext
    ) -> Dict[str, Any]:
        """
        决策：重试、升级或跳过。

        Args:
            diagnosis: DiagnosticsEngine 的诊断结果
            context: Pipeline 上下文

        Returns:
            {"action": "retry" | "human_review" | "skip", "details": {...}}
        """
        if not diagnosis:
            return {"action": "skip", "details": {"reason": "无诊断信息"}}

        # 检查是否可修复
        fixable = diagnosis.get("fixable", False)
        if not fixable:
            return self._escalate(diagnosis, context, "不可自动修复")

        # 检查重试次数
        max_retries = diagnosis.get("max_retries", 0)
        if context.retry_count >= max_retries:
            return self._escalate(
                diagnosis, context, f"已达最大重试次数({max_retries})"
            )

        # 检查历史（同一文档同一根因的重试次数）
        doc_key = f"{context.company}/{context.doc_type}/{context.period}"
        root_cause = diagnosis.get("root_cause", "unknown")
        history = self._retry_history.get(doc_key, [])
        same_cause_retries = sum(1 for h in history if h["root_cause"] == root_cause)

        if same_cause_retries >= 2:
            # 同一根因重试2次仍失败，不再重试
            return self._escalate(
                diagnosis,
                context,
                f"同一根因({root_cause})已重试{same_cause_retries}次",
            )

        # 执行重试
        context.increment_retry()
        context.fix_hint = diagnosis.get("fix_hint", "")

        # 记录历史
        history.append(
            {
                "root_cause": root_cause,
                "retry_count": context.retry_count,
                "fix_method": diagnosis.get("fix_method"),
                "timestamp": context.created_at,
            }
        )
        self._retry_history[doc_key] = history

        return {
            "action": "retry",
            "details": {
                "retry_count": context.retry_count,
                "max_retries": max_retries,
                "fix_method": diagnosis.get("fix_method"),
                "fix_hint": context.fix_hint,
                "root_cause": root_cause,
            },
        }

    def _escalate(
        self, diagnosis: Dict, context: PipelineContext, reason: str
    ) -> Dict[str, Any]:
        """
        升级到人工审核。
        """
        root_cause = diagnosis.get("root_cause", "unknown")
        issues = diagnosis.get("issues", [])

        # 写入审核队列
        self._append_to_review_queue(diagnosis, context, reason)

        return {
            "action": "human_review",
            "details": {
                "reason": reason,
                "root_cause": root_cause,
                "issues": issues[:5],
                "retry_count": context.retry_count,
                "queue_path": str(self.review_queue_path),
            },
        }

    def _append_to_review_queue(
        self, diagnosis: Dict, context: PipelineContext, reason: str
    ):
        """
        追加到人工审核队列。
        """
        try:
            # 确保文件存在
            if not self.review_queue_path.exists():
                self.review_queue_path.write_text(
                    "# 审核队列\n\n> 自动由 Pipeline Gate 系统生成\n\n---\n\n",
                    encoding="utf-8",
                )

            # 构建队列条目
            entry = f"""
### [{diagnosis.get("root_cause", "unknown")}] {context.company} {context.period} {context.doc_type}
- **来源**: Pipeline Gate 自动升级
- **原因**: {reason}
- **根因**: {diagnosis.get("root_cause", "unknown")}
- **重试次数**: {context.retry_count}
- **问题**:
"""
            for issue in diagnosis.get("issues", [])[:5]:
                entry += f"  - {issue}\n"

            entry += f"- **修复提示**: {diagnosis.get('fix_hint', '无')}\n"
            entry += f"- **时间**: {context.created_at}\n\n"

            with open(self.review_queue_path, "a", encoding="utf-8") as f:
                f.write(entry)

        except Exception as e:
            print(f"WARN: 写入审核队列失败: {e}")

    def get_retry_history(self, context: PipelineContext) -> list:
        """获取文档的重试历史"""
        doc_key = f"{context.company}/{context.doc_type}/{context.period}"
        return self._retry_history.get(doc_key, [])

    def reset_retry_count(self, context: PipelineContext):
        """重置重试计数（成功修复后调用）"""
        context.retry_count = 0
        context.fix_hint = ""


# ── 重试动作执行器 ──────────────────────────────


class FixActionExecutor:
    """
    执行具体的修复动作。
    根据 fix_method 调用对应的修复策略。
    """

    FIX_METHODS = {
        "re_analyze_with_unit_hint": "重新分析，附加单位提示",
        "re_analyze_with_fact_correction": "重新分析，附事实证明修正",
        "json_repair": "JSON修复器（正则+容错解析）",
        "re_analyze_with_field_reminder": "重新分析，提醒必填字段",
        "retry_with_different_strategy": "使用备用提取策略重试",
        "retry_with_ocr": "使用OCR重新提取",
        "retry_with_higher_quality_settings": "使用更高质量参数重试",
        "re_analyze_with_correction": "重新分析，修正数值错误",
        "re_analyze_with_logic_hint": "重新分析，提醒逻辑一致性",
        "re_analyze_with_reviewer_feedback": "重新分析，按审查意见修改",
    }

    @classmethod
    def execute(cls, fix_method: str, context: PipelineContext, hint: str = "") -> bool:
        """
        执行修复动作。

        Args:
            fix_method: 修复方法名称
            context: Pipeline 上下文
            hint: 修复提示

        Returns:
            bool: 是否成功准备修复（实际修复由Pipeline重新执行Stage）
        """
        if fix_method not in cls.FIX_METHODS:
            print(f"WARN: 未知修复方法 '{fix_method}'，跳过")
            return False

        # 将修复提示写入上下文，供Stage重新执行时使用
        context.fix_hint = hint or cls.FIX_METHODS.get(fix_method, "")

        # 记录修复动作
        print(f"  准备修复: {cls.FIX_METHODS[fix_method]}")
        if hint:
            print(f"  修复提示: {hint[:100]}...")

        return True

    @classmethod
    def list_methods(cls) -> Dict[str, str]:
        """列出所有支持的修复方法"""
        return cls.FIX_METHODS.copy()
