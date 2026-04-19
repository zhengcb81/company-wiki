#!/usr/bin/env python3
"""
clip_handler.py -- Obsidian Web Clipper 文件处理器

扫描 inbox 目录（companies/_inbox/），将 Web Clipper 剪藏的 markdown 文件
通过关键词匹配归入对应公司的 raw/news/ 目录。

用法：
    python scripts/clip_handler.py                    # 处理所有 inbox 文件
    python scripts/clip_handler.py --file path.md     # 处理指定文件
    python scripts/clip_handler.py --dry-run           # 预览，不移动

匹配策略：
    1. 精确匹配：公司名、ticker、aliases 在正文中出现
    2. 按匹配数排序，匹配最多的公司优先
    3. 如果无匹配，文件留在 inbox 中并打印警告
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── 路径 ──────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph
from log_writer import append_log

INBOX_DIR = WIKI_ROOT / "companies" / "_inbox"


# ── 公司名称黑名单 ────────────────────────
def _load_blacklist(graph):
    """从 graph.yaml settings 加载名称黑名单，避免误匹配"""
    return set(graph._data.get("settings", {}).get("name_blacklist", []))


# ── 匹配逻辑 ──────────────────────────────
def _build_company_patterns(graph):
    """
    为每家公司构建匹配模式列表。
    返回: [(company_name, [pattern_str, ...]), ...]
    模式按长度降序排列，确保长名优先匹配（如"北方华创科技"优先于"北方华创"）。
    """
    companies = graph.get_all_companies()
    result = []

    for comp in companies:
        name = comp["name"]
        patterns = [name]

        # 加入 ticker
        ticker = comp.get("ticker", "")
        if ticker:
            patterns.append(ticker)

        # 加入 aliases（来自 graph.yaml）
        raw_comp = graph._data.get("companies", {}).get(name, {})
        aliases = raw_comp.get("aliases", [])
        for alias in aliases:
            if alias and alias not in patterns:
                patterns.append(alias)

        # 按长度降序排列，长名优先匹配
        patterns.sort(key=len, reverse=True)
        result.append((name, patterns))

    # 公司名也按长度降序排列
    result.sort(key=lambda x: len(x[0]), reverse=True)
    return result


def match_company(content, company_patterns, blacklist):
    """
    对文件内容进行公司匹配。
    返回: [(company_name, match_count), ...] 按匹配数降序排列。
    """
    scores = {}

    for company_name, patterns in company_patterns:
        count = 0
        for pattern in patterns:
            # 跳过黑名单中的模式（如过短的通用名）
            if pattern in blacklist:
                continue
            if len(pattern) < 2:
                continue
            # 计算模式在内容中出现的次数
            occurrences = content.count(pattern)
            if occurrences > 0:
                count += occurrences
        if count > 0:
            scores[company_name] = count

    # 按匹配数降序排列
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


# ── 文件名生成 ──────────────────────────────
def generate_target_filename(filepath, company_name, content):
    """
    生成目标文件名: YYYY-MM-DD_{hash8}_{title}.md
    日期优先从 frontmatter 的 published_date 或 date 字段提取，
    否则使用文件修改时间或当前日期。
    """
    # 尝试从 frontmatter 提取日期
    date_str = None
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            for line in frontmatter.strip().split("\n"):
                for key in ("published_date", "date", "created", "clip_date"):
                    if line.startswith(f"{key}:"):
                        raw = line.split(":", 1)[1].strip().strip('"').strip("'")
                        # 取前 10 个字符 (YYYY-MM-DD)
                        if len(raw) >= 10:
                            date_str = raw[:10]
                        break
                if date_str:
                    break

    if not date_str:
        # 使用文件修改时间
        mtime = filepath.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    # 从 frontmatter 或第一行标题提取 title
    title = ""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            for line in frontmatter.strip().split("\n"):
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break

    if not title:
        # 从第一个 markdown 标题提取
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

    if not title:
        # 使用原文件名（去掉扩展名）
        title = filepath.stem

    # 生成 hash（基于文件内容）
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:8]

    # 清理 title 中的特殊字符
    safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:40]
    # 去掉首尾的下划线
    safe_title = safe_title.strip("_")

    return f"{date_str}_{content_hash}_{safe_title}.md"


# ── 单文件处理 ──────────────────────────────
def process_file(filepath, graph, company_patterns, blacklist, dry_run=False):
    """
    处理单个 inbox 文件。
    返回: (company_name, target_path) 或 (None, None)
    """
    content = filepath.read_text(encoding="utf-8")

    # 匹配公司
    ranked = match_company(content, company_patterns, blacklist)

    if not ranked:
        print(f"  WARNING: No company matched for {filepath.name}")
        print(f"           File remains in inbox.")
        return None, None

    best_company, match_count = ranked[0]
    # 附加信息：其他匹配的公司
    other_matches = ranked[1:4]  # 最多显示 3 个
    other_info = ""
    if other_matches:
        other_info = f" (also: {', '.join(f'{n}({c})' for n, c in other_matches)})"

    # 生成目标文件名
    target_filename = generate_target_filename(filepath, best_company, content)
    target_dir = WIKI_ROOT / "companies" / best_company / "raw" / "news"
    target_path = target_dir / target_filename

    # 避免文件名冲突
    if target_path.exists():
        # 在 hash 后追加数字
        base = target_filename.rsplit("_", 1)[0]
        ext = filepath.suffix
        counter = 1
        while target_path.exists():
            target_filename = f"{base}_{counter}{ext}"
            target_path = target_dir / target_filename
            counter += 1

    if dry_run:
        print(f"  [DRY] {filepath.name}")
        print(f"        -> {best_company} ({match_count} matches){other_info}")
        print(f"        -> {target_path.relative_to(WIKI_ROOT)}")
        return best_company, target_path

    # 创建目标目录
    target_dir.mkdir(parents=True, exist_ok=True)

    # 如果内容没有 frontmatter，添加基本元数据
    if not content.startswith("---"):
        title = filepath.stem
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

        date_str = datetime.now().strftime("%Y-%m-%d")
        frontmatter = (
            f"---\n"
            f"title: \"{title}\"\n"
            f"source: \"obsidian-clipper\"\n"
            f"collected_date: \"{datetime.now().strftime('%Y-%m-%d %H:%M')}\"\n"
            f"company: \"{best_company}\"\n"
            f"type: news\n"
            f"---\n\n"
        )
        content = frontmatter + content

    # 移动文件
    shutil.move(str(filepath), str(target_path))
    print(f"  + {filepath.name}")
    print(f"    -> {best_company} ({match_count} matches){other_info}")
    print(f"    -> {target_path.relative_to(WIKI_ROOT)}")

    return best_company, target_path


# ── 主流程 ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="处理 Obsidian Web Clipper 剪藏文件"
    )
    parser.add_argument(
        "--file", type=str,
        help="处理指定文件（而非扫描整个 inbox）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预览模式，不实际移动文件",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  Obsidian Web Clipper 文件处理器")
    print("=" * 50)

    # 初始化
    graph = Graph()
    blacklist = _load_blacklist(graph)
    company_patterns = _build_company_patterns(graph)

    # 确保 inbox 目录存在
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # 收集待处理文件
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            sys.exit(1)
        if not filepath.suffix.lower() == ".md":
            print(f"ERROR: Only markdown files are supported, got: {filepath.suffix}")
            sys.exit(1)
        files = [filepath]
    else:
        files = sorted(INBOX_DIR.glob("*.md"))

    if not files:
        print("\nNo files to process in inbox.")
        return

    print(f"\nFound {len(files)} file(s) to process.\n")

    processed = 0
    unmatched = 0
    companies_hit = {}

    for f in files:
        company, target = process_file(f, graph, company_patterns, blacklist, args.dry_run)
        if company:
            processed += 1
            companies_hit[company] = companies_hit.get(company, 0) + 1
        else:
            unmatched += 1

    # 汇总
    print(f"\n{'=' * 50}")
    print(f"  Processed: {processed}, Unmatched: {unmatched}")
    if companies_hit:
        print(f"  Companies:")
        for comp, count in sorted(companies_hit.items()):
            print(f"    {comp}: {count} file(s)")
    print(f"{'=' * 50}")

    # 写入日志
    if not args.dry_run and processed > 0:
        details = [
            f"{comp}: {count} file(s)" for comp, count in sorted(companies_hit.items())
        ]
        details.append(f"Unmatched: {unmatched}")
        append_log("clip_handler", f"Processed {processed} clipped files", details)


if __name__ == "__main__":
    main()
