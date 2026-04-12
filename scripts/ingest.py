#!/usr/bin/env python3
"""
ingest.py — 数据整理模块
扫描 raw/ 目录下的新文件，调用 LLM 整理到 wiki 时间线中。

用法：
    python3 scripts/ingest.py                       # 处理所有待 ingest 的文件
    python3 scripts/ingest.py --company 中微公司      # 只处理指定公司
    python3 scripts/ingest.py --check                 # 检查哪些文件待处理（不执行）
    python3 scripts/ingest.py --limit 3               # 最多处理 3 个文件（调试用）

设计：
  1. 扫描 raw/ 目录，找出尚未 ingest 的文件（通过 .ingested 标记文件判断）
  2. 对每个新文件，读取内容
  3. 判断相关性（属于哪些 company/sector/theme topics）
  4. 对每个相关 topic，读取现有 wiki 文档，判断是否有新进展
  5. 如果有新进展，在时间线中插入新条目
  6. 标记文件为已 ingest，更新 log.md
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 路径 ──────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# 添加 scripts 目录到 path，导入模块
sys.path.insert(0, str(SCRIPTS_DIR))
from extract import extract_summary, classify_info_type
from pdf_extract import extract_pdf_summary
from graph import Graph

LOG_PATH = WIKI_ROOT / "log.md"
INDEX_PATH = WIKI_ROOT / "index.md"
INGESTED_DIR = WIKI_ROOT / ".ingested"


def load_graph():
    """加载图数据（单一数据源）"""
    return Graph(str(WIKI_ROOT / "graph.yaml"))


# ── Ingest 标记管理 ────────────────────────
def get_ingested_set():
    """加载所有已 ingest 文件的集合（基于文件内容哈希）"""
    INGESTED_DIR.mkdir(parents=True, exist_ok=True)
    ingested = set()
    for f in INGESTED_DIR.glob("*.hash"):
        ingested.add(f.read_text().strip())
    return ingested


def mark_ingested(file_path):
    """标记文件为已 ingest"""
    INGESTED_DIR.mkdir(parents=True, exist_ok=True)
    content = Path(file_path).read_bytes()
    file_hash = hashlib.md5(content).hexdigest()
    marker = INGESTED_DIR / f"{file_hash}.hash"
    marker.write_text(file_hash)


def is_ingested(file_path, ingested_set):
    """检查文件是否已被 ingest"""
    content = Path(file_path).read_bytes()
    file_hash = hashlib.md5(content).hexdigest()
    return file_hash in ingested_set


# ── 扫描待处理文件 ─────────────────────────
def scan_pending_files(graph, company_name=None):
    """
    扫描所有待 ingest 文件（从 Graph 获取公司列表）。
    返回: [(file_path, entity_name, entity_type), ...]
    """
    ingested = get_ingested_set()
    pending = []

    # 从 graph 获取公司列表
    companies = graph.get_all_companies()
    if company_name:
        companies = [c for c in companies if c["name"] == company_name]

    # 扫描公司目录下所有文件
    for company in companies:
        name = company["name"]
        company_dir = WIKI_ROOT / "companies" / name
        if not company_dir.exists():
            continue
        for f in sorted(company_dir.rglob("*")):
            if f.is_file() and not is_ingested(f, ingested):
                if "/wiki/" in str(f) or "\\wiki\\" in str(f):
                    continue
                pending.append((str(f), name, "company"))

    # 扫描行业目录
    for sector_name in graph.get_all_sectors():
        sector_dir = WIKI_ROOT / "sectors" / sector_name
        if not sector_dir.exists():
            continue
        for f in sorted(sector_dir.rglob("*")):
            if f.is_file() and not is_ingested(f, ingested):
                if "/wiki/" in str(f) or "\\wiki\\" in str(f):
                    continue
                pending.append((str(f), sector_name, "sector"))

    return pending


# ── 读取文件元数据 ─────────────────────────
def read_news_metadata(file_path):
    """读取文件元数据（支持 markdown 和 PDF）"""
    path = Path(file_path)
    filename = path.name
    meta = {"_path": str(file_path), "_filename": filename}

    # PDF 文件
    if filename.lower().endswith(".pdf"):
        result = extract_pdf_summary(str(file_path))
        if result.get("error"):
            meta["_content"] = ""
            meta["_pdf_error"] = result["error"]
        else:
            # 合并所有提取的章节
            sections_text = "\n\n".join(
                f"[{s['name']}]\n{s['content']}" for s in result.get("sections", [])
            )
            meta["_content"] = sections_text
            meta["_pdf_type"] = result.get("type", "unknown")
            meta["_pdf_pages"] = result.get("pages_extracted", 0)
        meta["title"] = filename.replace(".pdf", "")
        meta["type"] = "report"
        return meta

    # Markdown 文件
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        content = ""

    # 解析 frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            front = content[3:end]
            for line in front.strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip().strip('"').strip("'")

    meta["_content"] = content
    return meta


# ── 判断相关性 ─────────────────────────────
def determine_relevance(meta, graph):
    """
    判断一条新闻/文档属于哪些 topics。
    返回: [(entity_name, entity_type, topic_name), ...]
    使用 Graph API 动态推导，不再硬编码。
    """
    title = meta.get("title", "")
    content = meta.get("_content", "")
    company_name = meta.get("company", "")

    # 提取正文（去掉 frontmatter）
    body = content
    if body.startswith("---"):
        end = body.find("---", 3)
        if end > 0:
            body = body[end + 3:]

    text = f"{title} {body}"

    # 使用 Graph API 一次性获取所有相关实体
    return graph.find_related_entities(text, company_hint=company_name or None)


# ── Wiki 页面操作 ──────────────────────────
def get_wiki_path(entity_name, entity_type, topic_name):
    """获取 wiki 文档路径"""
    if entity_type == "company":
        return WIKI_ROOT / "companies" / entity_name / "wiki" / f"{topic_name}.md"
    elif entity_type == "sector":
        return WIKI_ROOT / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
    elif entity_type == "theme":
        return WIKI_ROOT / "themes" / entity_name / "wiki" / f"{topic_name}.md"
    return None


def create_topic_template(entity_name, entity_type, topic_name, graph):
    """创建新 topic wiki 文档的模板"""
    # 从 graph 获取问题列表
    questions = []
    if entity_type == "sector":
        sector_info = graph.get_sector(entity_name)
        if sector_info:
            questions = sector_info.get("questions", [])
    elif entity_type == "theme":
        all_q = graph.get_all_questions()
        questions = all_q.get(entity_name, [])

    questions_md = "\n".join(f"- {q}" for q in questions) if questions else "- （待设定）"

    return f"""---
title: "{topic_name}"
entity: "{entity_name}"
type: {entity_type}_topic
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
sources_count: 0
tags: []
---

# {entity_name} — {topic_name}

## 核心问题
{questions_md}

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""


def add_timeline_entry(wiki_path, meta, topic_name, entity_type):
    """
    向 wiki 文档的时间线中添加新条目。
    返回: True 如果成功添加，False 如果跳过
    """
    title = meta.get("title", "未知标题")
    source_url = meta.get("source_url", "")
    published = meta.get("published_date", datetime.now().strftime("%Y-%m-%d"))
    content = meta.get("_content", "")
    filename = meta.get("_filename", "")

    # 从内容中提取摘要（使用 extract 模块）
    body = content
    if body.startswith("---"):
        end = body.find("---", 3)
        if end > 0:
            body = body[end + 3:]
    # 去掉第一个 # 标题行
    body_lines = body.strip().split("\n")
    clean_body_lines = []
    for line in body_lines:
        if line.startswith("#"):
            continue
        clean_body_lines.append(line)
    body_text = "\n".join(clean_body_lines)

    # 使用 extract 模块做智能摘要
    extracted = extract_summary(body_text, max_sentences=3)

    # 质量过滤：低质量内容只保留标题
    if extracted['quality'] == 'low' and len(body_text) < 100:
        summary_points = [title]
    else:
        summary_points = extracted['points'] if extracted['points'] else [title]

    summary = "\n".join(f"- {p}" for p in summary_points)

    # 来源类型判断
    info_type = extracted.get('info_type', '新闻')
    source_type = "新闻"
    if meta.get("type") == "report" or filename.lower().endswith(".pdf"):
        # PDF 文件按内容细分
        pdf_type = meta.get("_pdf_type", "")
        if pdf_type == "investor_relations":
            source_type = "投资者关系"
        elif pdf_type == "research_report":
            source_type = "研报"
        elif "招股" in title:
            source_type = "招股书"
        else:
            source_type = "财报"
    elif info_type == "财报":
        source_type = "财报"
    elif info_type == "产品":
        source_type = "产品"
    elif "研报" in title or "report" in filename.lower():
        source_type = "研报"
    elif "公告" in title:
        source_type = "公告"

    # 构建时间线条目
    relative_path = os.path.relpath(
        meta["_path"],
        str(wiki_path.parent)
    )

    entry = f"""
### {published} | {source_type} | {title}
{summary}

- [来源]({relative_path})
"""

    # 插入到时间线部分
    if wiki_path.exists():
        wiki_text = wiki_path.read_text(encoding="utf-8")
    else:
        return False

    # 找到 "## 时间线" 的位置
    timeline_pos = wiki_text.find("## 时间线")
    if timeline_pos < 0:
        return False

    # 找到时间线之后第一个 "###" 或 "##" 行（即第一个已有条目或下一个 section）
    after_timeline = wiki_text[timeline_pos:]
    next_section = after_timeline.find("\n## ", 1)  # 下一个二级标题
    first_entry = after_timeline.find("\n### ", 1)  # 第一个已有条目

    if first_entry < 0 and next_section < 0:
        # 时间线是最后一个部分，在末尾追加
        wiki_text = wiki_text.rstrip() + entry
    elif first_entry < 0 or (next_section > 0 and next_section < first_entry):
        # 时间线没有条目，或下一个 section 在第一个条目之前
        # 在时间线标题后插入
        insert_pos = timeline_pos + len("## 时间线")
        wiki_text = wiki_text[:insert_pos] + entry + wiki_text[insert_pos:]
    else:
        # 有已有条目，按日期排序插入
        # 简化处理：插入到第一个条目之前（新日期应该在最前面）
        insert_pos = timeline_pos + len("## 时间线") + (first_entry)
        # 找到第一个条目 ### 的绝对位置
        abs_first_entry = timeline_pos + first_entry
        wiki_text = wiki_text[:abs_first_entry] + entry + wiki_text[abs_first_entry:]

    # 更新 frontmatter
    wiki_text = re.sub(
        r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
        f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
        wiki_text
    )
    # 更新 sources_count
    count_match = re.search(r'sources_count: (\d+)', wiki_text)
    if count_match:
        old_count = int(count_match.group(1))
        wiki_text = wiki_text.replace(
            f"sources_count: {old_count}",
            f"sources_count: {old_count + 1}"
        )

    # 如果有 "暂无条目" 的占位文字，删除
    wiki_text = wiki_text.replace("（暂无条目）\n", "")

    wiki_path.write_text(wiki_text, encoding="utf-8")
    return True


# ── 主流程 ────────────────────────────────
def is_low_quality_source(file_path, meta):
    """
    检查是否是低质量来源（行情页、公司主页、百科等）。
    这些页面不进入 wiki，避免噪音。
    """
    filename = Path(file_path).name.lower()
    url = meta.get("source_url", "").lower()
    title = meta.get("title", "").lower()

    # URL 黑名单模式
    skip_url_patterns = [
        "quote.eastmoney.com",      # 东方财富行情页
        "quote.futunn.com",         # 富途行情页
        "xueqiu.com/S/",            # 雪球个股页
        "stock_quote",              # 通用行情页
        "baidu.com/baike",          # 百度百科
        "baike.baidu.com",
        "hq.sinajs.cn",             # 新浪行情
        "finance.sina.com.cn/realstock",
        "amec-inc.com",             # AMEC 公司主页
    ]

    # 标题黑名单模式
    skip_title_patterns = [
        "行情走势", "股票股价", "最新价格", "实时走势图",
        "公司简介", "股票行情中心",
        "百科", "百度百科",
        "最新新闻",  # 通常是行情页的标题
        "最新资讯",
        "个股资讯",
    ]

    for p in skip_url_patterns:
        if p in url:
            return True

    for p in skip_title_patterns:
        if p in title:
            return True

    # 文件名检查
    skip_file_patterns = [
        "行情走势", "股票股价", "最新价格", "行情_走势图",
        "公司简介", "行情中心", "百科",
        "_公司新闻",  # 公司新闻导航页（非新闻正文）
    ]

    # 内容太短且标题就是公司名（公司主页）
    if len(meta.get("_content", "")) < 200:
        # 从文件路径推断公司名
        company_from_path = Path(file_path).parts
        for part in company_from_path:
            if part == "companies":
                idx = company_from_path.index(part)
                if idx + 1 < len(company_from_path):
                    company_name_from_path = company_from_path[idx + 1]
                    title_clean = title.replace(" ", "")
                    if title_clean == company_name_from_path:
                        return True
                break
    for p in skip_file_patterns:
        if p in filename:
            return True

    return False


def process_file(file_path, entity_name, entity_type, graph, dry_run=False):
    """处理单个待 ingest 文件"""
    meta = read_news_metadata(file_path)

    # 质量过滤：跳过低质量来源
    if is_low_quality_source(file_path, meta):
        print(f"  SKIP (low quality): {meta.get('title', '')[:50]}")
        if not dry_run:
            mark_ingested(file_path)
        return []

    relevant = determine_relevance(meta, graph)

    if not relevant:
        print(f"  SKIP (no relevance): {meta.get('title', '')[:50]}")
        return []

    updated_topics = []

    for ent_name, ent_type, topic_name in relevant:
        wiki_path = get_wiki_path(ent_name, ent_type, topic_name)

        if wiki_path is None:
            continue

        # 如果 wiki 文档不存在，创建模板
        if not wiki_path.exists():
            if dry_run:
                print(f"    [DRY] Would create: {wiki_path.relative_to(WIKI_ROOT)}")
            else:
                wiki_path.parent.mkdir(parents=True, exist_ok=True)
                template = create_topic_template(ent_name, ent_type, topic_name, graph)
                wiki_path.write_text(template, encoding="utf-8")
                print(f"    Created: {wiki_path.relative_to(WIKI_ROOT)}")

        # 添加时间线条目
        if dry_run:
            print(f"    [DRY] Would update: {ent_name}/{topic_name}")
        else:
            success = add_timeline_entry(wiki_path, meta, topic_name, ent_type)
            if success:
                print(f"    Updated: {ent_name}/{topic_name}")
                updated_topics.append(f"{ent_name}/{topic_name}")
            else:
                print(f"    Skip: {ent_name}/{topic_name} (insert failed)")

    return updated_topics


def append_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] ingest | {message}\n"
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="数据整理 — Ingest")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()

    print("=" * 50)
    print("  上市公司知识库 — Ingest")
    print("=" * 50)

    graph = load_graph()
    pending = scan_pending_files(graph, args.company)

    if args.limit > 0:
        pending = pending[:args.limit]

    if not pending:
        print("\n  No pending files to ingest.")
        return

    print(f"\n  Pending files: {len(pending)}")

    if args.check:
        for fp, ent, etype in pending:
            rel = Path(fp).relative_to(WIKI_ROOT)
            print(f"    [{etype}] {ent}: {rel}")
        return

    total_updated = 0
    total_skipped = 0
    all_topics = set()

    for i, (fp, ent, etype) in enumerate(pending):
        rel = Path(fp).relative_to(WIKI_ROOT)
        print(f"\n  [{i+1}/{len(pending)}] {rel}")
        topics = process_file(fp, ent, etype, graph, args.dry_run)

        if topics:
            total_updated += len(topics)
            all_topics.update(topics)
            if not args.dry_run:
                mark_ingested(fp)
        else:
            total_skipped += 1
            if not args.dry_run:
                mark_ingested(fp)  # 即使跳过也标记，避免重复扫描

    print(f"\n{'=' * 50}")
    print(f"  Done. Topics updated: {total_updated}, Skipped: {total_skipped}")
    if all_topics:
        print(f"  Affected topics: {', '.join(sorted(all_topics))}")
    print(f"{'=' * 50}")

    if not args.dry_run and total_updated > 0:
        topics_str = ", ".join(sorted(all_topics))
        append_log(f"Ingested {len(pending)} files, updated {total_updated} topic entries: {topics_str}")


if __name__ == "__main__":
    main()
