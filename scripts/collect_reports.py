#!/usr/bin/env python3
"""
collect_reports.py — 财报/公告采集模块
调用 StockInfoDownloader 工具从巨潮资讯网下载财报和公告。

用法：
    python3 scripts/collect_reports.py                        # 采集所有公司
    python3 scripts/collect_reports.py --company 中微公司      # 只采集指定公司
    python3 scripts/collect_reports.py --pages research        # 只下载研报

前提：
    1. 本地已安装 StockInfoDownloader
    2. 在 config.yaml 中配置 report_downloader.tool_path
    3. 已安装 playwright: pip install playwright && playwright install

注意：
    StockInfoDownloader 需要 Playwright/Selenium 浏览器引擎，
    仅支持在本地桌面环境运行（Windows/Mac/Linux with GUI）。
    不适合在无头服务器上运行。
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── 路径 ──────────────────────────────────
WIKI_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"


def load_config():
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_downloader_path(config):
    """获取 StockInfoDownloader 路径"""
    dl_cfg = config.get("report_downloader", {})
    tool_path = dl_cfg.get("tool_path", "~/StockInfoDownloader")
    tool_path = os.path.expanduser(tool_path)

    if not os.path.isdir(tool_path):
        print(f"ERROR: StockInfoDownloader not found at: {tool_path}")
        print(f"  Please clone it or update config.yaml -> report_downloader.tool_path")
        sys.exit(1)

    main_py = os.path.join(tool_path, "main.py")
    if not os.path.isfile(main_py):
        print(f"ERROR: main.py not found in: {tool_path}")
        sys.exit(1)

    return tool_path, main_py


def run_downloader(main_py, stock_code, company_name, save_dir, pages, max_pages, strategy):
    """
    调用 StockInfoDownloader 下载指定公司的报告。
    """
    # StockInfoDownloader 的 config.json 需要动态生成
    import json

    config_data = {
        "stock_code": stock_code,
        "company_name": company_name,
        "save_dir": save_dir,
        "headless": True,
        "max_retries": 3,
        "browser": {
            "strategy": strategy,
            "headless": True,
            "timeout": 30,
        },
        "pages": [
            {
                "name": p["name"],
                "suffix": p["suffix"],
                "max_pages": max_pages,
            }
            for p in pages
        ],
    }

    # 写临时 config
    dl_dir = os.path.dirname(main_py)
    temp_config = os.path.join(dl_dir, "config_wiki_temp.json")
    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    cmd = [
        sys.executable, main_py,
        stock_code,
        "--config", temp_config,
    ]

    print(f"  Running: {' '.join(cmd)}")
    print(f"  Working dir: {dl_dir}")

    try:
        result = subprocess.run(
            cmd,
            cwd=dl_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per company
        )
        if result.returncode != 0:
            print(f"  WARNING: Exit code {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
        else:
            print(f"  Success")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout (300s)")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    finally:
        # 清理临时 config
        if os.path.exists(temp_config):
            os.remove(temp_config)


def copy_downloaded_files(downloader_save_dir, target_raw_dir, company_name):
    """
    将 StockInfoDownloader 下载的文件复制到知识库的 raw/ 目录。
    StockInfoDownloader 的目录结构: save_dir/{company_name}/research/ 和 periodicReports/
    """
    if not os.path.isdir(downloader_save_dir):
        print(f"  Download dir not found: {dl_save_dir}")
        return 0

    # StockInfoDownloader 可能创建以公司名或股票代码命名的子目录
    company_dir = None
    for candidate in [company_name, f"Stock_{company_name}"]:
        path = os.path.join(downloader_save_dir, candidate)
        if os.path.isdir(path):
            company_dir = path
            break

    if company_dir is None:
        # 尝试找第一个子目录
        subdirs = [d for d in os.listdir(downloader_save_dir)
                   if os.path.isdir(os.path.join(downloader_save_dir, d))]
        if subdirs:
            company_dir = os.path.join(downloader_save_dir, subdirs[0])

    if company_dir is None:
        print(f"  No downloaded files found for {company_name}")
        return 0

    # 映射：StockInfoDownloader 目录 → 知识库目录
    dir_mapping = {
        "research": "raw/research",
        "periodicReports": "raw/reports",
        "latestAnnouncement": "raw/reports",
    }

    count = 0
    for src_subdir, dst_subdir in dir_mapping.items():
        src = os.path.join(company_dir, src_subdir)
        dst = os.path.join(target_raw_dir, dst_subdir)

        if not os.path.isdir(src):
            continue

        os.makedirs(dst, exist_ok=True)

        for f in os.listdir(src):
            src_file = os.path.join(src, f)
            dst_file = os.path.join(dst, f)

            if os.path.isfile(src_file) and not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)
                count += 1

    return count


def append_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] collect_reports | {message}\n"
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="采集财报/公告/研报")
    parser.add_argument("--company", type=str, help="只采集指定公司")
    parser.add_argument("--pages", type=str, help="只下载指定类型 (research/periodicReports)")
    args = parser.parse_args()

    print("=" * 50)
    print("  上市公司知识库 — 财报/公告采集")
    print("=" * 50)

    config = load_config()
    dl_cfg = config.get("report_downloader", {})

    tool_path, main_py = get_downloader_path(config)
    save_dir = dl_cfg.get("save_dir", "downloads")
    max_pages = dl_cfg.get("max_pages", 5)
    strategy = dl_cfg.get("browser_strategy", "playwright")
    pages = dl_cfg.get("pages", [])

    if args.pages:
        pages = [p for p in pages if p["suffix"] == args.pages]
        if not pages:
            print(f"ERROR: Page type '{args.pages}' not found in config")
            sys.exit(1)

    companies = config.get("companies", [])
    if args.company:
        companies = [c for c in companies if c["name"] == args.company]
        if not companies:
            print(f"ERROR: Company '{args.company}' not found in config")
            sys.exit(1)

    total_copied = 0

    for company in companies:
        name = company["name"]
        ticker = company["ticker"]
        print(f"\n[{name}] ({ticker})")

        # 1. 运行 StockInfoDownloader
        dl_save = os.path.join(tool_path, save_dir)
        success = run_downloader(main_py, ticker, name, dl_save, pages, max_pages, strategy)

        if not success:
            print(f"  Download may have failed, checking for partial results...")

        # 2. 复制文件到知识库
        target_dir = WIKI_ROOT / "companies" / name
        if os.path.isdir(dl_save):
            count = copy_downloaded_files(dl_save, str(target_dir), name)
            print(f"  Copied {count} new files to raw/")
            total_copied += count

    print(f"\n{'=' * 50}")
    print(f"  Done. Total new files: {total_copied}")
    print(f"{'=' * 50}")

    if total_copied > 0:
        append_log(f"Collected {total_copied} report/research files")
        print(f"\n  Run ingest.py to process the new files:")
        print(f"    python3 scripts/ingest.py")


if __name__ == "__main__":
    main()
