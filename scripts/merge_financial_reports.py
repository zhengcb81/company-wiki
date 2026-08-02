#!/usr/bin/env python3
"""
merge_financial_reports.py — 合并旧版子目录到根目录

将 companies/{name}/raw/financial_reports/ 下的：
  - annual/      → 根目录
  - quarterly/   → 根目录
  - semi_annual/ → 根目录

移动后删除空子目录。
"""

import shutil
from pathlib import Path


def merge_financial_reports(wiki_root="."):
    """遍历所有公司，合并 financial_reports 子目录到根目录。"""
    wiki_root = Path(wiki_root)
    companies_dir = wiki_root / "companies"

    if not companies_dir.exists():
        print(f"ERROR: {companies_dir} not found")
        return

    merged_count = 0
    skipped_count = 0
    error_count = 0

    for company_dir in companies_dir.iterdir():
        if not company_dir.is_dir():
            continue

        fin_dir = company_dir / "raw" / "financial_reports"
        if not fin_dir.exists():
            continue

        subdirs = ["annual", "quarterly", "semi_annual"]
        for subdir_name in subdirs:
            subdir = fin_dir / subdir_name
            if not subdir.exists():
                continue

            for pdf_file in subdir.iterdir():
                if not pdf_file.is_file():
                    continue

                dest = fin_dir / pdf_file.name

                if dest.exists():
                    # 文件已存在于根目录，跳过
                    print(
                        f"  SKIP: {company_dir.name}/{subdir_name}/{pdf_file.name} (already exists in root)"
                    )
                    skipped_count += 1
                    continue

                try:
                    shutil.move(str(pdf_file), str(dest))
                    print(
                        f"  MOVE: {company_dir.name}/{subdir_name}/{pdf_file.name} → root/"
                    )
                    merged_count += 1
                except Exception as e:
                    print(
                        f"  ERROR: {company_dir.name}/{subdir_name}/{pdf_file.name}: {e}"
                    )
                    error_count += 1

            # 删除空子目录
            if subdir.exists():
                try:
                    subdir.rmdir()
                    print(f"  RMDIR: {company_dir.name}/{subdir_name}/")
                except OSError:
                    # 目录不为空（可能还有其他文件类型）
                    print(
                        f"  RMDIR-SKIP: {company_dir.name}/{subdir_name}/ (not empty)"
                    )

    print(f"\n{'=' * 50}")
    print("  合并完成:")
    print(f"    移动文件: {merged_count}")
    print(f"    跳过重复: {skipped_count}")
    print(f"    错误: {error_count}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    merge_financial_reports()
