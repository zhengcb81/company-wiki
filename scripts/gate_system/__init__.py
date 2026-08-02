#!/usr/bin/env python3
"""
gate_system/__init__.py — Pipeline Gate 系统

配置化、可诊断、可重试的质量控制框架。
所有规则从 pipeline_rules.yaml 加载，非硬编码。

使用示例：
    from gate_system import GateRegistry, PipelineContext
    registry = GateRegistry.load()
    context = PipelineContext(doc_type="annual_report", ...)
    result = registry.run_gate("extraction_quality", context)
    if result.failed:
        diagnosis = registry.diagnose(result)
        registry.retry_or_escalate(diagnosis, context)
"""

from .base import Gate, GateResult, PipelineContext
from .registry import GateRegistry
from .diagnostics import DiagnosticsEngine
from .retry import RetryOrchestrator
from .config_loader import load_pipeline_rules

__all__ = [
    "Gate",
    "GateResult",
    "PipelineContext",
    "GateRegistry",
    "DiagnosticsEngine",
    "RetryOrchestrator",
    "load_pipeline_rules",
]

__version__ = "1.0.0"
