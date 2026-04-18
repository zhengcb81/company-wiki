"""
异步文件扫描器
支持并发扫描文件
"""
import sys
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Set, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent.parent))
from models import GraphQueries

logger = logging.getLogger(__name__)


class AsyncFileScanner:
    """异步文件扫描器"""
    
    def __init__(self, wiki_root: Path, max_workers: int = 10):
        """
        初始化扫描器
        
        Args:
            wiki_root: Wiki 根目录
            max_workers: 最大线程数
        """
        self.wiki_root = wiki_root
        self.ingested_dir = wiki_root / ".ingested"
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def scan(
        self,
        graph: GraphQueries,
        company_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Tuple[str, str, str]]:
        """
        异步扫描待处理文件
        
        Args:
            graph: 图查询接口
            company_name: 只扫描指定公司（可选）
            progress_callback: 进度回调函数
            
        Returns:
            [(file_path, entity_name, entity_type), ...]
        """
        # 获取已处理文件集合
        ingested = await self._get_ingested_set()
        
        # 获取要扫描的目录
        scan_dirs = self._get_scan_dirs(graph, company_name)
        
        # 并发扫描目录
        pending = []
        completed = 0
        total = len(scan_dirs)
        
        tasks = []
        for scan_dir, entity_name, entity_type in scan_dirs:
            task = asyncio.create_task(
                self._scan_directory(scan_dir, entity_name, entity_type, ingested)
            )
            tasks.append(task)
        
        # 等待所有任务完成
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                pending.extend(result)
            except Exception as e:
                logger.error(f"扫描目录失败: {e}")
            
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        
        logger.info(f"扫描到 {len(pending)} 个待处理文件")
        return pending
    
    def _get_scan_dirs(
        self,
        graph: GraphQueries,
        company_name: Optional[str] = None,
    ) -> List[Tuple[Path, str, str]]:
        """
        获取要扫描的目录
        
        Args:
            graph: 图查询接口
            company_name: 只扫描指定公司（可选）
            
        Returns:
            [(目录路径, 实体名称, 实体类型), ...]
        """
        scan_dirs = []
        
        # 公司目录
        companies = graph.get_all_companies()
        if company_name:
            companies = [c for c in companies if c.name == company_name]
        
        for company in companies:
            company_dir = self.wiki_root / "companies" / company.name
            if company_dir.exists():
                scan_dirs.append((company_dir, company.name, "company"))
        
        # 行业目录
        for sector in graph.get_all_sectors():
            sector_dir = self.wiki_root / "sectors" / sector.name
            if sector_dir.exists():
                scan_dirs.append((sector_dir, sector.name, "sector"))
        
        return scan_dirs
    
    async def _scan_directory(
        self,
        directory: Path,
        entity_name: str,
        entity_type: str,
        ingested_set: Set[str],
    ) -> List[Tuple[str, str, str]]:
        """
        扫描单个目录
        
        Args:
            directory: 目录路径
            entity_name: 实体名称
            entity_type: 实体类型
            ingested_set: 已处理文件哈希集合
            
        Returns:
            [(file_path, entity_name, entity_type), ...]
        """
        pending = []
        
        # 获取目录下所有文件
        files = list(directory.rglob("*"))
        
        # 并发检查文件
        tasks = []
        for file_path in files:
            if file_path.is_file():
                task = asyncio.create_task(
                    self._check_file(file_path, entity_name, entity_type, ingested_set)
                )
                tasks.append(task)
        
        # 等待所有任务完成
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    pending.append(result)
            except Exception as e:
                logger.error(f"检查文件失败: {e}")
        
        return pending
    
    async def _check_file(
        self,
        file_path: Path,
        entity_name: str,
        entity_type: str,
        ingested_set: Set[str],
    ) -> Optional[Tuple[str, str, str]]:
        """
        检查单个文件
        
        Args:
            file_path: 文件路径
            entity_name: 实体名称
            entity_type: 实体类型
            ingested_set: 已处理文件哈希集合
            
        Returns:
            (file_path, entity_name, entity_type) 或 None
        """
        # 跳过 wiki 目录
        if "/wiki/" in str(file_path) or "\\wiki\\" in str(file_path):
            return None
        
        # 检查是否已处理
        is_ingested = await self._is_ingested(file_path, ingested_set)
        if is_ingested:
            return None
        
        return (str(file_path), entity_name, entity_type)
    
    async def _get_ingested_set(self) -> Set[str]:
        """
        异步获取已处理文件集合
        
        Returns:
            文件哈希集合
        """
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        ingested = set()
        
        # 获取所有 .hash 文件
        hash_files = list(self.ingested_dir.glob("*.hash"))
        
        # 并发读取文件
        tasks = []
        for hash_file in hash_files:
            task = asyncio.create_task(self._read_hash_file(hash_file))
            tasks.append(task)
        
        # 等待所有任务完成
        for coro in asyncio.as_completed(tasks):
            try:
                file_hash = await coro
                if file_hash:
                    ingested.add(file_hash)
            except Exception as e:
                logger.error(f"读取哈希文件失败: {e}")
        
        return ingested
    
    async def _read_hash_file(self, hash_file: Path) -> Optional[str]:
        """
        异步读取哈希文件
        
        Args:
            hash_file: 哈希文件路径
            
        Returns:
            文件哈希或 None
        """
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor,
                lambda: hash_file.read_text().strip()
            )
            return content
        except Exception as e:
            logger.error(f"读取哈希文件失败 {hash_file}: {e}")
            return None
    
    async def _is_ingested(self, file_path: Path, ingested_set: Set[str]) -> bool:
        """
        异步检查文件是否已处理
        
        Args:
            file_path: 文件路径
            ingested_set: 已处理文件哈希集合
            
        Returns:
            True 如果已处理
        """
        try:
            # 计算文件哈希
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor,
                lambda: file_path.read_bytes()
            )
            file_hash = hashlib.md5(content).hexdigest()
            return file_hash in ingested_set
        except Exception as e:
            logger.error(f"检查文件失败 {file_path}: {e}")
            return False
    
    async def mark_ingested(self, file_path: str) -> None:
        """
        异步标记文件为已处理
        
        Args:
            file_path: 文件路径
        """
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 计算文件哈希
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor,
                lambda: Path(file_path).read_bytes()
            )
            file_hash = hashlib.md5(content).hexdigest()
            
            # 写入哈希文件
            marker = self.ingested_dir / f"{file_hash}.hash"
            await loop.run_in_executor(
                self._executor,
                lambda: marker.write_text(file_hash)
            )
            
        except Exception as e:
            logger.error(f"标记文件失败 {file_path}: {e}")
    
    def shutdown(self) -> None:
        """关闭扫描器"""
        self._executor.shutdown(wait=True)