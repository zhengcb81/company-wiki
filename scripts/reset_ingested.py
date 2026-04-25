#!/usr/bin/env python3
"""
reset_ingested.py — 清除公司的 ingested 标记，让 v2 重新处理

用法:
    python scripts/reset_ingested.py --company 中微公司      # 清除指定公司
    python scripts/reset_ingested.py --company 中微公司 --dry-run  # 只查看不删除
    python scripts/reset_ingested.py --all                    # 清除所有（谨慎）
"""

import argparse
import hashlib
import sys
from pathlib import Path

# Windows 控制台 UTF-8 编码修复
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
INGESTED_DIR = WIKI_ROOT / ".ingested"


def get_company_files(company_name: str):
    """获取公司目录下的所有非wiki文件"""
    company_dir = WIKI_ROOT / "companies" / company_name
    if not company_dir.exists():
        return []
    files = []
    for f in company_dir.rglob("*"):
        if f.is_file() and "wiki" not in str(f):
            files.append(f)
    return files


def reset_company(company_name: str, dry_run: bool = False):
    """清除指定公司的 ingested 标记"""
    files = get_company_files(company_name)
    if not files:
        print(f"  未找到公司 '{company_name}' 的文件")
        return 0

    removed = 0
    not_marked = 0

    for f in files:
        file_hash = hashlib.md5(f.read_bytes()).hexdigest()
        marker = INGESTED_DIR / f"{file_hash}.hash"
        if marker.exists():
            if not dry_run:
                marker.unlink()
            removed += 1
        else:
            not_marked += 1

    action = "将清除" if dry_run else "已清除"
    print(f"  {action} {company_name}: {removed} 个标记 ({not_marked} 个原本未标记)")
    return removed


def main():
    parser = argparse.ArgumentParser(description="清除 ingested 标记")
    parser.add_argument("--company", type=str, help="指定公司名")
    parser.add_argument("--all", action="store_true", help="清除所有公司标记（谨慎）")
    parser.add_argument("--dry-run", action="store_true", help="只查看不删除")
    args = parser.parse_args()

    if not INGESTED_DIR.exists():
        print("ERROR: .ingested 目录不存在")
        sys.exit(1)

    if args.all:
        print("WARNING: --all 将清除所有公司的 ingested 标记")
        if not args.dry_run:
            confirm = input("确认删除所有标记? (yes/no): ")
            if confirm.lower() != "yes":
                print("已取消")
                return
        # 遍历所有公司
        companies_dir = WIKI_ROOT / "companies"
        total = 0
        for d in sorted(companies_dir.glob("*")):
            if d.is_dir():
                total += reset_company(d.name, args.dry_run)
        print(f"\n总计: {total} 个标记{'将' if args.dry_run else '已'}清除")

    elif args.company:
        reset_company(args.company, args.dry_run)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
