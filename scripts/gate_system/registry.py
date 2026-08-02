#!/usr/bin/env python3
"""
gate_system/registry.py — Gate 注册器

管理所有 Gate 的注册、发现和执行。
从 pipeline_rules.yaml 加载配置，按文档类型路由。
"""

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import Gate, GateResult, PipelineContext
from .config_loader import load_pipeline_rules
from .diagnostics import DiagnosticsEngine
from .retry import RetryOrchestrator


class GateRegistry:
    """
    Gate 注册器。

    负责：
    1. 从配置加载所有 Gate 规则
    2. 注册 Gate 实例
    3. 按文档类型路由执行
    4. 协调诊断和重试
    """

    def __init__(self, rules: Dict[str, Any] = None):
        """
        Args:
            rules: 已加载的 pipeline_rules 字典，None 时自动加载
        """
        self.rules = rules or {}
        self.gates: Dict[str, Gate] = {}
        self.diagnostics = DiagnosticsEngine()
        self.retry = RetryOrchestrator()
        self._execution_log: List[Dict[str, Any]] = []

    @classmethod
    def load(cls, rules_path: Optional[Path] = None) -> "GateRegistry":
        """
        从 YAML 配置加载注册器。

        Args:
            rules_path: 规则文件路径，None 时使用默认路径

        Returns:
            GateRegistry 实例
        """
        rules = load_pipeline_rules(rules_path)
        registry = cls(rules)
        registry._register_builtin_gates()
        return registry

    def _register_builtin_gates(self):
        """注册系统内置 Gate"""
        # 从 gates 子目录动态导入
        gates_dir = Path(__file__).parent / "gates"
        if not gates_dir.exists():
            return

        for file in gates_dir.glob("*_gate.py"):
            module_name = f"gate_system.gates.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Gate)
                        and attr is not Gate
                        and hasattr(attr, "name")
                        and attr.name
                    ):
                        self.register(attr)
            except ImportError as e:
                print(f"WARN: 无法导入 Gate 模块 {module_name}: {e}")

    def register(self, gate_class: Type[Gate], config: Dict[str, Any] = None):
        """
        注册一个 Gate 类。

        Args:
            gate_class: Gate 子类（非实例）
            config: 该 Gate 的配置（覆盖默认）
        """
        # 从 rules 中查找对应配置
        if config is None and self.rules:
            # 尝试按 doc_type 查找配置
            pass  # config 将在实例化时动态加载

        # 先创建实例（config 可能延迟加载）
        gate = gate_class(config=config)
        self.gates[gate.name] = gate

    def get_gate(self, name: str) -> Optional[Gate]:
        """获取已注册的 Gate"""
        return self.gates.get(name)

    def list_gates(self) -> List[str]:
        """列出所有已注册的 Gate 名称"""
        return list(self.gates.keys())

    def get_rules_for_doc_type(self, doc_type: str) -> Dict[str, Any]:
        """
        获取指定文档类型的规则配置。
        将具体 doc_type 映射到规则大类。
        """
        financial_types = ["annual_report", "semi_annual_report", "quarterly_report"]
        category = "financial_report" if doc_type in financial_types else doc_type
        return self.rules.get("pipeline_gates", {}).get(category, {})

    def run_gate(self, gate_name: str, context: PipelineContext) -> GateResult:
        """
        执行单个 Gate。

        Args:
            gate_name: Gate 名称
            context: Pipeline 上下文

        Returns:
            GateResult
        """
        gate = self.get_gate(gate_name)
        if not gate:
            return GateResult(
                status="skipped",
                issues=[f"Gate '{gate_name}' 未注册"],
            )

        # 检查是否适用
        if not gate.is_applicable(context):
            return GateResult(
                status="skipped",
                issues=[f"Gate '{gate_name}' 不适用于 {context.doc_type}"],
            )

        # 动态加载该文档类型的配置
        doc_rules = self.get_rules_for_doc_type(context.doc_type)
        gate_config = doc_rules.get(gate_name, {})
        if gate_config:
            gate.config = gate_config

        # 执行
        try:
            result = gate.run(context)
        except Exception as e:
            result = GateResult(
                status="failed",
                issues=[f"Gate '{gate_name}' 执行异常: {e}"],
                diagnosis={
                    "root_cause": "execution_error",
                    "fixable": False,
                    "escalation": "human_review",
                    "error": str(e),
                },
            )

        # 记录执行日志
        self._execution_log.append(
            {
                "gate_name": gate_name,
                "doc_type": context.doc_type,
                "company": context.company,
                "status": result.status,
                "score": result.score,
                "issues": result.issues,
                "timestamp": context.created_at,
            }
        )

        return result

    def run_all_gates(
        self, context: PipelineContext, stage: str = None
    ) -> Dict[str, GateResult]:
        """
        执行所有适用的 Gate。

        Args:
            context: Pipeline 上下文
            stage: 可选，只执行指定 stage 的 gates

        Returns:
            {gate_name: GateResult} 字典
        """
        results = {}
        for name, gate in self.gates.items():
            if stage and not name.startswith(stage):
                continue
            if gate.is_applicable(context):
                results[name] = self.run_gate(name, context)
        return results

    def diagnose(
        self, result: GateResult, gate_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        诊断 Gate 失败原因。
        """
        return self.diagnostics.analyze(gate_name, result)

    def retry_or_escalate(
        self, diagnosis: Dict[str, Any], context: PipelineContext
    ) -> Dict[str, Any]:
        """
        根据诊断结果决定：重试、升级或跳过。

        Returns:
            {"action": "retry" | "human_review" | "skip", "details": {...}}
        """
        return self.retry.decide(diagnosis, context)

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """获取执行日志"""
        return self._execution_log.copy()

    def __str__(self) -> str:
        return f"GateRegistry(gates={len(self.gates)}, rules_doc_types={list(self.rules.get('pipeline_gates', {}).keys())})"
