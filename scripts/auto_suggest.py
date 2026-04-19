#!/usr/bin/env python3
"""
auto_suggest.py — 用 LLM 发现未跟踪公司
把新闻给 LLM，让它识别其中提到的、我们没跟踪的公司。

用法：
    python3 scripts/auto_suggest.py                # 扫描并输出建议
    python3 scripts/auto_suggest.py --enrich       # 扫描后自动 enrich
"""

import argparse
import json
import os
import random
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
    system = "你是产业分析师。只输出 JSON，不要解释。"
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


def sample_news(wiki_root, max_files=30):
    """随机抽样新闻文件的标题和摘要"""
    samples = []
    news_files = list(wiki_root.glob("companies/*/raw/news/*.md"))
    random.shuffle(news_files)

    for f in news_files[:max_files]:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            # 取前 10 行（标题+摘要）
            lines = content.strip().split("\n")[:10]
            # 跳过 frontmatter
            if lines and lines[0].startswith("---"):
                end_idx = next((i for i, l in enumerate(lines) if i > 0 and l.startswith("---")), None)
                if end_idx:
                    lines = lines[end_idx+1:]
            text = " ".join(l.strip() for l in lines if l.strip())[:300]
            if text:
                company = f.parents[1].name
                samples.append(f"[{company}] {text}")
        except Exception:
            continue

    return samples


def discover_companies(graph, config):
    """用 LLM 从新闻中发现未跟踪公司"""
    known = set(graph._data.get("companies", {}).keys())

    # 抽样新闻
    news_samples = sample_news(WIKI_ROOT, max_files=25)
    news_text = "\n\n".join(news_samples[:20])

    # 获取现有行业列表
    sectors = [n for n, info in graph._data.get("nodes", {}).items()
               if info.get("type") == "sector"]

    prompt = f"""以下是多篇上市公司相关新闻的标题和摘要。

已跟踪的公司：{', '.join(sorted(known))}

已有的行业分类：{', '.join(sectors)}

请从新闻中找出：
1. 被频繁提及但不在"已跟踪公司"列表中的公司
2. 这些公司属于哪个已有行业（或需要新建什么行业）

新闻内容：
{news_text}

请以 JSON 格式输出：
{{
  "suggestions": [
    {{
      "name": "公司名",
      "reason": "为什么建议跟踪（一句话）",
      "sector": "所属行业（从已有行业中选，或建议新行业）",
      "estimated_ticker": "猜测的股票代码（如果能从新闻推断）"
    }}
  ]
}}

如果没有发现值得跟踪的新公司，输出 {{"suggestions": []}}。"""

    return call_llm(prompt, config)


def main():
    parser = argparse.ArgumentParser(description="LLM 驱动的新公司发现")
    parser.add_argument("--enrich", action="store_true", help="发现后自动 enrich")
    args = parser.parse_args()

    graph = Graph()
    config = load_config()

    print("正在用 LLM 分析新闻，发现未跟踪公司...")
    result = discover_companies(graph, config)

    if "error" in result:
        print(f"\nLLM error: {result['error']}")
        return

    suggestions = result.get("suggestions", [])

    if not suggestions:
        print("\n  没有发现值得跟踪的新公司。")
        return

    print(f"\n  发现 {len(suggestions)} 个建议跟踪的公司：\n")
    print(f"  {'公司名':<12} {'行业':<12} {'原因'}")
    print(f"  {'-'*12} {'-'*12} {'-'*40}")

    for s in suggestions:
        print(f"  {s['name']:<12} {s.get('sector', '?'):<12} {s.get('reason', '')[:40]}")

    if args.enrich:
        from enrich import enrich_company
        print(f"\n  自动 enrich...")
        for s in suggestions[:3]:
            ticker = s.get("estimated_ticker", "")
            if ticker:
                enrich_company(s["name"], ticker, graph, config)
            else:
                print(f"\n  跳过 {s['name']} — 无法推断股票代码")
                print(f"  手动添加: python3 scripts/enrich.py --company {s['name']} --ticker <CODE>")
    else:
        print(f"\n  添加公司:")
        for s in suggestions[:3]:
            ticker = s.get("estimated_ticker", "<CODE>")
            print(f"    python3 scripts/enrich.py --company {s['name']} --ticker {ticker}")


if __name__ == "__main__":
    main()
