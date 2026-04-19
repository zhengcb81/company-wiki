#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 wikilinks 断链脚本

wikilinks 格式 [[EntityName]] 引用实体名，应该能匹配到对应实体的 wiki 页面。
"""
import re
from pathlib import Path

def check_wikilinks():
    wiki_root = Path('.')
    entities = set()

    # Get all entity directories (companies, sectors, themes)
    for entity_type in ['companies', 'sectors', 'themes']:
        type_dir = wiki_root / entity_type
        if type_dir.exists():
            for entity_dir in type_dir.iterdir():
                if entity_dir.is_dir():
                    entities.add(entity_dir.name)

    print(f"Total entities: {len(entities)}")
    print(f"Sample entities: {list(entities)[:10]}")

    # Find all wikilinks in wiki files
    broken = []
    checked = set()

    for pattern in ['companies/**/*.md', 'sectors/**/*.md', 'themes/**/*.md']:
        for p in wiki_root.glob(pattern):
            if 'wiki' not in str(p) and p.name != '_产业链导航.md':
                continue
            try:
                content = p.read_text(encoding='utf-8', errors='replace')
                for match in re.finditer(r'\[\[([^\]]+)\]\]', content):
                    link = match.group(1).strip()
                    key = (str(p), link)
                    if key in checked:
                        continue
                    checked.add(key)
                    if link not in entities:
                        broken.append((str(p), link))
            except Exception as e:
                print(f"Error checking {p}: {e}")

    print(f"Total wikilinks checked: {len(checked)}")

    if broken:
        print(f"\nFound {len(broken)} broken links:")
        by_file = {}
        for path, link in broken:
            if path not in by_file:
                by_file[path] = []
            by_file[path].append(link)

        for path, links in sorted(by_file.items())[:30]:
            print(f"\n  {path}:")
            for link in links[:15]:
                print(f"    [[{link}]]")
            if len(links) > 15:
                print(f"    ... and {len(links) - 15} more")
    else:
        print("\nNo broken links found - all wikilinks are valid!")

    return len(broken) == 0

if __name__ == "__main__":
    success = check_wikilinks()
    exit(0 if success else 1)