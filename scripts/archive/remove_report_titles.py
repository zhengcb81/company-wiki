#!/usr/bin/env python3
"""
remove_report_titles.py — 清理纯财报标题条目

移除那些只是报告文件名（如"飞龙股份:2025年半年度报告摘要"）
却没有从报告中提取任何实际数据或分析的条目。

这类条目的特征：
- 标题包含 "年度报告/半年度报告/季度报告/年报/半年报/季报/投资者关系/招股书"
- 要点只是重复标题或极短的报告类型描述
- 没有从报告中提取的财务数据、业务分析或关键指标

用法：
    python3 scripts/remove_report_titles.py                # dry-run
    python3 scripts/remove_report_titles.py --execute       # 实际执行
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# 报告标题关键词
REPORT_KEYWORDS = [
    '年度报告', '半年度报告', '季度报告', '年度摘要',
    '半年度摘要', '季度摘要', '投资者关系', '投资者问答',
    '招股说明书', '募集说明书', '审计报告',
    '年报摘要', '半年报摘要', '季报摘要',
    '年度报告摘要', '半年度报告摘要',
]

# 要保留的报告类型关键词（这些是有数据的实质性财报条目）
SUBSTANTIVE_PATTERNS = [
    r'\d+\.?\d*\s*(亿|万|%|元)',       # 含具体数字
    r'(营收|净利润|毛利率|净利率|ROE|EPS)',  # 财务指标
    r'(同比增长|环比增长|下降|增长)',      # 趋势描述
    r'(出货量|产能|订单|市占率)',          # 运营数据
]


def is_report_title_entry(entry_text):
    """
    判断一个条目是否是纯财报标题条目（无实际数据提取）。
    返回 True 如果：
    1. 标题包含报告关键词
    2. 且要点中没有具体财务数据
    """
    lines = entry_text.strip().split('\n')
    if not lines:
        return True

    header = lines[0]
    header_match = re.match(r'###\s+\d{4}-\d{2}-\d{2}\s*\|[^|]+\|\s*(.+?)\s*$', header)
    if not header_match:
        return False
    title = header_match.group(1).strip()

    # 检查标题是否包含报告关键词
    has_report_keyword = any(kw in title for kw in REPORT_KEYWORDS)
    if not has_report_keyword:
        return False

    # 提取要点
    points = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith('- [来源]'):
            continue
        if stripped.startswith('- '):
            points.append(stripped[2:].strip())
        else:
            points.append(stripped)

    if not points:
        return True  # 没有要点

    # 检查要点中是否有实质性数据
    all_points_text = ' '.join(points)
    for pattern in SUBSTANTIVE_PATTERNS:
        if re.search(pattern, all_points_text):
            return False  # 有数据，不是纯标题

    # 要点中没有数据，检查是否要点只是标题的重复
    for point in points:
        point_clean = point.strip().rstrip('。.!')
        if len(point_clean) > 20 and point_clean != title:
            return False  # 有不同于标题的内容

    return True  # 纯报告标题条目


def parse_timeline_entries(wiki_text):
    """解析时间线条目"""
    entries = []
    timeline_pos = wiki_text.find("## 时间线")
    if timeline_pos < 0:
        return entries, timeline_pos, ""

    timeline_section = wiki_text[timeline_pos:]
    next_section = re.search(r'\n## (?!时间线)', timeline_section)
    after_timeline = ""
    if next_section:
        after_timeline = wiki_text[timeline_pos + next_section.start():]
        timeline_section = timeline_section[:next_section.start()]

    parts = re.split(r'\n(?=### )', timeline_section)
    for part in parts:
        if part.strip().startswith('###'):
            entries.append(part)

    return entries, timeline_pos, after_timeline


def clean_wiki_page(wiki_path, dry_run=True):
    """清理单个 wiki 页面"""
    if not wiki_path.exists():
        return 0, 0, 0

    wiki_text = wiki_path.read_text(encoding="utf-8")
    result = parse_timeline_entries(wiki_text)
    if len(result) == 2:
        return 0, 0, 0
    entries, timeline_pos, after_timeline = result

    if timeline_pos < 0 or not entries:
        return 0, 0, 0

    kept = []
    removed = 0

    for entry in entries:
        if is_report_title_entry(entry):
            removed += 1
        else:
            kept.append(entry)

    if dry_run or removed == 0:
        return len(entries), len(kept), removed

    new_timeline = "## 时间线\n\n"
    if kept:
        new_timeline += "\n".join(kept) + "\n"
    else:
        new_timeline += "（暂无条目）\n\n"

    new_wiki = wiki_text[:timeline_pos] + new_timeline + "\n" + after_timeline

    new_wiki = re.sub(
        r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
        f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
        new_wiki
    )
    old_count = re.search(r'sources_count: (\d+)', new_wiki)
    if old_count:
        new_wiki = new_wiki.replace(
            f"sources_count: {old_count.group(1)}",
            f"sources_count: {len(kept)}"
        )

    wiki_path.write_text(new_wiki, encoding="utf-8")
    return len(entries), len(kept), removed


def main():
    parser = argparse.ArgumentParser(description="清理纯财报标题条目")
    parser.add_argument("--execute", action="store_true", help="实际执行")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("  财报标题条目清理工具")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    grand_total = 0
    grand_kept = 0
    grand_removed = 0
    affected = 0

    for pattern_dir in ["companies", "sectors", "themes"]:
        base = WIKI_ROOT / pattern_dir
        if not base.exists():
            continue
        for wiki_dir in base.glob("*/wiki"):
            for md_file in sorted(wiki_dir.glob("*.md")):
                total, kept, removed = clean_wiki_page(md_file, dry_run)
                if removed > 0:
                    rel = md_file.relative_to(WIKI_ROOT)
                    pct = removed * 100 // max(total, 1)
                    status = "REMOVED" if not dry_run else "WOULD REMOVE"
                    print(f"  [{status}] {rel}: {removed}/{total} ({pct}%)")
                    affected += 1
                    grand_total += total
                    grand_kept += kept
                    grand_removed += removed

    print(f"\n{'=' * 60}")
    print(f"  Total: {grand_total} entries, {grand_kept} kept, {grand_removed} report titles removed")
    print(f"  Affected files: {affected}")
    if dry_run:
        print(f"  Use --execute to actually remove")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
