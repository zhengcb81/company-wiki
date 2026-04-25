#!/usr/bin/env python3
"""
cleanup_junk.py — 清理明显垃圾条目

功能：
1. 删除来源 URL 命中黑名单的新闻文件
2. 从 wiki 时间线中移除对应条目

用法：
    python3 scripts/cleanup_junk.py --dry-run
    python3 scripts/cleanup_junk.py --execute
"""

import argparse
import re
import sys
from pathlib import Path

from common import WIKI_ROOT

from config_rules_loader import RulesConfig


def load_blacklist():
    """加载 URL 黑名单"""
    rules = RulesConfig()
    return set(rules.get_url_blacklist())


def is_url_blacklisted(url, blacklist):
    """检查 URL 是否命中黑名单"""
    url_lower = url.lower()
    for pattern in blacklist:
        if pattern.lower() in url_lower:
            return True
    return False


def cleanup_news_files(blacklist, dry_run=True):
    """清理命中黑名单的新闻文件"""
    removed_files = 0
    checked_files = 0

    for news_file in WIKI_ROOT.rglob("companies/*/raw/news/*.md"):
        checked_files += 1
        try:
            text = news_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # 提取 source_url
        url = ""
        for line in text.split("\n"):
            if line.startswith("source_url:"):
                url = line.split(":", 1)[1].strip().strip('"').strip("'")
                break

        if url and is_url_blacklisted(url, blacklist):
            if not dry_run:
                news_file.unlink()
            removed_files += 1
            action = "WOULD REMOVE" if dry_run else "REMOVED"
            print(f"  [{action}] {news_file.name} ({url[:60]})")

    return checked_files, removed_files


def remove_orphan_entries(dry_run=True):
    """
    从 wiki 时间线中移除指向已不存在的文件的条目。
    同时也移除来源 URL 命中黑名单的条目。
    """
    blacklist = load_blacklist()
    files_checked = 0
    entries_checked = 0
    entries_removed = 0

    for wiki_path in WIKI_ROOT.rglob("*/wiki/*.md"):
        files_checked += 1
        try:
            text = wiki_path.read_text(encoding="utf-8")
        except Exception:
            continue

        if "## 时间线" not in text:
            continue

        original_text = text
        timeline_pos = text.find("## 时间线")
        timeline_section = text[timeline_pos:]
        next_section = re.search(r"\n## (?!时间线)", timeline_section)
        if next_section:
            after_timeline = timeline_section[next_section.start() :]
            timeline_section = timeline_section[: next_section.start()]
        else:
            after_timeline = ""

        # 分割条目
        parts = re.split(r"\n(?=### )", timeline_section)
        header = parts[0] if parts else ""
        entries = parts[1:] if len(parts) > 1 else []

        kept_entries = []
        removed_in_file = 0

        for entry in entries:
            entries_checked += 1
            # 查找来源链接
            source_match = re.search(r"- \[来源\]\(([^)]+)\)", entry)
            if not source_match:
                kept_entries.append(entry)
                continue

            source_path = source_match.group(1)
            # 相对路径转绝对路径
            if source_path.startswith("../"):
                resolved = wiki_path.parent / source_path
            elif source_path.startswith("../../"):
                resolved = wiki_path.parent.parent / source_path
            else:
                resolved = WIKI_ROOT / source_path

            # 检查文件是否存在
            file_exists = resolved.exists()

            # 检查 URL 是否黑名单（对新闻文件）
            url_blacklisted = False
            if resolved.suffix == ".md" and resolved.exists():
                try:
                    content = resolved.read_text(encoding="utf-8")
                    for line in content.split("\n"):
                        if line.startswith("source_url:"):
                            url = line.split(":", 1)[1].strip().strip('"').strip("'")
                            if is_url_blacklisted(url, blacklist):
                                url_blacklisted = True
                            break
                except Exception:
                    pass

            if not file_exists or url_blacklisted:
                removed_in_file += 1
                reason = "FILE_MISSING" if not file_exists else "URL_BLACKLISTED"
                action = "WOULD REMOVE" if dry_run else "REMOVED"
                # 提取标题
                title_match = re.search(r"### .*?\| (.*)", entry)
                title = title_match.group(1).strip() if title_match else ""
                print(f"  [{action}] {wiki_path.name}: {title[:50]} ({reason})")
            else:
                kept_entries.append(entry)

        if removed_in_file > 0 and not dry_run:
            new_timeline = (
                header + "\n" + "\n".join(kept_entries)
                if kept_entries
                else header + "\n"
            )
            new_text = text[:timeline_pos] + new_timeline + after_timeline
            # 清理连续空行
            new_text = re.sub(r"\n{4,}", "\n\n\n", new_text)
            wiki_path.write_text(new_text, encoding="utf-8")

        entries_removed += removed_in_file

    return files_checked, entries_checked, entries_removed


def main():
    parser = argparse.ArgumentParser(description="清理明显垃圾条目")
    parser.add_argument("--dry-run", action="store_true", help="预览模式（默认）")
    parser.add_argument("--execute", action="store_true", help="实际执行")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("  清理明显垃圾条目")
    if dry_run:
        print("  [DRY-RUN] 使用 --execute 实际执行")
    print("=" * 60)

    # 1. 清理新闻文件
    print("\n# 步骤 1: 清理黑名单来源的新闻文件")
    f_checked, f_removed = cleanup_news_files(load_blacklist(), dry_run=dry_run)
    print(f"  文件: 检查 {f_checked}, 移除 {f_removed}")

    # 2. 清理 wiki 中的孤儿条目
    print("\n# 步骤 2: 清理 wiki 中的孤儿/黑名单条目")
    w_checked, e_checked, e_removed = remove_orphan_entries(dry_run=dry_run)
    print(f"  文件: {w_checked}, 条目: 检查 {e_checked}, 移除 {e_removed}")

    print("\n" + "=" * 60)
    total_removed = f_removed + e_removed
    print(f"  总计移除: {total_removed} ({f_removed} 文件 + {e_removed} 条目)")
    print("=" * 60)

    if dry_run and total_removed > 0:
        print(f"\n提示: 运行 `python3 {__file__} --execute` 应用清理")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
