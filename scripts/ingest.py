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

# 添加 scripts 目录到 path，导入 extract 模块
sys.path.insert(0, str(SCRIPTS_DIR))
from extract import extract_summary, classify_info_type
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"
INDEX_PATH = WIKI_ROOT / "index.md"
INGESTED_DIR = WIKI_ROOT / ".ingested"  # 存储已 ingest 文件的标记


def load_config():
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
def scan_pending_files(config, company_name=None):
    """
    扫描所有 raw/ 目录，返回待 ingest 的文件列表。
    返回: [(file_path, entity_name, entity_type), ...]
    entity_type: company | sector | theme
    """
    ingested = get_ingested_set()
    pending = []

    companies = config.get("companies", [])
    if company_name:
        companies = [c for c in companies if c["name"] == company_name]

    # 扫描公司 raw/ 目录
    for company in companies:
        name = company["name"]
        for subdir in ["reports", "research", "news"]:
            raw_dir = WIKI_ROOT / "companies" / name / "raw" / subdir
            if not raw_dir.exists():
                continue
            for f in sorted(raw_dir.rglob("*")):
                if f.is_file() and not is_ingested(f, ingested):
                    pending.append((str(f), name, "company"))

    # 扫描行业 raw/ 目录
    sectors = config.get("sectors", {})
    for sector_name in sectors:
        for subdir in ["research", "news"]:
            raw_dir = WIKI_ROOT / "sectors" / sector_name / "raw" / subdir
            if not raw_dir.exists():
                continue
            for f in sorted(raw_dir.rglob("*")):
                if f.is_file() and not is_ingested(f, ingested):
                    pending.append((str(f), sector_name, "sector"))

    # 扫描主题 raw/ 目录
    themes = config.get("themes", {})
    for theme_name in themes:
        raw_dir = WIKI_ROOT / "themes" / theme_name / "raw" / "news"
        if not raw_dir.exists():
            continue
        for f in sorted(raw_dir.rglob("*")):
            if f.is_file() and not is_ingested(f, ingested):
                pending.append((str(f), theme_name, "theme"))

    return pending


# ── 读取文件元数据 ─────────────────────────
def read_news_metadata(file_path):
    """从 markdown 文件的 frontmatter 中读取元数据"""
    content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    meta = {}

    # 解析 frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            front = content[3:end]
            for line in front.strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    meta[key] = val

    meta["_content"] = content
    meta["_path"] = str(file_path)
    meta["_filename"] = Path(file_path).name
    return meta


# ── 判断相关性 ─────────────────────────────
def determine_relevance(meta, config):
    """
    判断一条新闻/文档属于哪些 topics。
    返回: [(entity_name, entity_type, topic_name), ...]
    """
    title = meta.get("title", "").lower()
    content = meta.get("_content", "").lower()
    company_name = meta.get("company", "")
    text = title + " " + content

    relevant = []

    companies = config.get("companies", {})
    sectors_cfg = config.get("sectors", {})
    themes_cfg = config.get("themes", {})

    # 1. 如果有明确的 company 标签，直接关联
    if company_name:
        # 找到该公司的所有 topics
        for comp in config.get("companies", []):
            if comp["name"] == company_name:
                # 添加公司专属 topics（从 config 中定义的）
                relevant.append((company_name, "company", "公司动态"))
                # 添加关联行业 topics
                for sector_name in comp.get("sectors", []):
                    if sector_name in sectors_cfg:
                        for topic in sectors_cfg[sector_name].get("topics", []):
                            relevant.append((sector_name, "sector", topic["name"]))
                # 添加关联主题 topics
                for theme_name in comp.get("themes", []):
                    if theme_name in themes_cfg:
                        for topic in themes_cfg[theme_name].get("topics", []):
                            relevant.append((theme_name, "theme", topic["name"]))
                break

    # 2. 关键词匹配（补充）
    # 检查是否提到了其他公司
    for comp in config.get("companies", []):
        if comp["name"] != company_name and comp["name"] in text:
            relevant.append((comp["name"], "company", "相关动态"))

    # 3. 行业/主题关键词匹配
    sector_keywords = {
        "半导体设备": ["半导体", "芯片", "晶圆", "刻蚀", "薄膜", "光刻", "设备"],
        "密封件": ["密封", "石化", "核电", "机械密封"],
    }
    theme_keywords = {
        "半导体国产替代": ["国产替代", "自主可控", "半导体设备国产", "大基金"],
        "高端制造": ["高端制造", "智能制造", "工业母机"],
    }

    for sector_name, keywords in sector_keywords.items():
        if any(kw in text for kw in keywords) and sector_name in sectors_cfg:
            for topic in sectors_cfg[sector_name].get("topics", []):
                entry = (sector_name, "sector", topic["name"])
                if entry not in relevant:
                    relevant.append(entry)

    for theme_name, keywords in theme_keywords.items():
        if any(kw in text for kw in keywords) and theme_name in themes_cfg:
            for topic in themes_cfg[theme_name].get("topics", []):
                entry = (theme_name, "theme", topic["name"])
                if entry not in relevant:
                    relevant.append(entry)

    # 去重
    return list(set(relevant))


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


def create_topic_template(entity_name, entity_type, topic_name, config):
    """创建新 topic wiki 文档的模板"""
    type_label = {
        "company": "公司动态",
        "sector": "行业动态",
        "theme": "主题动态"
    }.get(entity_type, "动态")

    # 从 config 获取问题列表
    questions = []
    if entity_type == "sector":
        sector_cfg = config.get("sectors", {}).get(entity_name, {})
        for t in sector_cfg.get("topics", []):
            if t["name"] == topic_name:
                questions = t.get("questions", [])
                break
    elif entity_type == "theme":
        theme_cfg = config.get("themes", {}).get(entity_name, {})
        for t in theme_cfg.get("topics", []):
            if t["name"] == topic_name:
                questions = t.get("questions", [])
                break

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


def add_timeline_entry(wiki_path, meta, topic_name, entity_type, config):
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

    # 来源类型判断（结合 extract 的分类结果）
    info_type = extracted.get('info_type', '新闻')
    source_type = "新闻"
    if info_type == "财报":
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
        company_names = ["中微公司", "中密控股", "珂玛科技", "AMEC"]
        title_clean = title.replace(" ", "")
        for cn in company_names:
            if title_clean == cn or title_clean == cn.lower():
                return True
    for p in skip_file_patterns:
        if p in filename:
            return True

    return False


def process_file(file_path, entity_name, entity_type, config, dry_run=False):
    """处理单个待 ingest 文件"""
    meta = read_news_metadata(file_path)

    # 质量过滤：跳过低质量来源
    if is_low_quality_source(file_path, meta):
        print(f"  SKIP (low quality): {meta.get('title', '')[:50]}")
        if not dry_run:
            mark_ingested(file_path)
        return []

    relevant = determine_relevance(meta, config)

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
                template = create_topic_template(ent_name, ent_type, topic_name, config)
                wiki_path.write_text(template, encoding="utf-8")
                print(f"    Created: {wiki_path.relative_to(WIKI_ROOT)}")

        # 添加时间线条目
        if dry_run:
            print(f"    [DRY] Would update: {ent_name}/{topic_name}")
        else:
            success = add_timeline_entry(wiki_path, meta, topic_name, ent_type, config)
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

    config = load_config()
    pending = scan_pending_files(config, args.company)

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
        topics = process_file(fp, ent, etype, config, args.dry_run)

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
