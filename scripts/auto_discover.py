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
from common import WIKI_ROOT

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


def extract_company_names(text: str, llm_client=None) -> List[str]:
    """
    从文本中提取公司名称（LLM 驱动）

    Args:
        text: 文本
        llm_client: LLM 客户端（可选，如果提供则使用 LLM 提取）

    Returns:
        公司名称列表
    """
    # 如果有 LLM 客户端，使用 LLM 提取（更准确）
    if llm_client and llm_client.available:
        try:
            return _extract_company_names_with_llm(text, llm_client)
        except Exception:
            pass  # LLM 失败时回退到正则

    # 回退：使用正则提取（保留原有逻辑但增强过滤）
    return _extract_company_names_with_regex(text)


def _extract_company_names_with_llm(text: str, llm_client) -> List[str]:
    """使用 LLM 从文本中提取公司名称"""
    # 截断文本避免过长
    text = text[:3000]

    prompt = f"""请从以下新闻文本中提取所有提到的公司（或机构）名称。

要求：
- 只提取真正的公司/机构名，不要提取"上市公司"、"该公司"等通用词
- 不要提取"该指标侧面反映出一家公司"等 boilerplate 中的公司名
- 不要提取职位（如 CEO、CFO）
- 返回标准公司全称或常用简称
- 如果文本中没有提到具体公司，返回空列表

文本：
{text[:2000]}

请以 JSON 格式回复：
{{"companies": ["公司名1", "公司名2"]}}

只输出 JSON。"""

    response = llm_client.chat_with_retry(
        prompt,
        "你是一个信息提取专家。只输出JSON。",
    )

    if response.success:
        import json

        result = json.loads(response.content.strip())
        companies = result.get("companies", [])
        # 过滤噪声
        noise = {
            "该指标侧面反映出一家公司",
            "上市公司",
            "该公司",
            "公司",
            "股份有限公司",
            "有限责任公司",
        }
        return [c for c in companies if c not in noise and len(c) >= 2]

    return []


def _extract_company_names_with_regex(text: str) -> List[str]:
    """使用正则提取公司名称（增强版）"""
    # 噪声词黑名单
    _NOISE_PHRASES = {
        "归属于上市公司",
        "公开发行证券的公司",
        "该指标侧面反映出一家公司",
        "市净率是公司",
        "每股收益是公司",
        "每股净资产是公司",
        "请问公司",
        "公司拟",
        "公司决定",
        "公司认为",
        "公司预计",
        "公司公告",
        "公司股票",
        "公司债券",
        "公司治理",
        "上市公司",
        "股份有限公司",
        "有限责任公司",
        "公司简称",
        "公司全称",
        "公司名称",
        "公司代码",
        "公司现有",
        "公司目前",
        "公司未来",
        "公司计划",
        "公司营收",
        "公司利润",
        "公司股价",
        "公司市值",
        "公司业务",
        "公司产品",
        "公司技术",
        "公司研发",
        "公司客户",
        "公司订单",
        "公司产能",
        "公司业绩",
        "公开发行证券",
        "证券投资基金",
        "证券投资",
        "基金管理",
        "资产管理",
        "投资管理",
        "投资咨询",
        "投资有限",
        "有限合伙",
        "合伙企业",
        "企业集团",
        "控股有限",
        "控股股份",
        "控股科技",
        "控股电子",
    }

    _NOISE_CAPS = {
        "CEO",
        "CFO",
        "CTO",
        "COO",
        "HTTP",
        "HTTPS",
        "HTML",
        "CSS",
        "JSON",
        "XML",
        "API",
        "SDK",
        "PDF",
        "DOC",
        "XLS",
        "PPT",
        "USA",
        "CNY",
        "USD",
        "RMB",
        "GDP",
        "IPO",
        "ROE",
        "ROA",
        "EPS",
        "PE",
        "PB",
        "AI",
        "IT",
        "OK",
        "NO",
        "GO",
        "TO",
        "BY",
        "AT",
        "IS",
        "IN",
        "ON",
        "AS",
        "OR",
        "INC",
        "LTD",
        "CORP",
        "PLC",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "FY",
        "H1",
        "H2",
        "YTD",
        "QOQ",
        "YOY",
    }

    # 公司名称模式
    patterns = [
        r"[\u4e00-\u9fff]{2,}(?:集团|股份|科技|电子|半导体|光电|微电子|集成电路|仪器|精密|新材|材料|化学|制药|生物|能源|环保|智能|机器人|通信|网络|软件|数据|云|计算|芯片|存储|显示|照明|电池|新能源|汽车|装备|机械|重工|航空|航天|船舶|钢铁|矿业|地产|金融|银行|保险|证券|基金|期货|信托|租赁|担保|典当)",
        r"[A-Z][a-zA-Z]{2,}(?:\s+(?:Inc|Corp|Ltd|Co|Technologies|Semiconductor|Electronics|Systems|Solutions|Group|Holdings|Capital|Partners|Associates|International|Global|Digital|Networks|Software|Services))",
        r"[\u4e00-\u9fff]{2,}(?:跳动|小红书|大疆|美团|快手|滴滴|拼多多|京东|阿里|腾讯|百度|华为|小米|比亚迪|宁德时代|中芯|华虹|长电|通富|晶方|寒武纪|海光|景嘉微|龙芯|飞腾|兆芯|申威|紫光|长江存储|合肥长鑫|士兰微|华润微|斯达半导|闻泰|韦尔|卓胜微|圣邦|思瑞浦|芯原|芯朋微|晶晨|乐鑫|瑞芯微|全志|翱捷|芯海|兆易创新|北京君正|澜起|聚辰|普冉|东芯|恒烁|佰维|江波龙|群联|慧荣|联咏|瑞昱|敦南|致新|矽力杰|天钰|晶豪|力旺|旺宏|华邦|南亚科|华亚科)",
        r"(?:中微|中芯|中兴|中环|中颖|中颖电子|中科创达|中际旭创|中科曙光|中科星图|中望软件|中微公司)",
        r"(?:北方华创|拓荆科技|华海清科|盛美上海|芯源微|至纯科技|精测电子|赛腾股份|万业企业|凯世通|华峰测控|长川科技|联动科技|金海通|耐科装备|富乐德|芯碁微装|大族数控|德龙激光|帝尔激光|迈为股份|捷佳伟创|拉普拉斯|奥特维|京运通|晶盛机电|天通股份|连城数控)",
        r"\b\d{6}\.(?:SZ|SH|BJ)\b",
    ]

    companies = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            m = m.strip()
            if (
                not m
                or len(m) < 2
                or m in _NOISE_PHRASES
                or (m.isupper() and m in _NOISE_CAPS)
            ):
                continue
            if m.replace(".", "").isdigit():
                continue
            companies.add(m)

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


def discover_new_companies(
    news_files: List[Path], known_companies: Set[str], llm_client=None
) -> List[CompanySuggestion]:
    """
    从新闻中发现新公司（LLM 增强版）

    Args:
        news_files: 新闻文件列表
        known_companies: 已知公司集合
        llm_client: LLM 客户端（可选）

    Returns:
        公司建议列表
    """
    company_mentions = Counter()
    company_contexts = {}

    for news_file in news_files:
        try:
            content = news_file.read_text(encoding="utf-8", errors="ignore")

            # 提取公司名称（优先使用 LLM）
            companies = extract_company_names(content, llm_client)

            for company in companies:
                if company not in known_companies:
                    company_mentions[company] += 1

                    # 保存上下文
                    if company not in company_contexts:
                        idx = content.find(company)
                        if idx >= 0:
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(company) + 50)
                            context = content[start:end].replace("\n", " ")
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


def discover_new_topics(
    news_files: List[Path], known_topics: Set[str]
) -> List[TopicSuggestion]:
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
            content = news_file.read_text(encoding="utf-8", errors="ignore")

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
        {"pattern": r"国产化率.*?达到.*?(\d+)%", "template": "国产化率达到{}%"},
        {"pattern": r"产能.*?提升.*?(\d+)%", "template": "产能提升{}%"},
        {"pattern": r"营收.*?增长.*?(\d+)%", "template": "营收增长{}%"},
        {"pattern": r"获得.*?订单", "template": "获得新订单"},
        {"pattern": r"发布.*?新品", "template": "发布新品"},
        {"pattern": r"突破.*?技术", "template": "技术突破"},
        {"pattern": r"客户.*?验证", "template": "客户验证通过"},
        {"pattern": r"量产.*?([\\u4e00-\\u9fff]+)", "template": "{}量产"},
    ]


def suggest_new_questions(
    news_files: List[Path], graph: Graph
) -> List[QuestionSuggestion]:
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
            content = news_file.read_text(encoding="utf-8", errors="ignore")

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
                    for entity_name, entity_type, _ in graph.find_related_entities(
                        content
                    ):
                        question = (
                            question_template.format(*matches)
                            if matches
                            else question_template
                        )

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
        "timestamp": __import__("datetime").datetime.now().isoformat(),
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

    with open(suggestions_file, "w", encoding="utf-8") as f:
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

    with open(suggestions_file, "r", encoding="utf-8") as f:
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
        (company_dir / "raw" / "news").mkdir(parents=True, exist_ok=True)
        (company_dir / "wiki").mkdir(parents=True, exist_ok=True)

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


def _filter_via_llm(candidates: list, known_companies: set, llm_client=None) -> list:
    """
    使用 LLM 过滤正则提取的候选列表，只保留真实公司名。

    正则提取了大量 boilerplate 文本（如"该指标侧面反映出一家公司"），
    LLM 可以从语义上判断哪些是真实的公司名称。

    Args:
        candidates: 候选列表，每项为 {"type": ..., "name": ..., "count": ...}
        known_companies: 已知公司名集合（已跟踪的）
        llm_client: LLM 客户端（可选，如果为 None 则自动获取）

    Returns:
        过滤后的候选列表（仅保留 LLM 确认的真实公司名）
    """
    if not candidates:
        return []

    if llm_client is None:
        try:
            from llm_client import get_llm_client

            llm_client = get_llm_client()
        except Exception:
            return candidates  # 回退到不过滤

    if not llm_client or not llm_client.available:
        return candidates  # LLM 不可用时回退

    # 构建候选列表文本（只传公司类型候选，排除 tech/link）
    company_candidates = [c for c in candidates if c["type"] == "company"]
    if not company_candidates:
        return candidates  # 没有公司候选可过滤

    candidate_text = "\n".join(
        f"- {c['name']} (出现{c['count']}次)"
        for c in company_candidates[:50]  # 最多 50 个
    )

    known_list = "\n".join(sorted(known_companies)[:30])

    prompt = f"""你是一个上市公司名称识别专家。以下是 wiki 文本中出现的高频词组列表。
请判断哪些是真实的公司名称（如"中微公司"、"北方华创"），哪些是通用词汇或财务术语（如"股份有限公司"、"归属于上市公司"、"市净率是公司"）。

已知已跟踪的公司:
{known_list}

候选列表:
{candidate_text}

请以 JSON 格式输出，只包含确认为真实公司名的项:
{{"valid_companies": ["公司名1", "公司名2", ...]}}

判断标准:
1. 是具体的公司名称（非通用术语、非财务 boilerplate）
2. 不是已知跟踪公司（已知列表已排除）
3. 是实际的上市公司或重要非上市公司（非虚构、非泛称）

只输出 JSON，不要其他文字。如果没有有效的公司名，输出 {{"valid_companies": []}}。"""

    try:
        response = llm_client.chat_with_retry(
            prompt,
            "你是一个专业的上市公司名称识别助手。只输出JSON。",
        )
        if response.success:
            import json

            result = json.loads(response.content.strip())
            valid_names = set(result.get("valid_companies", []))
            # 只保留 LLM 确认的公司名
            filtered = [
                c
                for c in candidates
                if c["type"] != "company" or c["name"] in valid_names
            ]
            return filtered
    except Exception as e:
        print(f"  LLM 过滤失败，回退到不过滤: {e}")

    return candidates  # 出错时回退到不过滤


def discover_from_wikis(
    graph: Graph, min_count: int = 3, top_n: int = 30, use_llm: bool = True
) -> Dict:
    """
    扫描所有 wiki 时间线，发现未跟踪的高频实体。
    """
    from collections import Counter

    NOISE = {
        "公司",
        "股份",
        "集团",
        "科技",
        "技术",
        "产品",
        "业务",
        "市场",
        "行业",
        "报告",
        "年度",
        "季度",
        "公告",
        "万元",
        "亿元",
        "同比",
        "环比",
        "增长",
        "下降",
        "增加",
        "减少",
        "其中",
        "主要",
        "相关",
        "其他",
        "进行",
        "表示",
        "认为",
        "预计",
        "关于",
        "通过",
        "根据",
        "目前",
        "未来",
        "阶段",
        "期间",
        "时间",
        "一个",
        "需要",
        "可能",
        "影响",
        "因素",
        "情况",
        "问题",
        "方面",
        "部分",
        "整体",
        "合计",
        "总计",
        "分别",
        "相应",
        "进一步",
        "持续",
        "不断",
        "已经",
        "正在",
        "完成",
        "实现",
        "达到",
        "超过",
        "接近",
        "积极",
        "有效",
        "显著",
        "明显",
        "大幅",
        "快速",
        "稳步",
        "全面",
        "系统",
        "完善",
        "加强",
        "提升",
        "优化",
        "推动",
        "促进",
        "开展",
        "实施",
        "推进",
        "落实",
        "建立",
        "形成",
        "构建",
        "打造",
        "证券",
        "研报",
        "研究所",
        # 通用公司名模式
        "有限公司",
        "股份有限公司",
        "上市公司",
        "归属于上市公司",
        "公开发行证券的公司",
        "实现归属于上市公司",
        "为全面了解本公司",
        "除同公司",
        # 银行/金融机构
        "中国工商银行股份",
        "中国建设银行股份",
        "香港中央结算有限公司",
        # 后缀
        "科技股份",
        "电子股份",
        "半导体股份",
        "集团股份",
    }

    tracked = set()
    for comp in graph.get_all_companies():
        tracked.add(comp["name"])
        for a in graph._data.get("nodes", {}).get(comp["name"], {}).get("aliases", []):
            tracked.add(a)
    for sector in graph.get_all_sectors():
        tracked.add(sector)
    for node_name, node_data in graph._data.get("nodes", {}).items():
        tracked.add(node_name)
        for kw in node_data.get("keywords", []):
            tracked.add(kw)
    tracked = {t.lower() for t in tracked if t}

    all_candidates = Counter()
    wiki_count = 0

    for pattern in ["companies/*/wiki/*.md", "sectors/*/wiki/*.md"]:
        for wiki in WIKI_ROOT.glob(pattern):
            if "_slides" in wiki.name:
                continue
            try:
                content = wiki.read_text(encoding="utf-8")
                # 去掉 frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2]
                wiki_count += 1

                # 提取公司名称候选
                for m in re.finditer(
                    r"[\u4e00-\u9fff]{2,8}(?:公司|股份|集团|科技|半导体|电子|微电|光电|通信)",
                    content,
                ):
                    name = m.group(0)
                    if len(name) >= 4 and name not in NOISE:
                        all_candidates[("company", name)] += 1

                # 提取技术术语
                for m in re.finditer(r"\b[A-Z]{2,6}\d?\b", content):
                    name = m.group(0)
                    if name not in NOISE and len(name) >= 2:
                        all_candidates[("tech", name)] += 1

                # 提取 wikilink
                for m in re.finditer(r"\[\[([^\]]+)\]\]", content):
                    link = m.group(1).split("/")[-1]
                    if link and link not in NOISE and len(link) >= 2:
                        all_candidates[("link", link)] += 1
            except Exception:
                continue

    discovered = []
    for (etype, name), count in all_candidates.most_common(top_n * 3):
        if count < min_count:
            continue
        normalized = name.lower().strip()
        if normalized in tracked:
            continue
        # 子串检查
        is_sub = False
        for t in tracked:
            if normalized in t or t in normalized:
                if abs(len(normalized) - len(t)) < 3:
                    is_sub = True
                    break
        if is_sub:
            continue
        discovered.append({"type": etype, "name": name, "count": count})
        if len(discovered) >= top_n:
            break

    # LLM 过滤：让 LLM 确认哪些是真实的公司名
    if use_llm and discovered:
        tracked_names = set()
        for comp in graph.get_all_companies():
            tracked_names.add(comp["name"])
        discovered = _filter_via_llm(discovered, tracked_names)

    return {
        "discovered": discovered,
        "wiki_count": wiki_count,
        "total_candidates": len(all_candidates),
    }


def main():
    parser = argparse.ArgumentParser(description="自动发现")
    parser.add_argument("--show-suggestions", action="store_true", help="显示建议")
    parser.add_argument("--apply", action="store_true", help="应用建议")
    parser.add_argument("--apply-company", type=str, help="应用指定公司建议")
    parser.add_argument("--apply-topic", type=str, help="应用指定主题建议")
    parser.add_argument("--apply-question", type=str, help="应用指定问题建议")
    parser.add_argument(
        "--from-wikis", action="store_true", help="从 wiki 时间线扫描（而非新闻）"
    )
    parser.add_argument("--min-count", type=int, default=3, help="最少出现次数")
    parser.add_argument("--top-n", type=int, default=30, help="最多报告数量")
    parser.add_argument("--report", action="store_true", help="生成 markdown 报告")
    parser.add_argument(
        "--no-llm", action="store_true", help="禁用 LLM 过滤（仅使用正则）"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  上市公司知识库 — 自动发现")
    print("=" * 50)

    if args.from_wikis:
        graph = Graph()
        result = discover_from_wikis(
            graph, min_count=args.min_count, top_n=args.top_n, use_llm=not args.no_llm
        )

        print(f"\n扫描了 {result['wiki_count']} 个 wiki 页面")
        print(f"提取了 {result['total_candidates']} 个候选实体")
        print(f"\n高频未跟踪实体（前 {len(result['discovered'])} 个）:\n")

        type_labels = {"company": "公司", "tech": "技术", "link": "链接"}
        for item in result["discovered"][:20]:
            tlabel = type_labels.get(item["type"], item["type"])
            print(f"  [{tlabel}] {item['name']} — 出现 {item['count']} 次")

        if args.report:
            report_path = WIKI_ROOT / "auto_discover_report.md"
            lines = [
                "# 自动发现报告",
                "",
                f"> 扫描 wiki 数: {result['wiki_count']}",
                f"> 候选实体数: {result['total_candidates']}",
                f"> 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "## 高频未跟踪实体",
                "",
                "| 类型 | 实体名 | 出现次数 | 建议操作 |",
                "|------|--------|----------|----------|",
            ]
            for item in result["discovered"]:
                tlabel = type_labels.get(item["type"], item["type"])
                if item["type"] == "company":
                    action = "建议添加到 graph.yaml 公司列表"
                elif item["type"] == "tech":
                    action = "建议创建 concept 页面或添加到行业 keywords"
                else:
                    action = "建议检查是否需要创建对应 wiki 页面"
                lines.append(
                    f"| {tlabel} | {item['name']} | {item['count']} | {action} |"
                )
            lines.extend(
                [
                    "",
                    "## 建议后续行动",
                    "",
                    "1. 审查上表中的公司名，确认是否需要添加到跟踪列表",
                    "2. 技术/产品术语考虑创建 `concept` 类型页面",
                    "3. wikilink 提及的未跟踪页面考虑补充内容",
                    "",
                ]
            )
            report_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"\n报告已保存: {report_path}")
            from log_writer import append_log

            append_log("lint", f"自动发现: {len(result['discovered'])} 个未跟踪实体")

        print("\n" + "=" * 50)
        return

    if args.show_suggestions:
        suggestions = load_suggestions()
        print(f"\n公司建议 ({len(suggestions['companies'])}个):")
        for s in suggestions["companies"][:10]:
            print(f"  - {s['name']} (出现{s['news_count']}次)")
            print(f"    {s['context'][:80]}...")
        print(f"\n主题建议 ({len(suggestions['topics'])}个):")
        for s in suggestions["topics"][:10]:
            print(f"  - {s['topic_name']} (出现{s['news_count']}次)")
            if s["related_companies"]:
                print(f"    相关公司: {', '.join(s['related_companies'][:3])}")
        print(f"\n问题建议 ({len(suggestions['questions'])}个):")
        for s in suggestions["questions"][:10]:
            print(f"  - [{s['entity_name']}] {s['question']}")
        return

    if args.apply_company:
        suggestions = load_suggestions()
        graph = Graph()
        for s in suggestions["companies"]:
            if s["name"] == args.apply_company:
                if apply_company_suggestion(s, graph):
                    print(f"Applied company suggestion: {args.apply_company}")
                else:
                    print(f"Failed to apply company suggestion: {args.apply_company}")
                break
        else:
            print(f"Company suggestion not found: {args.apply_company}")
        return

    if args.apply_topic:
        suggestions = load_suggestions()
        graph = Graph()
        for s in suggestions["topics"]:
            if s["topic_name"] == args.apply_topic:
                if apply_topic_suggestion(s, graph):
                    print(f"Applied topic suggestion: {args.apply_topic}")
                else:
                    print(f"Failed to apply topic suggestion: {args.apply_topic}")
                break
        else:
            print(f"Topic suggestion not found: {args.apply_topic}")
        return

    if args.apply_question:
        suggestions = load_suggestions()
        graph = Graph()
        for s in suggestions["questions"]:
            if s["question"] == args.apply_question:
                if apply_question_suggestion(s, graph):
                    print(f"Applied question suggestion: {args.apply_question}")
                else:
                    print(f"Failed to apply question suggestion: {args.apply_question}")
                break
        else:
            print(f"Question suggestion not found: {args.apply_question}")
        return

    # 默认运行：从新闻文件扫描
    print("\n扫描新闻文件...")
    news_files = []
    for company_dir in (WIKI_ROOT / "companies").iterdir():
        if company_dir.is_dir() and not company_dir.name.startswith("_"):
            news_dir = company_dir / "raw" / "news"
            if news_dir.exists():
                news_files.extend(news_dir.glob("*.md"))

    print(f"Found {len(news_files)} news files")
    graph = Graph()
    known_companies = set(c["name"] for c in graph.get_all_companies())
    known_topics = set(graph.get_all_sectors())
    print(f"Known companies: {len(known_companies)}")
    print(f"Known topics: {len(known_topics)}")

    print("\n发现新公司...")
    company_suggestions = discover_new_companies(news_files, known_companies)
    print(f"Found {len(company_suggestions)} company suggestions")

    print("\n发现新主题...")
    topic_suggestions = discover_new_topics(news_files, known_topics)
    print(f"Found {len(topic_suggestions)} topic suggestions")

    print("\n建议新问题...")
    question_suggestions = suggest_new_questions(news_files, graph)
    print(f"Found {len(question_suggestions)} question suggestions")

    suggestions_file = save_suggestions(
        company_suggestions, topic_suggestions, question_suggestions
    )
    print(f"\nSuggestions saved to: {suggestions_file}")

    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)
    print(f"Company suggestions: {len(company_suggestions)}")
    print(f"Topic suggestions: {len(topic_suggestions)}")
    print(f"Question suggestions: {len(question_suggestions)}")
    print("\nUse --show-suggestions to view details")
    print("Use --apply-company/--apply-topic/--apply-question to apply")
    print("Use --from-wikis to scan wiki timelines instead of news")


if __name__ == "__main__":
    main()
