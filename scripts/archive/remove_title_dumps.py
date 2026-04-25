#!/usr/bin/env python3
"""
remove_title_dumps.py — 清理 wiki 页面中的标题复制条目

扫描所有 wiki 页面，移除"标题复制"类型的低质量条目：
即摘要的唯一要点等于标题本身、或要点过短（<15字）的条目。

用法：
    python3 scripts/remove_title_dumps.py                    # dry-run
    python3 scripts/remove_title_dumps.py --execute           # 实际执行
    python3 scripts/remove_title_dumps.py --company 英伟达     # 只处理指定公司
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


def is_title_dump(entry_text):
    """
    判断一个时间线条目是否是"标题复制"。
    标准：
    1. 条目的非来源要点只有1条
    2. 且该要点等于标题本身（或子串）
    3. 或该要点长度<15字
    """
    lines = entry_text.strip().split('\n')
    if not lines:
        return True

    # 提取标题
    header = lines[0]  # ### date | type | title
    header_match = re.match(r'###\s+\d{4}-\d{2}-\d{2}\s*\|[^|]+\|\s*(.+?)\s*$', header)
    if not header_match:
        return False
    title = header_match.group(1).strip()

    # 提取要点（非来源、非空行）
    points = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('- [来源]') or stripped.startswith('- [来源]('):
            continue
        if stripped.startswith('- '):
            points.append(stripped[2:].strip())
        else:
            points.append(stripped)

    # 没有要点
    if not points:
        return True

    # 只有一个要点
    if len(points) == 1:
        point = points[0].rstrip('。.!,，')
        t = title.rstrip('。.!,，')
        # 要点等于标题
        if point == t or point in t or t in point:
            return True
        # 要点太短（<15字）
        if len(point) < 15:
            return True

    return False


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
    """清理单个 wiki 页面的标题复制条目"""
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
        if is_title_dump(entry):
            removed += 1
        else:
            kept.append(entry)

    if dry_run or removed == 0:
        return len(entries), len(kept), removed

    # 重建 wiki
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
    parser = argparse.ArgumentParser(description="清理标题复制条目")
    parser.add_argument("--execute", action="store_true", help="实际执行")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--sector", type=str, help="只处理指定行业")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("  标题复制条目清理工具")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    grand_total = 0
    grand_kept = 0
    grand_removed = 0
    affected = 0

    # 扫描所有 wiki 页面
    for pattern_dir in ["companies", "sectors", "themes"]:
        base = WIKI_ROOT / pattern_dir
        if not base.exists():
            continue
        for wiki_dir in base.glob("*/wiki"):
            entity_name = wiki_dir.parent.name
            if args.company and pattern_dir == "companies" and entity_name != args.company:
                continue
            if args.sector and pattern_dir == "sectors" and entity_name != args.sector:
                continue
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
    print(f"  Total: {grand_total} entries, {grand_kept} kept, {grand_removed} title dumps removed")
    print(f"  Affected files: {affected}")
    if dry_run:
        print(f"  Use --execute to actually remove")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
