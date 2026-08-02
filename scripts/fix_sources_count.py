#!/usr/bin/env python3
"""
fix_sources_count.py — 补全 wiki frontmatter 的 sources_count 字段

扫描所有 wiki 页面，统计实际时间线条目数量（含归档），
补全缺失或错误的 sources_count 字段。

用法：
    python scripts/fix_sources_count.py [--dry-run]
"""

import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


def count_timeline_entries(content: str) -> int:
    """统计 wiki 文件中的时间线条目数量，包括归档的。"""
    # 可见条目：### YYYY-MM-DD | ...
    visible = len(re.findall(r'^### \d{4}-\d{2}-\d{2} \| .+$', content, re.MULTILINE))

    # 归档条目：N 条历史时间线条目已归档
    archived = 0
    m = re.search(r'(\d+) 条历史时间线条目已归档', content)
    if m:
        archived = int(m.group(1))

    return visible + archived


def fix_sources_count(dry_run: bool = False) -> dict:
    """扫描所有 wiki 文件，补全 sources_count。

    Returns:
        dict with stats: {scanned, fixed, already_correct, no_frontmatter}
    """
    stats = {"scanned": 0, "fixed": 0, "already_correct": 0, "no_frontmatter": 0}

    for wiki_file in sorted(WIKI_ROOT.glob("companies/*/wiki/*.md")):
        stats["scanned"] += 1
        content = wiki_file.read_text(encoding="utf-8")

        # 检查是否有 YAML frontmatter
        if not content.startswith("---"):
            stats["no_frontmatter"] += 1
            continue

        # 提取 frontmatter
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            stats["no_frontmatter"] += 1
            continue

        frontmatter = fm_match.group(1)

        # 统计实际条目数
        actual_count = count_timeline_entries(content)

        # 检查现有 sources_count
        sc_match = re.search(r'sources_count:\s*(\d+)', frontmatter)

        if sc_match:
            current_count = int(sc_match.group(1))
            if current_count == actual_count:
                stats["already_correct"] += 1
                continue
            elif actual_count == 0 and current_count > 0:
                # 有 sources_count 但无条目 — 可能是空模板，保留原值
                # 这类文件（如英伟达公司动态 sources_count:8 但无条目）是已知问题
                stats["already_correct"] += 1
                continue

        # 需要修复
        stats["fixed"] += 1
        new_fm = frontmatter

        if sc_match:
            # 替换现有值
            new_fm = re.sub(
                r'sources_count:\s*\d+',
                f'sources_count: {actual_count}',
                new_fm,
            )
        else:
            # 添加字段（在 last_updated 之后）
            if re.search(r'last_updated:', new_fm):
                new_fm = re.sub(
                    r'(last_updated:.*\n)',
                    rf'\1sources_count: {actual_count}\n',
                    new_fm,
                )
            else:
                # 在 tags 之前添加
                if re.search(r'tags:', new_fm):
                    new_fm = re.sub(
                        r'(tags:.*\n)',
                        rf'sources_count: {actual_count}\n\1',
                        new_fm,
                    )
                else:
                    # 追加到 frontmatter 末尾
                    new_fm += f"\nsources_count: {actual_count}"

        if dry_run:
            print(f"  [{wiki_file.relative_to(WIKI_ROOT)}] "
                  f"{sc_match.group(1) if sc_match else 'missing'} → {actual_count}")
        else:
            new_content = f"---\n{new_fm}\n---{content[fm_match.end():]}"
            wiki_file.write_text(new_content, encoding="utf-8")

    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[DRY RUN] 仅显示变更，不写入文件\n")

    print("扫描 wiki 页面 sources_count ...")
    stats = fix_sources_count(dry_run=dry_run)

    print("\n结果:")
    print(f"  扫描: {stats['scanned']} 个文件")
    print(f"  已正确: {stats['already_correct']}")
    print(f"  修复: {stats['fixed']}")
    print(f"  无 frontmatter: {stats['no_frontmatter']}")


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
