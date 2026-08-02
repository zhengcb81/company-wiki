#!/usr/bin/env python3
"""
question_evolver.py — 核心问题动态进化器

LLM建议新问题，人类审核后采纳。

用法：
    python scripts/question_evolver.py --company 中微公司 --suggest   # 建议新问题
    python scripts/question_evolver.py --company 中微公司 --list      # 列出当前问题
    python scripts/question_evolver.py --company 中微公司 --review    # 生成审核清单
"""

import argparse
import re
from datetime import datetime

from common import WIKI_ROOT
from llm_client import LLMClient

SUGGEST_PROMPT_TEMPLATE = """你是一名资深股票分析师。请基于以下公司信息，建议3-5个新的核心追踪问题。

## 公司: {company}

## 当前核心问题
{current_questions}

## 最近时间线（最近10条）
{recent_timeline}

## 要求
1. 建议的问题应该是**可以追踪和验证**的（不是空泛的问题）
2. 建议的问题应该**关注未来**（不是回顾过去）
3. 建议的问题应该**有投资价值**（答案会影响投资判断）
4. 避免与现有问题重复

## 输出格式
```json
{{
  "suggested_questions": [
    {{
      "question": "问题内容",
      "rationale": "为什么这个问题重要",
      "category": "业绩/技术/竞争/风险/其他"
    }}
  ]
}}
```
"""


def get_current_questions(company: str) -> list:
    """获取当前核心问题"""
    # 从graph.yaml读取
    import yaml

    graph_path = WIKI_ROOT / "graph.yaml"
    if not graph_path.exists():
        return []

    graph = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
    companies = graph.get("companies", {})

    for comp in companies:
        if isinstance(comp, dict) and comp.get("name") == company:
            return comp.get("questions", [])

    return []


def get_recent_timeline(company: str, max_entries: int = 10) -> str:
    """获取最近的时间线条目"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    timeline_file = wiki_dir / "公司动态.md"

    if not timeline_file.exists():
        return "无时间线"

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
    recent = entries[-max_entries:]
    return "\n\n".join(recent)


def suggest_questions(company: str) -> dict:
    """建议新问题"""
    current_questions = get_current_questions(company)
    recent_timeline = get_recent_timeline(company)

    # 构建prompt
    prompt = SUGGEST_PROMPT_TEMPLATE.format(
        company=company,
        current_questions="\n".join(f"- {q}" for q in current_questions)
        if current_questions
        else "无",
        recent_timeline=recent_timeline[:10000],
    )

    # 调用LLM
    try:
        client = LLMClient()
        response = client.generate(prompt)
        result_text = response.content
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 解析结果
    try:
        # 提取JSON
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", result_text, re.DOTALL)
        if json_match:
            import json

            result = json.loads(json_match.group(1))
        else:
            import json

            result = json.loads(result_text)
    except Exception:
        return {
            "success": False,
            "error": "Failed to parse LLM output",
            "raw": result_text,
        }

    return {
        "success": True,
        "company": company,
        "current_questions": current_questions,
        "suggested_questions": result.get("suggested_questions", []),
    }


def list_questions(company: str):
    """列出当前问题"""
    questions = get_current_questions(company)

    print(f"\n{company} 当前核心问题:")
    print("=" * 60)

    if not questions:
        print("无核心问题")
    else:
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")


def generate_review(company: str):
    """生成审核清单"""
    result = suggest_questions(company)

    if not result.get("success"):
        print(f"错误: {result.get('error')}")
        return

    suggested = result.get("suggested_questions", [])

    print(f"\n{company} 问题建议审核清单:")
    print("=" * 60)

    if not suggested:
        print("无新建议")
        return

    for i, q in enumerate(suggested, 1):
        print(f"\n{i}. {q.get('question', '?')}")
        print(f"   类别: {q.get('category', '?')}")
        print(f"   理由: {q.get('rationale', '?')}")

    # 保存到审核队列
    review_path = WIKI_ROOT / "docs" / f"question_review_{company}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""# 问题建议审核: {company}

**生成时间**: {timestamp}

---

## 当前问题

{chr(10).join(f"- {q}" for q in result.get("current_questions", []))}

---

## 建议新问题

"""

    for i, q in enumerate(suggested, 1):
        content += f"""### {i}. {q.get("question", "?")}

- **类别**: {q.get("category", "?")}
- **理由**: {q.get("rationale", "?")}
- **采纳**: [ ] 是 / [ ] 否

"""

    content += """
---

## 审核说明

请审核以上问题建议：
1. 选择要采纳的问题（勾选"采纳: 是"）
2. 可以修改问题内容
3. 保存此文件后，运行 --apply 命令更新graph.yaml
"""

    review_path.write_text(content, encoding="utf-8")
    print(f"\n审核清单已保存: {review_path}")


def main():
    parser = argparse.ArgumentParser(description="核心问题动态进化器")
    parser.add_argument("--company", required=True, help="公司名称")
    parser.add_argument("--suggest", action="store_true", help="建议新问题")
    parser.add_argument("--list", action="store_true", help="列出当前问题")
    parser.add_argument("--review", action="store_true", help="生成审核清单")
    args = parser.parse_args()

    if args.list:
        list_questions(args.company)
    elif args.suggest:
        result = suggest_questions(args.company)
        if result.get("success"):
            suggested = result.get("suggested_questions", [])
            print(f"\n{args.company} 建议新问题:")
            print("=" * 60)
            for i, q in enumerate(suggested, 1):
                print(f"{i}. {q.get('question', '?')}")
                print(f"   类别: {q.get('category', '?')}")
        else:
            print(f"错误: {result.get('error')}")
    elif args.review:
        generate_review(args.company)
    else:
        list_questions(args.company)


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
