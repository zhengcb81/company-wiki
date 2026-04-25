#!/usr/bin/env python3
"""
backfill_wikilinks.py — 一次性回填所有 wiki 页面的 wikilinks

基于 graph.yaml 知识图谱关系:
- 同行业公司互相链接
- 公司 → 所属行业/主题
- 时间线中提及的实体 → 对应 wiki 页面
- 页面底部 "相关页面" 区域

用法:
    python scripts/backfill_wikilinks.py              # 执行回填
    python scripts/backfill_wikilinks.py --dry-run    # 只检查不修改
    python scripts/backfill_wikilinks.py --verify     # 验证无断链
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from wikilinks import WikilinkEngine


def main():
    import argparse
    parser = argparse.ArgumentParser(description="回填 wiki 页面 wikilinks")
    parser.add_argument("--dry-run", action="store_true", help="只检查不修改")
    parser.add_argument("--verify", action="store_true", help="验证无断链")
    args = parser.parse_args()

    engine = WikilinkEngine(wiki_root=str(WIKI_ROOT))

    if args.verify:
        verify_links(engine)
        return

    all_pages = engine.scan_all_pages()
    print(f"找到 {len(all_pages)} 个页面")

    files, links = engine.backfill_all(dry_run=args.dry_run)
    action = "将更新" if args.dry_run else "已更新"
    print(f"{action} {files} 个文件, 添加 {links} 个链接")

    if not args.dry_run and files > 0:
        print("\n验证...")
        verify_links(engine)


def verify_links(engine):
    """验证所有 wikilinks 无断链"""
    import re
    from pathlib import Path

    all_pages = engine.scan_all_pages()
    page_names = set(all_pages.keys())

    # 收集所有文件 stem 作为有效目标
    valid_targets = set(page_names)
    for pattern in ['companies/*/wiki/*.md', 'sectors/*/wiki/*.md', 'themes/*/wiki/*.md']:
        for f in engine.wiki_root.glob(pattern):
            valid_targets.add(f.stem)

    broken = []
    total = 0
    for pattern in ['companies/*/wiki/*.md', 'sectors/*/wiki/*.md', 'themes/*/wiki/*.md']:
        for f in engine.wiki_root.glob(pattern):
            content = f.read_text(encoding='utf-8', errors='replace')
            for link in re.findall(r'\[\[(.+?)\]\]', content):
                total += 1
                if link not in valid_targets:
                    broken.append((str(f.relative_to(engine.wiki_root)), link))

    print(f"扫描 {total} 个链接")
    if broken:
        print(f"发现 {len(broken)} 个断链:")
        for path, link in broken[:30]:
            print(f"  {path}: [[{link}]]")
    else:
        print("所有链接有效")


if __name__ == "__main__":
    main()
