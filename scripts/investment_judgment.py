#!/usr/bin/env python3
"""
investment_judgment.py — 投资判断层

从现有 wiki 时间线条目中提取财务数据、未来事件、风险信号，
生成 3 个结构化 wiki 页面（零 LLM 成本，纯正则提取）：

1. 投资估值.md — 历史财务数据追踪
2. 催化剂日历.md — 未来事件时间表
3. 风险雷达.md — 风险信号仪表盘

用法：
    python scripts/investment_judgment.py --company 中微公司
    python scripts/investment_judgment.py --company 中微公司 --page 估值
    python scripts/investment_judgment.py --all-companies
    python scripts/investment_judgment.py --company 中微公司 --dry-run
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Windows 控制台 UTF-8 编码
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


# ── 正则模式 ──────────────────────────────

FINANCIAL_PATTERNS: Dict[str, str] = {
    "营收": r'营收[额约]?(\d+\.?\d*)\s*亿',
    "净利润": r'净利润[约]?(\d+\.?\d*)\s*亿',
    "研发投入": r'研发[投入费用]?[约]?(\d+\.?\d*)\s*亿',
    "毛利率": r'毛利率[约]?(\d+\.?\d*)\s*%',
    "每股收益": r'每股收益[约]?(\d+\.?\d*)\s*元',
    "净利率": r'净利率[约]?(\d+\.?\d*)\s*%',
    "扣非净利润": r'扣[除非]?净利润[约]?(\d+\.?\d*)\s*亿',
    "经营现金流": r'经营[活动]?现金流[量净额约]?(\d+\.?\d*)\s*亿',
}

FUTURE_INDICATORS = [
    "将", "预计", "计划", "目标", "有望", "预期", "拟",
    "布局", "推进", "规划", "承诺", "指引",
]

FUTURE_YEAR_PATTERN = re.compile(r'(20[2-9]\d)年(?:[QH][1-4]|下半年|上半年)?')

RISK_PATTERNS: List[Tuple[str, str]] = [
    (r'(?:亏损|下降|减少|下滑|负增长)(?!.*(?:收窄|改善|好转|缓解))', "财务风险"),
    (r'(?:依赖|集中|单一).{0,10}(?:客户|供应商|产品|业务)', "运营风险"),
    (r'(?:政策|监管|制裁|管制|关税)', "外部风险"),
    (r'(?<!突破|克服|解决)(?:替代|落后|瓶颈|挑战)', "技术风险"),
    (r'(?:诉讼|纠纷|违规|处罚)', "合规风险"),
    (r'(?:质押|减持|套现)', "股东风险"),
]

SEVERITY_KEYWORDS = {
    "高": ["严重", "重大", "显著", "大幅", "巨额", "危机"],
    "中": ["值得关注", "值得警惕", "需关注", "压力", "承压"],
}


# ── 时间线条目解析 ────────────────────────

def parse_timeline_entries(wiki_path: Path) -> List[Dict]:
    """
    解析 wiki 页面的时间线条目。

    Args:
        wiki_path: wiki 文件路径

    Returns:
        条目列表，每个条目含 date, title, key_points, source_url
    """
    if not wiki_path.exists():
        return []

    content = wiki_path.read_text(encoding="utf-8")

    entries = []
    # 匹配时间线条目：### YYYY-MM-DD | source_type | title
    # 后跟 - 开头的要点行，直到下一个 ### 或 ##
    entry_pattern = re.compile(
        r'^### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)$\n'
        r'((?:^- .+$\n?)*)',
        re.MULTILINE
    )

    for match in entry_pattern.finditer(content):
        date = match.group(1)
        source_type = match.group(2).strip()
        title = match.group(3).strip()
        body = match.group(4)

        # 解析要点和来源链接
        points = []
        source_url = ""
        for line in body.strip().split("\n"):
            line = line.strip()
            if line.startswith("- [来源]"):
                # 提取来源链接
                src_match = re.search(r'\[来源\]\((.+?)\)', line)
                if src_match:
                    source_url = src_match.group(1)
            elif line.startswith("- "):
                points.append(line[2:])

        entries.append({
            "date": date,
            "source_type": source_type,
            "title": title,
            "key_points": points,
            "source_url": source_url,
        })

    return entries


def get_entry_source_url(entry: Dict, wiki_path: Path) -> str:
    """
    获取条目的来源链接（保持相对路径）。

    Args:
        entry: 时间线条目
        wiki_path: wiki 文件路径

    Returns:
        来源链接（相对路径）
    """
    return entry.get("source_url", "")


# ── 财务数据提取 ──────────────────────────

def extract_financial_data(entries: List[Dict], wiki_path: Path) -> List[Dict]:
    """
    从时间线条目中提取财务指标数据。

    Args:
        entries: 时间线条目列表
        wiki_path: wiki 文件路径，用于构建来源链接

    Returns:
        财务数据列表 [{date, metric, value, unit, source_url}]
    """
    results = []
    seen = set()  # 去重 (date, metric, value)

    for entry in entries:
        date = entry["date"]
        for point in entry["key_points"]:
            for metric_name, pattern in FINANCIAL_PATTERNS.items():
                match = re.search(pattern, point)
                if match:
                    value = match.group(1)
                    key = (date, metric_name, value)
                    if key not in seen:
                        seen.add(key)
                        # 判断单位
                        unit = "亿元" if "亿" in pattern else "%"
                        if "元" in pattern:
                            unit = "元"
                        results.append({
                            "date": date,
                            "metric": metric_name,
                            "value": value,
                            "unit": unit,
                            "source_url": get_entry_source_url(entry, wiki_path),
                        })

    # 按日期排序
    results.sort(key=lambda x: x["date"])
    return results


# ── 催化剂提取 ────────────────────────────

def extract_catalysts(entries: List[Dict], wiki_path: Path) -> List[Dict]:
    """
    从时间线条目中提取未来事件（催化剂）。

    Args:
        entries: 时间线条目列表
        wiki_path: wiki 文件路径

    Returns:
        催化剂列表 [{expected_time, event, event_type, source_url}]
    """
    results = []
    seen_titles = set()

    for entry in entries:
        title = entry["title"]

        # 检查标题是否包含未来时态关键词
        has_future = any(kw in title for kw in FUTURE_INDICATORS)
        has_future_year = FUTURE_YEAR_PATTERN.search(title)

        # 也检查要点
        point_text = " ".join(entry["key_points"])
        has_future_point = any(kw in point_text for kw in FUTURE_INDICATORS)
        future_year_point = FUTURE_YEAR_PATTERN.search(point_text) if not has_future_year else None

        if not (has_future or has_future_year or has_future_point or future_year_point):
            continue

        # 去重：相似标题跳过
        title_key = title[:30]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # 确定事件类型
        event_type = "其他"
        type_keywords = {
            "产品": ["发布", "推出", "量产", "产品"],
            "产能": ["产能", "投产", "扩产", "工厂"],
            "研发": ["研发", "技术", "突破", "流片"],
            "政策": ["政策", "补贴", "标准", "许可"],
            "市场": ["订单", "合同", "客户", "市场"],
        }
        combined = title + " " + point_text
        for ttype, kws in type_keywords.items():
            if any(kw in combined for kw in kws):
                event_type = ttype
                break

        # 提取预计时间
        expected_time = entry["date"]
        fy = has_future_year or future_year_point
        if fy:
            expected_time = fy.group(0)

        results.append({
            "expected_time": expected_time,
            "event": title,
            "event_type": event_type,
            "detail": point_text[:100] if point_text else "",
            "source_url": get_entry_source_url(entry, wiki_path),
        })

    # 按预计时间排序
    results.sort(key=lambda x: x["expected_time"])
    return results


# ── 风险信号提取 ──────────────────────────

def classify_severity(text: str) -> str:
    """根据文本判断风险严重程度"""
    for sev, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return sev
    return "低"


def extract_risks(entries: List[Dict], wiki_path: Path) -> List[Dict]:
    """
    从时间线条目中提取风险信号。

    Args:
        entries: 时间线条目列表
        wiki_path: wiki 文件路径

    Returns:
        风险列表 [{risk_type, description, severity, source_url}]
    """
    results = []
    seen = set()

    for entry in entries:
        combined = entry["title"] + " " + " ".join(entry["key_points"])

        for pattern, risk_type in RISK_PATTERNS:
            for match in re.finditer(pattern, combined):
                # 提取匹配行上下文
                start = max(0, match.start() - 20)
                end = min(len(combined), match.end() + 30)
                context = combined[start:end].strip()

                # 去重
                key = (risk_type, context[:50])
                if key in seen:
                    continue
                seen.add(key)

                severity = classify_severity(context)

                results.append({
                    "risk_type": risk_type,
                    "description": context,
                    "severity": severity,
                    "date": entry["date"],
                    "source_url": get_entry_source_url(entry, wiki_path),
                })

    # 按严重程度排序：高 > 中 > 低
    severity_order = {"高": 0, "中": 1, "低": 2}
    results.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["date"]))
    return results


# ── Wiki 页面生成 ─────────────────────────

def build_frontmatter(title: str, entity: str, tags: List[str] = None) -> str:
    """构建 YAML frontmatter"""
    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"entity: \"{entity}\"")
    lines.append("type: company_topic")
    lines.append(f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"')
    lines.append(f"tags: [{', '.join(tags or [])}]")
    lines.append("---")
    return "\n".join(lines)


def generate_valuation_page(company_name: str, wiki_dir: Path,
                            dry_run: bool = False) -> Dict:
    """
    生成投资估值.md — 历史财务数据追踪。

    Args:
        company_name: 公司名
        wiki_dir: wiki 目录路径 (companies/{name}/wiki/)
        dry_run: 仅预览不写入

    Returns:
        {status, path, metrics_count, error}
    """
    wiki_path = wiki_dir / "公司动态.md"
    if not wiki_path.exists():
        return {"status": "skip", "error": "公司动态.md not found"}

    entries = parse_timeline_entries(wiki_path)
    if not entries:
        return {"status": "skip", "error": "No timeline entries"}

    financial_data = extract_financial_data(entries, wiki_path)
    if not financial_data:
        return {"status": "skip", "error": "No financial data found"}

    # 构建页面
    lines = []
    lines.append(build_frontmatter("投资估值", company_name))
    lines.append("")
    lines.append(f"# {company_name} — [[投资估值]]")
    lines.append("")
    lines.append("## 历史财务数据")
    lines.append("")
    lines.append("| 日期 | 指标 | 数值 | 来源 |")
    lines.append("|------|------|------|------|")

    for item in financial_data:
        src = item.get("source_url", "")
        src_link = f"[链接]({src})" if src else "-"
        lines.append(f"| {item['date']} | {item['metric']} | {item['value']}{item['unit']} | {src_link} |")

    # 趋势分析
    lines.append("")
    lines.append("## 趋势分析")
    lines.append("")

    # 按指标分组做趋势描述
    by_metric = defaultdict(list)
    for item in financial_data:
        by_metric[item["metric"]].append(item)

    for metric, items in by_metric.items():
        values = [float(it["value"]) for it in items if it["value"].replace(".", "").isdigit()]
        if len(values) >= 2:
            trend = "增长" if values[-1] > values[0] else "下降"
            lines.append(f"- **{metric}**: 从 {items[0]['value']}{items[0]['unit']} → {items[-1]['value']}{items[-1]['unit']} ({trend}趋势)")
        elif values:
            lines.append(f"- **{metric}**: {items[0]['value']}{items[0]['unit']}")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n  [DRY] 投资估值.md — {len(financial_data)} 条数据")
        return {"status": "dry_run", "metrics_count": len(financial_data), "content": content}

    output_path = wiki_dir / "投资估值.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  [OK] 投资估值.md — {len(financial_data)} 条数据")
    return {"status": "success", "path": str(output_path), "metrics_count": len(financial_data)}


def generate_catalyst_page(company_name: str, wiki_dir: Path,
                           dry_run: bool = False) -> Dict:
    """
    生成催化剂日历.md — 未来事件时间表。

    Args:
        company_name: 公司名
        wiki_dir: wiki 目录路径
        dry_run: 仅预览不写入

    Returns:
        {status, path, catalyst_count, error}
    """
    wiki_path = wiki_dir / "公司动态.md"
    if not wiki_path.exists():
        return {"status": "skip", "error": "公司动态.md not found"}

    entries = parse_timeline_entries(wiki_path)
    if not entries:
        return {"status": "skip", "error": "No timeline entries"}

    catalysts = extract_catalysts(entries, wiki_path)
    if not catalysts:
        return {"status": "skip", "error": "No catalyst events found"}

    # 构建页面
    lines = []
    lines.append(build_frontmatter("催化剂日历", company_name))
    lines.append("")
    lines.append(f"# {company_name} — [[催化剂日历]]")
    lines.append("")
    lines.append("## 未来催化剂")
    lines.append("")
    lines.append("| 预计时间 | 事件 | 类型 | 来源 |")
    lines.append("|---------|------|------|------|")

    for item in catalysts:
        src = item.get("source_url", "")
        src_link = f"[链接]({src})" if src else "-"
        event_text = item["event"][:50] + "..." if len(item["event"]) > 50 else item["event"]
        lines.append(f"| {item['expected_time']} | {event_text} | {item['event_type']} | {src_link} |")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n  [DRY] 催化剂日历.md — {len(catalysts)} 个事件")
        return {"status": "dry_run", "catalyst_count": len(catalysts), "content": content}

    output_path = wiki_dir / "催化剂日历.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  [OK] 催化剂日历.md — {len(catalysts)} 个事件")
    return {"status": "success", "path": str(output_path), "catalyst_count": len(catalysts)}


def generate_risk_page(company_name: str, wiki_dir: Path,
                       dry_run: bool = False) -> Dict:
    """
    生成风险雷达.md — 风险信号仪表盘。

    Args:
        company_name: 公司名
        wiki_dir: wiki 目录路径
        dry_run: 仅预览不写入

    Returns:
        {status, path, risk_count, error}
    """
    wiki_path = wiki_dir / "公司动态.md"
    if not wiki_path.exists():
        return {"status": "skip", "error": "公司动态.md not found"}

    entries = parse_timeline_entries(wiki_path)
    if not entries:
        return {"status": "skip", "error": "No timeline entries"}

    risks = extract_risks(entries, wiki_path)
    if not risks:
        return {"status": "skip", "error": "No risk signals found"}

    # 构建页面
    lines = []
    lines.append(build_frontmatter("风险雷达", company_name))
    lines.append("")
    lines.append(f"# {company_name} — [[风险雷达]]")
    lines.append("")
    lines.append("## 风险信号")
    lines.append("")
    lines.append("| 风险类型 | 描述 | 严重程度 | 来源 |")
    lines.append("|---------|------|---------|------|")

    for item in risks:
        src = item.get("source_url", "")
        src_link = f"[链接]({src})" if src else "-"
        severity_badge = item["severity"]
        lines.append(f"| {item['risk_type']} | {item['description'][:60]} | {severity_badge} | {src_link} |")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n  [DRY] 风险雷达.md — {len(risks)} 个信号")
        high_count = sum(1 for r in risks if r["severity"] == "高")
        print(f"    - 高风险: {high_count}")
        return {"status": "dry_run", "risk_count": len(risks), "high_count": high_count, "content": content}

    output_path = wiki_dir / "风险雷达.md"
    output_path.write_text(content, encoding="utf-8")
    high_count = sum(1 for r in risks if r["severity"] == "高")
    print(f"  [OK] 风险雷达.md — {len(risks)} 个信号 ({high_count} 高风险)")
    return {"status": "success", "path": str(output_path), "risk_count": len(risks), "high_count": high_count}


def generate_all(company_name: str, wiki_root: Path,
                 pages: Optional[List[str]] = None,
                 dry_run: bool = False) -> Dict:
    """
    为公司生成所有投资判断页面。

    Args:
        company_name: 公司名
        wiki_root: 项目根目录
        pages: 要生成的页面列表 (默认全部)
        dry_run: 仅预览不写入

    Returns:
        汇总结果
    """
    wiki_dir = wiki_root / "companies" / company_name / "wiki"
    if not wiki_dir.exists():
        return {"status": "error", "error": f"Wiki directory not found: {wiki_dir}"}

    if pages is None:
        pages = ["估值", "催化剂", "风险"]

    results = {}
    if "估值" in pages:
        results["valuation"] = generate_valuation_page(company_name, wiki_dir, dry_run)
    if "催化剂" in pages:
        results["catalyst"] = generate_catalyst_page(company_name, wiki_dir, dry_run)
    if "风险" in pages:
        results["risk"] = generate_risk_page(company_name, wiki_dir, dry_run)

    summary = {
        "company": company_name,
        "results": results,
    }
    return summary


# ── CLI ─────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="投资判断层 — 生成投资估值/催化剂日历/风险雷达页面")
    parser.add_argument("--company", type=str, help="公司名")
    parser.add_argument("--all-companies", action="store_true", help="批量处理所有公司")
    parser.add_argument("--page", type=str, choices=["估值", "催化剂", "风险"],
                        help="指定生成的页面类型（默认全部）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写入")
    args = parser.parse_args()

    if not args.company and not args.all_companies:
        parser.print_help()
        return

    graph = Graph(str(WIKI_ROOT / "graph.yaml"))

    companies = []
    if args.all_companies:
        companies = [c["name"] for c in graph.get_all_companies()]
        print(f"\n批量处理 {len(companies)} 家公司...")
    elif args.company:
        companies = [args.company]

    pages = [args.page] if args.page else None
    total_results = {"success": 0, "skip": 0, "error": 0, "total_metrics": 0}

    for company in companies:
        print(f"\n{'=' * 40}")
        print(f"  {company}")
        print(f"{'=' * 40}")

        result = generate_all(company, WIKI_ROOT, pages, args.dry_run)

        page_results = result.get("results", {})
        if not page_results:
            total_results["error"] += 1
            continue

        for page_name, page_result in page_results.items():
            status = page_result.get("status", "unknown")
            if status in ("success", "dry_run"):
                total_results["success"] += 1
                if "metrics_count" in page_result:
                    total_results["total_metrics"] += page_result["metrics_count"]
            elif status == "skip":
                total_results["skip"] += 1
            else:
                total_results["error"] += 1

    mode = " (DRY-RUN)" if args.dry_run else ""
    print(f"\n{'=' * 40}")
    print(f"  完成{mode}")
    print(f"  公司: {len(companies)}")
    print(f"  成功: {total_results['success']}")
    print(f"  跳过: {total_results['skip']}")
    print(f"  错误: {total_results['error']}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
