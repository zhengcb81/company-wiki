#!/usr/bin/env python3
"""
collect_news.py — 新闻采集模块
使用 Tavily 搜索引擎，从 config.yaml 读取公司列表和搜索关键词，
采集最近的新闻并保存到对应公司的 raw/news/ 目录。

用法：
    python3 scripts/collect_news.py                    # 采集所有公司
    python3 scripts/collect_news.py --company 中微公司   # 只采集指定公司
    python3 scripts/collect_news.py --dry-run           # 只打印，不保存
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ── 路径 ──────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph
from config_rules_loader import RulesConfig

# ── 简易 YAML 解析（避免依赖 pyyaml）───────
def load_yaml_simple(path):
    """
    极简 YAML 解析器，只处理 config.yaml 中用到的结构。
    对于复杂嵌套，回退到尝试 import pyyaml。
    """
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        pass

    # 回退：用正则从 JSON-like 区块解析
    # 实际上我们的 config 结构复杂，还是用 json trick
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 尝试把 YAML 转成 JSON（只处理我们的特定格式）
    # 简单方案：直接 import json，手动解析
    try:
        import json as _json
        # 这个回退方案太脆弱，推荐安装 pyyaml
        print("WARNING: pyyaml not installed. Trying json fallback...")
        print("  Install with: pip install pyyaml")
        # 尝试最简解析
        return _minimal_yaml_parse(content)
    except Exception as e:
        print(f"ERROR: Cannot parse config.yaml: {e}")
        print("  Please install pyyaml: pip install pyyaml")
        sys.exit(1)


def _minimal_yaml_parse(content):
    """极简 YAML 解析 — 只处理 config.yaml 的特定格式"""
    import json

    # 移除注释
    lines = content.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # 移除行内注释（但保留引号内的 #）
        if "#" in line and not ('"' in line or "'" in line):
            line = line[:line.index("#")]
        clean_lines.append(line)

    content = "\n".join(clean_lines)

    # 用缩进推断结构太复杂，直接提示安装 pyyaml
    print("ERROR: Minimal YAML parser cannot handle this config.")
    print("  Please install pyyaml: pip install pyyaml")
    sys.exit(1)


def load_config():
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}")
        sys.exit(1)

    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        print("ERROR: pyyaml is required. Install with: pip install pyyaml")
        print("  Or: python3 -m pip install pyyaml")
        sys.exit(1)


# ── Tavily 搜索 ───────────────────────────
def tavily_search(query, api_key, max_results=8, days=7, language="zh"):
    """
    调用 Tavily Search API。
    返回结果列表: [{title, url, content, published_date}, ...]
    """
    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "days": days,
        "topic": "general",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  Tavily API error {e.code}: {body}")
        return []
    except Exception as e:
        print(f"  Tavily request failed: {e}")
        return []


# ── 去重 ──────────────────────────────────
def load_existing_urls(news_dir):
    """扫描已有的 news 文件，提取所有已采集的 URL"""
    urls = set()
    if not news_dir.exists():
        return urls

    for f in news_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            # 从 frontmatter 中提取 url
            for line in content.split("\n"):
                if line.startswith("source_url:"):
                    url = line.split(":", 1)[1].strip().strip('"').strip("'")
                    urls.add(url)
        except Exception:
            continue
    return urls


def has_mojibake(text):
    """检测文本是否包含乱码（mojibake），避免将损坏内容入库"""
    if not text:
        return False
    # Unicode replacement character（UTF-8 解码失败的标志）
    if '\ufffd' in text:
        return True
    # 连续的 Latin-1 补充字符（常见于 UTF-8 被错误解读为 Latin-1）
    if re.search(r'[\u00c0-\u00ff]{4,}', text):
        return True
    return False


def save_news_item(company_name, result, news_dir, rules=None):
    """
    将一条搜索结果保存为 markdown 文件。
    文件名格式: YYYY-MM-DD_{hash8}_{safe_title}.md
    在写入前执行质量预过滤，从源头拦截垃圾数据。
    """
    title = result.get("title", "untitled")
    url = result.get("url", "")
    content = result.get("content", "")
    published = result.get("published_date", "")

    # 编码质量门禁：跳过乱码内容
    if has_mojibake(content) or has_mojibake(title):
        return False

    # 质量预过滤（在写入文件之前拦截垃圾数据）
    if rules:
        # URL 黑名单检查
        if rules.is_url_blacklisted(url):
            return False

        # 标题黑名单检查
        if rules.is_title_blacklisted(title):
            return False

        # 最低内容长度检查
        cq = rules.get_collection_quality()
        min_content = cq.get("min_content_length", 100)
        min_title = cq.get("min_title_length", 10)

        if len(content) < min_content:
            # 内容太短，且标题=公司名 → 大概率是公司主页
            if cq.get("skip_if_title_equals_company", True):
                title_clean = title.replace(" ", "").replace("-", "")
                company_clean = company_name.replace(" ", "")
                if title_clean == company_clean or len(title) < min_title:
                    return False

    # 解析日期
    if published:
        try:
            # Tavily 返回格式可能是 ISO 或其他
            date_str = published[:10]  # 取 YYYY-MM-DD 部分
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 生成文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:40]
    filename = f"{date_str}_{url_hash}_{safe_title}.md"
    filepath = news_dir / filename

    # 如果文件已存在则跳过
    if filepath.exists():
        return False

    # 写入 markdown
    md = f"""---
title: "{title}"
source_url: "{url}"
published_date: "{date_str}"
collected_date: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
company: "{company_name}"
type: news
---

# {title}

{content}

---
来源: {url}
"""
    filepath.write_text(md, encoding="utf-8")
    return True


# ── 主流程 ────────────────────────────────
def load_search_config():
    """从 config.yaml 读取搜索运维配置（API key 等）"""
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("search", {})


def collect_for_company(company, search_cfg, dry_run=False, rules=None):
    """为单个公司采集新闻"""
    name = company["name"]
    queries = company.get("news_queries", [f"{name} 最新消息"])

    api_key = search_cfg.get("tavily_api_key", "")
    if not api_key:
        print(f"  ERROR: No Tavily API key in config.yaml")
        return 0, 0

    max_results = search_cfg.get("results_per_query", 8)
    days = search_cfg.get("max_age_days", 7)

    # 目标目录
    news_dir = WIKI_ROOT / "companies" / name / "raw" / "news"
    if not dry_run:
        news_dir.mkdir(parents=True, exist_ok=True)

    # 已采集的 URL（去重）
    existing_urls = load_existing_urls(news_dir) if not dry_run else set()

    total_new = 0
    total_dup = 0

    for query in queries:
        print(f"  Searching: {query}")
        results = tavily_search(query, api_key, max_results, days)

        for r in results:
            url = r.get("url", "")
            if url in existing_urls:
                total_dup += 1
                continue

            if dry_run:
                print(f"    [DRY] Would save: {r.get('title', '')[:50]}")
                total_new += 1
            else:
                saved = save_news_item(name, r, news_dir, rules=rules)
                if saved:
                    print(f"    + {r.get('title', '')[:60]}")
                    total_new += 1
                    existing_urls.add(url)
                else:
                    total_dup += 1

    return total_new, total_dup


def append_log(message):
    """追加操作日志"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] collect_news | {message}\n"

    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"

    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="采集上市公司新闻")
    parser.add_argument("--company", type=str, help="只采集指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只打印不保存")
    args = parser.parse_args()

    print("=" * 50)
    print("  上市公司知识库 — 新闻采集")
    print("=" * 50)

    graph = Graph()
    companies = graph.get_all_companies()
    search_cfg = load_search_config()
    rules = RulesConfig()

    if args.company:
        companies = [c for c in companies if c["name"] == args.company]
        if not companies:
            print(f"ERROR: Company '{args.company}' not found in graph.yaml")
            sys.exit(1)

    total_new = 0
    total_dup = 0

    for company in companies:
        print(f"\n[{company['name']}] ({company['ticker']})")
        new, dup = collect_for_company(company, search_cfg, args.dry_run, rules=rules)
        total_new += new
        total_dup += dup

    print(f"\n{'=' * 50}")
    print(f"  Done. New: {total_new}, Duplicates: {total_dup}")
    print(f"{'=' * 50}")

    if not args.dry_run and total_new > 0:
        append_log(f"Collected {total_new} new articles, {total_dup} duplicates skipped")


if __name__ == "__main__":
    main()
