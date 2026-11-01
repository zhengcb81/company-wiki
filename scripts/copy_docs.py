"""
Copy PDF/DOC/XLS files from Dropbox/Stock to company-wiki/companies,
categorizing each file into the correct subdirectory based on filename keywords.

Usage:
    python scripts/copy_docs.py [--dry-run]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

SOURCE_ROOT = Path(r"C:\Users\郑曾波\Dropbox\Stock")
WIKI_COMPANIES = Path(r"C:\Users\郑曾波\Projects\company-wiki\companies")

FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".mht"}


def categorize(filename: str) -> str:
    """Return target subdirectory under raw/ based on filename keywords."""
    if "摘要" in filename:
        return "research"

    if "年度报告" in filename or "季度报告" in filename:
        return "financial_reports"

    if "招股说明书" in filename:
        return "prospectus"

    return "research"


def build_company_set(wiki_companies: Path) -> set[str]:
    """Build set of company directory names from wiki."""
    if not wiki_companies.exists():
        print(f"Error: wiki companies dir not found: {wiki_companies}", file=sys.stderr)
        sys.exit(1)
    return {d.name for d in wiki_companies.iterdir() if d.is_dir() and not d.name.startswith("_")}


def copy_docs(dry_run: bool = False) -> None:
    company_names = build_company_set(WIKI_COMPANIES)

    stats = {"copied": 0, "skipped_exists": 0, "skipped_ext": 0, "total_files": 0}
    matched_companies: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(SOURCE_ROOT):
        dir_name = os.path.basename(dirpath)

        if dir_name not in company_names:
            continue

        matched_companies.add(dir_name)

        for filename in filenames:
            stats["total_files"] += 1

            ext = os.path.splitext(filename)[1].lower()
            if ext not in FILE_EXTENSIONS:
                stats["skipped_ext"] += 1
                continue

            category = categorize(filename)
            source_file = Path(dirpath) / filename
            target_dir = WIKI_COMPANIES / dir_name / "raw" / category
            target_file = target_dir / filename

            if target_file.exists():
                stats["skipped_exists"] += 1
                continue

            if dry_run:
                print(f"  [DRY] {source_file.relative_to(SOURCE_ROOT)} -> {target_file.relative_to(WIKI_COMPANIES)}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                print(f"  Copied: {source_file.relative_to(SOURCE_ROOT)} -> {target_file.relative_to(WIKI_COMPANIES)}")

            stats["copied"] += 1

    # Summary
    print("\n--- Summary ---")
    print(f"Wiki companies: {len(company_names)}")
    print(f"Matched source dirs: {len(matched_companies)}")
    print(f"Total files scanned: {stats['total_files']}")
    print(f"{'Would copy' if dry_run else 'Copied'}: {stats['copied']}")
    print(f"Skipped (already exists): {stats['skipped_exists']}")
    print(f"Skipped (unsupported ext): {stats['skipped_ext']}")

    if dry_run:
        print("\n(Dry run — no files were actually copied)")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Copy docs from Dropbox/Stock to company-wiki")
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying")
    args = parser.parse_args()

    if not SOURCE_ROOT.exists():
        print(f"Error: source dir not found: {SOURCE_ROOT}", file=sys.stderr)
        sys.exit(1)

    copy_docs(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
