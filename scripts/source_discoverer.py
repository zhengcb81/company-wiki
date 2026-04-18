#!/usr/bin/env python3
"""
source_discoverer.py — 源发现模块
根据知识缺口建议新的数据来源

用法：
    python3 scripts/source_discoverer.py                      # 分析知识缺口
    python3 scripts/source_discoverer.py --suggest             # 生成来源建议
    python3 scripts/source_discoverer.py --search "关键词"      # 搜索相关来源
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class KnowledgeGap:
    """知识缺口"""
    entity_name: str
    entity_type: str
    topic_name: str
    gap_type: str  # missing_page, empty_timeline, outdated, unanswered_question
    description: str
    priority: str  # high, medium, low
    suggestions: List[str] = field(default_factory=list)


@dataclass
class SourceSuggestion:
    """来源建议"""
    title: str
    description: str
    search_queries: List[str]
    related_entities: List[str]
    priority: str
    reason: str


class SourceDiscoverer:
    """源发现器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化发现器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
        self.graph = Graph(str(wiki_root / "graph.yaml"))
    
    def analyze_gaps(self) -> List[KnowledgeGap]:
        """
        分析知识缺口
        
        Returns:
            知识缺口列表
        """
        gaps = []
        
        # 1. 检查缺失的页面
        gaps.extend(self._check_missing_pages())
        
        # 2. 检查空时间线
        gaps.extend(self._check_empty_timelines())
        
        # 3. 检查过时页面
        gaps.extend(self._check_outdated_pages())
        
        # 4. 检查未回答的问题
        gaps.extend(self._check_unanswered_questions())
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.priority, 3))
        
        return gaps
    
    def _check_missing_pages(self) -> List[KnowledgeGap]:
        """
        检查缺失的页面
        
        Returns:
            知识缺口列表
        """
        gaps = []
        
        # 检查公司页面
        companies = self.graph.get_all_companies()
        for company in companies:
            company_name = company["name"]
            wiki_dir = self.wiki_root / "companies" / company_name / "wiki"
            
            if not wiki_dir.exists():
                gaps.append(KnowledgeGap(
                    entity_name=company_name,
                    entity_type="company",
                    topic_name="",
                    gap_type="missing_page",
                    description=f"公司 {company_name} 没有 wiki 目录",
                    priority="high",
                    suggestions=[f"创建 companies/{company_name}/wiki/ 目录"],
                ))
                continue
            
            # 检查是否有基本页面
            wiki_files = list(wiki_dir.glob("*.md"))
            if not wiki_files:
                gaps.append(KnowledgeGap(
                    entity_name=company_name,
                    entity_type="company",
                    topic_name="",
                    gap_type="missing_page",
                    description=f"公司 {company_name} 没有 wiki 页面",
                    priority="high",
                    suggestions=[f"创建 companies/{company_name}/wiki/公司动态.md"],
                ))
        
        # 检查行业页面
        sectors = self.graph.get_all_sectors()
        for sector in sectors:
            sector_name = sector.name if hasattr(sector, 'name') else sector
            wiki_dir = self.wiki_root / "sectors" / sector_name / "wiki"
            
            if not wiki_dir.exists():
                gaps.append(KnowledgeGap(
                    entity_name=sector_name,
                    entity_type="sector",
                    topic_name="",
                    gap_type="missing_page",
                    description=f"行业 {sector_name} 没有 wiki 目录",
                    priority="medium",
                    suggestions=[f"创建 sectors/{sector_name}/wiki/ 目录"],
                ))
        
        return gaps
    
    def _check_empty_timelines(self) -> List[KnowledgeGap]:
        """
        检查空时间线
        
        Returns:
            知识缺口列表
        """
        gaps = []
        
        # 扫描所有 wiki 页面
        for wiki_file in self.wiki_root.rglob("*/wiki/*.md"):
            try:
                content = wiki_file.read_text(encoding="utf-8")
                
                # 提取实体信息
                entity_name = self._extract_entity_name(content, wiki_file)
                entity_type = self._extract_entity_type(wiki_file)
                
                # 检查时间线是否为空
                timeline_match = re.search(r'## 时间线\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
                
                if timeline_match:
                    timeline_content = timeline_match.group(1).strip()
                    
                    # 如果时间线只有占位符
                    if timeline_content in ["（暂无条目）", "", "待添加"]:
                        gaps.append(KnowledgeGap(
                            entity_name=entity_name,
                            entity_type=entity_type,
                            topic_name=wiki_file.stem,
                            gap_type="empty_timeline",
                            description=f"{entity_name}/{wiki_file.stem} 的时间线为空",
                            priority="medium",
                            suggestions=[f"添加新闻/公告到 {entity_name}"],
                        ))
            
            except Exception as e:
                continue
        
        return gaps
    
    def _check_outdated_pages(self) -> List[KnowledgeGap]:
        """
        检查过时页面
        
        Returns:
            知识缺口列表
        """
        gaps = []
        
        # 扫描所有 wiki 页面
        for wiki_file in self.wiki_root.rglob("*/wiki/*.md"):
            try:
                content = wiki_file.read_text(encoding="utf-8")
                
                # 提取实体信息
                entity_name = self._extract_entity_name(content, wiki_file)
                entity_type = self._extract_entity_type(wiki_file)
                
                # 提取最后更新时间
                match = re.search(r'last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
                
                if match:
                    last_updated = match.group(1)
                    
                    # 检查是否过时（超过30天）
                    try:
                        last_date = datetime.strptime(last_updated, "%Y-%m-%d")
                        days_old = (datetime.now() - last_date).days
                        
                        if days_old > 30:
                            gaps.append(KnowledgeGap(
                                entity_name=entity_name,
                                entity_type=entity_type,
                                topic_name=wiki_file.stem,
                                gap_type="outdated",
                                description=f"{entity_name}/{wiki_file.stem} 已{days_old}天未更新",
                                priority="medium" if days_old > 90 else "low",
                                suggestions=[f"更新 {entity_name} 的最新信息"],
                            ))
                    
                    except ValueError:
                        pass
            
            except Exception as e:
                continue
        
        return gaps
    
    def _check_unanswered_questions(self) -> List[KnowledgeGap]:
        """
        检查未回答的问题
        
        Returns:
            知识缺口列表
        """
        gaps = []
        
        # 获取所有问题
        try:
            all_questions = self.graph.get_all_questions()
        except AttributeError:
            # 如果方法不存在，返回空列表
            return gaps
        
        for entity_name, questions in all_questions.items():
            # 检查该实体的 wiki 页面
            wiki_dir = self.wiki_root / "sectors" / entity_name / "wiki"
            
            if not wiki_dir.exists():
                continue
            
            # 收集所有页面内容
            all_content = ""
            for wiki_file in wiki_dir.glob("*.md"):
                try:
                    content = wiki_file.read_text(encoding="utf-8")
                    all_content += content
                except Exception:
                    continue
            
            # 检查每个问题是否有回答
            for question in questions:
                # 简单检查：问题关键词是否在内容中出现
                keywords = re.findall(r'[\u4e00-\u9fff]{2,}', question)
                
                if keywords:
                    found = any(kw in all_content for kw in keywords)
                    
                    if not found:
                        gaps.append(KnowledgeGap(
                            entity_name=entity_name,
                            entity_type="sector",
                            topic_name=entity_name,
                            gap_type="unanswered_question",
                            description=f"问题「{question}」没有相关回答",
                            priority="medium",
                            suggestions=[f"搜索关于 {entity_name} {question} 的信息"],
                        ))
        
        return gaps
    
    def generate_suggestions(self, gaps: List[KnowledgeGap]) -> List[SourceSuggestion]:
        """
        生成来源建议
        
        Args:
            gaps: 知识缺口列表
            
        Returns:
            来源建议列表
        """
        suggestions = []
        
        for gap in gaps:
            if gap.gap_type == "missing_page":
                suggestions.append(SourceSuggestion(
                    title=f"创建 {gap.entity_name} 的 wiki 页面",
                    description=f"为 {gap.entity_name} 创建基本的 wiki 页面",
                    search_queries=[
                        f"{gap.entity_name} 最新消息",
                        f"{gap.entity_name} 公司介绍",
                    ],
                    related_entities=[gap.entity_name],
                    priority=gap.priority,
                    reason=gap.description,
                ))
            
            elif gap.gap_type == "empty_timeline":
                suggestions.append(SourceSuggestion(
                    title=f"为 {gap.entity_name} 添加时间线条目",
                    description=f"收集 {gap.entity_name} 的最新新闻和公告",
                    search_queries=[
                        f"{gap.entity_name} 最新新闻",
                        f"{gap.entity_name} 公告",
                        f"{gap.entity_name} 财报",
                    ],
                    related_entities=[gap.entity_name],
                    priority=gap.priority,
                    reason=gap.description,
                ))
            
            elif gap.gap_type == "outdated":
                suggestions.append(SourceSuggestion(
                    title=f"更新 {gap.entity_name} 的信息",
                    description=f"收集 {gap.entity_name} 的最新动态",
                    search_queries=[
                        f"{gap.entity_name} 最新消息",
                        f"{gap.entity_name} 2026",
                    ],
                    related_entities=[gap.entity_name],
                    priority=gap.priority,
                    reason=gap.description,
                ))
            
            elif gap.gap_type == "unanswered_question":
                # 从描述中提取问题
                question_match = re.search(r'问题「(.+?)」', gap.description)
                if question_match:
                    question = question_match.group(1)
                    suggestions.append(SourceSuggestion(
                        title=f"回答问题: {question}",
                        description=f"搜索关于 {gap.entity_name} {question} 的信息",
                        search_queries=[
                            f"{gap.entity_name} {question}",
                            f"{gap.entity_name} 最新进展",
                        ],
                        related_entities=[gap.entity_name],
                        priority=gap.priority,
                        reason=gap.description,
                    ))
        
        return suggestions
    
    def _extract_entity_name(self, content: str, file_path: Path) -> str:
        """
        提取实体名称
        
        Args:
            content: 页面内容
            file_path: 文件路径
            
        Returns:
            实体名称
        """
        # 从 frontmatter 提取
        match = re.search(r'entity:\s*"?([^"\n]+)"?', content)
        if match:
            return match.group(1).strip()
        
        # 从文件路径推断
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part in ("companies", "sectors", "themes") and i + 1 < len(parts):
                return parts[i + 1]
        
        return "Unknown"
    
    def _extract_entity_type(self, file_path: Path) -> str:
        """
        提取实体类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            实体类型
        """
        parts = file_path.parts
        for part in parts:
            if part == "companies":
                return "company"
            elif part == "sectors":
                return "sector"
            elif part == "themes":
                return "theme"
        
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="源发现")
    parser.add_argument("--suggest", action="store_true", help="生成来源建议")
    parser.add_argument("--search", type=str, help="搜索相关来源")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 源发现")
    print("=" * 50)
    
    # 初始化发现器
    discoverer = SourceDiscoverer(WIKI_ROOT)
    
    # 分析知识缺口
    print("\n分析知识缺口...")
    gaps = discoverer.analyze_gaps()
    
    print(f"\n发现 {len(gaps)} 个知识缺口:")
    
    # 按类型分组
    by_type: Dict[str, List[KnowledgeGap]] = {}
    for gap in gaps:
        if gap.gap_type not in by_type:
            by_type[gap.gap_type] = []
        by_type[gap.gap_type].append(gap)
    
    for gap_type, gap_list in by_type.items():
        print(f"\n{gap_type} ({len(gap_list)}个):")
        for gap in gap_list[:5]:  # 只显示前5个
            print(f"  - {gap.description} (优先级: {gap.priority})")
    
    if args.suggest:
        # 生成来源建议
        print("\n生成来源建议...")
        suggestions = discoverer.generate_suggestions(gaps)
        
        print(f"\n生成 {len(suggestions)} 个来源建议:")
        for i, suggestion in enumerate(suggestions[:10], 1):
            print(f"\n{i}. {suggestion.title}")
            print(f"   {suggestion.description}")
            print(f"   搜索词: {', '.join(suggestion.search_queries)}")
            print(f"   优先级: {suggestion.priority}")
        
        # 保存建议
        output_path = args.output or str(WIKI_ROOT / "source_suggestions.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 来源建议报告\n\n")
            f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## 概述\n\n")
            f.write(f"发现 {len(gaps)} 个知识缺口，生成 {len(suggestions)} 个来源建议\n\n")
            
            f.write(f"## 知识缺口\n\n")
            for gap_type, gap_list in by_type.items():
                f.write(f"### {gap_type} ({len(gap_list)}个)\n\n")
                for gap in gap_list:
                    f.write(f"- {gap.description} (优先级: {gap.priority})\n")
                f.write("\n")
            
            f.write(f"## 来源建议\n\n")
            for i, suggestion in enumerate(suggestions, 1):
                f.write(f"### {i}. {suggestion.title}\n\n")
                f.write(f"{suggestion.description}\n\n")
                f.write(f"**搜索词**:\n")
                for query in suggestion.search_queries:
                    f.write(f"- {query}\n")
                f.write(f"\n**优先级**: {suggestion.priority}\n")
                f.write(f"**原因**: {suggestion.reason}\n\n")
        
        print(f"\n建议已保存到: {output_path}")


if __name__ == "__main__":
    main()