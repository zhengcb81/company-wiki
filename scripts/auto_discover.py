#!/usr/bin/env python3
"""
auto_discover.py — 自动发现模块
从新闻中自动发现新公司、新主题

用法：
    python3 scripts/auto_discover.py                      # 运行发现
    python3 scripts/auto_discover.py --show-suggestions   # 显示建议
    python3 scripts/auto_discover.py --apply              # 应用建议
"""

import argparse
import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import Counter

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class CompanySuggestion:
    """公司建议"""
    name: str
    context: str
    suggested_sectors: List[str] = field(default_factory=list)
    confidence: float = 0.0
    news_count: int = 0


@dataclass
class TopicSuggestion:
    """主题建议"""
    topic_name: str
    description: str
    related_companies: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)
    news_count: int = 0


@dataclass
class QuestionSuggestion:
    """问题建议"""
    entity_name: str
    entity_type: str
    question: str
    reason: str
    confidence: float = 0.0


def extract_company_names(text: str) -> List[str]:
    """
    从文本中提取公司名称
    
    Args:
        text: 文本
        
    Returns:
        公司名称列表
    """
    # 常见公司名称模式
    patterns = [
        r'[\u4e00-\u9fff]{2,}(?:公司|集团|股份|科技|电子|半导体|设备)',
        r'[\u4e00-\u9fff]{2,}(?:Inc|Corp|Ltd|Co)',
        r'[A-Z][a-zA-Z]+(?:Inc|Corp|Ltd|Co)',
    ]
    
    companies = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        companies.update(matches)
    
    return list(companies)


def load_topic_keywords() -> Dict[str, List[str]]:
    """
    加载主题关键词配置
    
    Returns:
        主题关键词字典
    """
    config_path = WIKI_ROOT / "config_rules.yaml"
    
    if not config_path.exists():
        return get_default_topic_keywords()
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("topic_keywords", get_default_topic_keywords())
    except Exception as e:
        print(f"Warning: Failed to load topic keywords from config: {e}")
        return get_default_topic_keywords()


def get_default_topic_keywords() -> Dict[str, List[str]]:
    """
    获取默认主题关键词
    
    Returns:
        默认主题关键词字典
    """
    return {
        "Chiplet": ["Chiplet", "芯粒", "小芯片", "异构集成"],
        "HBM": ["HBM", "高带宽内存", "High Bandwidth Memory", "HBM3", "HBM3E"],
        "先进封装": ["先进封装", "CoWoS", "2.5D", "3D封装", "SiP", "扇出"],
        "光刻": ["光刻", "EUV", "DUV", "Lithography", "曝光"],
        "刻蚀": ["刻蚀", "Etch", "ICP", "CCP", "干法刻蚀", "湿法刻蚀"],
        "沉积": ["沉积", "CVD", "PVD", "ALD", "薄膜", "外延"],
        "清洗": ["清洗", "Cleaning", "湿法清洗", "干法清洗"],
        "CMP": ["CMP", "化学机械抛光", "研磨", "平坦化"],
        "量检测": ["量检测", "检测", "量测", "计量", "缺陷检测"],
        "硅片": ["硅片", "硅晶圆", "Wafer", "大硅片", "12寸", "8寸"],
        "光刻胶": ["光刻胶", "Photoresist", "ArF", "KrF", "EUV光刻胶"],
        "电子特气": ["电子特气", "电子气体", "特种气体", "高纯气体"],
        "靶材": ["靶材", "Sputtering", "溅射", "高纯靶材"],
        "液冷": ["液冷", "浸没式", "冷板", "散热", "温控"],
        "光模块": ["光模块", "800G", "1.6T", "CPO", "硅光", "LPO"],
        "算力": ["算力", "AI服务器", "智算中心", "GPU服务器", "推理", "训练"],
        "储能": ["储能", "电池", "Energy Storage", "锂电池", "钠电池"],
    }


# 全局变量：主题关键词
TOPIC_KEYWORDS = load_topic_keywords()


def extract_topics(text: str) -> List[str]:
    """
    从文本中提取主题
    
    Args:
        text: 文本
        
    Returns:
        主题列表
    """
    topics = set()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                topics.add(topic)
                break
    
    return list(topics)


def discover_new_companies(news_files: List[Path], known_companies: Set[str]) -> List[CompanySuggestion]:
    """
    从新闻中发现新公司
    
    Args:
        news_files: 新闻文件列表
        known_companies: 已知公司集合
        
    Returns:
        公司建议列表
    """
    company_mentions = Counter()
    company_contexts = {}
    
    for news_file in news_files:
        try:
            content = news_file.read_text(encoding='utf-8', errors='ignore')
            
            # 提取公司名称
            companies = extract_company_names(content)
            
            for company in companies:
                if company not in known_companies:
                    company_mentions[company] += 1
                    
                    # 保存上下文
                    if company not in company_contexts:
                        # 找到公司名称在文本中的位置
                        idx = content.find(company)
                        if idx >= 0:
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(company) + 50)
                            context = content[start:end].replace('\n', ' ')
                            company_contexts[company] = context
        
        except Exception as e:
            print(f"Error reading {news_file}: {e}")
            continue
    
    # 生成建议
    suggestions = []
    for company, count in company_mentions.most_common(20):
        if count >= 2:  # 至少出现2次
            suggestion = CompanySuggestion(
                name=company,
                context=company_contexts.get(company, ""),
                news_count=count,
                confidence=min(count / 10, 1.0),  # 简单的置信度计算
            )
            suggestions.append(suggestion)
    
    return suggestions


def discover_new_topics(news_files: List[Path], known_topics: Set[str]) -> List[TopicSuggestion]:
    """
    从新闻中发现新主题
    
    Args:
        news_files: 新闻文件列表
        known_topics: 已知主题集合
        
    Returns:
        主题建议列表
    """
    topic_mentions = Counter()
    topic_companies = {}
    
    for news_file in news_files:
        try:
            content = news_file.read_text(encoding='utf-8', errors='ignore')
            
            # 提取主题
            topics = extract_topics(content)
            
            # 提取公司
            companies = extract_company_names(content)
            
            for topic in topics:
                if topic not in known_topics:
                    topic_mentions[topic] += 1
                    
                    # 记录相关公司
                    if topic not in topic_companies:
                        topic_companies[topic] = set()
                    topic_companies[topic].update(companies)
        
        except Exception as e:
            print(f"Error reading {news_file}: {e}")
            continue
    
    # 生成建议
    suggestions = []
    for topic, count in topic_mentions.most_common(10):
        if count >= 3:  # 至少出现3次
            suggestion = TopicSuggestion(
                topic_name=topic,
                description=f"从新闻中自动发现的主题",
                related_companies=list(topic_companies.get(topic, set()))[:5],
                news_count=count,
            )
            suggestions.append(suggestion)
    
    return suggestions


def load_question_patterns() -> List[Dict[str, str]]:
    """
    加载问题模式配置
    
    Returns:
        问题模式列表
    """
    config_path = WIKI_ROOT / "config_rules.yaml"
    
    if not config_path.exists():
        return get_default_question_patterns()
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("question_patterns", get_default_question_patterns())
    except Exception as e:
        print(f"Warning: Failed to load question patterns from config: {e}")
        return get_default_question_patterns()


def get_default_question_patterns() -> List[Dict[str, str]]:
    """
    获取默认问题模式
    
    Returns:
        默认问题模式列表
    """
    return [
        {"pattern": r'国产化率.*?达到.*?(\d+)%', "template": "国产化率达到{}%"},
        {"pattern": r'产能.*?提升.*?(\d+)%', "template": "产能提升{}%"},
        {"pattern": r'营收.*?增长.*?(\d+)%', "template": "营收增长{}%"},
        {"pattern": r'获得.*?订单', "template": "获得新订单"},
        {"pattern": r'发布.*?新品', "template": "发布新品"},
        {"pattern": r'突破.*?技术', "template": "技术突破"},
        {"pattern": r'客户.*?验证', "template": "客户验证通过"},
        {"pattern": r'量产.*?([\\u4e00-\\u9fff]+)', "template": "{}量产"},
    ]


def suggest_new_questions(news_files: List[Path], graph: Graph) -> List[QuestionSuggestion]:
    """
    建议新问题
    
    Args:
        news_files: 新闻文件列表
        graph: 图数据
        
    Returns:
        问题建议列表
    """
    suggestions = []
    
    # 获取现有问题
    existing_questions = set()
    try:
        for entity_name, questions in graph.get_all_questions().items():
            existing_questions.update(questions)
    except AttributeError:
        # 如果方法不存在，跳过
        pass
    
    # 加载问题模式
    question_patterns = load_question_patterns()
    
    for news_file in news_files[:50]:  # 只检查前50个文件
        try:
            content = news_file.read_text(encoding='utf-8', errors='ignore')
            
            for pattern_config in question_patterns:
                # 支持新格式（字典）和旧格式（元组）
                if isinstance(pattern_config, dict):
                    pattern = pattern_config.get("pattern", "")
                    question_template = pattern_config.get("template", "")
                else:
                    # 旧格式：(pattern, template)
                    pattern, question_template = pattern_config
                
                matches = re.findall(pattern, content)
                if matches:
                    # 找到相关的实体
                    for entity_name, entity_type, _ in graph.find_related_entities(content):
                        question = question_template.format(*matches) if matches else question_template
                        
                        if question not in existing_questions:
                            suggestion = QuestionSuggestion(
                                entity_name=entity_name,
                                entity_type=entity_type,
                                question=question,
                                reason=f"从新闻中自动发现",
                                confidence=0.5,
                            )
                            suggestions.append(suggestion)
        
        except Exception as e:
            continue
    
    # 去重
    unique_suggestions = []
    seen = set()
    for s in suggestions:
        key = (s.entity_name, s.question)
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(s)
    
    return unique_suggestions[:10]  # 返回前10个建议


def save_suggestions(
    company_suggestions: List[CompanySuggestion],
    topic_suggestions: List[TopicSuggestion],
    question_suggestions: List[QuestionSuggestion],
) -> Path:
    """
    保存建议到文件
    
    Args:
        company_suggestions: 公司建议
        topic_suggestions: 主题建议
        question_suggestions: 问题建议
        
    Returns:
        保存的文件路径
    """
    suggestions_file = WIKI_ROOT / "suggestions.json"
    
    data = {
        "timestamp": str(Path(__file__).stat().st_mtime),
        "companies": [
            {
                "name": s.name,
                "context": s.context,
                "suggested_sectors": s.suggested_sectors,
                "confidence": s.confidence,
                "news_count": s.news_count,
            }
            for s in company_suggestions
        ],
        "topics": [
            {
                "topic_name": s.topic_name,
                "description": s.description,
                "related_companies": s.related_companies,
                "suggested_questions": s.suggested_questions,
                "news_count": s.news_count,
            }
            for s in topic_suggestions
        ],
        "questions": [
            {
                "entity_name": s.entity_name,
                "entity_type": s.entity_type,
                "question": s.question,
                "reason": s.reason,
                "confidence": s.confidence,
            }
            for s in question_suggestions
        ],
    }
    
    with open(suggestions_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return suggestions_file


def load_suggestions() -> Dict[str, Any]:
    """
    加载建议
    
    Returns:
        建议数据
    """
    suggestions_file = WIKI_ROOT / "suggestions.json"
    
    if not suggestions_file.exists():
        return {"companies": [], "topics": [], "questions": []}
    
    with open(suggestions_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_company_suggestion(suggestion: Dict[str, Any], graph: Graph) -> bool:
    """
    应用公司建议
    
    Args:
        suggestion: 建议数据
        graph: 图数据
        
    Returns:
        True 如果成功应用
    """
    try:
        # 添加公司
        graph.add_company(
            name=suggestion["name"],
            ticker="",
            exchange="",
            sectors=suggestion.get("suggested_sectors", []),
            themes=[],
            news_queries=[f"{suggestion['name']} 最新消息"],
            position=suggestion.get("context", "")[:100],
        )
        
        # 保存
        graph.save()
        
        # 创建公司目录
        company_dir = WIKI_ROOT / "companies" / suggestion["name"]
        company_dir.mkdir(parents=True, exist_ok=True)
        (company_dir / "raw").mkdir(exist_ok=True)
        (company_dir / "raw" / "news").mkdir(exist_ok=True)
        (company_dir / "wiki").mkdir(exist_ok=True)
        
        return True
    
    except Exception as e:
        print(f"Error applying company suggestion: {e}")
        return False


def apply_topic_suggestion(suggestion: Dict[str, Any], graph: Graph) -> bool:
    """
    应用主题建议
    
    Args:
        suggestion: 建议数据
        graph: 图数据
        
    Returns:
        True 如果成功应用
    """
    try:
        # 添加节点
        graph.add_node(
            name=suggestion["topic_name"],
            node_type="sector",
            description=suggestion.get("description", ""),
            keywords=[suggestion["topic_name"]],
        )
        
        # 保存
        graph.save()
        
        # 创建行业目录
        sector_dir = WIKI_ROOT / "sectors" / suggestion["topic_name"]
        sector_dir.mkdir(parents=True, exist_ok=True)
        (sector_dir / "raw").mkdir(exist_ok=True)
        (sector_dir / "wiki").mkdir(exist_ok=True)
        
        return True
    
    except Exception as e:
        print(f"Error applying topic suggestion: {e}")
        return False


def apply_question_suggestion(suggestion: Dict[str, Any], graph: Graph) -> bool:
    """
    应用问题建议
    
    Args:
        suggestion: 建议数据
        graph: 图数据
        
    Returns:
        True 如果成功应用
    """
    try:
        entity_name = suggestion["entity_name"]
        entity_type = suggestion["entity_type"]
        question = suggestion["question"]
        
        # 获取现有问题
        if entity_type == "sector":
            sector = graph.get_sector(entity_name)
            if sector:
                questions = sector.get("questions", [])
                if question not in questions:
                    questions.append(question)
                    
                    # 更新 graph.yaml
                    if "questions" not in graph._data:
                        graph._data["questions"] = {}
                    graph._data["questions"][entity_name] = questions
                    
                    # 保存
                    graph.save()
                    
                    return True
        
        return False
    
    except Exception as e:
        print(f"Error applying question suggestion: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="自动发现")
    parser.add_argument("--show-suggestions", action="store_true", help="显示建议")
    parser.add_argument("--apply", action="store_true", help="应用建议")
    parser.add_argument("--apply-company", type=str, help="应用指定公司建议")
    parser.add_argument("--apply-topic", type=str, help="应用指定主题建议")
    parser.add_argument("--apply-question", type=str, help="应用指定问题建议")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 自动发现")
    print("=" * 50)
    
    if args.show_suggestions:
        # 显示建议
        suggestions = load_suggestions()
        
        print(f"\n公司建议 ({len(suggestions['companies'])}个):")
        for s in suggestions['companies'][:10]:
            print(f"  - {s['name']} (出现{s['news_count']}次)")
            print(f"    {s['context'][:80]}...")
        
        print(f"\n主题建议 ({len(suggestions['topics'])}个):")
        for s in suggestions['topics'][:10]:
            print(f"  - {s['topic_name']} (出现{s['news_count']}次)")
            if s['related_companies']:
                print(f"    相关公司: {', '.join(s['related_companies'][:3])}")
        
        print(f"\n问题建议 ({len(suggestions['questions'])}个):")
        for s in suggestions['questions'][:10]:
            print(f"  - [{s['entity_name']}] {s['question']}")
        
        return
    
    if args.apply_company:
        # 应用公司建议
        suggestions = load_suggestions()
        graph = Graph()
        
        for s in suggestions['companies']:
            if s['name'] == args.apply_company:
                if apply_company_suggestion(s, graph):
                    print(f"Applied company suggestion: {args.apply_company}")
                else:
                    print(f"Failed to apply company suggestion: {args.apply_company}")
                break
        else:
            print(f"Company suggestion not found: {args.apply_company}")
        
        return
    
    if args.apply_topic:
        # 应用主题建议
        suggestions = load_suggestions()
        graph = Graph()
        
        for s in suggestions['topics']:
            if s['topic_name'] == args.apply_topic:
                if apply_topic_suggestion(s, graph):
                    print(f"Applied topic suggestion: {args.apply_topic}")
                else:
                    print(f"Failed to apply topic suggestion: {args.apply_topic}")
                break
        else:
            print(f"Topic suggestion not found: {args.apply_topic}")
        
        return
    
    if args.apply_question:
        # 应用问题建议
        suggestions = load_suggestions()
        graph = Graph()
        
        for s in suggestions['questions']:
            if s['question'] == args.apply_question:
                if apply_question_suggestion(s, graph):
                    print(f"Applied question suggestion: {args.apply_question}")
                else:
                    print(f"Failed to apply question suggestion: {args.apply_question}")
                break
        else:
            print(f"Question suggestion not found: {args.apply_question}")
        
        return
    
    # 运行发现
    print("\n扫描新闻文件...")
    
    # 获取新闻文件
    news_files = []
    for company_dir in (WIKI_ROOT / "companies").iterdir():
        if company_dir.is_dir() and not company_dir.name.startswith("_"):
            news_dir = company_dir / "raw" / "news"
            if news_dir.exists():
                news_files.extend(news_dir.glob("*.md"))
    
    print(f"Found {len(news_files)} news files")
    
    # 获取已知公司和主题
    graph = Graph()
    known_companies = set(c["name"] for c in graph.get_all_companies())
    known_topics = set(graph.get_all_sectors())
    
    print(f"Known companies: {len(known_companies)}")
    print(f"Known topics: {len(known_topics)}")
    
    # 发现新公司
    print("\n发现新公司...")
    company_suggestions = discover_new_companies(news_files, known_companies)
    print(f"Found {len(company_suggestions)} company suggestions")
    
    # 发现新主题
    print("\n发现新主题...")
    topic_suggestions = discover_new_topics(news_files, known_topics)
    print(f"Found {len(topic_suggestions)} topic suggestions")
    
    # 建议新问题
    print("\n建议新问题...")
    question_suggestions = suggest_new_questions(news_files, graph)
    print(f"Found {len(question_suggestions)} question suggestions")
    
    # 保存建议
    suggestions_file = save_suggestions(company_suggestions, topic_suggestions, question_suggestions)
    print(f"\nSuggestions saved to: {suggestions_file}")
    
    # 显示摘要
    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)
    print(f"Company suggestions: {len(company_suggestions)}")
    print(f"Topic suggestions: {len(topic_suggestions)}")
    print(f"Question suggestions: {len(question_suggestions)}")
    print("\nUse --show-suggestions to view details")
    print("Use --apply-company/--apply-topic/--apply-question to apply")


if __name__ == "__main__":
    main()