#!/usr/bin/env python3
"""
stage3_analyze.py — 阶段3 Pipeline：LLM 分析

从 companies/{name}/extracts/ 读取提取的 Markdown，
调用 LLM 分析，验证输出，保存结果。

用法：
    python scripts/stage3_analyze.py                    # 处理所有公司
    python scripts/stage3_analyze.py --company 北方华创  # 只处理指定公司
    python scripts/stage3_analyze.py --check             # 列出待处理文件
    python scripts/stage3_analyze.py --dry-run           # 预览
    python scripts/stage3_analyze.py --limit 3           # 最多处理3个
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT
from config import Config
from llm_client import LLMClient
from llm_output_validator import validate_llm_output
from prompts import (
    build_financial_report_prompt,
    build_ir_prompt,
    build_analysis_prompt,
)
from graph import Graph
from framework_loader import FrameworkLoader

# 初始化框架加载器
framework_loader = FrameworkLoader()


def get_stage3_db_path() -> Path:
    return WIKI_ROOT / ".stage3_db.json"


def load_stage3_db() -> dict:
    db_path = get_stage3_db_path()
    if db_path.exists():
        try:
            return json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_stage3_db(db: dict):
    get_stage3_db_path().write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_extract_content(extract_path: Path) -> tuple:
    """读取提取文件，返回 (metadata, body)"""
    content = extract_path.read_text(encoding="utf-8")

    frontmatter_match = re.match(r"---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        return {}, content

    frontmatter = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    metadata = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')

    return metadata, body


def get_core_questions(graph, entity_name: str) -> list:
    """获取实体的核心问题"""
    company = graph.get_company(entity_name)
    if company:
        return company.get("questions", [])
    return ["公司最新动态如何？"]


def build_prompt_for_doc(
    metadata: dict, body: str, entity_name: str, core_questions: list
) -> str:
    """根据文档类型构建 prompt（优先使用配置驱动的Prompt）"""
    doc_type = metadata.get("doc_type", "unknown")
    period = metadata.get("period", "")

    # 截取 body 前 25000 字符（避免超出 token 限制）
    content = body[:25000]

    # 尝试使用配置驱动的Prompt
    try:
        framework = framework_loader.load_framework(doc_type, entity_name)
        template_config = framework_loader.load_prompt_template(doc_type)

        # 检查是否有有效的模板
        if template_config and "template" in template_config:
            # 从metadata中获取sections
            sections = metadata.get("sections", [])

            # 构建各部分
            framework_description = framework_loader.build_framework_description(
                framework
            )
            source_sections_description = (
                framework_loader.build_source_sections_description(framework, sections)
            )
            output_schema = framework_loader.build_output_schema(framework)

            # 渲染Prompt
            prompt = template_config["template"].format(
                company=entity_name,
                period=period,
                source_sections_description=source_sections_description,
                core_questions="\n".join(
                    f"{i + 1}. {q}" for i, q in enumerate(core_questions)
                ),
                framework_description=framework_description,
                content=content,
                output_schema=output_schema,
            )
            return prompt
    except Exception as e:
        # 如果配置驱动失败，回退到原有逻辑
        print(f"Warning: 配置驱动Prompt失败，回退到原有逻辑: {e}")

    # 回退到原有逻辑
    if doc_type in ["annual_report", "semi_annual_report", "quarterly_report"]:
        report_type = {
            "annual_report": "年度报告",
            "semi_annual_report": "半年度报告",
            "quarterly_report": "季度报告",
        }.get(doc_type, "报告")

        return build_financial_report_prompt(
            content=content,
            entity_name=entity_name,
            report_type=report_type,
            period=period,
            core_questions=core_questions,
            max_content_chars=25000,
        )
    elif doc_type == "investor_relations":
        return build_ir_prompt(
            content=content,
            entity_name=entity_name,
            event_date=period,
            core_questions=core_questions,
            max_content_chars=25000,
        )
    else:
        return build_analysis_prompt(
            content=content,
            entity_name=entity_name,
            source_type=doc_type,
            published_date=period,
            core_questions=core_questions,
            max_content_chars=25000,
        )


def analyze_single_file(
    extract_path: Path, client: LLMClient, graph: Graph, dry_run=False
) -> dict:
    """分析单个提取文件"""
    metadata, body = load_extract_content(extract_path)

    if not metadata:
        return {"status": "error", "error": "No metadata found"}

    doc_type = metadata.get("doc_type", "unknown")
    company = metadata.get("company", "unknown")
    period = metadata.get("period", "")

    # 从文件路径推断文档类型（如果metadata中没有）
    if doc_type == "unknown":
        # 使用正斜杠统一路径，避免Windows反斜杠转义问题
        path_str = str(extract_path).lower().replace("\\", "/")
        if "research" in path_str or "研报" in path_str:
            doc_type = "research_report"
        elif "investor_relations" in path_str or "投资者关系" in path_str:
            doc_type = "investor_relations"
        elif "prospectus" in path_str or "招股" in path_str:
            doc_type = "prospectus"
        elif "annual" in path_str or "年报" in path_str:
            doc_type = "annual_report"
        elif "semi_annual" in path_str or "半年报" in path_str:
            doc_type = "semi_annual_report"
        elif "quarterly" in path_str or "季报" in path_str:
            doc_type = "quarterly_report"

    # 获取核心问题
    core_questions = get_core_questions(graph, company)

    # 构建 prompt
    prompt = build_prompt_for_doc(metadata, body, company, core_questions)

    if dry_run:
        return {
            "status": "dry_run",
            "doc_type": doc_type,
            "company": company,
            "period": period,
            "prompt_length": len(prompt),
            "body_length": len(body),
        }

    # 调用 LLM
    try:
        response = client.generate(prompt)
        llm_output = response.content
    except Exception as e:
        return {"status": "error", "error": f"LLM call failed: {e}"}

    # 预处理：提取 markdown 代码块中的 JSON（如果有）
    import re as re_module

    if llm_output.strip().startswith("```"):
        json_match = re_module.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", llm_output, re_module.DOTALL
        )
        if json_match:
            llm_output_clean = json_match.group(1).strip()
        else:
            llm_output_clean = llm_output
    else:
        llm_output_clean = llm_output

    # 验证输出（使用完整文本进行数字对比，避免漏检）
    validation = validate_llm_output(llm_output, body, doc_type)

    # 保存结果（保存清理后的JSON，便于后续Gate处理）
    result_path = extract_path.with_suffix(".analysis.json")
    result = {
        "metadata": metadata,
        "llm_output": llm_output_clean,
        "validation": {
            "status": validation["status"],
            "json_valid": validation["json_valid"],
            "field_check": validation["field_check"],
            "timeline_check": validation["timeline_check"],
            "financial_check": validation["financial_check"],
            "logic_check": validation["logic_check"],
            "hallucination": {
                "has_hallucination": validation["hallucination"]["has_hallucination"],
                "hallucinated_count": len(
                    validation["hallucination"]["hallucinated_numbers"]
                ),
                "verified_count": len(validation["hallucination"]["verified_numbers"]),
            },
            "issues": validation["all_issues"],
        },
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "status": "success",
        "validation_status": validation["status"],
        "result_path": str(result_path),
        "parsed": validation.get("parsed"),
        "issues_count": len(validation["all_issues"]),
        "issues": validation["all_issues"][:5],  # 只返回前5个问题
    }


def main():
    parser = argparse.ArgumentParser(description="阶段3：LLM 分析")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  阶段3：LLM 分析")
    print("=" * 60)

    # 初始化 LLM 客户端
    try:
        config = Config.load()
        client = LLMClient(config=config)
        print(f"LLM: {client.provider} / {client.model}")
    except Exception as e:
        print(f"ERROR: 无法初始化 LLM 客户端: {e}")
        return 1

    # 初始化 Graph
    graph = Graph()

    # 扫描待处理文件
    extract_files = []
    companies_dir = WIKI_ROOT / "companies"

    if args.company:
        company_dirs = [companies_dir / args.company]
    else:
        company_dirs = list(companies_dir.iterdir())

    for company_dir in company_dirs:
        if not company_dir.is_dir():
            continue
        extracts_dir = company_dir / "extracts"
        if not extracts_dir.exists():
            continue
        for md_file in extracts_dir.rglob("*.md"):
            analysis_file = md_file.with_suffix(".analysis.json")
            if not analysis_file.exists():
                extract_files.append(md_file)

    print(f"找到 {len(extract_files)} 个待处理文件")

    if args.check:
        for f in extract_files[:20]:
            print(f"  {f.relative_to(WIKI_ROOT)}")
        if len(extract_files) > 20:
            print(f"  ... 还有 {len(extract_files) - 20} 个")
        return 0

    if not extract_files:
        print("没有待处理的文件")
        return 0

    if args.limit > 0:
        extract_files = extract_files[: args.limit]
        print(f"限制处理 {len(extract_files)} 个文件")

    success = 0
    needs_review = 0
    failed = 0
    errors = 0

    for i, extract_path in enumerate(extract_files, 1):
        print(f"\n[{i}/{len(extract_files)}] {extract_path.relative_to(WIKI_ROOT)}")
        result = analyze_single_file(extract_path, client, graph, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            validation_status = result["validation_status"]
            if validation_status == "passed":
                success += 1
                print(f"  -> OK | passed | issues: {result['issues_count']}")
            elif validation_status == "needs_review":
                needs_review += 1
                print(f"  -> OK | needs_review | issues: {result['issues_count']}")
                for issue in result.get("issues", [])[:3]:
                    print(f"     - {issue}")
            else:
                failed += 1
                print(f"  -> OK | failed | issues: {result['issues_count']}")
                for issue in result.get("issues", [])[:3]:
                    print(f"     - {issue}")
        elif status == "dry_run":
            print(f"  -> DRY-RUN | prompt: {result['prompt_length']} chars")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print(
            f"完成: {success} 通过, {needs_review} 待审核, {failed} 失败, {errors} 错误"
        )
        print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
