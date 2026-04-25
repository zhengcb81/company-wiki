#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 wiki 页面中的 broken source links

扫描所有 wiki 文件中的 [来源](path) 链接，对于失效的链接：
1. 如果 PDF 存在于项目中，更新为正确的相对路径
2. 如果 PDF 不存在，移除该来源链接行
"""
import os
import re
import glob
from pathlib import Path
from collections import defaultdict

from common import WIKI_ROOT
DRY_RUN = False  # Set to True to only report, not fix


def build_pdf_index():
    """构建所有 PDF 文件的索引"""
    pdf_index = {}
    for pdf in glob.glob(str(WIKI_ROOT / 'companies' / '**' / '*.pdf'), recursive=True):
        basename = os.path.basename(pdf)
        if basename not in pdf_index:
            pdf_index[basename] = []
        pdf_index[basename].append(pdf)
    return pdf_index


def compute_relative_path(from_file, to_file):
    """计算从 wiki 文件到目标文件的正确相对路径"""
    from_dir = os.path.dirname(from_file)
    rel = os.path.relpath(to_file, from_dir)
    # Convert to forward slashes for markdown
    return rel.replace('\\', '/')


def fix_wiki_files(pdf_index, dry_run=False):
    """修复所有 wiki 文件中的 broken links"""
    stats = {
        'files_scanned': 0,
        'links_fixed': 0,
        'links_removed': 0,
        'links_unfixable': 0,
        'files_modified': set(),
    }

    for pattern in ['companies/*/wiki/*.md', 'sectors/*/wiki/*.md', 'themes/*/wiki/*.md']:
        for wiki_file in glob.glob(pattern):
            stats['files_scanned'] += 1
            content = Path(wiki_file).read_text(encoding='utf-8')
            wiki_dir = os.path.dirname(wiki_file)
            new_content = content
            modified = False

            # Find all [来源](path) links
            for match in re.finditer(r'\[来源\]\(([^)]+)\)', content):
                ref = match.group(1)
                resolved = os.path.normpath(os.path.join(wiki_dir, ref))

                if os.path.exists(resolved):
                    continue  # Link is valid

                basename = os.path.basename(ref)

                # Try to find the PDF in the index
                if basename in pdf_index:
                    # Use the first match (could be improved with company matching)
                    actual_path = pdf_index[basename][0]
                    new_ref = compute_relative_path(wiki_file, actual_path)
                    old_link = f'[来源]({ref})'
                    new_link = f'[来源]({new_ref})'
                    new_content = new_content.replace(old_link, new_link)
                    stats['links_fixed'] += 1
                    modified = True
                else:
                    # PDF not found - remove the entire timeline entry's source link line
                    # Find and remove just the [来源](...) line
                    source_line_pattern = r'\n- \[来源\]\(' + re.escape(ref) + r'\)\s*\n'
                    if re.search(source_line_pattern, new_content):
                        new_content = re.sub(source_line_pattern, '\n', new_content)
                        stats['links_removed'] += 1
                        modified = True
                    else:
                        stats['links_unfixable'] += 1

            if modified and not dry_run:
                Path(wiki_file).write_text(new_content, encoding='utf-8')
                stats['files_modified'].add(wiki_file)

    return stats


def main():
    import sys
    global DRY_RUN
    DRY_RUN = '--dry-run' in sys.argv

    print("Building PDF index...")
    pdf_index = build_pdf_index()
    print(f"  Found {len(pdf_index)} unique PDF names, {sum(len(v) for v in pdf_index.values())} total files")

    print(f"\nFixing broken links ({'DRY RUN' if DRY_RUN else 'LIVE RUN'})...")
    stats = fix_wiki_files(pdf_index, dry_run=DRY_RUN)

    print(f"\nResults:")
    print(f"  Files scanned: {stats['files_scanned']}")
    print(f"  Links fixed (path updated): {stats['links_fixed']}")
    print(f"  Links removed (PDF not found): {stats['links_removed']}")
    print(f"  Links unfixable: {stats['links_unfixable']}")
    print(f"  Files modified: {len(stats['files_modified'])}")

    if DRY_RUN:
        print("\n[DRY RUN] No files were modified. Run without --dry-run to apply fixes.")


if __name__ == '__main__':
    main()
