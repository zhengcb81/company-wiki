#!/usr/bin/env python3
"""
cleanup_contamination.py — 行业/主题页面交叉污染清洗
检查行业和主题 wiki 页面中的时间线条目，找出来源公司不属于该行业的条目，
移入审查文件供人工审核。

用法：
    python3 scripts/cleanup_contamination.py                # dry-run 模式（默认）
    python3 scripts/cleanup_contamination.py --execute      # 实际执行
    python3 scripts/cleanup_contamination.py --sector 液冷   # 只处理指定行业
    python3 scripts/cleanup_contamination.py --theme 半导体国产替代  # 只处理指定主题
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def get_sector_companies(graph, sector_name):
    """获取属于某行业及其子领域/父领域的所有公司名"""
    sector = graph.get_sector(sector_name)
    if not sector:
        return set()

    companies = set(sector.get("companies", []))

    # 也包含子领域的公司
    for sub, sub_comps in sector.get("subsector_companies", {}).items():
        companies.update(sub_comps)

    # 如果是子领域（有 parent_sector），也包含父领域的公司
    for parent in sector.get("parent_sector", []):
        parent_companies = [
            cname for cname, comp in graph._data.get("companies", {}).items()
            if parent in comp.get("sectors", [])
        ]
        companies.update(parent_companies)

    # 也包含直接归属到该子领域的公司（通过 sectors 字段）
    for comp_name, comp in graph._data.get("companies", {}).items():
        if sector_name in comp.get("sectors", []):
            companies.add(comp_name)

    return companies


def get_theme_companies(graph, theme_name):
    """获取属于某主题的所有公司名"""
    companies = set()
    for comp_name, comp in graph._data.get("companies", {}).items():
        if theme_name in comp.get("themes", []):
            companies.add(comp_name)
    return companies


def extract_source_company(entry_text):
    """从时间线条目的来源链接中提取公司名"""
    # 来源格式: - [来源](../raw/.../companies/公司名/...)
    # 或: - [来源](../../companies/公司名/...)
    match = re.search(r'companies/([^/\]]+)', entry_text)
    if match:
        return match.group(1)
    return None


def parse_timeline_entries(wiki_text):
    """解析时间线条目，返回 [(header, body, full_text), ...]"""
    entries = []
    # 找到时间线部分
    timeline_pos = wiki_text.find("## 时间线")
    if timeline_pos < 0:
        return entries

    timeline_section = wiki_text[timeline_pos:]

    # 找到下一个 ## 部分
    next_section = re.search(r'\n## (?!时间线)', timeline_section)
    if next_section:
        timeline_section = timeline_section[:next_section.start()]

    # 按 ### 分割条目
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


def clean_sector_page(wiki_path, allowed_companies, graph, dry_run=True):
    """
    清洗单个行业/主题页面。
    返回: (total_entries, contaminated_entries, clean_entries)
    """
    if not wiki_path.exists():
        return 0, 0, 0

    wiki_text = wiki_path.read_text(encoding="utf-8")
    entries = parse_timeline_entries(wiki_text)

    if not entries:
        return 0, 0, 0

    contaminated = []
    clean = []

    for header, body, full_text in entries:
        source_company = extract_source_company(full_text)

        if source_company and source_company not in allowed_companies:
            contaminated.append((header, body, full_text, source_company))
        else:
            clean.append((header, body, full_text))

    if not contaminated:
        return len(entries), 0, len(entries)

    if dry_run:
        return len(entries), len(contaminated), len(clean)

    # 实际执行：重建时间线，只保留干净条目
    timeline_pos = wiki_text.find("## 时间线")
    next_section = re.search(r'\n## (?!时间线)', wiki_text[timeline_pos:])

    if next_section:
        after_timeline = wiki_text[timeline_pos + next_section.start():]
    else:
        after_timeline = ""

    # 重建时间线部分
    new_timeline = "## 时间线\n\n"
    if clean:
        for header, body, _ in clean:
            new_timeline += f"{header}\n{body}\n\n"
    else:
        new_timeline += "（暂无条目）\n\n"

    new_wiki = wiki_text[:timeline_pos] + new_timeline + after_timeline

    # 更新 sources_count
    old_count_match = re.search(r'sources_count: (\d+)', new_wiki)
    if old_count_match:
        old_count = int(old_count_match.group(1))
        new_count = max(0, old_count - len(contaminated))
        new_wiki = new_wiki.replace(
            f"sources_count: {old_count}",
            f"sources_count: {new_count}"
        )

    # 更新 last_updated
    new_wiki = re.sub(
        r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
        f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
        new_wiki
    )

    wiki_path.write_text(new_wiki, encoding="utf-8")
    return len(entries), len(contaminated), len(clean)


def save_contaminated_entries(contaminated_map, output_path):
    """将污染条目保存到审查文件"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"# 交叉污染条目审查文件\n\n> 生成时间: {now}\n"
    content += "> 这些条目来自不属于对应行业的公司，已被从行业/主题页面移出。\n"
    content += "> 请人工审查：有价值的条目可手动恢复，无价值的可直接删除。\n\n"

    for page_name, entries in contaminated_map.items():
        if not entries:
            continue
        content += f"---\n\n## {page_name} ({len(entries)} 条污染条目)\n\n"
        for header, body, _, source_company in entries:
            content += f"### 污染源: {source_company}\n"
            content += f"{header}\n{body}\n\n"

    output_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="清洗行业/主题页面的交叉污染")
    parser.add_argument("--sector", type=str, help="只处理指定行业")
    parser.add_argument("--theme", type=str, help="只处理指定主题")
    parser.add_argument("--execute", action="store_true",
                        help="实际执行清理（默认为 dry-run）")
    args = parser.parse_args()

    print("=" * 60)
    print("  交叉污染清洗工具")
    if not args.execute:
        print("  [DRY-RUN] 使用 --execute 实际执行清理")
    print("=" * 60)

    graph = Graph()
    contaminated_map = {}

    # 处理行业页面
    sectors = graph.get_all_sectors()
    if args.sector:
        sectors = [s for s in sectors if s == args.sector]
        if not sectors:
            print(f"ERROR: Sector '{args.sector}' not found")
            sys.exit(1)

    for sector_name in sectors:
        wiki_path = WIKI_ROOT / "sectors" / sector_name / "wiki" / f"{sector_name}.md"
        allowed = get_sector_companies(graph, sector_name)

        total, contam, clean_count = clean_sector_page(
            wiki_path, allowed, graph, dry_run=not args.execute
        )

        if total > 0:
            status = "CLEANED" if args.execute else "WOULD CLEAN"
            if contam > 0:
                print(f"  [{status}] {sector_name}: {total} entries, "
                      f"{contam} contaminated ({contam*100//total}%), "
                      f"{clean_count} clean")
                # 收集污染条目用于审查文件
                if not args.execute:
                    wiki_text = wiki_path.read_text(encoding="utf-8")
                    entries = parse_timeline_entries(wiki_text)
                    contam_entries = []
                    for header, body, full_text in entries:
                        source_company = extract_source_company(full_text)
                        if source_company and source_company not in allowed:
                            contam_entries.append((header, body, full_text, source_company))
                    if contam_entries:
                        contaminated_map[sector_name] = contam_entries
            else:
                print(f"  [OK] {sector_name}: {total} entries, no contamination")

    # 处理主题页面
    themes = ["AI产业链", "半导体国产替代", "高端制造"]
    if args.theme:
        themes = [t for t in themes if t == args.theme]

    for theme_name in themes:
        wiki_path = WIKI_ROOT / "themes" / theme_name / "wiki" / f"{theme_name}.md"
        allowed = get_theme_companies(graph, theme_name)

        total, contam, clean_count = clean_sector_page(
            wiki_path, allowed, graph, dry_run=not args.execute
        )

        if total > 0:
            status = "CLEANED" if args.execute else "WOULD CLEAN"
            if contam > 0:
                print(f"  [{status}] {theme_name}: {total} entries, "
                      f"{contam} contaminated ({contam*100//total}%), "
                      f"{clean_count} clean")
                if not args.execute:
                    wiki_text = wiki_path.read_text(encoding="utf-8")
                    entries = parse_timeline_entries(wiki_text)
                    contam_entries = []
                    for header, body, full_text in entries:
                        source_company = extract_source_company(full_text)
                        if source_company and source_company not in allowed:
                            contam_entries.append((header, body, full_text, source_company))
                    if contam_entries:
                        contaminated_map[theme_name] = contam_entries
            else:
                print(f"  [OK] {theme_name}: {total} entries, no contamination")

    # 保存审查文件
    if contaminated_map and not args.execute:
        review_path = WIKI_ROOT / "docs" / "contaminated_entries_review.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        save_contaminated_entries(contaminated_map, review_path)
        print(f"\n  污染条目已保存到: {review_path}")
        print(f"  审查后使用 --execute 实际执行清理")

    print(f"\n{'=' * 60}")
    print("  Done.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
