"""
scripts/cleanup_deprecated.py — 清理已弃用的脚本

删除 scripts/models/ 和 tests/archive/ 中的文件。

用法：
  python scripts/cleanup_deprecated.py --plan      # 只规划，不执行
  python scripts/cleanup_deprecated.py --apply     # 执行删除
  python scripts/cleanup_deprecated.py --apply --dry-run  # 模拟删除
"""

import argparse
import shutil
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def find_deprecated_files(project_root: Path) -> list[dict]:
    """查找已弃用的文件"""
    deprecated = []

    # scripts/models/ - 已弃用的 Graph 实现
    models_dir = project_root / "scripts" / "models"
    if models_dir.exists():
        for f in models_dir.rglob("*"):
            if f.is_file() and f.name != "__init__.py":
                deprecated.append({
                    "path": str(f.relative_to(project_root)),
                    "reason": "scripts/models/ 已弃用，被 scripts/graph.py 替代",
                    "safe_to_delete": True,
                })

    # tests/archive/ - 归档的测试
    archive_dir = project_root / "tests" / "archive"
    if archive_dir.exists():
        for f in archive_dir.rglob("*"):
            if f.is_file():
                deprecated.append({
                    "path": str(f.relative_to(project_root)),
                    "reason": "归档的测试文件，不再使用",
                    "safe_to_delete": True,
                })

    return deprecated


def verify_no_production_calls(project_root: Path, files: list[dict]) -> list[dict]:
    """验证文件没有生产调用"""
    verified = []

    for file_info in files:
        file_path = Path(file_info["path"])
        module_name = file_path.stem

        # 检查是否有其他文件通过 import 引用
        has_import_references = False
        for py_file in project_root.rglob("*.py"):
            if py_file == file_path:
                continue
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                # 检查是否有实际的 import 语句
                if f"from.*models.*{module_name}" in content or f"import.*models.*{module_name}" in content:
                    has_import_references = True
                    break
            except Exception:
                continue

        file_info["has_references"] = has_import_references
        if not has_import_references:
            file_info["safe_to_delete"] = True
        else:
            file_info["safe_to_delete"] = False
            file_info["reason"] += " (有 import 引用，需进一步检查)"

        verified.append(file_info)

    return verified


def cleanup_deprecated(project_root: Path, files: list[dict], dry_run: bool = True) -> dict:
    """清理已弃用的文件"""
    results = {
        "total": len(files),
        "deleted": 0,
        "skipped": 0,
        "errors": [],
    }

    for file_info in files:
        if not file_info["safe_to_delete"]:
            results["skipped"] += 1
            continue

        file_path = project_root / file_info["path"]
        if not file_path.exists():
            results["skipped"] += 1
            continue

        try:
            if not dry_run:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
            results["deleted"] += 1
        except Exception as e:
            results["errors"].append(f"{file_info['path']}: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="清理已弃用的脚本")
    parser.add_argument("--plan", action="store_true", help="只规划，不执行")
    parser.add_argument("--apply", action="store_true", help="执行删除")
    parser.add_argument("--dry-run", action="store_true", help="模拟删除")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    # 查找已弃用文件
    print("查找已弃用文件...")
    deprecated = find_deprecated_files(project_root)
    print(f"发现 {len(deprecated)} 个已弃用文件")

    # 验证没有生产调用
    print("\n验证没有生产调用...")
    verified = verify_no_production_calls(project_root, deprecated)

    safe_to_delete = [f for f in verified if f["safe_to_delete"]]
    has_references = [f for f in verified if f["has_references"]]

    print(f"安全删除: {len(safe_to_delete)}")
    print(f"有引用: {len(has_references)}")

    # 显示文件列表
    print("\n待删除文件:")
    for f in safe_to_delete:
        print(f"  - {f['path']}: {f['reason']}")

    if has_references:
        print("\n有引用文件（需进一步检查）:")
        for f in has_references:
            print(f"  - {f['path']}: {f['reason']}")

    # 执行删除
    if args.apply or args.dry_run:
        print("\n执行清理...")
        results = cleanup_deprecated(project_root, safe_to_delete, dry_run=args.dry_run)

        print(f"总计: {results['total']}")
        print(f"已删除: {results['deleted']}")
        print(f"跳过: {results['skipped']}")
        if results["errors"]:
            print(f"错误: {len(results['errors'])}")
            for err in results["errors"]:
                print(f"  - {err}")

        if args.dry_run:
            print("\n[DRY-RUN] 未实际执行")


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
