#!/usr/bin/env python3
"""
audit_config.py — 审计配置读取

扫描所有配置读取点，生成审计报告。

用法：
    python scripts/audit_config.py --scan    # 扫描配置读取
    python scripts/audit_config.py --report  # 生成报告
"""

import argparse
import re
from pathlib import Path

WIKI_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = WIKI_ROOT / "scripts"


def scan_config_reads() -> dict:
    """扫描所有配置读取"""
    results = {
        "yaml.safe_load": [],
        "Config.load": [],
        "RulesConfig": [],
        "graph.yaml": [],
        "other": [],
    }

    # 扫描所有Python文件
    for py_file in SCRIPTS_DIR.glob("**/*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # 检查yaml.safe_load
        for match in re.finditer(r"yaml\.safe_load", content):
            line_num = content[: match.start()].count("\n") + 1
            line = content.split("\n")[line_num - 1].strip()
            results["yaml.safe_load"].append(
                {
                    "file": str(py_file.relative_to(WIKI_ROOT)),
                    "line": line_num,
                    "code": line,
                }
            )

        # 检查Config.load
        for match in re.finditer(r"Config\.load", content):
            line_num = content[: match.start()].count("\n") + 1
            line = content.split("\n")[line_num - 1].strip()
            results["Config.load"].append(
                {
                    "file": str(py_file.relative_to(WIKI_ROOT)),
                    "line": line_num,
                    "code": line,
                }
            )

        # 检查RulesConfig
        for match in re.finditer(r"RulesConfig", content):
            line_num = content[: match.start()].count("\n") + 1
            line = content.split("\n")[line_num - 1].strip()
            results["RulesConfig"].append(
                {
                    "file": str(py_file.relative_to(WIKI_ROOT)),
                    "line": line_num,
                    "code": line,
                }
            )

        # 检查graph.yaml
        for match in re.finditer(r"graph\.yaml|graph\.yml", content):
            line_num = content[: match.start()].count("\n") + 1
            line = content.split("\n")[line_num - 1].strip()
            results["graph.yaml"].append(
                {
                    "file": str(py_file.relative_to(WIKI_ROOT)),
                    "line": line_num,
                    "code": line,
                }
            )

    return results


def generate_report(results: dict):
    """生成审计报告"""
    report = """# 配置读取审计报告

**生成时间**: 2026-05-18

---

## 概览

| 配置读取方式 | 使用次数 |
|--------------|----------|
"""

    for method, reads in results.items():
        report += f"| {method} | {len(reads)} |\n"

    report += "\n---\n\n## 详细信息\n\n"

    for method, reads in results.items():
        report += f"### {method}\n\n"

        if not reads:
            report += "无使用\n\n"
            continue

        report += "| 文件 | 行号 | 代码 |\n"
        report += "|------|------|------|\n"

        for read in reads[:20]:  # 限制显示数量
            file = read["file"]
            line = read["line"]
            code = read["code"][:50]
            report += f"| {file} | {line} | `{code}` |\n"

        if len(reads) > 20:
            report += f"| ... | ... | 还有 {len(reads) - 20} 条 |\n"

        report += "\n"

    # 保存报告
    report_path = WIKI_ROOT / "docs" / "config_audit_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"审计报告已保存: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="审计配置读取")
    parser.add_argument("--scan", action="store_true", help="扫描配置读取")
    parser.add_argument("--report", action="store_true", help="生成报告")
    args = parser.parse_args()

    if args.scan or args.report:
        results = scan_config_reads()

        # 打印摘要
        print("\n配置读取审计:")
        print("=" * 60)
        for method, reads in results.items():
            print(f"  {method}: {len(reads)} 次")

        if args.report:
            generate_report(results)
    else:
        # 默认扫描
        results = scan_config_reads()
        print("\n配置读取审计:")
        print("=" * 60)
        for method, reads in results.items():
            print(f"  {method}: {len(reads)} 次")


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
