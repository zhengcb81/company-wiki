"""
tests/unit/test_deployment.py — 部署管理测试
"""



from company_wiki.deployment import (
    DeploymentConfig,
    DeploymentManager,
    DeploymentMetrics,
    DeploymentStage,
    FailureDrillType,
    create_deployment_manager,
)
from company_wiki.scheduler import SchedulerDB


# ── DeploymentMetrics 测试 ──────────────────────────────

class TestDeploymentMetrics:
    def test_metrics_healthy(self):
        """测试健康指标"""
        metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )
        assert metrics.is_healthy is True

    def test_metrics_unhealthy_raw_deleted(self):
        """测试不健康指标（有删除）"""
        metrics = DeploymentMetrics(raw_deleted=1)
        assert metrics.is_healthy is False

    def test_metrics_unhealthy_provenance(self):
        """测试不健康指标（来源覆盖不足）"""
        metrics = DeploymentMetrics(provenance_coverage=0.9)
        assert metrics.is_healthy is False

    def test_metrics_unhealthy_link_errors(self):
        """测试不健康指标（有链接错误）"""
        metrics = DeploymentMetrics(link_errors=1)
        assert metrics.is_healthy is False


# ── DeploymentManager 测试 ──────────────────────────────

class TestDeploymentManager:
    def _make_manager(self, tmp_path) -> DeploymentManager:
        db = SchedulerDB(tmp_path / "scheduler.db")
        config = DeploymentConfig(stage=DeploymentStage.SHADOW)
        return DeploymentManager(db, config)

    def test_initial_stage(self, tmp_path):
        """测试初始阶段"""
        manager = self._make_manager(tmp_path)
        assert manager.current_stage == DeploymentStage.SHADOW
        assert manager.is_write_enabled is False

    def test_advance_stage(self, tmp_path):
        """测试推进阶段"""
        manager = self._make_manager(tmp_path)

        metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )

        # 从 SHADOW 推进到 CANARY
        assert manager.advance_stage(metrics) is True
        assert manager.current_stage == DeploymentStage.CANARY

    def test_advance_stage_unhealthy(self, tmp_path):
        """测试不健康指标时推进阶段"""
        manager = self._make_manager(tmp_path)

        metrics = DeploymentMetrics(raw_deleted=1)  # 不健康

        # 不应该推进
        assert manager.advance_stage(metrics) is False
        assert manager.current_stage == DeploymentStage.SHADOW

    def test_advance_stage_kill_switch(self, tmp_path):
        """测试 kill switch 时推进阶段"""
        manager = self._make_manager(tmp_path)
        manager.activate_kill_switch("测试")

        metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )

        # 不应该推进
        assert manager.advance_stage(metrics) is False

    def test_rollback(self, tmp_path):
        """测试回滚"""
        manager = self._make_manager(tmp_path)

        # 先推进到 CANARY
        metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )
        manager.advance_stage(metrics)
        assert manager.current_stage == DeploymentStage.CANARY

        # 回滚到 SHADOW
        manager.rollback("测试回滚")
        assert manager.current_stage == DeploymentStage.SHADOW

    def test_rollback_at_initial(self, tmp_path):
        """测试在初始阶段回滚"""
        manager = self._make_manager(tmp_path)

        # 在 SHADOW 阶段回滚应该保持不变
        manager.rollback("测试回滚")
        assert manager.current_stage == DeploymentStage.SHADOW

    def test_kill_switch(self, tmp_path):
        """测试紧急停止"""
        manager = self._make_manager(tmp_path)

        # 激活
        manager.activate_kill_switch("测试")
        assert manager._config.kill_switch is True
        assert manager.is_write_enabled is False

        # 停用
        manager.deactivate_kill_switch()
        assert manager._config.kill_switch is False

    def test_record_metrics_auto_rollback(self, tmp_path):
        """测试记录指标自动回滚"""
        manager = self._make_manager(tmp_path)

        # 先推进到 CANARY
        healthy_metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )
        manager.advance_stage(healthy_metrics)
        assert manager.current_stage == DeploymentStage.CANARY

        # 记录不健康指标
        unhealthy_metrics = DeploymentMetrics(raw_deleted=1)
        manager.record_metrics(unhealthy_metrics)

        # 应该自动回滚
        assert manager.current_stage == DeploymentStage.SHADOW

    def test_failure_drill_repeat_run(self, tmp_path):
        """演练：重复运行"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.REPEAT_RUN)
        assert drill.success is True
        assert drill.completed_at is not None

    def test_failure_drill_interrupt_recovery(self, tmp_path):
        """演练：中断恢复"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.INTERRUPT_RECOVERY)
        assert drill.success is True

    def test_failure_drill_partial_failure(self, tmp_path):
        """演练：部分失败"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.PARTIAL_FAILURE)
        assert drill.success is True

    def test_failure_drill_budget_exhaustion(self, tmp_path):
        """演练：预算耗尽"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.BUDGET_EXHAUSTION)
        assert drill.success is True

    def test_failure_drill_review_rejection(self, tmp_path):
        """演练：审核拒绝"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.REVIEW_REJECTION)
        assert drill.success is True

    def test_failure_drill_rollback(self, tmp_path):
        """演练：回滚"""
        manager = self._make_manager(tmp_path)

        # 先推进到 CANARY
        metrics = DeploymentMetrics(
            raw_deleted=0,
            duplicate_deliveries=0,
            provenance_coverage=1.0,
            link_errors=0,
            schema_errors=0,
        )
        manager.advance_stage(metrics)

        drill = manager.run_failure_drill(FailureDrillType.ROLLBACK)
        assert drill.success is True

    def test_failure_drill_kill_switch(self, tmp_path):
        """演练：紧急停止"""
        manager = self._make_manager(tmp_path)

        drill = manager.run_failure_drill(FailureDrillType.KILL_SWITCH)
        assert drill.success is True

    def test_generate_retirement_report(self, tmp_path):
        """测试生成退役报告"""
        manager = self._make_manager(tmp_path)

        report = manager.generate_retirement_report()

        assert "generated_at" in report
        assert "current_stage" in report
        assert report["current_stage"] == "shadow"
        assert len(report["legacy_entries"]) == 4

        # 检查 legacy entries
        entry_names = [e["name"] for e in report["legacy_entries"]]
        assert "full_pipeline.py" in entry_names
        assert "batch_process.py" in entry_names
        assert "batch_ingest.py" in entry_names
        assert "cleanup_junk.py" in entry_names


# ── create_deployment_manager 测试 ──────────────────────────────

class TestCreateDeploymentManager:
    def test_create_manager(self, tmp_path):
        """测试创建部署管理器"""
        db_path = tmp_path / "scheduler.db"
        manager = create_deployment_manager(db_path)

        assert manager is not None
        assert manager.current_stage == DeploymentStage.SHADOW

    def test_create_manager_with_allowlist(self, tmp_path):
        """测试创建部署管理器（带 allowlist）"""
        db_path = tmp_path / "scheduler.db"
        manager = create_deployment_manager(db_path, allowlist=["北方华创", "中微公司"])

        assert "北方华创" in manager._config.allowlist
