#!/usr/bin/env python3
"""
批量 Ingest v2 — 高效处理一家公司的全部历史文件。
避免重复初始化 graph 和 llm_client。
"""

import sys
import re
import argparse
import hashlib
from pathlib import Path

from common import SCRIPTS_DIR

from ingest_v2 import (
    process_file,
    get_ingested_set,
    is_ingested,
    mark_ingested,
    WIKI_ROOT,
)
from graph import Graph
from llm_client import get_llm_client


def is_high_value(file_path: str) -> bool:
    """判断是否为高价值文件（年报/半年报/季报/IR/重大事件）"""
    n = Path(file_path).name
    # 年报/半年报/季报
    if re.search(r"\d{4}年?度?年报(?!摘要|审计|内部控制|鉴证|专项)", n):
        return True
    if re.search(r"\d{4}年?度?年度报告(?!摘要|审计|内部控制|鉴证|专项)", n):
        return True
    if re.search(r"\d{4}年?半年度?报告(?!摘要)", n) or re.search(
        r"\d{4}年?半年报(?!摘要)", n
    ):
        return True
    if re.search(r"\d{4}年第[一二三四1234]季度报告", n):
        return True
    # IR
    if "投资者关系" in n or "调研" in n or "接待" in n:
        return True
    # 重大事件
    if any(
        k in n
        for k in ["并购", "收购", "定增", "增发", "股权激励", "重大资产重组", "预案"]
    ):
        return True
    return False


def scan_company_files(
    company_name, ingested_set=None, skip_ingested=True, high_value_only=False
):
    """扫描某公司的所有待处理文件"""
    company_dir = WIKI_ROOT / "companies" / company_name
    if not company_dir.exists():
        return []
    pending = []
    seen_hashes = set()
    seen_norm_names = set()  # Q2 fix: 文件名规范化去重
    # 公司扫描时跳过明显属于行业层面的文件（防污染）
    _sector_patterns = ["行业分析", "行业研究", "行业报告"]
    # 同一报告的不同后缀变体视为重复（"全文"/"正文"/"修订版"等）
    _dup_suffixes = (
        "全文",
        "正文",
        "修订版",
        "更新版",
        "最终版",
        "（修订版）",
        "(修订版)",
    )
    for f in sorted(company_dir.rglob("*")):
        if not f.is_file():
            continue
        fp_str = str(f)
        if "/wiki/" in fp_str or "\\wiki\\" in fp_str:
            continue
        if any(p in f.name for p in _sector_patterns):
            continue
        if high_value_only and not is_high_value(fp_str):
            continue
        # Q2 fix: 文件名规范化去重 — 剥除 末尾"全文"/"正文"等次要后缀变体
        # 例："2017年第三季度报告全文" 与 "2017年第三季度报告正文" 都归一为
        #     "2017年第三季度报告"，只保留排序后最先出现的那份
        stem_norm = f.stem
        for suf in _dup_suffixes:
            if stem_norm.endswith(suf):
                stem_norm = stem_norm[: -len(suf)]
                break
        if stem_norm in seen_norm_names:
            continue
        seen_norm_names.add(stem_norm)
        # 去重（流式哈希，避免大文件全部读入内存）
        md5 = hashlib.md5()
        try:
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(8192), b""):
                    md5.update(chunk)
        except (FileNotFoundError, PermissionError, OSError):
            continue
        h = md5.hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        if skip_ingested and ingested_set and is_ingested(fp_str, ingested_set):
            continue
        pending.append((fp_str, company_name, "company"))
    return pending


def main():
    parser = argparse.ArgumentParser(description="批量 Ingest v2")
    parser.add_argument("--company", type=str, required=True)
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个")
    parser.add_argument("--reset", action="store_true", help="忽略已处理标记")
    parser.add_argument(
        "--high-value-only", action="store_true", help="只处理高价值文件"
    )
    args = parser.parse_args()

    graph = Graph(str(WIKI_ROOT / "graph.yaml"))
    llm_client = get_llm_client()
    llm_client.model = "deepseek-v4-flash"
    llm_client._max_tokens = 4096
    llm_client._timeout = 120

    ingested = get_ingested_set() if not args.reset else set()
    pending = scan_company_files(
        args.company,
        ingested,
        skip_ingested=not args.reset,
        high_value_only=args.high_value_only,
    )

    if args.limit > 0:
        pending = pending[: args.limit]

    print(f"Company: {args.company}")
    print(f"Files to process: {len(pending)}")
    print("-" * 50)

    total_entries = 0
    total_assessments = 0
    skipped = 0
    errors = 0

    for i, (fp, ent, etype) in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {Path(fp).name[:60]}")
        try:
            result = process_file(fp, ent, etype, graph, llm_client, dry_run=False)
            status = result["status"]
            if status == "success":
                total_entries += result.get("entries_added", 0)
                if result.get("assessment_updated"):
                    total_assessments += 1
                print(
                    f"  -> OK | entries:{result.get('entries_added', 0)} assess:{result.get('assessment_updated', False)}"
                )
                mark_ingested(fp)
            elif status == "skip":
                skipped += 1
                print(f"  -> SKIP | {result.get('error', '')[:50]}")
            else:
                errors += 1
                print(f"  -> ERR | {status}: {result.get('error', '')[:80]}")
        except Exception as e:
            errors += 1
            print(f"  -> EXC | {e}")
            import traceback

            traceback.print_exc()

    print("-" * 50)
    print(
        f"Done. Entries:{total_entries} Assessments:{total_assessments} Skip:{skipped} Err:{errors}"
    )


if __name__ == "__main__":
    main()
