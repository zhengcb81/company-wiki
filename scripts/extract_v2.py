#!/usr/bin/env python3
"""
extract_v2.py — 内容提取模块（v2，LLM驱动简化版）

核心设计变更：
- 删除硬编码的分句打分取top3逻辑（交给LLM做理解）
- 保留文本清洗（去HTML标签、去噪音行）——这是确定性的前置处理
- 保留来源类型判断（根据文件名/关键词）
- 新增：简单的文本截断（供LLM prompt使用）

用法：
    from extract_v2 import clean_text, classify_source, truncate_for_llm
    cleaned = clean_text(raw_text)
    source_type = classify_source(filename)
    chunks = truncate_for_llm(cleaned, max_chars=30000)
"""

import re
import sys
from pathlib import Path
from typing import List


# ── 噪音模式 ──────────────────────────
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


def clean_text(text: str) -> str:
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


def classify_source(filename: str, content_preview: str = "") -> str:
    """
    根据文件名判断来源类型。
    """
    name = filename.lower()

    # PDF 类型判断
    if any(kw in name for kw in ["年报", "年度报告"]):
        return "annual_report"
    elif any(kw in name for kw in ["半年报", "半年度报告"]):
        return "semi_annual_report"
    elif any(kw in name for kw in ["季报", "季度报告", "一季度", "二季度", "三季度", "四季度"]):
        return "quarterly_report"
    elif any(kw in name for kw in ["招股"]):
        return "prospectus"
    elif any(kw in name for kw in ["投资者关系", "调研", "交流", "投资者活动"]):
        return "investor_relations"
    elif any(kw in name for kw in ["研报", "深度", "首次覆盖", "点评"]):
        return "research_report"
    elif any(kw in name for kw in ["公告", "通知", "决议", "提示", "预案", "并购", "收购", "定增", "增发", "股权激励", "重大资产重组"]):
        return "announcement"

    # Markdown 类型判断（根据 frontmatter 或内容）
    if content_preview:
        if "type: news" in content_preview:
            return "news"
        elif "type: report" in content_preview:
            return "report"

    return "unknown"


def truncate_for_llm(text: str, max_chars: int = 30000) -> List[str]:
    """
    将文本截断为适合 LLM 处理的块。
    优先在段落边界处分割。
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para

    if current:
        chunks.append(current.strip())

    return chunks


def extract_frontmatter(text: str) -> tuple:
    """
    从 markdown 文本中提取 YAML frontmatter。
    返回: (frontmatter_dict, body_text)
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end < 0:
        return {}, text

    front_text = text[3:end].strip()
    body = text[end + 3:]

    front = {}
    for line in front_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            front[key.strip()] = val.strip().strip('"').strip("'")

    return front, body


# ── CLI ───────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="内容提取（v2 简化版）")
    parser.add_argument("file", nargs="?", help="要分析的文件路径")
    parser.add_argument("--text", type=str, help="直接分析文本")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        content = Path(args.file).read_text(encoding="utf-8", errors="replace")
        front, body = extract_frontmatter(content)
        text = body
    else:
        parser.print_help()
        sys.exit(1)

    cleaned = clean_text(text)
    print(f"原始长度: {len(text)} 字符")
    print(f"清洗后: {len(cleaned)} 字符")
    print(f"\n前500字符:\n{cleaned[:500]}")


if __name__ == "__main__":
    main()
