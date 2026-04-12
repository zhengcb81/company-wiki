#!/usr/bin/env python3
"""
enrich.py — 新公司自动拓扑发现
给定公司名+股票代码，自动搜索业务信息，匹配行业，生成图更新提案。

用法：
    # 交互式：搜索 → LLM分析 → 确认 → 写入 graph.yaml
    python3 scripts/enrich.py --company 寒武纪 --ticker 688256

    # 批量模式：从文件读取公司列表
    python3 scripts/enrich.py --batch companies_to_add.txt

    # 仅搜索（不写入）
    python3 scripts/enrich.py --company 寒武纪 --ticker 688256 --dry-run

companies_to_add.txt 格式（每行一个）：
    寒武纪,688256
    海光信息,688041
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def load_config():
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Tavily 搜索 ───────────────────────────
def search_company_info(name, ticker, api_key):
    """搜索公司业务信息"""
    queries = [
        f"{name} 主营业务 简介",
        f"{name} {ticker} 行业 竞争对手",
    ]
    all_results = []

    for query in queries:
        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "query": query,
            "max_results": 5,
            "search_depth": "basic",
            "include_answer": True,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {api_key}")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("answer"):
                    all_results.append(f"[搜索摘要] {data['answer']}")
                for r in data.get("results", []):
                    all_results.append(f"- {r.get('title', '')}: {r.get('content', '')[:200]}")
        except Exception as e:
            all_results.append(f"[搜索失败: {e}]")

    return "\n".join(all_results)


# ── LLM 分析 ──────────────────────────────
def analyze_with_llm(name, ticker, search_results, graph, config):
    """用 DeepSeek 分析公司应该属于哪些行业"""
    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key", "")
    model = llm_cfg.get("model", "deepseek-reasoner")
    base_url = llm_cfg.get("base_url", "https://api.deepseek.com")

    # 构建现有行业的上下文
    sectors = []
    for s_name, s_info in graph._data.get("nodes", {}).items():
        if s_info.get("type") == "sector":
            desc = s_info.get("description", "")
            keywords = s_info.get("keywords", [])
            sectors.append(f"- {s_name}: {desc} (关键词: {', '.join(keywords[:5])})")

    themes = []
    for t_name, t_info in graph._data.get("nodes", {}).items():
        if t_info.get("type") == "theme":
            themes.append(f"- {t_name}: {t_info.get('description', '')}")

    prompt = f"""请分析以下公司，确定其在产业链中的位置。

公司: {name} (股票代码: {ticker})

搜索到的业务信息:
{search_results}

现有行业:
{chr(10).join(sectors)}

现有主题:
{chr(10).join(themes)}

请以 JSON 格式输出（不要输出其他内容）:
{{
  "exchange": "SSE STAR/SZSE/SSE/HKEX/NASDAQ/...",
  "position": "一句话描述公司在行业中的位置",
  "sectors": ["从现有行业中选择，可多选"],
  "themes": ["从现有主题中选择"],
  "news_queries": ["3-4个搜索关键词，用于日常新闻采集"],
  "competes_with": ["在现有公司中找到的竞争对手"],
  "suggested_new_sector": null 或 "如果现有行业都不匹配，建议新行业名",
  "keywords": ["5-8个关键词，用于新闻相关性匹配"]
}}
"""

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个产业分析师，负责将公司归类到产业链中。只输出 JSON，不要解释。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        # 提取 JSON（可能被 ```json 包裹）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


# ── 写入 graph.yaml ───────────────────────
def apply_enrichment(name, ticker, proposal, graph, dry_run=False):
    """将分析结果写入 graph.yaml"""
    exchange = proposal.get("exchange", "SZSE")
    position = proposal.get("position", "")
    sectors = proposal.get("sectors", [])
    themes = proposal.get("themes", [])
    news_queries = proposal.get("news_queries", [f"{name} 最新消息"])
    competes_with = proposal.get("competes_with", [])
    keywords = proposal.get("keywords", [])
    new_sector = proposal.get("suggested_new_sector")

    if dry_run:
        print(f"\n  [DRY RUN] Would add:")
        print(f"    {name} ({ticker}) on {exchange}")
        print(f"    sectors: {sectors}")
        print(f"    themes: {themes}")
        print(f"    news_queries: {news_queries}")
        print(f"    position: {position}")
        if competes_with:
            print(f"    competes_with: {competes_with}")
        if new_sector:
            print(f"    NEW SECTOR needed: {new_sector}")
        return False

    # 添加新行业（如果需要）
    if new_sector and new_sector not in graph._data.get("nodes", {}):
        graph.add_node(new_sector, "sector", parent_theme=themes[:1] if themes else None,
                       keywords=keywords)
        print(f"  Added new sector: {new_sector}")

    # 添加公司
    graph.add_company(
        name=name, ticker=ticker, exchange=exchange,
        sectors=sectors, themes=themes,
        news_queries=news_queries, position=position,
        competes_with=competes_with if competes_with else None,
    )

    # 添加关键词到现有行业节点（如果行业节点缺少关键词）
    for sector_name in sectors:
        node = graph._data.get("nodes", {}).get(sector_name, {})
        if not node.get("keywords"):
            node["keywords"] = [sector_name] + [kw for kw in keywords if kw != sector_name]

    graph.save()
    print(f"  Added to graph.yaml: {name}")

    # 创建目录
    for subdir in ["raw/news", "wiki"]:
        (WIKI_ROOT / "companies" / name / subdir).mkdir(parents=True, exist_ok=True)

    return True


# ── 主流程 ────────────────────────────────
def enrich_company(name, ticker, graph, config, dry_run=False):
    """完整的公司 enrich 流程"""
    print(f"\n{'='*50}")
    print(f"  Enriching: {name} ({ticker})")
    print(f"{'='*50}")

    # 检查是否已存在
    if graph.get_company(name):
        print(f"  Already in graph.yaml, skipping")
        return False

    # 1. 搜索业务信息
    api_key = config.get("search", {}).get("tavily_api_key", "")
    print(f"\n  [1/3] Searching company info...")
    search_results = search_company_info(name, ticker, api_key)
    print(f"    Found {len(search_results.split(chr(10)))} results")

    # 2. LLM 分析
    print(f"  [2/3] Analyzing with LLM...")
    proposal = analyze_with_llm(name, ticker, search_results, graph, config)

    if "error" in proposal:
        print(f"    LLM error: {proposal['error']}")
        return False

    # 3. 展示结果
    print(f"\n  [3/3] Proposal:")
    print(f"    exchange: {proposal.get('exchange')}")
    print(f"    position: {proposal.get('position')}")
    print(f"    sectors: {proposal.get('sectors')}")
    print(f"    themes: {proposal.get('themes')}")
    print(f"    news_queries: {proposal.get('news_queries')}")
    if proposal.get("competes_with"):
        print(f"    competes_with: {proposal.get('competes_with')}")
    if proposal.get("suggested_new_sector"):
        print(f"    ⚠️  needs new sector: {proposal.get('suggested_new_sector')}")

    # 4. 写入
    return apply_enrichment(name, ticker, proposal, graph, dry_run)


def main():
    parser = argparse.ArgumentParser(description="新公司自动拓扑发现")
    parser.add_argument("--company", type=str, help="公司名")
    parser.add_argument("--ticker", type=str, help="股票代码")
    parser.add_argument("--batch", type=str, help="批量文件（每行: 公司名,股票代码）")
    parser.add_argument("--dry-run", action="store_true", help="只分析不写入")
    args = parser.parse_args()

    graph = Graph()
    config = load_config()

    if args.batch:
        with open(args.batch, "r") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        for line in lines:
            parts = line.split(",")
            name, ticker = parts[0].strip(), parts[1].strip()
            enrich_company(name, ticker, graph, config, args.dry_run)
    elif args.company and args.ticker:
        enrich_company(args.company, args.ticker, graph, config, args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
