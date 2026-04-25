#!/usr/bin/env python3
"""
fix_wiki_encoding.py — 清理 wiki 页面中的编码乱码条目

扫描所有 wiki 页面的时间线条目，移除包含 GBK-as-UTF-8 乱码字符的条目。
乱码字符特征：˾ (U+02BE), ɷ (U+0277), ƾ (U+01BE), 以及其他 Latin Extended 字符。

用法：
    python3 scripts/fix_wiki_encoding.py                    # dry-run
    python3 scripts/fix_wiki_encoding.py --execute           # 实际执行
    python3 scripts/fix_wiki_encoding.py --company 中微公司   # 只处理指定公司
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# GBK-as-UTF-8 乱码特征字符
MOJIBAKE_PATTERNS = [
    '\u02be',  # ˾
    '\u0277',  # ɷ
    '\u01be',  # ƾ
    '\u02b9',  # ʹ
    '\u02b2',  # ʲ
    '\u02b7',  # ʷ
    '\u026a',  # ɪ
    '\u0282',  # ʂ
    '\u027e',  # ɾ
    '\u028a',  # ʊ
    '\u0264',  # ɤ
    '\u0261',  # ɡ
]


def has_mojibake(text):
    """检测文本是否包含乱码"""
    for ch in MOJIBAKE_PATTERNS:
        if ch in text:
            return True
    # 连续 Latin Extended 字符
    if re.search(r'[\u00c0-\u02af]{3,}', text):
        return True
    # Unicode replacement character
    if '\ufffd' in text:
        return True
    return False


def parse_timeline_entries(wiki_text):
    """解析时间线条目"""
    entries = []
    timeline_pos = wiki_text.find("## 时间线")
    if timeline_pos < 0:
        return entries, timeline_pos

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
    """
    清理单个 wiki 页面的乱码条目。
    返回: (total, kept, removed)
    """
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
        if has_mojibake(entry):
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

    # 更新元数据
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
    parser = argparse.ArgumentParser(description="清理 wiki 页面中的编码乱码条目")
    parser.add_argument("--execute", action="store_true", help="实际执行（默认 dry-run）")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--sector", type=str, help="只处理指定行业")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("  Wiki 页面编码乱码清理")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    total_entries = 0
    total_kept = 0
    total_removed = 0
    affected_files = []

    # 扫描公司页面
    companies_dir = WIKI_ROOT / "companies"
    for wiki_dir in companies_dir.glob("*/wiki"):
        company_name = wiki_dir.parent.name
        if args.company and company_name != args.company:
            continue
        for md_file in wiki_dir.glob("*.md"):
            total, kept, removed = clean_wiki_page(md_file, dry_run)
            if total > 0 and removed > 0:
                rel = md_file.relative_to(WIKI_ROOT)
                pct = removed * 100 // total
                status = "REMOVED" if not dry_run else "WOULD REMOVE"
                print(f"  [{status}] {rel}: {removed}/{total} ({pct}%)")
                affected_files.append(str(rel))
                total_entries += total
                total_kept += kept
                total_removed += removed

    # 扫描行业页面
    sectors_dir = WIKI_ROOT / "sectors"
    if sectors_dir.exists():
        for wiki_dir in sectors_dir.glob("*/wiki"):
            sector_name = wiki_dir.parent.name
            if args.sector and sector_name != args.sector:
                continue
            for md_file in wiki_dir.glob("*.md"):
                total, kept, removed = clean_wiki_page(md_file, dry_run)
                if total > 0 and removed > 0:
                    rel = md_file.relative_to(WIKI_ROOT)
                    pct = removed * 100 // total
                    status = "REMOVED" if not dry_run else "WOULD REMOVE"
                    print(f"  [{status}] {rel}: {removed}/{total} ({pct}%)")
                    affected_files.append(str(rel))
                    total_entries += total
                    total_kept += kept
                    total_removed += removed

    # 扫描主题页面
    themes_dir = WIKI_ROOT / "themes"
    if themes_dir.exists():
        for wiki_dir in themes_dir.glob("*/wiki"):
            for md_file in wiki_dir.glob("*.md"):
                total, kept, removed = clean_wiki_page(md_file, dry_run)
                if total > 0 and removed > 0:
                    rel = md_file.relative_to(WIKI_ROOT)
                    pct = removed * 100 // total
                    status = "REMOVED" if not dry_run else "WOULD REMOVE"
                    print(f"  [{status}] {rel}: {removed}/{total} ({pct}%)")
                    affected_files.append(str(rel))
                    total_entries += total
                    total_kept += kept
                    total_removed += removed

    print(f"\n{'=' * 60}")
    print(f"  Total: {total_entries} entries, {total_kept} kept, {total_removed} garbled entries removed")
    print(f"  Affected files: {len(affected_files)}")
    if dry_run:
        print(f"  Use --execute to actually remove garbled entries")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
