#!/usr/bin/env python3
"""
scheduler.py — 知识库调度器

协调整个知识库的自动化更新流程：
1. 新闻采集 (collect_news)
2. 文件处理 (ingest_v2)
3. 评估更新 (batch_assessment)
4. 矛盾检测 (contradiction_detector)
5. 行业蒸馏 (sector_distiller)
6. 投资判断 (investment_judgment)
7. 交叉验证 (cross_verify)
8. 问题演化 (evolve_questions)
9. 质量仪表盘 (quality_dashboard)
10. 健康检查 (lint)

用法：
    python3 scripts/scheduler.py                    # 执行完整周期
    python3 scripts/scheduler.py --collect-only     # 只采集新闻
    python3 scripts/scheduler.py --ingest-only      # 只处理文件
    python3 scripts/scheduler.py --assess-only      # 只更新评估
    python3 scripts/scheduler.py --evolve-only      # 只执行问题演化
    python3 scripts/scheduler.py --dashboard-only   # 只生成质量仪表盘
    python3 scripts/scheduler.py --lint-only        # 只执行健康检查
    python3 scripts/scheduler.py --company 中微公司  # 只处理指定公司
    python3 scripts/scheduler.py --dry-run          # 只打印不执行
    python3 scripts/scheduler.py --daemon           # 守护模式，按配置自动调度
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from writer_policy import enforce_direct_cli

enforce_direct_cli(__name__, __file__)

import yaml

# Windows 控制台 UTF-8 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from dotenv import load_dotenv

if os.environ.get("PYTHON_DOTENV_DISABLED", "").casefold() not in {"1", "true", "yes"}:
    load_dotenv()

from log_writer import append_log
from graph import Graph
from llm_client import get_llm_client
from review_queue import ReviewQueue

# 导入步骤函数注册表
from scheduler_steps import STEP_RUNNERS


class Scheduler:
    """知识库调度器"""

    def __init__(self, company_filter: Optional[str] = None, dry_run: bool = False):
        self.company_filter = company_filter
        self.dry_run = dry_run
        self.graph = Graph(str(WIKI_ROOT / "graph.yaml"))
        self.llm_client = get_llm_client()
        self.llm_client._timeout = 120  # scheduler tasks may take longer
        self.review_queue = ReviewQueue()
        self.summary: Dict[str, Any] = {}
        self._running = True
        # 加载审核队列配置
        self._load_review_config()

    def _load_review_config(self):
        """加载审核队列配置"""
        config_path = WIKI_ROOT / "config.yaml"
        self.review_config = {
            "enabled": True,
            "auto_approve_low": True,
            "auto_approve_medium": False,
            "auto_approve_high": False,
        }
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                if config and "review_queue" in config:
                    self.review_config.update(config["review_queue"])
            except Exception as e:
                print(f"[WARN] {e}")

    def load_schedule_config(self) -> Dict:
        """从 config.yaml 加载调度配置"""
        try:
            from config import Config

            config = Config.load()
            return {
                "news_collection": config.schedule.news_collection,
                "report_check": config.schedule.report_check,
                "lint": config.schedule.lint,
            }
        except Exception:
            # Fallback: 直接读取 YAML
            config_path = WIKI_ROOT / "config.yaml"
            if not config_path.exists():
                return {}
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config.get("schedule", {})

    def parse_interval(self, interval_str: str) -> timedelta:
        """解析调度间隔字符串"""
        interval_map = {
            "hourly": timedelta(hours=1),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }
        return interval_map.get(interval_str, timedelta(days=1))

    def run_daemon(self):
        """守护模式：按配置自动调度"""
        schedule_config = self.load_schedule_config()
        if not schedule_config:
            print("错误: 无法加载调度配置")
            return

        print("=" * 50)
        print("  知识库调度器 — 守护模式")
        print("=" * 50)
        print("\n调度配置:")
        for task, interval in schedule_config.items():
            print(f"  {task}: {interval}")

        # 设置信号处理
        def signal_handler(sig, frame):
            print("\n\n收到停止信号，正在退出...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)

        # 记录上次执行时间
        last_run = {}

        # 任务映射
        task_steps = {
            "news_collection": ["collect"],
            "report_check": ["ingest"],
            "lint": ["lint", "evolve", "dashboard"],
            "maintenance": [
                "collect",
                "ingest",
                "assess",
                "distill",
                "judgment",
                "detect",
                "evolve",
                "dashboard",
                "lint",
                "consolidate",
            ],
        }

        print("\n守护模式启动。按 Ctrl+C 停止。\n")

        while self._running:
            now = datetime.now()

            for task_name, interval_str in schedule_config.items():
                if not self._running:
                    break

                interval = self.parse_interval(interval_str)
                last = last_run.get(task_name)

                if last is None or (now - last) >= interval:
                    steps = task_steps.get(task_name, [])
                    if not steps:
                        continue

                    print(f"\n[{now.strftime('%Y-%m-%d %H:%M')}] 执行任务: {task_name}")
                    try:
                        self.run(steps)
                        last_run[task_name] = now
                        print(f"  任务 {task_name} 完成")
                    except Exception as e:
                        print(f"  任务 {task_name} 失败: {e}")

            # 休眠 60 秒后检查
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1)

        print("\n守护模式已停止。")

    def run(self, steps: List[str]) -> Dict:
        """
        执行指定的调度步骤。

        Args:
            steps: 步骤列表 ['collect', 'ingest', 'assess', 'detect']

        Returns:
            完整运行摘要
        """
        start_time = datetime.now()
        print("=" * 50)
        print("  知识库调度器")
        print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.company_filter:
            print(f"  过滤条件: 公司 = {self.company_filter}")
        if self.dry_run:
            print("  模式: DRY-RUN (只打印不执行)")
        print("=" * 50)

        results = {}

        for step_name in steps:
            runner = STEP_RUNNERS.get(step_name)
            if runner:
                results[step_name] = runner(self)

        # 生成摘要
        elapsed = (datetime.now() - start_time).total_seconds()
        self.summary = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": int(elapsed),
            "dry_run": self.dry_run,
            "company_filter": self.company_filter,
            "steps": steps,
            "results": results,
        }

        self._print_summary()
        return self.summary

    def _print_summary(self):
        """打印运行摘要"""
        print("\n" + "=" * 50)
        print("  运行摘要")
        print("=" * 50)

        s = self.summary
        print(f"\n  耗时: {s['elapsed_seconds']} 秒")
        print(f"  步骤: {', '.join(s['steps'])}")

        if "collect" in s["results"]:
            r = s["results"]["collect"]
            print("\n  [新闻采集]")
            print(f"    新文章: {r.get('new', 0)}")
            print(f"    重复: {r.get('dup', 0)}")

        if "extract" in s["results"]:
            r = s["results"]["extract"]
            print("\n  [PDF提取]")
            print(f"    成功: {r.get('processed', 0)}")
            print(f"    跳过: {r.get('skipped', 0)}")
            print(f"    错误: {r.get('errors', 0)}")

        if "tag" in s["results"]:
            r = s["results"]["tag"]
            print("\n  [标签化分段]")
            print(f"    成功: {r.get('processed', 0)}")
            print(f"    跳过: {r.get('skipped', 0)}")
            print(f"    错误: {r.get('errors', 0)}")
            print(f"    总段数: {r.get('segments', 0)}")

        if "ingest" in s["results"]:
            r = s["results"]["ingest"]
            print("\n  [文件处理]")
            print(f"    成功: {r.get('processed', 0)}")
            print(f"    新条目: {r.get('entries', 0)}")
            print(f"    错误: {r.get('errors', 0)}")
            if r.get("error_files"):
                for ef in r["error_files"][:3]:
                    print(f"      - {ef}")

        if "assess" in s["results"]:
            r = s["results"]["assess"]
            print("\n  [评估更新]")
            print(f"    成功: {r.get('success', 0)}")
            print(f"    跳过: {r.get('skipped', 0)}")
            print(f"    错误: {r.get('errors', 0)}")

        if "detect" in s["results"]:
            r = s["results"]["detect"]
            print("\n  [矛盾检测]")
            print(f"    潜在矛盾: {r.get('total', 0)}")
            print(f"    高置信度: {r.get('high_confidence', 0)}")
            by_type = r.get("by_type", {})
            for ctype, count in sorted(by_type.items()):
                print(f"      - {ctype}: {count}")

        if "distill" in s["results"]:
            r = s["results"]["distill"]
            print("\n  [行业蒸馏]")
            print(f"    行业数: {r.get('processed', 0)}")
            print(f"    成功: {r.get('success', 0)}")
            print(f"    新增条目: {r.get('added', 0)}")

        if "judgment" in s["results"]:
            r = s["results"]["judgment"]
            print("\n  [投资判断]")
            print(f"    公司数: {r.get('success', 0)}")
            print(f"    跳过: {r.get('skipped', 0)}")
            print(f"    数据条目: {r.get('total_metrics', 0)}")

        if "verify" in s["results"]:
            r = s["results"]["verify"]
            print("\n  [交叉验证]")
            print(f"    条目数: {r.get('total', 0)}")
            print(f"    事件数: {r.get('clusters', 0)}")
            print(f"    高可信度: {r.get('high', 0)}")
            print(f"    中可信度: {r.get('medium', 0)}")
            print(f"    待验证: {r.get('low', 0)}")

        if "evolve" in s["results"]:
            r = s["results"]["evolve"]
            print("\n  [问题演化]")
            print(f"    总问题数: {r.get('total_questions', 0)}")
            print(f"    活跃: {r.get('active', 0)}")
            print(f"    陈旧: {r.get('stale', 0)}")
            print(f"    未回答: {r.get('unaddressed', 0)}")
            print(f"    文件更新: {r.get('modified_wikis', 0)}")

        if "dashboard" in s["results"]:
            r = s["results"]["dashboard"]
            print("\n  [质量仪表盘]")
            print(f"    报告: {r.get('path', 'N/A')}")
            print(f"    状态: {r.get('status', 'N/A')}")

        if "lint" in s["results"]:
            r = s["results"]["lint"]
            print("\n  [健康检查]")
            print(f"    Errors: {r.get('errors', 0)}")
            print(f"    Warnings: {r.get('warnings', 0)}")
            print(f"    Info: {r.get('infos', 0)}")
            if r.get("broken_links_fixed", 0) > 0:
                print(f"    修复链接: {r.get('broken_links_fixed', 0)}")

        if "consolidate" in s["results"]:
            r = s["results"]["consolidate"]
            print("\n  [知识压缩]")
            print(f"    处理: {r.get('processed', 0)} 页")
            print(f"    成功: {r.get('success', 0)}")
            print(
                f"    行数: {r.get('original_lines', 0)} -> {r.get('compressed_lines', 0)}"
            )

        if "schema_evolve" in s["results"]:
            r = s["results"]["schema_evolve"]
            print("\n  [Schema 进化]")
            print(f"    指标数: {r.get('metrics_count', 0)}")
            print(f"    建议长度: {r.get('suggestions_chars', 0)} chars")

        print("\n" + "=" * 50)

        # 写入日志
        if not self.dry_run:
            details = [f"elapsed={s['elapsed_seconds']}s"]
            for step, result in s["results"].items():
                if step == "ingest":
                    details.append(
                        f"ingest={result.get('processed', 0)}/{result.get('entries', 0)}"
                    )
                elif step == "collect":
                    details.append(f"collect=+{result.get('new', 0)}")
                elif step == "extract":
                    details.append(f"extract=+{result.get('processed', 0)}")
                elif step == "tag":
                    details.append(
                        f"tag=+{result.get('processed', 0)}/{result.get('segments', 0)}segs"
                    )
                elif step == "assess":
                    details.append(f"assess=+{result.get('success', 0)}")
                elif step == "detect":
                    details.append(f"detect={result.get('high_confidence', 0)}high")
                elif step == "distill":
                    details.append(f"distill=+{result.get('added', 0)}entries")
                elif step == "judgment":
                    details.append(f"judgment={result.get('success', 0)}companies")
                elif step == "verify":
                    details.append(f"verify={result.get('clusters', 0)}events")
                elif step == "evolve":
                    details.append(
                        f"evolve={result.get('stale', 0)}stale/{result.get('unaddressed', 0)}unanswered"
                    )
                elif step == "dashboard":
                    details.append(f"dashboard={result.get('status', 'N/A')}")
                elif step == "lint":
                    details.append(
                        f"lint={result.get('errors', 0)}err/{result.get('warnings', 0)}warn"
                    )
                elif step == "consolidate":
                    details.append(
                        f"consolidate={result.get('success', 0)}pages/{result.get('original_lines', 0)}->{result.get('compressed_lines', 0)}lines"
                    )
                elif step == "schema_evolve":
                    details.append(
                        f"schema_evolve={result.get('metrics_count', 0)}metrics/{result.get('suggestions_chars', 0)}chars"
                    )
            append_log("scheduler", "调度周期完成", details=details)


def main():
    parser = argparse.ArgumentParser(description="知识库调度器")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只打印不执行")
    parser.add_argument("--collect-only", action="store_true", help="只执行新闻采集")
    parser.add_argument("--extract-only", action="store_true", help="只执行 PDF 提取")
    parser.add_argument("--tag-only", action="store_true", help="只执行标签化分段")
    parser.add_argument("--ingest-only", action="store_true", help="只执行文件处理")
    parser.add_argument("--assess-only", action="store_true", help="只执行评估更新")
    parser.add_argument("--detect-only", action="store_true", help="只执行矛盾检测")
    parser.add_argument("--distill-only", action="store_true", help="只执行行业蒸馏")
    parser.add_argument("--judgment-only", action="store_true", help="只执行投资判断")
    parser.add_argument("--verify-only", action="store_true", help="只执行交叉验证")
    parser.add_argument("--evolve-only", action="store_true", help="只执行问题演化")
    parser.add_argument(
        "--dashboard-only", action="store_true", help="只执行质量仪表盘"
    )
    parser.add_argument("--lint-only", action="store_true", help="只执行健康检查")
    parser.add_argument(
        "--consolidate-only", action="store_true", help="只执行知识压缩"
    )
    parser.add_argument(
        "--schema-evolve-only", action="store_true", help="只执行 Schema 进化"
    )
    parser.add_argument(
        "--daemon", action="store_true", help="守护模式，按配置自动调度"
    )
    parser.add_argument(
        "--steps",
        type=str,
        default="collect,extract,tag,ingest,assess,consolidate,distill,judgment,detect,evolve,dashboard,lint",
        help="执行的步骤，逗号分隔 (默认: collect,extract,tag,ingest,assess,distill,judgment,detect,evolve,dashboard,lint)",
    )
    args = parser.parse_args()

    scheduler = Scheduler(company_filter=args.company, dry_run=args.dry_run)

    # 守护模式
    if args.daemon:
        scheduler.run_daemon()
        return

    # 确定执行步骤
    if args.collect_only:
        steps = ["collect"]
    elif args.extract_only:
        steps = ["extract"]
    elif args.tag_only:
        steps = ["tag"]
    elif args.ingest_only:
        steps = ["ingest"]
    elif args.assess_only:
        steps = ["assess"]
    elif args.distill_only:
        steps = ["distill"]
    elif args.judgment_only:
        steps = ["judgment"]
    elif args.verify_only:
        steps = ["verify"]
    elif args.detect_only:
        steps = ["detect"]
    elif args.evolve_only:
        steps = ["evolve"]
    elif args.dashboard_only:
        steps = ["dashboard"]
    elif args.lint_only:
        steps = ["lint"]
    elif args.consolidate_only:
        steps = ["consolidate"]
    elif args.schema_evolve_only:
        steps = ["schema_evolve"]
    else:
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    scheduler.run(steps)


if __name__ == "__main__":
    main()
