#!/usr/bin/env python3
"""
snapshot_manifest.py — 生成项目快照 manifest

为代码、配置、wiki、测试生成 SHA-256 哈希清单。
不包含敏感内容（.env、raw 数据、.state DB）。

用法：
    python scripts/snapshot_manifest.py                    # 输出到 stdout
    python scripts/snapshot_manifest.py -o manifest.json   # 输出到文件
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT


def sha256_file(path: Path) -> str:
    """计算文件的 SHA-256"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (OSError, PermissionError):
        return "INACCESSIBLE"
    return h.hexdigest()


def git_info() -> dict:
    """获取当前 Git 状态"""
    info = {}
    try:
        info["head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=WIKI_ROOT, text=True
        ).strip()
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=WIKI_ROOT, text=True
        ).strip()
    except Exception:
        info["head"] = "UNKNOWN"
        info["branch"] = "UNKNOWN"
    return info


def scan_category(name: str, root: Path, patterns: list[str], exclude: list[str] = None) -> dict:
    """扫描一类文件，返回 manifest 条目"""
    exclude = exclude or []
    files = {}
    for pattern in patterns:
        for f in root.glob(pattern):
            if not f.is_file():
                continue
            rel = str(f.relative_to(WIKI_ROOT)).replace("\\", "/")
            # 排除敏感文件
            if any(ex in rel for ex in exclude):
                continue
            files[rel] = {
                "sha256": sha256_file(f),
                "size": f.stat().st_size,
            }
    return {
        "name": name,
        "file_count": len(files),
        "total_size": sum(f["size"] for f in files.values()),
        "files": files,
    }


def build_manifest(include_files: bool = False) -> dict:
    """构建完整 manifest"""
    git = git_info()
    categories = {}

    # 代码
    categories["scripts"] = scan_category(
        "scripts", WIKI_ROOT, ["scripts/*.py"]
    )

    # 测试
    categories["tests"] = scan_category(
        "tests", WIKI_ROOT, ["tests/**/*.py"]
    )

    # 配置
    categories["config"] = scan_category(
        "config", WIKI_ROOT,
        ["*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg"],
        exclude=[".env"]
    )

    # 规划文档
    categories["planning"] = scan_category(
        "planning", WIKI_ROOT,
        ["task_plan.md", "findings.md", "progress.md", "CLAUDE.md", "log.md"]
    )

    # wiki 页面（只统计数量和大小，不逐文件哈希以减少输出）
    wiki_files = list(WIKI_ROOT.rglob("companies/*/wiki/*.md"))
    wiki_sector = list(WIKI_ROOT.rglob("sectors/*/wiki/*.md"))
    categories["wiki"] = {
        "name": "wiki",
        "file_count": len(wiki_files) + len(wiki_sector),
        "total_size": sum(f.stat().st_size for f in wiki_files + wiki_sector),
        "files": {} if not include_files else {
            str(f.relative_to(WIKI_ROOT)).replace("\\", "/"): {
                "sha256": sha256_file(f),
                "size": f.stat().st_size,
            }
            for f in wiki_files + wiki_sector
        },
    }

    # .state（只记录存在性和大小，不包含内容）
    state_dir = WIKI_ROOT / ".state"
    state_info = {"exists": state_dir.exists(), "files": {}}
    if state_dir.exists():
        for f in state_dir.iterdir():
            if f.is_file():
                state_info["files"][f.name] = {
                    "size": f.stat().st_size,
                    "sha256": sha256_file(f),
                }
    categories["state"] = state_info

    # 汇总
    total_files = sum(c.get("file_count", 0) for c in categories.values())
    total_size = sum(c.get("total_size", 0) for c in categories.values())

    return {
        "generated_at": datetime.now().isoformat(),
        "tool": "snapshot_manifest.py",
        "git": git,
        "summary": {
            "total_files": total_files,
            "total_size_bytes": total_size,
        },
        "categories": categories,
    }


def main():
    parser = argparse.ArgumentParser(description="生成项目快照 manifest")
    parser.add_argument("-o", "--output", type=str, help="输出文件路径")
    parser.add_argument("--include-files", action="store_true",
                        help="在 manifest 中包含每个文件的哈希（会增大输出）")
    args = parser.parse_args()

    manifest = build_manifest(include_files=args.include_files)
    output = json.dumps(manifest, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output, encoding="utf-8")
        print(f"Manifest 写入: {out_path}")
        print(f"文件数: {manifest['summary']['total_files']}")
        print(f"总大小: {manifest['summary']['total_size_bytes']:,} bytes")
    else:
        print(output)


if __name__ == "__main__":
    main()
