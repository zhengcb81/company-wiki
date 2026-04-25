"""
文件扫描器
负责扫描待处理的文件
"""
import sys
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Set

sys.path.insert(0, str(Path(__file__).parent.parent))
from models import GraphQueries

logger = logging.getLogger(__name__)


class FileScanner:
    """文件扫描器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化扫描器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
        self.ingested_dir = wiki_root / ".ingested"
    
    def scan(self, graph: GraphQueries, company_name: str = None) -> List[Tuple[str, str, str]]:
        """
        扫描所有待 ingest 文件
        
        Args:
            graph: 图查询接口
            company_name: 只扫描指定公司（可选）
            
        Returns:
            [(file_path, entity_name, entity_type), ...]
        """
        ingested = self.get_ingested_set()
        pending = []
        
        # 扫描公司目录
        companies = graph.get_all_companies()
        if company_name:
            companies = [c for c in companies if c.name == company_name]
        
        for company in companies:
            company_dir = self.wiki_root / "companies" / company.name
            if not company_dir.exists():
                continue
            
            for f in sorted(company_dir.rglob("*")):
                if f.is_file() and not self.is_ingested(f, ingested):
                    # 跳过 wiki 目录
                    if "/wiki/" in str(f) or "\\wiki\\" in str(f):
                        continue
                    pending.append((str(f), company.name, "company"))
        
        # 扫描行业目录
        for sector in graph.get_all_sectors():
            sector_dir = self.wiki_root / "sectors" / sector.name
            if not sector_dir.exists():
                continue
            
            for f in sorted(sector_dir.rglob("*")):
                if f.is_file() and not self.is_ingested(f, ingested):
                    # 跳过 wiki 目录
                    if "/wiki/" in str(f) or "\\wiki\\" in str(f):
                        continue
                    pending.append((str(f), sector.name, "sector"))
        
        logger.info(f"扫描到 {len(pending)} 个待处理文件")
        return pending
    
    def get_ingested_set(self) -> Set[str]:
        """
        加载所有已 ingest 文件的集合
        
        Returns:
            文件哈希集合
        """
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        ingested = set()
        
        for f in self.ingested_dir.glob("*.hash"):
            ingested.add(f.read_text().strip())
        
        return ingested
    
    def mark_ingested(self, file_path: str) -> None:
        """
        标记文件为已 ingest
        
        Args:
            file_path: 文件路径
        """
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        
        content = Path(file_path).read_bytes()
        file_hash = hashlib.md5(content).hexdigest()
        marker = self.ingested_dir / f"{file_hash}.hash"
        marker.write_text(file_hash)
    
    def is_ingested(self, file_path: Path, ingested_set: Set[str]) -> bool:
        """
        检查文件是否已被 ingest
        
        Args:
            file_path: 文件路径
            ingested_set: 已 ingest 文件哈希集合
            
        Returns:
            True 如果已 ingest
        """
        content = file_path.read_bytes()
        file_hash = hashlib.md5(content).hexdigest()
        return file_hash in ingested_set
    
    def get_pending_count(self, graph: GraphQueries, company_name: str = None) -> int:
        """
        获取待处理文件数量
        
        Args:
            graph: 图查询接口
            company_name: 只统计指定公司（可选）
            
        Returns:
            待处理文件数量
        """
        return len(self.scan(graph, company_name))