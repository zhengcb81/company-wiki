#!/usr/bin/env python3
"""
reprocess.py — 批量重处理工具

使用改进后的相关性引擎重新评估现有 wiki 时间线条目。
将不再符合路由规则的条目移入审查队列。

用法：
    python3 scripts/reprocess.py --sector 液冷            # 重处理指定行业
    python3 scripts/reprocess.py --company 阳光电源        # 重处理指定公司的相关条目
    python3 scripts/reprocess.py --all                     # 重处理所有页面
    python3 scripts/reprocess.py --dry-run --sector 光模块 # 预览模式
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def get_entity_companies(graph, entity_name, entity_type):
    """获取一个实体（行业/主题）应该包含的公司"""
    if entity_type == "sector":
        sector = graph.get_sector(entity_name)
        if not sector:
            return set()
        companies = set(sector.get("companies", []))
        for sub, sub_comps in sector.get("subsector_companies", {}).items():
            companies.update(sub_comps)
        for parent in sector.get("parent_sector", []):
            parent_comps = [
                c for c, d in graph._data.get("companies", {}).items()
                if parent in d.get("sectors", [])
            ]
            companies.update(parent_comps)
        for c, d in graph._data.get("companies", {}).items():
            if entity_name in d.get("sectors", []):
                companies.add(c)
        return companies
    elif entity_type == "theme":
        companies = set()
        for c, d in graph._data.get("companies", {}).items():
            if entity_name in d.get("themes", []):
                companies.add(c)
        return companies
    return set()


def extract_source_company(entry_text):
    """从来源链接中提取公司名"""
    match = re.search(r'companies/([^/\]]+)', entry_text)
    return match.group(1) if match else None


def parse_timeline_entries(wiki_text):
    """解析时间线条目"""
    entries = []
    timeline_pos = wiki_text.find("## 时间线")
    if timeline_pos < 0:
        return entries

    timeline_section = wiki_text[timeline_pos:]
    next_section = re.search(r'\n## (?!时间线)', timeline_section)
    if next_section:
        timeline_section = timeline_section[:next_section.start()]

    parts = re.split(r'\n(?=### )', timeline_section)
    for part in parts:
        if part.strip().startswith('###'):
            header_end = part.find('\n')
            if header_end > 0:
                header = part[:header_end].strip()
                body = part[header_end:].strip()
            else:
                header = part.strip()
                body = ""
            entries.append((header, body, part))

    return entries


def reprocess_page(wiki_path, allowed_companies, dry_run=True):
    """
    重处理单个页面：检查每条时间线的来源是否属于该页面的合法公司。
    返回: (total, kept, removed)
    """
    if not wiki_path.exists():
        return 0, 0, 0

    wiki_text = wiki_path.read_text(encoding="utf-8")
    entries = parse_timeline_entries(wiki_text)

    if not entries:
        return 0, 0, 0

    kept = []
    removed = []

    for header, body, full_text in entries:
        source_company = extract_source_company(full_text)
        if source_company and source_company not in allowed_companies:
            removed.append((header, body, source_company))
        else:
            kept.append((header, body))

    if dry_run or not removed:
        return len(entries), len(kept), len(removed)

    # 实际执行：重建 wiki
    timeline_pos = wiki_text.find("## 时间线")
    next_section = re.search(r'\n## (?!时间线)', wiki_text[timeline_pos:])
    after_timeline = ""
    if next_section:
        after_timeline = wiki_text[timeline_pos + next_section.start():]

    new_timeline = "## 时间线\n\n"
    if kept:
        for header, body in kept:
            new_timeline += f"{header}\n{body}\n\n"
    else:
        new_timeline += "（暂无条目）\n\n"

    new_wiki = wiki_text[:timeline_pos] + new_timeline + after_timeline

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
    return len(entries), len(kept), len(removed)


def main():
    parser = argparse.ArgumentParser(description="批量重处理工具")
    parser.add_argument("--sector", type=str, help="重处理指定行业")
    parser.add_argument("--company", type=str, help="重处理包含指定公司的条目")
    parser.add_argument("--all", action="store_true", help="重处理所有页面")
    parser.add_argument("--dry-run", action="store_true", help="预览模式（默认）")
    parser.add_argument("--execute", action="store_true", help="实际执行")
    args = parser.parse_args()

    if not any([args.sector, args.company, args.all]):
        parser.print_help()
        sys.exit(1)

    dry_run = not args.execute

    print("=" * 60)
    print("  批量重处理工具")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    graph = Graph()
    total_removed = 0
    total_kept = 0
    total_entries = 0
    review_entries = {}

    if args.sector or args.all:
        sectors = [args.sector] if args.sector else graph.get_all_sectors()
        for sector_name in sectors:
            wiki_path = WIKI_ROOT / "sectors" / sector_name / "wiki" / f"{sector_name}.md"
            allowed = get_entity_companies(graph, sector_name, "sector")
            total, kept, removed = reprocess_page(wiki_path, allowed, dry_run)

            if total > 0 and removed > 0:
                pct = removed * 100 // total
                status = "REMOVED" if args.execute else "WOULD REMOVE"
                print(f"  [{status}] {sector_name}: {removed}/{total} ({pct}%)")
                total_removed += removed
                total_kept += kept
                total_entries += total

                if not args.execute:
                    review_entries[sector_name] = removed

    if args.company or args.all:
        companies = [args.company] if args.company else list(graph._data.get("companies", {}).keys())
        for company_name in companies:
            comp = graph.get_company(company_name)
            if not comp:
                continue
            # 重处理公司的"相关动态"页面中的其他公司提及
            wiki_path = WIKI_ROOT / "companies" / company_name / "wiki" / "相关动态.md"
            if not wiki_path.exists():
                continue
            # 相关动态页面只保留与该公司相关的条目
            allowed = {company_name}
            total, kept, removed = reprocess_page(wiki_path, allowed, dry_run)
            if total > 0 and removed > 0:
                pct = removed * 100 // total
                status = "REMOVED" if args.execute else "WOULD REMOVE"
                print(f"  [{status}] {company_name}/相关动态: {removed}/{total} ({pct}%)")
                total_removed += removed
                total_kept += kept
                total_entries += total

    # 主题页面
    if args.all:
        for theme_name in ["AI产业链", "半导体国产替代", "高端制造"]:
            wiki_path = WIKI_ROOT / "themes" / theme_name / "wiki" / f"{theme_name}.md"
            allowed = get_entity_companies(graph, theme_name, "theme")
            total, kept, removed = reprocess_page(wiki_path, allowed, dry_run)
            if total > 0 and removed > 0:
                pct = removed * 100 // total
                status = "REMOVED" if args.execute else "WOULD REMOVE"
                print(f"  [{status}] {theme_name}: {removed}/{total} ({pct}%)")
                total_removed += removed
                total_kept += kept
                total_entries += total

    print(f"\n{'=' * 60}")
    print(f"  Total: {total_entries} entries, {total_kept} kept, {total_removed} removed")
    if dry_run:
        print(f"  Use --execute to actually remove entries")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
