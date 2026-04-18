#!/usr/bin/env python3
"""
query.py — Wiki 查询模块
搜索 wiki 页面，综合答案，并将答案存回 wiki

用法：
    python3 scripts/query.py "中微公司的刻蚀设备进展？"
    python3 scripts/query.py --search "国产化率"
    python3 scripts/query.py --save-answer "问题" "答案"
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class WikiPage:
    """Wiki 页面"""
    path: Path
    title: str
    entity_name: str
    entity_type: str
    topic_name: str
    content: str
    last_updated: Optional[str] = None
    sources_count: int = 0


@dataclass
class SearchResult:
    """搜索结果"""
    page: WikiPage
    relevance_score: float
    matched_sections: List[str] = field(default_factory=list)


@dataclass
class QueryAnswer:
    """查询答案"""
    question: str
    answer: str
    sources: List[WikiPage] = field(default_factory=list)
    confidence: str = "medium"
    generated_at: str = ""
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


class WikiSearcher:
    """Wiki 搜索器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化搜索器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        搜索 wiki 页面
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        # 提取查询关键词
        keywords = self._extract_keywords(query)
        
        # 扫描所有 wiki 页面
        all_pages = self._scan_all_pages()
        
        # 计算相关性
        results = []
        for page in all_pages:
            score, sections = self._calculate_relevance(page, keywords, query)
            if score > 0:
                results.append(SearchResult(
                    page=page,
                    relevance_score=score,
                    matched_sections=sections,
                ))
        
        # 排序并返回 top N
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:max_results]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词
        
        Args:
            query: 查询文本
            
        Returns:
            关键词列表
        """
        # 移除问号
        query = query.replace("？", "").replace("?", "")
        
        # 提取中文词汇
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', query)
        
        # 如果没有中文词汇，提取英文
        if not keywords:
            keywords = re.findall(r'[a-zA-Z]+', query)
        
        return keywords
    
    def _scan_all_pages(self) -> List[WikiPage]:
        """
        扫描所有 wiki 页面
        
        Returns:
            Wiki 页面列表
        """
        pages = []
        
        # 扫描公司 wiki
        companies_dir = self.wiki_root / "companies"
        if companies_dir.exists():
            for company_dir in companies_dir.iterdir():
                if company_dir.is_dir() and not company_dir.name.startswith("_"):
                    wiki_dir = company_dir / "wiki"
                    if wiki_dir.exists():
                        for wiki_file in wiki_dir.glob("*.md"):
                            page = self._load_page(wiki_file, company_dir.name, "company")
                            if page:
                                pages.append(page)
        
        # 扫描行业 wiki
        sectors_dir = self.wiki_root / "sectors"
        if sectors_dir.exists():
            for sector_dir in sectors_dir.iterdir():
                if sector_dir.is_dir():
                    wiki_dir = sector_dir / "wiki"
                    if wiki_dir.exists():
                        for wiki_file in wiki_dir.glob("*.md"):
                            page = self._load_page(wiki_file, sector_dir.name, "sector")
                            if page:
                                pages.append(page)
        
        # 扫描主题 wiki
        themes_dir = self.wiki_root / "themes"
        if themes_dir.exists():
            for theme_dir in themes_dir.iterdir():
                if theme_dir.is_dir():
                    wiki_dir = theme_dir / "wiki"
                    if wiki_dir.exists():
                        for wiki_file in wiki_dir.glob("*.md"):
                            page = self._load_page(wiki_file, theme_dir.name, "theme")
                            if page:
                                pages.append(page)
        
        return pages
    
    def _load_page(self, file_path: Path, entity_name: str, entity_type: str) -> Optional[WikiPage]:
        """
        加载 wiki 页面
        
        Args:
            file_path: 文件路径
            entity_name: 实体名称
            entity_type: 实体类型
            
        Returns:
            Wiki 页面或 None
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # 解析 frontmatter
            title = file_path.stem
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
                            
                            if key == "title":
                                title = val
                            elif key == "last_updated":
                                last_updated = val
                            elif key == "sources_count":
                                try:
                                    sources_count = int(val)
                                except ValueError:
                                    pass
            
            return WikiPage(
                path=file_path,
                title=title,
                entity_name=entity_name,
                entity_type=entity_type,
                topic_name=file_path.stem,
                content=content,
                last_updated=last_updated,
                sources_count=sources_count,
            )
        
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def _calculate_relevance(self, page: WikiPage, keywords: List[str], query: str) -> Tuple[float, List[str]]:
        """
        计算页面与查询的相关性
        
        Args:
            page: Wiki 页面
            keywords: 关键词列表
            query: 原始查询
            
        Returns:
            (相关性分数, 匹配的章节列表)
        """
        content_lower = page.content.lower()
        query_lower = query.lower()
        
        score = 0.0
        matched_sections = []
        
        # 1. 实体名称匹配（最高优先级）
        if page.entity_name.lower() in query_lower:
            score += 20.0
            matched_sections.append(f"实体匹配: {page.entity_name}")
        
        # 2. 查询中的实体名称在页面中
        for keyword in keywords:
            if keyword in page.entity_name:
                score += 15.0
                matched_sections.append(f"实体关键词: {keyword}")
                break
        
        # 3. 标题匹配
        if any(kw.lower() in page.title.lower() for kw in keywords):
            score += 10.0
            matched_sections.append(f"标题匹配: {page.title}")
        
        # 4. 内容关键词匹配
        keyword_matches = 0
        for keyword in keywords:
            if keyword.lower() in content_lower:
                keyword_matches += 1
        
        if keywords:
            keyword_ratio = keyword_matches / len(keywords)
            score += keyword_ratio * 5.0
        
        # 5. 提取匹配的章节
        sections = self._extract_matching_sections(page.content, keywords)
        matched_sections.extend(sections)
        
        # 6. 时间线匹配（如果查询包含时间相关词汇）
        time_keywords = ["最新", "最近", "进展", "动态", "新闻"]
        for tk in time_keywords:
            if tk in query and "时间线" in page.content:
                score += 3.0
                matched_sections.append("包含时间线")
                break
        
        return score, matched_sections
    
    def _extract_matching_sections(self, content: str, keywords: List[str], max_sections: int = 3) -> List[str]:
        """
        提取匹配的章节
        
        Args:
            content: 页面内容
            keywords: 关键词列表
            max_sections: 最大章节数
            
        Returns:
            匹配的章节列表
        """
        # 分割成章节
        sections = re.split(r'\n(?=#{1,3}\s)', content)
        
        matched = []
        for section in sections:
            section_lower = section.lower()
            
            # 检查是否包含关键词
            matches = sum(1 for kw in keywords if kw.lower() in section_lower)
            
            if matches > 0:
                # 提取前100个字符
                preview = section[:150].replace('\n', ' ')
                matched.append(f"[{matches}个关键词匹配] {preview}...")
            
            if len(matched) >= max_sections:
                break
        
        return matched


class AnswerSynthesizer:
    """答案综合器 (支持 LLM)"""

    def __init__(self, wiki_root: Path):
        self.wiki_root = wiki_root
        self._llm = None

    def _get_llm(self):
        """懒加载 LLM 客户端"""
        if self._llm is None:
            try:
                from llm_client import LLMClient
                self._llm = LLMClient()
            except Exception:
                self._llm = None
        return self._llm

    def synthesize(self, question: str, search_results: List[SearchResult]) -> QueryAnswer:
        """
        综合答案 (先尝试 LLM, fallback 到规则)
        """
        if not search_results:
            return QueryAnswer(question=question, answer="未找到相关信息", confidence="low")

        # 收集相关页面内容
        sources = []
        page_contents = []
        for result in search_results[:5]:
            page = result.page
            sources.append(page)
            # 提取时间线条目内容
            entries = self._extract_timeline_entries(page.content)
            if entries:
                page_contents.append({
                    "title": page.title,
                    "entity": page.entity_name,
                    "content": "\n".join(entries[:5]),
                })
            elif result.matched_sections:
                page_contents.append({
                    "title": page.title,
                    "entity": page.entity_name,
                    "content": "\n".join(result.matched_sections[:3]),
                })

        if not page_contents:
            return QueryAnswer(question=question, answer="未找到相关信息", confidence="low")

        # 尝试 LLM 综合答案
        llm = self._get_llm()
        answer_text = ""
        if llm and llm.available:
            answer_text = llm.answer_query(question, page_contents)

        # Fallback 到规则综合
        if not answer_text or answer_text == "无法生成答案 (LLM 不可用)":
            answer_text = self._build_answer(question, [
                {"entity": p["entity"], "entries": p["content"].split("\n")[:3]}
                for p in page_contents
            ])

        confidence = "high" if len(sources) >= 3 else ("medium" if len(sources) >= 1 else "low")

        return QueryAnswer(
            question=question,
            answer=answer_text,
            sources=sources,
            confidence=confidence,
        )
    
    def _extract_timeline_entries(self, content: str, max_entries: int = 5) -> List[str]:
        """
        提取时间线条目
        
        Args:
            content: 页面内容
            max_entries: 最大条目数
            
        Returns:
            时间线条目列表
        """
        # 查找时间线部分
        timeline_match = re.search(r'## 时间线\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        
        if not timeline_match:
            return []
        
        timeline_content = timeline_match.group(1)
        
        # 提取 ### 开头的条目
        entries = re.findall(r'### .+', timeline_content)
        
        return entries[:max_entries]
    
    def _build_answer(self, question: str, relevant_info: List[Dict[str, Any]]) -> str:
        """
        构建答案
        
        Args:
            question: 问题
            relevant_info: 相关信息
            
        Returns:
            答案文本
        """
        if not relevant_info:
            return "未找到直接相关信息。"
        
        answer_parts = [f"根据知识库中的信息，关于「{question}」：\n"]
        
        for info in relevant_info:
            answer_parts.append(f"**{info['entity']}**:")
            for entry in info["entries"]:
                answer_parts.append(f"  - {entry}")
            answer_parts.append("")
        
        answer_parts.append("以上信息来自知识库中的多个页面，详情请查看相关 wiki 页面。")
        
        return "\n".join(answer_parts)


class AnswerSaver:
    """答案保存器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化保存器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
    
    def save_to_wiki(self, answer: QueryAnswer, entity_name: str, entity_type: str) -> Optional[Path]:
        """
        将答案保存到 wiki
        
        Args:
            answer: 查询答案
            entity_name: 实体名称
            entity_type: 实体类型
            
        Returns:
            保存的文件路径
        """
        # 确定目标目录
        if entity_type == "company":
            wiki_dir = self.wiki_root / "companies" / entity_name / "wiki"
        elif entity_type == "sector":
            wiki_dir = self.wiki_root / "sectors" / entity_name / "wiki"
        elif entity_type == "theme":
            wiki_dir = self.wiki_root / "themes" / entity_name / "wiki"
        else:
            print(f"Unknown entity type: {entity_type}")
            return None
        
        # 确保目录存在
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        safe_question = re.sub(r'[^\w\u4e00-\u9fff]', '_', answer.question)[:50]
        filename = f"Q_{safe_question}.md"
        file_path = wiki_dir / filename
        
        # 构建内容
        content = f"""---
title: "{answer.question}"
entity: "{entity_name}"
type: {entity_type}_query
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
query_confidence: "{answer.confidence}"
generated_at: "{answer.generated_at}"
tags: [query, auto-generated]
---

# {entity_name} — {answer.question}

## 问题
{answer.question}

## 答案
{answer.answer}

## 来源
"""
        
        for source in answer.sources:
            rel_path = source.path.relative_to(self.wiki_root)
            content += f"- [{source.entity_name}/{source.topic_name}]({rel_path})\n"
        
        content += f"""
## 元数据
- 生成时间: {answer.generated_at}
- 置信度: {answer.confidence}
- 来源数量: {len(answer.sources)}

---
*此页面由 query.py 自动生成*
"""
        
        # 保存文件
        file_path.write_text(content, encoding="utf-8")
        print(f"答案已保存到: {file_path.relative_to(self.wiki_root)}")
        
        # 更新 log.md
        self._append_log(f"Query answer saved: {answer.question} -> {entity_name}")
        
        return file_path
    
    def save_as_timeline_entry(self, answer: QueryAnswer, entity_name: str, entity_type: str, topic_name: str) -> bool:
        """
        将答案作为时间线条目保存到现有页面
        
        Args:
            answer: 查询答案
            entity_name: 实体名称
            entity_type: 实体类型
            topic_name: 主题名称
            
        Returns:
            True 如果保存成功
        """
        # 确定目标文件
        if entity_type == "company":
            wiki_file = self.wiki_root / "companies" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "sector":
            wiki_file = self.wiki_root / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "theme":
            wiki_file = self.wiki_root / "themes" / entity_name / "wiki" / f"{topic_name}.md"
        else:
            return False
        
        if not wiki_file.exists():
            print(f"Wiki file not found: {wiki_file}")
            return False
        
        # 读取现有内容
        content = wiki_file.read_text(encoding="utf-8")
        
        # 构建时间线条目
        entry = f"""
### {datetime.now().strftime('%Y-%m-%d')} | 查询 | {answer.question}
{answer.answer[:200]}...

**来源**: {len(answer.sources)} 个 wiki 页面
"""
        
        # 插入到时间线
        timeline_pos = content.find("## 时间线")
        if timeline_pos < 0:
            print("No timeline section found")
            return False
        
        # 找到时间线后第一个条目
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
        
        # 保存文件
        wiki_file.write_text(content, encoding="utf-8")
        print(f"答案已作为时间线条目保存到: {wiki_file.relative_to(self.wiki_root)}")
        
        return True
    
    def _append_log(self, message: str) -> None:
        """
        追加日志
        
        Args:
            message: 日志消息
        """
        log_path = self.wiki_root / "log.md"
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] query | {message}\n"
        
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"
        
        content += entry
        log_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Wiki 查询")
    parser.add_argument("question", nargs="?", help="查询问题")
    parser.add_argument("--search", type=str, help="搜索关键词")
    parser.add_argument("--save-answer", nargs=2, metavar=("QUESTION", "ANSWER"), help="保存答案到 wiki")
    parser.add_argument("--entity", type=str, help="目标实体名称")
    parser.add_argument("--entity-type", type=str, default="company", choices=["company", "sector", "theme"], help="实体类型")
    parser.add_argument("--topic", type=str, help="目标主题名称")
    parser.add_argument("--max-results", type=int, default=5, help="最大搜索结果数")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 查询")
    print("=" * 50)
    
    # 初始化
    searcher = WikiSearcher(WIKI_ROOT)
    synthesizer = AnswerSynthesizer(WIKI_ROOT)
    saver = AnswerSaver(WIKI_ROOT)
    
    if args.save_answer:
        # 直接保存答案
        question, answer_text = args.save_answer
        
        if not args.entity:
            print("Error: --entity is required when using --save-answer")
            sys.exit(1)
        
        answer = QueryAnswer(
            question=question,
            answer=answer_text,
            confidence="manual",
        )
        
        if args.topic:
            # 保存为时间线条目
            saver.save_as_timeline_entry(answer, args.entity, args.entity_type, args.topic)
        else:
            # 保存为新页面
            saver.save_to_wiki(answer, args.entity, args.entity_type)
        
        return
    
    # 搜索
    query = args.question or args.search
    if not query:
        print("Error: Please provide a question or use --search")
        sys.exit(1)
    
    print(f"\n查询: {query}")
    print(f"搜索 wiki 页面...")
    
    results = searcher.search(query, max_results=args.max_results)
    
    print(f"找到 {len(results)} 个相关页面:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.page.entity_name}/{result.page.topic_name} (相关性: {result.relevance_score:.1f})")
        for section in result.matched_sections[:2]:
            print(f"     - {section[:80]}...")
    
    if args.search:
        # 只搜索，不综合答案
        return
    
    # 综合答案
    print(f"\n综合答案...")
    answer = synthesizer.synthesize(query, results)
    
    print(f"\n{'=' * 50}")
    print(f"答案 (置信度: {answer.confidence}):")
    print(f"{'=' * 50}")
    print(answer.answer)
    
    # 询问是否保存
    if answer.sources:
        print(f"\n来源: {len(answer.sources)} 个 wiki 页面")
        
        # 自动保存到第一个来源的实体
        first_source = answer.sources[0]
        print(f"\n自动保存到: {first_source.entity_name}/{first_source.topic_name}")
        
        saver.save_as_timeline_entry(
            answer,
            first_source.entity_name,
            first_source.entity_type,
            first_source.topic_name,
        )


if __name__ == "__main__":
    main()