#!/usr/bin/env python3
"""
stage1_extract.py — 阶段1 Pipeline：PDF 提取与验证

将 companies/{name}/raw/ 下的 PDF 提取为 Markdown，
保存到 companies/{name}/extracts/，并运行检查点1验证。

用法：
    python scripts/stage1_extract.py                    # 处理所有公司
    python scripts/stage1_extract.py --company 北方华创  # 只处理指定公司
    python scripts/stage1_extract.py --check             # 列出待处理文件
    python scripts/stage1_extract.py --dry-run           # 预览
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT
from pdf_extract_v3 import classify_pdf_v2, extract_pdf_text_v3, validate_extraction
from graph import Graph
from section_discovery import discover_sections


def get_stage1_db_path() -> Path:
    return WIKI_ROOT / ".stage1_db.json"


def load_stage1_db() -> dict:
    db_path = get_stage1_db_path()
    if db_path.exists():
        try:
            return json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_stage1_db(db: dict):
    get_stage1_db_path().write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def file_hash(file_path: Path) -> str:
    """基于文件内容和大小的简单哈希"""
    stat = file_path.stat()
    return hashlib.md5(
        f"{file_path.name}:{stat.st_size}:{stat.st_mtime}".encode()
    ).hexdigest()


def scan_pdf_files(company_filter=None):
    """扫描所有待提取的 PDF 文件"""
    graph = Graph()
    companies = graph.get_all_companies()
    if company_filter:
        companies = [c for c in companies if c["name"] == company_filter]

    pdf_files = []
    for company in companies:
        name = company["name"]
        raw_dir = WIKI_ROOT / "companies" / name / "raw"
        if not raw_dir.exists():
            continue
        for pdf_path in sorted(raw_dir.rglob("*.pdf")):
            # 跳过摘要
            filename = pdf_path.name
            if "摘要" in filename:
                continue
            pdf_files.append((name, pdf_path))

    return pdf_files


def process_single_pdf(company_name: str, pdf_path: Path, dry_run=False) -> dict:
    """处理单个 PDF 文件"""
    filename = pdf_path.name

    # 步骤1：分类
    classify_result = classify_pdf_v2(filename, str(pdf_path))
    doc_type = classify_result["doc_type"]

    # 如果是摘要或 unknown，跳过
    if classify_result.get("skip", False):
        return {"status": "skip", "reason": "abstract", "doc_type": doc_type}

    if doc_type == "unknown":
        return {"status": "skip", "reason": "unknown_type", "doc_type": doc_type}

    # 步骤2：提取文本
    extract_result = extract_pdf_text_v3(str(pdf_path))

    if extract_result["error"]:
        return {
            "status": "error",
            "error": extract_result["error"],
            "doc_type": doc_type,
        }

    # 步骤3：检查点1验证
    validation = validate_extraction(extract_result, doc_type)

    if dry_run:
        return {
            "status": "dry_run",
            "doc_type": doc_type,
            "classify": classify_result,
            "extract": {
                "chars": extract_result["total_chars"],
                "pages": extract_result["pages_read"],
                "quality": extract_result["quality_score"],
            },
            "validation": validation,
        }

    # 步骤4：发现章节结构
    sections = discover_sections(extract_result["text"])

    # 步骤5：确定输出路径
    relative = pdf_path.relative_to(WIKI_ROOT / "companies" / company_name / "raw")
    extract_path = WIKI_ROOT / "companies" / company_name / "extracts" / relative
    extract_path = extract_path.with_suffix(".md")

    # 步骤6：写入文件
    extract_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建sections YAML
    sections_yaml = ""
    if sections:
        sections_yaml = "sections:\n"
        for sec in sections:
            sections_yaml += f'  - number: "{sec["number"]}"\n'
            sections_yaml += f'    title: "{sec["title"]}"\n'
            sections_yaml += f"    position: {sec['position']}\n"

    frontmatter = f"""---
source_pdf: "{relative.as_posix()}"
company: "{company_name}"
doc_type: "{doc_type}"
period: "{classify_result.get("period", "")}"
confidence: {classify_result.get("confidence", 0.0)}
method: "{classify_result.get("method", "")}"
needs_review: {str(classify_result.get("needs_review", False)).lower()}
pages: {extract_result["pages_read"]}
total_chars: {extract_result["total_chars"]}
quality_score: {extract_result["quality_score"]:.3f}
validation_status: "{validation["status"]}"
{sections_yaml}extracted_at: "{datetime.now().strftime("%Y-%m-%d %H:%M")}"
---

"""

    extract_path.write_text(frontmatter + extract_result["text"], encoding="utf-8")

    return {
        "status": "success",
        "doc_type": doc_type,
        "extract_path": str(extract_path),
        "chars": extract_result["total_chars"],
        "pages": extract_result["pages_read"],
        "quality": extract_result["quality_score"],
        "validation": validation,
        "classify": classify_result,
    }


def main():
    parser = argparse.ArgumentParser(description="阶段1：PDF 提取与验证")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  阶段1：PDF 提取与验证")
    print("=" * 60)

    pdf_files = scan_pdf_files(args.company)
    db = load_stage1_db()

    # 过滤已处理的文件
    pending = []
    for company_name, pdf_path in pdf_files:
        fh = file_hash(pdf_path)
        key = f"{company_name}/{pdf_path.name}"
        if db.get(key) != fh:
            pending.append((company_name, pdf_path, fh))

    print(f"找到 {len(pdf_files)} 个 PDF，待处理 {len(pending)} 个")

    if args.check:
        for company_name, pdf_path, _ in pending[:20]:
            print(f"  [{company_name}] {pdf_path.name}")
        if len(pending) > 20:
            print(f"  ... 还有 {len(pending) - 20} 个")
        return 0 if not pending else 1

    if not pending:
        print("没有待处理的 PDF")
        return 0

    if args.limit > 0:
        pending = pending[: args.limit]
        print(f"限制处理 {len(pending)} 个文件")

    success = 0
    skipped = 0
    errors = 0
    needs_review = 0

    for i, (company_name, pdf_path, fh) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {company_name}/{pdf_path.name}")
        result = process_single_pdf(company_name, pdf_path, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            success += 1
            validation = result.get("validation", {})
            print(
                f"  -> OK | {result['chars']} chars, {result['pages']} pages, "
                f"type={result['doc_type']}, quality={result['quality']:.2f}"
            )
            if validation.get("status") == "needs_review":
                needs_review += 1
                print(f"       WARNING: {validation.get('review_reason', '')}")
            if not args.dry_run:
                key = f"{company_name}/{pdf_path.name}"
                db[key] = fh
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | {result['extract']['chars']} chars, "
                f"type={result['doc_type']}"
            )
            validation = result.get("validation", {})
            if validation.get("status") != "passed":
                print(
                    f"       Validation: {validation.get('status')} - "
                    f"{validation.get('review_reason', '')}"
                )
        elif status == "skip":
            skipped += 1
            print(
                f"  -> SKIP | {result.get('reason', '')} ({result.get('doc_type', '')})"
            )
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        save_stage1_db(db)

    print(f"\n{'=' * 60}")
    print(f"完成: {success} 成功, {skipped} 跳过, {errors} 错误, {needs_review} 待审核")
    print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
