#!/usr/bin/env python3
"""
download_reports.py — 批量下载财报/研报/投资者关系文档
调用 StockInfoDownloader 从巨潮资讯网下载，保存到 wiki 的 companies/ 目录。

用法：
    python3 scripts/download_reports.py                   # 下载所有 A 股公司
    python3 scripts/download_reports.py --company 中微公司  # 只下载指定公司
    python3 scripts/download_reports.py --parallel 2       # 并行下载（2 workers）
    python3 scripts/download_reports.py --pages periodicReports  # 只下载定期报告
"""

import argparse
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

# StockInfoDownloader 路径
DOWNLOADER_DIR = Path(os.path.expanduser("~/StockInfoDownloader"))
WIKI_COMPANIES = WIKI_ROOT / "companies"


def get_a_share_companies(graph):
    """获取所有 A 股公司（可下载财报）"""
    a_share_exchanges = {"SSE STAR", "SSE", "SZSE", "BSE"}
    return [
        c for c in graph.get_all_companies()
        if c["exchange"] in a_share_exchanges
    ]


def run_single(stock_code, company_name, pages_filter=None):
    """下载单个公司的文档"""
    if not DOWNLOADER_DIR.exists():
        print(f"  ERROR: StockInfoDownloader not found at {DOWNLOADER_DIR}")
        return False

    cmd = [sys.executable, str(DOWNLOADER_DIR / "main.py"), stock_code]

    # 用我们的配置
    config_file = WIKI_ROOT / "configs" / "stockinfo_config.json"
    if config_file.exists():
        cmd.extend(["--config", str(config_file)])

    print(f"  Running: python main.py {stock_code}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(DOWNLOADER_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )

        # 检查是否成功（看是否有文件下载）
        dl_dir = DOWNLOADER_DIR / "downloads" / company_name
        if dl_dir.exists():
            pdfs = list(dl_dir.glob("*.pdf"))
            if pdfs:
                # 搬到 wiki 目录
                dst = WIKI_COMPANIES / company_name
                dst.mkdir(parents=True, exist_ok=True)
                copied = 0
                for f in pdfs:
                    dst_file = dst / f.name
                    if not dst_file.exists():
                        shutil.copy2(f, dst_file)
                        copied += 1
                print(f"  Downloaded {len(pdfs)} PDFs, copied {copied} new to wiki")
                return True

        if result.returncode != 0:
            print(f"  Exit code: {result.returncode}")
        return False

    except subprocess.TimeoutExpired:
        print(f"  Timeout (600s)")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


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
    parser = argparse.ArgumentParser(description="批量下载财报/研报/投资者关系")
    parser.add_argument("--company", type=str, help="只下载指定公司")
    parser.add_argument("--pages", type=str, help="只下载指定类型")
    parser.add_argument("--list", action="store_true", help="列出所有 A 股公司")
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

    print("=" * 50)
    print(f"  批量下载 — {len(companies)} 家 A 股公司")
    print("=" * 50)

    success = 0
    failed = 0

    for i, company in enumerate(companies):
        print(f"\n[{i+1}/{len(companies)}] {company['name']} ({company['ticker']})")
        ok = run_single(company["ticker"], company["name"], args.pages)
        if ok:
            success += 1
        else:
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Done. Success: {success}, Failed: {failed}")
    print(f"{'=' * 50}")

    append_log(f"Downloaded reports: {success} success, {failed} failed")

    if success > 0:
        print(f"\n  下一步: python3 scripts/ingest.py")


if __name__ == "__main__":
    main()
