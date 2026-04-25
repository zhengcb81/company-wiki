#!/usr/bin/env python3
"""
build_extracts.py — Layer 2: PDF → 完整 Markdown

将 companies/{name}/raw/ 下的所有 PDF 提取为完整 Markdown 文本，
保存到 companies/{name}/extracts/，保留原始目录结构。

用法：
    python3 scripts/build_extracts.py                    # 处理所有公司
    python3 scripts/build_extracts.py --company 北方华创  # 只处理指定公司
    python3 scripts/build_extracts.py --check             # 列出待处理文件
    python3 scripts/build_extracts.py --dry-run           # 预览
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

# 公共基础设施（路径、环境、配置）
from common import WIKI_ROOT

from pdf_extract_v2 import extract_pdf_text, classify_pdf
from graph import Graph


def get_extracts_db_path() -> Path:
    return WIKI_ROOT / ".extracts_db.json"


def load_extracts_db() -> dict:
    db_path = get_extracts_db_path()
    if db_path.exists():
        try:
            return json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_extracts_db(db: dict):
    get_extracts_db_path().write_text(
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
            pdf_files.append((name, pdf_path))

    return pdf_files


def build_extract(company_name: str, pdf_path: Path, dry_run=False) -> dict:
    """提取单个 PDF 为 Markdown"""
    result = extract_pdf_text(str(pdf_path))

    if result["error"]:
        return {"status": "error", "error": result["error"]}
    if result["is_scanned"]:
        return {"status": "skip", "error": "扫描版PDF，无法提取文本"}
    if result["total_chars"] < 100:
        return {"status": "skip", "error": "内容过短"}

    # 确定输出路径
    relative = pdf_path.relative_to(WIKI_ROOT / "companies" / company_name / "raw")
    extract_path = WIKI_ROOT / "companies" / company_name / "extracts" / relative
    extract_path = extract_path.with_suffix(".md")

    doc_type = classify_pdf(pdf_path.name)

    if dry_run:
        return {
            "status": "dry_run",
            "extract_path": str(extract_path),
            "chars": result["total_chars"],
            "pages": result["pages_read"],
        }

    # 创建目录
    extract_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建 frontmatter
    frontmatter = f"""---
source_pdf: "{relative.as_posix()}"
company: "{company_name}"
doc_type: "{doc_type}"
pages: {result["pages_read"]}
total_chars: {result["total_chars"]}
extracted_at: "{datetime.now().strftime("%Y-%m-%d %H:%M")}"
---

"""

    # 写入文件
    extract_path.write_text(frontmatter + result["text"], encoding="utf-8")

    return {
        "status": "success",
        "extract_path": str(extract_path),
        "chars": result["total_chars"],
        "pages": result["pages_read"],
    }


def main():
    parser = argparse.ArgumentParser(description="PDF → 完整 Markdown 提取")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    pdf_files = scan_pdf_files(args.company)
    db = load_extracts_db()

    # 过滤已处理的文件
    pending = []
    for company_name, pdf_path in pdf_files:
        fh = file_hash(pdf_path)
        key = f"{company_name}/{pdf_path.name}"
        if db.get(key) != fh:
            pending.append((company_name, pdf_path, fh))

    print(f"找到 {len(pdf_files)} 个 PDF，待处理 {len(pending)} 个")

    if args.check:
        for company_name, pdf_path, _ in pending:
            print(f"  [{company_name}] {pdf_path.name}")
        return 0 if not pending else 1

    if not pending:
        print("没有待处理的 PDF")
        return 0

    success = 0
    skipped = 0
    errors = 0

    for i, (company_name, pdf_path, fh) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {company_name}/{pdf_path.name}")
        result = build_extract(company_name, pdf_path, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            success += 1
            print(f"  -> OK | {result['chars']} chars, {result['pages']} pages")
            if not args.dry_run:
                key = f"{company_name}/{pdf_path.name}"
                db[key] = fh
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | {result['chars']} chars, {result['pages']} pages -> {result['extract_path']}"
            )
        elif status == "skip":
            skipped += 1
            print(f"  -> SKIP | {result.get('error', '')}")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        save_extracts_db(db)

    print(f"\n完成: {success} 成功, {skipped} 跳过, {errors} 错误")
    return 0


if __name__ == "__main__":
    sys.exit(main())
