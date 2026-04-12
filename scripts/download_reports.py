#!/usr/bin/env python3
"""
download_reports.py — 批量下载财报/招股说明书/投资者关系文档
调用 StockInfoDownloader 从巨潮资讯网下载，按类型保存到 wiki 的 raw/ 子目录。

下载内容：
  1. 定期报告 → companies/{name}/raw/reports/
  2. 招股说明书 → companies/{name}/raw/reports/
  3. 投资者关系文档 → companies/{name}/raw/research/

用法：
    python3 scripts/download_reports.py                    # 下载所有 A 股公司的全部类型
    python3 scripts/download_reports.py --company 中微公司  # 只下载指定公司
    python3 scripts/download_reports.py --pages periodicReports  # 只下载定期报告
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
LOG_PATH = WIKI_ROOT / "log.md"

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph

DOWNLOADER_DIR = Path(os.path.expanduser("~/StockInfoDownloader"))
WIKI_COMPANIES = WIKI_ROOT / "companies"

# 页面类型 → wiki 子目录 映射
PAGE_TYPE_MAP = {
    "periodicReports": {"name": "定期报告", "wiki_subdir": "raw/reports"},
    "latestAnnouncement": {"name": "招股说明书", "wiki_subdir": "raw/reports"},
    "research": {"name": "投资者关系", "wiki_subdir": "raw/research"},
}

# 所有要下载的页面类型
ALL_PAGE_TYPES = ["periodicReports", "latestAnnouncement", "research"]


def get_a_share_companies(graph):
    a_share = {"SSE STAR", "SSE", "SZSE", "BSE"}
    return [c for c in graph.get_all_companies() if c["exchange"] in a_share]


def build_config_for_page(stock_code, company_name, page_suffix, save_dir):
    """为单个页面类型构建 StockInfoDownloader 配置"""
    page_config = {
        "periodicReports": {
            "name": "定期报告", "suffix": "periodicReports",
            "max_pages": 10,
        },
        "latestAnnouncement": {
            "name": "招股说明书", "suffix": "latestAnnouncement",
            "allowed_keywords": ["招股说明书", "上市招股说明书"],
            "max_pages": 3, "reverse_order": True,
        },
        "research": {
            "name": "投资者关系", "suffix": "research",
            "allowed_keywords": [
                "投资者关系活动记录表",
                "投资者关系管理信息",
                "调研活动",
            ],
            "max_pages": 10,
        },
    }

    return {
        "save_dir": save_dir,
        "headless": True,
        "max_retries": 3,
        "use_dynamic_delay": True,
        "base_url": "https://www.cninfo.com.cn",
        "page_load_strategy": "eager",
        "timeout": {"page_load": 30, "element_wait": 30, "download": 180, "script": 30},
        "selectors": {
            "detail_links": "//a[contains(@href, '/new/disclosure/detail')]",
            "download_button": "//button[contains(., '公告下载')]",
            "next_page_button": "//button[contains(@class, 'el-pagination__next')]",
            "table_element": "//table[contains(@class, 'el-table__body')]",
        },
        "files": {
            "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
            "mapping_file": "stock_orgid_mapping.json",
            "log_dir": "logs",
        },
        "browser": {
            "strategy": "playwright", "headless": True,
            "window_size": {"width": 1920, "height": 1080},
            "timeout": 30, "page_load_timeout": 60, "implicit_wait": 10,
        },
        "anti_crawler": {
            "enabled": True, "base_delay": 1.0,
            "random_delay_range": [0.5, 2.0], "session_limit": 50,
            "max_retries": 3, "retry_backoff_factor": 2.0,
        },
        "download": {
            "max_pages": page_config[page_suffix].get("max_pages", 5),
            "timeout": 180, "download_delay": 0.5,
            "concurrent_downloads": 3, "chunk_size": 8192,
            "file_name_format": "{stock_name}_{date}_{description}.pdf",
            "save_directory": save_dir, "create_subdirs": True,
            "validate_downloads": True, "min_file_size": 1024,
            "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
        },
        "pages": [page_config[page_suffix]],
        "companies": [{
            "stock_code": stock_code,
            "company_name": company_name,
            "enabled": True, "priority": 1,
        }],
    }


def run_download(stock_code, company_name, page_suffix):
    """下载单个公司的单种类型文档"""
    if not DOWNLOADER_DIR.exists():
        print(f"  ERROR: StockInfoDownloader not found at {DOWNLOADER_DIR}")
        return []

    save_dir = str(DOWNLOADER_DIR / "downloads")
    config = build_config_for_page(stock_code, company_name, page_suffix, save_dir)

    # 写临时配置
    config_file = DOWNLOADER_DIR / "config_wiki_temp.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    page_name = PAGE_TYPE_MAP[page_suffix]["name"]
    print(f"  [{page_name}] python main.py {stock_code}")

    try:
        result = subprocess.run(
            [sys.executable, str(DOWNLOADER_DIR / "main.py"), stock_code,
             "--config", str(config_file)],
            cwd=str(DOWNLOADER_DIR),
            capture_output=True, text=True, timeout=600,
        )

        # 收集下载的文件
        dl_dir = DOWNLOADER_DIR / "downloads" / company_name
        downloaded = []
        if dl_dir.exists():
            downloaded = list(dl_dir.glob("*.pdf")) + list(dl_dir.glob("*.doc*"))

        if downloaded:
            print(f"    {len(downloaded)} files downloaded")
        else:
            if result.returncode != 0:
                print(f"    Exit code: {result.returncode}")

        return downloaded

    except subprocess.TimeoutExpired:
        print(f"    Timeout")
        return []
    except Exception as e:
        print(f"    ERROR: {e}")
        return []
    finally:
        if config_file.exists():
            config_file.unlink()


def organize_files(company_name, page_suffix, downloaded_files):
    """将下载的文件归类到 wiki 的 raw/ 子目录"""
    wiki_subdir = PAGE_TYPE_MAP[page_suffix]["wiki_subdir"]
    dst_dir = WIKI_COMPANIES / company_name / wiki_subdir
    dst_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for f in downloaded_files:
        dst = dst_dir / f.name
        if not dst.exists():
            shutil.copy2(f, dst)
            copied += 1

    return copied


def append_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] download_reports | {message}\n"
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="批量下载财报/招股说明书/投资者关系")
    parser.add_argument("--company", type=str, help="只下载指定公司")
    parser.add_argument("--pages", type=str,
                        help="只下载指定类型 (periodicReports/latestAnnouncement/research)")
    parser.add_argument("--list", action="store_true", help="列出 A 股公司")
    args = parser.parse_args()

    graph = Graph()
    companies = get_a_share_companies(graph)

    if args.company:
        companies = [c for c in companies if c["name"] == args.company]
        if not companies:
            print(f"Company '{args.company}' not found or not A-share")
            sys.exit(1)

    if args.list:
        print(f"A 股公司 ({len(companies)} 家):")
        for c in companies:
            print(f"  {c['ticker']} {c['name']} ({c['exchange']})")
        return

    page_types = [args.pages] if args.pages else ALL_PAGE_TYPES

    print("=" * 50)
    print(f"  批量下载 — {len(companies)} 家 A 股公司 × {len(page_types)} 种类型")
    print(f"  类型: {', '.join(PAGE_TYPE_MAP[p]['name'] for p in page_types)}")
    print("=" * 50)

    total_files = 0

    for i, company in enumerate(companies):
        print(f"\n[{i+1}/{len(companies)}] {company['name']} ({company['ticker']})")

        for page_suffix in page_types:
            files = run_download(company["ticker"], company["name"], page_suffix)
            if files:
                copied = organize_files(company["name"], page_suffix, files)
                total_files += copied

    print(f"\n{'=' * 50}")
    print(f"  Done. Total new files saved: {total_files}")
    print(f"{'=' * 50}")

    append_log(f"Downloaded {total_files} report/research files for {len(companies)} companies")

    if total_files > 0:
        print(f"\n  下一步: python3 scripts/ingest.py")


if __name__ == "__main__":
    main()
