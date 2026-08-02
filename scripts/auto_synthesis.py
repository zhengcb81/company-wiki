#!/usr/bin/env python3
"""
auto_synthesis.py — 自动综合触发器

当公司wiki时间线条目超过阈值时，自动触发LLM综合评估更新。

用法：
    python scripts/auto_synthesis.py --company 中微公司 --check    # 检查是否需要综合
    python scripts/auto_synthesis.py --company 中微公司 --run       # 运行综合
    python scripts/auto_synthesis.py --company 中微公司 --dry-run   # 预览综合
"""

import argparse
import re
from datetime import datetime

from common import WIKI_ROOT
from llm_client import LLMClient

# 配置
TIMELINE_THRESHOLD = 50  # 时间线条目阈值
SYNTHESIS_PROMPT_TEMPLATE = """你是一名资深股票分析师。请基于以下时间线条目，生成一份综合评估。

## 公司: {company}

## 时间线条目（共{count}条）
{timeline_entries}

## 要求
1. **关键判断**: 基于时间线，总结公司当前的核心状态（3-5条）
2. **核心矛盾**: 识别时间线中的主要矛盾或风险（2-3条）
3. **投资论点**: 基于以上分析，给出投资建议（看多/看空/中性，附理由）

## 输出格式
```json
{{
  "key_judgments": ["判断1", "判断2", ...],
  "core_contradictions": ["矛盾1", "矛盾2", ...],
  "investment_thesis": {{
    "stance": "bullish/bearish/neutral",
    "reasons": ["原因1", "原因2", ...]
  }}
}}
```
"""


def count_timeline_entries(company: str) -> int:
    """统计公司时间线条目数量"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    if not wiki_dir.exists():
        return 0

    # 找到主要的时间线文件（公司动态.md）
    timeline_file = wiki_dir / "公司动态.md"
    if not timeline_file.exists():
        return 0

    content = timeline_file.read_text(encoding="utf-8")

    # 统计时间线条目（### YYYY-MM-DD 格式）
    entries = re.findall(r"^### \d{4}-\d{2}-\d{2}", content, re.MULTILINE)
    return len(entries)


def extract_timeline_entries(company: str, max_entries: int = 100) -> str:
    """提取时间线条目"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    timeline_file = wiki_dir / "公司动态.md"

    if not timeline_file.exists():
        return ""

    content = timeline_file.read_text(encoding="utf-8")

    # 提取时间线条目
    entries = []
    current_entry = []

    for line in content.split("\n"):
        if line.startswith("### "):
            if current_entry:
                entries.append("\n".join(current_entry))
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)

    if current_entry:
        entries.append("\n".join(current_entry))

    # 只取最近的条目
    recent_entries = entries[-max_entries:]

    return "\n\n".join(recent_entries)


def check_synthesis_needed(company: str) -> dict:
    """检查是否需要综合"""
    entry_count = count_timeline_entries(company)

    # 检查是否已有综合评估
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    synthesis_file = wiki_dir / "综合评估.md"

    has_synthesis = synthesis_file.exists()
    synthesis_date = None

    if has_synthesis:
        content = synthesis_file.read_text(encoding="utf-8")
        # 提取最后更新日期
        date_match = re.search(r"最后更新: (\d{4}-\d{2}-\d{2})", content)
        if date_match:
            synthesis_date = date_match.group(1)

    return {
        "company": company,
        "entry_count": entry_count,
        "threshold": TIMELINE_THRESHOLD,
        "needs_synthesis": entry_count >= TIMELINE_THRESHOLD,
        "has_synthesis": has_synthesis,
        "synthesis_date": synthesis_date,
    }


def run_synthesis(company: str, dry_run: bool = False) -> dict:
    """运行综合评估"""
    # 提取时间线条目
    timeline_text = extract_timeline_entries(company)
    entry_count = count_timeline_entries(company)

    if not timeline_text:
        return {"success": False, "error": "No timeline entries found"}

    # 构建prompt
    prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        company=company,
        count=entry_count,
        timeline_entries=timeline_text[:20000],  # 限制长度
    )

    if dry_run:
        print("=" * 60)
        print("  预览综合评估")
        print("=" * 60)
        print(f"\n公司: {company}")
        print(f"时间线条目: {entry_count}")
        print(f"\nPrompt长度: {len(prompt)} 字符")
        print("\nPrompt前500字符:")
        print(prompt[:500])
        return {"success": True, "dry_run": True}

    # 调用LLM
    try:
        client = LLMClient()
        response = client.generate(prompt)
        synthesis_text = response.content
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 保存综合评估
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    synthesis_file = wiki_dir / "综合评估.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
title: {company} 综合评估
description: 基于时间线条目的自动综合评估
entity: {company}
type: overview
last_updated: {timestamp}
source: auto_synthesis
---

# {company} 综合评估

**生成时间**: {timestamp}
**基于条目数**: {entry_count}
**生成方式**: 自动综合触发器

---

{synthesis_text}

---

*此评估由 auto_synthesis.py 自动生成，基于公司时间线条目。*
"""

    synthesis_file.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "company": company,
        "entry_count": entry_count,
        "output_file": str(synthesis_file),
    }


def main():
    parser = argparse.ArgumentParser(description="自动综合触发器")
    parser.add_argument("--company", required=True, help="公司名称")
    parser.add_argument("--check", action="store_true", help="检查是否需要综合")
    parser.add_argument("--run", action="store_true", help="运行综合")
    parser.add_argument("--dry-run", action="store_true", help="预览综合")
    args = parser.parse_args()

    if args.check:
        result = check_synthesis_needed(args.company)
        print("\n综合检查:")
        print("=" * 60)
        print(f"公司: {result['company']}")
        print(f"时间线条目: {result['entry_count']}")
        print(f"阈值: {result['threshold']}")
        print(f"需要综合: {result['needs_synthesis']}")
        print(f"已有综合: {result['has_synthesis']}")
        if result["synthesis_date"]:
            print(f"综合日期: {result['synthesis_date']}")
    elif args.run or args.dry_run:
        result = run_synthesis(args.company, dry_run=args.dry_run)
        if result.get("success"):
            if not args.dry_run:
                print(f"\n综合评估已生成: {result.get('output_file')}")
        else:
            print(f"\n错误: {result.get('error')}")
    else:
        # 默认检查
        result = check_synthesis_needed(args.company)
        print(
            f"{args.company}: {result['entry_count']} 条目, 需要综合: {result['needs_synthesis']}"
        )


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
