#!/usr/bin/env python3
"""
gate_system/base.py — Gate 核心基类

定义 Gate、GateResult、PipelineContext 三个核心抽象。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class GateResult:
    """
    Gate 执行结果。

    Attributes:
        status: passed | failed | needs_review | skipped
        score: 0-5 质量评分（可选）
        issues: 发现的问题列表
        diagnosis: 失败诊断信息（供 DiagnosticsEngine 使用）
        metadata: 额外元数据
    """

    status: str  # "passed", "failed", "needs_review", "skipped"
    score: Optional[float] = None
    issues: List[str] = field(default_factory=list)
    diagnosis: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    @property
    def needs_review(self) -> bool:
        return self.status == "needs_review"

    def __str__(self) -> str:
        parts = [f"GateResult(status={self.status})"]
        if self.score is not None:
            parts.append(f"score={self.score:.2f}")
        if self.issues:
            parts.append(f"issues={len(self.issues)}")
        return " | ".join(parts)


@dataclass
class PipelineContext:
    """
    Pipeline 执行上下文，携带所有阶段共享的状态。

    Attributes:
        company: 公司名称
        doc_type: 文档类型（annual_report, investor_relations, prospectus 等）
        period: 报告期（YYYY-MM-DD）
        source_path: 原始文件路径
        extract_path: Stage 1 输出路径
        structured_path: Stage 2 输出路径
        analysis_path: Stage 3 输出路径
        review_path: Stage 4 输出路径
        retry_count: 当前重试计数
        fix_hint: 修复提示（DiagnosticsEngine 生成）
        data: 各阶段产生的数据缓存
    """

    company: str
    doc_type: str
    period: str = ""
    source_path: Optional[Path] = None
    extract_path: Optional[Path] = None
    structured_path: Optional[Path] = None
    analysis_path: Optional[Path] = None
    review_path: Optional[Path] = None
    retry_count: int = 0
    max_retries: int = 2
    fix_hint: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_doc_type_category(self) -> str:
        """
        将具体 doc_type 映射到规则配置中的大类。
        """
        financial_types = ["annual_report", "semi_annual_report", "quarterly_report"]
        if self.doc_type in financial_types:
            return "financial_report"
        return self.doc_type  # investor_relations, prospectus, etc.

    def increment_retry(self) -> int:
        """增加重试计数并返回当前值"""
        self.retry_count += 1
        return self.retry_count

    def set_data(self, key: str, value: Any):
        """在上下文中缓存数据"""
        self.data[key] = value

    def get_data(self, key: str, default=None) -> Any:
        """从上下文中获取数据"""
        return self.data.get(key, default)


class Gate(ABC):
    """
    Gate 抽象基类。

    所有质量控制关卡必须继承此类并实现 run 方法。
    """

    name: str = ""
    doc_types: List[str] = field(default_factory=list)
    description: str = ""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 从 pipeline_rules.yaml 加载的该 Gate 配置
        """
        self.config = config or {}

    @abstractmethod
    def run(self, context: PipelineContext) -> GateResult:
        """
        执行 Gate 检查。

        Args:
            context: 当前 Pipeline 上下文

        Returns:
            GateResult
        """
        pass

    def is_applicable(self, context: PipelineContext) -> bool:
        """
        判断此 Gate 是否适用于当前文档类型。
        """
        if not self.doc_types:
            return True
        return context.doc_type in self.doc_types

    def diagnose(self, result: GateResult) -> Optional[Dict[str, Any]]:
        """
        诊断失败原因。子类可覆盖以提供更具体的诊断。
        默认返回 result.diagnosis 或通用诊断。
        """
        if result.diagnosis:
            return result.diagnosis
        return {
            "root_cause": f"{self.name}_failed",
            "fixable": False,
            "fix_method": None,
            "max_retries": 0,
            "escalation": "human_review",
            "gate_name": self.name,
        }

    def __str__(self) -> str:
        return f"Gate(name={self.name}, doc_types={self.doc_types})"


# ── 便捷工厂 ──────────────────────────────


def create_gate_result(
    status: str,
    score: Optional[float] = None,
    issues: List[str] = None,
    diagnosis: Dict[str, Any] = None,
) -> GateResult:
    """便捷创建 GateResult"""
    return GateResult(
        status=status,
        score=score,
        issues=issues or [],
        diagnosis=diagnosis,
    )


def create_passed_result(score: float = None, issues: List[str] = None) -> GateResult:
    """便捷创建 passed 结果"""
    return create_gate_result("passed", score=score, issues=issues)


def create_failed_result(
    issues: List[str],
    diagnosis: Dict[str, Any] = None,
    score: float = None,
) -> GateResult:
    """便捷创建 failed 结果"""
    return create_gate_result("failed", score=score, issues=issues, diagnosis=diagnosis)


def create_needs_review_result(
    issues: List[str],
    diagnosis: Dict[str, Any] = None,
    score: float = None,
) -> GateResult:
    """便捷创建 needs_review 结果"""
    return create_gate_result(
        "needs_review", score=score, issues=issues, diagnosis=diagnosis
    )
