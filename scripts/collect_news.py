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
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── 路径 ──────────────────────────────────
from common import WIKI_ROOT, CONFIG_PATH, LOG_PATH

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

    # 移除注释
    lines = content.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # 移除行内注释（但保留引号内的 #）
        if "#" in line and not ('"' in line or "'" in line):
            line = line[: line.index("#")]
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
    payload = json.dumps(
        {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": True,
            "days": days,
            "topic": "general",
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    # 带指数退避的重试机制
    max_retries = 3
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", [])
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # 4xx 错误不_retry（客户端错误）
            if 400 <= e.code < 500:
                print(f"  Tavily API error {e.code}: {body}")
                return []
            # 5xx 错误重试
            print(
                f"  Tavily API error {e.code} (attempt {attempt + 1}/{max_retries}): {body}"
            )
        except Exception as e:
            print(f"  Tavily request failed (attempt {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            delay = base_delay * (2**attempt)
            print(f"  Retrying in {delay:.1f}s...")
            time.sleep(delay)

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
    if "\ufffd" in text:
        return True
    # 连续的 Latin-1 补充字符（常见于 UTF-8 被错误解读为 Latin-1）
    if re.search(r"[\u00c0-\u00ff]{4,}", text):
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
    safe_title = re.sub(r"[^\w\u4e00-\u9fff]", "_", title)[:40]
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
collected_date: "{datetime.now().strftime("%Y-%m-%d %H:%M")}"
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


# ── 问题驱动搜索 ──────────────────────────
def load_company_questions(name: str, entity_type: str = "company") -> list:
    """
    从 wiki 页面加载核心问题，用于生成定向搜索查询。

    解析 companies/{name}/wiki/公司动态.md 或 sectors/{name}/wiki/{name}.md
    中 '## 核心问题' 下的所有条目，清理后返回。
    """
    if entity_type == "company":
        wiki_path = WIKI_ROOT / "companies" / name / "wiki" / "公司动态.md"
    elif entity_type == "sector":
        wiki_path = WIKI_ROOT / "sectors" / name / "wiki" / f"{name}.md"
    else:
        return []

    if not wiki_path.exists():
        return []

    content = wiki_path.read_text(encoding="utf-8")
    questions = []
    in_section = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "## 核心问题":
            in_section = True
            continue
        elif in_section and stripped.startswith("## "):
            break
        elif in_section and stripped.startswith("- "):
            q = stripped[2:]
            # 跳过占位符
            if q in ("（待设定）", "（待补充）", ""):
                continue
            # 移除 wikilinks: [[设备国产化]] → 设备国产化
            q = re.sub(r"\[\[([^\]]+)\]\]", r"\1", q)
            # 移除陈旧/过时标记: [陈旧]
            q = re.sub(r"\s*\[[^\]]*\]", "", q)
            q = q.strip().rstrip("？?").strip()
            if q and len(q) > 4:
                questions.append(q)

    return questions[:5]  # 最多取 5 个问题


def generate_question_queries(name: str, questions: list) -> list:
    """
    根据核心问题生成定向搜索查询。
    格式: "{公司名} {问题核心}"

    对长问题截断到 80 字（保留前部分，移除具体细节）。
    """
    queries = []
    for q in questions:
        # 截断过长的问题（保留核心意图）
        if len(q) > 80:
            # 尝试按句号/逗号截断到第一个完整子句
            truncated = q[:80]
            last_punct = max(
                truncated.rfind("，"),
                truncated.rfind("、"),
                truncated.rfind(" "),
                truncated.rfind("的"),
            )
            if last_punct > 20:
                truncated = truncated[:last_punct]
            q = truncated

        query = f"{name} {q}"
        queries.append(query)

    return queries


# ── 主流程 ────────────────────────────────
def load_search_config():
    """从 config.yaml 读取搜索运维配置（API key 等）"""
    try:
        from config import Config

        config = Config.load()
        return {
            "api_key": config.search.api_key,
            "results_per_query": config.search.results_per_query,
            "max_age_days": config.search.max_age_days,
            "language": config.search.language,
        }
    except Exception:
        # Fallback: 直接读取 YAML
        import yaml

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        search_cfg = cfg.get("search", {})
        return {
            "api_key": search_cfg.get("tavily_api_key", search_cfg.get("api_key", "")),
            "results_per_query": search_cfg.get("results_per_query", 8),
            "max_age_days": search_cfg.get("max_age_days", 7),
            "language": search_cfg.get("language", "zh"),
        }


def collect_for_company(
    company, search_cfg, dry_run=False, rules=None, use_questions=True
):
    """为单个公司采集新闻（含配额检查）"""
    name = company["name"]
    queries = company.get("news_queries", [f"{name} 最新消息"])

    api_key = search_cfg.get("api_key", "") or os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        print("  ERROR: No Tavily API key (config.yaml or TAVILY_API_KEY env)")
        return 0, 0

    max_results = search_cfg.get("results_per_query", 8)
    days = search_cfg.get("max_age_days", 7)

    # ── 配额检查：30 天无采集则拓宽关键词 ──
    try:
        from state_store import get_state

        state = get_state()
        company_state = state.get_company_state(name)
        if company_state and company_state.get("last_collect_time"):
            last_collect = datetime.fromisoformat(company_state["last_collect_time"])
            days_since = (datetime.now() - last_collect).days
            if days_since > 30:
                # 拓宽关键词：添加行业相关词
                broad_queries = [
                    f"{name} 行业动态",
                    f"{name} 最新进展",
                    f"{name} 市场表现",
                ]
                queries = list(dict.fromkeys(queries + broad_queries))  # 去重保持顺序
                print(f"  [配额] {name} 已 {days_since} 天未采集，拓宽关键词")
    except Exception:
        pass  # state_store 未初始化时不阻塞

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

    # ── 问题驱动搜索（补充） ─────────────────
    if use_questions:
        questions = load_company_questions(name)
        if questions:
            question_queries = generate_question_queries(name, questions)
            print(f"  Question-driven search ({len(question_queries)} queries)...")
            for q_query in question_queries:
                print(f"  Searching: {q_query[:80]}")
                results = tavily_search(
                    q_query, api_key, max(3, max_results // 2), days
                )

                for r in results:
                    url = r.get("url", "")
                    if url in existing_urls:
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

    # ── 记录采集时间 ──
    if not dry_run:
        try:
            from state_store import get_state

            state = get_state()
            state.set_last_collect(name)
        except Exception:
            pass

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


def get_last_collect_time(company_name: str) -> datetime:
    """获取公司上次采集时间，优先从 state_store 读取，fallback 到 news 目录最新文件时间"""
    try:
        from state_store import get_state

        state = get_state()
        company_state = state.get_company_state(company_name)
        if company_state and company_state.get("last_collect_time"):
            return datetime.fromisoformat(company_state["last_collect_time"])
    except Exception:
        pass

    # Fallback: 检查 news 目录最新文件
    news_dir = WIKI_ROOT / "companies" / company_name / "raw" / "news"
    if news_dir.exists():
        newest = None
        for f in news_dir.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if newest is None or mtime > newest:
                    newest = mtime
            except Exception:
                pass
        if newest:
            return newest

    # 从未采集过
    return datetime.min


def main():
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    parser = argparse.ArgumentParser(description="采集上市公司新闻")
    parser.add_argument("--company", type=str, help="只采集指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只打印不保存")
    parser.add_argument(
        "--use-questions",
        action="store_true",
        default=True,
        help="使用核心问题驱动搜索（默认启用）",
    )
    parser.add_argument(
        "--no-use-questions",
        action="store_false",
        dest="use_questions",
        help="禁用问题驱动搜索",
    )
    parser.add_argument(
        "--max-companies",
        type=int,
        default=0,
        help="每轮最多采集 N 家公司（0=全部，默认）",
    )
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
    else:
        # 均衡采集：按上次采集时间排序，最久未采集的优先
        companies_with_time = [(c, get_last_collect_time(c["name"])) for c in companies]
        companies_with_time.sort(key=lambda x: x[1])
        companies = [c for c, _ in companies_with_time]

        if args.max_companies > 0:
            companies = companies[: args.max_companies]
            print(f"  均衡模式: 处理最久未采集的 {len(companies)} 家公司")

    total_new = 0
    total_dup = 0

    for company in companies:
        print(f"\n[{company['name']}] ({company['ticker']})")
        new, dup = collect_for_company(
            company,
            search_cfg,
            args.dry_run,
            rules=rules,
            use_questions=args.use_questions,
        )
        total_new += new
        total_dup += dup

    print(f"\n{'=' * 50}")
    print(f"  Done. New: {total_new}, Duplicates: {total_dup}")
    print(f"{'=' * 50}")

    if not args.dry_run and total_new > 0:
        append_log(
            f"Collected {total_new} new articles, {total_dup} duplicates skipped"
        )


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
