"""
scripts/migrate_raw.py — Raw 文件全量注册

扫描 companies/ 下所有非 wiki 文件，注册到 SourceRegistry。

用法：
  python scripts/migrate_raw.py --plan          # 只规划，不执行
  python scripts/migrate_raw.py --apply         # 执行注册
  python scripts/migrate_raw.py --apply --dry-run  # 模拟执行
"""

import argparse
import hashlib
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from company_wiki.migration import (
    EntryClassification,
    MigrationAction,
    MigrationManifest,
    MigrationPlanner,
    verify_manifest_consistency,
)
from company_wiki.source_registry import SourceRegistry


def classify_file(path: Path) -> EntryClassification:
    """分类文件"""
    name = path.name.lower()

    # 年报/季报/半年报
    if any(pattern in name for pattern in ["年报", "季报", "半年报", "annual", "quarterly"]):
        return EntryClassification.VERIFIED

    # 公告
    if any(pattern in name for pattern in ["公告", "announcement"]):
        return EntryClassification.VERIFIED

    # PDF 文件
    if name.endswith(".pdf"):
        return EntryClassification.VERIFIED

    # 新闻文件（有日期）
    if name.endswith(".md") and any(year in name for year in ["2024", "2025", "2026"]):
        return EntryClassification.VERIFIED

    # 其他
    return EntryClassification.UNVERIFIED


def plan_migration(wiki_root: Path) -> MigrationManifest:
    """规划迁移"""
    planner = MigrationPlanner(wiki_root)
    manifest = planner.plan_raw_registration()

    # 更新分类
    for entry in manifest.entries:
        source_path = Path(wiki_root) / entry.source_path
        if source_path.exists():
            entry.classification = classify_file(source_path)

    return manifest


def execute_migration(wiki_root: Path, manifest: MigrationManifest, dry_run: bool = True) -> dict:
    """执行迁移"""
    # 验证清单
    is_consistent, errors = verify_manifest_consistency(manifest)
    if not is_consistent:
        return {"success": False, "errors": errors}

    # 初始化注册表
    db_path = wiki_root / ".state" / "source_registry.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    registry = SourceRegistry(db_path)

    results = {
        "total": len(manifest.entries),
        "registered": 0,
        "skipped": 0,
        "errors": [],
    }

    for entry in manifest.entries:
        if entry.action == MigrationAction.SKIP:
            # 尝试注册
            source_path = Path(wiki_root) / entry.source_path
            if source_path.exists():
                try:
                    if not dry_run:
                        # 计算 content hash
                        h = hashlib.sha256()
                        with open(source_path, "rb") as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                h.update(chunk)
                        content_hash = h.hexdigest()

                        # 注册
                        registry.register(
                            path=source_path,
                            content_hash=content_hash,
                            source_kind=_classify_to_source_kind(entry.classification),
                        )
                        results["registered"] += 1
                    else:
                        results["registered"] += 1
                except Exception as e:
                    results["errors"].append(f"{entry.source_path}: {e}")
            else:
                results["skipped"] += 1

    results["success"] = len(results["errors"]) == 0
    return results


def _classify_to_source_kind(classification: EntryClassification) -> str:
    """将分类映射为 SourceKind"""
    mapping = {
        EntryClassification.VERIFIED: "regulatory",
        EntryClassification.RECOVERABLE: "original_news",
        EntryClassification.UNVERIFIED: "aggregated_news",
    }
    return mapping.get(classification, "aggregated_news")


def main():
    parser = argparse.ArgumentParser(description="Raw 文件全量注册")
    parser.add_argument("--plan", action="store_true", help="只规划，不执行")
    parser.add_argument("--apply", action="store_true", help="执行注册")
    parser.add_argument("--dry-run", action="store_true", help="模拟执行")
    parser.add_argument("--output", "-o", help="输出清单文件路径")
    args = parser.parse_args()

    wiki_root = Path(__file__).parent.parent

    # 规划
    print("扫描 raw 文件...")
    manifest = plan_migration(wiki_root)

    print(f"发现 {len(manifest.entries)} 个文件")
    print(f"  验证通过: {sum(1 for e in manifest.entries if e.classification == EntryClassification.VERIFIED)}")
    print(f"  待验证: {sum(1 for e in manifest.entries if e.classification == EntryClassification.UNVERIFIED)}")

    # 输出清单
    if args.output:
        manifest.save(Path(args.output))
        print(f"清单已保存到: {args.output}")

    # 执行
    if args.apply or args.dry_run:
        print("\n执行注册...")
        results = execute_migration(wiki_root, manifest, dry_run=args.dry_run)

        print(f"总计: {results['total']}")
        print(f"已注册: {results['registered']}")
        print(f"跳过: {results['skipped']}")
        if results["errors"]:
            print(f"错误: {len(results['errors'])}")
            for err in results["errors"][:10]:
                print(f"  - {err}")

        if args.dry_run:
            print("\n[DRY-RUN] 未实际执行")


if __name__ == "__main__":
    main()
