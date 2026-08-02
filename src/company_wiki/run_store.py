"""
run_store.py — 运行状态存储

管理处理运行的状态：job/step/attempt/lease/budget/outcome。
替代旧的 state_store.py 中的时间戳逻辑。
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    attempt INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',  -- pending/running/completed/failed/blocked
    error TEXT DEFAULT '',
    cost REAL DEFAULT 0.0,
    tokens_used INTEGER DEFAULT 0,
    patch_id TEXT DEFAULT '',
    output_hash TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    patch_id TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_page TEXT NOT NULL,
    status TEXT DEFAULT 'planned',  -- planned/patch_ready/validated/committed/verified/failed
    before_hash TEXT DEFAULT '',
    after_hash TEXT DEFAULT '',
    error TEXT DEFAULT '',
    attempt INTEGER DEFAULT 1,
    idempotency_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    committed_at TEXT,
    verified_at TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS budget_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    amount REAL NOT NULL,
    reason TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_runs_source_id ON runs(source_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_run_id ON deliveries(run_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_idempotency ON deliveries(idempotency_key);
"""


class RunStore:
    """
    运行状态存储。

    管理处理运行的生命周期：创建、执行、完成、失败。
    支持 delivery outbox 和预算账本。
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        """初始化数据库 schema"""
        current_version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if current_version < _SCHEMA_VERSION:
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
            self._conn.commit()

    def close(self):
        """关闭数据库连接"""
        self._conn.close()

    # ── Run 管理 ──────────────────────────────

    def create_run(
        self,
        source_id: str,
        pipeline_version: str,
        run_id: str = None,
    ) -> str:
        """
        创建新的处理运行。

        Returns:
            run_id
        """
        if not run_id:
            import hashlib
            run_id = hashlib.sha256(
                f"{source_id}:{pipeline_version}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]

        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT OR IGNORE INTO runs
               (run_id, source_id, pipeline_version, status, created_at, updated_at)
               VALUES (?, ?, ?, 'pending', ?, ?)""",
            (run_id, source_id, pipeline_version, now, now),
        )
        self._conn.commit()
        return run_id

    def start_run(self, run_id: str):
        """标记运行开始"""
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE runs SET status = 'running', updated_at = ? WHERE run_id = ?",
            (now, run_id),
        )
        self._conn.commit()

    def complete_run(self, run_id: str, output_hash: str = ""):
        """标记运行完成"""
        now = datetime.now().isoformat()
        self._conn.execute(
            """UPDATE runs SET status = 'completed', output_hash = ?,
               completed_at = ?, updated_at = ? WHERE run_id = ?""",
            (output_hash, now, now, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str, error: str):
        """标记运行失败"""
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE runs SET status = 'failed', error = ?, updated_at = ? WHERE run_id = ?",
            (error, now, run_id),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> Optional[dict]:
        """获取运行记录"""
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_pending_runs(self, limit: int = 10) -> list[dict]:
        """获取待处理的运行"""
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE status = 'pending' ORDER BY created_at LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_by_status(self) -> dict[str, int]:
        """统计各状态的运行数量"""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM runs GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}

    # ── Delivery 管理 ──────────────────────────────

    def create_delivery(
        self,
        run_id: str,
        patch_id: str,
        target_entity: str,
        target_page: str,
        idempotency_key: str = None,
    ) -> str:
        """
        创建 delivery outbox 条目。

        Args:
            run_id: 运行 ID
            patch_id: 提案 ID
            target_entity: 目标实体
            target_page: 目标页面路径
            idempotency_key: 幂等键（patch_id + target + claim_id）

        Returns:
            delivery_id
        """
        import hashlib
        delivery_id = hashlib.sha256(
            f"{run_id}:{patch_id}:{target_entity}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        if not idempotency_key:
            idempotency_key = f"{patch_id}:{target_entity}:{target_page}"

        now = datetime.now().isoformat()
        try:
            self._conn.execute(
                """INSERT INTO deliveries
                   (delivery_id, run_id, patch_id, target_entity, target_page,
                    idempotency_key, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'planned', ?, ?)""",
                (delivery_id, run_id, patch_id, target_entity, target_page,
                 idempotency_key, now, now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            # 已存在（幂等）
            row = self._conn.execute(
                "SELECT delivery_id FROM deliveries WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row:
                delivery_id = row["delivery_id"]

        return delivery_id

    def update_delivery_status(self, delivery_id: str, status: str, error: str = ""):
        """更新 delivery 状态"""
        now = datetime.now().isoformat()
        updates = {"status": status, "updated_at": now, "error": error}
        if status == "committed":
            updates["committed_at"] = now
        elif status == "verified":
            updates["verified_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [delivery_id]
        self._conn.execute(
            f"UPDATE deliveries SET {set_clause} WHERE delivery_id = ?", values
        )
        self._conn.commit()

    def get_deliveries(self, run_id: str) -> list[dict]:
        """获取运行的所有 delivery"""
        rows = self._conn.execute(
            "SELECT * FROM deliveries WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_incomplete_deliveries(self, run_id: str) -> list[dict]:
        """获取未完成的 delivery"""
        rows = self._conn.execute(
            """SELECT * FROM deliveries WHERE run_id = ?
               AND status NOT IN ('committed', 'verified', 'failed')
               ORDER BY created_at""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 预算 ──────────────────────────────

    def log_cost(self, run_id: str, amount: float, reason: str = ""):
        """记录成本"""
        now = datetime.now().isoformat()
        self._conn.execute(
            "INSERT INTO budget_log (run_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (run_id, amount, reason, now),
        )
        # 更新 run 的成本
        self._conn.execute(
            "UPDATE runs SET cost = cost + ?, updated_at = ? WHERE run_id = ?",
            (amount, now, run_id),
        )
        self._conn.commit()

    def get_total_cost(self, run_id: str = None) -> float:
        """获取总成本"""
        if run_id:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM budget_log WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM budget_log"
            ).fetchone()
        return row["total"] if row else 0.0
