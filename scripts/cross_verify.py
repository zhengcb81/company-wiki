#!/usr/bin/env python3
"""
cross_verify.py — 多源交叉验证

扫描所有 wiki 页面，聚类相似事件，基于来源数量分配可信度标签，
输出 cross_verify_report.md。

核心方法：
1. 收集所有时间线条目（含公司名、来源）
2. 按标题相似度聚类事件 (difflib.SequenceMatcher)
3. 按来源数量计算可信度
4. 生成交叉验证报告

用法：
    python scripts/cross_verify.py                     # 全量扫描
    python scripts/cross_verify.py --company 中微公司   # 指定公司
    python scripts/cross_verify.py --report            # 生成报告
    python scripts/cross_verify.py --dry-run           # 预览
"""

import argparse
import difflib
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from common import WIKI_ROOT

from graph import Graph


# ── 数据结构 ──────────────────────────────


class EventCluster:
    """事件聚类"""

    def __init__(self, canonical_title: str):
        self.canonical_title = canonical_title  # 规范化标题
        self.entries: List[Dict] = []  # 时间线条目
        self.companies: Set[str] = set()  # 涉及的公司
        self.sources: Set[str] = set()  # 来源文件

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def company_count(self) -> int:
        return len(self.companies)

    @property
    def credibility(self) -> str:
        if self.source_count >= 3:
            return "高可信度（多源确认）"
        elif self.source_count == 2:
            return "中可信度（双源报道）"
        else:
            return "待验证（单一来源）"

    @property
    def first_date(self) -> str:
        dates = [e.get("date", "9999-99-99") for e in self.entries]
        return min(dates)

    def add_entry(self, entry: Dict):
        """添加条目到聚类"""
        self.entries.append(entry)
        company = entry.get("company", "未知")
        self.companies.add(company)
        source = entry.get("source_url", "")
        if source:
            self.sources.add(source)


# ── 条目收集 ──────────────────────────────


def collect_all_entries(company_filter: Optional[str] = None) -> List[Dict]:
    """
    从所有 wiki 页面收集时间线条目。

    Args:
        company_filter: 公司名过滤（可选）

    Returns:
        条目列表
    """
    entries = []

    # 扫描公司 wiki
    companies_dir = WIKI_ROOT / "companies"
    if not companies_dir.exists():
        return entries

    for company_dir in companies_dir.iterdir():
        if not company_dir.is_dir():
            continue
        company_name = company_dir.name
        if company_filter and company_name != company_filter:
            continue

        wiki_dir = company_dir / "wiki"
        if not wiki_dir.exists():
            continue

        for wiki_file in wiki_dir.glob("*.md"):
            if "_slides" in wiki_file.name:
                continue
            content = wiki_file.read_text(encoding="utf-8")
            file_entries = _parse_wiki_entries(content, wiki_file, company_name)
            entries.extend(file_entries)

    return entries


def _parse_wiki_entries(content: str, wiki_file: Path, company_name: str) -> List[Dict]:
    """解析 wiki 文件中的时间线条目"""
    entries = []
    entry_pattern = re.compile(
        r"^### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)$\n"
        r"((?:^- .+$\n?)*)",
        re.MULTILINE,
    )

    for match in entry_pattern.finditer(content):
        date = match.group(1)
        source_type = match.group(2).strip()
        title = match.group(3).strip()
        body = match.group(4)

        source_url = ""
        for line in body.split("\n"):
            src_match = re.search(r"\[来源\]\((.+?)\)", line)
            if src_match:
                source_url = src_match.group(1)
                break

        entries.append(
            {
                "date": date,
                "source_type": source_type,
                "title": title,
                "company": company_name,
                "source_url": source_url,
                "file": str(wiki_file.relative_to(WIKI_ROOT)),
            }
        )

    return entries


# ── 事件聚类 ──────────────────────────────


def normalize_title(title: str) -> str:
    """规范化标题用于聚类比较"""
    # 移除常见的前缀/后缀
    title = re.sub(r"^(?:[A-Z]+[\s-]+)?", "", title)
    # 移除日期
    title = re.sub(r"\d{4}年\d{1,2}月\d{1,2}日", "", title)
    title = re.sub(r"\d{4}年\d{1,2}月", "", title)
    title = re.sub(r"\d{4}", "", title)
    # 统一空格
    title = re.sub(r"\s+", " ", title).strip()
    return title


def title_similarity(title1: str, title2: str) -> float:
    """计算两个标题的相似度（结合字符串匹配和语义判断）"""
    n1 = normalize_title(title1)
    n2 = normalize_title(title2)
    if not n1 or not n2:
        return 0.0

    # 1. 快速字符串匹配
    str_sim = difflib.SequenceMatcher(None, n1, n2).ratio()
    if str_sim >= 0.8:
        return str_sim  # 高字符串相似度直接返回

    # 2. 语义判断：提取核心事件类型
    # 如果两个标题描述不同类型的事件，相似度降低
    event_types_1 = _extract_event_keywords(n1)
    event_types_2 = _extract_event_keywords(n2)

    if event_types_1 and event_types_2:
        # 如果事件类型完全不同，大幅降低相似度
        if not event_types_1.intersection(event_types_2):
            return str_sim * 0.3

    return str_sim


def _extract_event_keywords(title: str) -> set:
    """提取标题中的事件关键词"""
    event_keywords = {
        "财报": ["年报", "季报", "半年报", "营收", "净利润", "毛利率"],
        "订单": ["订单", "合同", "中标", "采购"],
        "产品": ["发布", "新品", "推出", "量产"],
        "产能": ["产能", "扩产", "投产", "建设"],
        "投资": ["投资", "并购", "收购", "定增"],
        "人事": ["任命", "离职", "高管", "董事"],
        "技术": ["专利", "技术", "研发", "突破"],
    }

    found_types = set()
    for event_type, keywords in event_keywords.items():
        if any(kw in title for kw in keywords):
            found_types.add(event_type)

    return found_types


def cluster_events(
    entries: List[Dict], similarity_threshold: float = 0.6
) -> List[EventCluster]:
    """
    将相似的时间线条目聚类为事件。

    Args:
        entries: 时间线条目列表
        similarity_threshold: 相似度阈值 (0.0-1.0)

    Returns:
        事件聚类列表
    """
    if not entries:
        return []

    # 按日期排序
    sorted_entries = sorted(entries, key=lambda e: e["date"])

    clusters: List[EventCluster] = []
    clustered_indices: Set[int] = set()

    # 将 entries 列表转为索引可访问的形式
    flat_entries = sorted_entries

    for i, entry_i in enumerate(flat_entries):
        if i in clustered_indices:
            continue

        # 创建新聚类
        cluster = EventCluster(entry_i["title"])
        cluster.add_entry(entry_i)
        clustered_indices.add(i)

        # 同一个月内的条目比较
        month_key = entry_i["date"][:7]

        # 提取条目的事件类型和公司名
        entry_i_event_types = _extract_event_keywords(entry_i["title"])
        entry_i_company = entry_i.get("company", "")

        for j in range(i + 1, len(flat_entries)):
            if j in clustered_indices:
                continue
            entry_j = flat_entries[j]

            # 只比较同一月或相邻月的条目
            j_month = entry_j["date"][:7]
            if j_month > month_key:
                # 计算月份差（正确处理跨年）
                try:
                    y1, m1 = month_key.split("-")
                    y2, m2 = j_month.split("-")
                    month_diff = abs((int(y2) - int(y1)) * 12 + int(m2) - int(m1))
                    if month_diff > 1:
                        continue
                except (ValueError, IndexError):
                    continue

            # 过滤：如果两个条目属于不同公司且标题相似度不高，跳过
            entry_j_company = entry_j.get("company", "")
            if (
                entry_j_company
                and entry_i_company
                and entry_j_company != entry_i_company
            ):
                # 跨公司匹配需要更高的相似度阈值
                sim = title_similarity(entry_i["title"], entry_j["title"])
                if sim < similarity_threshold + 0.15:  # 跨公司需要 +0.15
                    continue
            else:
                sim = title_similarity(entry_i["title"], entry_j["title"])
                if sim < similarity_threshold:
                    continue

            # 额外过滤：检查事件类型
            entry_j_event_types = _extract_event_keywords(entry_j["title"])
            if entry_i_event_types and entry_j_event_types:
                # 如果事件类型完全不同，跳过（除非是财报类通用事件）
                common_types = entry_i_event_types.intersection(entry_j_event_types)
                if (
                    not common_types
                    and "财报" not in entry_i_event_types
                    and "财报" not in entry_j_event_types
                ):
                    continue

            cluster.add_entry(entry_j)
            clustered_indices.add(j)

        clusters.append(cluster)

    # 按来源数量降序排序
    clusters.sort(key=lambda c: (c.source_count, c.company_count), reverse=True)
    return clusters


# ── 报告生成 ──────────────────────────────


def generate_report(
    clusters: List[EventCluster], output_path: Optional[Path] = None
) -> str:
    """
    生成交叉验证报告。

    Args:
        clusters: 事件聚类列表
        output_path: 输出路径

    Returns:
        报告内容
    """
    lines = []
    lines.append("# 交叉验证报告")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## 概述")
    lines.append("")
    lines.append(f"- 总事件数: {len(clusters)}")
    lines.append(f"- 总条目数: {sum(c.source_count for c in clusters)}")

    high = [c for c in clusters if c.credibility.startswith("高")]
    medium = [c for c in clusters if c.credibility.startswith("中")]
    low = [c for c in clusters if c.credibility.startswith("待")]
    lines.append(f"- 高可信度(3+来源): {len(high)}")
    lines.append(f"- 中可信度(2来源): {len(medium)}")
    lines.append(f"- 待验证(1来源): {len(low)}")
    lines.append("")

    if high:
        lines.append("## 高可信度事件（3+ 来源）")
        lines.append("")
        lines.append("| 事件 | 来源数 | 公司数 | 涉及公司 | 最早日期 |")
        lines.append("|------|--------|--------|---------|---------|")
        for c in high[:20]:
            companies_str = ", ".join(sorted(c.companies)[:3])
            if len(c.companies) > 3:
                companies_str += f" 等{len(c.companies)}家"
            title_short = c.canonical_title[:50]
            if len(c.canonical_title) > 50:
                title_short += "..."
            lines.append(
                f"| {title_short} | {c.source_count} | {c.company_count} | {companies_str} | {c.first_date} |"
            )
        lines.append("")

    if medium:
        lines.append("## 中可信度事件（2 来源）")
        lines.append("")
        lines.append("| 事件 | 来源数 | 公司数 | 涉及公司 | 最早日期 |")
        lines.append("|------|--------|--------|---------|---------|")
        for c in medium[:20]:
            companies_str = ", ".join(sorted(c.companies)[:3])
            if len(c.companies) > 3:
                companies_str += f" 等{len(c.companies)}家"
            title_short = c.canonical_title[:50]
            if len(c.canonical_title) > 50:
                title_short += "..."
            lines.append(
                f"| {title_short} | {c.source_count} | {c.company_count} | {companies_str} | {c.first_date} |"
            )
        lines.append("")

    if low:
        lines.append("## 待验证事件（单一来源）")
        lines.append("")
        lines.append(f"共 {len(low)} 个事件，仅显示前 20 个：")
        lines.append("")
        lines.append("| 事件 | 公司 | 日期 |")
        lines.append("|------|------|------|")
        for c in low[:20]:
            companies_str = ", ".join(sorted(c.companies))
            title_short = c.canonical_title[:50]
            if len(c.canonical_title) > 50:
                title_short += "..."
            lines.append(f"| {title_short} | {companies_str} | {c.first_date} |")
        lines.append("")

    report = "\n".join(lines)

    if output_path:
        output_path.write_text(report, encoding="utf-8")
        print(f"报告已保存: {output_path}")

    return report


# ── CLI ─────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="多源交叉验证")
    parser.add_argument("--company", type=str, help="指定公司")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument(
        "--threshold", type=float, default=0.6, help="标题相似度阈值 (默认: 0.6)"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览不生成报告")
    args = parser.parse_args()

    print("=" * 50)
    print("  多源交叉验证")
    print("=" * 50)

    # 收集条目
    print("\n收集时间线条目...")
    entries = collect_all_entries(args.company)
    print(f"  条目数: {len(entries)}")

    if not entries:
        print("  无条目可分析")
        return

    # 事件聚类
    print(f"\n事件聚类 (阈值: {args.threshold})...")
    clusters = cluster_events(entries, args.threshold)
    print(f"  事件数: {len(clusters)}")
    print(f"  平均来源数: {sum(c.source_count for c in clusters) / len(clusters):.1f}")

    # 统计
    high = [c for c in clusters if c.credibility.startswith("高")]
    medium = [c for c in clusters if c.credibility.startswith("中")]
    low = [c for c in clusters if c.credibility.startswith("待")]

    print(f"\n可信度分布:")
    print(f"  高(3+来源): {len(high)}")
    print(f"  中(2来源):  {len(medium)}")
    print(f"  待验证:     {len(low)}")

    if high:
        print(f"\nTop 5 高可信度事件:")
        for i, c in enumerate(high[:5], 1):
            title_short = c.canonical_title[:60]
            print(f"  {i}. [{c.source_count}来源] {title_short}")
            print(f"     公司: {', '.join(sorted(c.companies))}")

    # 生成报告
    if args.report and not args.dry_run:
        report_path = WIKI_ROOT / "cross_verify_report.md"
        generate_report(clusters, report_path)
        print(f"\n报告路径: {report_path}")
    elif args.dry_run:
        print(f"\n(DRY-RUN 模式，未生成报告)")


if __name__ == "__main__":
    main()
