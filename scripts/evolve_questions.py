#!/usr/bin/env python3
"""
evolve_questions.py — 问题清单演化

扫描所有 wiki 页面的核心问题，分析时间线覆盖情况：
1. 标记长期无进展（超过6个月无相关条目）的问题为 [陈旧]
2. 基于最近时间线条目建议新问题
3. 生成问题演化报告

用法：
    python scripts/evolve_questions.py                    # 扫描所有 wiki
    python scripts/evolve_questions.py --company 中微公司  # 只扫描指定公司
    python scripts/evolve_questions.py --dry-run          # 只报告，不修改文件
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from log_writer import append_log

# 陈旧阈值（天）
STALE_DAYS = 180


def extract_core_questions(content: str) -> List[Tuple[int, str]]:
    """从 wiki 内容提取核心问题，返回 (行号, 问题文本) 列表"""
    questions = []
    in_core_questions = False
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped == "## 核心问题":
            in_core_questions = True
            continue
        if in_core_questions:
            if stripped.startswith("## ") and not stripped.startswith("### "):
                break
            if stripped.startswith("- ") and len(stripped) > 2:
                questions.append((i, stripped[2:].strip()))
    return questions


def extract_timeline_dates(content: str) -> List[Tuple[str, str]]:
    """从 wiki 提取时间线条目的 (日期, 标题) 列表"""
    entries = []
    pattern = re.compile(r'### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)')
    for match in pattern.finditer(content):
        date = match.group(1)
        title = match.group(3)
        entries.append((date, title))
    return entries


def is_question_addressed(question: str, timeline_entries: List[Tuple[str, str]],
                          content: str) -> Tuple[bool, Optional[str]]:
    """
    判断问题是否被时间线回答。
    通过提取问题关键词，在时间线标题和内容中匹配。
    返回 (是否被回答, 最近回答日期)
    """
    # 提取问题关键词（去掉常见虚词，保留名词/动词）
    keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}', question))
    # 过滤掉过于通用的词
    generic = {"什么", "如何", "怎么", "为什么", "是否", "多少", "哪些", "怎样",
               "公司", "行业", "市场", "情况", "进展", "变化", "趋势", "影响",
               "核心", "主要", "最新", "当前"}
    keywords = keywords - generic
    if not keywords:
        return False, None

    matched_dates = []
    for date, title in timeline_entries:
        title_lower = title.lower()
        # 计算匹配的关键词数
        matched = sum(1 for kw in keywords if kw in title_lower)
        if matched >= max(1, len(keywords) // 3):
            matched_dates.append(date)

    if matched_dates:
        return True, max(matched_dates)
    return False, None


def mark_stale_questions(wiki_path: Path, stale_indices: List[int], dry_run: bool) -> int:
    """在 wiki 中标记陈旧问题"""
    content = wiki_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    modified = False

    question_count = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## 核心问题"):
            question_count = 0
            continue
        if stripped.startswith("## ") and not stripped.startswith("### "):
            question_count = -1
            continue
        if question_count >= 0 and stripped.startswith("- "):
            if question_count in stale_indices:
                if "[陈旧]" not in line:
                    lines[i] = line + " [陈旧]"
                    modified = True
            question_count += 1

    if modified and not dry_run:
        wiki_path.write_text("\n".join(lines), encoding="utf-8")

    return len([i for i in stale_indices if i >= 0])


def analyze_wiki(wiki_path: Path, stale_days: int) -> Dict:
    """分析单个 wiki 页面的问题演化情况"""
    content = wiki_path.read_text(encoding="utf-8")
    questions = extract_core_questions(content)
    timeline = extract_timeline_dates(content)

    if not questions:
        return {"questions": 0, "stale": [], "active": [], "no_timeline": True}

    now = datetime.now()
    stale_threshold = now - timedelta(days=stale_days)

    stale = []
    active = []
    unaddressed = []

    for idx, (line_no, q_text) in enumerate(questions):
        addressed, last_date = is_question_addressed(q_text, timeline, content)
        if addressed and last_date:
            last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            if last_dt < stale_threshold:
                stale.append({
                    "index": idx,
                    "question": q_text,
                    "last_answered": last_date,
                    "days_ago": (now - last_dt).days,
                })
            else:
                active.append({
                    "question": q_text,
                    "last_answered": last_date,
                })
        else:
            unaddressed.append({
                "index": idx,
                "question": q_text,
            })

    return {
        "questions": len(questions),
        "stale": stale,
        "active": active,
        "unaddressed": unaddressed,
        "no_timeline": len(timeline) == 0,
    }


def suggest_new_questions(wiki_path: Path, llm_client=None) -> List[str]:
    """
    基于最近的时间线条目建议新问题。
    简单版：提取最近3个月的条目主题，生成问题建议。
    """
    content = wiki_path.read_text(encoding="utf-8")
    timeline = extract_timeline_dates(content)

    if not timeline:
        return []

    # 取最近3个月的条目
    now = datetime.now()
    recent = []
    for date, title in timeline:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            if (now - dt).days <= 90:
                recent.append(title)
        except ValueError:
            continue

    if not recent:
        return []

    # 简单启发式：从最近条目中提取未在现有问题中覆盖的主题
    # 更复杂的实现可以用 LLM，这里先用规则
    suggestions = []

    # 检查是否有财务相关条目但无财务问题
    has_financial = any(k in " ".join(recent) for k in ["营收", "净利润", "毛利率", "增长", "同比下降"])
    existing = " ".join(q[1] for q in extract_core_questions(content))
    if has_financial and "营收" not in existing and "利润" not in existing:
        suggestions.append("公司最新季度营收和利润增长驱动力是什么？")

    # 检查是否有研发相关条目
    has_rnd = any(k in " ".join(recent) for k in ["研发", "专利", "新产品", "技术突破"])
    if has_rnd and "研发" not in existing:
        suggestions.append("公司研发投入方向及新产品进展如何？")

    # 检查是否有订单/客户相关条目
    has_order = any(k in " ".join(recent) for k in ["订单", "客户", "中标", "合同", "产能"])
    if has_order and "订单" not in existing and "客户" not in existing:
        suggestions.append("公司最新订单获取情况及大客户动态？")

    return suggestions[:3]


def main():
    parser = argparse.ArgumentParser(description="问题清单演化")
    parser.add_argument("--company", type=str, help="只扫描指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只报告不修改")
    parser.add_argument("--stale-days", type=int, default=STALE_DAYS,
                        help=f"陈旧阈值天数（默认 {STALE_DAYS}）")
    args = parser.parse_args()

    print("=" * 50)
    print("  问题清单演化分析")
    print("=" * 50)

    targets = []

    # 公司 wiki
    for d in (WIKI_ROOT / "companies").iterdir():
        if not d.is_dir():
            continue
        if args.company and d.name != args.company:
            continue
        wiki_dir = d / "wiki"
        if not wiki_dir.exists():
            continue
        for wiki in wiki_dir.glob("*.md"):
            if "_slides" in wiki.name:
                continue
            targets.append(("company", d.name, wiki))

    # 行业 wiki
    if not args.company:
        for d in (WIKI_ROOT / "sectors").iterdir():
            if not d.is_dir():
                continue
            wiki_dir = d / "wiki"
            if not wiki_dir.exists():
                continue
            for wiki in wiki_dir.glob("*.md"):
                if "_slides" in wiki.name:
                    continue
                targets.append(("sector", d.name, wiki))

    total_stale = 0
    total_active = 0
    total_unaddressed = 0
    modified_wikis = 0

    print(f"\n扫描 {len(targets)} 个 wiki 页面...\n")

    for etype, name, wiki in targets:
        result = analyze_wiki(wiki, args.stale_days)
        if result["questions"] == 0:
            continue

        stale_indices = [s["index"] for s in result["stale"]]
        stale_indices.extend([u["index"] for u in result["unaddressed"]])

        print(f"[{etype}] {name} — {wiki.name}")
        print(f"  问题数: {result['questions']}")
        print(f"  活跃: {len(result['active'])} | 陈旧: {len(result['stale'])} | 未回答: {len(result['unaddressed'])}")

        if result["stale"]:
            for s in result["stale"][:2]:
                print(f"    [陈旧] {s['question'][:60]}... (上次回答: {s['last_answered']})")

        if result["unaddressed"]:
            for u in result["unaddressed"][:2]:
                print(f"    [未回答] {u['question'][:60]}...")

        # 建议新问题
        suggestions = suggest_new_questions(wiki)
        if suggestions:
            print(f"  建议新问题:")
            for sq in suggestions:
                print(f"    + {sq}")

        # 标记陈旧问题
        if stale_indices and not args.dry_run:
            count = mark_stale_questions(wiki, stale_indices, args.dry_run)
            if count > 0:
                modified_wikis += 1
                print(f"  -> 已标记 {count} 个陈旧/未回答问题")

        print()
        total_stale += len(result["stale"])
        total_active += len(result["active"])
        total_unaddressed += len(result["unaddressed"])

    print("=" * 50)
    print("  问题清单演化报告")
    print("=" * 50)
    print(f"\n总问题数: {total_active + total_stale + total_unaddressed}")
    print(f"  活跃: {total_active}")
    print(f"  陈旧: {total_stale}")
    print(f"  未回答: {total_unaddressed}")
    print(f"\n修改文件数: {modified_wikis}")

    if not args.dry_run:
        append_log("lint", f"问题清单演化: {total_stale} 陈旧, {total_unaddressed} 未回答, {modified_wikis} 文件更新")


if __name__ == "__main__":
    main()
