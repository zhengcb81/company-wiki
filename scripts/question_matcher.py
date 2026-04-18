#!/usr/bin/env python3
"""
question_matcher.py — 问题匹配模块
检查新闻/公告是否回答了预设问题

用法：
    python3 scripts/question_matcher.py --test                    # 测试匹配
    python3 scripts/question_matcher.py --company 中微公司         # 分析指定公司
    python3 scripts/question_matcher.py --file path/to/file.md    # 分析指定文件
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class QuestionMatch:
    """问题匹配结果"""
    question: str
    relevance_score: float
    answer_summary: str
    key_points: List[str] = field(default_factory=list)
    confidence: str = "medium"  # low, medium, high


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    file_path: str
    title: str
    entity_name: str
    entity_type: str
    matches: List[QuestionMatch] = field(default_factory=list)
    has_updates: bool = False


def extract_key_sentences(text: str, max_sentences: int = 5) -> List[str]:
    """
    提取关键句子
    
    Args:
        text: 文本
        max_sentences: 最大句子数
        
    Returns:
        关键句子列表
    """
    # 分句
    sentences = re.split(r'(?<=[。！？；\n])\s*', text)
    
    # 过滤短句
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    
    # 评分
    scored_sentences = []
    for sentence in sentences:
        score = 0
        
        # 包含数字
        if re.search(r'\d+\.?\d*\s*(亿|万|%|元|倍|年|月|日|季度|Q[1-4])', sentence):
            score += 3
        
        # 包含动作词
        action_words = ['发布', '推出', '宣布', '获得', '突破', '增长', '下降', '合作', 
                       '收购', '投资', '融资', '上市', '签约', '中标', '获批', '实现']
        for word in action_words:
            if word in sentence:
                score += 2
                break
        
        # 包含行业关键词
        industry_words = ['半导体', '芯片', '刻蚀', '沉积', '晶圆', '封装', '光刻',
                         '密封', '石化', '核电', '国产替代', '自主可控']
        for word in industry_words:
            if word in sentence:
                score += 1
                break
        
        scored_sentences.append((score, sentence))
    
    # 排序并取 top N
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s[1] for s in scored_sentences[:max_sentences]]
    
    return top_sentences


def match_question_with_content(question: str, content: str) -> Optional[QuestionMatch]:
    """
    匹配单个问题与内容
    
    Args:
        question: 问题
        content: 内容
        
    Returns:
        匹配结果或 None
    """
    question_lower = question.lower()
    content_lower = content.lower()
    
    # 提取问题关键词
    keywords = extract_question_keywords(question)
    
    # 计算关键词匹配度
    matched_keywords = []
    for keyword in keywords:
        if keyword.lower() in content_lower:
            matched_keywords.append(keyword)
    
    if not matched_keywords:
        return None
    
    # 计算相关性分数
    relevance_score = len(matched_keywords) / len(keywords) if keywords else 0
    
    # 如果相关性太低，返回 None
    if relevance_score < 0.3:
        return None
    
    # 提取相关句子
    relevant_sentences = extract_relevant_sentences(question, content)
    
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
    
    return QuestionMatch(
        question=question,
        relevance_score=relevance_score,
        answer_summary=answer_summary,
        key_points=relevant_sentences,
        confidence=confidence,
    )


def extract_question_keywords(question: str) -> List[str]:
    """
    从问题中提取关键词
    
    Args:
        question: 问题
        
    Returns:
        关键词列表
    """
    # 移除问号和常见词汇
    question = question.replace("？", "").replace("?", "")
    
    # 常见问题模式
    patterns = {
        r'(.+?)(如何|怎样|怎么样)': lambda m: [m.group(1)],
        r'(.+?)(进展|情况|状况)': lambda m: [m.group(1), "进展"],
        r'(.+?)(趋势|方向)': lambda m: [m.group(1), "趋势"],
        r'(.+?)(格局|竞争)': lambda m: [m.group(1), "格局", "竞争"],
        r'(.+?)(国产化率|替代)': lambda m: [m.group(1), "国产化", "替代"],
        r'(.+?)(产能|产量)': lambda m: [m.group(1), "产能"],
        r'(.+?)(订单|客户)': lambda m: [m.group(1), "订单", "客户"],
        r'(.+?)(技术|创新)': lambda m: [m.group(1), "技术", "创新"],
    }
    
    for pattern, extractor in patterns.items():
        match = re.search(pattern, question)
        if match:
            return extractor(match)
    
    # 默认：提取所有2字以上的词
    words = re.findall(r'[\u4e00-\u9fff]{2,}', question)
    return words if words else [question]


def extract_relevant_sentences(question: str, content: str, max_sentences: int = 3) -> List[str]:
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
    keywords = extract_question_keywords(question)
    
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


def analyze_content_for_questions(
    content: str,
    questions: List[str],
    entity_name: str,
    entity_type: str,
) -> ContentAnalysis:
    """
    分析内容与问题的匹配
    
    Args:
        content: 内容
        questions: 问题列表
        entity_name: 实体名称
        entity_type: 实体类型
        
    Returns:
        内容分析结果
    """
    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown"
    
    # 匹配每个问题
    matches = []
    for question in questions:
        match = match_question_with_content(question, content)
        if match:
            matches.append(match)
    
    return ContentAnalysis(
        file_path="",
        title=title,
        entity_name=entity_name,
        entity_type=entity_type,
        matches=matches,
        has_updates=len(matches) > 0,
    )


def generate_timeline_entry_with_questions(
    analysis: ContentAnalysis,
    published_date: str,
    source_type: str,
    source_path: str,
) -> str:
    """
    生成带有问题匹配的时间线条目
    
    Args:
        analysis: 内容分析结果
        published_date: 发布日期
        source_type: 来源类型
        source_path: 来源路径
        
    Returns:
        格式化的时间线条目
    """
    entry = f"### {published_date} | {source_type} | {analysis.title}\n"
    
    # 添加关键点
    if analysis.matches:
        # 取第一个匹配的答案摘要作为要点
        first_match = analysis.matches[0]
        entry += f"- {first_match.answer_summary[:200]}\n"
    
    # 添加问题匹配部分
    if analysis.matches:
        entry += "\n**回答问题**：\n"
        for match in analysis.matches:
            if match.confidence in ["high", "medium"]:
                entry += f"- [{match.question}] {match.answer_summary[:150]}...\n"
    
    entry += f"\n- [来源]({source_path})\n"
    
    return entry


def main():
    parser = argparse.ArgumentParser(description="问题匹配")
    parser.add_argument("--company", type=str, help="分析指定公司")
    parser.add_argument("--file", type=str, help="分析指定文件")
    parser.add_argument("--test", action="store_true", help="测试匹配功能")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 问题匹配")
    print("=" * 50)
    
    if args.test:
        # 测试模式
        test_questions = [
            "各环节设备国产化率？",
            "先进制程设备进展？",
            "大客户订单和扩产计划？",
            "美国制裁对设备出口的影响？",
        ]
        
        test_content = """
# 中微公司发布新一代刻蚀设备

中微公司（688012）今日宣布推出新一代电感耦合ICP等离子体刻蚀设备，该设备在先进制程节点表现出色。

## 主要亮点

1. 刻蚀精度提升30%，支持5nm以下先进制程
2. 产能提高20%，已获得多家晶圆厂验证
3. 国产化率达到85%，打破国外垄断

公司董事长尹志尧表示，这标志着国产半导体设备在高端领域取得重要突破。公司已与中芯国际、华虹半导体等大客户签署订单，预计2026年实现量产。

关于美国制裁影响，公司表示已做好技术储备，关键零部件已实现国产替代。
"""
        
        print("\nTest Questions:")
        for q in test_questions:
            print(f"  - {q}")
        
        print("\nAnalyzing content...")
        analysis = analyze_content_for_questions(
            test_content,
            test_questions,
            "中微公司",
            "company",
        )
        
        print(f"\nResults:")
        print(f"  Title: {analysis.title}")
        print(f"  Has Updates: {analysis.has_updates}")
        print(f"  Matched Questions: {len(analysis.matches)}")
        
        for match in analysis.matches:
            print(f"\n  Question: {match.question}")
            print(f"  Relevance: {match.relevance_score:.0%}")
            print(f"  Confidence: {match.confidence}")
            print(f"  Answer: {match.answer_summary[:100]}...")
        
        # 生成时间线条目
        print("\n" + "=" * 50)
        print("Generated Timeline Entry:")
        print("=" * 50)
        
        entry = generate_timeline_entry_with_questions(
            analysis,
            "2026-04-17",
            "新闻",
            "../raw/news/test.md",
        )
        print(entry)
        
        return
    
    if args.file:
        # 分析指定文件
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"ERROR: File not found: {file_path}")
            sys.exit(1)
        
        content = file_path.read_text(encoding="utf-8")
        
        # 从文件路径推断公司名
        parts = file_path.parts
        company_name = None
        for i, part in enumerate(parts):
            if part == "companies" and i + 1 < len(parts):
                company_name = parts[i + 1]
                break
        
        if not company_name:
            print("ERROR: Cannot determine company from file path")
            sys.exit(1)
        
        # 获取问题列表
        graph = Graph()
        company = graph.get_company(company_name)
        if not company:
            print(f"ERROR: Company not found in graph: {company_name}")
            sys.exit(1)
        
        # 获取相关行业的问题
        questions = []
        for sector_name in company.get("sectors", []):
            sector = graph.get_sector(sector_name)
            if sector:
                questions.extend(sector.get("questions", []))
        
        if not questions:
            print("No questions found for this company")
            return
        
        print(f"\nAnalyzing file: {file_path.name}")
        print(f"Company: {company_name}")
        print(f"Questions: {len(questions)}")
        
        analysis = analyze_content_for_questions(
            content,
            questions,
            company_name,
            "company",
        )
        
        print(f"\nResults:")
        print(f"  Has Updates: {analysis.has_updates}")
        print(f"  Matched Questions: {len(analysis.matches)}")
        
        for match in analysis.matches:
            print(f"\n  Question: {match.question}")
            print(f"  Relevance: {match.relevance_score:.0%}")
            print(f"  Answer: {match.answer_summary[:100]}...")
        
        return
    
    print("Use --test to run test, or --file to analyze a file")


if __name__ == "__main__":
    main()