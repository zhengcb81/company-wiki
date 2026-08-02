#!/usr/bin/env python3
"""
cleanup_log.py — 清理log.md测试污染

移除测试查询记录，保留正常日志。

用法：
    python scripts/cleanup_log.py --dry-run   # 预览要删除的内容
    python scripts/cleanup_log.py --execute   # 执行清理
    python scripts/cleanup_log.py --verify    # 验证清理结果
"""

import argparse
import re
import shutil
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent
LOG_PATH = WIKI_ROOT / "log.md"
BACKUP_PATH = WIKI_ROOT / "log.md.backup"


def identify_test_lines(content: str) -> list:
    """识别测试查询行"""
    lines = content.split("\n")
    test_lines = []

    for i, line in enumerate(lines):
        # 匹配测试查询模式
        if "测试问题" in line and "Query answer saved" in line:
            test_lines.append(i)
        elif (
            re.search(r"测试[一二三四五六七八九十\d]", line)
            and "Query answer saved" in line
        ):
            test_lines.append(i)

    return test_lines


def dry_run():
    """预览要删除的内容"""
    content = LOG_PATH.read_text(encoding="utf-8")
    test_lines = identify_test_lines(content)

    print("=" * 60)
    print("  预览清理")
    print("=" * 60)

    print(f"\n总行数: {len(content.split(chr(10)))}")
    print(f"测试查询行数: {len(test_lines)}")

    print("\n将删除的行:")
    lines = content.split("\n")
    for i in test_lines[:10]:  # 只显示前10行
        print(f"  Line {i + 1}: {lines[i].strip()[:80]}")

    if len(test_lines) > 10:
        print(f"  ... 还有 {len(test_lines) - 10} 行")


def execute():
    """执行清理"""
    # 备份原文件
    shutil.copy2(LOG_PATH, BACKUP_PATH)
    print(f"已备份: {BACKUP_PATH}")

    # 读取内容
    content = LOG_PATH.read_text(encoding="utf-8")
    test_lines = identify_test_lines(content)

    # 移除测试行
    lines = content.split("\n")
    cleaned_lines = [line for i, line in enumerate(lines) if i not in test_lines]

    # 保存清理后的内容
    cleaned_content = "\n".join(cleaned_lines)
    LOG_PATH.write_text(cleaned_content, encoding="utf-8")

    print(f"已清理 {len(test_lines)} 条测试查询")
    print(f"清理前行数: {len(lines)}")
    print(f"清理后行数: {len(cleaned_lines)}")


def verify():
    """验证清理结果"""
    content = LOG_PATH.read_text(encoding="utf-8")
    test_lines = identify_test_lines(content)

    print("=" * 60)
    print("  验证清理结果")
    print("=" * 60)

    if len(test_lines) == 0:
        print("\n✅ 清理成功！没有测试查询记录")
    else:
        print(f"\n❌ 仍有 {len(test_lines)} 条测试查询")

    # 检查备份是否存在
    if BACKUP_PATH.exists():
        print(f"✅ 备份文件存在: {BACKUP_PATH}")
    else:
        print("⚠️ 备份文件不存在")

    # 统计正常日志
    lines = content.split("\n")
    info_lines = [l for l in lines if "INFO" in l]
    print(f"\n正常日志行数: {len(info_lines)}")


def main():
    parser = argparse.ArgumentParser(description="清理log.md测试污染")
    parser.add_argument("--dry-run", action="store_true", help="预览")
    parser.add_argument("--execute", action="store_true", help="执行清理")
    parser.add_argument("--verify", action="store_true", help="验证结果")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.execute:
        execute()
    elif args.verify:
        verify()
    else:
        # 默认预览
        dry_run()


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
