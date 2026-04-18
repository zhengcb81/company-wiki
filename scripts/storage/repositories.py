"""
数据访问层
实现 Repository 模式
"""
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .database import Database

logger = logging.getLogger(__name__)


class CompanyRepository:
    """公司数据访问层"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有公司"""
        rows = self.db.execute("SELECT * FROM companies ORDER BY name")
        return [self._row_to_dict(row) for row in rows]
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取公司"""
        row = self.db.execute_one("SELECT * FROM companies WHERE name = ?", (name,))
        return self._row_to_dict(row) if row else None
    
    def get_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """根据 ticker 获取公司"""
        row = self.db.execute_one("SELECT * FROM companies WHERE ticker = ?", (ticker,))
        return self._row_to_dict(row) if row else None
    
    def get_by_sector(self, sector_name: str) -> List[Dict[str, Any]]:
        """根据行业获取公司"""
        rows = self.db.execute(
            "SELECT * FROM companies WHERE sectors LIKE ? ORDER BY name",
            (f"%{sector_name}%",)
        )
        return [self._row_to_dict(row) for row in rows]
    
    def create(self, company: Dict[str, Any]) -> int:
        """创建公司"""
        sql = """
        INSERT INTO companies (name, ticker, exchange, position, sectors, themes, 
                              news_queries, aliases, competes_with)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            company["name"],
            company.get("ticker", ""),
            company.get("exchange", ""),
            company.get("position", ""),
            json.dumps(company.get("sectors", []), ensure_ascii=False),
            json.dumps(company.get("themes", []), ensure_ascii=False),
            json.dumps(company.get("news_queries", []), ensure_ascii=False),
            json.dumps(company.get("aliases", []), ensure_ascii=False),
            json.dumps(company.get("competes_with", []), ensure_ascii=False),
        )
        return self.db.execute_insert(sql, params)
    
    def update(self, name: str, company: Dict[str, Any]) -> int:
        """更新公司"""
        sql = """
        UPDATE companies 
        SET ticker = ?, exchange = ?, position = ?, sectors = ?, themes = ?,
            news_queries = ?, aliases = ?, competes_with = ?, updated_at = ?
        WHERE name = ?
        """
        params = (
            company.get("ticker", ""),
            company.get("exchange", ""),
            company.get("position", ""),
            json.dumps(company.get("sectors", []), ensure_ascii=False),
            json.dumps(company.get("themes", []), ensure_ascii=False),
            json.dumps(company.get("news_queries", []), ensure_ascii=False),
            json.dumps(company.get("aliases", []), ensure_ascii=False),
            json.dumps(company.get("competes_with", []), ensure_ascii=False),
            datetime.now().isoformat(),
            name,
        )
        return self.db.execute_update(sql, params)
    
    def delete(self, name: str) -> int:
        """删除公司"""
        return self.db.execute_update("DELETE FROM companies WHERE name = ?", (name,))
    
    def count(self) -> int:
        """获取公司数量"""
        result = self.db.execute_one("SELECT COUNT(*) as count FROM companies")
        return result["count"] if result else 0
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        if not row:
            return {}
        
        return {
            "id": row["id"],
            "name": row["name"],
            "ticker": row["ticker"],
            "exchange": row["exchange"],
            "position": row["position"],
            "sectors": json.loads(row["sectors"]) if row["sectors"] else [],
            "themes": json.loads(row["themes"]) if row["themes"] else [],
            "news_queries": json.loads(row["news_queries"]) if row["news_queries"] else [],
            "aliases": json.loads(row["aliases"]) if row["aliases"] else [],
            "competes_with": json.loads(row["competes_with"]) if row["competes_with"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


class SectorRepository:
    """行业数据访问层"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有行业"""
        rows = self.db.execute("SELECT * FROM sectors ORDER BY name")
        return [self._row_to_dict(row) for row in rows]
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取行业"""
        row = self.db.execute_one("SELECT * FROM sectors WHERE name = ?", (name,))
        return self._row_to_dict(row) if row else None
    
    def get_by_type(self, sector_type: str) -> List[Dict[str, Any]]:
        """根据类型获取行业"""
        rows = self.db.execute("SELECT * FROM sectors WHERE type = ? ORDER BY name", (sector_type,))
        return [self._row_to_dict(row) for row in rows]
    
    def create(self, sector: Dict[str, Any]) -> int:
        """创建行业"""
        sql = """
        INSERT INTO sectors (name, type, description, tier, keywords, 
                            parent_theme, parent_sector, questions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            sector["name"],
            sector.get("type", "sector"),
            sector.get("description", ""),
            sector.get("tier"),
            json.dumps(sector.get("keywords", []), ensure_ascii=False),
            json.dumps(sector.get("parent_theme", []), ensure_ascii=False),
            json.dumps(sector.get("parent_sector", []), ensure_ascii=False),
            json.dumps(sector.get("questions", []), ensure_ascii=False),
        )
        return self.db.execute_insert(sql, params)
    
    def update(self, name: str, sector: Dict[str, Any]) -> int:
        """更新行业"""
        sql = """
        UPDATE sectors 
        SET type = ?, description = ?, tier = ?, keywords = ?,
            parent_theme = ?, parent_sector = ?, questions = ?, updated_at = ?
        WHERE name = ?
        """
        params = (
            sector.get("type", "sector"),
            sector.get("description", ""),
            sector.get("tier"),
            json.dumps(sector.get("keywords", []), ensure_ascii=False),
            json.dumps(sector.get("parent_theme", []), ensure_ascii=False),
            json.dumps(sector.get("parent_sector", []), ensure_ascii=False),
            json.dumps(sector.get("questions", []), ensure_ascii=False),
            datetime.now().isoformat(),
            name,
        )
        return self.db.execute_update(sql, params)
    
    def delete(self, name: str) -> int:
        """删除行业"""
        return self.db.execute_update("DELETE FROM sectors WHERE name = ?", (name,))
    
    def count(self) -> int:
        """获取行业数量"""
        result = self.db.execute_one("SELECT COUNT(*) as count FROM sectors")
        return result["count"] if result else 0
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        if not row:
            return {}
        
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "description": row["description"],
            "tier": row["tier"],
            "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
            "parent_theme": json.loads(row["parent_theme"]) if row["parent_theme"] else [],
            "parent_sector": json.loads(row["parent_sector"]) if row["parent_sector"] else [],
            "questions": json.loads(row["questions"]) if row["questions"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


class WikiRepository:
    """Wiki 条目数据访问层"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有 Wiki 条目"""
        rows = self.db.execute("SELECT * FROM wiki_entries ORDER BY entity_name, topic_name")
        return [self._row_to_dict(row) for row in rows]
    
    def get_by_entity(self, entity_name: str, entity_type: str) -> List[Dict[str, Any]]:
        """根据实体获取 Wiki 条目"""
        rows = self.db.execute(
            "SELECT * FROM wiki_entries WHERE entity_name = ? AND entity_type = ? ORDER BY topic_name",
            (entity_name, entity_type)
        )
        return [self._row_to_dict(row) for row in rows]
    
    def get_by_topic(self, entity_name: str, entity_type: str, topic_name: str) -> Optional[Dict[str, Any]]:
        """根据主题获取 Wiki 条目"""
        row = self.db.execute_one(
            "SELECT * FROM wiki_entries WHERE entity_name = ? AND entity_type = ? AND topic_name = ?",
            (entity_name, entity_type, topic_name)
        )
        return self._row_to_dict(row) if row else None
    
    def create(self, entry: Dict[str, Any]) -> int:
        """创建 Wiki 条目"""
        sql = """
        INSERT INTO wiki_entries (entity_name, entity_type, topic_name, content, 
                                 last_updated, sources_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            entry["entity_name"],
            entry["entity_type"],
            entry["topic_name"],
            entry.get("content", ""),
            entry.get("last_updated", datetime.now().strftime("%Y-%m-%d")),
            entry.get("sources_count", 0),
        )
        return self.db.execute_insert(sql, params)
    
    def update(self, entity_name: str, entity_type: str, topic_name: str, entry: Dict[str, Any]) -> int:
        """更新 Wiki 条目"""
        sql = """
        UPDATE wiki_entries 
        SET content = ?, last_updated = ?, sources_count = ?, updated_at = ?
        WHERE entity_name = ? AND entity_type = ? AND topic_name = ?
        """
        params = (
            entry.get("content", ""),
            entry.get("last_updated", datetime.now().strftime("%Y-%m-%d")),
            entry.get("sources_count", 0),
            datetime.now().isoformat(),
            entity_name,
            entity_type,
            topic_name,
        )
        return self.db.execute_update(sql, params)
    
    def upsert(self, entry: Dict[str, Any]) -> int:
        """创建或更新 Wiki 条目"""
        existing = self.get_by_topic(
            entry["entity_name"],
            entry["entity_type"],
            entry["topic_name"]
        )
        
        if existing:
            return self.update(
                entry["entity_name"],
                entry["entity_type"],
                entry["topic_name"],
                entry
            )
        else:
            return self.create(entry)
    
    def delete(self, entity_name: str, entity_type: str, topic_name: str) -> int:
        """删除 Wiki 条目"""
        return self.db.execute_update(
            "DELETE FROM wiki_entries WHERE entity_name = ? AND entity_type = ? AND topic_name = ?",
            (entity_name, entity_type, topic_name)
        )
    
    def count(self) -> int:
        """获取 Wiki 条目数量"""
        result = self.db.execute_one("SELECT COUNT(*) as count FROM wiki_entries")
        return result["count"] if result else 0
    
    def get_stale(self, max_age_days: int = 30) -> List[Dict[str, Any]]:
        """获取过时的 Wiki 条目"""
        cutoff = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
        rows = self.db.execute(
            "SELECT * FROM wiki_entries WHERE last_updated < ? ORDER BY last_updated",
            (cutoff,)
        )
        return [self._row_to_dict(row) for row in rows]
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        if not row:
            return {}
        
        return {
            "id": row["id"],
            "entity_name": row["entity_name"],
            "entity_type": row["entity_type"],
            "topic_name": row["topic_name"],
            "content": row["content"],
            "last_updated": row["last_updated"],
            "sources_count": row["sources_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


class IngestedFileRepository:
    """已处理文件数据访问层"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有已处理文件"""
        rows = self.db.execute("SELECT * FROM ingested_files ORDER BY ingested_at DESC")
        return [dict(row) for row in rows]
    
    def get_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """根据哈希获取已处理文件"""
        row = self.db.execute_one("SELECT * FROM ingested_files WHERE file_hash = ?", (file_hash,))
        return dict(row) if row else None
    
    def create(self, file_hash: str, file_path: str) -> int:
        """创建已处理文件记录"""
        sql = "INSERT INTO ingested_files (file_hash, file_path) VALUES (?, ?)"
        return self.db.execute_insert(sql, (file_hash, file_path))
    
    def exists(self, file_hash: str) -> bool:
        """检查文件是否已处理"""
        row = self.db.execute_one("SELECT 1 FROM ingested_files WHERE file_hash = ?", (file_hash,))
        return row is not None
    
    def delete(self, file_hash: str) -> int:
        """删除已处理文件记录"""
        return self.db.execute_update("DELETE FROM ingested_files WHERE file_hash = ?", (file_hash,))
    
    def count(self) -> int:
        """获取已处理文件数量"""
        result = self.db.execute_one("SELECT COUNT(*) as count FROM ingested_files")
        return result["count"] if result else 0