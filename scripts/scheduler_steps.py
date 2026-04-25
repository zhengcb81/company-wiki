#!/usr/bin/env python3
"""
scheduler_steps.py — 调度器步骤函数

从 scheduler.py 提取的 14 个独立步骤函数，每个对应一个调度阶段。
通过 STEP_RUNNERS 注册表统一管理步骤名到函数的映射。
"""

import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

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

load_dotenv()

from log_writer import append_log
from graph import Graph
from llm_client import get_llm_client

# 导入各模块核心函数
from collect_news import collect_for_company, load_search_config
from config_rules_loader import RulesConfig
from ingest_v2 import scan_pending_files, process_file, get_wiki_path
from batch_assessment import (
    has_assessment,
    extract_timeline_entries,
    generate_assessment,
    add_assessment_section,
    is_assessment_stale,
    verify_predictions,
)
from contradiction_detector import ContradictionDetector
from sector_distiller import distill_sector
from investment_judgment import generate_all as generate_judgment
from cross_verify import (
    collect_all_entries,
    cluster_events,
    generate_report as generate_verify_report,
)
from evolve_questions import analyze_wiki, mark_stale_questions, suggest_new_questions
from quality_dashboard import generate_report as generate_dashboard
from lint import run_lint
from consolidate import find_oversized_pages, consolidate_page
from review_queue import ReviewQueue
from build_extracts import scan_pdf_files, build_extract
from tag_segments import scan_extract_files, process_extract


def run_collect(scheduler) -> Dict:
    """Step 1: 新闻采集（支持均衡调度）"""
    print("\n" + "=" * 50)
    print("  Step 1: 新闻采集")
    print("=" * 50)

    search_cfg = load_search_config()
    rules = RulesConfig()
    companies = scheduler.graph.get_all_companies()
    if scheduler.company_filter:
        companies = [c for c in companies if c["name"] == scheduler.company_filter]
    else:
        # 均衡采集：按上次采集时间排序，最久未采集的优先
        try:
            from collect_news import get_last_collect_time

            companies_with_time = [
                (c, get_last_collect_time(c["name"])) for c in companies
            ]
            companies_with_time.sort(key=lambda x: x[1])
            companies = [c for c, _ in companies_with_time]
        except Exception as e:
            logger.warning(str(e))

        # 限制每轮采集数量（从配置读取，默认 30）
        max_per_round = search_cfg.get("max_companies_per_round", 30)
        if max_per_round > 0:
            companies = companies[:max_per_round]
            print(f"  均衡模式: 处理最久未采集的 {len(companies)} 家公司")

    total_new = 0
    total_dup = 0
    company_results = []

    for company in companies:
        name = company["name"]
        print(f"\n[{name}] ({company.get('ticker', '')})")
        new, dup = collect_for_company(company, search_cfg, scheduler.dry_run, rules)
        total_new += new
        total_dup += dup
        company_results.append(f"{name}: +{new}")

    result = {
        "new": total_new,
        "dup": total_dup,
        "companies": company_results,
    }

    print(f"\n  采集完成: {total_new} 新文章, {total_dup} 重复跳过")
    if not scheduler.dry_run and total_new > 0:
        append_log(
            "collect_news",
            f"scheduler采集 {total_new} 篇新文章",
            details=company_results,
        )
    return result


def run_build_extracts(scheduler) -> Dict:
    """Step 1.5: PDF → 完整 Markdown (Layer 2)"""
    print("\n" + "=" * 50)
    print("  Step 1.5: PDF 提取 (build_extracts)")
    print("=" * 50)

    pdf_files = scan_pdf_files(scheduler.company_filter)
    db = {}
    db_path = WIKI_ROOT / ".extracts_db.json"
    if db_path.exists():
        try:
            db = json.loads(db_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(str(e))

    pending = []
    for company_name, pdf_path in pdf_files:
        stat = pdf_path.stat()
        fh = hashlib.md5(
            f"{pdf_path.name}:{stat.st_size}:{stat.st_mtime}".encode()
        ).hexdigest()
        key = f"{company_name}/{pdf_path.name}"
        if db.get(key) != fh:
            pending.append((company_name, pdf_path, fh))

    print(f"  PDF 总数: {len(pdf_files)}, 待处理: {len(pending)}")

    if not pending:
        return {"processed": 0, "skipped": 0, "errors": 0}

    success = 0
    skipped = 0
    errors = 0

    for i, (company_name, pdf_path, fh) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {company_name}/{pdf_path.name}")
        result = build_extract(company_name, pdf_path, dry_run=scheduler.dry_run)
        status = result["status"]
        if status == "success":
            success += 1
            print(f"  -> OK | {result['chars']} chars")
            if not scheduler.dry_run:
                db[f"{company_name}/{pdf_path.name}"] = fh
        elif status == "dry_run":
            print(f"  -> DRY-RUN | {result['chars']} chars")
        elif status == "skip":
            skipped += 1
            print(f"  -> SKIP | {result.get('error', '')}")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not scheduler.dry_run:
        db_path.write_text(
            json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\n  提取完成: {success} 成功, {skipped} 跳过, {errors} 错误")
    return {"processed": success, "skipped": skipped, "errors": errors}


def run_tag_segments(scheduler) -> Dict:
    """Step 1.8: Markdown → 标签化分段 (Layer 3)"""
    print("\n" + "=" * 50)
    print("  Step 1.8: 标签化分段 (tag_segments)")
    print("=" * 50)

    extract_files = scan_extract_files(scheduler.company_filter)
    db = {}
    db_path = WIKI_ROOT / ".segments_db.json"
    if db_path.exists():
        try:
            db = json.loads(db_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(str(e))

    pending = []
    for company_name, extract_path in extract_files:
        stat = extract_path.stat()
        fh = hashlib.md5(
            f"{extract_path.name}:{stat.st_size}:{stat.st_mtime}".encode()
        ).hexdigest()
        key = f"{company_name}/{extract_path.name}"
        if db.get(key) != fh:
            pending.append((company_name, extract_path, fh))

    print(f"  Extract 总数: {len(extract_files)}, 待处理: {len(pending)}")

    if not pending:
        return {"processed": 0, "skipped": 0, "errors": 0, "segments": 0}

    success = 0
    skipped = 0
    errors = 0
    total_segments = 0

    for i, (company_name, extract_path, fh) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {company_name}/{extract_path.name}")
        result = process_extract(
            company_name, extract_path, scheduler.llm_client, dry_run=scheduler.dry_run
        )
        status = result["status"]
        if status == "success":
            success += 1
            segs = result["segments"]
            total_segments += segs
            print(f"  -> OK | {segs} segments")
            if not scheduler.dry_run:
                db[f"{company_name}/{extract_path.name}"] = fh
        elif status == "dry_run":
            print(f"  -> DRY-RUN | ~{result.get('est_segments', 0)} segments")
        elif status == "skip":
            skipped += 1
            print(f"  -> SKIP | {result.get('error', '')}")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not scheduler.dry_run:
        db_path.write_text(
            json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(
        f"\n  分段完成: {success} 成功, {skipped} 跳过, {errors} 错误, {total_segments} 总段数"
    )
    return {
        "processed": success,
        "skipped": skipped,
        "errors": errors,
        "segments": total_segments,
    }


def run_ingest(scheduler) -> Dict:
    """Step 2: 文件处理"""
    print("\n" + "=" * 50)
    print("  Step 2: 文件处理 (ingest)")
    print("=" * 50)

    pending = scan_pending_files(scheduler.graph, scheduler.company_filter)
    print(f"  待处理文件: {len(pending)}")

    if not pending:
        return {"processed": 0, "entries": 0, "errors": 0}

    success = 0
    total_entries = 0
    errors = 0
    error_files = []

    processed_companies = set()
    for i, (file_path, entity_name, entity_type) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {Path(file_path).name[:60]}")
        try:
            result = process_file(
                file_path,
                entity_name,
                entity_type,
                scheduler.graph,
                scheduler.llm_client,
                dry_run=scheduler.dry_run,
            )
            status = result["status"]
            if status == "success":
                entries = result.get("entries_added", 0)
                total_entries += entries
                success += 1
                print(f"  -> OK | entries:{entries}")
                if not scheduler.dry_run and entity_type == "company":
                    processed_companies.add(entity_name)
            elif status == "dry_run":
                success += 1
                print(f"  -> DRY-RUN | would process")
            elif status == "skip":
                err = result.get("error") or ""
                print(f"  -> SKIP | {str(err)[:50]}")
            else:
                errors += 1
                err_msg = str(result.get("error") or "unknown")[:60]
                error_files.append(f"{Path(file_path).name}: {err_msg}")
                print(f"  -> ERR | {err_msg}")
        except Exception as e:
            logger.warning(str(e))
            errors += 1
            error_files.append(f"{Path(file_path).name}: {e}")
            print(f"  -> EXC | {e}")

    result = {
        "processed": success,
        "entries": total_entries,
        "errors": errors,
        "error_files": error_files,
    }

    print(f"\n  处理完成: {success} 成功, {total_entries} 条目, {errors} 错误")
    if not scheduler.dry_run and (success > 0 or errors > 0):
        append_log(
            "ingest",
            f"scheduler处理 {success} 文件, +{total_entries} 条目, {errors} 错误",
        )
        # 更新 state_store: last_ingest_time
        try:
            from state_store import get_state

            state = get_state()
            for company_name in processed_companies:
                state.set_last_ingest(company_name)
        except Exception as e:
            logger.warning(str(e))
    return result


def run_assess(scheduler) -> Dict:
    """Step 3: 评估更新（缺失 + 过时）"""
    print("\n" + "=" * 50)
    print("  Step 3: 评估更新")
    print("=" * 50)

    targets = []

    # 公司 wiki
    for d in (WIKI_ROOT / "companies").iterdir():
        if not d.is_dir():
            continue
        if scheduler.company_filter and d.name != scheduler.company_filter:
            continue
        wiki_dir = d / "wiki"
        if not wiki_dir.exists():
            continue
        for wiki in wiki_dir.glob("*.md"):
            if "_slides" in wiki.name:
                continue
            if not has_assessment(wiki):
                targets.append(("company", d.name, wiki, "missing"))
            elif is_assessment_stale(wiki):
                targets.append(("company", d.name, wiki, "stale"))

    # 行业 wiki
    for d in (WIKI_ROOT / "sectors").iterdir():
        if not d.is_dir():
            continue
        wiki_dir = d / "wiki"
        if not wiki_dir.exists():
            continue
        for wiki in wiki_dir.glob("*.md"):
            if "_slides" in wiki.name:
                continue
            if not has_assessment(wiki):
                targets.append(("sector", d.name, wiki, "missing"))
            elif is_assessment_stale(wiki):
                targets.append(("sector", d.name, wiki, "stale"))

    missing_count = sum(1 for t in targets if t[3] == "missing")
    stale_count = sum(1 for t in targets if t[3] == "stale")
    print(
        f"  待更新评估: {len(targets)} 页 (缺失: {missing_count}, 过时: {stale_count})"
    )

    if not targets:
        return {"success": 0, "skipped": 0, "errors": 0}

    # 批量限制：每次最多处理 20 个，优先处理缺失的
    MAX_ASSESS_PER_RUN = 50
    if len(targets) > MAX_ASSESS_PER_RUN:
        # 优先处理缺失评估，然后按过时时间排序
        targets = sorted(
            targets,
            key=lambda t: (
                0 if t[3] == "missing" else 1,
                t[2].stat().st_mtime if t[2].exists() else 0,
            ),
        )
        targets = targets[:MAX_ASSESS_PER_RUN]
        print(
            f"  本次处理前 {MAX_ASSESS_PER_RUN} 个（剩余 {missing_count + stale_count - MAX_ASSESS_PER_RUN} 个下次处理）"
        )

    success = 0
    skipped = 0
    errors = 0

    for i, (etype, name, wiki, reason) in enumerate(targets, 1):
        print(f"\n[{i}/{len(targets)}] {wiki.name} ({reason})")

        entries = extract_timeline_entries(wiki)
        if not entries:
            print(f"  -> SKIP | No timeline entries")
            skipped += 1
            continue

        # 获取核心问题
        if etype == "company":
            company = scheduler.graph.get_company(name)
            questions = company.get("questions", []) if company else []
            topic = "公司动态"
        else:
            sector = scheduler.graph.get_sector(name)
            questions = sector.get("questions", []) if sector else []
            topic = name

        try:
            if scheduler.dry_run:
                print(
                    f"  -> [DRY] Would {'regenerate' if reason == 'stale' else 'generate'} assessment from {len(entries)} entries"
                )
                success += 1
                continue

            assessment = generate_assessment(
                wiki, name, topic, questions, scheduler.llm_client
            )
            if assessment:
                add_assessment_section(wiki, assessment)
                print(
                    f"  -> OK | {len(assessment)} chars, based on {len(entries)} entries"
                )
                # 添加到审核队列（根据配置决定是否自动批准）
                try:
                    risk_level = "low"  # assessment 更新为低风险
                    rq_id = scheduler.review_queue.add_entry(
                        risk=risk_level,
                        op_type="assess",
                        entity=name,
                        description=f"更新综合评估: {wiki.name} ({reason})",
                        source=str(wiki.relative_to(WIKI_ROOT)),
                    )
                    # 只有配置允许时才自动批准
                    auto_approve = scheduler.review_config.get(
                        f"auto_approve_{risk_level}", False
                    )
                    if auto_approve:
                        scheduler.review_queue.approve(rq_id)
                except Exception as e:
                    logger.warning(str(e))

                # 验证历史预测
                try:
                    verifications = verify_predictions(wiki)
                    if verifications:
                        print(
                            f"  -> 预测验证: {len(verifications)} 个历史预测需关注"
                        )
                        for v in verifications[:2]:  # 只显示前2个
                            print(
                                f"      • {v['prediction'][:50]}... | 偏差: {v['deviation']}"
                            )
                except Exception as e:
                    logger.warning(str(e))

                success += 1
            else:
                print(f"  -> SKIP | LLM returned empty")
                skipped += 1
        except Exception as e:
            print(f"  -> ERR | {e}")
            errors += 1

    result = {
        "success": success,
        "skipped": skipped,
        "errors": errors,
    }

    print(f"\n  评估更新完成: {success} 成功, {skipped} 跳过, {errors} 错误")
    if not scheduler.dry_run and success > 0:
        append_log("enrich", f"scheduler补全 {success} 页评估")
    return result


def run_distill(scheduler) -> Dict:
    """Step 3.5: 行业蒸馏"""
    print("\n" + "=" * 50)
    print("  Step 3.5: 行业蒸馏")
    print("=" * 50)

    all_sectors = scheduler.graph.get_all_sectors()
    processed = 0
    success = 0
    total_entries = 0

    for sname in all_sectors:
        if scheduler.company_filter:
            continue  # distill 不支持按公司过滤
        if scheduler.dry_run:
            print(f"  [DRY] Would distill: {sname}")
            processed += 1
            continue

        try:
            result = distill_sector(
                sname, scheduler.graph, scheduler.llm_client, dry_run=False
            )
            status = result.get("status", "unknown")
            if status == "success":
                success += 1
                total_entries += result.get("added", 0)
                print(f"  [OK] {sname}: +{result.get('added', 0)} entries")
            else:
                print(f"  [{status.upper()}] {sname}")
            processed += 1
        except Exception as e:
            print(f"  [ERR] {sname}: {e}")

    result = {
        "processed": processed,
        "success": success,
        "added": total_entries,
    }

    print(f"\n  蒸馏完成: {success}/{processed} 行业成功, +{total_entries} 条目")
    if not scheduler.dry_run and success > 0:
        append_log(
            "distill", f"scheduler蒸馏 {success} 行业, +{total_entries} 条目"
        )
    return result


def run_judgment(scheduler) -> Dict:
    """Step 5: 投资判断层 — 为所有公司生成投资判断页面"""
    print("\n" + "=" * 50)
    print("  Step 5: 投资判断层")
    print("=" * 50)

    companies = scheduler.graph.get_all_companies()
    if scheduler.company_filter:
        companies = [c for c in companies if c["name"] == scheduler.company_filter]

    success_count = 0
    skip_count = 0
    total_metrics = 0
    company_details = []

    for company in companies:
        name = company["name"]
        if scheduler.dry_run:
            print(f"  [DRY] Would generate judgment pages for: {name}")
            success_count += 1
            continue

        result = generate_judgment(
            name, WIKI_ROOT, dry_run=False, use_llm=True, llm_client=scheduler.llm_client
        )
        page_results = result.get("results", {})
        if page_results:
            success_count += 1
            for pname, presult in page_results.items():
                if presult.get("status") == "success":
                    if "metrics_count" in presult:
                        total_metrics += presult["metrics_count"]
                    company_details.append(f"{name}/{pname}: OK")
                else:
                    skip_count += 1
        else:
            skip_count += 1

    result = {
        "success": success_count,
        "skipped": skip_count,
        "total_metrics": total_metrics,
    }

    print(f"\n  投资判断完成: {success_count} 公司成功, {skip_count} 跳过")
    if not scheduler.dry_run and success_count > 0:
        append_log("enrich", f"scheduler投资判断: {success_count} 公司")
    return result


def run_cross_verify(scheduler) -> Dict:
    """Step 6: 多源交叉验证"""
    print("\n" + "=" * 50)
    print("  Step 6: 多源交叉验证")
    print("=" * 50)

    entries = collect_all_entries(scheduler.company_filter)
    if not entries:
        print("  无条目可分析")
        return {"total": 0, "clusters": 0, "report_path": ""}

    clusters = cluster_events(entries, similarity_threshold=0.6)

    high = [c for c in clusters if c.credibility.startswith("高")]
    medium = [c for c in clusters if c.credibility.startswith("中")]
    low = [c for c in clusters if c.credibility.startswith("待")]

    print(f"\n  条目数: {len(entries)}, 事件数: {len(clusters)}")
    print(f"  高可信度(3+来源): {len(high)}")
    print(f"  中可信度(2来源):  {len(medium)}")
    print(f"  待验证(1来源):    {len(low)}")

    report_path = ""
    if not scheduler.dry_run:
        report_path = str(WIKI_ROOT / "cross_verify_report.md")
        generate_verify_report(clusters, Path(report_path))
        print(f"  报告已保存: {report_path}")
        append_log(
            "lint", f"scheduler交叉验证: {len(clusters)} 事件, {len(high)} 高可信度"
        )

    return {
        "total": len(entries),
        "clusters": len(clusters),
        "high": len(high),
        "medium": len(medium),
        "low": len(low),
        "report_path": report_path,
    }


def run_evolve(scheduler) -> Dict:
    """Step 7: 问题清单演化"""
    print("\n" + "=" * 50)
    print("  Step 7: 问题清单演化")
    print("=" * 50)

    targets = []

    # 公司 wiki
    for d in (WIKI_ROOT / "companies").iterdir():
        if not d.is_dir():
            continue
        if scheduler.company_filter and d.name != scheduler.company_filter:
            continue
        wiki_dir = d / "wiki"
        if not wiki_dir.exists():
            continue
        for wiki in wiki_dir.glob("*.md"):
            if "_slides" in wiki.name:
                continue
            targets.append(("company", d.name, wiki))

    # 行业 wiki
    if not scheduler.company_filter:
        for d in (WIKI_ROOT / "sectors").iterdir():
            if not d.is_dir():
                continue
            wiki_dir = d / "wiki"
            if not wiki_dir.exists():
                continue
            for wiki in wiki_dir.glob("*.md"):
                if "_slides" in wiki.name:
                    continue
                targets.append(("sector", d.name, wiki))

    total_stale = 0
    total_active = 0
    total_unaddressed = 0
    modified_wikis = 0

    print(f"\n  扫描 {len(targets)} 个 wiki 页面...")

    for etype, name, wiki in targets:
        result = analyze_wiki(wiki, 180)
        if result["questions"] == 0:
            continue

        stale_indices = [s["index"] for s in result["stale"]]
        stale_indices.extend([u["index"] for u in result["unaddressed"]])

        if stale_indices and not scheduler.dry_run:
            count = mark_stale_questions(wiki, stale_indices, scheduler.dry_run)
            if count > 0:
                modified_wikis += 1

        total_stale += len(result["stale"])
        total_active += len(result["active"])
        total_unaddressed += len(result["unaddressed"])

    result = {
        "total_questions": total_active + total_stale + total_unaddressed,
        "active": total_active,
        "stale": total_stale,
        "unaddressed": total_unaddressed,
        "modified_wikis": modified_wikis,
    }

    print(
        f"\n  问题演化完成: {total_active} 活跃, {total_stale} 陈旧, {total_unaddressed} 未回答, {modified_wikis} 文件更新"
    )
    if not scheduler.dry_run and modified_wikis > 0:
        append_log(
            "lint",
            f"scheduler问题演化: {total_stale} 陈旧, {total_unaddressed} 未回答, {modified_wikis} 文件更新",
        )
    return result


def run_dashboard(scheduler) -> Dict:
    """Step 8: 质量仪表盘"""
    print("\n" + "=" * 50)
    print("  Step 8: 质量仪表盘")
    print("=" * 50)

    output_path = str(WIKI_ROOT / "quality_report.md")

    if scheduler.dry_run:
        print(f"  [DRY] Would generate dashboard to {output_path}")
        return {"path": output_path, "status": "dry_run"}

    try:
        report_text = generate_dashboard(scheduler.graph, output_path)
        print(f"  报告已保存: {output_path}")
        append_log("lint", f"scheduler质量仪表盘已更新")
        return {"path": output_path, "status": "success"}
    except Exception as e:
        print(f"  [ERR] {e}")
        return {"path": "", "status": "error", "error": str(e)}


def run_lint_step(scheduler) -> Dict:
    """Step 9: 健康检查"""
    print("\n" + "=" * 50)
    print("  Step 9: 健康检查 (lint)")
    print("=" * 50)

    if scheduler.dry_run:
        print("  [DRY] Would run lint checks")
        return {"status": "dry_run"}

    try:
        result = run_lint(checks=["all"], use_llm=False)
        errors, warnings, infos = result.summary()
        print(f"\n  Lint 完成: {errors} errors, {warnings} warnings, {infos} info")

        # 自动修复 broken links
        broken_link_count = sum(
            1 for i in result.issues if i["category"] == "broken_link"
        )
        if broken_link_count > 0:
            print(f"  尝试修复 {broken_link_count} 个 broken links...")
            try:
                import subprocess

                fix_script = SCRIPTS_DIR / "fix_broken_links.py"
                if fix_script.exists():
                    proc = subprocess.run(
                        [sys.executable, str(fix_script)],
                        capture_output=True,
                        text=True,
                        cwd=str(WIKI_ROOT),
                    )
                    if proc.returncode == 0:
                        print(f"  修复完成")
            except Exception as e:
                print(f"  修复失败: {e}")

        return {
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "broken_links_fixed": broken_link_count,
        }
    except Exception as e:
        print(f"  [ERR] {e}")
        return {"status": "error", "error": str(e)}


def run_consolidate(scheduler) -> Dict:
    """Step 10: 知识压缩"""
    print("\n" + "=" * 50)
    print("  Step 10: 知识压缩")
    print("=" * 50)

    targets = find_oversized_pages(500, scheduler.company_filter)
    print(f"  超过 500 行的页面: {len(targets)}")

    if not targets:
        return {"processed": 0, "success": 0, "errors": 0}

    success = 0
    errors = 0
    total_original = 0
    total_compressed = 0

    for i, (etype, name, wiki) in enumerate(targets, 1):
        lines = len(wiki.read_text(encoding="utf-8").splitlines())
        print(f"\n[{i}/{len(targets)}] {name}/{wiki.name} ({lines} 行)")

        if scheduler.dry_run:
            print(f"  -> DRY | Would compress")
            success += 1
            continue

        try:
            result = consolidate_page(wiki, name, scheduler.llm_client, dry_run=False)
            if result["status"] == "success":
                success += 1
                total_original += result["original_lines"]
                total_compressed += result["compressed_lines"]
                print(
                    f"  -> OK | {result['original_lines']} -> {result['compressed_lines']} 行"
                )
            elif result["status"] == "skip":
                print(f"  -> SKIP | {result.get('reason', '')}")
            else:
                errors += 1
                print(f"  -> ERR | {result.get('reason', 'unknown')}")
        except Exception as e:
            logger.warning(str(e))
            errors += 1
            print(f"  -> EXC | {e}")

    result = {
        "processed": len(targets),
        "success": success,
        "errors": errors,
        "original_lines": total_original,
        "compressed_lines": total_compressed,
    }

    print(f"\n  压缩完成: {success} 成功, {errors} 错误")
    if total_original > 0:
        print(f"  行数: {total_original} -> {total_compressed}")
    if not scheduler.dry_run and success > 0:
        append_log(
            "enrich",
            f"scheduler知识压缩: {success} 页面, {total_original} -> {total_compressed} 行",
        )
    return result


def run_detect(scheduler) -> Dict:
    """Step 4: 矛盾检测"""
    print("\n" + "=" * 50)
    print("  Step 4: 矛盾检测")
    print("=" * 50)

    detector = ContradictionDetector(WIKI_ROOT)
    contradictions = detector.detect_all()

    # 按类型分组
    by_type: Dict[str, int] = {}
    for c in contradictions:
        by_type[c.contradiction_type] = by_type.get(c.contradiction_type, 0) + 1

    print(f"\n  发现 {len(contradictions)} 个潜在矛盾:")
    for ctype, count in by_type.items():
        print(f"    - {ctype}: {count}")

    # 生成报告（只保留 high confidence 的）
    high_conf = [c for c in contradictions if c.confidence == "high"]
    report_path = WIKI_ROOT / "contradiction_report.md"

    if not scheduler.dry_run:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 矛盾检测报告\n\n")
            f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## 概述\n\n")
            f.write(f"- 总矛盾数: {len(contradictions)}\n")
            f.write(f"- 高置信度: {len(high_conf)}\n")
            for ctype, count in sorted(by_type.items()):
                f.write(f"- {ctype}: {count}\n")
            f.write("\n## 高置信度矛盾\n\n")
            for c in high_conf[:20]:
                f.write(f"### {c.description}\n\n")
                f.write(f"- 实体: {c.entity1}\n")
                f.write(f"- 页面1: {c.page1}\n")
                f.write(f"- 陈述1: {c.statement1[:200]}\n")
                f.write(f"- 页面2: {c.page2}\n")
                f.write(f"- 陈述2: {c.statement2[:200]}\n\n")

        # 高置信度矛盾 → 审核队列
        added_to_queue = 0
        for c in high_conf[:10]:  # 最多 10 个加入队列
            try:
                scheduler.review_queue.add_entry(
                    risk="high",
                    op_type="contradiction",
                    entity=c.entity1,
                    description=f"矛盾: {c.description[:100]}",
                    source=f"{c.page1} vs {c.page2}",
                )
                added_to_queue += 1
            except Exception as e:
                logger.warning(str(e))
        if added_to_queue > 0:
            print(f"  -> {added_to_queue} 个高置信度矛盾已加入审核队列")

        append_log(
            "lint",
            f"scheduler矛盾检测: {len(contradictions)} 潜在, {len(high_conf)} 高置信度, {added_to_queue} 入队列",
        )

    return {
        "total": len(contradictions),
        "high_confidence": len(high_conf),
        "by_type": by_type,
    }


# --- Schema evolve helper functions ---

def _collect_metrics(scheduler) -> Dict[str, Any]:
    """收集系统运行指标"""
    metrics = {}

    # 统计 wiki 页面数
    company_wikis = list(WIKI_ROOT.glob("companies/*/wiki/*.md"))
    sector_wikis = list(WIKI_ROOT.glob("sectors/*/wiki/*.md"))
    theme_wikis = list(WIKI_ROOT.glob("themes/*/wiki/*.md"))
    metrics["company_pages"] = len(
        [w for w in company_wikis if "_slides" not in w.name]
    )
    metrics["sector_pages"] = len(
        [w for w in sector_wikis if "_slides" not in w.name]
    )
    metrics["theme_pages"] = len(theme_wikis)

    # 统计过时页面 (>60 天未更新)
    stale_pages = 0
    total_assessments = 0
    missing_assessments = 0
    for wiki_list in [company_wikis, sector_wikis]:
        for w in wiki_list:
            if "_slides" in w.name or not w.exists():
                continue
            if has_assessment(w):
                total_assessments += 1
                if is_assessment_stale(w):
                    stale_pages += 1
            else:
                missing_assessments += 1
    metrics["stale_assessments"] = stale_pages
    metrics["total_assessments"] = total_assessments
    metrics["missing_assessments"] = missing_assessments

    # 统计公司数
    companies = scheduler.graph.get_all_companies()
    metrics["tracked_companies"] = len(companies)

    # 统计行业数
    sectors = scheduler.graph.get_all_sectors()
    metrics["tracked_sectors"] = len(sectors)

    return metrics


def _get_recent_logs(days: int = 7) -> List[str]:
    """读取近 N 天日志条目摘要"""
    log_path = WIKI_ROOT / "log.md"
    if not log_path.exists():
        return []

    try:
        content = log_path.read_text(encoding="utf-8")
        # 提取最近的日志条目 (按日期分组)

        # 匹配形如 "## [2026-04-24 22:43] ..." 的日志标题
        date_pattern = re.compile(r"##\s*\[?(\d{4}-\d{2}-\d{2})")
        entries = []
        current_date = None
        current_lines = []

        for line in content.splitlines():
            m = date_pattern.search(line.strip())
            if m:
                if current_date and current_lines:
                    try:
                        entry_date = datetime.strptime(current_date, "%Y-%m-%d")
                        if (datetime.now() - entry_date).days <= days:
                            entries.append(
                                current_date + ": " + " | ".join(current_lines)
                            )
                    except ValueError:
                        pass
                current_date = m.group(1)
                # 提取 header 的描述部分（去掉日期和级别前缀）
                header_desc = re.sub(r"\[.*?\]\s*\w+\s*", "", line.strip()).strip()
                current_lines = [header_desc] if header_desc else []
            elif current_date and line.strip().startswith("- "):
                current_lines.append(line.strip()[2:])

        # 最后一个条目
        if current_date and current_lines:
            try:
                entry_date = datetime.strptime(current_date, "%Y-%m-%d")
                if (datetime.now() - entry_date).days <= days:
                    entries.append(current_date + ": " + " | ".join(current_lines))
            except ValueError:
                pass

        return entries[-20:]  # 最多保留 20 条
    except Exception:
        return []


def _get_review_stats() -> Dict[str, int]:
    """读取审核队列统计"""
    try:
        from review_queue import ReviewQueue

        rq = ReviewQueue()
        entries = rq.get_all()
        stats = {"pending": 0, "approved": 0, "rejected": 0, "total": len(entries)}
        for e in entries:
            status = e.get("status", "")
            if status == "pending":
                stats["pending"] += 1
            elif status == "approved":
                stats["approved"] += 1
            elif status == "rejected":
                stats["rejected"] += 1
        return stats
    except Exception:
        return {"pending": 0, "approved": 0, "rejected": 0, "total": 0}


def _get_lint_summary() -> str:
    """获取最近一次 lint 报告的问题摘要"""
    lint_report = WIKI_ROOT / "lint_report.md"
    quality_report = WIKI_ROOT / "quality_report.md"
    parts = []

    if lint_report.exists():
        try:
            content = lint_report.read_text(encoding="utf-8")
            # 提取前几行关键信息
            lines = content.splitlines()
            for line in lines[:30]:
                s = line.strip()
                if (
                    s.startswith("- ")
                    or s.startswith("* ")
                    or "error" in s.lower()
                    or "warning" in s.lower()
                ):
                    parts.append(s)
            if not parts:
                parts.append(f"Lint 报告存在 ({len(lines)} 行)")
        except Exception:
            parts.append("_（无法读取 lint_report.md）_")

    if quality_report.exists():
        try:
            content = quality_report.read_text(encoding="utf-8")
            lines = content.splitlines()
            summary_lines = [l.strip() for l in lines[1:15] if l.strip()]
            if summary_lines:
                parts.append(f"质量报告: {len(lines)} 行")
        except Exception as e:
            logger.warning(str(e))

    return "\\n".join(parts[:5]) if parts else "_（暂无 lint 数据）_"


def _generate_evolve_suggestions(
    scheduler,
    metrics: Dict,
    recent_logs: List[str],
    review_stats: Dict,
    lint_summary: str,
) -> str:
    """用 LLM 分析系统状态并生成改进建议"""
    prompt = f"""你是公司知识库系统的自我优化分析助手。

以下是系统的当前运行数据，请分析并生成 2-4 条具体的改进建议，每条建议应包括"问题"和"建议"。
建议应针对 CLAUDE.md 中定义的维护规范（LLM 驱动的上市公司知识库），重点关注：数据质量、自动闭环、信息发现。

## 系统指标
- 跟踪公司数: {metrics.get("tracked_companies", "N/A")}
- 跟踪行业数: {metrics.get("tracked_sectors", "N/A")}
- 公司 wiki 页面: {metrics.get("company_pages", "N/A")}
- 行业 wiki 页面: {metrics.get("sector_pages", "N/A")}
- 已有综合评估: {metrics.get("total_assessments", "N/A")}
- 过时评估(>60天): {metrics.get("stale_assessments", "N/A")}
- 缺失评估: {metrics.get("missing_assessments", "N/A")}

## 近期日志（近 7 天）
{chr(10).join(recent_logs[:10]) if recent_logs else "（暂无）"}

## 审核队列
- 总计: {review_stats.get("total", 0)}
- 待审: {review_stats.get("pending", 0)}
- 已批: {review_stats.get("approved", 0)}

## Lint 报告
{lint_summary}

请用以下格式输出（不超过 500 字）：
### 发现的问题
1. **问题描述** → **改进建议**

### 重点关注
- 最需要关注的一两件事
"""
    if not scheduler.llm_client:
        return "_（LLM 客户端未初始化）_"

    response = scheduler.llm_client.chat_with_retry(
        prompt,
        "你是一个知识库系统维护专家。请用中文简洁回答。",
    )
    if response.success:
        return response.content.strip()
    return "_（LLM 分析失败）_"


def _update_claude_feedback(
    metrics: Dict, review_stats: Dict, lint_summary: str, suggestions: str
):
    """更新 CLAUDE.md 的反馈记录 section"""
    claude_path = WIKI_ROOT / "CLAUDE.md"
    if not claude_path.exists():
        print("  [WARN] CLAUDE.md 不存在，跳过更新")
        return

    content = claude_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")

    # 构建反馈记录内容
    feedback = f"""\n\n## 反馈记录（自动生成）

> 此 section 由 scheduler.py 的 schema evolve 机制自动更新。
> 记录了系统运行中的质量指标和改进建议，供 LLM 自我优化参考。
> 最后更新：{today}

### 运行指标
- 跟踪实体：{metrics.get("tracked_companies", 0)} 家公司, {metrics.get("tracked_sectors", 0)} 个行业
- Wiki 页面：{metrics.get("company_pages", 0)} 公司页, {metrics.get("sector_pages", 0)} 行业页
- 综合评估：{metrics.get("total_assessments", 0)} 已有, {metrics.get("stale_assessments", 0)} 过时, {metrics.get("missing_assessments", 0)} 缺失
- 审核队列：{review_stats.get("total", 0)} 总计, {review_stats.get("pending", 0)} 待审, {review_stats.get("approved", 0)} 已批
- Lint 状态：{lint_summary}

### 改进建议

{suggestions}
"""

    # 替换或添加反馈记录 section
    if "## 反馈记录" in content:
        content = re.sub(
            r"## 反馈记录[\s\S]*?(?=\Z)",
            lambda m: feedback.strip() + "\n",
            content,
        )
    else:
        content = content.rstrip() + feedback.strip() + "\n"

    claude_path.write_text(content, encoding="utf-8")
    print(f"  已更新 CLAUDE.md 反馈记录")


def run_schema_evolve(scheduler) -> Dict:
    """Step 11: Schema 自我进化 — 收集系统指标并更新 CLAUDE.md 反馈记录"""
    print("\n" + "=" * 50)
    print("  Step 11: Schema 进化")
    print("=" * 50)

    if scheduler.dry_run:
        print("  [DRY] Would collect metrics and update CLAUDE.md")
        return {"status": "dry_run"}

    # 1. 收集系统运行指标
    metrics = _collect_metrics(scheduler)
    print(f"  系统指标: {len(metrics)} 项")

    # 2. 读取近 7 天日志摘要
    recent_logs = _get_recent_logs(days=7)
    print(f"  近期日志: {len(recent_logs)} 条")

    # 3. 读取 review queue 统计
    review_stats = _get_review_stats()
    print(
        f"  审核队列: {review_stats.get('pending', 0)} 待审, {review_stats.get('approved', 0)} 已批"
    )

    # 4. 读取 lint 报告问题摘要
    lint_summary = _get_lint_summary()
    print(f"  Lint: {lint_summary}")

    # 5. 用 LLM 生成改进建议
    suggestions = ""
    try:
        suggestions = _generate_evolve_suggestions(
            scheduler, metrics, recent_logs, review_stats, lint_summary
        )
        print(f"  改进建议: {len(suggestions)} chars")
    except Exception as e:
        print(f"  [WARN] LLM 建议生成失败: {e}")
        suggestions = "_（LLM 分析暂时不可用）_"

    # 6. 更新 CLAUDE.md 反馈记录 section
    _update_claude_feedback(metrics, review_stats, lint_summary, suggestions)

    result = {
        "status": "success",
        "metrics_count": len(metrics),
        "suggestions_chars": len(suggestions),
    }

    print(f"\n  Schema 进化完成")
    if not scheduler.dry_run:
        append_log(
            "evolve",
            f"scheduler schema进化: {len(metrics)} 指标, 建议 {len(suggestions)} chars",
        )
    return result


# --- Step registry ---

STEP_RUNNERS = {
    "collect": run_collect,
    "extract": run_build_extracts,
    "tag": run_tag_segments,
    "ingest": run_ingest,
    "assess": run_assess,
    "detect": run_detect,
    "distill": run_distill,
    "judgment": run_judgment,
    "verify": run_cross_verify,
    "evolve": run_evolve,
    "dashboard": run_dashboard,
    "lint": run_lint_step,
    "consolidate": run_consolidate,
    "schema_evolve": run_schema_evolve,
}
