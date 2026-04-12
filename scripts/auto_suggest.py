#!/usr/bin/env python3
"""
auto_suggest.py — 新公司自动发现
扫描已采集的新闻，找出频繁出现但不在 graph.yaml 中的公司名，建议添加。

用法：
    python3 scripts/auto_suggest.py              # 扫描并输出建议
    python3 scripts/auto_suggest.py --enrich     # 扫描后自动 enrich
    python3 scripts/auto_suggest.py --top 10     # 只显示前10个
"""

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def load_graph_config():
    """从 graph.yaml 加载黑名单和别名"""
    import yaml
    graph_path = WIKI_ROOT / "graph.yaml"
    with open(graph_path, "r", encoding="utf-8") as f:
        g = yaml.safe_load(f)

    blacklist = set(g.get("settings", {}).get("name_blacklist", []))

    # 从每家公司的 aliases 字段构建反向映射
    aliases = {}  # alias -> canonical_name
    for name, info in g.get("companies", {}).items():
        for alias in info.get("aliases", []):
            aliases[alias] = name

    return blacklist, aliases


BLACKLIST, ALIASES = load_graph_config()


def extract_company_names(text):
    """从文本中提取可能的公司名"""
    patterns = [
        # 完整公司名：XX + 行业后缀
        r'[\u4e00-\u9fff]{2,4}(?:科技|控股|电气|能源|医药|生物|银行|证券|保险|信托|材料|精密|新能|光电|半导体|信息|通信|装备|环保|智能)',
        # 带"公司"的：XX公司（排除"有限公司"等通用词）
        r'[\u4e00-\u9fff]{2,4}公司(?![\u4e00-\u9fff])',
        # 已知公司名模式
        r'(?:华为|腾讯|阿里|百度|京东|美团|小米|字节|宁德|比亚迪|中芯|华虹|长电|通富|浪潮|中科|紫光|中际|新易盛|天孚|光迅|太辰|英维克|高澜|曙光)',
    ]

    names = set()
    for p in patterns:
        for m in re.finditer(p, text):
            name = m.group()
            if name not in BLACKLIST and len(name) >= 3:
                names.add(name)

    return names


def scan_news_for_companies(graph):
    """扫描新闻，找出在多篇不同文章中出现的未跟踪公司名"""
    known_companies = set(graph._data.get("companies", {}).keys())
    known_companies.update(ALIASES.values())

    # name -> set of distinct news files where it appears
    name_files = {}

    news_dir = WIKI_ROOT / "companies"
    if not news_dir.exists():
        return Counter()

    for md_file in news_dir.rglob("raw/news/*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    content = content[end+3:]

            # 只看前 15 行（标题+摘要，避免正文噪音）
            lines = content.strip().split("\n")[:15]
            short_content = "\n".join(lines)

            names = extract_company_names(short_content)
            parent = md_file.parents[1].name
            file_id = md_file.name  # 用文件名去重

            for name in names:
                if name in BLACKLIST or name in ALIASES or name in known_companies:
                    continue
                if name == parent:
                    continue
                if name not in name_files:
                    name_files[name] = set()
                name_files[name].add(file_id)
        except Exception:
            continue

    # 出现在 3+ 个不同新闻文件中的名字
    mentions = Counter()
    for name, files in name_files.items():
        if len(files) >= 3:
            mentions[name] = len(files)

    return mentions


def suggest_companies(mentions, min_count=2, top_n=20):
    """筛选出值得添加的公司"""
    suggestions = []
    for name, count in mentions.most_common(top_n):
        if count >= min_count:
            suggestions.append({"name": name, "mentions": count})
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="新公司自动发现")
    parser.add_argument("--enrich", action="store_true", help="自动 enrich 建议的公司")
    parser.add_argument("--top", type=int, default=20, help="显示前N个建议")
    parser.add_argument("--min", type=int, default=2, dest="min_count", help="最少提及次数")
    args = parser.parse_args()

    graph = Graph()

    print("Scanning news for untracked companies...")
    mentions = scan_news_for_companies(graph)

    suggestions = suggest_companies(mentions, args.min_count, args.top)

    if not suggestions:
        print("\n  No new companies found. All mentioned companies are already tracked.")
        return

    print(f"\n  Found {len(suggestions)} potential new companies:\n")
    print(f"  {'公司名':<12} {'提及次数':>8}  状态")
    print(f"  {'-'*12} {'-'*8}  {'-'*20}")

    for s in suggestions:
        status = "建议添加"
        print(f"  {s['name']:<12} {s['mentions']:>8}  {status}")

    if args.enrich:
        from enrich import enrich_company
        import yaml
        with open(WIKI_ROOT / "config.yaml") as f:
            config = yaml.safe_load(f)

        print(f"\n  Enriching top {min(5, len(suggestions))} companies...")
        for s in suggestions[:5]:
            # 需要 ticker，这里用占位符（实际需要用户提供或搜索）
            print(f"\n  Skipping {s['name']} - need ticker code")
            print(f"  Run: python3 scripts/enrich.py --company {s['name']} --ticker <CODE>")
    else:
        print(f"\n  To add a company, run:")
        print(f"    python3 scripts/enrich.py --company <名> --ticker <代码>")


if __name__ == "__main__":
    main()
