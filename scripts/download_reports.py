#!/usr/bin/env python3
"""
download_reports.py — 批量下载财报/招股说明书/投资者关系文档
调用 StockInfoDownloader 从巨潮资讯网下载，按类型保存到 wiki 的 raw/ 子目录。

用法：
    python3 scripts/download_reports.py                    # 下载所有 A 股公司的全部类型
    python3 scripts/download_reports.py --company 中微公司  # 只下载指定公司
    python3 scripts/download_reports.py --pages research    # 只下载投资者关系
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

def load_page_types():
    """从 config.yaml 读取页面类型配置"""
    import yaml
    cfg_path = WIKI_ROOT / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    types = {}
    for page in cfg.get("report_downloader", {}).get("pages", []):
        suffix = page["suffix"]
        # 确定 wiki 子目录
        if suffix == "research":
            wiki_subdir = "raw/research"
        else:
            wiki_subdir = "raw/reports"

        types[suffix] = {
            "name": page["name"],
            "wiki_subdir": wiki_subdir,
            "keywords": page.get("allowed_keywords"),
            "max_pages": page.get("max_pages", 3),
            "reverse": page.get("reverse_order", False),
        }
    return types


PAGE_TYPES = load_page_types()


def get_a_share_companies(graph):
    a_share = {"SSE STAR", "SSE", "SZSE", "BSE"}
    return [c for c in graph.get_all_companies() if c["exchange"] in a_share]


def run_download(stock_code, company_name, page_suffix):
    """运行 StockInfoDownloader 下载一种类型"""
    pt = PAGE_TYPES[page_suffix]

    # 构建配置（写入默认 config.json）
    page_config = {
        "name": pt["name"],
        "suffix": page_suffix,
        "max_pages": pt["max_pages"],
    }
    if pt["keywords"]:
        page_config["allowed_keywords"] = pt["keywords"]
    if pt.get("reverse_order"):
        page_config["reverse_order"] = True

    # 读取现有 config.json，只修改 pages 部分
    config_path = DOWNLOADER_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["pages"] = [page_config]
    config["companies"] = [{
        "stock_code": stock_code,
        "company_name": company_name,
        "enabled": True, "priority": 1,
    }]
    config["save_dir"] = str(DOWNLOADER_DIR / "downloads")
    config["download"]["save_directory"] = config["save_dir"]
    config["download"]["max_pages"] = pt["max_pages"]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 清理下载目录（避免"File already exists"跳过）
    dl_dir = DOWNLOADER_DIR / "downloads" / company_name
    if dl_dir.exists():
        shutil.rmtree(dl_dir)

    print(f"  [{pt['name']}] downloading...")

    try:
        result = subprocess.run(
            [sys.executable, str(DOWNLOADER_DIR / "main.py"), stock_code],
            cwd=str(DOWNLOADER_DIR),
            capture_output=True, text=True, timeout=600,
        )

        # 收集文件
        if dl_dir.exists():
            files = list(dl_dir.glob("*.pdf")) + list(dl_dir.glob("*.doc*"))
            if files:
                print(f"    {len(files)} files downloaded")
                return files

        if result.returncode != 0:
            print(f"    Exit code: {result.returncode}")
        return []

    except subprocess.TimeoutExpired:
        print(f"    Timeout")
        return []
    except Exception as e:
        print(f"    ERROR: {e}")
        return []


def organize_files(company_name, page_suffix, files):
    """归类到 wiki 的 raw/ 子目录"""
    wiki_subdir = PAGE_TYPES[page_suffix]["wiki_subdir"]
    dst_dir = WIKI_COMPANIES / company_name / wiki_subdir
    dst_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for f in files:
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
    parser.add_argument("--company", type=str)
    parser.add_argument("--pages", type=str, help="periodicReports / latestAnnouncement / research")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    graph = Graph()
    companies = get_a_share_companies(graph)

    if args.company:
        companies = [c for c in companies if c["name"] == args.company]
        if not companies:
            print(f"'{args.company}' not found or not A-share")
            sys.exit(1)

    if args.list:
        print(f"A 股公司 ({len(companies)} 家):")
        for c in companies:
            print(f"  {c['ticker']} {c['name']}")
        return

    page_types = [args.pages] if args.pages else list(PAGE_TYPES.keys())

    print("=" * 50)
    print(f"  批量下载 — {len(companies)} 家 × {len(page_types)} 种类型")
    print("=" * 50)

    total = 0
    for i, company in enumerate(companies):
        print(f"\n[{i+1}/{len(companies)}] {company['name']} ({company['ticker']})")
        for suffix in page_types:
            files = run_download(company["ticker"], company["name"], suffix)
            if files:
                copied = organize_files(company["name"], suffix, files)
                total += copied

    print(f"\n{'=' * 50}")
    print(f"  Done. {total} files saved to wiki")
    print(f"{'=' * 50}")

    append_log(f"Downloaded {total} files for {len(companies)} companies")

    if total > 0:
        print(f"\n  下一步: python3 scripts/ingest.py")


if __name__ == "__main__":
    main()
