"""
内容提取器
负责从文件中提取内容和元数据
"""
import sys
import re
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ContentExtractor:
    """内容提取器"""
    
    def __init__(self):
        """初始化提取器"""
        # 导入依赖模块
        try:
            from extract import extract_summary, classify_info_type
            self.extract_summary = extract_summary
            self.classify_info_type = classify_info_type
        except ImportError:
            logger.warning("无法导入 extract 模块，使用简化版本")
            self.extract_summary = None
            self.classify_info_type = None
        
        try:
            from pdf_extract import extract_pdf_summary
            self.extract_pdf_summary = extract_pdf_summary
        except ImportError:
            logger.warning("无法导入 pdf_extract 模块，PDF 处理将受限")
            self.extract_pdf_summary = None
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        从文件中提取内容和元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含元数据和内容的字典
        """
        path = Path(file_path)
        filename = path.name
        meta = {"_path": str(file_path), "_filename": filename}
        
        # PDF 文件
        if filename.lower().endswith(".pdf"):
            return self._extract_pdf(file_path, meta)
        
        # Markdown 文件
        return self._extract_markdown(file_path, meta)
    
    def _extract_pdf(self, file_path: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取 PDF 内容
        
        Args:
            file_path: 文件路径
            meta: 元数据字典
            
        Returns:
            更新后的元数据字典
        """
        if self.extract_pdf_summary is None:
            meta["_content"] = ""
            meta["_pdf_error"] = "PDF 提取模块不可用"
            meta["title"] = Path(file_path).name.replace(".pdf", "")
            meta["type"] = "report"
            return meta
        
        try:
            result = self.extract_pdf_summary(file_path)
            
            if result.get("error"):
                meta["_content"] = ""
                meta["_pdf_error"] = result["error"]
            else:
                # 合并所有提取的章节
                sections_text = "\n\n".join(
                    f"[{s['name']}]\n{s['content']}" 
                    for s in result.get("sections", [])
                )
                meta["_content"] = sections_text
                meta["_pdf_type"] = result.get("type", "unknown")
                meta["_pdf_pages"] = result.get("pages_extracted", 0)
            
            meta["title"] = Path(file_path).name.replace(".pdf", "")
            meta["type"] = "report"
            
        except Exception as e:
            logger.error(f"PDF 提取失败 {file_path}: {e}")
            meta["_content"] = ""
            meta["_pdf_error"] = str(e)
            meta["title"] = Path(file_path).name.replace(".pdf", "")
            meta["type"] = "report"
        
        return meta
    
    def _extract_markdown(self, file_path: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取 Markdown 内容
        
        Args:
            file_path: 文件路径
            meta: 元数据字典
            
        Returns:
            更新后的元数据字典
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            content = ""
        
        # 解析 frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                front = content[3:end]
                for line in front.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip().strip('"').strip("'")
        
        meta["_content"] = content
        return meta
    
    def extract_summary_points(self, text: str, max_sentences: int = 3) -> List[str]:
        """
        从文本中提取摘要要点
        
        Args:
            text: 原始文本
            max_sentences: 最大句子数
            
        Returns:
            摘要要点列表
        """
        if self.extract_summary is None:
            # 简化版本：返回前几个句子
            sentences = re.split(r'(?<=[。！？；\n])\s*', text)
            return [s.strip() for s in sentences if s.strip()][:max_sentences]
        
        try:
            result = self.extract_summary(text, max_sentences=max_sentences)
            return result.get("points", [])
        except Exception as e:
            logger.error(f"提取摘要失败: {e}")
            return []
    
    def classify_content_type(self, text: str) -> str:
        """
        分类内容类型
        
        Args:
            text: 文本内容
            
        Returns:
            内容类型
        """
        if self.classify_info_type is None:
            # 简化版本：基于关键词判断
            if any(word in text for word in ["营收", "净利润", "每股收益", "财报"]):
                return "财报"
            elif any(word in text for word in ["发布", "推出", "宣布"]):
                return "产品"
            elif any(word in text for word in ["研报", "分析", "评级"]):
                return "研报"
            else:
                return "新闻"
        
        try:
            return self.classify_info_type(text)
        except Exception as e:
            logger.error(f"分类失败: {e}")
            return "新闻"