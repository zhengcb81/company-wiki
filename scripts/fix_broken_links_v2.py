#!/usr/bin/env python3
"""一次性 fix: themes 等多个 wiki 里指向 中密控股/中微公司 的 broken_link，
通过文件名在公司 raw 目下做模糊匹配（lowercase）找真实路径。"""

import re
import os
from pathlib import Path

WIKI_ROOT = Path(".")
fix_targets = [
    ("themes/高端制造/wiki/高端制造.md", "中密控股"),
    ("themes/高端制造/wiki/高端制造.md", "中微公司"),
    ("themes/AI产业链/wiki/AI产业链.md", None),
    ("themes/半导体国产替代/wiki/半导体国产替代.md", None),
    ("themes/半导体国产替代/wiki/市场与需求.md", None),
    ("themes/半导体国产替代/wiki/资本投入.md", None),
    ("themes/半导体国产替代/wiki/设备国产化.md", None),
    ("themes/高端制造/wiki/技术突破.md", None),
    ("themes/高端制造/wiki/政策支持.md", None),
    ("sectors/半导体设备/wiki/半导体设备.md", None),
    ("sectors/刻蚀设备/wiki/刻蚀设备.md", None),
    ("sectors/光刻设备/wiki/光刻设备.md", None),
    ("sectors/封测/wiki/封测.md", None),
]

# Build full companies/ raw index
all_files_index = {}
for f in WIKI_ROOT.joinpath("companies").rglob("*"):
    if f.is_file():
        all_files_index[f.name.lower()] = str(f).replace("\\", "/")

print(f"cached {len(all_files_index)} files under companies/")

total_fixed = 0
total_skipped_list = []

for wiki_path, hint in fix_targets:
    p = WIKI_ROOT / wiki_path
    if not p.exists():
        continue
    wiki_dir = p.parent
    content = p.read_text(encoding="utf-8")

    # match [来源](xxx companies/[name] yyy) 这类带 companies/ 路径的 link
    pattern = re.compile(r"\[来源\]\(([^)]+companies/[^)]+)\)")
    fixed = 0
    skipped = []

    def fix(m):
        global fixed
        ref = m.group(1)
        # 只处理指向 companies/ 的 link
        if "companies/" not in ref:
            skipped.append(ref)
            return m.group(0)
        fname_match = re.search(r"([^/]+)$", ref)
        if not fname_match:
            skipped.append(ref)
            return m.group(0)
        fname = fname_match.group(1)
        target = all_files_index.get(fname.lower())
        if target:
            rel = os.path.relpath(target, str(wiki_dir)).replace("\\", "/")
            return f"[来源]({rel})"
        # 也试 不带正反括号 同名版本
        # 试加/剥 .pdf/.PDF 后缀
        for alt in (
            fname.replace(".pdf", ".PDF"),
            fname.replace(".PDF", ".pdf"),
            fname + ".pdf",
            fname + ".md",
            fname + ".jsonl",
        ):
            target = all_files_index.get(alt.lower())
            if target:
                rel = os.path.relpath(target, str(wiki_dir)).replace("\\", "/")
                return f"[来源]({rel})"
        skipped.append(ref)
        return m.group(0)

    # state closure workaround：用 shared list
    state = {"fixed": 0}

    def fix_state(m):
        ref = m.group(1)
        if "companies/" not in ref:
            skipped.append(ref)
            return m.group(0)
        fname_match = re.search(r"([^/]+)$", ref)
        if not fname_match:
            skipped.append(ref)
            return m.group(0)
        fname = fname_match.group(1)
        target = all_files_index.get(fname.lower())
        if target:
            rel = os.path.relpath(target, str(wiki_dir)).replace("\\", "/")
            state["fixed"] += 1
            return f"[来源]({rel})"
        for alt in (
            fname.replace(".pdf", ".PDF"),
            fname.replace(".PDF", ".pdf"),
            fname + ".pdf",
            fname + ".md",
            fname + ".jsonl",
        ):
            target = all_files_index.get(alt.lower())
            if target:
                rel = os.path.relpath(target, str(wiki_dir)).replace("\\", "/")
                state["fixed"] += 1
                return f"[来源]({rel})"
        skipped.append(ref)
        return m.group(0)

    content_new = pattern.sub(fix_state, content)
    if state["fixed"]:
        p.write_text(content_new, encoding="utf-8")
    print(f"{wiki_path}: fixed {state['fixed']}, skipped {len(skipped)}")
    total_fixed += state["fixed"]
    total_skipped_list.extend([(wiki_path, s) for s in skipped])

print()
print(f"TOTAL fixed: {total_fixed}")
print(f"TOTAL skipped: {len(total_skipped_list)}")
for path, s in total_skipped_list[:10]:
    print(f"  {path}: {s}")
