"""
数据库管理
包含 SQLite 数据库连接和 schema 定义
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 数据库 schema
SCHEMA = """
-- 公司表
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    ticker TEXT,
    exchange TEXT,
    position TEXT,
    sectors TEXT,  -- JSON 数组
    themes TEXT,   -- JSON 数组
    news_queries TEXT,  -- JSON 数组
    aliases TEXT,  -- JSON 数组
    competes_with TEXT,  -- JSON 数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 行业表
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT CHECK(type IN ('sector', 'subsector')),
    description TEXT,
    tier INTEGER,
    keywords TEXT,  -- JSON 数组
    parent_theme TEXT,  -- JSON 数组
    parent_sector TEXT,  -- JSON 数组
    questions TEXT,  -- JSON 数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 主题表
CREATE TABLE IF NOT EXISTS themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    keywords TEXT,  -- JSON 数组
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 边表
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_entity, to_entity, edge_type)
);

-- Wiki 条目表
CREATE TABLE IF NOT EXISTS wiki_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    content TEXT,
    last_updated DATE,
    sources_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_name, entity_type, topic_name)
);

-- 已处理文件表
CREATE TABLE IF NOT EXISTS ingested_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 问题表
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    question TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_name, question)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_sectors_name ON sectors(name);
CREATE INDEX IF NOT EXISTS idx_themes_name ON themes(name);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_entity);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_entity);
CREATE INDEX IF NOT EXISTS idx_wiki_entity ON wiki_entries(entity_name, entity_type);
CREATE INDEX IF NOT EXISTS idx_ingested_hash ON ingested_files(file_hash);
"""


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认为 ~/company-wiki/data/wiki.db
        """
        if db_path is None:
            db_path = Path.home() / "company-wiki" / "data" / "wiki.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库 schema"""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA)
            logger.info(f"数据库初始化完成: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        Usage:
            with db.get_connection() as conn:
                conn.execute("SELECT * FROM companies")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 返回字典而不是元组
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()
    
    def execute(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            if cursor.description:
                return [dict(row) for row in cursor.fetchall()]
            return []
    
    def execute_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        执行 SQL 查询，返回单条结果
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            结果字典，如果没有结果返回 None
        """
        results = self.execute(sql, params)
        return results[0] if results else None
    
    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """
        执行插入操作
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            插入的行 ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid
    
    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        执行更新操作
        
        Args:
            sql: SQL 语句
            params: 参数
            
        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount
    
    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            备份文件路径
        """
        if backup_path is None:
            backup_path = self.db_path.with_suffix(".db.bak")
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"数据库备份完成: {backup_path}")
        return backup_path
    
    def restore(self, backup_path: Optional[Path] = None) -> None:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
        """
        if backup_path is None:
            backup_path = self.db_path.with_suffix(".db.bak")
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        import shutil
        shutil.copy2(backup_path, self.db_path)
        logger.info(f"数据库恢复完成: {backup_path}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        stats = {}
        
        tables = ["companies", "sectors", "themes", "edges", "wiki_entries", "ingested_files"]
        for table in tables:
            result = self.execute_one(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = result["count"] if result else 0
        
        return stats
    
    def vacuum(self) -> None:
        """优化数据库"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("数据库优化完成")
    
    def close(self) -> None:
        """关闭数据库连接"""
        # SQLite 连接在上下文管理器中自动关闭
        pass