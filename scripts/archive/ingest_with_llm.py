#!/usr/bin/env python3
"""
ingest_with_llm.py — LLM 增强的 Ingest 流程 (备用入口，函数式实现)
使用 LLM 深度理解内容，提取关键信息，整合到 wiki

主入口: ingest.py (规则驱动)
备选:   llm_ingest.py (类式 LLM 入口)

用法：
    python3 scripts/ingest_with_llm.py                       # 处理所有待 ingest 文件
    python3 scripts/ingest_with_llm.py --company 中微公司      # 只处理指定公司
    python3 scripts/ingest_with_llm.py --dry-run              # 只检查不执行
    python3 scripts/ingest_with_llm.py --file path/to/file.md # 处理指定文件
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from config import Config
from logger import get_logger
from utils import load_yaml, save_yaml, extract_frontmatter, log_message
from graph import Graph

logger = get_logger(__name__)


@dataclass
class LLMExtractedInfo:
    """LLM 提取的信息"""
    key_points: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    topics_affected: List[str] = field(default_factory=list)
    sentiment: str = "neutral"  # positive, negative, neutral
    importance: float = 0.5  # 0-1
    contradictions: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_points": self.key_points,
            "entities_mentioned": self.entities_mentioned,
            "topics_affected": self.topics_affected,
            "sentiment": self.sentiment,
            "importance": self.importance,
            "contradictions": self.contradictions,
            "suggested_questions": self.suggested_questions,
        }


@dataclass
class WikiUpdate:
    """Wiki 更新"""
    entity_name: str
    entity_type: str
    topic_name: str
    content: str
    llm_extracted: LLMExtractedInfo
    confidence: float = 0.8


class LLMIngester:
    """LLM 增强的 Ingest"""
    
    def __init__(self, config: Config):
        """
        初始化
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.graph = Graph(str(config.paths.wiki_root / "graph.yaml"))
        self.llm_client = self._init_llm_client()
    
    def _init_llm_client(self):
        """初始化 LLM 客户端 (使用统一 llm_client)"""
        try:
            from llm_client import get_llm_client
            return get_llm_client()
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")
            return None
    
    def ingest_file(self, file_path: Path, dry_run: bool = False) -> List[WikiUpdate]:
        """
        使用 LLM 处理文件
        
        Args:
            file_path: 文件路径
            dry_run: 只检查不执行
            
        Returns:
            Wiki 更新列表
        """
        logger.info(f"LLM ingest: {file_path.name}")
        
        # 1. 读取文件内容
        content = file_path.read_text(encoding="utf-8", errors="replace")
        meta = self._extract_metadata(content)
        
        # 2. 获取相关实体
        entities = self._find_relevant_entities(content, meta)
        
        if not entities:
            logger.info(f"  无相关实体，跳过")
            return []
        
        # 3. 使用 LLM 提取信息
        llm_extracted = self._extract_with_llm(content, entities)
        
        # 4. 检查矛盾
        contradictions = self._check_contradictions(llm_extracted, entities)
        llm_extracted.contradictions = contradictions
        
        # 5. 生成 wiki 更新
        updates = self._generate_wiki_updates(
            meta, entities, llm_extracted, file_path
        )
        
        # 6. 应用更新
        if not dry_run:
            applied = self._apply_updates(updates)
            logger.info(f"  应用 {applied} 个更新")
        
        return updates
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """提取元数据"""
        meta = {}
        
        # 提取 frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                front = content[3:end]
                for line in front.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip().strip('"').strip("'")
        
        return meta
    
    def _find_relevant_entities(self, content: str, meta: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """查找相关实体"""
        # 使用 graph 查找相关实体
        company_hint = meta.get("company")
        entities = self.graph.find_related_entities(content, company_hint=company_hint)
        
        return entities
    
    def _extract_with_llm(self, content: str, entities: List[Tuple[str, str, str]]) -> LLMExtractedInfo:
        """
        使用 LLM 提取信息
        
        Args:
            content: 内容
            entities: 相关实体
            
        Returns:
            LLM 提取的信息
        """
        # 如果 LLM 客户端不可用，使用规则提取
        if not self.llm_client:
            return self._extract_with_rules(content, entities)
        
        # 准备提示词
        entity_names = [e[0] for e in entities]
        prompt = self._build_extraction_prompt(content, entity_names)
        
        try:
            # 调用 LLM (统一客户端)
            response = self.llm_client.chat_with_retry(
                prompt,
                "你是一个专业的上市公司研究分析助手。请准确提取关键信息。"
            )
            if response.success:
                return self._parse_llm_response(response.content)
            else:
                raise RuntimeError(f"LLM 调用失败: {response.error}")
        
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            # 回退到规则提取
            return self._extract_with_rules(content, entities)
    
    def _build_extraction_prompt(self, content: str, entity_names: List[str]) -> str:
        """构建提取提示词"""
        # 截取内容（避免 token 过多）
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""
请分析以下新闻/文档，提取关键信息。

相关实体: {', '.join(entity_names)}

内容:
{content_preview}

请以 JSON 格式返回:
{{
    "key_points": ["要点1", "要点2", "要点3"],
    "entities_mentioned": ["提及的实体"],
    "topics_affected": ["影响的主题"],
    "sentiment": "positive/negative/neutral",
    "importance": 0.0-1.0,
    "suggested_questions": ["可能回答的问题"]
}}

只返回 JSON，不要其他内容。
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> LLMExtractedInfo:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return LLMExtractedInfo(
                    key_points=data.get("key_points", []),
                    entities_mentioned=data.get("entities_mentioned", []),
                    topics_affected=data.get("topics_affected", []),
                    sentiment=data.get("sentiment", "neutral"),
                    importance=float(data.get("importance", 0.5)),
                    suggested_questions=data.get("suggested_questions", []),
                )
        
        except Exception as e:
            logger.warning(f"解析 LLM 响应失败: {e}")
        
        # 回退
        return LLMExtractedInfo()
    
    def _extract_with_rules(self, content: str, entities: List[Tuple[str, str, str]]) -> LLMExtractedInfo:
        """使用规则提取（回退方案）"""
        # 提取关键句子
        sentences = re.split(r'(?<=[。！？；\n])\s*', content)
        
        # 评分
        scored_sentences = []
        for sentence in sentences:
            if len(sentence) < 15:
                continue
            
            score = 0
            
            # 包含数字
            if re.search(r'\d+\.?\d*\s*(亿|万|%|元)', sentence):
                score += 3
            
            # 包含动作词
            action_words = ['发布', '推出', '宣布', '获得', '突破', '增长']
            for word in action_words:
                if word in sentence:
                    score += 2
                    break
            
            # 包含实体
            for entity_name, _, _ in entities:
                if entity_name in sentence:
                    score += 1
            
            if score > 0:
                scored_sentences.append((score, sentence))
        
        # 取 top 3
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        key_points = [s[1] for s in scored_sentences[:3]]
        
        # 判断情感
        positive_words = ['增长', '突破', '创新', '领先', '成功']
        negative_words = ['下降', '亏损', '延迟', '失败', '风险']
        
        content_lower = content.lower()
        positive_count = sum(1 for w in positive_words if w in content_lower)
        negative_count = sum(1 for w in negative_words if w in content_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return LLMExtractedInfo(
            key_points=key_points,
            entities_mentioned=[e[0] for e in entities],
            topics_affected=[e[2] for e in entities],
            sentiment=sentiment,
            importance=0.5,
        )
    
    def _check_contradictions(self, extracted: LLMExtractedInfo, entities: List[Tuple[str, str, str]]) -> List[str]:
        """检查矛盾"""
        contradictions = []
        
        # 这里可以实现更复杂的矛盾检测逻辑
        # 目前返回空列表
        
        return contradictions
    
    def _generate_wiki_updates(
        self,
        meta: Dict[str, Any],
        entities: List[Tuple[str, str, str]],
        llm_extracted: LLMExtractedInfo,
        file_path: Path,
    ) -> List[WikiUpdate]:
        """生成 wiki 更新"""
        updates = []
        
        title = meta.get("title", file_path.stem)
        published = meta.get("published_date", datetime.now().strftime("%Y-%m-%d"))
        
        # 生成时间线条目
        entry = self._format_timeline_entry(
            title=title,
            published=published,
            key_points=llm_extracted.key_points,
            sentiment=llm_extracted.sentiment,
            file_path=file_path,
        )
        
        # 为每个相关实体生成更新
        for entity_name, entity_type, topic_name in entities:
            update = WikiUpdate(
                entity_name=entity_name,
                entity_type=entity_type,
                topic_name=topic_name,
                content=entry,
                llm_extracted=llm_extracted,
                confidence=0.8,
            )
            updates.append(update)
        
        return updates
    
    def _format_timeline_entry(
        self,
        title: str,
        published: str,
        key_points: List[str],
        sentiment: str,
        file_path: Path,
    ) -> str:
        """格式化时间线条目"""
        # 情感标记
        sentiment_mark = ""
        if sentiment == "positive":
            sentiment_mark = " 📈"
        elif sentiment == "negative":
            sentiment_mark = " 📉"
        
        # 要点
        points = "\n".join(f"- {p}" for p in key_points[:3])
        
        entry = f"""
### {published} | LLM提取 | {title}{sentiment_mark}
{points}

- [来源]({file_path.relative_to(self.config.paths.wiki_root)})
"""
        return entry
    
    def _apply_updates(self, updates: List[WikiUpdate]) -> int:
        """应用更新"""
        applied = 0
        
        for update in updates:
            try:
                # 获取 wiki 文件路径
                wiki_path = self._get_wiki_path(
                    update.entity_name,
                    update.entity_type,
                    update.topic_name,
                )
                
                if not wiki_path:
                    continue
                
                # 如果文件不存在，创建模板
                if not wiki_path.exists():
                    self._create_wiki_template(wiki_path, update)
                
                # 添加时间线条目
                success = self._add_timeline_entry(wiki_path, update.content)
                
                if success:
                    applied += 1
            
            except Exception as e:
                logger.error(f"应用更新失败: {e}")
        
        return applied
    
    def _get_wiki_path(self, entity_name: str, entity_type: str, topic_name: str) -> Optional[Path]:
        """获取 wiki 文件路径"""
        if entity_type == "company":
            return self.config.paths.wiki_root / "companies" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "sector":
            return self.config.paths.wiki_root / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "theme":
            return self.config.paths.wiki_root / "themes" / entity_name / "wiki" / f"{topic_name}.md"
        return None
    
    def _create_wiki_template(self, wiki_path: Path, update: WikiUpdate) -> None:
        """创建 wiki 模板"""
        wiki_path.parent.mkdir(parents=True, exist_ok=True)
        
        template = f"""---
title: "{update.topic_name}"
entity: "{update.entity_name}"
type: {update.entity_type}_topic
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
sources_count: 0
tags: []
---

# {update.entity_name} — {update.topic_name}

## 核心问题
- （待设定）

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""
        wiki_path.write_text(template, encoding="utf-8")
    
    def _add_timeline_entry(self, wiki_path: Path, entry: str) -> bool:
        """添加时间线条目"""
        try:
            content = wiki_path.read_text(encoding="utf-8")
            
            # 找到时间线部分
            timeline_pos = content.find("## 时间线")
            if timeline_pos < 0:
                return False
            
            # 找到插入位置
            after_timeline = content[timeline_pos:]
            first_entry = after_timeline.find("\n### ", 1)
            
            if first_entry < 0:
                # 没有现有条目，在时间线标题后插入
                insert_pos = timeline_pos + len("## 时间线")
                content = content[:insert_pos] + entry + content[insert_pos:]
            else:
                # 插入到第一个条目之前
                abs_first_entry = timeline_pos + first_entry
                content = content[:abs_first_entry] + entry + content[abs_first_entry:]
            
            # 更新 frontmatter
            content = re.sub(
                r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
                f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
                content
            )
            
            # 更新 sources_count
            count_match = re.search(r'sources_count: (\d+)', content)
            if count_match:
                old_count = int(count_match.group(1))
                content = content.replace(
                    f"sources_count: {old_count}",
                    f"sources_count: {old_count + 1}"
                )
            
            # 删除占位文字
            content = content.replace("（暂无条目）\n", "")
            
            wiki_path.write_text(content, encoding="utf-8")
            return True
        
        except Exception as e:
            logger.error(f"添加时间线条目失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="LLM 增强的 Ingest")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--file", type=str, help="处理指定文件")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — LLM Ingest")
    print("=" * 50)
    
    # 加载配置
    config = Config.load()
    
    # 创建 ingester
    ingester = LLMIngester(config)
    
    if args.file:
        # 处理指定文件
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"ERROR: 文件不存在: {file_path}")
            sys.exit(1)
        
        updates = ingester.ingest_file(file_path, dry_run=args.dry_run)
        print(f"\n处理完成: {len(updates)} 个更新")
        return
    
    # 扫描待处理文件
    from ingest.scanner import FileScanner
    scanner = FileScanner(config.paths.wiki_root)
    pending = scanner.scan(ingester.graph._queries, args.company)
    
    if args.limit > 0:
        pending = pending[:args.limit]
    
    if not pending:
        print("\n没有待处理的文件")
        return
    
    print(f"\n待处理文件: {len(pending)}")
    
    # 处理文件
    total_updates = 0
    for i, (file_path, entity_name, entity_type) in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] {Path(file_path).name}")
        
        updates = ingester.ingest_file(Path(file_path), dry_run=args.dry_run)
        total_updates += len(updates)
    
    print(f"\n{'=' * 50}")
    print(f"完成: {total_updates} 个更新")
    print(f"{'=' * 50}")
    
    if not args.dry_run and total_updates > 0:
        log_message(f"LLM ingest: {len(pending)} files, {total_updates} updates")


if __name__ == "__main__":
    main()