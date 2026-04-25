#!/usr/bin/env python3
"""
ingested_db.py — SQLite 标记数据库（替代 .ingested/*.hash 文件系统）

功能：
- 用单文件 SQLite 替代数千个微型 .hash 文件
- 无缝迁移旧 .hash 文件到新数据库
- 文件哈希缓存，避免重复读取
- 错误处理：文件删除不会中断批处理

用法：
    from ingested_db import IngestedDB

    db = IngestedDB()
    ingested = db.get_ingested_set()
    db.mark_ingested("/path/to/file.pdf")
    ok = db.is_ingested("/path/to/file.pdf")
    db.close()
"""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Set

from common import WIKI_ROOT

logger = logging.getLogger(__name__)

# ── 路径 ──────────────────────────────────
DEFAULT_DB_PATH = WIKI_ROOT / ".ingested" / "ingested.db"
HASH_DIR = WIKI_ROOT / ".ingested"


class IngestedDB:
    """SQLite 标记数据库"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS ingested "
            "(hash TEXT PRIMARY KEY, created_at TEXT DEFAULT (datetime('now')))"
        )
        self._conn.commit()
        # 自动从旧 .hash 文件迁移（仅首次）
        self._auto_migrate()
        self._cache: Optional[Set[str]] = None
        # 文件路径 → hash 缓存，避免重复读取同一文件
        self._hash_cache: dict = {}

    def close(self):
        """关闭数据库连接"""
        self._conn.close()

    def get_ingested_set(self) -> Set[str]:
        """获取所有已标记的 hash 集合"""
        if self._cache is None:
            rows = self._conn.execute("SELECT hash FROM ingested").fetchall()
            self._cache = {row[0] for row in rows}
        return self._cache

    def _compute_hash(self, file_path: str) -> Optional[str]:
        """计算文件 MD5 哈希，带缓存和错误处理"""
        if file_path in self._hash_cache:
            return self._hash_cache[file_path]
        try:
            content = Path(file_path).read_bytes()
            file_hash = hashlib.md5(content).hexdigest()
            self._hash_cache[file_path] = file_hash
            return file_hash
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"无法读取文件计算哈希: {file_path}: {e}")
            return None

    def mark_ingested(self, file_path: str) -> None:
        """标记文件为已处理"""
        file_hash = self._compute_hash(file_path)
        if file_hash is None:
            return
        self._conn.execute(
            "INSERT OR IGNORE INTO ingested (hash) VALUES (?)",
            (file_hash,),
        )
        self._conn.commit()
        if self._cache is not None:
            self._cache.add(file_hash)

    def is_ingested(self, file_path: str, ingested_set: Optional[Set[str]] = None) -> bool:
        """检查文件是否已被处理"""
        file_hash = self._compute_hash(file_path)
        if file_hash is None:
            return False
        if ingested_set is not None:
            return file_hash in ingested_set
        return file_hash in self.get_ingested_set()

    def clear(self) -> None:
        """清空所有标记"""
        self._conn.execute("DELETE FROM ingested")
        self._conn.commit()
        self._cache = None
        self._hash_cache.clear()

    def count(self) -> int:
        """返回已标记的文件数"""
        row = self._conn.execute("SELECT COUNT(*) FROM ingested").fetchone()
        return row[0] if row else 0

    def _auto_migrate(self) -> int:
        """从旧的 .hash 文件自动迁移（仅首次）"""
        # 检查 DB 是否已有数据
        count = self.count()
        if count > 0:
            return 0

        # 检查是否有 .hash 文件
        hash_files = list(HASH_DIR.glob("*.hash"))
        if not hash_files:
            return 0

        imported = 0
        for f in hash_files:
            try:
                h = f.read_text().strip()
                if h:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO ingested (hash) VALUES (?)",
                        (h,),
                    )
                    imported += 1
            except Exception:
                pass

        self._conn.commit()
        print(f"[ingested_db] 已迁移 {imported}/{len(hash_files)} 个 .hash 文件到 SQLite")
        return imported


# ── 单例工厂 ──────────────────────────────
_default_db: Optional[IngestedDB] = None


def get_db() -> IngestedDB:
    """获取全局单例"""
    global _default_db
    if _default_db is None:
        _default_db = IngestedDB()
    return _default_db


# ── 独立运行：迁移或统计 ──────────────────
if __name__ == "__main__":
    import sys

    db = IngestedDB()
    if "--migrate" in sys.argv:
        n = db._auto_migrate()
        print(f"迁移完成: {n} 条记录")
    elif "--clear" in sys.argv:
        db.clear()
        print("已清空所有标记")
    else:
        print(f"数据库路径: {db.db_path}")
        print(f"记录数: {db.count()}")
        hash_files = list(HASH_DIR.glob("*.hash"))
        print(f".hash 文件数: {len(hash_files)}")
    db.close()
