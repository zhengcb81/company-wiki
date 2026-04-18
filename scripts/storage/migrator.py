"""
数据迁移工具
从 YAML 迁移到 SQLite
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from .database import Database
from .repositories import CompanyRepository, SectorRepository, WikiRepository, IngestedFileRepository

logger = logging.getLogger(__name__)


class DataMigrator:
    """数据迁移工具"""
    
    def __init__(self, db: Database, wiki_root: Path):
        """
        初始化迁移工具
        
        Args:
            db: 数据库实例
            wiki_root: Wiki 根目录
        """
        self.db = db
        self.wiki_root = wiki_root
        self.company_repo = CompanyRepository(db)
        self.sector_repo = SectorRepository(db)
        self.wiki_repo = WikiRepository(db)
        self.ingested_repo = IngestedFileRepository(db)
    
    def migrate_from_yaml(self, graph_yaml_path: Optional[Path] = None) -> Dict[str, int]:
        """
        从 YAML 迁移到 SQLite
        
        Args:
            graph_yaml_path: graph.yaml 文件路径
            
        Returns:
            迁移统计
        """
        if graph_yaml_path is None:
            graph_yaml_path = self.wiki_root / "graph.yaml"
        
        if not graph_yaml_path.exists():
            raise FileNotFoundError(f"graph.yaml 不存在: {graph_yaml_path}")
        
        logger.info(f"开始从 {graph_yaml_path} 迁移数据")
        
        # 加载 YAML
        with open(graph_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        stats = {
            "companies": 0,
            "sectors": 0,
            "themes": 0,
            "edges": 0,
            "questions": 0,
            "wiki_entries": 0,
            "ingested_files": 0,
        }
        
        # 迁移公司
        for name, company_data in data.get("companies", {}).items():
            company = {"name": name, **company_data}
            self.company_repo.create(company)
            stats["companies"] += 1
        
        # 迁移行业和主题
        for name, node_data in data.get("nodes", {}).items():
            node_type = node_data.get("type", "sector")
            
            if node_type in ("sector", "subsector"):
                sector = {"name": name, **node_data}
                self.sector_repo.create(sector)
                stats["sectors"] += 1
            elif node_type == "theme":
                # 主题暂时存储在 sectors 表中
                sector = {
                    "name": name,
                    "type": "theme",
                    "description": node_data.get("description", ""),
                    "keywords": node_data.get("keywords", []),
                }
                self.sector_repo.create(sector)
                stats["themes"] += 1
        
        # 迁移边
        for edge in data.get("edges", []):
            sql = """
            INSERT OR IGNORE INTO edges (from_entity, to_entity, edge_type, label)
            VALUES (?, ?, ?, ?)
            """
            self.db.execute_insert(sql, (
                edge["from"],
                edge["to"],
                edge["type"],
                edge.get("label", ""),
            ))
            stats["edges"] += 1
        
        # 迁移问题
        for entity_name, questions in data.get("questions", {}).items():
            for question in questions:
                sql = "INSERT OR IGNORE INTO questions (entity_name, question) VALUES (?, ?)"
                self.db.execute_insert(sql, (entity_name, question))
                stats["questions"] += 1
        
        # 迁移已处理文件
        ingested_dir = self.wiki_root / ".ingested"
        if ingested_dir.exists():
            for hash_file in ingested_dir.glob("*.hash"):
                file_hash = hash_file.read_text().strip()
                self.ingested_repo.create(file_hash, str(hash_file))
                stats["ingested_files"] += 1
        
        # 迁移 Wiki 条目
        stats["wiki_entries"] = self._migrate_wiki_entries()
        
        logger.info(f"迁移完成: {stats}")
        return stats
    
    def _migrate_wiki_entries(self) -> int:
        """迁移 Wiki 条目"""
        count = 0
        
        # 扫描公司 Wiki
        companies_dir = self.wiki_root / "companies"
        if companies_dir.exists():
            for company_dir in companies_dir.iterdir():
                if company_dir.is_dir():
                    wiki_dir = company_dir / "wiki"
                    if wiki_dir.exists():
                        for wiki_file in wiki_dir.glob("*.md"):
                            self._migrate_wiki_file(wiki_file, company_dir.name, "company")
                            count += 1
        
        # 扫描行业 Wiki
        sectors_dir = self.wiki_root / "sectors"
        if sectors_dir.exists():
            for sector_dir in sectors_dir.iterdir():
                if sector_dir.is_dir():
                    wiki_dir = sector_dir / "wiki"
                    if wiki_dir.exists():
                        for wiki_file in wiki_dir.glob("*.md"):
                            self._migrate_wiki_file(wiki_file, sector_dir.name, "sector")
                            count += 1
        
        return count
    
    def _migrate_wiki_file(self, wiki_file: Path, entity_name: str, entity_type: str) -> None:
        """迁移单个 Wiki 文件"""
        try:
            content = wiki_file.read_text(encoding="utf-8")
            
            # 解析 frontmatter
            last_updated = None
            sources_count = 0
            
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    front = content[3:end]
                    for line in front.strip().split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            
                            if key == "last_updated":
                                last_updated = val
                            elif key == "sources_count":
                                try:
                                    sources_count = int(val)
                                except ValueError:
                                    pass
            
            # 创建 Wiki 条目
            entry = {
                "entity_name": entity_name,
                "entity_type": entity_type,
                "topic_name": wiki_file.stem,
                "content": content,
                "last_updated": last_updated,
                "sources_count": sources_count,
            }
            
            self.wiki_repo.upsert(entry)
            
        except Exception as e:
            logger.error(f"迁移 Wiki 文件失败 {wiki_file}: {e}")
    
    def export_to_yaml(self, output_path: Optional[Path] = None) -> Path:
        """
        导出到 YAML
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self.wiki_root / "graph_export.yaml"
        
        data = {
            "nodes": {},
            "companies": {},
            "edges": [],
            "questions": {},
            "settings": {},
        }
        
        # 导出公司
        for company in self.company_repo.get_all():
            data["companies"][company["name"]] = {
                "ticker": company["ticker"],
                "exchange": company["exchange"],
                "position": company["position"],
                "sectors": company["sectors"],
                "themes": company["themes"],
                "news_queries": company["news_queries"],
                "aliases": company["aliases"],
            }
            if company["competes_with"]:
                data["companies"][company["name"]]["competes_with"] = company["competes_with"]
        
        # 导出行业和主题
        for sector in self.sector_repo.get_all():
            if sector["type"] == "theme":
                data["nodes"][sector["name"]] = {
                    "type": "theme",
                    "description": sector["description"],
                    "keywords": sector["keywords"],
                }
            else:
                node = {
                    "type": sector["type"],
                    "description": sector["description"],
                    "keywords": sector["keywords"],
                }
                if sector["tier"] is not None:
                    node["tier"] = sector["tier"]
                if sector["parent_theme"]:
                    node["parent_theme"] = sector["parent_theme"]
                if sector["parent_sector"]:
                    node["parent_sector"] = sector["parent_sector"]
                
                data["nodes"][sector["name"]] = node
        
        # 导出边
        rows = self.db.execute("SELECT * FROM edges ORDER BY from_entity, to_entity")
        for row in rows:
            edge = {
                "from": row["from_entity"],
                "to": row["to_entity"],
                "type": row["edge_type"],
            }
            if row["label"]:
                edge["label"] = row["label"]
            data["edges"].append(edge)
        
        # 导出问题
        rows = self.db.execute("SELECT * FROM questions ORDER BY entity_name, question")
        for row in rows:
            entity_name = row["entity_name"]
            if entity_name not in data["questions"]:
                data["questions"][entity_name] = []
            data["questions"][entity_name].append(row["question"])
        
        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)
        
        logger.info(f"导出完成: {output_path}")
        return output_path
    
    def validate_migration(self) -> Dict[str, Any]:
        """
        验证迁移结果
        
        Returns:
            验证结果
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": self.db.get_stats(),
        }
        
        # 检查公司数量
        company_count = self.company_repo.count()
        if company_count == 0:
            results["warnings"].append("没有公司数据")
        
        # 检查行业数量
        sector_count = self.sector_repo.count()
        if sector_count == 0:
            results["warnings"].append("没有行业数据")
        
        # 检查边数量
        edge_count = self.db.execute_one("SELECT COUNT(*) as count FROM edges")["count"]
        if edge_count == 0:
            results["warnings"].append("没有边数据")
        
        # 检查 Wiki 条目
        wiki_count = self.wiki_repo.count()
        if wiki_count == 0:
            results["warnings"].append("没有 Wiki 条目")
        
        # 检查数据完整性
        # 1. 检查公司的行业是否存在
        for company in self.company_repo.get_all():
            for sector_name in company["sectors"]:
                sector = self.sector_repo.get_by_name(sector_name)
                if not sector:
                    results["errors"].append(f"公司 {company['name']} 引用的行业 {sector_name} 不存在")
                    results["valid"] = False
        
        # 2. 检查边的实体是否存在
        edges = self.db.execute("SELECT DISTINCT from_entity, to_entity FROM edges")
        for edge in edges:
            from_entity = edge["from_entity"]
            to_entity = edge["to_entity"]
            
            # 检查 from_entity
            company = self.company_repo.get_by_name(from_entity)
            sector = self.sector_repo.get_by_name(from_entity)
            if not company and not sector:
                results["errors"].append(f"边引用的实体 {from_entity} 不存在")
                results["valid"] = False
            
            # 检查 to_entity
            company = self.company_repo.get_by_name(to_entity)
            sector = self.sector_repo.get_by_name(to_entity)
            if not company and not sector:
                results["errors"].append(f"边引用的实体 {to_entity} 不存在")
                results["valid"] = False
        
        return results