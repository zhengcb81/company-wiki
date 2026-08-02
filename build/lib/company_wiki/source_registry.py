"""
source_registry.py — 来源注册表

管理所有原始来源的注册、去重、状态和元数据。
路径只作为 location，不作为身份；SHA-256 为来源身份。
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .domain import SourceRecord, SourceKind


# ── Schema ──────────────────────────────

_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    publisher TEXT DEFAULT '',
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    url TEXT DEFAULT '',
    license TEXT DEFAULT '',
    quality_score REAL DEFAULT 0.0,
    status TEXT DEFAULT 'registered',  -- registered/processing/completed/quarantined
    entity_hints TEXT DEFAULT '[]',    -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_aliases (
    alias_path TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_content_hash ON sources(content_hash);
CREATE INDEX IF NOT EXISTS idx_source_aliases_source_id ON source_aliases(source_id);
"""


class SourceRegistry:
    """
    来源注册表。

    使用 SQLite 管理所有来源的状态和元数据。
    来源身份 = SHA-256(content)；路径仅为 location。
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        """初始化数据库 schema"""
        # 检查版本
        current_version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if current_version < _SCHEMA_VERSION:
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
            self._conn.commit()

    def close(self):
        """关闭数据库连接"""
        self._conn.close()

    # ── 注册 ──────────────────────────────

    def register(
        self,
        path: Path,
        source_kind: SourceKind,
        publisher: str = "",
        published_at: Optional[datetime] = None,
        url: str = "",
        entity_hints: list[str] = None,
    ) -> SourceRecord:
        """
        注册一个来源。如果已存在（相同 content_hash），返回现有记录。

        Args:
            path: 文件路径
            source_kind: 来源类型
            publisher: 发布者
            published_at: 发布时间
            url: 来源 URL
            entity_hints: 关联实体提示

        Returns:
            SourceRecord
        """
        # 计算 content hash
        content_hash = self._hash_file(path)
        size = path.stat().st_size if path.exists() else 0

        # 检查是否已存在
        existing = self._get_by_hash(content_hash)
        if existing:
            # 添加别名
            self._add_alias(str(path), existing.source_id)
            return existing

        # 创建新记录
        source_id = content_hash  # 用 content hash 作为 source_id
        now = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO sources (source_id, path, source_kind, publisher,
               published_at, fetched_at, content_hash, size, url, quality_score,
               status, entity_hints, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registered', ?, ?, ?)""",
            (
                source_id, str(path), source_kind.value, publisher,
                published_at.isoformat() if published_at else None,
                now, content_hash, size, url, 0.0,
                json.dumps(entity_hints or []), now, now,
            ),
        )
        self._conn.commit()

        return SourceRecord(
            source_id=source_id,
            path=str(path),
            source_kind=source_kind,
            publisher=publisher,
            published_at=published_at,
            fetched_at=datetime.now(),
            content_hash=content_hash,
            size=size,
            url=url,
            entity_hints=entity_hints or [],
        )

    def get(self, source_id: str) -> Optional[SourceRecord]:
        """根据 source_id 获取来源记录"""
        row = self._conn.execute(
            "SELECT * FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def get_by_path(self, path: str) -> Optional[SourceRecord]:
        """根据路径获取来源记录"""
        # 先查主表
        row = self._conn.execute(
            "SELECT * FROM sources WHERE path = ?", (path,)
        ).fetchone()
        if row:
            return self._row_to_record(row)

        # 再查别名
        alias = self._conn.execute(
            "SELECT source_id FROM source_aliases WHERE alias_path = ?", (path,)
        ).fetchone()
        if alias:
            return self.get(alias["source_id"])
        return None

    def list_by_status(self, status: str, limit: int = 100) -> list[SourceRecord]:
        """按状态列出来源"""
        rows = self._conn.execute(
            "SELECT * FROM sources WHERE status = ? LIMIT ?", (status, limit)
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count_by_status(self) -> dict[str, int]:
        """统计各状态的来源数量"""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM sources GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}

    def update_status(self, source_id: str, status: str):
        """更新来源状态"""
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE sources SET status = ?, updated_at = ? WHERE source_id = ?",
            (status, now, source_id),
        )
        self._conn.commit()

    def quarantine(self, source_id: str, reason: str = ""):
        """隔离来源（不删除，保留内容和原因）"""
        self.update_status(source_id, "quarantined")

    def exists(self, content_hash: str) -> bool:
        """检查是否已有相同内容的来源"""
        row = self._conn.execute(
            "SELECT 1 FROM sources WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return row is not None

    # ── 内部方法 ──────────────────────────────

    def _hash_file(self, path: Path) -> str:
        """计算文件 SHA-256"""
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        except (OSError, FileNotFoundError):
            h.update(str(path).encode())
        return h.hexdigest()

    def _get_by_hash(self, content_hash: str) -> Optional[SourceRecord]:
        """根据 content_hash 获取来源"""
        row = self._conn.execute(
            "SELECT * FROM sources WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if row:
            return self._row_to_record(row)
        return None

    def _add_alias(self, alias_path: str, source_id: str):
        """添加路径别名"""
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO source_aliases (alias_path, source_id) VALUES (?, ?)",
                (alias_path, source_id),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass

    def _row_to_record(self, row: sqlite3.Row) -> SourceRecord:
        """将数据库行转换为 SourceRecord"""
        return SourceRecord(
            source_id=row["source_id"],
            path=row["path"],
            source_kind=SourceKind(row["source_kind"]),
            publisher=row["publisher"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            content_hash=row["content_hash"],
            size=row["size"],
            url=row["url"],
            quality_score=row["quality_score"],
            entity_hints=json.loads(row["entity_hints"]) if row["entity_hints"] else [],
        )
