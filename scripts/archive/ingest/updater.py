"""
Wiki 更新器
负责更新 wiki 文件
"""
import sys
import re
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class WikiUpdater:
    """Wiki 更新器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化更新器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
    
    def update(self, topic: Tuple[str, str, str], meta: Dict[str, Any]) -> bool:
        """
        更新 wiki 文件
        
        Args:
            topic: (entity_name, entity_type, topic_name)
            meta: 文件元数据
            
        Returns:
            True 如果更新成功
        """
        entity_name, entity_type, topic_name = topic
        
        # 获取 wiki 文件路径
        wiki_path = self._get_wiki_path(entity_name, entity_type, topic_name)
        
        if wiki_path is None:
            logger.warning(f"无法确定 wiki 路径: {entity_name}/{topic_name}")
            return False
        
        # 如果 wiki 文档不存在，创建模板
        if not wiki_path.exists():
            self._create_wiki_template(wiki_path, entity_name, entity_type, topic_name)
        
        # 添加时间线条目
        return self._add_timeline_entry(wiki_path, meta, topic_name, entity_type)
    
    def _get_wiki_path(self, entity_name: str, entity_type: str, topic_name: str) -> Optional[Path]:
        """
        获取 wiki 文件路径
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型
            topic_name: 主题名称
            
        Returns:
            wiki 文件路径
        """
        if entity_type == "company":
            return self.wiki_root / "companies" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "sector":
            return self.wiki_root / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "theme":
            return self.wiki_root / "themes" / entity_name / "wiki" / f"{topic_name}.md"
        return None
    
    def _create_wiki_template(self, wiki_path: Path, entity_name: str, 
                             entity_type: str, topic_name: str) -> None:
        """
        创建 wiki 模板
        
        Args:
            wiki_path: wiki 文件路径
            entity_name: 实体名称
            entity_type: 实体类型
            topic_name: 主题名称
        """
        # 确保目录存在
        wiki_path.parent.mkdir(parents=True, exist_ok=True)
        
        template = f"""---
title: "{topic_name}"
entity: "{entity_name}"
type: {entity_type}_topic
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
sources_count: 0
tags: []
---

# {entity_name} — {topic_name}

## 核心问题
- （待设定）

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""
        
        wiki_path.write_text(template, encoding="utf-8")
        logger.info(f"创建 wiki 模板: {wiki_path.relative_to(self.wiki_root)}")
    
    def _add_timeline_entry(self, wiki_path: Path, meta: Dict[str, Any], 
                           topic_name: str, entity_type: str) -> bool:
        """
        向 wiki 文档的时间线中添加新条目
        
        Args:
            wiki_path: wiki 文件路径
            meta: 文件元数据
            topic_name: 主题名称
            entity_type: 实体类型
            
        Returns:
            True 如果添加成功
        """
        title = meta.get("title", "未知标题")
        published = meta.get("published_date", datetime.now().strftime("%Y-%m-%d"))
        content = meta.get("_content", "")
        filename = meta.get("_filename", "")
        
        # 从内容中提取摘要
        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:]
        
        # 去掉第一个 # 标题行
        body_lines = body.strip().split("\n")
        clean_body_lines = []
        for line in body_lines:
            if line.startswith("#"):
                continue
            clean_body_lines.append(line)
        body_text = "\n".join(clean_body_lines)
        
        # 提取摘要要点
        from .extractor import ContentExtractor
        extractor = ContentExtractor()
        summary_points = extractor.extract_summary_points(body_text, max_sentences=3)
        
        # 质量过滤：低质量内容只保留标题
        if len(summary_points) == 0 or (len(body_text) < 100 and len(summary_points) == 0):
            summary_points = [title]
        
        summary = "\n".join(f"- {p}" for p in summary_points)
        
        # 来源类型判断
        info_type = extractor.classify_content_type(body_text)
        source_type = "新闻"
        
        if meta.get("type") == "report" or filename.lower().endswith(".pdf"):
            # PDF 文件按内容细分
            pdf_type = meta.get("_pdf_type", "")
            if pdf_type == "investor_relations":
                source_type = "投资者关系"
            elif pdf_type == "research_report":
                source_type = "研报"
            elif "招股" in title:
                source_type = "招股书"
            else:
                source_type = "财报"
        elif info_type == "财报":
            source_type = "财报"
        elif info_type == "产品":
            source_type = "产品"
        elif "研报" in title or "report" in filename.lower():
            source_type = "研报"
        elif "公告" in title:
            source_type = "公告"
        
        # 问题匹配
        question_matches = self._match_questions(body_text, topic_name, entity_type)
        
        # 构建时间线条目
        # 计算相对路径
        file_path = Path(meta["_path"])
        try:
            relative_path = file_path.relative_to(wiki_path.parent)
        except ValueError:
            # 如果不在子目录中，使用相对于 wiki_root 的路径
            relative_path = file_path.relative_to(self.wiki_root)
        
        entry = f"""
### {published} | {source_type} | {title}
{summary}
"""
        
        # 添加问题匹配结果
        if question_matches:
            entry += "\n**回答问题**：\n"
            for match in question_matches:
                if match["confidence"] in ["high", "medium"]:
                    entry += f"- [{match['question']}] {match['answer'][:150]}...\n"
        
        entry += f"\n- [来源]({relative_path})\n"
        
        # 读取现有内容
        if wiki_path.exists():
            wiki_text = wiki_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Wiki 文件不存在: {wiki_path}")
            return False
        
        # 找到 "## 时间线" 的位置
        timeline_pos = wiki_text.find("## 时间线")
        if timeline_pos < 0:
            logger.warning(f"找不到时间线部分: {wiki_path}")
            return False
        
        # 找到时间线之后第一个 "###" 或 "##" 行
        after_timeline = wiki_text[timeline_pos:]
        next_section = after_timeline.find("\n## ", 1)  # 下一个二级标题
        first_entry = after_timeline.find("\n### ", 1)  # 第一个已有条目
        
        if first_entry < 0 and next_section < 0:
            # 时间线是最后一个部分，在末尾追加
            wiki_text = wiki_text.rstrip() + entry
        elif first_entry < 0 or (next_section > 0 and next_section < first_entry):
            # 时间线没有条目，或下一个 section 在第一个条目之前
            # 在时间线标题后插入
            insert_pos = timeline_pos + len("## 时间线")
            wiki_text = wiki_text[:insert_pos] + entry + wiki_text[insert_pos:]
        else:
            # 有已有条目，按日期排序插入
            # 简化处理：插入到第一个条目之前（新日期应该在最前面）
            abs_first_entry = timeline_pos + first_entry
            wiki_text = wiki_text[:abs_first_entry] + entry + wiki_text[abs_first_entry:]
        
        # 更新 frontmatter
        wiki_text = re.sub(
            r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
            f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
            wiki_text
        )
        
        # 更新 sources_count
        count_match = re.search(r'sources_count: (\d+)', wiki_text)
        if count_match:
            old_count = int(count_match.group(1))
            wiki_text = wiki_text.replace(
                f"sources_count: {old_count}",
                f"sources_count: {old_count + 1}"
            )
        
        # 如果有 "暂无条目" 的占位文字，删除
        wiki_text = wiki_text.replace("（暂无条目）\n", "")
        
        # 保存文件
        wiki_path.write_text(wiki_text, encoding="utf-8")
        logger.debug(f"更新 wiki: {wiki_path.relative_to(self.wiki_root)}")
        
        return True
    
    def _match_questions(self, content: str, topic_name: str, entity_type: str) -> List[Dict[str, Any]]:
        """
        匹配内容与问题
        
        Args:
            content: 内容
            topic_name: 主题名称
            entity_type: 实体类型
            
        Returns:
            匹配结果列表
        """
        try:
            # 导入 graph 模块
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from graph import Graph
            
            # 获取问题列表
            graph = Graph()
            questions = []
            
            if entity_type == "sector":
                sector = graph.get_sector(topic_name)
                if sector:
                    questions = sector.get("questions", [])
            elif entity_type == "company":
                # 获取公司相关行业的问题
                company = graph.get_company(topic_name)
                if company:
                    for sector_name in company.get("sectors", []):
                        sector = graph.get_sector(sector_name)
                        if sector:
                            questions.extend(sector.get("questions", []))
            
            if not questions:
                return []
            
            # 匹配每个问题
            matches = []
            for question in questions:
                match = self._match_single_question(question, content)
                if match:
                    matches.append(match)
            
            return matches
            
        except Exception as e:
            logger.error(f"问题匹配失败: {e}")
            return []
    
    def _match_single_question(self, question: str, content: str) -> Optional[Dict[str, Any]]:
        """
        匹配单个问题
        
        Args:
            question: 问题
            content: 内容
            
        Returns:
            匹配结果或 None
        """
        # 提取问题关键词
        keywords = self._extract_question_keywords(question)
        
        # 计算关键词匹配度
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in content.lower():
                matched_keywords.append(keyword)
        
        if not matched_keywords:
            return None
        
        # 计算相关性分数
        relevance_score = len(matched_keywords) / len(keywords) if keywords else 0
        
        # 如果相关性太低，返回 None
        if relevance_score < 0.3:
            return None
        
        # 提取相关句子
        relevant_sentences = self._extract_relevant_sentences(question, content)
        
        if not relevant_sentences:
            return None
        
        # 生成答案摘要
        answer_summary = " ".join(relevant_sentences[:2])
        
        # 确定置信度
        if relevance_score >= 0.7:
            confidence = "high"
        elif relevance_score >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "question": question,
            "relevance_score": relevance_score,
            "answer": answer_summary,
            "confidence": confidence,
        }
    
    def _load_question_keywords(self) -> Dict[str, List[str]]:
        """
        加载问题关键词映射
        
        Returns:
            关键词映射字典
        """
        config_path = self.wiki_root / "config_rules.yaml"
        
        if not config_path.exists():
            return self._get_default_question_keywords()
        
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config.get("question_keywords", self._get_default_question_keywords())
        except Exception as e:
            logger.warning(f"Failed to load question keywords from config: {e}")
            return self._get_default_question_keywords()
    
    def _get_default_question_keywords(self) -> Dict[str, List[str]]:
        """
        获取默认问题关键词映射
        
        Returns:
            默认关键词映射
        """
        return {
            "国产化率": ["国产化", "国产替代", "自主可控", "国产", "本土化"],
            "先进制程": ["先进制程", "制程", "nm", "纳米", "工艺节点"],
            "订单": ["订单", "客户", "签约", "中标", "采购"],
            "扩产": ["扩产", "产能", "产量", "扩建", "投产"],
            "制裁": ["制裁", "出口管制", "限制", "美国", "实体清单"],
            "技术": ["技术", "创新", "研发", "突破", "专利"],
            "竞争": ["竞争", "格局", "对手", "市场份额", "龙头"],
            "趋势": ["趋势", "方向", "发展", "前景", "展望"],
            "财务": ["营收", "利润", "增长", "毛利率", "净利率"],
        }
    
    def _extract_question_keywords(self, question: str) -> List[str]:
        """
        从问题中提取关键词
        
        Args:
            question: 问题
            
        Returns:
            关键词列表
        """
        # 移除问号和常见词汇
        question = question.replace("？", "").replace("?", "")
        
        # 加载关键词映射
        keyword_patterns = self._load_question_keywords()
        
        # 检查问题是否包含特定模式
        keywords = []
        for pattern, pattern_keywords in keyword_patterns.items():
            if pattern in question:
                keywords.extend(pattern_keywords)
        
        # 如果没有匹配的模式，提取所有2字以上的词
        if not keywords:
            words = re.findall(r'[\u4e00-\u9fff]{2,}', question)
            keywords = words if words else [question]
        
        return keywords
    
    def _extract_relevant_sentences(self, question: str, content: str, max_sentences: int = 3) -> List[str]:
        """
        提取与问题相关的句子
        
        Args:
            question: 问题
            content: 内容
            max_sentences: 最大句子数
            
        Returns:
            相关句子列表
        """
        # 提取问题关键词
        keywords = self._extract_question_keywords(question)
        
        # 分句
        sentences = re.split(r'(?<=[。！？；\n])\s*', content)
        
        # 计算每个句子的相关性
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.strip()) < 15:
                continue
            
            score = 0
            for keyword in keywords:
                if keyword.lower() in sentence.lower():
                    score += 1
            
            if score > 0:
                scored_sentences.append((score, sentence.strip()))
        
        # 排序并取 top N
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored_sentences[:max_sentences]]