#!/usr/bin/env python3
"""
collect_reports.py — 财报/公告/投资者关系采集模块
调用 StockInfoDownloader 从巨潮资讯网下载文档。

下载内容：
  1. 定期报告（季报、半年报、年报）
  2. 招股说明书
  3. 投资者关系活动记录

用法：
    # 在 Windows 本地运行（StockInfoDownloader 所在机器）

    # 模式1：生成配置文件（不下载）
    python3 scripts/collect_reports.py --generate-config

    # 模式2：下载所有公司的所有类型文档
    python3 scripts/collect_reports.py

    # 模式3：只下载指定公司的指定类型
    python3 scripts/collect_reports.py --company 中微公司
    python3 scripts/collect_reports.py --pages periodicReports
    python3 scripts/collect_reports.py --company 中密控股 --pages research

前提：
    1. 本地已安装 StockInfoDownloader
    2. 已安装依赖：pip install -r requirements.txt && playwright install
    3. 在 config.yaml 中配置 report_downloader.tool_path

注意：
    StockInfoDownloader 需要 Playwright 浏览器引擎，
    仅支持在本地桌面环境运行（Windows/Mac/Linux with GUI）。
"""

import argparse
import json
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


def get_downloader_info(config):
    """获取 StockInfoDownloader 路径信息"""
    dl_cfg = config.get("report_downloader", {})
    tool_path = os.path.expanduser(dl_cfg.get("tool_path", ""))
    tool_path = tool_path.replace("/", os.sep)  # Windows 路径兼容

    if not os.path.isdir(tool_path):
        print(f"ERROR: StockInfoDownloader not found at: {tool_path}")
        print(f"  请在 config.yaml -> report_downloader.tool_path 中配置正确路径")
        print(f"  Windows 示例: C:/Users/xxx/Projects/StockInfoDownloader")
        sys.exit(1)

    main_py = os.path.join(tool_path, "main.py")
    if not os.path.isfile(main_py):
        print(f"ERROR: main.py not found in: {tool_path}")
        sys.exit(1)

    return tool_path, main_py


def generate_stockinfo_config(config, companies=None, pages=None):
    """
    生成 StockInfoDownloader 的配置 JSON。
    返回配置字典。
    """
    dl_cfg = config.get("report_downloader", {})
    wiki_companies = config.get("companies", [])
    dl_pages = dl_cfg.get("pages", [])

    # 过滤公司
    if companies:
        wiki_companies = [c for c in wiki_companies if c["name"] in companies]

    # 过滤页面类型
    if pages:
        dl_pages = [p for p in dl_pages if p["suffix"] in pages]

    # 构建 StockInfoDownloader 的 pages 配置
    sd_pages = []
    for p in dl_pages:
        page = {
            "name": p["name"],
            "suffix": p["suffix"],
            "max_pages": p.get("max_pages", 5),
        }
        if p.get("allowed_keywords"):
            page["allowed_keywords"] = p["allowed_keywords"]
        if p.get("reverse_order"):
            page["reverse_order"] = p["reverse_order"]
        sd_pages.append(page)

    # 构建 companies 配置
    sd_companies = []
    for c in wiki_companies:
        sd_companies.append({
            "stock_code": c["ticker"],
            "company_name": c["name"],
            "enabled": True,
            "priority": 1,
        })

    # 完整配置
    sd_config = {
        "save_dir": dl_cfg.get("save_dir", "downloads"),
        "headless": True,
        "max_retries": 3,
        "use_dynamic_delay": True,
        "base_url": "https://www.cninfo.com.cn",
        "page_load_strategy": "eager",
        "timeout": {
            "page_load": 30,
            "element_wait": 30,
            "download": 180,
            "script": 30,
        },
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
            "strategy": dl_cfg.get("browser_strategy", "playwright"),
            "headless": True,
            "window_size": {"width": 1920, "height": 1080},
            "timeout": 30,
            "page_load_timeout": 60,
            "implicit_wait": 10,
        },
        "anti_crawler": {
            "enabled": True,
            "base_delay": 1.0,
            "random_delay_range": [0.5, 2.0],
            "session_limit": 50,
            "max_retries": 3,
            "retry_backoff_factor": 2.0,
        },
        "download": {
            "max_pages": max(p.get("max_pages", 5) for p in dl_pages) if dl_pages else 5,
            "timeout": 180,
            "download_delay": 0.5,
            "concurrent_downloads": 3,
            "chunk_size": 8192,
            "file_name_format": "{stock_name}_{date}_{description}.pdf",
            "save_directory": dl_cfg.get("save_dir", "downloads"),
            "create_subdirs": True,
            "validate_downloads": True,
            "min_file_size": 1024,
            "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
        },
        "pages": sd_pages,
        "companies": sd_companies,
    }

    return sd_config


def run_downloader(main_py, stock_code, dl_config, tool_path):
    """
    调用 StockInfoDownloader 下载指定公司的文档。
    使用 --config 参数传入配置。
    """
    # 写临时配置到 StockInfoDownloader 目录
    temp_config = os.path.join(tool_path, "config_wiki.json")
    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump(dl_config, f, ensure_ascii=False, indent=2)

    cmd = [
        sys.executable, main_py,
        stock_code,
        "--config", temp_config,
    ]

    print(f"  CMD: python main.py {stock_code} --config config_wiki.json")
    print(f"  Working dir: {tool_path}")

    try:
        result = subprocess.run(
            cmd,
            cwd=tool_path,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout per company
        )
        if result.returncode != 0:
            print(f"  Exit code: {result.returncode}")
            if result.stderr:
                # 只显示最后几行 stderr
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines[-5:]:
                    print(f"  stderr: {line}")
        else:
            print(f"  Success")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout (600s)")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    finally:
        # 清理临时配置
        if os.path.exists(temp_config):
            os.remove(temp_config)


def copy_to_wiki(downloader_save_dir, wiki_root, company_name):
    """
    将下载的文件复制到知识库的 raw/ 目录。
    StockInfoDownloader 的目录结构:
      save_dir/{company_name}/research/
      save_dir/{company_name}/periodicReports/
      save_dir/{company_name}/latestAnnouncement/
    """
    if not os.path.isdir(downloader_save_dir):
        print(f"  Download dir not found: {downloader_save_dir}")
        return 0

    # 查找公司目录
    company_dir = None
    for candidate in [company_name, f"Stock_{company_name}"]:
        path = os.path.join(downloader_save_dir, candidate)
        if os.path.isdir(path):
            company_dir = path
            break

    if company_dir is None:
        # 尝试找包含公司名的目录
        for d in os.listdir(downloader_save_dir):
            full = os.path.join(downloader_save_dir, d)
            if os.path.isdir(full) and company_name in d:
                company_dir = full
                break

    if company_dir is None:
        print(f"  No download dir found for {company_name}")
        return 0

    print(f"  Source: {company_dir}")

    # 目录映射：StockInfoDownloader 子目录 → 知识库子目录
    dir_mapping = {
        "research": "raw/research",
        "periodicReports": "raw/reports",
        "latestAnnouncement": "raw/reports",
    }

    target_base = os.path.join(wiki_root, "companies", company_name)
    count = 0

    for src_subdir, dst_subdir in dir_mapping.items():
        src = os.path.join(company_dir, src_subdir)
        dst = os.path.join(target_base, dst_subdir)

        if not os.path.isdir(src):
            continue

        os.makedirs(dst, exist_ok=True)

        for f in os.listdir(src):
            src_file = os.path.join(src, f)
            dst_file = os.path.join(dst, f)

            if os.path.isfile(src_file) and not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)
                count += 1
                print(f"    + {dst_subdir}/{f}")

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
    parser = argparse.ArgumentParser(description="采集财报/公告/投资者关系文档")
    parser.add_argument("--company", type=str, help="只采集指定公司")
    parser.add_argument("--pages", type=str,
                        help="只下载指定类型 (periodicReports/latestAnnouncement/research)")
    parser.add_argument("--generate-config", action="store_true",
                        help="只生成配置文件，不下载")
    parser.add_argument("--output", type=str,
                        help="配置文件输出路径（配合 --generate-config）")
    args = parser.parse_args()

    print("=" * 50)
    print("  上市公司知识库 — 财报/公告/投资者关系采集")
    print("=" * 50)

    config = load_config()

    # 过滤公司和页面
    companies = None
    if args.company:
        companies = [args.company]

    pages = None
    if args.pages:
        pages = [args.pages]

    # 生成配置
    sd_config = generate_stockinfo_config(config, companies, pages)

    if args.generate_config:
        output_path = args.output or str(WIKI_ROOT / "configs" / "stockinfo_config.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sd_config, f, ensure_ascii=False, indent=2)
        print(f"\n  Config saved to: {output_path}")
        print(f"  Companies: {len(sd_config['companies'])}")
        print(f"  Page types: {[p['suffix'] for p in sd_config['pages']]}")
        print(f"\n  To download, run:")
        print(f"    cd {config['report_downloader']['tool_path']}")
        print(f"    copy {output_path} config.json")
        print(f"    python main.py --parallel --workers 2")
        return

    # 下载模式
    tool_path, main_py = get_downloader_info(config)
    wiki_root = str(WIKI_ROOT)

    total_copied = 0

    for company in sd_config["companies"]:
        name = company["company_name"]
        code = company["stock_code"]
        print(f"\n[{name}] ({code})")

        # 运行下载器
        success = run_downloader(main_py, code, sd_config, tool_path)

        if not success:
            print(f"  Download may have failed, checking for partial results...")

        # 复制到知识库
        dl_save_dir = os.path.join(tool_path, sd_config["save_dir"])
        if os.path.isdir(dl_save_dir):
            count = copy_to_wiki(dl_save_dir, wiki_root, name)
            print(f"  Copied {count} new files")
            total_copied += count

    print(f"\n{'=' * 50}")
    print(f"  Done. Total new files: {total_copied}")
    print(f"{'=' * 50}")

    if total_copied > 0:
        append_log(f"Collected {total_copied} report/research files")
        print(f"\n  下一步: python3 scripts/ingest.py")


if __name__ == "__main__":
    main()
