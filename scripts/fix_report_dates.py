#!/usr/bin/env python3
"""
fix_report_dates.py — 修复 wiki 中财务报告条目的错误日期

背景：pdf_extract_v2.py:classify_pdf 曾将半年报/季报全部标为 annual_report，
导致 ingest_v2.py 的 extract_report_date 错误地将所有报告日期推断为 12-31。

用法：
    python3 scripts/fix_report_dates.py --dry-run   # 预览
    python3 scripts/fix_report_dates.py --execute   # 实际执行
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from common import WIKI_ROOT


def infer_correct_date(filename: str) -> Optional[str]:
    """根据文件名推断正确的财务报告日期（报告期）"""
    name = filename.lower()

    # 提取年份
    year_match = re.search(r"(20\d{2})", name)
    if not year_match:
        return None
    year = year_match.group(1)

    # 判断报告类型
    if any(kw in name for kw in ["年报", "年度报告"]):
        return f"{year}-12-31"
    elif any(kw in name for kw in ["半年报", "半年度报告"]):
        return f"{year}-06-30"
    elif any(kw in name for kw in ["一季报", "第一季度", "q1", "1季报"]):
        return f"{year}-03-31"
    elif any(kw in name for kw in ["二季报", "第二季度", "q2", "2季报"]):
        return f"{year}-06-30"
    elif any(kw in name for kw in ["三季报", "第三季度", "q3", "3季报"]):
        return f"{year}-09-30"
    elif any(kw in name for kw in ["四季报", "第四季度", "q4", "4季报"]):
        return f"{year}-12-31"
    elif "季报" in name or "季度报告" in name:
        # 通用季报，无法判断季度 → 不修正
        return None

    return None


def fix_wiki_dates(wiki_path: Path, dry_run=True):
    """
    修复单个 wiki 文件中的错误财务报告日期。
    返回: (total_entries, fixed_entries, skipped_entries)
    """
    if not wiki_path.exists():
        return 0, 0, 0

    text = wiki_path.read_text(encoding="utf-8")
    original_text = text

    # 找到时间线部分
    timeline_pos = text.find("## 时间线")
    if timeline_pos < 0:
        return 0, 0, 0

    timeline_section = text[timeline_pos:]
    next_section = re.search(r"\n## (?!时间线)", timeline_section)
    if next_section:
        after_timeline = timeline_section[next_section.start() :]
        timeline_section = timeline_section[: next_section.start()]
    else:
        after_timeline = ""

    # 分割条目（每个条目以 ### 开头）
    entry_pattern = re.compile(
        r"^(### \d{4}-\d{2}-\d{2} \| .*?)(?=\n### |\Z)", re.MULTILINE | re.DOTALL
    )
    entries = entry_pattern.findall(timeline_section)

    # 如果没有匹配到，尝试另一种分割方式
    if not entries:
        parts = re.split(r"\n(?=### )", timeline_section)
        entries = parts[1:] if len(parts) > 1 else []
    else:
        # entry_pattern 返回的是元组（如果有捕获组），需要处理
        if isinstance(entries[0], tuple):
            entries = [e[0] if isinstance(e, tuple) else e for e in entries]

    fixed_count = 0
    total_count = 0

    for entry in entries:
        total_count += 1
        # 查找来源链接
        source_match = re.search(r"- \[来源\]\(([^)]+)\)", entry)
        if not source_match:
            continue

        source_path = source_match.group(1)
        if "financial_reports" not in source_path:
            continue

        # 提取文件名
        filename = Path(source_path).name
        correct_date = infer_correct_date(filename)
        if not correct_date:
            continue

        # 提取当前日期
        header_match = re.match(r"### (\d{4}-\d{2}-\d{2})", entry)
        if not header_match:
            continue

        current_date = header_match.group(1)
        if current_date == correct_date:
            continue

        # 修正日期
        old_header = f"### {current_date}"
        new_header = f"### {correct_date}"
        new_entry = entry.replace(old_header, new_header, 1)

        if not dry_run:
            text = text.replace(entry, new_entry, 1)

        fixed_count += 1
        action = "WOULD FIX" if dry_run else "FIXED"
        print(
            f"  [{action}] {wiki_path.name}: {current_date} → {correct_date} ({filename[:50]})"
        )

    if not dry_run and fixed_count > 0:
        # 更新 last_updated
        text = re.sub(
            r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
            f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
            text,
        )
        wiki_path.write_text(text, encoding="utf-8")

    return total_count, fixed_count, 0


def main():
    parser = argparse.ArgumentParser(description="修复 wiki 中财务报告条目的错误日期")
    parser.add_argument("--dry-run", action="store_true", help="预览模式（默认）")
    parser.add_argument("--execute", action="store_true", help="实际执行")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("  修复财务报告日期")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    total_entries = 0
    total_fixed = 0
    files_checked = 0
    files_fixed = 0

    # 扫描所有公司 wiki
    for wiki_path in sorted(WIKI_ROOT.rglob("companies/*/wiki/*.md")):
        files_checked += 1
        t, f, _ = fix_wiki_dates(wiki_path, dry_run=dry_run)
        total_entries += t
        total_fixed += f
        if f > 0:
            files_fixed += 1

    # 扫描所有行业 wiki（行业 wiki 也可能引用公司财报）
    for wiki_path in sorted(WIKI_ROOT.rglob("sectors/*/wiki/*.md")):
        files_checked += 1
        t, f, _ = fix_wiki_dates(wiki_path, dry_run=dry_run)
        total_entries += t
        total_fixed += f
        if f > 0:
            files_fixed += 1

    print("\n" + "=" * 60)
    print(f"  结果: {files_fixed}/{files_checked} 文件需要修正")
    print(f"  条目: {total_fixed}/{total_entries} 条被修正")
    print("=" * 60)

    if dry_run and total_fixed > 0:
        print(f"\n提示: 运行 `python3 {__file__} --execute` 应用修正")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
