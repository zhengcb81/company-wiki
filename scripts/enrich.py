#!/usr/bin/env python3
"""
enrich.py — 用 LLM 为新公司自动构建拓扑
给 LLM 公司名+现有行业图谱，让它决定归属。

用法：
    python3 scripts/enrich.py --company 寒武纪 --ticker 688256
    python3 scripts/enrich.py --company 寒武纪 --ticker 688256 --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph
from llm_client import get_llm_client


def load_config():
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def call_llm(prompt, config):
    """使用统一 LLM 客户端调用"""
    llm = get_llm_client()
    system = "你是产业分析师，负责将公司归类到产业链图谱中。只输出 JSON。"
    response = llm.chat_with_retry(prompt, system)
    if response.success:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": f"JSON parse failed: {content[:200]}"}
    return {"error": response.error}


def enrich(name, ticker, graph, config, dry_run=False):
    """用 LLM 分析公司并写入 graph.yaml"""
    if graph.get_company(name):
        print(f"  {name} 已在 graph.yaml 中")
        return False

    # 构建行业上下文
    sectors_info = []
    for n, info in graph._data.get("nodes", {}).items():
        if info.get("type") == "sector":
            desc = info.get("description", "")
            kws = ", ".join(info.get("keywords", [])[:5])
            comps = [c for c, ci in graph._data.get("companies", {}).items()
                     if n in ci.get("sectors", [])]
            sectors_info.append(f"  {n}: {desc}\n    关键词: {kws}\n    已有公司: {', '.join(comps[:5])}")

    # 构建已有公司列表
    known_companies = sorted(graph._data.get("companies", {}).keys())

    prompt = f"""请将以下公司归类到我们的产业链图谱中。

公司: {name}
股票代码: {ticker}

现有行业:
{chr(10).join(sectors_info)}

已有跟踪的公司: {', '.join(known_companies)}

请分析 {name} 的主营业务，确定：
1. 属于哪个现有行业（可多选）
2. 属于哪个现有主题
3. 在已有公司中，哪些是它的竞争对手
4. 推荐 3-4 个日常新闻搜索关键词
5. 一句话描述它在行业中的位置

如果你了解这家公司的业务，请直接输出 JSON。
如果你不确定，请在 position 中说明。

JSON 格式:
{{
  "exchange": "SSE STAR/SZSE/SSE/HKEX/NASDAQ",
  "position": "一句话定位",
  "sectors": ["行业1", "行业2"],
  "themes": ["主题1"],
  "news_queries": ["关键词1 最新消息", "关键词2"],
  "competes_with": ["竞争对手1", "竞争对手2"],
  "keywords": ["用于新闻匹配的关键词"]
}}"""

    print(f"\n  [LLM] 分析 {name} ({ticker})...")
    proposal = call_llm(prompt, config)

    if "error" in proposal:
        print(f"  LLM error: {proposal['error']}")
        return False

    # 展示
    print(f"  定位: {proposal.get('position', '?')}")
    print(f"  行业: {proposal.get('sectors', [])}")
    print(f"  主题: {proposal.get('themes', [])}")
    print(f"  搜索词: {proposal.get('news_queries', [])}")
    if proposal.get("competes_with"):
        print(f"  竞争对手: {proposal['competes_with']}")

    if dry_run:
        print(f"\n  [DRY RUN] 未写入")
        return False

    # 写入 graph.yaml
    new_sector = None
    for s in proposal.get("sectors", []):
        if s not in graph._data.get("nodes", {}):
            new_sector = s
            graph.add_node(s, "sector",
                          description=f"{s}行业",
                          keywords=proposal.get("keywords", []),
                          parent_theme=proposal.get("themes", [])[:1])

    graph.add_company(
        name=name, ticker=ticker,
        exchange=proposal.get("exchange", "SZSE"),
        sectors=proposal.get("sectors", []),
        themes=proposal.get("themes", []),
        news_queries=proposal.get("news_queries", [f"{name} 最新消息"]),
        position=proposal.get("position", ""),
        competes_with=proposal.get("competes_with"),
    )

    graph.save()
    print(f"\n  ✅ 已添加到 graph.yaml")

    # 创建目录
    for sub in ["raw/news", "wiki"]:
        (WIKI_ROOT / "companies" / name / sub).mkdir(parents=True, exist_ok=True)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", type=str, required=True)
    parser.add_argument("--ticker", type=str, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    graph = Graph()
    config = load_config()
    enrich(args.company, args.ticker, graph, config, args.dry_run)


if __name__ == "__main__":
    main()
