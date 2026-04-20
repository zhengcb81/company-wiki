#!/usr/bin/env python3
"""
extract.py — 内容提取与摘要模块
从原始文本中清洗噪音、提取关键信息、生成结构化摘要。

用法（独立测试）：
    python3 scripts/extract.py <file.md>
    python3 scripts/extract.py --text "要分析的文本"
"""

import argparse
import re
import sys
from pathlib import Path

# ── 尝试从 config_rules.yaml 加载噪声模式 ─────────
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config_rules_loader import RulesConfig
    _rules = RulesConfig()
    NOISE_PATTERNS = _rules.get_noise_patterns()
except Exception:
    # 回退：硬编码的噪声模式（当 config_rules.yaml 不可用时）
    NOISE_PATTERNS = [
        r'^#{1,6}\s*(关于|产品|支持|联系|服务|首页|导航|菜单|公司简介|版权所有)',
        r'^#{1,6}\s*(Company|Products|Support|Contact|About|Menu|Navigation)',
        r'^#+\s*-+\s*[▲▼↑↓]?\s*$',
        r'(登录|注册|搜索|订阅|分享|收藏|点赞|评论区|版权所有|版权声明)',
        r'(Copyright|All rights reserved|Terms of Service|Privacy Policy)',
        r'(备案号|ICP备|增值电信|互联网新闻信息服务)',
        r'(粤公网安备|京ICP|沪ICP)',
        r'^\|?\s*(开盘价|昨收盘|最高|最低|换手率|振幅|成交额|市盈率|市净率)',
        r'^\|?\s*(日期|两融余额|融资余额|环比|占流通市值)',
        r'^\|?\s*(Open|High|Low|Close|Volume|Turnover)',
        r'^[\s\-_=*#]{10,}$',
        r'^[\|:\s]+$',
        r'^(更多|详情|点击|查看|进入|返回|上一页|下一页)',
        r'^(Read more|Learn more|Click here|Continue)',
        r'手机财新网|新浪财经|东方财富|雪球|格隆汇',
    ]


def clean_text(text):
    """
    清洗原始文本：移除 HTML 标签、噪音行、多余空白。
    返回清洗后的文本。
    """
    if not text:
        return ""

    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', text)

    # 移除 HTML 实体
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)

    # 处理转义字符
    text = text.replace('\\n', '\n').replace('\\t', ' ').replace('\\r', '')
    text = text.replace('\\_', '_')

    lines = text.split('\n')
    clean_lines = []

    for line in lines:
        stripped = line.strip()

        # 跳过空行
        if not stripped:
            continue

        # 检查噪音模式
        is_noise = False
        for pattern in NOISE_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                is_noise = True
                break
        if is_noise:
            continue

        # 跳过纯标点/数字的行
        if re.match(r'^[\d\s.,;:!?|+\-=/\\<>]+$', stripped):
            continue

        # 跳过过短的行（少于8个字符）
        if len(stripped) < 8:
            continue

        # 跳过来源行（由 ingest 单独处理）
        if stripped.startswith('来源:') or stripped.startswith('来源：'):
            continue
        if stripped.startswith('---'):
            continue

        clean_lines.append(stripped)

    return '\n'.join(clean_lines)


def split_sentences(text):
    """将文本分割为句子"""
    # 中英文句子分割
    sentences = re.split(r'(?<=[。！？；\n])\s*', text)
    # 也按英文句号分割（但要小心小数点）
    result = []
    for s in sentences:
        parts = re.split(r'(?<=[a-zA-Z])\.(?=\s+[A-Z])', s)
        result.extend(parts)

    # 清理
    result = [s.strip() for s in result if s.strip() and len(s.strip()) > 10]
    return result


def score_sentence(sentence):
    """
    评估句子的信息价值。分数越高越重要。
    """
    score = 0

    # 包含具体数字（金额、百分比、数量）
    if re.search(r'\d+\.?\d*\s*(亿|万|%|元|倍|年|月|日|季度|Q[1-4])', sentence):
        score += 3
    if re.search(r'\d{4}年', sentence):
        score += 2

    # 包含动作/事件关键词
    action_words = [
        '发布', '推出', '宣布', '获得', '突破', '增长', '下降', '合作',
        '收购', '投资', '融资', '上市', '签约', '中标', '获批', '实现',
        '完成', '计划', '预计', '同比', '环比', '创新', '量产',
        'launched', 'announced', 'acquired', 'grew', 'declined', 'partnered',
    ]
    for w in action_words:
        if w in sentence.lower():
            score += 2
            break

    # 包含行业关键词
    industry_words = [
        '半导体', '芯片', '刻蚀', '沉积', '晶圆', '封装', '光刻',
        '密封', '石化', '核电', '国产替代', '自主可控', '先进制程',
        '大模型', 'AI', '人工智能', '算力',
    ]
    for w in industry_words:
        if w in sentence:
            score += 1

    # 包含公司/人物名称
    if re.search(r'(公司|集团|股份|CEO|董事长|总经理|总裁)', sentence):
        score += 1

    # 长度适中的加分
    if 20 < len(sentence) < 200:
        score += 1

    # 太长的扣分（可能是杂糅文本）
    if len(sentence) > 300:
        score -= 2

    # 纯引用/问答格式扣分
    if sentence.startswith('请问') or sentence.startswith('您好'):
        score -= 1

    return score


def score_document_quality(text, title=""):
    """
    对文档整体质量进行评分。
    返回: {
        'score': 0.0-1.0,
        'grade': 'S'|'A'|'B'|'C',
        'reasons': ['reason1', ...],
        'action': 'accept'|'review'|'reject'
    }
    所有权重和阈值从 config_rules.yaml 的 quality_grading 段读取。
    """
    # 加载配置
    try:
        grading_cfg = _rules._data.get("quality_grading", {})
        weights = grading_cfg.get("weights", {})
        thresholds = grading_cfg.get("thresholds", {})
        grading = grading_cfg.get("grading", {})
    except (AttributeError, TypeError):
        weights = {}
        thresholds = {}
        grading = {}

    # 默认值
    w_numbers = weights.get("has_specific_numbers", 0.25)
    w_entities = weights.get("has_entity_names", 0.20)
    w_length = weights.get("content_length", 0.15)
    w_diversity = weights.get("sentence_diversity", 0.15)
    w_actions = weights.get("has_action_verbs", 0.10)
    w_no_noise = weights.get("no_noise_ratio", 0.15)

    t_accept = thresholds.get("accept", 0.5)
    t_review = thresholds.get("review", 0.2)

    if not text or len(text.strip()) < 20:
        return {
            "score": 0.0,
            "grade": "C",
            "reasons": ["内容过短或为空"],
            "action": "reject"
        }

    reasons = []
    dimension_scores = {}

    # 1. 具体数字检测
    has_numbers = bool(re.search(
        r'\d+\.?\d*\s*(亿|万|%|元|倍|美元|人民币|万元|亿元|Q[1-4]|mm|nm|nm|GB|TB)',
        text
    ))
    dimension_scores["has_specific_numbers"] = 1.0 if has_numbers else 0.0
    if has_numbers:
        reasons.append("含具体数据")

    # 2. 实体名称检测
    entity_patterns = [
        r'(公司|集团|股份|有限|科技|电子|半导体|芯片|设备|材料)',
        r'(NVIDIA|AMD|TSMC|Intel|Samsung|ASML)',
    ]
    has_entities = any(re.search(p, text) for p in entity_patterns)
    dimension_scores["has_entity_names"] = 1.0 if has_entities else 0.0
    if has_entities:
        reasons.append("含实体名称")

    # 3. 内容长度（归一化到 0-1）
    length_score = min(1.0, len(text) / 1000)
    dimension_scores["content_length"] = length_score
    if len(text) < 100:
        reasons.append("内容过短")

    # 4. 句子多样性
    sentences = split_sentences(clean_text(text))
    if sentences:
        unique_starts = len(set(s[:10] for s in sentences if len(s) >= 10))
        diversity = min(1.0, unique_starts / max(len(sentences), 1))
    else:
        diversity = 0.0
    dimension_scores["sentence_diversity"] = diversity
    if diversity < 0.3 and len(sentences) > 3:
        reasons.append("句子重复度高")

    # 5. 动作性动词
    action_words = [
        '发布', '推出', '宣布', '获得', '突破', '增长', '下降', '合作',
        '收购', '投资', '融资', '上市', '签约', '中标', '获批', '实现',
        'launched', 'announced', 'acquired', 'grew',
    ]
    text_lower = text.lower()
    has_actions = any(w in text_lower for w in action_words)
    dimension_scores["has_action_verbs"] = 1.0 if has_actions else 0.0
    if has_actions:
        reasons.append("含事件描述")

    # 6. 非噪声比例
    cleaned = clean_text(text)
    noise_ratio = 1.0 - (len(cleaned) / max(len(text), 1))
    dimension_scores["no_noise_ratio"] = max(0.0, 1.0 - noise_ratio)
    if noise_ratio > 0.5:
        reasons.append("噪声占比高")

    # 计算加权总分
    total_score = (
        dimension_scores.get("has_specific_numbers", 0) * w_numbers
        + dimension_scores.get("has_entity_names", 0) * w_entities
        + dimension_scores.get("content_length", 0) * w_length
        + dimension_scores.get("sentence_diversity", 0) * w_diversity
        + dimension_scores.get("has_action_verbs", 0) * w_actions
        + dimension_scores.get("no_noise_ratio", 0) * w_no_noise
    )

    # 确定等级
    s_threshold = grading.get("S", {}).get("min_score", 0.8)
    a_threshold = grading.get("A", {}).get("min_score", 0.5)
    b_threshold = grading.get("B", {}).get("min_score", 0.2)

    if total_score >= s_threshold:
        grade = "S"
    elif total_score >= a_threshold:
        grade = "A"
    elif total_score >= b_threshold:
        grade = "B"
    else:
        grade = "C"
        reasons.append("质量分过低")

    # 确定动作
    if total_score >= t_accept:
        action = "accept"
    elif total_score >= t_review:
        action = "review"
    else:
        action = "reject"

    return {
        "score": round(total_score, 3),
        "grade": grade,
        "reasons": reasons if reasons else ["无显著特征"],
        "action": action,
        "dimensions": dimension_scores
    }


def extract_summary(text, max_sentences=3):
    """
    从文本中提取摘要。
    返回: {
        'summary': '要点列表文本',
        'points': ['要点1', '要点2', ...],
        'info_type': '新闻|产品|财务|...',
        'quality': 'high|medium|low'
    }
    """
    if not text or not text.strip():
        return {
            'summary': '（无可用内容）',
            'points': [],
            'info_type': '未知',
            'quality': 'low'
        }

    # 清洗
    cleaned = clean_text(text)

    if not cleaned or len(cleaned) < 20:
        return {
            'summary': '（内容过少）',
            'points': [],
            'info_type': '未知',
            'quality': 'low'
        }

    # 分句
    sentences = split_sentences(cleaned)

    if not sentences:
        return {
            'summary': cleaned[:200],
            'points': [cleaned[:200]],
            'info_type': classify_info_type(cleaned),
            'quality': 'low'
        }

    # 评分
    scored = [(score_sentence(s), s) for s in sentences]

    # 按分数排序，取 top N
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_sentences]

    # 按原文顺序排列
    top_ordered = []
    for s in sentences:
        if any(s == t[1] for t in top):
            top_ordered.append(s)
        if len(top_ordered) >= max_sentences:
            break

    points = top_ordered if top_ordered else [sentences[0]]

    # 质量评估
    max_score = max(s[0] for s in scored) if scored else 0
    if max_score >= 5:
        quality = 'high'
    elif max_score >= 2:
        quality = 'medium'
    else:
        quality = 'low'

    # 分类
    info_type = classify_info_type(cleaned)

    summary = '\n'.join(points)

    return {
        'summary': summary,
        'points': points,
        'info_type': info_type,
        'quality': quality
    }


def classify_info_type(text):
    """判断信息类型"""
    type_patterns = {
        '财报': [r'季报', r'年报', r'营收', r'净利润', r'每股收益', r'EPS', r'earnings'],
        '产品': [r'发布', r'推出', r'新产品', r'技术突破', r'量产', r'launched'],
        '人事': [r'任命', r'辞职', r'董事长', r'CEO', r'高管', r'resigned'],
        '并购': [r'收购', r'并购', r'重组', r'资产注入', r'acquisition'],
        '合作': [r'合作', r'协议', r'合同', r'订单', r'中标', r'partnership'],
        '政策': [r'政策', r'法规', r'监管', r'补贴', r'产业政策'],
        '行情': [r'股价', r'涨停', r'跌停', r'涨\d+%', r'市值'],
    }

    for info_type, patterns in type_patterns.items():
        for p in patterns:
            if re.search(p, text):
                return info_type

    return '新闻'


def format_timeline_entry(summary_result, title, date, source_type, relative_path):
    """
    格式化为 wiki 时间线条目。
    返回 markdown 字符串。
    """
    points = summary_result['points']
    if not points:
        points = [title]

    lines = [f"### {date} | {source_type} | {title}"]
    for p in points:
        lines.append(f"- {p}")
    lines.append(f"- [来源]({relative_path})")

    return '\n'.join(lines)


# ── CLI ───────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="内容提取与摘要")
    parser.add_argument("file", nargs="?", help="要分析的文件路径")
    parser.add_argument("--text", type=str, help="直接分析文本")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        content = Path(args.file).read_text(encoding="utf-8", errors="replace")
        # 跳过 frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end+3:]
        text = content
    else:
        parser.print_help()
        sys.exit(1)

    result = extract_summary(text)
    print(f"信息类型: {result['info_type']}")
    print(f"质量评级: {result['quality']}")
    print(f"摘要:\n{result['summary']}")


if __name__ == "__main__":
    main()
