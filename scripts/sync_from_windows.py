#!/usr/bin/env python3
"""
sync_from_windows.py — 从 Windows 同步下载的文件
将 StockInfoDownloader/downloads 中的文件同步到 company-wiki

用法：
    python3 scripts/sync_from_windows.py                    # 同步所有文件
    python3 scripts/sync_from_windows.py --check            # 只检查不复制
    python3 scripts/sync_from_windows.py --company 中微公司  # 只同步指定公司
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# Windows 下载目录
WINDOWS_DOWNLOADS = Path("/mnt/c/Users/郑曾波/Projects/StockInfoDownloader/downloads")

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


def scan_windows_downloads() -> Dict[str, List[Path]]:
    """
    扫描 Windows 下载目录
    
    Returns:
        {公司名: [文件路径列表]}
    """
    if not WINDOWS_DOWNLOADS.exists():
        print(f"ERROR: Windows 下载目录不存在: {WINDOWS_DOWNLOADS}")
        return {}
    
    files_by_company = defaultdict(list)
    
    # 扫描所有 PDF 文件
    for pdf_file in WINDOWS_DOWNLOADS.rglob("*.pdf"):
        # 从路径推断公司名
        parts = pdf_file.parts
        
        # 查找公司名（通常是目录名）
        for i, part in enumerate(parts):
            if part == "downloads" and i + 1 < len(parts):
                company_name = parts[i + 1]
                # 清理公司名（移除股票代码前缀）
                if "_" in company_name:
                    company_name = company_name.split("_", 1)[1]
                files_by_company[company_name].append(pdf_file)
                break
    
    return dict(files_by_company)


def classify_file(file_path: Path) -> str:
    """
    分类文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        目标子目录
    """
    filename = file_path.name.lower()
    
    # 年报
    if "年年度报告" in filename or "年年报" in filename:
        return "financial_reports/annual"
    
    # 半年报
    if "半年度报告" in filename or "半年报" in filename:
        return "financial_reports/semi_annual"
    
    # 季报
    if "季度报告" in filename or "季报" in filename:
        return "financial_reports/quarterly"
    
    # 招股说明书
    if "招股说明书" in filename or "招股意向书" in filename:
        return "prospectus"
    
    # 投资者关系
    if "投资者关系" in filename or "投资者交流" in filename:
        return "investor_relations"
    
    # 公告
    if "公告" in filename or "决议" in filename or "通知" in filename:
        return "announcements"
    
    # 默认为研报
    return "research"


def sync_company_files(company_name: str, files: List[Path], dry_run: bool = False) -> Dict[str, Any]:
    """
    同步公司的文件
    
    Args:
        company_name: 公司名称
        files: 文件列表
        dry_run: 只检查不复制
        
    Returns:
        同步结果统计
    """
    stats = {
        "total": len(files),
        "copied": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    # 目标目录
    target_dir = WIKI_ROOT / "companies" / company_name / "raw"
    
    if not target_dir.exists():
        if dry_run:
            print(f"  [DRY] 将创建目录: {target_dir.relative_to(WIKI_ROOT)}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
    
    for file_path in files:
        # 分类文件
        subdir = classify_file(file_path)
        target_subdir = target_dir / subdir
        
        # 确保目标目录存在
        if not dry_run:
            target_subdir.mkdir(parents=True, exist_ok=True)
        
        # 目标文件路径
        target_file = target_subdir / file_path.name
        
        # 检查是否已存在
        if target_file.exists():
            stats["skipped"] += 1
            continue
        
        if dry_run:
            print(f"  [DRY] 将复制: {file_path.name} -> {subdir}/")
            stats["copied"] += 1
        else:
            try:
                shutil.copy2(file_path, target_file)
                print(f"  COPY: {file_path.name} -> {subdir}/")
                stats["copied"] += 1
            except Exception as e:
                print(f"  ERROR: {file_path.name} - {e}")
                stats["errors"] += 1
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="从 Windows 同步文件")
    parser.add_argument("--check", action="store_true", help="只检查不复制")
    parser.add_argument("--company", type=str, help="只同步指定公司")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  从 Windows 同步下载文件")
    print("=" * 60)
    
    # 检查 Windows 目录
    if not WINDOWS_DOWNLOADS.exists():
        print(f"\nERROR: Windows 下载目录不存在: {WINDOWS_DOWNLOADS}")
        print("请确保 WSL 可以访问 Windows 文件系统")
        sys.exit(1)
    
    # 扫描文件
    print(f"\n扫描 Windows 下载目录: {WINDOWS_DOWNLOADS}")
    files_by_company = scan_windows_downloads()
    
    if not files_by_company:
        print("未找到任何文件")
        return
    
    print(f"找到 {len(files_by_company)} 家公司的文件")
    
    # 过滤指定公司
    if args.company:
        if args.company in files_by_company:
            files_by_company = {args.company: files_by_company[args.company]}
        else:
            print(f"\nERROR: 公司 '{args.company}' 未找到")
            print(f"可用公司: {', '.join(sorted(files_by_company.keys())[:10])}...")
            sys.exit(1)
    
    # 统计总文件数
    total_files = sum(len(files) for files in files_by_company.values())
    print(f"总计: {total_files} 个 PDF 文件\n")
    
    # 同步文件
    total_stats = {
        "companies": 0,
        "total": 0,
        "copied": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    for company_name, files in sorted(files_by_company.items()):
        print(f"[{company_name}] ({len(files)} 个文件)")
        
        stats = sync_company_files(company_name, files, dry_run=args.check)
        
        total_stats["companies"] += 1
        total_stats["total"] += stats["total"]
        total_stats["copied"] += stats["copied"]
        total_stats["skipped"] += stats["skipped"]
        total_stats["errors"] += stats["errors"]
        
        if stats["copied"] > 0 or stats["errors"] > 0:
            print(f"  复制: {stats['copied']}, 跳过: {stats['skipped']}, 错误: {stats['errors']}")
        print()
    
    # 总结
    print("=" * 60)
    print("  同步完成")
    print("=" * 60)
    print(f"处理公司: {total_stats['companies']}")
    print(f"总文件数: {total_stats['total']}")
    print(f"已复制: {total_stats['copied']}")
    print(f"已跳过: {total_stats['skipped']}")
    print(f"错误: {total_stats['errors']}")


if __name__ == "__main__":
    main()