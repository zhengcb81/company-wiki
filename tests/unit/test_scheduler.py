"""
tests/unit/test_scheduler.py — 调度器测试
"""


import pytest

from company_wiki.scheduler import (
    Budget,
    Job,
    JobStatus,
    Scheduler,
    SchedulerDB,
    Step,
    StepStatus,
    WriteMode,
    create_scheduler,
)


# ── SchedulerDB 测试 ──────────────────────────────

class TestSchedulerDB:
    def test_init_db(self, tmp_path):
        """测试数据库初始化"""
        db_path = tmp_path / "scheduler.db"
        SchedulerDB(db_path)
        assert db_path.exists()

    def test_create_and_get_job(self, tmp_path):
        """测试创建和获取任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        job = Job(
            job_id="test-job-001",
            job_type="analyze",
            entity_id="北方华创",
        )

        db.create_job(job)
        loaded = db.get_job("test-job-001")

        assert loaded is not None
        assert loaded.job_type == "analyze"
        assert loaded.entity_id == "北方华创"

    def test_update_job_status(self, tmp_path):
        """测试更新任务状态"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        job = Job(job_id="test-job-001", job_type="analyze")
        db.create_job(job)

        # 启动
        db.update_job_status("test-job-001", JobStatus.RUNNING)
        loaded = db.get_job("test-job-001")
        assert loaded.status == JobStatus.RUNNING
        assert loaded.started_at is not None

        # 完成
        db.update_job_status("test-job-001", JobStatus.COMPLETED)
        loaded = db.get_job("test-job-001")
        assert loaded.status == JobStatus.COMPLETED
        assert loaded.completed_at is not None

    def test_update_job_status_failed(self, tmp_path):
        """测试更新任务状态为失败"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        job = Job(job_id="test-job-001", job_type="analyze")
        db.create_job(job)

        db.update_job_status("test-job-001", JobStatus.FAILED, "错误信息")
        loaded = db.get_job("test-job-001")
        assert loaded.status == JobStatus.FAILED
        assert loaded.error_message == "错误信息"

    def test_get_pending_jobs(self, tmp_path):
        """测试获取待处理任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        # 创建多个任务
        db.create_job(Job(job_id="job-1", job_type="analyze", priority=1))
        db.create_job(Job(job_id="job-2", job_type="analyze", priority=3))
        db.create_job(Job(job_id="job-3", job_type="analyze", priority=2))

        # 获取待处理任务（按优先级排序）
        jobs = db.get_pending_jobs(limit=2)
        assert len(jobs) == 2
        assert jobs[0].priority >= jobs[1].priority

    def test_create_and_update_step(self, tmp_path):
        """测试创建和更新步骤"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        job = Job(job_id="test-job-001", job_type="analyze")
        db.create_job(job)

        step = Step(step_id="step-001", job_id="test-job-001", step_type="analyze")
        db.create_step(step)

        # 启动步骤
        db.update_step_status("step-001", StepStatus.RUNNING)
        # 完成步骤
        db.update_step_status("step-001", StepStatus.COMPLETED)

    def test_acquire_and_release_lease(self, tmp_path):
        """测试获取和释放租约"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        job = Job(job_id="test-job-001", job_type="analyze")
        db.create_job(job)

        step = Step(step_id="step-001", job_id="test-job-001", step_type="analyze")
        db.create_step(step)

        # 获取租约
        assert db.acquire_lease("step-001") is True

        # 释放租约
        db.release_lease("step-001")

        # 释放后再次获取应该成功
        assert db.acquire_lease("step-001") is True

    def test_budget_logging(self, tmp_path):
        """测试预算日志"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        db.log_budget_usage("job-1", 1000, 0.05)
        db.log_budget_usage("job-1", 2000, 0.10)
        db.log_budget_usage("job-2", 500, 0.02)

        # 查询特定任务
        usage = db.get_budget_usage("job-1")
        assert usage["total_tokens"] == 3000
        assert usage["total_cost_usd"] == pytest.approx(0.15)

        # 查询全部
        usage = db.get_budget_usage()
        assert usage["total_tokens"] == 3500

    def test_write_mode(self, tmp_path):
        """测试写入模式"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        # 默认 OFF
        assert db.get_write_mode() == WriteMode.OFF

        # 设置为 CANARY
        db.set_write_mode(WriteMode.CANARY)
        assert db.get_write_mode() == WriteMode.CANARY

    def test_allowlist(self, tmp_path):
        """测试 allowlist"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        # 设置 allowlist
        db.set_allowlist(["北方华创", "中微公司"])
        assert db.get_allowlist() == ["北方华创", "中微公司"]

        # 检查写入权限
        db.set_write_mode(WriteMode.CANARY)
        assert db.is_write_allowed("北方华创") is True
        assert db.is_write_allowed("中芯国际") is False

    def test_write_mode_off_blocks_all(self, tmp_path):
        """测试 OFF 模式阻止所有写入"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        db.set_write_mode(WriteMode.OFF)
        assert db.is_write_allowed("北方华创") is False

    def test_write_mode_full_allows_all(self, tmp_path):
        """测试 FULL 模式允许所有写入"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        db.set_write_mode(WriteMode.FULL)
        assert db.is_write_allowed("任意实体") is True

    def test_write_mode_shadow_no_write(self, tmp_path):
        """测试 SHADOW 模式不允许写入"""
        db = SchedulerDB(tmp_path / "scheduler.db")

        db.set_write_mode(WriteMode.SHADOW)
        assert db.is_write_allowed("北方华创") is False


# ── Budget 测试 ──────────────────────────────

class TestBudget:
    def test_budget_creation(self):
        """测试预算创建"""
        budget = Budget(total_tokens=1000000, total_cost_usd=10.0)
        assert budget.remaining_tokens == 1000000
        assert budget.remaining_cost == pytest.approx(10.0)
        assert budget.is_exhausted is False

    def test_budget_exhausted(self):
        """测试预算耗尽"""
        budget = Budget(total_tokens=1000, total_cost_usd=1.0)
        budget.used_tokens = 1000
        assert budget.is_exhausted is True

    def test_budget_cost_exhausted(self):
        """测试成本预算耗尽"""
        budget = Budget(total_tokens=1000, total_cost_usd=1.0)
        budget.used_cost_usd = 1.0
        assert budget.is_exhausted is True


# ── Scheduler 测试 ──────────────────────────────

class TestScheduler:
    def test_schedule_job(self, tmp_path):
        """测试调度任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        job = scheduler.schedule_job("analyze", entity_id="北方华创", priority=5)
        assert job.job_type == "analyze"
        assert job.entity_id == "北方华创"
        assert job.priority == 5

    def test_get_next_job(self, tmp_path):
        """测试获取下一个任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        # 没有任务
        assert scheduler.get_next_job() is None

        # 添加任务
        scheduler.schedule_job("analyze", entity_id="北方华创")
        job = scheduler.get_next_job()
        assert job is not None
        assert job.entity_id == "北方华创"

    def test_get_next_job_budget_exhausted(self, tmp_path):
        """测试预算耗尽时获取任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget(total_tokens=100)
        budget.used_tokens = 100  # 耗尽
        scheduler = Scheduler(db, budget)

        scheduler.schedule_job("analyze")
        assert scheduler.get_next_job() is None

    def test_run_job_success(self, tmp_path):
        """测试成功运行任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        job = scheduler.schedule_job("analyze", entity_id="北方华创")

        # 设置写入权限
        db.set_write_mode(WriteMode.FULL)

        # 运行任务
        def handler(j, s):
            return True

        scheduler.run_job(job, handler)

        # 检查状态
        loaded = db.get_job(job.job_id)
        assert loaded.status == JobStatus.COMPLETED

    def test_run_job_failure(self, tmp_path):
        """测试任务失败"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        job = scheduler.schedule_job("analyze", entity_id="北方华创")

        # 设置写入权限
        db.set_write_mode(WriteMode.FULL)

        # 运行任务
        def handler(j, s):
            return False

        scheduler.run_job(job, handler)

        # 检查状态
        loaded = db.get_job(job.job_id)
        assert loaded.status == JobStatus.FAILED

    def test_run_job_exception(self, tmp_path):
        """测试任务异常"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        job = scheduler.schedule_job("analyze", entity_id="北方华创")

        # 设置写入权限
        db.set_write_mode(WriteMode.FULL)

        # 运行任务
        def handler(j, s):
            raise ValueError("测试异常")

        scheduler.run_job(job, handler)

        # 检查状态
        loaded = db.get_job(job.job_id)
        assert loaded.status == JobStatus.FAILED
        assert "测试异常" in loaded.error_message

    def test_run_job_no_write_permission(self, tmp_path):
        """测试无写入权限时运行任务"""
        db = SchedulerDB(tmp_path / "scheduler.db")
        budget = Budget()
        scheduler = Scheduler(db, budget)

        job = scheduler.schedule_job("analyze", entity_id="北方华创")

        # 不设置写入权限（默认 OFF）

        # 运行任务
        def handler(j, s):
            return True

        scheduler.run_job(job, handler)

        # 检查状态
        loaded = db.get_job(job.job_id)
        assert loaded.status == JobStatus.FAILED
        assert "写入权限" in loaded.error_message


# ── create_scheduler 测试 ──────────────────────────────

class TestCreateScheduler:
    def test_create_scheduler(self, tmp_path):
        """测试创建调度器"""
        db_path = tmp_path / "scheduler.db"
        scheduler = create_scheduler(db_path)

        assert scheduler is not None
        assert db_path.exists()

    def test_create_scheduler_with_budget(self, tmp_path):
        """测试创建调度器（自定义预算）"""
        db_path = tmp_path / "scheduler.db"
        budget = Budget(total_tokens=500000, total_cost_usd=5.0)
        scheduler = create_scheduler(db_path, budget)

        assert scheduler._budget.total_tokens == 500000
