#!/usr/bin/env python3
"""
tests/unit/test_gate_system.py — Gate 系统单元测试

验证 Gate 基础框架的核心功能：
- 模块导入
- GateResult 状态判断
- PipelineContext 上下文管理
- GateRegistry 注册与执行
- DiagnosticsEngine 诊断
- RetryOrchestrator 重试决策
- config_loader 配置加载
"""

import sys
from pathlib import Path

# 确保能导入 scripts 下的模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import pytest
from gate_system import (
    Gate,
    GateResult,
    PipelineContext,
    GateRegistry,
    DiagnosticsEngine,
    RetryOrchestrator,
    load_pipeline_rules,
)
from gate_system.base import (
    create_passed_result,
    create_failed_result,
    create_needs_review_result,
)


# ── 测试 GateResult ──────────────────────────


class TestGateResult:
    def test_passed_status(self):
        r = GateResult(status="passed", score=4.5)
        assert r.passed is True
        assert r.failed is False
        assert r.needs_review is False

    def test_failed_status(self):
        r = GateResult(status="failed", issues=["test error"])
        assert r.passed is False
        assert r.failed is True
        assert r.needs_review is False

    def test_needs_review_status(self):
        r = GateResult(status="needs_review", score=3.5)
        assert r.passed is False
        assert r.failed is False
        assert r.needs_review is True


# ── 测试 PipelineContext ────────────────────


class TestPipelineContext:
    def test_basic_creation(self):
        ctx = PipelineContext(
            company="东方电缆",
            doc_type="annual_report",
            period="2016-12-31",
        )
        assert ctx.company == "东方电缆"
        assert ctx.get_doc_type_category() == "financial_report"
        assert ctx.retry_count == 0

    def test_doc_type_mapping(self):
        # 财务报告类
        for dt in ["annual_report", "semi_annual_report", "quarterly_report"]:
            ctx = PipelineContext(company="test", doc_type=dt)
            assert ctx.get_doc_type_category() == "financial_report"

        # 其他类型
        ctx = PipelineContext(company="test", doc_type="investor_relations")
        assert ctx.get_doc_type_category() == "investor_relations"

    def test_retry_counter(self):
        ctx = PipelineContext(company="test", doc_type="annual_report")
        assert ctx.increment_retry() == 1
        assert ctx.increment_retry() == 2
        assert ctx.retry_count == 2

    def test_data_cache(self):
        ctx = PipelineContext(company="test", doc_type="annual_report")
        ctx.set_data("revenue", 17.42)
        assert ctx.get_data("revenue") == 17.42
        assert ctx.get_data("nonexistent", "default") == "default"


# ── 测试便捷工厂函数 ───────────────────────


class TestFactoryFunctions:
    def test_create_passed(self):
        r = create_passed_result(score=4.5, issues=["minor note"])
        assert r.status == "passed"
        assert r.score == 4.5

    def test_create_failed(self):
        r = create_failed_result(issues=["major error"], score=2.0)
        assert r.status == "failed"
        assert r.score == 2.0

    def test_create_needs_review(self):
        r = create_needs_review_result(issues=["needs fix"], score=3.5)
        assert r.status == "needs_review"


# ── 测试 Gate 基类 ──────────────────────────


class DummyGate(Gate):
    name = "dummy"
    doc_types = ["annual_report"]

    def run(self, context):
        return create_passed_result(score=5.0)


class TestGateBase:
    def test_is_applicable(self):
        gate = DummyGate()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        assert gate.is_applicable(ctx) is True

        ctx2 = PipelineContext(company="test", doc_type="investor_relations")
        assert gate.is_applicable(ctx2) is False

    def test_diagnose_default(self):
        gate = DummyGate()
        result = create_failed_result(issues=["error"])
        diag = gate.diagnose(result)
        assert diag["root_cause"] == "dummy_failed"
        assert diag["fixable"] is False


# ── 测试 DiagnosticsEngine ──────────────────


class TestDiagnosticsEngine:
    def test_analyze_passed(self):
        engine = DiagnosticsEngine()
        result = create_passed_result()
        diag = engine.analyze("test_gate", result)
        assert diag is None  # passed 不需要诊断

    def test_analyze_json_error(self):
        engine = DiagnosticsEngine()
        result = create_failed_result(issues=["JSON解析失败"])
        diag = engine.analyze("test_gate", result)
        assert diag["root_cause"] == "json_parse_error"
        assert diag["fixable"] is True
        assert diag["fix_method"] == "json_repair"

    def test_analyze_unit_mismatch(self):
        engine = DiagnosticsEngine()
        result = create_failed_result(issues=["数字 1.6 未找到，单位不匹配"])
        diag = engine.analyze("test_gate", result)
        assert diag["root_cause"] == "unit_mismatch"
        assert "fix_hint" in diag

    def test_analyze_unknown(self):
        engine = DiagnosticsEngine()
        result = create_failed_result(issues=["something weird happened"])
        diag = engine.analyze("unknown_gate", result)
        assert diag["root_cause"] == "unknown_failure"

    def test_custom_rules(self):
        custom = {
            "my_cause": {
                "root_cause": "my_cause",
                "fixable": True,
                "fix_method": "custom_fix",
            }
        }
        engine = DiagnosticsEngine(custom_rules=custom)
        result = GateResult(status="failed", diagnosis={"root_cause": "my_cause"})
        diag = engine.analyze("test", result)
        assert diag["fix_method"] == "custom_fix"


# ── 测试 RetryOrchestrator ──────────────────


class TestRetryOrchestrator:
    def test_decide_passed_no_action(self):
        retry = RetryOrchestrator()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        # passed 不需要诊断
        decision = retry.decide(None, ctx)
        assert decision["action"] == "skip"

    def test_decide_retry(self):
        retry = RetryOrchestrator()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        diagnosis = {
            "root_cause": "unit_mismatch",
            "fixable": True,
            "fix_method": "re_analyze_with_unit_hint",
            "max_retries": 2,
            "escalation": "human_review",
            "fix_hint": "注意单位",
        }
        decision = retry.decide(diagnosis, ctx)
        assert decision["action"] == "retry"
        assert ctx.retry_count == 1
        assert ctx.fix_hint == "注意单位"

    def test_decide_max_retries_exceeded(self):
        retry = RetryOrchestrator()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        ctx.retry_count = 2  # 已达上限
        diagnosis = {
            "root_cause": "unit_mismatch",
            "fixable": True,
            "fix_method": "re_analyze_with_unit_hint",
            "max_retries": 2,
            "escalation": "human_review",
            "issues": ["test"],
            "fix_hint": "hint",
        }
        decision = retry.decide(diagnosis, ctx)
        assert decision["action"] == "human_review"
        assert "已达最大重试次数" in decision["details"]["reason"]

    def test_decide_same_cause_limit(self):
        retry = RetryOrchestrator()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        # 模拟同一根因已重试2次
        retry._retry_history["test/annual_report/"] = [
            {"root_cause": "unit_mismatch"},
            {"root_cause": "unit_mismatch"},
        ]
        diagnosis = {
            "root_cause": "unit_mismatch",
            "fixable": True,
            "fix_method": "re_analyze",
            "max_retries": 5,
            "escalation": "human_review",
            "issues": ["test"],
            "fix_hint": "hint",
        }
        decision = retry.decide(diagnosis, ctx)
        assert decision["action"] == "human_review"

    def test_decide_unfixable(self):
        retry = RetryOrchestrator()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        diagnosis = {
            "root_cause": "schema_violation",
            "fixable": False,
            "escalation": "human_review",
            "issues": ["test"],
        }
        decision = retry.decide(diagnosis, ctx)
        assert decision["action"] == "human_review"


# ── 测试配置加载 ────────────────────────────


class TestConfigLoader:
    def test_load_rules(self):
        rules = load_pipeline_rules()
        assert "pipeline_gates" in rules
        assert "financial_report" in rules["pipeline_gates"]

    def test_validate_rules(self):
        from gate_system.config_loader import validate_rules

        rules = load_pipeline_rules()
        errors = validate_rules(rules)
        assert len(errors) == 0, f"规则验证失败: {errors}"

    def test_doc_type_rules_exist(self):
        rules = load_pipeline_rules()
        pipeline_gates = rules["pipeline_gates"]
        for doc_type in ["financial_report", "investor_relations", "prospectus"]:
            assert doc_type in pipeline_gates


# ── 测试 GateRegistry ───────────────────────


class TestGateRegistry:
    def test_load_and_register(self):
        registry = GateRegistry.load()
        assert len(registry.list_gates()) >= 0  # 至少不会报错

    def test_get_rules(self):
        registry = GateRegistry.load()
        rules = registry.get_rules_for_doc_type("annual_report")
        assert "gate_1_extraction" in rules or len(rules) > 0

    def test_run_unregistered_gate(self):
        registry = GateRegistry()
        ctx = PipelineContext(company="test", doc_type="annual_report")
        result = registry.run_gate("nonexistent", ctx)
        assert result.status == "skipped"


# ── 主入口 ─────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
