#!/usr/bin/env python3
"""
download_reports_v2.py — 批量下载财报/招股说明书/投资者关系文档 (修复版)
调用 StockInfoDownloader 从巨潮资讯网下载，确保文件保存到正确位置。

修复的问题：
1. 配置修改后立即验证
2. 下载完成后检查实际文件位置
3. 如果文件在错误位置，自动复制到正确位置
4. 完整的错误处理和日志记录

用法：
    python3 scripts/download_reports_v2.py                    # 下载所有 A 股公司
    python3 scripts/download_reports_v2.py --company 中微公司  # 只下载指定公司
    python3 scripts/download_reports_v2.py --check            # 检查配置和文件状态
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
LOG_PATH = WIKI_ROOT / "log.md"

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph

# 关键路径定义
DOWNLOADER_DIR = Path(os.path.expanduser("~/StockInfoDownloader"))
WIKI_COMPANIES = WIKI_ROOT / "companies"
WINDOWS_DOWNLOADS = Path("/mnt/c/Users/郑曾波/Projects/StockInfoDownloader/downloads")


def log(message):
    """记录日志"""
    print(message)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] download_reports_v2 | {message}\n"
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def load_page_types():
    """从 config.yaml 读取页面类型配置"""
    import yaml
    cfg_path = WIKI_ROOT / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    types = {}
    for page in cfg.get("report_downloader", {}).get("pages", []):
        suffix = page["suffix"]
        # 确定目标子目录
        target_dirs = {
            "periodicReports": "raw/reports",
            "latestAnnouncement": "raw/prospectus",
            "research": "raw/investor_relations",
        }
        types[suffix] = {
            "name": page["name"],
            "target_dir": target_dirs.get(suffix, "raw/reports"),
            "keywords": page.get("allowed_keywords"),
            "max_pages": page.get("max_pages", 3),
            "reverse": page.get("reverse_order", False),
        }
    return types


PAGE_TYPES = load_page_types()


def get_a_share_companies(graph):
    """获取A股公司列表"""
    a_share = {"SSE STAR", "SSE", "SZSE", "BSE"}
    return [c for c in graph.get_all_companies() if c["exchange"] in a_share]


def check_config():
    """检查配置是否正确"""
    print("=" * 70)
    print("  配置检查")
    print("=" * 70)
    
    issues = []
    
    # 检查 StockInfoDownloader 目录
    if not DOWNLOADER_DIR.exists():
        issues.append(f"StockInfoDownloader 目录不存在: {DOWNLOADER_DIR}")
    
    # 检查 config.json
    config_path = DOWNLOADER_DIR / "config.json"
    if not config_path.exists():
        issues.append(f"config.json 不存在: {config_path}")
    else:
        with open(config_path) as f:
            config = json.load(f)
        
        save_dir = config.get("save_dir", "")
        print(f"当前 save_dir: {save_dir}")
        
        # 检查是否是绝对路径
        if not os.path.isabs(save_dir):
            issues.append(f"save_dir 是相对路径: {save_dir}")
            print(f"  ⚠️ 相对路径会保存到: {DOWNLOADER_DIR / save_dir}")
    
    # 检查 Windows downloads 目录
    if WINDOWS_DOWNLOADS.exists():
        pdf_count = len(list(WINDOWS_DOWNLOADS.rglob("*.pdf")))
        print(f"Windows downloads 目录: {pdf_count} 个 PDF 文件")
    else:
        issues.append(f"Windows downloads 目录不存在: {WINDOWS_DOWNLOADS}")
    
    # 检查 wiki companies 目录
    if WIKI_COMPANIES.exists():
        pdf_count = len(list(WIKI_COMPANIES.rglob("raw/**/*.pdf")))
        print(f"Wiki companies 目录: {pdf_count} 个 PDF 文件")
    else:
        issues.append(f"Wiki companies 目录不存在: {WIKI_COMPANIES}")
    
    print()
    if issues:
        print("❌ 发现问题:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ 配置正确")
        return True


def update_config(stock_code, company_name, page_suffix):
    """更新 StockInfoDownloader 的 config.json"""
    pt = PAGE_TYPES[page_suffix]
    
    # 构建页面配置
    page_config = {
        "name": pt["name"],
        "suffix": page_suffix,
        "max_pages": pt["max_pages"],
    }
    if pt["keywords"]:
        page_config["allowed_keywords"] = pt["keywords"]
    if pt.get("reverse"):
        page_config["reverse_order"] = True
    
    # 读取现有配置
    config_path = DOWNLOADER_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 更新配置
    config["pages"] = [page_config]
    config["companies"] = [{
        "stock_code": stock_code,
        "company_name": company_name,
        "enabled": True,
        "priority": 1,
    }]
    
    # 关键：使用绝对路径
    target_dir = WIKI_COMPANIES / company_name
    config["save_dir"] = str(target_dir)
    if "download" in config:
        config["download"]["save_directory"] = str(target_dir)
    
    # 写入配置
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 验证配置已更新
    with open(config_path, "r", encoding="utf-8") as f:
        verify_config = json.load(f)
    
    if verify_config.get("save_dir") != str(target_dir):
        raise Exception(f"配置更新失败: save_dir={verify_config.get('save_dir')}")
    
    return target_dir


def run_download(stock_code, company_name, page_suffix):
    """运行 StockInfoDownloader 下载"""
    log(f"开始下载: {company_name} ({stock_code}) - {PAGE_TYPES[page_suffix]['name']}")
    
    # 1. 更新配置
    try:
        target_dir = update_config(stock_code, company_name, page_suffix)
        log(f"  配置更新成功: save_dir={target_dir}")
    except Exception as e:
        log(f"  配置更新失败: {e}")
        return []
    
    # 2. 运行下载
    try:
        result = subprocess.run(
            [sys.executable, str(DOWNLOADER_DIR / "main.py"), stock_code],
            cwd=str(DOWNLOADER_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
        
        if result.returncode != 0:
            log(f"  下载失败: exit code {result.returncode}")
            if result.stderr:
                log(f"  错误信息: {result.stderr[:200]}")
            return []
        
    except subprocess.TimeoutExpired:
        log(f"  下载超时")
        return []
    except Exception as e:
        log(f"  下载异常: {e}")
        return []
    
    # 3. 检查下载结果
    # 首先检查目标目录
    if target_dir.exists():
        files = list(target_dir.rglob("*.pdf")) + list(target_dir.rglob("*.doc*"))
        if files:
            log(f"  下载成功: {len(files)} 个文件 (目标目录)")
            return files
    
    # 如果目标目录没有，检查 Windows downloads 目录
    windows_company_dir = WINDOWS_DOWNLOADS / company_name
    if not windows_company_dir.exists():
        # 尝试带股票代码的目录名
        for dir_name in os.listdir(WINDOWS_DOWNLOADS):
            if company_name in dir_name:
                windows_company_dir = WINDOWS_DOWNLOADS / dir_name
                break
    
    if windows_company_dir.exists():
        files = list(windows_company_dir.glob("*.pdf")) + list(windows_company_dir.glob("*.doc*"))
        if files:
            log(f"  下载成功: {len(files)} 个文件 (Windows目录)")
            return files
    
    log(f"  未找到下载文件")
    return []


def copy_files_to_wiki(company_name, files, target_subdir):
    """将文件复制到 wiki 目录"""
    if not files:
        return 0
    
    # 确定目标目录
    target_dir = WIKI_COMPANIES / company_name / target_subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    copied = 0
    for file_path in files:
        target_file = target_dir / file_path.name
        if not target_file.exists():
            try:
                shutil.copy2(file_path, target_file)
                copied += 1
            except Exception as e:
                log(f"  复制失败: {file_path.name} - {e}")
    
    return copied


def sync_from_windows(company_name):
    """从 Windows 目录同步文件到 wiki"""
    # 查找 Windows 目录
    windows_company_dir = WINDOWS_DOWNLOADS / company_name
    if not windows_company_dir.exists():
        # 尝试带股票代码的目录名
        for dir_name in os.listdir(WINDOWS_DOWNLOADS):
            if company_name in dir_name:
                windows_company_dir = WINDOWS_DOWNLOADS / dir_name
                break
    
    if not windows_company_dir.exists():
        return 0
    
    # 获取所有文件
    files = list(windows_company_dir.glob("*.pdf")) + list(windows_company_dir.glob("*.doc*"))
    if not files:
        return 0
    
    # 分类并复制到 wiki
    total_copied = 0
    for file_path in files:
        filename = file_path.name
        
        # 分类
        if any(x in filename for x in ["一季度", "二季度", "三季度", "四季度", "季报"]):
            target_subdir = "raw/financial_reports/quarterly"
        elif "年度报告" in filename:
            target_subdir = "raw/financial_reports/annual"
        elif "半年度" in filename:
            target_subdir = "raw/financial_reports/semi_annual"
        elif "招股" in filename:
            target_subdir = "raw/prospectus"
        elif "投资者" in filename:
            target_subdir = "raw/investor_relations"
        elif any(x in filename for x in ["公告", "决议", "通知"]):
            target_subdir = "raw/announcements"
        else:
            target_subdir = "raw/research"
        
        # 复制文件
        target_dir = WIKI_COMPANIES / company_name / target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename
        
        if not target_file.exists():
            try:
                shutil.copy2(file_path, target_file)
                total_copied += 1
            except Exception as e:
                log(f"  复制失败: {filename} - {e}")
    
    return total_copied


def main():
    parser = argparse.ArgumentParser(description="批量下载财报/招股说明书/投资者关系")
    parser.add_argument("--company", type=str, help="只下载指定公司")
    parser.add_argument("--pages", type=str, help="periodicReports / latestAnnouncement / research")
    parser.add_argument("--check", action="store_true", help="检查配置")
    parser.add_argument("--sync", action="store_true", help="从 Windows 目录同步")
    parser.add_argument("--list", action="store_true", help="列出A股公司")
    args = parser.parse_args()
    
    # 检查配置
    if args.check:
        check_config()
        return
    
    # 列出公司
    graph = Graph()
    companies = get_a_share_companies(graph)
    
    if args.list:
        print(f"A 股公司 ({len(companies)} 家):")
        for c in companies:
            print(f"  {c['ticker']} {c['name']}")
        return
    
    # 过滤公司
    if args.company:
        companies = [c for c in companies if c["name"] == args.company]
        if not companies:
            print(f"'{args.company}' not found or not A-share")
            sys.exit(1)
    
    # 确定页面类型
    page_types = [args.pages] if args.pages else list(PAGE_TYPES.keys())
    
    print("=" * 70)
    print(f"  批量下载 — {len(companies)} 家 × {len(page_types)} 种类型")
    print("=" * 70)
    
    total_downloaded = 0
    total_copied = 0
    
    for i, company in enumerate(companies):
        print(f"\n[{i+1}/{len(companies)}] {company['name']} ({company['ticker']})")
        
        for suffix in page_types:
            # 下载
            files = run_download(company["ticker"], company["name"], suffix)
            
            if files:
                # 复制到 wiki
                target_subdir = PAGE_TYPES[suffix]["target_dir"]
                copied = copy_files_to_wiki(company["name"], files, target_subdir)
                total_copied += copied
                total_downloaded += len(files)
        
        # 如果开启了同步模式，也从 Windows 目录同步
        if args.sync:
            synced = sync_from_windows(company["name"])
            if synced > 0:
                print(f"  从 Windows 同步: {synced} 个文件")
                total_copied += synced
    
    print(f"\n{'=' * 70}")
    print(f"  完成")
    print(f"  下载文件: {total_downloaded}")
    print(f"  复制到 wiki: {total_copied}")
    print(f"{'=' * 70}")
    
    log(f"下载完成: {total_downloaded} 个文件下载, {total_copied} 个文件复制到 wiki")
    
    if total_copied > 0:
        print(f"\n  下一步: python3 scripts/ingest.py")


if __name__ == "__main__":
    main()