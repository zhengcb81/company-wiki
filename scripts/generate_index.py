#!/usr/bin/env python3
"""
generate_index.py — 自动生成 index.md 索引
扫描所有 wiki 页面，生成带 wikilinks 和摘要的目录。

用法：
    python3 scripts/generate_index.py
    # ingest 后自动调用
"""

import os
import re
import glob
import yaml
from datetime import datetime
from pathlib import Path

WIKI_ROOT = Path(__file__).resolve().parent.parent

MAX_SUMMARY_LEN = 80


def _extract_page_summary(wiki_file: Path) -> str:
    """从 wiki 页面提取一行摘要（≤80 字）。

    优先使用 frontmatter 中的 description 字段，
    否则取第一个非标题非 frontmatter 的有意义的段落。
    """
    try:
        content = wiki_file.read_text(encoding="utf-8")
    except Exception:
        return ""

    # 跳过 frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            fm_text = content[3:end]
            # 优先使用 description 字段
            desc_match = re.search(r'description:\s*["\']?(.+?)["\']?\s*$', fm_text, re.MULTILINE)
            if desc_match:
                desc = desc_match.group(1).strip().strip('"\'')
                if len(desc) > MAX_SUMMARY_LEN:
                    return desc[:MAX_SUMMARY_LEN - 3] + "..."
                return desc
            body = content[end + 3:]
        else:
            body = content
    else:
        body = content

    # 从正文中提取：跳过标题、空行、核心问题标题、引用块
    in_core_questions = False
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if "核心问题" in stripped:
                in_core_questions = True
            continue
        if in_core_questions and stripped.startswith("-"):
            # 核心问题中的条目可作为摘要来源
            text = stripped.lstrip("- ").strip()
            if text and len(text) > 5:
                if len(text) > MAX_SUMMARY_LEN:
                    return text[:MAX_SUMMARY_LEN - 3] + "..."
                return text
            continue
        if in_core_questions and not stripped.startswith("-"):
            in_core_questions = False
        if stripped.startswith(">"):
            continue
        if stripped.startswith("- [来源"):
            continue
        if stripped.startswith("###"):
            continue
        # 找到有意义的正文段落
        text = stripped.lstrip("- ").strip()
        if text and len(text) > 5:
            if len(text) > MAX_SUMMARY_LEN:
                return text[:MAX_SUMMARY_LEN - 3] + "..."
            return text

    return ""


def _extract_frontmatter(wiki_file: Path) -> dict:
    """从 wiki 文件提取 frontmatter 字典。"""
    try:
        content = wiki_file.read_text(encoding="utf-8")
    except Exception:
        return {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            try:
                return yaml.safe_load(content[3:end]) or {}
            except yaml.YAMLError:
                return {}
    return {}


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

    # ── 按行业分组的公司（带摘要）──
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
                # 每个公司一行，带主要 wiki 页面摘要
                for c in comps:
                    wiki_dir = WIKI_ROOT / "companies" / c / "wiki"
                    if wiki_dir.exists() and list(wiki_dir.glob("*.md")):
                        # 取第一个 wiki 页面（通常是公司动态）的摘要
                        main_wiki = sorted(wiki_dir.glob("*.md"))[0]
                        summary = _extract_page_summary(main_wiki)
                        if summary:
                            lines.append(f"  - [[{c}]] — {summary}")
                        else:
                            lines.append(f"  - [[{c}]]")
                    else:
                        lines.append(f"  - {c}")
                lines.append("")

    # ── 行业 wiki 页面（带摘要）──
    lines.append("## 行业 Wiki")
    lines.append("")
    sector_wikis = sorted(glob.glob(str(WIKI_ROOT / "sectors/*/wiki/*.md")))
    if sector_wikis:
        for f in sector_wikis:
            sector_name = Path(f).parents[1].name
            page_name = Path(f).stem
            summary = _extract_page_summary(Path(f))
            if summary:
                lines.append(f"- [[{sector_name}/{page_name}]] — {summary}")
            else:
                lines.append(f"- [[{sector_name}/{page_name}]]")
    else:
        lines.append("（暂无）")
    lines.append("")

    # ── 主题 wiki 页面（带摘要）──
    lines.append("## 跨行业主题")
    lines.append("")
    theme_wikis = sorted(glob.glob(str(WIKI_ROOT / "themes/*/wiki/*.md")))
    if theme_wikis:
        for f in theme_wikis:
            theme_name = Path(f).parents[1].name
            page_name = Path(f).stem
            summary = _extract_page_summary(Path(f))
            if summary:
                lines.append(f"- [[{theme_name}/{page_name}]] — {summary}")
            else:
                lines.append(f"- [[{theme_name}/{page_name}]]")
    else:
        lines.append("（暂无）")
    lines.append("")

    # ── 概念百科 ──
    concept_pages = []
    comparison_pages = []
    synthesis_pages = []
    all_wiki_files = glob.glob(str(WIKI_ROOT / "**/wiki/*.md"), recursive=True)
    for f in all_wiki_files:
        fm = _extract_frontmatter(Path(f))
        page_type = fm.get("type", "")
        if page_type == "concept":
            concept_pages.append((Path(f), fm))
        elif page_type == "comparison":
            comparison_pages.append((Path(f), fm))
        elif page_type == "synthesis":
            synthesis_pages.append((Path(f), fm))

    if concept_pages:
        lines.append("## 概念百科")
        lines.append("")
        for f, fm in sorted(concept_pages, key=lambda x: x[1].get("title", "")):
            title = fm.get("title", f.stem)
            summary = _extract_page_summary(f)
            if summary:
                lines.append(f"- [[{f.stem}]] — {summary}")
            else:
                lines.append(f"- [[{f.stem}]] — {title}")
        lines.append("")

    if comparison_pages:
        lines.append("## 对比分析")
        lines.append("")
        for f, fm in sorted(comparison_pages, key=lambda x: x[1].get("title", "")):
            title = fm.get("title", f.stem)
            summary = _extract_page_summary(f)
            if summary:
                lines.append(f"- [[{f.stem}]] — {summary}")
            else:
                lines.append(f"- [[{f.stem}]] — {title}")
        lines.append("")

    if synthesis_pages:
        lines.append("## 综合报告")
        lines.append("")
        for f, fm in sorted(synthesis_pages, key=lambda x: x[1].get("title", "")):
            title = fm.get("title", f.stem)
            summary = _extract_page_summary(f)
            if summary:
                lines.append(f"- [[{f.stem}]] — {summary}")
            else:
                lines.append(f"- [[{f.stem}]] — {title}")
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
