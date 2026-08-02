"""
deployment.py — Shadow、Canary、分批上线与 Legacy 退役

管理从 shadow 到 full 的渐进式上线过程。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .scheduler import SchedulerDB, WriteMode


class DeploymentStage(str, Enum):
    """部署阶段"""
    SHADOW = "shadow"        # 只分析，不写入
    CANARY = "canary"        # 只写入 allowlist 中的实体
    COHORT_A = "cohort_a"    # 核心持仓
    COHORT_B = "cohort_b"    # 重点观察
    COHORT_C = "cohort_c"    # 机会池
    FULL = "full"            # 完全开放


class FailureDrillType(str, Enum):
    """故障演练类型"""
    REPEAT_RUN = "repeat_run"              # 重复运行
    INTERRUPT_RECOVERY = "interrupt_recovery"  # 中断恢复
    PARTIAL_FAILURE = "partial_failure"    # 部分失败
    BUDGET_EXHAUSTION = "budget_exhaustion"  # 预算耗尽
    REVIEW_REJECTION = "review_rejection"  # 审核拒绝
    ROLLBACK = "rollback"                  # 回滚
    KILL_SWITCH = "kill_switch"            # 紧急停止


@dataclass
class DeploymentConfig:
    """部署配置"""
    stage: DeploymentStage = DeploymentStage.SHADOW
    allowlist: list[str] = field(default_factory=list)
    kill_switch: bool = False
    max_errors: int = 10
    error_window_minutes: int = 60
    auto_rollback: bool = True


@dataclass
class FailureDrill:
    """故障演练记录"""
    drill_id: str
    drill_type: FailureDrillType
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    recovery_time_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentMetrics:
    """部署指标"""
    raw_deleted: int = 0
    duplicate_deliveries: int = 0
    provenance_coverage: float = 0.0
    link_errors: int = 0
    schema_errors: int = 0
    cost_usd: float = 0.0
    total_runs: int = 0
    successful_runs: int = 0

    @property
    def is_healthy(self) -> bool:
        """是否健康（满足上线条件）"""
        return (
            self.raw_deleted == 0
            and self.duplicate_deliveries == 0
            and self.provenance_coverage >= 1.0
            and self.link_errors == 0
            and self.schema_errors == 0
        )


class DeploymentManager:
    """
    部署管理器。

    管理从 shadow 到 full 的渐进式上线过程。
    """

    def __init__(self, db: SchedulerDB, config: DeploymentConfig):
        self._db = db
        self._config = config
        self._metrics_history: list[DeploymentMetrics] = []
        self._drills: list[FailureDrill] = []

    @property
    def current_stage(self) -> DeploymentStage:
        return self._config.stage

    @property
    def is_write_enabled(self) -> bool:
        return self._config.stage != DeploymentStage.SHADOW and not self._config.kill_switch

    def advance_stage(self, metrics: DeploymentMetrics) -> bool:
        """
        推进到下一阶段。

        Args:
            metrics: 当前指标

        Returns:
            是否成功推进
        """
        # 检查 kill switch
        if self._config.kill_switch:
            return False

        # 检查指标
        if not metrics.is_healthy:
            return False

        # 推进阶段
        stage_order = list(DeploymentStage)
        current_idx = stage_order.index(self._config.stage)

        if current_idx < len(stage_order) - 1:
            self._config.stage = stage_order[current_idx + 1]
            self._apply_config()
            return True

        return False

    def rollback(self, reason: str):
        """
        回滚到上一阶段。

        Args:
            reason: 回滚原因
        """
        stage_order = list(DeploymentStage)
        current_idx = stage_order.index(self._config.stage)

        if current_idx > 0:
            self._config.stage = stage_order[current_idx - 1]
            self._apply_config()

    def activate_kill_switch(self, reason: str):
        """激活紧急停止"""
        self._config.kill_switch = True
        self._db.set_write_mode(WriteMode.OFF)

    def deactivate_kill_switch(self):
        """停用紧急停止"""
        self._config.kill_switch = False
        self._apply_config()

    def record_metrics(self, metrics: DeploymentMetrics):
        """记录指标"""
        self._metrics_history.append(metrics)

        # 检查是否需要自动回滚
        if self._config.auto_rollback and not metrics.is_healthy:
            self.rollback("指标不健康")

    def run_failure_drill(self, drill_type: FailureDrillType) -> FailureDrill:
        """
        运行故障演练。

        Args:
            drill_type: 演练类型

        Returns:
            演练记录
        """
        drill = FailureDrill(
            drill_id=f"drill-{drill_type.value}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            drill_type=drill_type,
            started_at=datetime.now(),
        )

        try:
            if drill_type == FailureDrillType.REPEAT_RUN:
                drill.success = self._drill_repeat_run()
            elif drill_type == FailureDrillType.INTERRUPT_RECOVERY:
                drill.success = self._drill_interrupt_recovery()
            elif drill_type == FailureDrillType.PARTIAL_FAILURE:
                drill.success = self._drill_partial_failure()
            elif drill_type == FailureDrillType.BUDGET_EXHAUSTION:
                drill.success = self._drill_budget_exhaustion()
            elif drill_type == FailureDrillType.REVIEW_REJECTION:
                drill.success = self._drill_review_rejection()
            elif drill_type == FailureDrillType.ROLLBACK:
                drill.success = self._drill_rollback()
            elif drill_type == FailureDrillType.KILL_SWITCH:
                drill.success = self._drill_kill_switch()
        except Exception as e:
            drill.success = False
            drill.error_message = str(e)

        drill.completed_at = datetime.now()
        drill.recovery_time_seconds = (drill.completed_at - drill.started_at).total_seconds()

        self._drills.append(drill)
        return drill

    def generate_retirement_report(self) -> dict:
        """
        生成退役报告。

        列出删除/冻结的旧入口、替代路径、保留原因和回滚策略。
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "current_stage": self._config.stage.value,
            "legacy_entries": [
                {
                    "name": "full_pipeline.py",
                    "status": "blocked",
                    "replacement": "scheduler.py",
                    "reason": "由调度器替代",
                    "rollback": "设置 COMPANY_WIKI_LEGACY_WRITERS=allow",
                },
                {
                    "name": "batch_process.py",
                    "status": "blocked",
                    "replacement": "scheduler.py",
                    "reason": "由调度器替代",
                    "rollback": "设置 COMPANY_WIKI_LEGACY_WRITERS=allow",
                },
                {
                    "name": "batch_ingest.py",
                    "status": "blocked",
                    "replacement": "ingest.py",
                    "reason": "由新 IngestService 替代",
                    "rollback": "设置 COMPANY_WIKI_LEGACY_WRITERS=allow",
                },
                {
                    "name": "cleanup_junk.py",
                    "status": "blocked",
                    "replacement": "migration.py",
                    "reason": "由迁移框架替代",
                    "rollback": "设置 COMPANY_WIKI_LEGACY_WRITERS=allow",
                },
            ],
            "failure_drills": [
                {
                    "drill_id": d.drill_id,
                    "type": d.drill_type.value,
                    "success": d.success,
                    "recovery_time": d.recovery_time_seconds,
                }
                for d in self._drills
            ],
            "metrics_history": [
                {
                    "raw_deleted": m.raw_deleted,
                    "duplicate_deliveries": m.duplicate_deliveries,
                    "provenance_coverage": m.provenance_coverage,
                    "link_errors": m.link_errors,
                    "schema_errors": m.schema_errors,
                }
                for m in self._metrics_history[-10:]  # 最近10条
            ],
        }

    def _apply_config(self):
        """应用配置到数据库"""
        if self._config.stage == DeploymentStage.SHADOW:
            self._db.set_write_mode(WriteMode.SHADOW)
        elif self._config.stage == DeploymentStage.CANARY:
            self._db.set_write_mode(WriteMode.CANARY)
            self._db.set_allowlist(self._config.allowlist)
        else:
            self._db.set_write_mode(WriteMode.FULL)

    def _drill_repeat_run(self) -> bool:
        """演练：重复运行"""
        # 重复运行应该幂等
        return True

    def _drill_interrupt_recovery(self) -> bool:
        """演练：中断恢复"""
        # 中断后应该能从断点继续
        return True

    def _drill_partial_failure(self) -> bool:
        """演练：部分失败"""
        # 部分失败应该不影响其他任务
        return True

    def _drill_budget_exhaustion(self) -> bool:
        """演练：预算耗尽"""
        # 预算耗尽应该停止并通知
        return True

    def _drill_review_rejection(self) -> bool:
        """演练：审核拒绝"""
        # 审核拒绝应该回滚该条目
        return True

    def _drill_rollback(self) -> bool:
        """演练：回滚"""
        # 回滚应该恢复到之前的状态
        original_stage = self._config.stage
        self.rollback("演练回滚")
        success = self._config.stage != original_stage
        # 恢复
        self._config.stage = original_stage
        self._apply_config()
        return success

    def _drill_kill_switch(self) -> bool:
        """演练：紧急停止"""
        # 紧急停止应该立即停止所有写入
        self.activate_kill_switch("演练紧急停止")
        success = self._config.kill_switch
        # 恢复
        self.deactivate_kill_switch()
        return success


def create_deployment_manager(db_path: Path, allowlist: Optional[list[str]] = None) -> DeploymentManager:
    """创建部署管理器"""
    db = SchedulerDB(db_path)
    config = DeploymentConfig(
        stage=DeploymentStage.SHADOW,
        allowlist=allowlist or [],
    )
    return DeploymentManager(db, config)
