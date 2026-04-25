#!/usr/bin/env python3
"""
重试 Phase 2 中 parse_error 的文件。
这些文件未被 mark_ingested，可以直接重新处理。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingest_v2 import process_file, mark_ingested
from graph import Graph
from llm_client import get_llm_client

WIKI_ROOT = Path(__file__).resolve().parent.parent

# Phase 2 中 parse_error 的15个文件
ERROR_FILES = [
    ("companies/北方华创/raw/financial_reports/quarterly/北方华创：2018年第三季度报告正文.pdf", "北方华创", "company"),
    ("companies/北方华创/raw/financial_reports/quarterly/北方华创：2020年第一季度报告正文.pdf", "北方华创", "company"),
    ("companies/寒武纪/raw/financial_reports/quarterly/寒武纪：2025年第一季度报告.pdf", "寒武纪", "company"),
    ("companies/寒武纪/raw/financial_reports/semi_annual/寒武纪：2022年半年度报告.pdf", "寒武纪", "company"),
    ("companies/寒武纪/raw/financial_reports/semi_annual/寒武纪：2023年半年度报告.pdf", "寒武纪", "company"),
    ("companies/中科曙光/raw/financial_reports/quarterly/中科曙光：2019年第三季度报告.pdf", "中科曙光", "company"),
    ("companies/中科曙光/raw/financial_reports/quarterly/中科曙光：2020年第一季度报告.pdf", "中科曙光", "company"),
    ("companies/南大光电/raw/financial_reports/quarterly/南大光电：2014年第一季度报告全文.pdf", "南大光电", "company"),
    ("companies/南大光电/raw/financial_reports/quarterly/南大光电：2020年第一季度报告全文.pdf", "南大光电", "company"),
    ("companies/华特气体/raw/financial_reports/quarterly/华特气体：广东华特气体股份有限公司2023年第三季度报告.pdf", "华特气体", "company"),
    ("companies/东方电缆/raw/financial_reports/quarterly/东方电缆：东方电缆2023年第三季度报告.pdf", "东方电缆", "company"),
    ("companies/东方电缆/raw/financial_reports/quarterly/东方电缆：宁波东方电缆股份有限公司2025年第一季度报告.pdf", "东方电缆", "company"),
    ("companies/东方电缆/raw/financial_reports/semi_annual/东方电缆：2017年半年度报告.pdf", "东方电缆", "company"),
    ("companies/中密控股/raw/financial_reports/quarterly/日机密封：2016年第三季度报告全文.pdf", "中密控股", "company"),
    ("companies/中密控股/raw/financial_reports/quarterly/日机密封：2017年第一季度报告全文.pdf", "中密控股", "company"),
]


def main():
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    graph = Graph(str(WIKI_ROOT / "graph.yaml"))
    llm_client = get_llm_client()
    llm_client.model = "deepseek-v4-flash"
    llm_client._max_tokens = 4096
    llm_client._timeout = 120

    print("=" * 50)
    print("  Phase 2 Parse Error Retry")
    print("=" * 50)

    total_entries = 0
    success = 0
    still_errors = 0

    for i, (rel_path, entity, etype) in enumerate(ERROR_FILES, 1):
        fp = WIKI_ROOT / rel_path
        if not fp.exists():
            print(f"[{i}/15] SKIP | File not found: {fp}")
            still_errors += 1
            continue

        print(f"[{i}/15] {fp.name[:60]}")
        try:
            result = process_file(str(fp), entity, etype, graph, llm_client, dry_run=False)
            status = result["status"]
            if status == "success":
                total_entries += result.get("entries_added", 0)
                success += 1
                print(f"  -> OK | entries:{result.get('entries_added',0)}")
                mark_ingested(str(fp))
            elif status == "skip":
                print(f"  -> SKIP | {result.get('error','')[:50]}")
                still_errors += 1
            else:
                print(f"  -> ERR | {status}: {result.get('error','')[:80]}")
                still_errors += 1
        except Exception as e:
            print(f"  -> EXC | {e}")
            still_errors += 1

    print("=" * 50)
    print(f"Done. Success:{success} Entries:{total_entries} Still errors:{still_errors}")
    print("=" * 50)


if __name__ == "__main__":
    main()
