#!/usr/bin/env python3
"""
test_framework.py — 统一测试运行器

运行所有测试，生成测试报告，记录审核日志。

用法：
    python scripts/test_framework.py --suite all          # 运行所有测试
    python scripts/test_framework.py --suite unit         # 运行单元测试
    python scripts/test_framework.py --suite integration  # 运行集成测试
    python scripts/test_framework.py --suite gate         # 运行Gate测试
    python scripts/test_framework.py --company 中微公司    # 测试指定公司
    python scripts/test_framework.py --report             # 生成测试报告
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 项目根目录
WIKI_ROOT = Path(__file__).parent.parent
TEST_RESULTS_DIR = WIKI_ROOT / "docs" / "test_results"
REVIEW_LOG = WIKI_ROOT / "docs" / "review_log.md"


def run_command(cmd: list, timeout: int = 300) -> dict:
    """运行命令并返回结果"""
    try:
        # 设置环境变量以确保UTF-8编码
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WIKI_ROOT),
            env=env,
            encoding="utf-8",
            errors="replace",  # 替换无法解码的字符
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Timeout",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def run_unit_tests() -> dict:
    """运行单元测试"""
    print("\n" + "=" * 60)
    print("  运行单元测试")
    print("=" * 60)

    # 运行pytest
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
    result = run_command(cmd, timeout=120)

    # 解析结果
    test_results = {
        "suite": "unit",
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "output": result["stdout"],
        "errors": result["stderr"],
    }

    # 统计测试数量
    if "passed" in result["stdout"]:
        # 解析 pytest 输出
        lines = result["stdout"].split("\n")
        for line in lines:
            if "passed" in line or "failed" in line or "error" in line:
                test_results["summary"] = line.strip()
                break

    return test_results


def run_integration_tests(company: str = "中微公司") -> dict:
    """运行集成测试（Pipeline端到端）"""
    print("\n" + "=" * 60)
    print(f"  运行集成测试: {company}")
    print("=" * 60)

    # 运行Pipeline
    cmd = [
        sys.executable,
        "scripts/full_pipeline.py",
        "--company",
        company,
        "--limit",
        "1",
        "--no-gates",
    ]
    result = run_command(cmd, timeout=180)

    test_results = {
        "suite": "integration",
        "company": company,
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "output": result["stdout"],
        "errors": result["stderr"],
    }

    return test_results


def run_gate_tests(company: str = "中微公司") -> dict:
    """运行Gate系统测试"""
    print("\n" + "=" * 60)
    print(f"  运行Gate测试: {company}")
    print("=" * 60)

    # 运行Pipeline with gates
    cmd = [
        sys.executable,
        "scripts/full_pipeline.py",
        "--company",
        company,
        "--limit",
        "1",
        "--gate-log",
    ]
    result = run_command(cmd, timeout=180)

    test_results = {
        "suite": "gate",
        "company": company,
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "output": result["stdout"],
        "errors": result["stderr"],
    }

    # 解析Gate结果
    if "gate_3_1_llm_format" in result["stdout"]:
        gate_results = {}
        for gate in [
            "gate_3_1_llm_format",
            "gate_3_2_hallucination",
            "gate_3_3_logic_consistency",
        ]:
            if f"✅ {gate}" in result["stdout"]:
                gate_results[gate] = "passed"
            elif f"❌ {gate}" in result["stdout"]:
                gate_results[gate] = "failed"
            else:
                gate_results[gate] = "skipped"
        test_results["gate_results"] = gate_results

    return test_results


def run_section_discovery_test() -> dict:
    """运行章节发现测试"""
    print("\n" + "=" * 60)
    print("  运行章节发现测试")
    print("=" * 60)

    # 运行章节发现
    cmd = [sys.executable, "scripts/section_discovery.py"]
    result = run_command(cmd, timeout=60)

    test_results = {
        "suite": "section_discovery",
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "output": result["stdout"],
        "errors": result["stderr"],
    }

    return test_results


def run_framework_loader_test() -> dict:
    """运行框架加载器测试"""
    print("\n" + "=" * 60)
    print("  运行框架加载器测试")
    print("=" * 60)

    # 运行框架加载器
    cmd = [sys.executable, "scripts/framework_loader.py"]
    result = run_command(cmd, timeout=60)

    test_results = {
        "suite": "framework_loader",
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "output": result["stdout"],
        "errors": result["stderr"],
    }

    return test_results


def save_test_results(results: list, filename: str = None):
    """保存测试结果到文件"""
    if filename is None:
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    filepath = TEST_RESULTS_DIR / filename

    # 汇总结果
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.get("success", False)),
        "failed": sum(1 for r in results if not r.get("success", False)),
        "results": results,
    }

    # 保存到文件
    filepath.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 同时保存为latest.json
    latest_path = TEST_RESULTS_DIR / "latest.json"
    latest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n测试结果已保存: {filepath}")
    return filepath


def update_review_log(results: list):
    """更新审核日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))
    failed = total - passed

    # 构建日志条目
    log_entry = f"\n## {timestamp} 测试运行\n\n"
    log_entry += f"- 总测试数: {total}\n"
    log_entry += f"- 通过: {passed}\n"
    log_entry += f"- 失败: {failed}\n\n"

    log_entry += "| 测试套件 | 状态 | 说明 |\n"
    log_entry += "|----------|------|------|\n"

    for result in results:
        suite = result.get("suite", "unknown")
        status = "✅ 通过" if result.get("success", False) else "❌ 失败"
        summary = result.get("summary", "")
        log_entry += f"| {suite} | {status} | {summary} |\n"

    log_entry += "\n---\n"

    # 追加到审核日志
    if REVIEW_LOG.exists():
        content = REVIEW_LOG.read_text(encoding="utf-8")
    else:
        content = "# 审核日志\n\n记录所有测试运行和审核结果。\n\n---\n"

    content += log_entry
    REVIEW_LOG.write_text(content, encoding="utf-8")

    print(f"审核日志已更新: {REVIEW_LOG}")


def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("  生成测试报告")
    print("=" * 60)

    # 读取最新的测试结果
    latest_path = TEST_RESULTS_DIR / "latest.json"
    if not latest_path.exists():
        print("没有找到测试结果，请先运行测试")
        return

    data = json.loads(latest_path.read_text(encoding="utf-8"))

    # 生成报告
    report = f"""# 测试报告

**生成时间**: {data["timestamp"]}
**总测试数**: {data["total_tests"]}
**通过**: {data["passed"]}
**失败**: {data["failed"]}

---

## 测试结果详情

"""

    for result in data["results"]:
        status = "✅ 通过" if result.get("success", False) else "❌ 失败"
        report += f"### {result.get('suite', 'unknown')} {status}\n\n"

        if result.get("summary"):
            report += f"**摘要**: {result['summary']}\n\n"

        if result.get("gate_results"):
            report += "**Gate结果**:\n"
            for gate, gate_status in result["gate_results"].items():
                report += f"- {gate}: {gate_status}\n"
            report += "\n"

        if result.get("errors"):
            report += f"**错误**:\n```\n{result['errors'][:500]}\n```\n\n"

    # 保存报告
    report_path = WIKI_ROOT / "docs" / "test_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"测试报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="统一测试运行器")
    parser.add_argument(
        "--suite",
        choices=[
            "all",
            "unit",
            "integration",
            "gate",
            "section_discovery",
            "framework_loader",
        ],
        default="all",
        help="测试套件",
    )
    parser.add_argument("--company", default="中微公司", help="测试公司")
    parser.add_argument("--report", action="store_true", help="生成测试报告")
    args = parser.parse_args()

    # 确保目录存在
    TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.report:
        generate_report()
        return

    print("=" * 60)
    print("  统一测试运行器")
    print("=" * 60)

    results = []

    if args.suite in ["all", "section_discovery"]:
        results.append(run_section_discovery_test())

    if args.suite in ["all", "framework_loader"]:
        results.append(run_framework_loader_test())

    if args.suite in ["all", "unit"]:
        results.append(run_unit_tests())

    if args.suite in ["all", "integration"]:
        results.append(run_integration_tests(args.company))

    if args.suite in ["all", "gate"]:
        results.append(run_gate_tests(args.company))

    # 保存结果
    save_test_results(results)

    # 更新审核日志
    update_review_log(results)

    # 打印汇总
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))
    failed = total - passed

    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    for result in results:
        status = "✅" if result.get("success", False) else "❌"
        print(f"  {status} {result.get('suite', 'unknown')}")

    # 返回状态码
    return 0 if failed == 0 else 1


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main() or 0)
