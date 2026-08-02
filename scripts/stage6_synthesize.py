#!/usr/bin/env python3
"""
stage6_synthesize.py — 阶段6：Wiki 全量重写与综合演化

取代旧的无脑追加（Append-Only）和零散更新模式。
每当有新数据入库后，收集所有 approved 的 analysis.json 数据，
由 LLM 重新进行全量审阅，生成最新视角的《综合评估.md》和《核心问题.md》。
同时将所有 timeline_entries 按时间线重构为《公司动态.md》。
"""

import argparse
import json
import sys
from datetime import datetime

from common import WIKI_ROOT
from llm_client import get_llm_client

PROMPT_TEMPLATE = """你是一名资深股票分析师。请基于以下最新的公司数据（财报、调研），生成最新的综合评估和核心追踪问题。
必须摒弃陈旧的观点（如数年前的招股书观点），基于最新的数据给出深度、前瞻的研判。

## 公司: {company}

## 最新数据片段（最多包含最近20条核心动态/分析）
{data_context}

## 任务要求
1. 输出《综合评估》，包括：
   - 关键判断：基于最新数据，总结公司当前的核心状态和竞争格局变化。
   - 核心矛盾：识别主要的风险、财务矛盾或市场担忧（如营收与现金流背离、产能过剩）。
   - 投资论点：给出投资建议视角（看多/看空/中立）及其催化剂。
2. 输出《核心问题》，列出3-5个在接下来一个季度/年度需要重点追踪的深度问题。

请只返回一个严格合法的JSON对象，不要输出其他Markdown，格式如下：
{{
  "comprehensive_assessment": "# 综合评估\\n\\n## 关键判断\\n...\\n## 核心矛盾\\n...\\n## 投资论点\\n...",
  "core_questions": "# 核心问题\\n\\n- 问题1: ...\\n- 问题2: ..."
}}
"""

def build_wiki_for_company(company: str, dry_run: bool = False):
    extracts_dir = WIKI_ROOT / "companies" / company / "extracts"
    if not extracts_dir.exists():
        print(f"No extracts found for {company}")
        return

    # 找到所有被 ingest 的 analysis.json
    analysis_files = []
    for ingested_marker in extracts_dir.rglob("*.ingested"):
        review_file = ingested_marker.with_suffix(".json")
        analysis_file = review_file.with_name(review_file.name.replace(".review.json", ".json"))
        if analysis_file.exists():
            analysis_files.append(analysis_file)

    if not analysis_files:
        print(f"No approved analysis found for {company}")
        return

    all_entries = []
    data_context_parts = []

    # 收集所有数据
    for f in analysis_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            llm_output_str = data.get("llm_output", "{}")
            parsed = json.loads(llm_output_str)

            # 收集 timeline
            entries = parsed.get("timeline_entries", [])
            metadata = data.get("metadata", {})
            for e in entries:
                e["_source_pdf"] = metadata.get("source_pdf", "")
                e["_doc_type"] = metadata.get("doc_type", "")
            all_entries.extend(entries)

            # 收集 insights (限制数量以控制 prompt 长度)
            if len(data_context_parts) < 20:
                insights = parsed.get("key_insights", [])
                date = metadata.get("period", "")
                data_context_parts.append(f"### {date} ({metadata.get('doc_type', '')})\\n- " + "\\n- ".join(insights))

        except Exception as e:
            print(f"WARN: Error reading {f}: {e}")

    # 排序 timeline
    all_entries.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 1. 重新生成 公司动态.md (无 LLM，直接生成)
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    
    timeline_md = f"---\ntitle: \"公司动态\"\nentity: \"{company}\"\ntype: company_topic\nlast_updated: {datetime.now().strftime('%Y-%m-%d')}\nsources_count: {len(analysis_files)}\n---\n\n## 近期时间线\n\n"
    
    for entry in all_entries:
        date = entry.get("date", "未知日期")
        title = entry.get("title", "未命名")
        points = entry.get("key_points", [])
        src = entry.get("_source_pdf", "")
        
        timeline_md += f"### {date} | {title}\n"
        for p in points:
            timeline_md += f"- {p}\n"
        if src:
            timeline_md += f"- [来源](../raw/{src})\n"
        timeline_md += "\n"

    if dry_run:
        print(f"[DRY RUN] Would write 公司动态.md with {len(all_entries)} entries.")
    else:
        (wiki_dir / "公司动态.md").write_text(timeline_md, encoding="utf-8")
        print(f"-> 写入 公司动态.md ({len(all_entries)} 条目)")

    # 2. LLM 重写 综合评估 和 核心问题
    client = get_llm_client()
    context_str = "\n\n".join(data_context_parts[:20])
    prompt = PROMPT_TEMPLATE.format(company=company, data_context=context_str)

    if dry_run:
        print(f"[DRY RUN] Would call LLM with prompt ({len(prompt)} chars).")
        return

    print("-> 正在调用 LLM 进行全量评估重写...")
    resp = client.chat(prompt, max_tokens=2048)
    if not resp.success:
        print(f"ERROR: LLM call failed: {resp.error}")
        return

    content = resp.content.strip()
    if content.startswith("```json"):
        content = content[7:-3]
    
    try:
        result_json = json.loads(content)
        assess_md = result_json.get("comprehensive_assessment", "")
        questions_md = result_json.get("core_questions", "")

        # 写入文件
        assess_header = f"---\ntitle: \"综合评估\"\nentity: \"{company}\"\nlast_updated: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n"
        (wiki_dir / "综合评估.md").write_text(assess_header + assess_md, encoding="utf-8")
        
        questions_header = f"---\ntitle: \"核心问题\"\nentity: \"{company}\"\nlast_updated: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n"
        (wiki_dir / "核心问题.md").write_text(questions_header + questions_md, encoding="utf-8")
        
        print("-> 成功重写 综合评估.md 和 核心问题.md")

    except Exception as e:
        print(f"ERROR: Failed to parse LLM synthesis output: {e}\nRaw output:\n{content}")

def main():
    parser = argparse.ArgumentParser(description="阶段6：Wiki 综合重写")
    parser.add_argument("--company", type=str, required=True, help="要处理的公司")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  阶段6：Wiki 全量重写 ({args.company})")
    print(f"{'='*60}")
    
    build_wiki_for_company(args.company, args.dry_run)

from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
