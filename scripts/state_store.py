#!/usr/bin/env python3
"""
state_store.py — 动态状态存储

核心设计：
- 分离动态状态（最后采集时间、评估分数、错误次数）from 静态配置（config.yaml）
- scheduler 不再扫描文件系统来推断状态，直接查 state.db
- 支持 per-company / per-page / per-prompt 状态追踪

用法：
    from state_store import get_state
    state = get_state()
    state.set_last_collect("中微公司", "2026-04-25")
    state.increment_error_count("ingest_v2", "parse_error")
    state.get_company_state("中微公司")
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# ── 路径 ──────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
DB_PATH = WIKI_ROOT / ".state" / "state.db"


class StateStore:
    """SQLite-backed dynamic state store."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with self._conn() as conn:
            # 公司级状态
            conn.execute("""
                CREATE TABLE IF NOT EXISTS company_state (
                    company_name TEXT PRIMARY KEY,
                    last_collect_time TIMESTAMP,
                    last_ingest_time TIMESTAMP,
                    last_assessment_time TIMESTAMP,
                    entry_count INTEGER DEFAULT 0,
                    avg_entry_quality REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 页面级状态
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_state (
                    page_path TEXT PRIMARY KEY,
                    last_updated TIMESTAMP,
                    entry_count INTEGER DEFAULT 0,
                    assessment_score REAL,
                    stale_marked BOOLEAN DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Prompt 成功率追踪
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_stats (
                    prompt_name TEXT PRIMARY KEY,
                    version TEXT,
                    call_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    parse_error_count INTEGER DEFAULT 0,
                    avg_tokens INTEGER,
                    avg_latency_ms INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 错误计数器
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_counter (
                    module TEXT,
                    error_type TEXT,
                    count INTEGER DEFAULT 0,
                    last_occurred TIMESTAMP,
                    PRIMARY KEY (module, error_type)
                )
            """)

            # 指标历史（用于趋势分析）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics_history (
                    metric_name TEXT,
                    metric_value REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # ── 公司级状态 ─────────────────────────

    def set_last_collect(self, company: str, timestamp: Optional[str] = None):
        now = timestamp or datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO company_state (company_name, last_collect_time, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(company_name) DO UPDATE SET
                   last_collect_time = excluded.last_collect_time,
                   updated_at = excluded.updated_at""",
                (company, now, now),
            )
            conn.commit()

    def set_last_ingest(self, company: str, timestamp: Optional[str] = None):
        now = timestamp or datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO company_state (company_name, last_ingest_time, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(company_name) DO UPDATE SET
                   last_ingest_time = excluded.last_ingest_time,
                   updated_at = excluded.updated_at""",
                (company, now, now),
            )
            conn.commit()

    def set_last_assessment(self, company: str, timestamp: Optional[str] = None):
        now = timestamp or datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO company_state (company_name, last_assessment_time, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(company_name) DO UPDATE SET
                   last_assessment_time = excluded.last_assessment_time,
                   updated_at = excluded.updated_at""",
                (company, now, now),
            )
            conn.commit()

    def update_entry_stats(self, company: str, entry_count: int, avg_quality: float):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO company_state (company_name, entry_count, avg_entry_quality, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(company_name) DO UPDATE SET
                   entry_count = excluded.entry_count,
                   avg_entry_quality = excluded.avg_entry_quality,
                   updated_at = excluded.updated_at""",
                (company, entry_count, avg_quality, datetime.now().isoformat()),
            )
            conn.commit()

    def get_company_state(self, company: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM company_state WHERE company_name = ?", (company,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def get_all_company_states(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM company_state").fetchall()
            return [dict(row) for row in rows]

    def get_companies_needing_collect(self, days: int = 7) -> List[str]:
        """获取超过 N 天未采集的公司。"""
        cutoff = datetime.now() - __import__("datetime").timedelta(days=days)
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT company_name FROM company_state
                   WHERE last_collect_time IS NULL
                      OR last_collect_time < ?
                   ORDER BY last_collect_time ASC""",
                (cutoff.isoformat(),),
            ).fetchall()
            return [row["company_name"] for row in rows]

    # ── Prompt 统计 ────────────────────────

    def record_prompt_call(
        self,
        prompt_name: str,
        version: str,
        success: bool,
        parse_error: bool = False,
        tokens: int = 0,
        latency_ms: int = 0,
    ):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO prompt_stats (prompt_name, version, call_count, success_count,
                    parse_error_count, avg_tokens, avg_latency_ms, updated_at)
                   VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                   ON CONFLICT(prompt_name) DO UPDATE SET
                   version = excluded.version,
                   call_count = call_count + 1,
                   success_count = success_count + excluded.success_count,
                   parse_error_count = parse_error_count + excluded.parse_error_count,
                   avg_tokens = (avg_tokens * call_count + excluded.avg_tokens) / (call_count + 1),
                   avg_latency_ms = (avg_latency_ms * call_count + excluded.avg_latency_ms) / (call_count + 1),
                   updated_at = excluded.updated_at""",
                (
                    prompt_name,
                    version,
                    1 if success else 0,
                    1 if parse_error else 0,
                    tokens,
                    latency_ms,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_prompt_stats(self, prompt_name: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM prompt_stats WHERE prompt_name = ?", (prompt_name,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    # ── 错误计数 ───────────────────────────

    def increment_error_count(self, module: str, error_type: str):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO error_counter (module, error_type, count, last_occurred)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(module, error_type) DO UPDATE SET
                   count = count + 1,
                   last_occurred = excluded.last_occurred""",
                (module, error_type, now),
            )
            conn.commit()

    def get_error_counts(self, module: Optional[str] = None) -> List[Dict]:
        with self._conn() as conn:
            if module:
                rows = conn.execute(
                    "SELECT * FROM error_counter WHERE module = ? ORDER BY count DESC",
                    (module,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM error_counter ORDER BY count DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    # ── 指标历史 ───────────────────────────

    def record_metric(self, metric_name: str, metric_value: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO metrics_history (metric_name, metric_value) VALUES (?, ?)",
                (metric_name, metric_value),
            )
            conn.commit()

    def get_metric_history(self, metric_name: str, limit: int = 30) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM metrics_history
                   WHERE metric_name = ?
                   ORDER BY recorded_at DESC
                   LIMIT ?""",
                (metric_name, limit),
            ).fetchall()
            return [dict(row) for row in rows]


# ── 单例 ──────────────────────────────────
_STATE_INSTANCE: Optional[StateStore] = None


def get_state() -> StateStore:
    global _STATE_INSTANCE
    if _STATE_INSTANCE is None:
        _STATE_INSTANCE = StateStore()
    return _STATE_INSTANCE


# ── CLI ───────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="State Store CLI")
    parser.add_argument("--company", help="Show company state")
    parser.add_argument("--errors", action="store_true", help="Show error counts")
    parser.add_argument("--prompts", action="store_true", help="Show prompt stats")
    parser.add_argument(
        "--set-collect",
        nargs=2,
        metavar=("COMPANY", "TIME"),
        help="Set last collect time",
    )
    args = parser.parse_args()

    state = get_state()

    if args.company:
        s = state.get_company_state(args.company)
        print(json.dumps(s, indent=2, ensure_ascii=False) if s else "No state found")
    elif args.errors:
        errors = state.get_error_counts()
        for e in errors:
            print(
                f"  {e['module']}/{e['error_type']}: {e['count']} (last: {e['last_occurred']})"
            )
    elif args.prompts:
        print("Prompt stats not yet implemented in CLI")
    elif args.set_collect:
        state.set_last_collect(args.set_collect[0], args.set_collect[1])
        print(f"Set last_collect for {args.set_collect[0]} = {args.set_collect[1]}")
    else:
        parser.print_help()
