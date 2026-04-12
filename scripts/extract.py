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


# ── 噪音模式 ──────────────────────────────
NOISE_PATTERNS = [
    # 导航/菜单
    r'^#{1,6}\s*(关于|产品|支持|联系|服务|首页|导航|菜单|公司简介|版权所有)',
    r'^#{1,6}\s*(Company|Products|Support|Contact|About|Menu|Navigation)',
    r'^#+\s*-+\s*[▲▼↑↓]?\s*$',
    # 网站元素
    r'(登录|注册|搜索|订阅|分享|收藏|点赞|评论区|版权所有|版权声明)',
    r'(Copyright|All rights reserved|Terms of Service|Privacy Policy)',
    r'(备案号|ICP备|增值电信|互联网新闻信息服务)',
    r'(粤公网安备|京ICP|沪ICP)',
    # 股票行情页特有
    r'^\|?\s*(开盘价|昨收盘|最高|最低|换手率|振幅|成交额|市盈率|市净率)',
    r'^\|?\s*(日期|两融余额|融资余额|环比|占流通市值)',
    r'^\|?\s*(Open|High|Low|Close|Volume|Turnover)',
    # 重复分隔符
    r'^[\s\-_=*#]{10,}$',
    r'^[\|:\s]+$',  # 纯表格分隔行
    # 杂项
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
