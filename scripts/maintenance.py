#!/usr/bin/env python3
"""
maintenance.py — 知识库统一维护管道

将所有数据清理和质量提升步骤系统化为一个可重复执行的管道。
每个步骤有明确的输入/输出/验证标准。

用法：
    # 完整维护流程（推荐定期执行）
    python scripts/maintenance.py --all

    # 只运行清理步骤
    python scripts/maintenance.py --clean

    # 只运行 LLM 富化步骤（需要 DeepSeek API）
    python scripts/maintenance.py --enrich

    # 只运行质量报告
    python scripts/maintenance.py --report

    # dry-run 模式（预览不执行）
    python scripts/maintenance.py --clean --dry-run

管道步骤：

    Phase 1 — 数据清理（规则驱动，无需 LLM）
      1.1 交叉污染清洗（cleanup_contamination）
      1.2 编码乱码清理（fix_wiki_encoding）
      1.3 标题复制清理（remove_title_dumps）
      1.4 财报标题清理（remove_report_titles）
      1.5 重处理校验（reprocess）

    Phase 2 — LLM 富化（需要 API）
      2.1 核心问题生成（enrich --questions）
      2.2 综合评估生成（enrich --assessments）

    Phase 3 — 质量报告
      3.1 生成质量仪表盘
      3.2 输出统计摘要
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


def run_step(cmd, description, dry_run=False):
    """运行单个维护步骤"""
    print(f"\n{'=' * 60}")
    print(f"  STEP: {description}")
    print(f"  CMD:  {' '.join(cmd)}")
    if dry_run and '--execute' in cmd:
        print(f"  [DRY-RUN] Removing --execute flag")
        cmd = [c for c in cmd if c != '--execute']
        if '--dry-run' not in cmd:
            cmd.append('--dry-run')
    print(f"{'=' * 60}")

    result = subprocess.run(
        cmd,
        cwd=str(WIKI_ROOT),
        capture_output=False,
        text=True
    )
    return result.returncode == 0


def phase_clean(dry_run=False):
    """Phase 1: 数据清理"""
    print("\n" + "#" * 60)
    print("# Phase 1: 数据清理（规则驱动）")
    print("#" * 60)

    steps = [
        (
            [sys.executable, str(SCRIPTS_DIR / "cleanup_contamination.py")]
            + (["--execute"] if not dry_run else []),
            "1.1 交叉污染清洗"
        ),
        (
            [sys.executable, str(SCRIPTS_DIR / "fix_wiki_encoding.py")]
            + (["--execute"] if not dry_run else []),
            "1.2 编码乱码清理"
        ),
        (
            [sys.executable, str(SCRIPTS_DIR / "remove_title_dumps.py")]
            + (["--execute"] if not dry_run else []),
            "1.3 标题复制清理"
        ),
        (
            [sys.executable, str(SCRIPTS_DIR / "remove_report_titles.py")]
            + (["--execute"] if not dry_run else []),
            "1.4 财报标题清理"
        ),
        (
            [sys.executable, str(SCRIPTS_DIR / "reprocess.py"), "--all"]
            + (["--execute"] if not dry_run else []),
            "1.5 重处理校验"
        ),
    ]

    results = {}
    for cmd, desc in steps:
        ok = run_step(cmd, desc, dry_run=False)  # dry_run handled by flag presence
        results[desc] = "OK" if ok else "FAILED"
        if not ok:
            print(f"  WARNING: {desc} returned non-zero, continuing...")

    return results


def phase_enrich():
    """Phase 2: LLM 富化"""
    print("\n" + "#" * 60)
    print("# Phase 2: LLM 富化（需要 DeepSeek API）")
    print("#" * 60)

    steps = [
        (
            [sys.executable, str(SCRIPTS_DIR / "enrich_wiki.py"), "--questions"],
            "2.1 核心问题生成"
        ),
        (
            [sys.executable, str(SCRIPTS_DIR / "enrich_wiki.py"), "--assessments"],
            "2.2 综合评估生成"
        ),
    ]

    results = {}
    for cmd, desc in steps:
        ok = run_step(cmd, desc)
        results[desc] = "OK" if ok else "FAILED"
        if not ok:
            print(f"  WARNING: {desc} returned non-zero, continuing...")

    return results


def phase_report():
    """Phase 3: 质量报告"""
    print("\n" + "#" * 60)
    print("# Phase 3: 质量报告")
    print("#" * 60)

    report_path = str(WIKI_ROOT / "docs" / "quality_report.md")
    ok = run_step(
        [sys.executable, str(SCRIPTS_DIR / "quality_dashboard.py"),
         "--output", report_path],
        "3.1 生成质量仪表盘"
    )

    # 读取并输出摘要
    if Path(report_path).exists():
        text = Path(report_path).read_text(encoding="utf-8")
        lines = text.split("\n")
        for line in lines[:20]:
            print(line)

    return {"3.1 质量报告": "OK" if ok else "FAILED"}


def main():
    parser = argparse.ArgumentParser(description="知识库统一维护管道")
    parser.add_argument("--all", action="store_true",
                        help="运行完整维护流程（清理 + 富化 + 报告）")
    parser.add_argument("--clean", action="store_true",
                        help="只运行清理步骤")
    parser.add_argument("--enrich", action="store_true",
                        help="只运行 LLM 富化步骤")
    parser.add_argument("--report", action="store_true",
                        help="只生成质量报告")
    parser.add_argument("--dry-run", action="store_true",
                        help="清理步骤只预览不执行")
    args = parser.parse_args()

    if not any([args.all, args.clean, args.enrich, args.report]):
        parser.print_help()
        print("\n提示: 使用 --all 运行完整维护流程")
        sys.exit(1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"  知识库维护管道 — {now}")
    print(f"  dry-run={args.dry_run}")
    print("=" * 60)

    all_results = {}

    if args.clean or args.all:
        all_results.update(phase_clean(dry_run=args.dry_run))

    if args.enrich or args.all:
        all_results.update(phase_enrich())

    if args.report or args.all:
        all_results.update(phase_report())

    # 输出总结
    print("\n" + "=" * 60)
    print("  维护管道执行摘要")
    print("=" * 60)
    for step, status in all_results.items():
        marker = "OK" if status == "OK" else "FAIL"
        print(f"  [{marker}] {step}")

    failed = sum(1 for s in all_results.values() if s == "FAILED")
    if failed:
        print(f"\n  {failed} 步骤失败，请检查日志")
    else:
        print(f"\n  所有步骤完成")


if __name__ == "__main__":
    main()
