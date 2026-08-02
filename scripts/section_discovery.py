#!/usr/bin/env python3
"""
section_discovery.py — 章节发现模块

从PDF提取的文本中识别章节结构。
支持多种章节标题格式：
- "第X节 标题"
- "第X章 标题"
- "一、标题"
- "（一）标题"
- "1. 标题"
"""

import re
from typing import List, Dict, Optional


# 章节标题正则模式（按优先级排序）
SECTION_PATTERNS = [
    # "第X节 标题" 或 "第X章 标题"（只匹配主要章节，不匹配子章节）
    (r"^\s*(第[一二三四五六七八九十百千]+[节章])\s+(.+?)(?:\n|$)", "numbered"),
    # "一、标题"（只匹配主要章节）
    (r"^\s*([一二三四五六七八九十]+)、(.+?)(?:\n|$)", "chinese_numbered"),
    # "（一）标题"（子章节）
    (r"^\s*（([一二三四五六七八九十]+)）(.+?)(?:\n|$)", "parenthesized"),
]


def discover_sections(text: str) -> List[Dict]:
    """
    从文本中发现章节结构。

    Args:
        text: 提取的文档文本

    Returns:
        章节列表 [{"number": "六", "title": "业务与技术", "position": 12345}, ...]
    """
    sections = []
    seen = set()

    for pattern, pattern_type in SECTION_PATTERNS:
        # 使用re.MULTILINE让^匹配每行开头
        for match in re.finditer(pattern, text, re.MULTILINE):
            number = match.group(1).strip()
            title = match.group(2).strip()

            # 去重（同一章节可能被多个模式匹配）
            key = f"{number}|{title}"
            if key in seen:
                continue
            seen.add(key)

            # 过滤噪音
            if not _is_valid_section_title(title, pattern_type):
                continue

            sections.append(
                {
                    "number": number,
                    "title": title,
                    "position": match.start(),
                    "raw_text": match.group(0),
                }
            )

    # 按位置排序
    sections.sort(key=lambda x: x["position"])

    return sections


def match_section_type(section_title: str, section_types: Dict) -> Optional[str]:
    """
    匹配章节类型。

    Args:
        section_title: 章节标题
        section_types: 章节类型定义 {"business": {"patterns": [...]}, ...}

    Returns:
        匹配的章节类型，或None
    """
    for section_type, config in section_types.items():
        patterns = config.get("patterns", [])
        for pattern in patterns:
            if pattern in section_title:
                return section_type
    return None


def _is_valid_section_title(title: str, pattern_type: str) -> bool:
    """
    验证是否是有效的章节标题（过滤噪音）。
    """
    # 标题通常不超过50字
    if len(title) > 50:
        return False

    # 标题通常不含句号、分号等标点
    if re.search(r"[。；！]", title):
        return False

    # 标题不应以数字开头（除非是"第X节"格式）
    if pattern_type != "numbered" and re.match(r"^\d", title):
        return False

    # 对于数字编号模式，需要额外验证
    if pattern_type == "digit_numbered":
        # 过滤掉表格中的数字（如"2024年营收123.45亿元"）
        if re.search(r"\d{4}年", title):
            return False
        # 过滤掉财务数据（如"123.45亿元"）
        if re.search(r"\d+\.?\d*[亿万]", title):
            return False
        # 过滤掉百分比
        if re.search(r"\d+\.?\d*%", title):
            return False

    # 对于"第X节"和"一、"格式，需要额外验证
    if pattern_type in ["numbered", "chinese_numbered"]:
        # 过滤掉包含大量数字的行（通常是财务数据）
        digit_count = sum(c.isdigit() for c in title)
        if digit_count > len(title) * 0.2:  # 数字占比超过20%
            return False
        # 过滤掉包含逗号的行（通常是财务数据）
        if "," in title:
            return False
        # 过滤掉包含小数点的行（通常是财务数据）
        if "." in title and re.search(r"\d+\.\d+", title):
            return False
        # 过滤掉太短的标题（可能是噪音）
        if len(title) < 4:
            return False
        # 过滤掉包含页码标记（如".......... 76"）
        if re.search(r"\.{4,}", title):
            return False

    return True


def get_section_content(
    text: str, section: Dict, next_section: Optional[Dict] = None
) -> str:
    """
    获取指定章节的内容。

    Args:
        text: 完整文档文本
        section: 当前章节信息
        next_section: 下一个章节信息（可选）

    Returns:
        章节内容文本
    """
    start = section["position"]
    if next_section:
        end = next_section["position"]
    else:
        end = len(text)

    return text[start:end]


def find_sections_by_type(
    sections: List[Dict], section_types: Dict, target_type: str
) -> List[Dict]:
    """
    根据类型查找章节。

    Args:
        sections: 章节列表
        section_types: 章节类型定义
        target_type: 目标类型

    Returns:
        匹配的章节列表
    """
    matched = []
    for section in sections:
        section_type = match_section_type(section["title"], section_types)
        if section_type == target_type:
            matched.append(section)
    return matched


# 测试代码
if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # 默认测试文件
        filepath = "companies/中微公司/extracts/prospectus/中微半导体招股说明书.md"

    print(f"测试章节发现: {filepath}")
    print("=" * 60)

    content = Path(filepath).read_text(encoding="utf-8")

    # 跳过frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :]

    sections = discover_sections(content)

    print(f"\n发现 {len(sections)} 个章节:")
    for i, sec in enumerate(sections[:20]):  # 只显示前20个
        print(f"  {i + 1}. 第{sec['number']}节 {sec['title']} (pos: {sec['position']})")

    if len(sections) > 20:
        print(f"  ... 还有 {len(sections) - 20} 个章节")
