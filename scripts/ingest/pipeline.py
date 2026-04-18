"""
Ingest 流水线
可测试、可恢复的 Ingest 流水线
"""
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import Config
from models import GraphData, GraphQueries

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """流水线执行结果"""
    updated: List[Tuple[str, str]] = field(default_factory=list)  # (file_path, topic)
    skipped: List[str] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (file_path, error)
    
    @property
    def total_files(self) -> int:
        """处理的文件总数"""
        return len(self.updated) + len(self.skipped) + len(self.errors)
    
    @property
    def success_count(self) -> int:
        """成功更新的文件数"""
        return len(self.updated)
    
    @property
    def error_count(self) -> int:
        """失败的文件数"""
        return len(self.errors)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_files == 0:
            return 1.0
        return self.success_count / self.total_files
    
    def summary(self) -> str:
        """生成摘要"""
        return (
            f"处理完成: {self.total_files} 个文件\n"
            f"  成功更新: {self.success_count}\n"
            f"  跳过: {len(self.skipped)}\n"
            f"  失败: {self.error_count}\n"
            f"  成功率: {self.success_rate:.1%}"
        )


class IngestPipeline:
    """可测试、可恢复的 Ingest 流水线"""
    
    def __init__(self, config: Config, graph_queries: GraphQueries):
        """
        初始化流水线
        
        Args:
            config: 配置对象
            graph_queries: 图查询接口
        """
        self.config = config
        self.graph = graph_queries
        self.wiki_root = config.wiki_root
        
        # 导入子模块
        from .scanner import FileScanner
        from .extractor import ContentExtractor
        from .updater import WikiUpdater
        
        self.scanner = FileScanner(self.wiki_root)
        self.extractor = ContentExtractor()
        self.updater = WikiUpdater(self.wiki_root)
    
    def run(self, company: Optional[str] = None, dry_run: bool = False, 
            limit: int = 0) -> PipelineResult:
        """
        执行完整流水线
        
        Args:
            company: 只处理指定公司（可选）
            dry_run: 只检查不执行
            limit: 最多处理文件数（0表示不限制）
            
        Returns:
            PipelineResult 对象
        """
        result = PipelineResult()
        
        # 1. 扫描待处理文件
        pending = self.scanner.scan(self.graph, company)
        
        if limit > 0:
            pending = pending[:limit]
        
        if not pending:
            logger.info("没有待处理的文件")
            return result
        
        logger.info(f"开始处理 {len(pending)} 个文件")
        
        # 2. 处理每个文件
        for i, (file_path, entity_name, entity_type) in enumerate(pending):
            logger.debug(f"处理 [{i+1}/{len(pending)}] {file_path}")
            
            try:
                # 提取内容
                meta = self.extractor.extract(file_path)
                
                # 检查是否应该处理
                if not self._should_process(meta):
                    logger.debug(f"跳过低质量内容: {file_path}")
                    result.skipped.append(file_path)
                    if not dry_run:
                        self.scanner.mark_ingested(file_path)
                    continue
                
                # 确定相关性
                topics = self._determine_relevance(meta)
                
                if not topics:
                    logger.debug(f"没有相关主题: {file_path}")
                    result.skipped.append(file_path)
                    if not dry_run:
                        self.scanner.mark_ingested(file_path)
                    continue
                
                # 更新 wiki
                for topic in topics:
                    if not dry_run:
                        success = self.updater.update(topic, meta)
                        if success:
                            result.updated.append((file_path, f"{topic[0]}/{topic[2]}"))
                        else:
                            logger.warning(f"更新失败: {topic}")
                    else:
                        result.updated.append((file_path, f"{topic[0]}/{topic[2]}"))
                
                # 标记为已处理
                if not dry_run:
                    self.scanner.mark_ingested(file_path)
                
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")
                result.errors.append((file_path, str(e)))
                # 继续处理下一个文件
                continue
        
        logger.info(result.summary())
        return result
    
    def _should_process(self, meta: Dict[str, Any]) -> bool:
        """
        判断是否应该处理该文件
        
        Args:
            meta: 文件元数据
            
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
            meta: 文件元数据
            
        Returns:
            True 如果是低质量来源
        """
        file_path = meta.get("_path", "")
        url = meta.get("source_url", "").lower()
        title = meta.get("title", "").lower()
        
        # URL 黑名单模式
        skip_url_patterns = [
            "quote.eastmoney.com",      # 东方财富行情页
            "quote.futunn.com",         # 富途行情页
            "xueqiu.com/S/",            # 雪球个股页
            "stock_quote",              # 通用行情页
            "baidu.com/baike",          # 百度百科
            "baike.baidu.com",
            "hq.sinajs.cn",             # 新浪行情
            "finance.sina.com.cn/realstock",
        ]
        
        # 标题黑名单模式
        skip_title_patterns = [
            "行情走势", "股票股价", "最新价格", "实时走势图",
            "公司简介", "股票行情中心",
            "百科", "百度百科",
            "最新新闻",  # 通常是行情页的标题
            "最新资讯",
            "个股资讯",
        ]
        
        for p in skip_url_patterns:
            if p in url:
                return True
        
        for p in skip_title_patterns:
            if p in title:
                return True
        
        # 内容太短且标题就是公司名（公司主页）
        content = meta.get("_content", "")
        if len(content) < 200:
            company_from_path = Path(file_path).parts
            for part in company_from_path:
                if part == "companies":
                    idx = company_from_path.index(part)
                    if idx + 1 < len(company_from_path):
                        company_name_from_path = company_from_path[idx + 1]
                        title_clean = title.replace(" ", "")
                        if title_clean == company_name_from_path:
                            return True
                    break
        
        return False
    
    def _determine_relevance(self, meta: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        确定文件的相关主题
        
        Args:
            meta: 文件元数据
            
        Returns:
            [(entity_name, entity_type, topic_name), ...]
        """
        title = meta.get("title", "")
        content = meta.get("_content", "")
        company_name = meta.get("company", "")
        
        # 提取正文（去掉 frontmatter）
        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:]
        
        text = f"{title} {body}"
        
        # 使用 Graph API 获取相关实体
        return self.graph.find_related_entities(text, company_hint=company_name or None)