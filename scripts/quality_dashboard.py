#!/usr/bin/env python3
"""
quality_dashboard.py — 知识库质量仪表盘

生成 markdown 格式的质量报告，包含：
- 每页统计（条目数、最后更新、问题数、评估状态）
- 每行业统计（总条目、污染率、评估完整度）
- 全局统计（缺评估页面数、条目<3页面数、过期页面数）

用法：
    python3 scripts/quality_dashboard.py                    # 输出到控制台
    python3 scripts/quality_dashboard.py --output docs/quality_report.md
    python3 scripts/quality_dashboard.py --sector 液冷      # 只看某个行业
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def parse_frontmatter(text):
    """解析 markdown 文件的 frontmatter"""
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            front = text[3:end].strip()
            for line in front.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta


def count_timeline_entries(text):
    """计算时间线条目数"""
    return len(re.findall(r'^###\s+\d{4}-\d{2}-\d{2}', text, re.MULTILINE))


def has_section(text, section_name):
    """检查是否有某个 ## section"""
    return bool(re.search(rf'^##\s+{re.escape(section_name)}', text, re.MULTILINE))


def get_section_content(text, section_name):
    """获取某个 ## section 的内容"""
    pattern = rf'^##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def count_core_questions(text):
    """计算核心问题数"""
    section = get_section_content(text, "核心问题")
    if not section:
        return 0
    return len([l for l in section.split("\n") if l.strip().startswith("-")])


def has_assessment(text):
    """检查是否有实质性的综合评估"""
    section = get_section_content(text, "综合评估")
    if not section:
        return False
    # 排除占位文字
    placeholders = ["待积累数据后补充", "暂无", "有待观察", "待补充"]
    for p in placeholders:
        if p in section:
            return False
    return len(section) > 50


def scan_wiki_page(path):
    """扫描单个 wiki 页面，返回统计信息"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    meta = parse_frontmatter(text)
    return {
        "path": str(path.relative_to(WIKI_ROOT)),
        "title": meta.get("title", path.stem),
        "entity": meta.get("entity", ""),
        "type": meta.get("type", ""),
        "last_updated": meta.get("last_updated", ""),
        "sources_count": int(meta.get("sources_count", 0)),
        "timeline_entries": count_timeline_entries(text),
        "core_questions": count_core_questions(text),
        "has_assessment": has_assessment(text),
        "tags": meta.get("tags", []),
    }


def generate_report(graph, output_path=None, sector_filter=None):
    """生成质量报告"""
    now = datetime.now()
    report = []
    report.append(f"# 知识库质量报告")
    report.append(f"\n> 生成时间: {now.strftime('%Y-%m-%d %H:%M')}\n")

    # ── 收集所有 wiki 页面 ──
    all_pages = []

    # 公司页面
    for company_name in graph._data.get("companies", {}):
        company_dir = WIKI_ROOT / "companies" / company_name / "wiki"
        if not company_dir.exists():
            continue
        for md_file in company_dir.glob("*.md"):
            info = scan_wiki_page(md_file)
            if info:
                info["category"] = "company"
                info["company_name"] = company_name
                all_pages.append(info)

    # 行业页面
    for sector_name in graph.get_all_sectors():
        if sector_filter and sector_name != sector_filter:
            continue
        md_file = WIKI_ROOT / "sectors" / sector_name / "wiki" / f"{sector_name}.md"
        if md_file.exists():
            info = scan_wiki_page(md_file)
            if info:
                info["category"] = "sector"
                all_pages.append(info)

    # 主题页面
    for theme_name in ["AI产业链", "半导体国产替代", "高端制造"]:
        if sector_filter and theme_name != sector_filter:
            continue
        md_file = WIKI_ROOT / "themes" / theme_name / "wiki" / f"{theme_name}.md"
        if md_file.exists():
            info = scan_wiki_page(md_file)
            if info:
                info["category"] = "theme"
                all_pages.append(info)

    # ── 全局统计 ──
    total_pages = len(all_pages)
    total_entries = sum(p["timeline_entries"] for p in all_pages)
    pages_no_assessment = [p for p in all_pages if not p["has_assessment"]]
    pages_few_entries = [p for p in all_pages if p["timeline_entries"] < 3]
    pages_no_questions = [p for p in all_pages if p["core_questions"] == 0]

    stale_days = 30
    stale_date = (now - timedelta(days=stale_days)).strftime("%Y-%m-%d")
    pages_stale = [
        p for p in all_pages
        if p["last_updated"] and p["last_updated"] < stale_date
    ]

    report.append("## 全局统计\n")
    report.append(f"| 指标 | 数值 |")
    report.append(f"|------|------|")
    report.append(f"| 总 wiki 页面 | {total_pages} |")
    report.append(f"| 总时间线条目 | {total_entries} |")
    report.append(f"| 缺少综合评估 | {len(pages_no_assessment)} ({len(pages_no_assessment)*100//max(total_pages,1)}%) |")
    report.append(f"| 条目<3 | {len(pages_few_entries)} ({len(pages_few_entries)*100//max(total_pages,1)}%) |")
    report.append(f"| 无核心问题 | {len(pages_no_questions)} ({len(pages_no_questions)*100//max(total_pages,1)}%) |")
    report.append(f"| {stale_days}天未更新 | {len(pages_stale)} ({len(pages_stale)*100//max(total_pages,1)}%) |")
    report.append("")

    # ── 按类别统计 ──
    report.append("## 按类别统计\n")
    for cat in ["company", "sector", "theme"]:
        cat_pages = [p for p in all_pages if p["category"] == cat]
        if not cat_pages:
            continue
        cat_name = {"company": "公司", "sector": "行业", "theme": "主题"}[cat]
        cat_entries = sum(p["timeline_entries"] for p in cat_pages)
        cat_no_assess = len([p for p in cat_pages if not p["has_assessment"]])
        report.append(f"### {cat_name} ({len(cat_pages)} 页, {cat_entries} 条目)")
        report.append(f"- 缺评估: {cat_no_assess}")
        report.append("")

    # ── 最需要关注的页面 ──
    report.append("## 需要关注的页面\n")

    # 条目最多的行业（可能存在污染）
    report.append("### 条目数 Top 10（可能含交叉污染）\n")
    sector_pages = sorted(
        [p for p in all_pages if p["category"] in ("sector", "theme")],
        key=lambda p: p["timeline_entries"],
        reverse=True
    )[:10]
    report.append("| 页面 | 条目数 | 有评估 | 最后更新 |")
    report.append("|------|--------|--------|----------|")
    for p in sector_pages:
        assess_mark = "Y" if p["has_assessment"] else "N"
        report.append(f"| {p['entity']} | {p['timeline_entries']} | {assess_mark} | {p['last_updated']} |")
    report.append("")

    # 条目最少的页面
    report.append("### 条目数最少的页面（Top 10）\n")
    sparse_pages = sorted(all_pages, key=lambda p: p["timeline_entries"])[:10]
    report.append("| 页面 | 类别 | 条目数 | 问题数 |")
    report.append("|------|------|--------|--------|")
    for p in sparse_pages:
        report.append(f"| {p['entity']}/{p['title']} | {p['category']} | {p['timeline_entries']} | {p['core_questions']} |")
    report.append("")

    # 缺评估的页面
    if pages_no_assessment:
        report.append(f"### 缺少综合评估的页面 ({len(pages_no_assessment)})\n")
        report.append("| 页面 | 条目数 | 问题数 |")
        report.append("|------|--------|--------|")
        for p in sorted(pages_no_assessment, key=lambda p: p["timeline_entries"], reverse=True)[:15]:
            report.append(f"| {p['entity']}/{p['title']} | {p['timeline_entries']} | {p['core_questions']} |")
        if len(pages_no_assessment) > 15:
            report.append(f"| ... 还有 {len(pages_no_assessment) - 15} 页 | | |")
        report.append("")

    # ── 行业覆盖度 ──
    report.append("## 行业覆盖度\n")
    report.append("| 行业 | 公司数 | 条目数 | 有评估 | 问题数 |")
    report.append("|------|--------|--------|--------|--------|")
    for sector_name in graph.get_all_sectors():
        sector_info = graph.get_sector(sector_name)
        if not sector_info:
            continue
        comp_count = len(sector_info.get("companies", []))
        # 找到对应的 wiki 页面
        sp = [p for p in all_pages if p["entity"] == sector_name]
        entries = sp[0]["timeline_entries"] if sp else 0
        assess = "Y" if (sp and sp[0]["has_assessment"]) else "N"
        questions = sp[0]["core_questions"] if sp else 0
        report.append(f"| {sector_name} | {comp_count} | {entries} | {assess} | {questions} |")
    report.append("")

    report_text = "\n".join(report)

    if output_path:
        Path(output_path).write_text(report_text, encoding="utf-8")
        print(f"Report saved to: {output_path}")
    else:
        print(report_text)

    return report_text


def main():
    parser = argparse.ArgumentParser(description="知识库质量仪表盘")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--sector", type=str, help="只看某个行业")
    args = parser.parse_args()

    graph = Graph()
    generate_report(graph, args.output, args.sector)


if __name__ == "__main__":
    main()
