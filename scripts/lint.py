#!/usr/bin/env python3
"""
lint.py — 知识库健康检查模块
定期检查 wiki 的健康状态，发现问题并报告。

用法：
    python3 scripts/lint.py                    # 完整检查
    python3 scripts/lint.py --check stale      # 只检查过时页面
    python3 scripts/lint.py --check orphans    # 只检查孤儿页面
    python3 scripts/lint.py --check quality    # 只检查质量
    python3 scripts/lint.py --fix              # 自动修复可修复的问题

检查项：
    1. 过时：页面长期未更新
    2. 孤儿：页面没有被其他页面引用
    3. 空页面：时间线没有条目的页面
    4. 质量：摘要质量统计
    5. 配置一致性：config.yaml 与目录结构是否匹配
    6. 引用完整性：wiki 中的来源链接是否有效
"""

import argparse
import glob
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"


def load_config():
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class LintResult:
    def __init__(self):
        self.issues = []
        self.stats = {}

    def add(self, level, category, message, file_path=None):
        self.issues.append({
            'level': level,      # ERROR, WARNING, INFO
            'category': category,
            'message': message,
            'file': str(file_path) if file_path else None,
        })

    def summary(self):
        errors = sum(1 for i in self.issues if i['level'] == 'ERROR')
        warnings = sum(1 for i in self.issues if i['level'] == 'WARNING')
        infos = sum(1 for i in self.issues if i['level'] == 'INFO')
        return errors, warnings, infos


def check_stale_pages(result, max_age_days=30):
    """检查过时页面"""
    cutoff = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")

    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")

            # 从 frontmatter 提取 last_updated
            match = re.search(r'last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
            if match:
                last_updated = match.group(1)
                if last_updated < cutoff:
                    age = (datetime.now() - datetime.strptime(last_updated, "%Y-%m-%d")).days
                    relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                    result.add("WARNING", "stale",
                              f"Page not updated for {age} days (last: {last_updated})",
                              relpath)
            else:
                relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                result.add("INFO", "stale", "No last_updated in frontmatter", relpath)


def check_orphan_pages(result):
    """检查孤儿页面（没有被其他页面引用的页面）"""
    all_pages = set()
    referenced = set()

    # 收集所有页面
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for f in glob.glob(pattern):
            rel = os.path.relpath(f, WIKI_ROOT)
            all_pages.add(rel)

    # 扫描引用关系
    for wiki_file in glob.glob(f"{WIKI_ROOT}/**/wiki/*.md", recursive=True):
        content = Path(wiki_file).read_text(encoding="utf-8")
        # 提取 wikilinks [[...]]
        for match in re.finditer(r'\[\[([^\]]+)\]\]', content):
            referenced.add(match.group(1))
        # 提取相对路径链接 [text](path)
        for match in re.finditer(r'\[.*?\]\(([^)]+)\)', content):
            ref = match.group(1)
            if ref.startswith("../") or ref.startswith("../../"):
                # 解析相对路径
                base = os.path.dirname(wiki_file)
                resolved = os.path.normpath(os.path.join(base, ref))
                referenced.add(os.path.relpath(resolved, WIKI_ROOT))

    # 检查孤儿
    for page in all_pages:
        # index.md 和 overview.md 不算孤儿
        if page.endswith("index.md") or page.endswith("overview.md"):
            continue
        # 检查是否有其他页面引用此页面
        basename = os.path.basename(page).replace(".md", "")
        if basename not in referenced and page not in referenced:
            result.add("INFO", "orphan", f"Page may be orphaned (no inbound references)", page)


def check_empty_pages(result):
    """检查空页面（时间线没有条目）"""
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")

            # 检查时间线部分是否有条目
            timeline_pos = content.find("## 时间线")
            if timeline_pos < 0:
                continue

            after_timeline = content[timeline_pos:]
            has_entries = "### 2" in after_timeline  # 日期格式 20xx-xx-xx

            if not has_entries:
                relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                result.add("WARNING", "empty", "Timeline has no entries", relpath)


def check_broken_links(result):
    """检查来源链接是否有效"""
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")
            wiki_dir = os.path.dirname(wiki_file)

            # 提取 [来源](path) 链接
            for match in re.finditer(r'\[来源\]\(([^)]+)\)', content):
                ref = match.group(1)
                resolved = os.path.normpath(os.path.join(wiki_dir, ref))
                if not os.path.exists(resolved):
                    relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                    result.add("WARNING", "broken_link",
                              f"Source file not found: {ref}", relpath)


def check_config_consistency(result, config):
    """检查 config.yaml 与目录结构是否一致"""
    # 检查公司目录
    for company in config.get("companies", []):
        name = company["name"]
        company_dir = WIKI_ROOT / "companies" / name
        if not company_dir.exists():
            result.add("ERROR", "config", f"Company directory missing: {name}")

    # 检查行业目录
    for sector_name in config.get("sectors", {}):
        sector_dir = WIKI_ROOT / "sectors" / sector_name
        if not sector_dir.exists():
            result.add("ERROR", "config", f"Sector directory missing: {sector_name}")

    # 检查主题目录
    for theme_name in config.get("themes", {}):
        theme_dir = WIKI_ROOT / "themes" / theme_name
        if not theme_dir.exists():
            result.add("ERROR", "config", f"Theme directory missing: {theme_name}")


def check_data_freshness(result):
    """检查数据新鲜度（最近一次采集时间）"""
    log_content = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""

    # 查找最后一次 collect_news 的时间
    last_collect = None
    for match in re.finditer(r'## \[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\] collect_news', log_content):
        last_collect = match.group(1)

    if last_collect:
        age = (datetime.now() - datetime.strptime(last_collect, "%Y-%m-%d")).days
        if age > 1:
            result.add("WARNING", "freshness",
                      f"Last news collection was {age} days ago ({last_collect})")
        else:
            result.add("INFO", "freshness", f"Data is fresh (last collected: {last_collect})")
    else:
        result.add("WARNING", "freshness", "No news collection found in log")


def run_lint(checks=None):
    """运行指定的检查项"""
    result = LintResult()
    config = load_config()

    all_checks = {
        'stale': lambda: check_stale_pages(result),
        'orphans': lambda: check_orphan_pages(result),
        'empty': lambda: check_empty_pages(result),
        'links': lambda: check_broken_links(result),
        'config': lambda: check_config_consistency(result, config),
        'freshness': lambda: check_data_freshness(result),
    }

    if checks is None or 'all' in checks:
        checks = list(all_checks.keys())

    for check_name in checks:
        if check_name in all_checks:
            all_checks[check_name]()

    return result


def main():
    parser = argparse.ArgumentParser(description="知识库健康检查")
    parser.add_argument("--check", type=str, default="all",
                        help="检查项: all|stale|orphans|empty|links|config|freshness")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    checks = args.check.split(",") if args.check != "all" else ["all"]
    result = run_lint(checks)

    if args.json:
        import json
        print(json.dumps(result.issues, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("  上市公司知识库 — 健康检查")
        print("=" * 50)

        if not result.issues:
            print("\n  All checks passed! No issues found.")
        else:
            # 按级别分组
            for level in ["ERROR", "WARNING", "INFO"]:
                issues = [i for i in result.issues if i['level'] == level]
                if issues:
                    icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}[level]
                    print(f"\n  [{level}] ({len(issues)})")
                    for i in issues:
                        file_info = f" ({i['file']})" if i['file'] else ""
                        print(f"    {icon} [{i['category']}] {i['message']}{file_info}")

        errors, warnings, infos = result.summary()
        print(f"\n{'=' * 50}")
        print(f"  Summary: {errors} errors, {warnings} warnings, {infos} info")
        print(f"{'=' * 50}")

    # 记录到 log
    errors, warnings, infos = result.summary()
    if errors > 0 or warnings > 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] lint | {errors} errors, {warnings} warnings, {infos} info\n"
        for i in result.issues:
            if i['level'] in ('ERROR', 'WARNING'):
                entry += f"- [{i['level']}] {i['category']}: {i['message']}\n"
        if LOG_PATH.exists():
            content = LOG_PATH.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"
        content += entry
        LOG_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
