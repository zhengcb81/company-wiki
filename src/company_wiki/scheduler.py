"""
scheduler.py — 持久化调度器

只调用服务和队列，不直接改 wiki，不包含业务解析。
"""

import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class WriteMode(str, Enum):
    """写入模式"""
    OFF = "off"          # 完全关闭
    SHADOW = "shadow"    # 只分析，不写入
    CANARY = "canary"    # 只写入 allowlist 中的实体
    FULL = "full"        # 完全开放


class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Job:
    """调度任务"""
    job_id: str
    job_type: str  # collect, register, normalize, analyze, review, project, verify, lint
    entity_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """任务步骤"""
    step_id: str
    job_id: str
    step_type: str
    status: StepStatus = StepStatus.PENDING
    attempt: int = 0
    max_attempts: int = 3
    lease_until: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Budget:
    """预算"""
    total_tokens: int = 1000000
    used_tokens: int = 0
    total_cost_usd: float = 10.0
    used_cost_usd: float = 0.0
    max_retries: int = 3
    retry_count: int = 0

    @property
    def remaining_tokens(self) -> int:
        return self.total_tokens - self.used_tokens

    @property
    def remaining_cost(self) -> float:
        return self.total_cost_usd - self.used_cost_usd

    @property
    def is_exhausted(self) -> bool:
        return self.used_tokens >= self.total_tokens or self.used_cost_usd >= self.total_cost_usd


class SchedulerDB:
    """
    调度器持久化存储。

    使用 SQLite 存储 job/step/attempt/lease 状态。
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    entity_id TEXT,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS steps (
                    step_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    lease_until TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    tokens_used INTEGER,
                    cost_usd REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS write_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    @contextmanager
    def _connect(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ── Job 操作 ──────────────────────────────

    def create_job(self, job: Job) -> Job:
        """创建任务"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO jobs (job_id, job_type, entity_id, status, priority, created_at, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (job.job_id, job.job_type, job.entity_id, job.status.value, job.priority, job.created_at.isoformat(), str(job.metadata)),
                )
                conn.commit()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return Job(
                job_id=row["job_id"],
                job_type=row["job_type"],
                entity_id=row["entity_id"],
                status=JobStatus(row["status"]),
                priority=row["priority"],
                created_at=datetime.fromisoformat(row["created_at"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error_message=row["error_message"],
            )

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None):
        """更新任务状态"""
        with self._lock:
            with self._connect() as conn:
                now = datetime.now().isoformat()
                if status == JobStatus.RUNNING:
                    conn.execute("UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?", (status.value, now, job_id))
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    conn.execute("UPDATE jobs SET status = ?, completed_at = ?, error_message = ? WHERE job_id = ?", (status.value, now, error_message, job_id))
                else:
                    conn.execute("UPDATE jobs SET status = ? WHERE job_id = ?", (status.value, job_id))
                conn.commit()

    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        """获取待处理任务"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT ?",
                (JobStatus.PENDING.value, limit),
            ).fetchall()
            return [
                Job(
                    job_id=row["job_id"],
                    job_type=row["job_type"],
                    entity_id=row["entity_id"],
                    status=JobStatus(row["status"]),
                    priority=row["priority"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    # ── Step 操作 ──────────────────────────────

    def create_step(self, step: Step) -> Step:
        """创建步骤"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO steps (step_id, job_id, step_type, status, attempt, max_attempts) VALUES (?, ?, ?, ?, ?, ?)",
                    (step.step_id, step.job_id, step.step_type, step.status.value, step.attempt, step.max_attempts),
                )
                conn.commit()
        return step

    def update_step_status(self, step_id: str, status: StepStatus, error_message: Optional[str] = None):
        """更新步骤状态"""
        with self._lock:
            with self._connect() as conn:
                now = datetime.now().isoformat()
                if status == StepStatus.RUNNING:
                    conn.execute("UPDATE steps SET status = ?, started_at = ?, attempt = attempt + 1 WHERE step_id = ?", (status.value, now, step_id))
                elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
                    conn.execute("UPDATE steps SET status = ?, completed_at = ?, error_message = ? WHERE step_id = ?", (status.value, now, error_message, step_id))
                else:
                    conn.execute("UPDATE steps SET status = ? WHERE step_id = ?", (status.value, step_id))
                conn.commit()

    def acquire_lease(self, step_id: str, lease_duration: timedelta = timedelta(minutes=5)) -> bool:
        """获取步骤租约"""
        with self._lock:
            with self._connect() as conn:
                now = datetime.now()
                lease_until = (now + lease_duration).isoformat()
                result = conn.execute(
                    "UPDATE steps SET lease_until = ? WHERE step_id = ? AND (lease_until IS NULL OR lease_until < ?)",
                    (lease_until, step_id, now.isoformat()),
                )
                conn.commit()
                return result.rowcount > 0

    def release_lease(self, step_id: str):
        """释放步骤租约"""
        with self._lock:
            with self._connect() as conn:
                conn.execute("UPDATE steps SET lease_until = NULL WHERE step_id = ?", (step_id,))
                conn.commit()

    # ── Budget 操作 ──────────────────────────────

    def log_budget_usage(self, job_id: str, tokens_used: int, cost_usd: float):
        """记录预算使用"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO budget_log (job_id, tokens_used, cost_usd, timestamp) VALUES (?, ?, ?, ?)",
                    (job_id, tokens_used, cost_usd, datetime.now().isoformat()),
                )
                conn.commit()

    def get_budget_usage(self, job_id: Optional[str] = None) -> dict:
        """获取预算使用情况"""
        with self._connect() as conn:
            if job_id:
                row = conn.execute(
                    "SELECT SUM(tokens_used) as total_tokens, SUM(cost_usd) as total_cost FROM budget_log WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT SUM(tokens_used) as total_tokens, SUM(cost_usd) as total_cost FROM budget_log",
                ).fetchone()
            return {
                "total_tokens": row["total_tokens"] or 0,
                "total_cost_usd": row["total_cost"] or 0.0,
            }

    # ── Write Config 操作 ──────────────────────────────

    def set_write_mode(self, mode: WriteMode):
        """设置写入模式"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO write_config (key, value) VALUES (?, ?)",
                    ("write_mode", mode.value),
                )
                conn.commit()

    def get_write_mode(self) -> WriteMode:
        """获取写入模式"""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM write_config WHERE key = ?", ("write_mode",)).fetchone()
            if row:
                return WriteMode(row["value"])
            return WriteMode.OFF  # 默认关闭

    def set_allowlist(self, entities: list[str]):
        """设置 allowlist"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO write_config (key, value) VALUES (?, ?)",
                    ("allowlist", ",".join(entities)),
                )
                conn.commit()

    def get_allowlist(self) -> list[str]:
        """获取 allowlist"""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM write_config WHERE key = ?", ("allowlist",)).fetchone()
            if row and row["value"]:
                return row["value"].split(",")
            return []

    def is_write_allowed(self, entity_id: str) -> bool:
        """检查实体是否允许写入"""
        mode = self.get_write_mode()
        if mode == WriteMode.OFF:
            return False
        if mode == WriteMode.FULL:
            return True
        if mode == WriteMode.CANARY:
            return entity_id in self.get_allowlist()
        # SHADOW 模式不允许写入
        return False


class Scheduler:
    """
    调度器。

    从 registry/job/run/outbox 队列取任务，不直接改 wiki。
    """

    def __init__(self, db: SchedulerDB, budget: Budget):
        self._db = db
        self._budget = budget
        self._running = False

    def schedule_job(self, job_type: str, entity_id: Optional[str] = None, priority: int = 0) -> Job:
        """调度任务"""
        job = Job(
            job_id=f"{job_type}-{entity_id or 'global'}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            job_type=job_type,
            entity_id=entity_id,
            priority=priority,
        )
        return self._db.create_job(job)

    def get_next_job(self) -> Optional[Job]:
        """获取下一个待处理任务"""
        # 检查预算
        if self._budget.is_exhausted:
            return None

        jobs = self._db.get_pending_jobs(limit=1)
        return jobs[0] if jobs else None

    def run_job(self, job: Job, handler: callable):
        """
        运行任务。

        Args:
            job: 任务
            handler: 任务处理函数 (job, step) -> bool
        """
        # 检查写入权限
        if job.entity_id and not self._db.is_write_allowed(job.entity_id):
            self._db.update_job_status(job.job_id, JobStatus.FAILED, "写入权限不足")
            return

        # 启动任务
        self._db.update_job_status(job.job_id, JobStatus.RUNNING)

        try:
            # 创建步骤
            step = Step(
                step_id=f"{job.job_id}-step-1",
                job_id=job.job_id,
                step_type=job.job_type,
            )
            self._db.create_step(step)

            # 获取租约
            if not self._db.acquire_lease(step.step_id):
                self._db.update_job_status(job.job_id, JobStatus.FAILED, "无法获取租约")
                return

            # 执行处理
            success = handler(job, step)

            # 释放租约
            self._db.release_lease(step.step_id)

            # 更新状态
            if success:
                self._db.update_step_status(step.step_id, StepStatus.COMPLETED)
                self._db.update_job_status(job.job_id, JobStatus.COMPLETED)
            else:
                self._db.update_step_status(step.step_id, StepStatus.FAILED)
                self._db.update_job_status(job.job_id, JobStatus.FAILED)

        except Exception as e:
            self._db.update_job_status(job.job_id, JobStatus.FAILED, str(e))

    def start(self, handler: callable):
        """启动调度循环"""
        self._running = True
        while self._running:
            job = self.get_next_job()
            if job:
                self.run_job(job, handler)
            else:
                time.sleep(1)  # 等待新任务

    def stop(self):
        """停止调度循环"""
        self._running = False


def create_scheduler(db_path: Path, budget: Optional[Budget] = None) -> Scheduler:
    """创建调度器实例"""
    db = SchedulerDB(db_path)
    if budget is None:
        budget = Budget()
    return Scheduler(db, budget)
