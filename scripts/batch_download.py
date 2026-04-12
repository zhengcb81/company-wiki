#!/usr/bin/env python3
"""
batch_download.py — 稳健的批量下载（支持断点续传）
逐公司下载，每个类型限 2 页（~60 个文档），跳过已有文件。

用法：
    python3 scripts/batch_download.py                     # 下载所有缺失的
    python3 scripts/batch_download.py --company 中微公司   # 只下一家
    python3 scripts/batch_download.py --pages research     # 只下投资者关系
"""

import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph

DOWNLOADER = Path(os.path.expanduser("~/StockInfoDownloader"))
WIKI = WIKI_ROOT / "companies"
LOG = WIKI_ROOT / "log.md"

def load_types():
    """从 config.yaml 读取页面类型"""
    import yaml
    with open(WIKI_ROOT / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    types = {}
    for p in cfg.get("report_downloader", {}).get("pages", []):
        suffix = p["suffix"]
        types[suffix] = {
            "name": p["name"],
            "dir": "raw/research" if suffix == "research" else "raw/reports",
            "kw": p.get("allowed_keywords"),
            "pages": p.get("max_pages", 3),
            "reverse": p.get("reverse_order", False),
        }
    return types


TYPES = load_types()


def needs_download(company, suffix):
    """检查该公司该类型是否需要下载"""
    t = TYPES[suffix]
    target = WIKI / company / t["dir"]
    if not target.exists():
        return True
    existing = len(list(target.glob("*.pdf")))
    # 只下载完全没有文件的
    return existing == 0


def download_one(stock_code, company_name, suffix):
    """下载单个公司的单种类型"""
    t = TYPES[suffix]
    config_path = DOWNLOADER / "config.json"

    # 写配置
    with open(config_path) as f:
        cfg = json.load(f)
    cfg["pages"] = [{"name": t["name"], "suffix": suffix, "max_pages": t["pages"]}]
    if t["kw"]:
        cfg["pages"][0]["allowed_keywords"] = t["kw"]
    if t.get("reverse"):
        cfg["pages"][0]["reverse_order"] = True
    cfg["companies"] = [{"stock_code": stock_code, "company_name": company_name, "enabled": True, "priority": 1}]
    cfg["save_dir"] = str(DOWNLOADER / "downloads")
    cfg["download"]["save_directory"] = cfg["save_dir"]
    cfg["download"]["max_pages"] = t["pages"]
    with open(config_path, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    # 清理旧下载
    dl = DOWNLOADER / "downloads" / company_name
    if dl.exists():
        shutil.rmtree(dl)

    try:
        subprocess.run(
            [sys.executable, str(DOWNLOADER / "main.py"), stock_code],
            cwd=str(DOWNLOADER), capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        print(f"    timeout")
        return 0

    # 搬文件
    if not dl.exists():
        return 0
    dst = WIKI / company_name / t["dir"]
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in dl.glob("*.pdf"):
        d = dst / f.name
        if not d.exists():
            shutil.copy2(f, d)
            n += 1
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", type=str)
    parser.add_argument("--pages", type=str)
    args = parser.parse_args()

    graph = Graph()
    a_share = {"SSE STAR", "SSE", "SZSE", "BSE"}
    companies = [c for c in graph.get_all_companies() if c["exchange"] in a_share]
    if args.company:
        companies = [c for c in companies if c["name"] == args.company]

    suffixes = [args.pages] if args.pages else list(TYPES.keys())

    print(f"={50}")
    print(f"  批量下载 {len(companies)} 家 × {len(suffixes)} 类型")
    print(f"={50}")

    total = 0
    for i, comp in enumerate(companies):
        name, code = comp["name"], comp["ticker"]
        downloaded_this_company = False

        for suffix in suffixes:
            if not needs_download(name, suffix):
                continue

            t = TYPES[suffix]
            print(f"\n[{i+1}/{len(companies)}] {name} [{t['name']}]", end="", flush=True)
            n = download_one(code, name, suffix)
            if n > 0:
                print(f" +{n} files")
                total += n
                downloaded_this_company = True
            else:
                print(f" (no new files)")

        # 每家公司之间休息 2 秒避免反爬
        if downloaded_this_company:
            time.sleep(2)

    print(f"\n{'='*50}")
    print(f"  Done. {total} new files")
    print(f"{'='*50}")

    if total > 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] batch_download | {total} files\n"
        if LOG.exists():
            content = LOG.read_text()
        else:
            content = "# 知识库操作日志\n"
        (LOG).write_text(content + entry, encoding="utf-8")


if __name__ == "__main__":
    main()
