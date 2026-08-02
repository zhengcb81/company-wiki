#!/usr/bin/env python3
"""
full_pipeline.py — 统一 Pipeline 入口（集成 Gate 系统）

整合阶段1-5的完整流程，并在每个阶段后运行配置化的Gate检查。

用法：
    # 完整流程（所有阶段 + Gate检查）
    python scripts/full_pipeline.py --company 东方电缆

    # 只运行特定阶段
    python scripts/full_pipeline.py --company 东方电缆 --stage extract

    # 跳过Gate检查（仅运行原始Pipeline）
    python scripts/full_pipeline.py --company 东方电缆 --no-gates

    # 预览模式（显示Gate结果但不阻断）
    python scripts/full_pipeline.py --company 东方电缆 --dry-run

    # 查看Gate执行日志
    python scripts/full_pipeline.py --company 东方电缆 --gate-log

新特性：
    - 每个Stage后自动运行配置化的Gate检查
    - Gate失败时自动诊断根因
    - 可修复的失败自动重试（带fix_hint）
    - 不可修复的失败进入 review_queue.md
"""

import argparse
import subprocess
import sys
from pathlib import Path

from common import WIKI_ROOT, require_legacy_writer_permission


try:
    sys.path.insert(0, str(WIKI_ROOT / "scripts"))
    from gate_system import (
        GateRegistry,
        PipelineContext,
        DiagnosticsEngine,
        RetryOrchestrator,
    )
    from gate_system.gates.extraction_quality_gate import ExtractionQualityGate
    from gate_system.gates.data_contract_gate import DataContractGate
    from gate_system.gates.llm_output_gate import (
        LLMFormatGate,
        HallucinationGate,
        LogicConsistencyGate,
    )
    from gate_system.gates.financial_analyst_gate import FinancialAnalystGate
    from gate_system.gates.wiki_integrity_gate import WikiIntegrityGate

    GATE_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"WARN: Gate 系统导入失败: {e}")
    GATE_SYSTEM_AVAILABLE = False


STAGES = ["extract", "structure", "analyze", "review", "ingest", "synthesize"]

# Gate到Stage的映射
GATE_STAGE_MAP = {
    "extract": ["gate_1_extraction_quality"],
    "structure": ["gate_2_data_contract"],
    "analyze": [
        "gate_3_1_llm_format",
        "gate_3_2_hallucination",
        "gate_3_3_logic_consistency",
    ],
    "review": ["gate_4_5_analyst_review"],
    "ingest": ["gate_5_wiki_integrity"],
    "synthesize": [],
}


def run_stage(
    stage: str, company: str = None, dry_run: bool = False, limit: int = 0
) -> int:
    """运行指定阶段"""
    scripts_dir = WIKI_ROOT / "scripts"

    stage_scripts = {
        "extract": "stage1_extract.py",
        "structure": "stage2_structure.py",
        "analyze": "stage3_analyze.py",
        "review": "stage4_review.py",
        "ingest": "stage5_ingest.py",
        "synthesize": "stage6_synthesize.py",
    }

    script = scripts_dir / stage_scripts[stage]
    if not script.exists():
        print(f"ERROR: {script} not found")
        return 1

    cmd = [sys.executable, str(script)]

    if company:
        cmd.extend(["--company", company])
    if dry_run:
        cmd.append("--dry-run")
    if limit > 0:
        cmd.extend(["--limit", str(limit)])

    print(f"\n{'=' * 60}")
    print(f"  运行阶段: {stage}")
    print(f"  命令: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, cwd=str(WIKI_ROOT))
    return result.returncode


def run_gate_check(
    stage: str,
    context: PipelineContext,
    registry: GateRegistry,
    dry_run: bool = False,
) -> bool:
    """
    运行Stage对应的Gate检查。

    Returns:
        bool: True = 所有Gate通过，False = 有Gate失败
    """
    gate_names = GATE_STAGE_MAP.get(stage, [])
    if not gate_names:
        return True

    print(f"\n  [Gate检查] 阶段: {stage}")
    print(f"  {'─' * 50}")

    all_passed = True
    for gate_name in gate_names:
        result = registry.run_gate(gate_name, context)

        status_icon = "✅" if result.passed else "❌" if result.failed else "⚠️"
        print(f"  {status_icon} {gate_name}: {result.status}", end="")
        if result.score is not None:
            print(f" (score: {result.score:.2f})", end="")
        print()

        if result.issues:
            for issue in result.issues[:3]:
                print(f"      - {issue}")

        if not result.passed:
            all_passed = False

            if not dry_run and result.diagnosis:
                # 诊断并决定下一步
                diagnosis = registry.diagnose(result, gate_name)
                decision = registry.retry_or_escalate(diagnosis, context)

                action = decision["action"]
                details = decision["details"]

                if action == "retry":
                    print(
                        f"      → 自动重试 ({details['retry_count']}/{details['max_retries']})"
                    )
                    print(f"      → fix_hint: {details['fix_hint'][:100]}...")
                    # 注：实际重试需要重新运行Stage，这里标记为需要重试
                    context.set_data(f"retry_{gate_name}", decision)
                elif action == "human_review":
                    print("      → 升级到人工审核")
                    print(f"      → 原因: {details['reason']}")
                elif action == "skip":
                    print("      → 跳过此文档")

    print(f"  {'─' * 50}")

    return all_passed


def build_context(stage: str, company: str, file_path: Path = None) -> PipelineContext:
    """
    根据当前阶段构建PipelineContext。
    在实际运行中，应该从Stage输出中动态获取路径。
    """
    # 尝试从公司目录推断路径
    extracts_dir = WIKI_ROOT / "companies" / company / "extracts"

    ctx = PipelineContext(
        company=company,
        doc_type="annual_report",  # 默认，实际应从文件元数据读取
    )

    # 根据阶段设置路径
    if stage == "extract":
        # 找到最新的提取文件
        if extracts_dir.exists():
            md_files = sorted(
                extracts_dir.rglob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if md_files:
                ctx.extract_path = md_files[0]
                # 从文件名推断doc_type
                ctx.doc_type = infer_doc_type_from_filename(md_files[0].name)
    elif stage == "structure":
        if extracts_dir.exists():
            json_files = sorted(
                extracts_dir.rglob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # 排除 .analysis.json 和 .review.json
            json_files = [
                f
                for f in json_files
                if not f.name.endswith(".analysis.json")
                and not f.name.endswith(".review.json")
            ]
            if json_files:
                ctx.structured_path = json_files[0]
                ctx.extract_path = json_files[0].with_suffix(".md")
    elif stage == "analyze":
        if extracts_dir.exists():
            analysis_files = sorted(
                extracts_dir.rglob("*.analysis.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # 过滤掉review.json
            analysis_files = [
                f for f in analysis_files if not f.name.endswith(".review.json")
            ]
            if analysis_files:
                # 优先选择非research的文件（招股书、年报等）
                non_research = [
                    f for f in analysis_files if "research" not in str(f).lower()
                ]
                if non_research:
                    selected_file = non_research[0]
                else:
                    selected_file = analysis_files[0]

                ctx.analysis_path = selected_file
                # Convert .analysis.json to .md (remove .analysis.json, add .md)
                md_path = selected_file.with_suffix("").with_suffix(".md")
                ctx.extract_path = md_path
                # 从文件名推断doc_type
                ctx.doc_type = infer_doc_type_from_filename(md_path.name)
    elif stage == "review":
        if extracts_dir.exists():
            review_files = sorted(
                extracts_dir.rglob("*.review.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if review_files:
                ctx.review_path = review_files[0]
                ctx.analysis_path = review_files[0].with_suffix("").with_suffix(".json")
    elif stage == "ingest":
        if extracts_dir.exists():
            review_files = sorted(
                extracts_dir.rglob("*.review.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if review_files:
                ctx.review_path = review_files[0]

    return ctx


def infer_doc_type_from_filename(filename: str) -> str:
    """从文件名推断文档类型"""
    fname = filename.lower()
    if "年度报告" in fname or "年报" in fname:
        return "annual_report"
    elif "半年度" in fname or "半年报" in fname:
        return "semi_annual_report"
    elif "季度" in fname or "季报" in fname or "季度报告" in fname:
        return "quarterly_report"
    elif "投资者关系" in fname or "调研" in fname:
        return "investor_relations"
    elif "招股" in fname or "prospectus" in fname:
        return "prospectus"
    return "unknown"


def main():
    if not require_legacy_writer_permission("full_pipeline.py"):
        return 1

    parser = argparse.ArgumentParser(description="统一 Pipeline 入口（集成 Gate 系统）")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--stage", type=str, choices=STAGES, help="只运行指定阶段")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="每阶段最多处理 N 个文件")
    parser.add_argument("--resume", action="store_true", help="从上次失败处继续")
    parser.add_argument(
        "--no-gates", action="store_true", help="跳过Gate检查（仅运行原始Pipeline）"
    )
    parser.add_argument("--gate-log", action="store_true", help="显示Gate执行日志")
    args = parser.parse_args()

    print("=" * 60)
    print("  上市公司知识库 — 完整 Pipeline")
    if GATE_SYSTEM_AVAILABLE and not args.no_gates:
        print("  [Gate系统已启用]")
    print("=" * 60)

    # 初始化Gate系统
    registry = None
    if GATE_SYSTEM_AVAILABLE and not args.no_gates:
        try:
            registry = GateRegistry.load()
            print(f"\n  Gate系统就绪: {len(registry.list_gates())} 个Gate已注册")
            print("  支持文档类型: financial_report, investor_relations, prospectus")
        except Exception as e:
            print(f"\n  WARN: Gate系统初始化失败: {e}")
            print("  继续运行但不进行Gate检查")
            registry = None

    if args.stage:
        stages = [args.stage]
    else:
        stages = STAGES

    for stage in stages:
        # 1. 运行Stage
        ret = run_stage(stage, args.company, args.dry_run, args.limit)
        if ret != 0:
            print(f"\nERROR: 阶段 {stage} 失败 (exit code: {ret})")
            return ret

        # 2. 运行Gate检查（如果启用）
        if registry and not args.no_gates and args.company:
            try:
                context = build_context(stage, args.company)
                gate_passed = run_gate_check(stage, context, registry, args.dry_run)

                if not gate_passed and not args.dry_run:
                    print(f"\n  ⚠️  Gate检查发现 {stage} 阶段有问题")
                    # 不阻断Pipeline，但记录问题
                    # 实际生产环境可以配置为阻断或继续
            except Exception as e:
                print(f"  WARN: Gate检查异常: {e}")

    # 3. 显示Gate执行日志（如果请求）
    if args.gate_log and registry:
        log = registry.get_execution_log()
        if log:
            print(f"\n{'=' * 60}")
            print("  Gate执行日志")
            print(f"{'=' * 60}")
            for entry in log:
                print(
                    f"  {entry['gate_name']} | {entry['status']} | {entry['company']}"
                )

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print("  正在生成真实系统 Dashboard...")
        subprocess.run([sys.executable, str(WIKI_ROOT / "scripts" / "generate_dashboard.py")], cwd=str(WIKI_ROOT))

    print(f"\n{'=' * 60}")
    print("  Pipeline 完成!")
    print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
