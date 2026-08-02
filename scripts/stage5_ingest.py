#!/usr/bin/env python3
"""
stage5_ingest.py — 阶段5 Pipeline：入库与审查队列

从 companies/{name}/extracts/ 读取审查结果，
将 approved 的内容写入 wiki，将 needs_revision 的加入审查队列。

用法：
    python scripts/stage5_ingest.py                    # 处理所有已审查文件
    python scripts/stage5_ingest.py --company 北方华创  # 只处理指定公司
    python scripts/stage5_ingest.py --check             # 列出待入库文件
    python scripts/stage5_ingest.py --dry-run           # 预览
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT


def get_review_queue_path() -> Path:
    return WIKI_ROOT / "review_queue.md"


def append_to_review_queue(entry: dict):
    """追加到审查队列"""
    queue_path = get_review_queue_path()

    # 如果文件不存在，创建模板
    if not queue_path.exists():
        queue_path.write_text(
            """# 审查队列

> 自动由 stage5_ingest.py 生成。
> 需要人工审查的项目会追加到此文件。

---

""",
            encoding="utf-8",
        )

    # 追加条目
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    priority = entry.get("priority", "MEDIUM")
    company = entry.get("company", "unknown")
    doc_type = entry.get("doc_type", "unknown")
    period = entry.get("period", "")
    reason = entry.get("reason", "")
    score = entry.get("score", 0)
    issues = entry.get("issues", [])

    md = f"""
### [{priority}] {company} {period} {doc_type} — 待审查
- **来源**: 阶段5入库
- **分数**: {score}/5.0
- **原因**: {reason}
- **问题**:
"""
    for issue in issues[:5]:
        md += f"  - {issue}\n"

    md += f"- **添加时间**: {now}\n"

    with open(queue_path, "a", encoding="utf-8") as f:
        f.write(md)


def generate_wiki_entry(parsed: dict, metadata: dict) -> str:
    """从 LLM 分析结果生成 wiki 时间线条目"""
    entries = parsed.get("timeline_entries", [])

    if not entries:
        return ""

    metadata.get("company", "unknown")
    period = metadata.get("period", "")
    doc_type = metadata.get("doc_type", "unknown")

    # 文档类型映射
    type_map = {
        "annual_report": "年报",
        "semi_annual_report": "半年报",
        "quarterly_report": "季报",
        "investor_relations": "投资者关系",
        "prospectus": "招股说明书",
        "research_report": "研报",
        "announcement": "公告",
    }
    source_type = type_map.get(doc_type, doc_type)

    wiki_entries = []
    for entry in entries:
        date = entry.get("date", period)
        title = entry.get("title", "未命名")
        key_points = entry.get("key_points", [])
        entry.get("importance", 0.5)
        entry.get("sentiment", "neutral")

        # 构建条目
        points_md = "\n".join(f"- {p}" for p in key_points)

        entry_md = f"""### {date} | {source_type} | {title}
{points_md}
"""
        wiki_entries.append(entry_md)

    return "\n".join(wiki_entries)


def write_to_wiki(company: str, wiki_entry: str, metadata: dict) -> bool:
    """将时间线条目写入公司wiki页面"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    wiki_path = wiki_dir / "公司动态.md"

    if not wiki_path.exists():
        # 如果wiki文件不存在，不创建（避免生成空wiki）
        return False

    try:
        content = wiki_path.read_text(encoding="utf-8")

        # 找到 "## 近期时间线" 部分并插入新条目
        timeline_marker = "## 近期时间线"
        if timeline_marker in content:
            # 在标记后插入新条目
            insert_pos = content.find(timeline_marker) + len(timeline_marker)
            # 跳过下一行（如果有空行）
            while insert_pos < len(content) and content[insert_pos] == "\n":
                insert_pos += 1

            # 构建新条目（带来源信息）
            source_pdf = metadata.get("source_pdf", "")
            source_link = f"- [来源](../raw/{source_pdf})" if source_pdf else ""
            entry_with_source = wiki_entry.strip()
            if source_link:
                entry_with_source += f"\n{source_link}\n"
            else:
                entry_with_source += "\n"

            new_content = (
                content[:insert_pos]
                + "\n"
                + entry_with_source
                + "\n"
                + content[insert_pos:]
            )
            wiki_path.write_text(new_content, encoding="utf-8")

            # 更新 frontmatter 中的 last_updated 和 sources_count
            # 简单替换 last_updated 行
            today = datetime.now().strftime("%Y-%m-%d")
            content_after = wiki_path.read_text(encoding="utf-8")
            updated_content = re.sub(
                r"last_updated:\s*\d{4}-\d{2}-\d{2}",
                f"last_updated: {today}",
                content_after,
            )
            # 增加 sources_count
            updated_content = re.sub(
                r"sources_count:\s*(\d+)",
                lambda m: f"sources_count: {int(m.group(1)) + 1}",
                updated_content,
            )
            wiki_path.write_text(updated_content, encoding="utf-8")
            return True
        else:
            # 如果没有时间线标记，追加到文件末尾
            with open(wiki_path, "a", encoding="utf-8") as f:
                f.write("\n## 近期时间线\n\n" + wiki_entry + "\n")
            return True
    except Exception as e:
        print(f"  WARN: 写入wiki失败: {e}")
        return False


def ingest_single_file(review_path: Path, dry_run=False) -> dict:
    """入库单个审查结果"""
    try:
        content = review_path.read_text(encoding="utf-8")
        review = json.loads(content)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    metadata = review.get("metadata", {})
    quality = review.get("quality_score", {})
    financial = review.get("financial_checks", {})

    company = metadata.get("company", "unknown")
    doc_type = metadata.get("doc_type", "unknown")
    period = metadata.get("period", "")
    review_status = review.get("review_status", "unknown")
    total_score = quality.get("total_score", 0)

    # 读取对应的 analysis.json 获取 LLM 输出
    # review_path 格式: xxx.analysis.review.json
    # analysis_path 格式: xxx.analysis.json
    analysis_path = review_path.with_name(
        review_path.name.replace(".analysis.review.json", ".analysis.json")
    )
    if not analysis_path.exists():
        return {
            "status": "error",
            "error": f"analysis.json not found: {analysis_path.name}",
        }

    try:
        analysis_content = analysis_path.read_text(encoding="utf-8")
        analysis = json.loads(analysis_content)
        llm_output = analysis.get("llm_output", "")
        parsed = json.loads(llm_output)
    except Exception as e:
        return {"status": "error", "error": f"Failed to parse analysis: {e}"}

    # 生成 wiki 条目
    wiki_entry = generate_wiki_entry(parsed, metadata)

    if dry_run:
        return {
            "status": "dry_run",
            "review_status": review_status,
            "total_score": total_score,
            "wiki_entry_preview": wiki_entry[:200] + "..."
            if len(wiki_entry) > 200
            else wiki_entry,
        }

    # 根据审查状态决定处理方式
    if review_status == "approved":
        # 直接入库：写入wiki文件
        wiki_written = False
        if wiki_entry.strip():
            wiki_written = write_to_wiki(company, wiki_entry, metadata)

        return {
            "status": "success",
            "action": "ingest",
            "review_status": review_status,
            "total_score": total_score,
            "wiki_entry": wiki_entry,
            "wiki_written": wiki_written,
        }
    elif review_status == "needs_revision":
        # 加入审查队列
        issues = quality.get("dimensions", {})
        issue_list = []
        for dim, info in issues.items():
            if info.get("score", 5) < 4:
                issue_list.append(f"{dim}: {info.get('reason', '')}")

        append_to_review_queue(
            {
                "priority": "MEDIUM",
                "company": company,
                "doc_type": doc_type,
                "period": period,
                "score": total_score,
                "reason": "质量评分不足，需人工修订",
                "issues": issue_list + financial.get("issues", []),
            }
        )

        return {
            "status": "success",
            "action": "queue",
            "review_status": review_status,
            "total_score": total_score,
        }
    else:
        # rejected，加入审查队列（高优先级）
        append_to_review_queue(
            {
                "priority": "HIGH",
                "company": company,
                "doc_type": doc_type,
                "period": period,
                "score": total_score,
                "reason": "质量评分过低，需人工审核",
                "issues": financial.get("issues", ["质量评分过低"]),
            }
        )

        return {
            "status": "success",
            "action": "queue",
            "review_status": review_status,
            "total_score": total_score,
        }


def main():
    parser = argparse.ArgumentParser(description="阶段5：入库与审查队列")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待入库文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  阶段5：入库与审查队列")
    print("=" * 60)

    # 扫描待入库文件
    review_files = []
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
        for review_file in extracts_dir.rglob("*.review.json"):
            # 检查是否已入库
            ingest_marker = review_file.with_suffix(".ingested")
            if not ingest_marker.exists():
                review_files.append(review_file)

    print(f"找到 {len(review_files)} 个待入库文件")

    if args.check:
        for f in review_files[:20]:
            print(f"  {f.relative_to(WIKI_ROOT)}")
        if len(review_files) > 20:
            print(f"  ... 还有 {len(review_files) - 20} 个")
        return 0

    if not review_files:
        print("没有待入库的文件")
        return 0

    if args.limit > 0:
        review_files = review_files[: args.limit]
        print(f"限制处理 {len(review_files)} 个文件")

    ingested = 0
    queued = 0
    errors = 0

    for i, review_path in enumerate(review_files, 1):
        print(f"\n[{i}/{len(review_files)}] {review_path.relative_to(WIKI_ROOT)}")
        result = ingest_single_file(review_path, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            action = result["action"]
            review_status = result["review_status"]
            total_score = result["total_score"]

            if action == "ingest":
                ingested += 1
                wiki_written = result.get("wiki_written", False)
                print(
                    f"  -> 入库 | {review_status} | score: {total_score} | wiki: {'已更新' if wiki_written else '未更新'}"
                )
                if not args.dry_run:
                    # 标记已入库
                    ingest_marker = review_path.with_suffix(".ingested")
                    ingest_marker.write_text(
                        json.dumps(
                            {
                                "ingested_at": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M"
                                ),
                                "review_status": review_status,
                                "total_score": total_score,
                                "wiki_written": wiki_written,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
            else:
                queued += 1
                print(f"  -> 入队 | {review_status} | score: {total_score}")
                if not args.dry_run:
                    # 标记已处理
                    ingest_marker = review_path.with_suffix(".ingested")
                    ingest_marker.write_text(
                        json.dumps(
                            {
                                "queued_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "review_status": review_status,
                                "total_score": total_score,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | {result['review_status']} | score: {result['total_score']}"
            )
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print(f"完成: {ingested} 入库, {queued} 入队, {errors} 错误")
        print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
