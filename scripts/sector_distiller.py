#!/usr/bin/env python3
"""
sector_distiller.py — 行业蒸馏模块

从公司 wiki 的时间线条目中提取行业层面洞察，写入行业 wiki。

核心逻辑：
1. 对每个有公司的行业，读取其所有公司的最新时间线条目
2. 用 LLM 提取跨公司模式（市场趋势、竞争格局、技术动向等）
3. 将行业级洞察写入行业 wiki

用法：
    python3 scripts/sector_distiller.py                         # 处理所有行业
    python3 scripts/sector_distiller.py --sector 半导体设备      # 只处理指定行业
    python3 scripts/sector_distiller.py --dry-run               # 只打印不写入
    python3 scripts/sector_distiller.py --limit 3               # 最多处理 3 个行业
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from common import WIKI_ROOT

from llm_client import LLMClient, get_llm_client
from graph import Graph
from prompts import build_distillation_prompt
from ingest_v2 import add_timeline_entries
from batch_assessment import extract_timeline_entries
from log_writer import append_log


# 每个公司最多读取的最近条目数
MAX_ENTRIES_PER_COMPANY = 15
# 每个行业最多包含的公司数（取最近有更新的）
MAX_COMPANIES_PER_SECTOR = 10
# 每个 LLM 调用最多包含的总条目数（避免 token 超限）
MAX_TOTAL_ENTRIES = 80
# 行业蒸馏条目使用的 source_type
SOURCE_TYPE = "行业蒸馏"


def load_sector_wiki(sector_name: str) -> Optional[Path]:
    """获取行业 wiki 路径"""
    wiki_dir = WIKI_ROOT / "sectors" / sector_name / "wiki"
    if not wiki_dir.exists():
        return None
    wikis = list(wiki_dir.glob("*.md"))
    if not wikis:
        return None
    # 排除 _slides 文件
    wikis = [w for w in wikis if "_slides" not in w.name]
    return wikis[0] if wikis else None


def get_recent_company_entries(
    company_name: str,
    max_entries: int = MAX_ENTRIES_PER_COMPANY,
) -> List[Dict]:
    """获取公司 wiki 的最新时间线条目"""
    wiki_dir = WIKI_ROOT / "companies" / company_name / "wiki"
    if not wiki_dir.exists():
        return []
    wikis = list(wiki_dir.glob("*.md"))
    if not wikis:
        return []
    # 取第一个 wiki（通常是 公司动态.md）
    wiki_path = wikis[0]
    entries = extract_timeline_entries(wiki_path)
    # 取最新的 max_entries 条（时间线是倒序，前几条就是最新的）
    return entries[:max_entries]


def get_sector_companies(graph: Graph, sector_name: str) -> List[str]:
    """获取属于某行业的所有公司名称（含子行业）"""
    sector = graph.get_sector(sector_name)
    if not sector:
        return []

    companies = list(sector.get("companies", []))

    # 包含子行业的公司
    for sub_comps in sector.get("subsector_companies", {}).values():
        for c in sub_comps:
            if c not in companies:
                companies.append(c)

    return companies


def distill_sector(
    sector_name: str,
    graph: Graph,
    llm_client: LLMClient,
    dry_run: bool = False,
) -> Dict:
    """对单个行业执行蒸馏"""
    print(f"\n[{sector_name}]")

    # 获取行业信息
    sector = graph.get_sector(sector_name)
    if not sector:
        print("  -> SKIP | Sector not found in graph.yaml")
        return {"status": "skip", "reason": "not_found"}

    # 获取所属公司
    companies = get_sector_companies(graph, sector_name)
    if not companies:
        print("  -> SKIP | No companies in this sector")
        return {"status": "skip", "reason": "no_companies"}

    # 获取各公司最新的时间线条目
    company_entries = {}
    for cname in companies:
        entries = get_recent_company_entries(cname)
        if entries:
            company_entries[cname] = entries

    if not company_entries:
        print("  -> SKIP | No company wiki entries found")
        return {"status": "skip", "reason": "no_entries"}

    # 如果公司太多，按最近更新时间取前几个
    if len(company_entries) > MAX_COMPANIES_PER_SECTOR:
        # 按每个公司最新的条目日期排序
        sorted_companies = sorted(
            company_entries.items(),
            key=lambda x: x[1][0].get("date", ""),
            reverse=True,
        )
        company_entries = dict(sorted_companies[:MAX_COMPANIES_PER_SECTOR])

    # 如果总条目太多，按比例截断
    total_entries = sum(len(e) for e in company_entries.values())
    if total_entries > MAX_TOTAL_ENTRIES:
        ratio = MAX_TOTAL_ENTRIES / total_entries
        for cname in company_entries:
            limit = max(2, int(len(company_entries[cname]) * ratio))
            company_entries[cname] = company_entries[cname][:limit]
        total_entries = sum(len(e) for e in company_entries.values())

    # 获取行业 wiki 的现有评估
    sector_wiki = load_sector_wiki(sector_name)
    existing_assessment = ""
    if sector_wiki:
        content = sector_wiki.read_text(encoding="utf-8")
        pos = content.find("## 综合评估")
        if pos >= 0:
            m = re.search(r"> .+\n(?:> .+\n)*", content[pos:])
            if m:
                existing_assessment = m.group(0).strip()

    # 获取行业核心问题
    core_questions = sector.get("questions", [])

    # 构建 prompt 并调用 LLM
    prompt = build_distillation_prompt(
        sector_name, company_entries, core_questions, existing_assessment,
    )

    print(f"  Companies: {len(company_entries)}, Entries: {total_entries}")
    print("  Calling LLM...")

    if dry_run:
        print(f"  [DRY] Would call LLM with {total_entries} entries from {len(company_entries)} companies")
        return {"status": "dry_run", "insights": 0, "assessment": ""}

    response = llm_client.chat_with_retry(
        prompt,
        "你是一个专业的行业研究分析师。",
    )

    if not response.success:
        print("  -> ERR | LLM call failed")
        return {"status": "error", "reason": "llm_failed"}

    # 解析 JSON 输出
    content = response.content.strip()
    # 提取 JSON（处理 LLM 可能用 ```json 包裹的情况）
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        content = json_match.group(1).strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  -> ERR | JSON parse failed: {e}")
        return {"status": "error", "reason": f"json_parse: {e}"}

    insights = result.get("industry_insights", [])
    assessment_update = result.get("assessment_update", "")
    no_insights_reason = result.get("no_insights_reason", "")

    if not insights:
        print(f"  -> SKIP | {no_insights_reason or 'No industry insights extracted'}")
        return {"status": "skip", "reason": "no_insights", "detail": no_insights_reason}

    print(f"  Insights extracted: {len(insights)}")

    # 写入行业 wiki
    if sector_wiki:
        added = 0
        for insight in insights:
            title = insight.get("title", "行业洞察")
            date = insight.get("date", datetime.now().strftime("%Y-%m-%d"))
            key_points = insight.get("key_points", [])

            # 添加来源公司信息到 key_points
            source_companies = insight.get("source_companies", [])
            if source_companies:
                key_points.append(f"来源公司: {'/'.join(source_companies)}")

            entry = {
                "date": date,
                "title": title,
                "key_points": key_points,
                "source_type": SOURCE_TYPE,
            }

            added += add_timeline_entries(
                sector_wiki, [entry], source_file=None,
            )

        print(f"  -> OK | {added} entries written to sector wiki")

        # 如果有评估更新，写评估
        if assessment_update:
            from batch_assessment import add_assessment_section
            add_assessment_section(sector_wiki, assessment_update)
            print("  -> Assessment updated")

        return {
            "status": "success",
            "insights": len(insights),
            "added": added,
            "assessment": bool(assessment_update),
        }
    else:
        print("  -> SKIP | Sector wiki not found")
        return {"status": "skip", "reason": "no_wiki"}


def main():
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="行业蒸馏：从公司数据提取行业洞察")
    parser.add_argument("--sector", type=str, help="只处理指定行业")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写入")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个行业（0=不限）")
    args = parser.parse_args()

    print("=" * 50)
    print("  行业蒸馏模块")
    print("=" * 50)

    graph = Graph(str(WIKI_ROOT / "graph.yaml"))
    llm_client = get_llm_client()
    llm_client._max_tokens = 4096
    llm_client._timeout = 120

    # 获取所有行业
    all_sectors = graph.get_all_sectors()

    # 只处理有公司的核心行业（非 subsector）
    sectors = []
    for s in all_sectors:
        if args.sector and s != args.sector:
            continue
        companies = get_sector_companies(graph, s)
        if companies:
            sectors.append(s)

    if args.sector and not sectors:
        print(f"ERROR: Sector '{args.sector}' not found or has no companies")
        sys.exit(1)

    print(f"\nSectors to process: {len(sectors)}")

    if args.limit > 0:
        sectors = sectors[:args.limit]

    results = {"success": 0, "skip": 0, "error": 0}
    details = []

    for i, sname in enumerate(sectors, 1):
        print(f"\n[{i}/{len(sectors)}]", end="")
        result = distill_sector(sname, graph, llm_client, args.dry_run)
        status = result.get("status", "unknown")
        results[status] = results.get(status, 0) + 1
        details.append(f"{sname}: {status}")

    print("\n" + "=" * 50)
    print("  蒸馏完成")
    print(f"  成功: {results.get('success', 0)}")
    print(f"  跳过: {results.get('skip', 0)}")
    print(f"  错误: {results.get('error', 0)}")
    print("=" * 50)

    if not args.dry_run and results.get("success", 0) > 0:
        append_log("distill",
                   f"行业蒸馏: {results['success']} 行业完成")


if __name__ == "__main__":
    main()
