#!/usr/bin/env python3
"""
enrich_wiki.py — Wiki 内容增强模块
为现有 wiki 页面自动生成核心问题和综合评估

用法:
    # 生成核心问题
    python3 scripts/enrich_wiki.py --questions

    # 生成综合评估 (需要 >=5 条时间线条目的页面)
    python3 scripts/enrich_wiki.py --assessments

    # 一键增强: 问题 + 评估
    python3 scripts/enrich_wiki.py --all

    # 查看统计
    python3 scripts/enrich_wiki.py --stats

    # 指定公司
    python3 scripts/enrich_wiki.py --questions --company 中微公司
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))


def load_graph():
    """加载 graph.yaml"""
    import yaml
    graph_path = WIKI_ROOT / "graph.yaml"
    if not graph_path.exists():
        return {}
    with open(graph_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_company_info(graph_data: dict, company_name: str) -> dict:
    """获取公司信息"""
    # Try top-level companies key
    companies = graph_data.get("companies", {})
    if company_name in companies:
        return companies[company_name]
    # Try nodes
    for name, info in graph_data.get("nodes", {}).items():
        if name == company_name:
            return info
    return {}


def scan_wiki_pages(company_filter: str = None) -> List[Dict[str, Any]]:
    """扫描所有 wiki 页面, 返回结构化信息"""
    pages = []

    for pattern_dir, entity_type in [
        ("companies", "company"),
        ("sectors", "sector"),
        ("themes", "theme"),
    ]:
        base = WIKI_ROOT / pattern_dir
        if not base.exists():
            continue

        for entity_dir in base.iterdir():
            if not entity_dir.is_dir():
                continue

            if company_filter and entity_dir.name != company_filter:
                continue

            wiki_dir = entity_dir / "wiki"
            if not wiki_dir.exists():
                continue

            for wiki_file in wiki_dir.glob("*.md"):
                try:
                    content = wiki_file.read_text(encoding="utf-8")
                    page_info = parse_wiki_page(content, wiki_file, entity_dir.name, entity_type)
                    if page_info:
                        pages.append(page_info)
                except Exception:
                    continue

    return pages


def parse_wiki_page(content: str, file_path: Path, entity_name: str, entity_type: str) -> Optional[Dict]:
    """解析 wiki 页面"""
    # 提取 frontmatter
    title = file_path.stem
    last_updated = ""
    sources_count = 0

    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            front = content[3:end]
            for line in front.strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key == "title":
                        title = val
                    elif key == "last_updated":
                        last_updated = val
                    elif key == "sources_count":
                        try:
                            sources_count = int(val)
                        except ValueError:
                            pass

    # 提取核心问题
    core_questions = []
    questions_match = re.search(r'## 核心问题\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if questions_match:
        for line in questions_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line and line != "（待设定）":
                core_questions.append(line)

    # 提取时间线条目
    timeline_entries = []
    timeline_match = re.search(r'## 时间线\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if timeline_match:
        # 提取每个 ### 条目
        entry_pattern = r'### (\d{4}-\d{2}-\d{2}) \| ([^|]+) \| (.+?)\n(.*?)(?=\n### |\Z)'
        for match in re.finditer(entry_pattern, timeline_match.group(1), re.DOTALL):
            date, source_type, entry_title, body = match.groups()
            # 提取要点
            points = []
            for line in body.strip().split("\n"):
                line = line.strip()
                if line.startswith("- ") and not line.startswith("- [来源]"):
                    points.append(line[2:])
            timeline_entries.append({
                "date": date,
                "source_type": source_type.strip(),
                "title": entry_title.strip(),
                "points": points,
                "raw": f"### {date} | {source_type} | {entry_title}\n{body.strip()}",
            })

    # 检查综合评估状态
    assessment = ""
    assessment_match = re.search(r'## 综合评估\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if assessment_match:
        assessment = assessment_match.group(1).strip()
    has_assessment = bool(assessment and "待积累数据后补充" not in assessment)

    return {
        "path": file_path,
        "title": title,
        "entity_name": entity_name,
        "entity_type": entity_type,
        "last_updated": last_updated,
        "sources_count": sources_count,
        "core_questions": core_questions,
        "has_core_questions": len(core_questions) > 0,
        "timeline_entries": timeline_entries,
        "timeline_count": len(timeline_entries),
        "assessment": assessment,
        "has_assessment": has_assessment,
        "content": content,
    }


def generate_core_questions(pages: List[Dict], graph_data: dict, dry_run: bool = False) -> int:
    """为缺少核心问题的页面生成问题"""
    from llm_client import LLMClient

    llm = LLMClient()
    if not llm.available:
        print("  LLM 不可用, 跳过核心问题生成")
        return 0

    updated = 0
    pages_needing_questions = [p for p in pages if not p["has_core_questions"]]

    print(f"  需要生成核心问题的页面: {len(pages_needing_questions)}")

    for i, page in enumerate(pages_needing_questions):
        entity = page["entity_name"]
        print(f"  [{i+1}/{len(pages_needing_questions)}] {entity}/{page['title']}", end="")

        # 获取实体信息
        entity_info = get_company_info(graph_data, entity)
        sector = ", ".join(entity_info.get("sectors", []))
        position = entity_info.get("position", "")

        # 提取时间线摘要作为已有数据
        existing_data = ""
        if page["timeline_entries"]:
            summaries = []
            for entry in page["timeline_entries"][:5]:
                summaries.append(f"{entry['date']}: {'; '.join(entry['points'][:2])}")
            existing_data = "\n".join(summaries)

        # 调用 LLM 生成核心问题
        questions = llm.generate_core_questions(
            entity=entity,
            sector=sector,
            position=position,
            existing_data=existing_data,
        )

        if questions:
            # 写入页面
            new_content = update_core_questions(page["content"], questions)
            if new_content != page["content"] and not dry_run:
                page["path"].write_text(new_content, encoding="utf-8")
            updated += 1
            print(f" -> {len(questions)} questions")
        else:
            print(f" -> skipped")

    return updated


def generate_assessments(pages: List[Dict], dry_run: bool = False) -> int:
    """为缺少综合评估的页面生成评估"""
    from llm_client import LLMClient

    llm = LLMClient()
    if not llm.available:
        print("  LLM 不可用, 跳过综合评估生成")
        return 0

    updated = 0
    # 只处理有 >= 3 条时间线条目且缺少评估的页面
    pages_needing_assessment = [
        p for p in pages
        if not p["has_assessment"] and p["timeline_count"] >= 3
    ]

    print(f"  需要生成综合评估的页面: {len(pages_needing_assessment)}")

    for i, page in enumerate(pages_needing_assessment):
        entity = page["entity_name"]
        topic = page["title"]
        print(f"  [{i+1}/{len(pages_needing_assessment)}] {entity}/{topic}", end="")

        # 收集时间线条目文本
        timeline_texts = [entry["raw"] for entry in page["timeline_entries"][:15]]

        # 调用 LLM 生成评估
        assessment = llm.synthesize_assessment(
            timeline_entries=timeline_texts,
            topic=topic,
            entity=entity,
            core_questions=page["core_questions"] if page["has_core_questions"] else None,
        )

        if assessment and "待积累数据后补充" not in assessment:
            # 写入页面
            new_content = update_assessment(page["content"], assessment)
            if new_content != page["content"] and not dry_run:
                page["path"].write_text(new_content, encoding="utf-8")
            updated += 1
            print(f" -> done")
        else:
            print(f" -> skipped")

    return updated


def update_core_questions(content: str, questions: List[str]) -> str:
    """更新页面中的核心问题"""
    # 替换 "（待设定）" 或空的 "## 核心问题" 区域
    questions_text = "\n".join(f"- {q}" for q in questions)
    new_section = f"## 核心问题\n{questions_text}\n"

    # 找到核心问题区域
    pattern = r'## 核心问题\s*\n.*?(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_section + content[match.end():]

    return content


def update_assessment(content: str, assessment: str) -> str:
    """更新页面中的综合评估"""
    new_section = f"## 综合评估\n{assessment}\n"

    # 找到综合评估区域
    pattern = r'## 综合评估\s*\n.*?(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_section + content[match.end():]

    return content


def show_stats(pages: List[Dict]):
    """显示统计信息"""
    total = len(pages)
    has_questions = sum(1 for p in pages if p["has_core_questions"])
    has_assessment = sum(1 for p in pages if p["has_assessment"])
    has_timeline = sum(1 for p in pages if p["timeline_count"] > 0)

    print(f"\n  Wiki 页面总数: {total}")
    print(f"  有核心问题的页面: {has_questions}/{total} ({100*has_questions/max(total,1):.0f}%)")
    print(f"  有综合评估的页面: {has_assessment}/{total} ({100*has_assessment/max(total,1):.0f}%)")
    print(f"  有时间线的页面: {has_timeline}/{total}")
    print(f"  可生成评估的页面 (>=3条目): {sum(1 for p in pages if p['timeline_count'] >= 3)}")

    # 显示时间线条目分布
    counts = [p["timeline_count"] for p in pages]
    if counts:
        print(f"\n  时间线条目数: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")


def main():
    parser = argparse.ArgumentParser(description="Wiki 内容增强")
    parser.add_argument("--questions", action="store_true", help="生成核心问题")
    parser.add_argument("--assessments", action="store_true", help="生成综合评估")
    parser.add_argument("--all", action="store_true", help="一键增强")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--company", type=str, help="指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    args = parser.parse_args()

    print("=" * 50)
    print("  Wiki 内容增强")
    print("=" * 50)

    # 加载数据
    graph_data = load_graph()
    pages = scan_wiki_pages(args.company)

    print(f"\n  扫描到 {len(pages)} 个 wiki 页面")

    if args.stats:
        show_stats(pages)
        return

    if not args.questions and not args.assessments and not args.all:
        parser.print_help()
        return

    total_updated = 0

    if args.all or args.questions:
        print("\n  --- 生成核心问题 ---")
        count = generate_core_questions(pages, graph_data, dry_run=args.dry_run)
        total_updated += count
        print(f"  更新了 {count} 个页面的核心问题")

    if args.all or args.assessments:
        print("\n  --- 生成综合评估 ---")
        # 重新扫描 (questions 可能已更新)
        if not args.dry_run:
            pages = scan_wiki_pages(args.company)
        count = generate_assessments(pages, dry_run=args.dry_run)
        total_updated += count
        print(f"  更新了 {count} 个页面的综合评估")

    print(f"\n{'=' * 50}")
    action = "将更新" if args.dry_run else "已更新"
    print(f"  {action} {total_updated} 个页面")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
