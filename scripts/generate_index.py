#!/usr/bin/env python3
"""
generate_index.py — 自动生成 index.md 索引
扫描所有 wiki 页面，生成带 wikilinks 的目录。

用法：
    python3 scripts/generate_index.py
    # ingest 后自动调用
"""

import os
import glob
import yaml
from datetime import datetime
from pathlib import Path

WIKI_ROOT = Path(__file__).resolve().parent.parent


def generate():
    graph_path = WIKI_ROOT / "graph.yaml"
    with open(graph_path, "r", encoding="utf-8") as f:
        g = yaml.safe_load(f)

    lines = []
    lines.append("---")
    lines.append('title: "知识库索引"')
    lines.append(f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"')
    lines.append("---")
    lines.append("")
    lines.append("# 上市公司知识库索引")
    lines.append("")
    lines.append(f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # ── 产业链概览 ──
    lines.append("## 产业链概览")
    lines.append("")
    lines.append("[[_产业链导航|查看完整产业链拓扑图 →]]")
    lines.append("")

    # ── 按行业分组的公司 ──
    lines.append("## 公司（按行业）")
    lines.append("")

    # 构建行业→公司映射
    sector_companies = {}
    for name, info in g.get("companies", {}).items():
        for sector in info.get("sectors", []):
            if sector not in sector_companies:
                sector_companies[sector] = []
            sector_companies[sector].append(name)

    # 按 tier 排序行业
    sector_tiers = {}
    for name, info in g.get("nodes", {}).items():
        if info.get("type") == "sector":
            sector_tiers[name] = info.get("tier", 99)

    tier_labels = {0: "应用层", 1: "支撑层", 2: "基础设施层",
                   3: "核心器件层", 4: "制造层", 5: "上游基础层"}

    by_tier = {}
    for sector, tier in sector_tiers.items():
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(sector)

    for tier in sorted(by_tier.keys()):
        label = tier_labels.get(tier, f"Tier {tier}")
        lines.append(f"### {label}")
        lines.append("")

        for sector in sorted(by_tier[tier]):
            comps = sorted(sector_companies.get(sector, []))
            if comps:
                lines.append(f"**{sector}**")
                # 检查公司 wiki 是否存在
                comp_links = []
                for c in comps:
                    wiki_exists = (WIKI_ROOT / "companies" / c / "wiki").exists() and \
                                  list((WIKI_ROOT / "companies" / c / "wiki").glob("*.md"))
                    if wiki_exists:
                        comp_links.append(f"[[{c}]]")
                    else:
                        comp_links.append(c)
                lines.append(f"  {', '.join(comp_links)}")
                lines.append("")

    # ── 行业 wiki 页面 ──
    lines.append("## 行业 Wiki")
    lines.append("")
    sector_wikis = sorted(glob.glob(str(WIKI_ROOT / "sectors/*/wiki/*.md")))
    if sector_wikis:
        for f in sector_wikis:
            rel = os.path.relpath(f, WIKI_ROOT)
            sector_name = Path(f).parents[1].name
            page_name = Path(f).stem
            lines.append(f"- [[{sector_name}/{page_name}]]")
    else:
        lines.append("（暂无）")
    lines.append("")

    # ── 主题 wiki 页面 ──
    lines.append("## 跨行业主题")
    lines.append("")
    theme_wikis = sorted(glob.glob(str(WIKI_ROOT / "themes/*/wiki/*.md")))
    if theme_wikis:
        for f in theme_wikis:
            rel = os.path.relpath(f, WIKI_ROOT)
            theme_name = Path(f).parents[1].name
            page_name = Path(f).stem
            lines.append(f"- [[{theme_name}/{page_name}]]")
    else:
        lines.append("（暂无）")
    lines.append("")

    # ── 数据统计 ──
    news_count = len(glob.glob(str(WIKI_ROOT / "companies/*/raw/news/*.md")))
    pdf_count = len(glob.glob(str(WIKI_ROOT / "companies/**/*.pdf"), recursive=True))
    wiki_count = len(glob.glob(str(WIKI_ROOT / "companies/*/wiki/*.md"))) + \
                 len(sector_wikis) + len(theme_wikis)

    lines.append("## 数据统计")
    lines.append("")
    lines.append(f"| 指标 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 公司 | {len(g['companies'])} 家 |")
    lines.append(f"| 行业/主题 | {len(g['nodes'])} 个 |")
    lines.append(f"| 新闻 | {news_count} 篇 |")
    lines.append(f"| PDF | {pdf_count} 份 |")
    lines.append(f"| Wiki页面 | {wiki_count} 个 |")
    lines.append("")

    # 写入
    index_path = WIKI_ROOT / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {index_path}")
    print(f"  {len(lines)} lines, {wiki_count} wiki pages indexed")


if __name__ == "__main__":
    generate()
