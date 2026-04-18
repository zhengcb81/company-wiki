#!/usr/bin/env python3
"""
cninfo_download.py — 从巨潮资讯网下载所有类型的文档（独立实现）

三种模式：
  1. 年报/季报 — 用搜索 API（快速）
  2. 招股说明书 — 用搜索 API（快速）
  3. 投资者关系 — 用 Playwright 浏览器（因为 API 不暴露这些文档）

用法：
  python3 scripts/cninfo_download.py                      # 下载所有缺文档的公司
  python3 scripts/cninfo_download.py --company 寒武纪     # 只下载指定公司
  python3 scripts/cninfo_download.py --type ir            # 只下载投资者关系
  python3 scripts/cninfo_download.py --type annual        # 只下载年报
  python3 scripts/cninfo_download.py --type prospectus    # 只下载招股说明书
  python3 scripts/cninfo_download.py --all                # 重新下载全部（跳过已有检查）
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from playwright.sync_api import sync_playwright

# ── 路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
LOG_PATH = WIKI_ROOT / "log.md"

# ── 搜索 API 配置 ──
CNINFO_SEARCH_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
CNINFO_PDF_BASE = "https://static.cninfo.com.cn/"

# ── 下载类型 ──
DOWNLOAD_TYPES = {
    "annual": {
        "label": "年报/季报",
        "searchkeys": ["年度报告", "半年度报告"],
        "wiki_subdir": "raw/reports",
        "method": "api",
        "filter_include": ["报告"],
        "filter_exclude": ["摘要"],
        "max_items": 6,
    },
    "prospectus": {
        "label": "招股说明书",
        "searchkeys": ["招股说明书"],
        "wiki_subdir": "raw/reports",
        "method": "api",
        "filter_include": ["招股说明书"],
        "filter_exclude": [],
        "max_items": 3,
    },
    "ir": {
        "label": "投资者关系",
        "searchkeys": [],
        "wiki_subdir": "raw/research",
        "method": "browser",
        "max_items": 20,
    },
}


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120]


# ══════════════════════════════════════
#  方法1: 搜索 API（年报/招股书）
# ══════════════════════════════════════

def search_api(company_name, ticker, searchkey, page_size=20):
    """用巨潮搜索 API 查公告."""
    params = {
        "searchkey": f"{ticker} {searchkey}" if ticker else f"{company_name} {searchkey}",
        "sdate": "2019-01-01",
        "edate": "2026-12-31",
        "isfulltext": "false",
        "sortname": "nothing",
        "sorttype": "desc",
        "pageNum": "1",
        "pageSize": str(page_size),
    }
    try:
        resp = requests.get(CNINFO_SEARCH_URL, headers=HEADERS, params=params, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("announcements", []) or []
    except Exception:
        pass
    return []


def download_pdf_api(adjunct_url, save_path):
    """下载 PDF."""
    url = CNINFO_PDF_BASE + adjunct_url
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        if resp.status_code == 200 and len(resp.content) > 1024:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False


def download_api_type(company_name, ticker, type_key):
    """用搜索 API 下载一种类型."""
    config = DOWNLOAD_TYPES[type_key]
    save_dir = WIKI_ROOT / "companies" / company_name / config["wiki_subdir"]
    save_dir.mkdir(parents=True, exist_ok=True)
    existing = {f.name for f in save_dir.glob("*.pdf")}

    downloaded = 0
    for sk in config["searchkeys"]:
        anns = search_api(company_name, ticker, sk)
        # 过滤
        inc = config["filter_include"]
        exc = config["filter_exclude"]
        for a in anns:
            title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
            a["_title"] = title
            if inc and not any(kw in title for kw in inc):
                continue
            if exc and any(kw in title for kw in exc):
                continue

            filename = f"{sanitize_filename(company_name)}：{sanitize_filename(title)}.pdf"
            if filename in existing:
                continue
            if downloaded >= config["max_items"]:
                break

            save_path = save_dir / filename
            ts = a.get("announcementTime", 0)
            date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else "?"
            print(f"    {title[:50]} ({date_str})", end="", flush=True)

            if download_pdf_api(a.get("adjunctUrl", ""), save_path):
                size_kb = save_path.stat().st_size / 1024
                print(f" [{size_kb:.0f}KB]")
                downloaded += 1
                existing.add(filename)
            else:
                print(f" FAILED")
            time.sleep(0.3)

    return downloaded


# ══════════════════════════════════════
#  方法2: Playwright（投资者关系）
# ══════════════════════════════════════

# 交易所 → 巨潮 URL 参数
EXCHANGE_MAP = {
    "SSE STAR": ("sse_star", "科创板"),
    "SSE": ("sse", "上交所"),
    "SZSE": ("szse", "深交所"),
    "BSE": ("bse", "北交所"),
}


def download_ir_browser(company_name, ticker, exchange):
    """用 Playwright 从巨潮下载投资者关系活动记录表."""
    config = DOWNLOAD_TYPES["ir"]
    save_dir = WIKI_ROOT / "companies" / company_name / config["wiki_subdir"]
    save_dir.mkdir(parents=True, exist_ok=True)
    existing = {f.name for f in save_dir.glob("*.pdf")}

    column, _ = EXCHANGE_MAP.get(exchange, ("szse", "深交所"))

    downloaded = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # 访问公司公告页，筛选"投资者关系"
        # 巨潮的投资者关系记录在 "互动易" 或 "投资者关系" 栏目
        url = (f"https://www.cninfo.com.cn/new/disclosure/stock"
               f"?stockCode={ticker}&orgId=")
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(2)
        except Exception as e:
            print(f"    page load error: {e}")
            browser.close()
            return 0

        # 尝试在页面上查找投资者关系分类
        # 方法1: 直接访问投资者关系活动记录的 API
        api_url = (f"https://www.cninfo.com.cn/new/information/topSearch/query"
                   f"?keyWord={ticker}+投资者关系活动记录表"
                   f"&maxSecNum=10&maxListNum=50")
        try:
            page.goto(api_url, timeout=15000, wait_until="domcontentloaded")
            text = page.inner_text("body")
            import json
            data = json.loads(text)
            anns = data.get("classifiedAnnouncements", [])
            if not anns:
                anns = data.get("announcements", [])
            if anns:
                for a in anns[:config["max_items"]]:
                    title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
                    adjunct = a.get("adjunctUrl", "")
                    if not adjunct:
                        continue
                    filename = f"{sanitize_filename(company_name)}：{sanitize_filename(title)}.pdf"
                    if filename in existing:
                        continue
                    save_path = save_dir / filename
                    print(f"    {title[:50]}", end="", flush=True)
                    if download_pdf_api(adjunct, save_path):
                        size_kb = save_path.stat().st_size / 1024
                        print(f" [{size_kb:.0f}KB]")
                        downloaded += 1
                        existing.add(filename)
                    else:
                        print(f" FAILED")
                    time.sleep(0.3)
                browser.close()
                return downloaded
        except Exception:
            pass

        # 方法2: 浏览公告列表页，用 Playwright 模拟点击
        # 先搜索全部公告，筛选包含"投资者关系"的
        search_url = (f"https://www.cninfo.com.cn/new/fulltextSearch?"
                      f"notautosubmit=&keyWord={ticker}+投资者关系")
        try:
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)

            # 获取搜索结果
            items = page.query_selector_all("a[href*='/new/disclosure/detail']")
            print(f"    found {len(items)} result links")

            for item in items[:config["max_items"]]:
                title = item.inner_text().strip()
                if "投资者关系" not in title and "调研" not in title:
                    continue
                filename = f"{sanitize_filename(company_name)}：{sanitize_filename(title)}.pdf"
                if filename in existing:
                    continue

                # 点击进入详情页
                href = item.get_attribute("href")
                if not href:
                    continue

                detail_url = f"https://www.cninfo.com.cn{href}" if href.startswith("/") else href
                try:
                    page.goto(detail_url, timeout=20000, wait_until="domcontentloaded")
                    time.sleep(1)

                    # 找到 PDF 下载链接
                    pdf_link = page.query_selector("a[href*='.pdf'], a[href*='.PDF'], a[download]")
                    if pdf_link:
                        pdf_url = pdf_link.get_attribute("href") or pdf_link.get_attribute("download")
                        if pdf_url and not pdf_url.startswith("http"):
                            pdf_url = f"https://static.cninfo.com.cn/{pdf_url}"

                        save_path = save_dir / filename
                        print(f"    {title[:50]}", end="", flush=True)
                        try:
                            resp = requests.get(pdf_url, headers=HEADERS, timeout=60, stream=True)
                            if resp.status_code == 200 and len(resp.content) > 1024:
                                with open(save_path, "wb") as f:
                                    f.write(resp.content)
                                size_kb = save_path.stat().st_size / 1024
                                print(f" [{size_kb:.0f}KB]")
                                downloaded += 1
                                existing.add(filename)
                            else:
                                print(f" FAILED (no content)")
                        except Exception as e:
                            print(f" FAILED ({e})")
                except Exception as e:
                    print(f"    detail page error: {e}")

                time.sleep(0.5)

        except Exception as e:
            print(f"    search page error: {e}")

        browser.close()

    return downloaded


# ══════════════════════════════════════
#  主程序
# ══════════════════════════════════════

def needs_download(company_name, type_key):
    """检查是否需要下载."""
    config = DOWNLOAD_TYPES[type_key]
    save_dir = WIKI_ROOT / "companies" / company_name / config["wiki_subdir"]
    if not save_dir.exists():
        return True
    pdfs = list(save_dir.glob("*.pdf"))
    if not pdfs:
        return True
    if type_key == "annual":
        has_annual = any("年度报告" in f.name and "摘要" not in f.name for f in pdfs)
        if not has_annual:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="从巨潮资讯网下载财报/招股书/投资者关系")
    parser.add_argument("--company", type=str, help="只下载指定公司")
    parser.add_argument("--type", type=str, choices=["annual", "prospectus", "ir"],
                        help="只下载指定类型")
    parser.add_argument("--all", action="store_true", help="重新下载全部")
    args = parser.parse_args()

    with open(WIKI_ROOT / "graph.yaml") as f:
        graph = yaml.safe_load(f)

    companies = graph.get("companies", {})
    a_share = {"SSE STAR", "SSE", "SZSE", "BSE"}

    comp_list = []
    for name, info in companies.items():
        if info.get("exchange") not in a_share:
            continue
        if args.company and name != args.company:
            continue
        comp_list.append({
            "name": name,
            "ticker": info.get("ticker"),
            "exchange": info.get("exchange"),
        })

    type_keys = [args.type] if args.type else list(DOWNLOAD_TYPES.keys())

    print(f"{'='*55}")
    print(f"  巨潮资讯网文档下载 (Playwright + API)")
    print(f"  公司: {len(comp_list)} 家")
    print(f"  类型: {', '.join(DOWNLOAD_TYPES[t]['label'] for t in type_keys)}")
    print(f"{'='*55}")

    total = 0
    for i, comp in enumerate(comp_list):
        print(f"\n[{i+1}/{len(comp_list)}] {comp['name']} ({comp['ticker']})")

        for type_key in type_keys:
            config = DOWNLOAD_TYPES[type_key]
            label = config["label"]

            if not args.all and not needs_download(comp["name"], type_key):
                save_dir = WIKI_ROOT / "companies" / comp["name"] / config["wiki_subdir"]
                n = len(list(save_dir.glob("*.pdf"))) if save_dir.exists() else 0
                print(f"  [{label}] 已有 {n} 份，跳过")
                continue

            print(f"  [{label}]", end="", flush=True)

            if config["method"] == "api":
                n = download_api_type(comp["name"], comp["ticker"], type_key)
            else:
                n = download_ir_browser(comp["name"], comp["ticker"], comp["exchange"])

            if n > 0:
                print(f"  -> +{n} files")
                total += n
            else:
                print(f"  -> 无新文件")

        time.sleep(1)

    print(f"\n{'='*55}")
    print(f"  完成. 新下载: {total} 份")
    print(f"{'='*55}")

    if total > 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] cninfo_download | {total} files for {len(comp_list)} companies\n"
        if LOG_PATH.exists():
            content = LOG_PATH.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"
        LOG_PATH.write_text(content + entry, encoding="utf-8")


if __name__ == "__main__":
    main()
