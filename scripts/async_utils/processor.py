"""
异步处理器
支持并发处理文件
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import Config
from models import GraphQueries

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """处理结果"""
    file_path: str
    success: bool
    topics: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "success": self.success,
            "topics": self.topics,
            "error": self.error,
            "duration": self.duration,
        }


class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self, config: Config, graph: GraphQueries, max_concurrent: int = 5):
        """
        初始化处理器
        
        Args:
            config: 配置对象
            graph: 图查询接口
            max_concurrent: 最大并发数
        """
        self.config = config
        self.graph = graph
        self.wiki_root = config.wiki_root
        self.max_concurrent = max_concurrent
        
        # 导入依赖模块
        from .scanner import AsyncFileScanner
        from ingest.extractor import ContentExtractor
        from ingest.updater import WikiUpdater
        
        self.scanner = AsyncFileScanner(self.wiki_root)
        self.extractor = ContentExtractor()
        self.updater = WikiUpdater(self.wiki_root)
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cancelled = False
    
    async def process_files(
        self,
        files: List[Tuple[str, str, str]],
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[ProcessResult]:
        """
        异步处理文件
        
        Args:
            files: 文件列表 [(file_path, entity_name, entity_type), ...]
            dry_run: 只检查不执行
            progress_callback: 进度回调函数
            
        Returns:
            处理结果列表
        """
        self._cancelled = False
        results = []
        completed = 0
        total = len(files)
        
        # 创建异步任务
        tasks = []
        for file_path, entity_name, entity_type in files:
            task = asyncio.create_task(
                self._process_single_file(file_path, entity_name, entity_type, dry_run)
            )
            tasks.append(task)
        
        # 等待所有任务完成
        for coro in asyncio.as_completed(tasks):
            if self._cancelled:
                break
            
            try:
                result = await coro
                results.append(result)
            except Exception as e:
                logger.error(f"处理文件异常: {e}")
            
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        
        # 按原始顺序排序
        file_paths = [f[0] for f in files]
        results.sort(key=lambda r: file_paths.index(r.file_path) if r.file_path in file_paths else len(file_paths))
        
        return results
    
    async def _process_single_file(
        self,
        file_path: str,
        entity_name: str,
        entity_type: str,
        dry_run: bool,
    ) -> ProcessResult:
        """
        异步处理单个文件
        
        Args:
            file_path: 文件路径
            entity_name: 实体名称
            entity_type: 实体类型
            dry_run: 只检查不执行
            
        Returns:
            处理结果
        """
        async with self._semaphore:
            if self._cancelled:
                return ProcessResult(file_path, False, error="已取消")
            
            start_time = datetime.now()
            result = ProcessResult(file_path, False)
            
            try:
                # 提取内容
                meta = await self._extract_content(file_path)
                
                # 检查是否应该处理
                if not self._should_process(meta):
                    result.success = True
                    result.error = "跳过低质量内容"
                    return result
                
                # 确定相关性
                topics = self._determine_relevance(meta)
                
                if not topics:
                    result.success = True
                    result.error = "没有相关主题"
                    return result
                
                # 更新 wiki
                if not dry_run:
                    for topic in topics:
                        success = await self._update_wiki(topic, meta)
                        if success:
                            result.topics.append(f"{topic[0]}/{topic[2]}")
                
                # 标记为已处理
                if not dry_run:
                    await self.scanner.mark_ingested(file_path)
                
                result.success = True
                
            except Exception as e:
                result.error = str(e)
                logger.error(f"处理文件失败 {file_path}: {e}")
            
            finally:
                end_time = datetime.now()
                result.duration = (end_time - start_time).total_seconds()
            
            return result
    
    async def _extract_content(self, file_path: str) -> Dict[str, Any]:
        """
        异步提取内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            元数据字典
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.extractor.extract,
            file_path
        )
    
    def _should_process(self, meta: Dict[str, Any]) -> bool:
        """
        判断是否应该处理
        
        Args:
            meta: 元数据
            
        Returns:
            True 如果应该处理
        """
        # 检查低质量来源
        if self._is_low_quality_source(meta):
            return False
        
        # 检查内容长度
        content = meta.get("_content", "")
        if len(content) < 50:
            return False
        
        return True
    
    def _is_low_quality_source(self, meta: Dict[str, Any]) -> bool:
        """
        检查是否是低质量来源
        
        Args:
            meta: 元数据
            
        Returns:
            True 如果是低质量来源
        """
        file_path = meta.get("_path", "")
        url = meta.get("source_url", "").lower()
        title = meta.get("title", "").lower()
        
        # URL 黑名单模式
        skip_url_patterns = [
            "quote.eastmoney.com",
            "quote.futunn.com",
            "xueqiu.com/S/",
            "stock_quote",
            "baidu.com/baike",
            "baike.baidu.com",
            "hq.sinajs.cn",
            "finance.sina.com.cn/realstock",
        ]
        
        # 标题黑名单模式
        skip_title_patterns = [
            "行情走势", "股票股价", "最新价格", "实时走势图",
            "公司简介", "股票行情中心",
            "百科", "百度百科",
            "最新新闻",
            "最新资讯",
            "个股资讯",
        ]
        
        for p in skip_url_patterns:
            if p in url:
                return True
        
        for p in skip_title_patterns:
            if p in title:
                return True
        
        return False
    
    def _determine_relevance(self, meta: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        确定相关性
        
        Args:
            meta: 元数据
            
        Returns:
            [(entity_name, entity_type, topic_name), ...]
        """
        title = meta.get("title", "")
        content = meta.get("_content", "")
        company_name = meta.get("company", "")
        
        # 提取正文
        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:]
        
        text = f"{title} {body}"
        
        # 使用 Graph API 获取相关实体
        return self.graph.find_related_entities(text, company_hint=company_name or None)
    
    async def _update_wiki(self, topic: Tuple[str, str, str], meta: Dict[str, Any]) -> bool:
        """
        异步更新 wiki
        
        Args:
            topic: (entity_name, entity_type, topic_name)
            meta: 元数据
            
        Returns:
            True 如果更新成功
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.updater.update,
            topic,
            meta
        )
    
    def cancel(self) -> None:
        """取消所有任务"""
        self._cancelled = True
        logger.info("取消所有任务")
    
    def shutdown(self) -> None:
        """关闭处理器"""
        self.scanner.shutdown()