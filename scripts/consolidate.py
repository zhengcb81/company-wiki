#!/usr/bin/env python3
"""
consolidate.py — 知识压缩机制（Phase 3 增强版）

当 wiki 页面过于庞大时（>500行），智能压缩：
- 保留 <90 天的时间线条目（近期动态）
- 归档 >=90 天的旧条目到 archive/ 目录
- 用 LLM 生成：关键判断 + 核心矛盾 + 投资论点
- 添加中期摘要（季度汇总）

压缩后的页面结构：
  ## 核心问题
  ## 关键判断（自动压缩）
  ## 近期时间线（<90 天）
  ## 中期摘要（季度汇总）
  ## 综合评估
  ## 相关页面

用法：
    python3 scripts/consolidate.py                    # 扫描并压缩所有过大的页面
    python3 scripts/consolidate.py --company 中微公司  # 只压缩指定公司
    python3 scripts/consolidate.py --dry-run          # 只报告不执行
    python3 scripts/consolidate.py --threshold 500    # 设置行数阈值
"""

import argparse
import re
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from log_writer import append_log
from llm_client import get_llm_client

# 保留近期条目的天数阈值
RECENT_DAYS = 90


def count_lines(path: Path) -> int:
    """计算文件行数"""
    try:
        content = path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except Exception:
        return 0


def extract_frontmatter(content: str) -> Tuple[str, str]:
    """提取 frontmatter 和正文，返回 (frontmatter, body)"""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            fm = content[: end + 3]
            body = content[end + 3 :].strip()
            return fm, body
    return "", content


def extract_timeline_entries(content: str) -> List[Dict]:
    """提取所有时间线条目"""
    entries = []
    pattern = re.compile(
        r"(### \d{4}-\d{2}-\d{2} \| .+?)(?=\n### |\n## |\Z)", re.DOTALL
    )
    for match in pattern.finditer(content):
        block = match.group(0).strip()
        # 提取日期和标题
        header_match = re.match(r"### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)", block)
        if header_match:
            entries.append(
                {
                    "date": header_match.group(1),
                    "source_type": header_match.group(2),
                    "title": header_match.group(3),
                    "block": block,
                }
            )
    return entries


def split_entries_by_age(
    entries: List[Dict], days: int = RECENT_DAYS
) -> Tuple[List[Dict], List[Dict]]:
    """
    按年龄分割时间线条目

    Returns:
        (recent_entries, old_entries)
    """
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    old = []

    for e in entries:
        try:
            entry_date = datetime.strptime(e["date"], "%Y-%m-%d")
            if entry_date >= cutoff:
                recent.append(e)
            else:
                old.append(e)
        except (ValueError, TypeError):
            # 无法解析日期的条目视为旧的
            old.append(e)

    return recent, old


def extract_sections(content: str) -> Dict[str, str]:
    """提取各 ## section 的内容"""
    sections = {}
    parts = re.split(r"^(## .+)$", content, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        section_name = header[3:].strip()
        sections[section_name] = body
    return sections


def compress_with_llm(
    old_entries: List[Dict], recent_entries: List[Dict], entity_name: str, llm_client
) -> Optional[Dict[str, str]]:
    """
    用 LLM 压缩旧时间线条目为结构化摘要

    Returns:
        {"key_judgments": str, "core_contradictions": str, "investment_thesis": str,
         "quarterly_summary": str}
    """
    if not old_entries:
        return None

    # 构建条目摘要（限制 token 用量）
    entry_texts = []
    for e in old_entries[:100]:  # 最多取 100 个旧条目
        entry_texts.append(f"- [{e['date']}] {e['title']}")
    entries_str = "\n".join(entry_texts)

    # 构建近期条目上下文
    recent_texts = []
    for e in recent_entries[:20]:
        recent_texts.append(f"- [{e['date']}] {e['title']}")
    recent_str = "\n".join(recent_texts) if recent_texts else "（无近期条目）"

    prompt = f"""你是一名资深的上市公司研究分析师。以下是关于"{entity_name}"的时间线条目。

需要压缩的旧条目（{len(old_entries)} 条，距今超过 {RECENT_DAYS} 天）：
{entries_str[:6000]}

近期条目（{len(recent_entries)} 条，距今 {RECENT_DAYS} 天内，仅供参考上下文）：
{recent_str[:2000]}

请将旧条目压缩为以下 4 个部分，直接输出 markdown 格式（不要包含 ```markdown 代码块标记）：

## 关键判断
列出 5-10 个最重要的判断/结论（每个一行，用 `- ` 开头）。这些应该是从时间线中提炼出的最核心的洞察，而不是简单的事实罗列。注意结合近期条目判断这些旧结论是否仍然成立。

## 核心矛盾
列出 2-3 个当前最值得关注的矛盾或分歧（每个一行，用 `- ` 开头）。例如：营收增长但毛利率下滑、订单饱满但产能不足等。

## 投资论点
用 1-2 段话总结当前的投资论点（看多或看空的核心逻辑）。如果旧判断已被近期信息推翻，请明确指出。

## 中期摘要（季度汇总）
按季度汇总关键事件（每个季度 2-3 行），格式为 `#### YYYY-QX` 子标题。只汇总有实质性内容的季度。"""

    try:
        response = llm_client.chat(prompt)
        if response and response.content:
            content = response.content.strip()

            # 解析返回的 4 个部分
            result = {}

            # 关键判断
            kj_match = re.search(r"## 关键判断\n+([\s\S]*?)(?=\n## |\Z)", content)
            result["key_judgments"] = kj_match.group(1).strip() if kj_match else ""

            # 核心矛盾
            cc_match = re.search(r"## 核心矛盾\n+([\s\S]*?)(?=\n## |\Z)", content)
            result["core_contradictions"] = (
                cc_match.group(1).strip() if cc_match else ""
            )

            # 投资论点
            it_match = re.search(r"## 投资论点\n+([\s\S]*?)(?=\n## |\Z)", content)
            result["investment_thesis"] = it_match.group(1).strip() if it_match else ""

            # 中期摘要
            ms_match = re.search(r"## 中期摘要.*?\n+([\s\S]*?)(?=\n## |\Z)", content)
            result["quarterly_summary"] = ms_match.group(1).strip() if ms_match else ""

            return result
    except Exception as e:
        print(f"  [LLM ERR] {e}")

    return None


def archive_entries(entries: List[Dict], archive_path: Path, entity_name: str) -> bool:
    """将时间线条目归档到指定文件"""
    if not entries:
        return False

    archive_content = f"# {entity_name} — 归档时间线条目\n\n"
    archive_content += f"> 归档时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    archive_content += f"> 条目数: {len(entries)}\n"
    archive_content += f"> 日期范围: {entries[0]['date']} 至 {entries[-1]['date']}\n\n"

    for e in entries:
        archive_content += e["block"] + "\n\n"

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(archive_content, encoding="utf-8")
    return True


def build_compressed_content(
    frontmatter: str,
    sections: Dict[str, str],
    compressed: Dict[str, str],
    recent_entries: List[Dict],
    entity_name: str,
    old_count: int,
) -> str:
    """构建压缩后的 wiki 内容"""
    # 更新 frontmatter 中的 last_updated
    today = datetime.now().strftime("%Y-%m-%d")
    if "last_updated:" in frontmatter:
        frontmatter = re.sub(
            r'last_updated:\s*"?[^"\n]+"?', f"last_updated: {today}", frontmatter
        )

    parts = [frontmatter, ""]

    # 核心问题（保留）
    if "核心问题" in sections:
        parts.append("## 核心问题")
        parts.append(sections["核心问题"])
        parts.append("")

    # 关键判断
    if compressed.get("key_judgments"):
        parts.append("## 关键判断")
        parts.append(compressed["key_judgments"])
        parts.append("")

    # 核心矛盾
    if compressed.get("core_contradictions"):
        parts.append("## 核心矛盾")
        parts.append(compressed["core_contradictions"])
        parts.append("")

    # 投资论点
    if compressed.get("investment_thesis"):
        parts.append("## 投资论点")
        parts.append("> " + compressed["investment_thesis"].replace("\n", "\n> "))
        parts.append("")

    # 近期时间线（<90 天）
    if recent_entries:
        parts.append(f"## 近期时间线（<{RECENT_DAYS} 天）")
        for e in recent_entries:
            parts.append(e["block"])
            parts.append("")

    # 中期摘要
    if compressed.get("quarterly_summary"):
        parts.append("## 中期摘要（季度汇总）")
        parts.append(compressed["quarterly_summary"])
        parts.append("")

    # 综合评估（保留）
    if "综合评估" in sections:
        parts.append("## 综合评估")
        parts.append(sections["综合评估"])
        parts.append("")

    # 相关页面（保留）
    if "相关页面" in sections:
        parts.append("## 相关页面")
        parts.append(sections["相关页面"])
        parts.append("")

    # 归档说明
    parts.append("---")
    parts.append(
        f"> 本页面已智能压缩。{old_count} 条历史时间线条目已归档至 `archive/` 目录。"
    )
    parts.append(f"> 保留 {len(recent_entries)} 条近期条目（<{RECENT_DAYS} 天）。")
    parts.append(f"> 压缩时间: {today}")

    return "\n".join(parts)


def consolidate_page(
    wiki_path: Path,
    entity_name: str,
    llm_client,
    dry_run: bool = False,
    archive_only: bool = False,
) -> Dict:
    """
    压缩单个 wiki 页面

    Returns:
        操作结果字典
    """
    content = wiki_path.read_text(encoding="utf-8")
    original_lines = len(content.splitlines())

    frontmatter, body = extract_frontmatter(content)
    sections = extract_sections(body)
    all_entries = extract_timeline_entries(content)

    if not all_entries:
        return {"status": "skip", "reason": "no_entries", "lines": original_lines}

    # 分割近期和旧条目
    recent_entries, old_entries = split_entries_by_age(all_entries, RECENT_DAYS)

    # 如果旧条目太少（<10 条），不值得压缩
    if len(old_entries) < 10:
        return {
            "status": "skip",
            "reason": "too_few_old_entries",
            "lines": original_lines,
            "old_entries": len(old_entries),
            "recent_entries": len(recent_entries),
        }

    # dry-run 时跳过 LLM 调用
    if dry_run:
        estimated_compressed = len(recent_entries) * 5 + 50  # 近期条目 + 压缩部分估算
        return {
            "status": "dry_run",
            "original_lines": original_lines,
            "compressed_lines": estimated_compressed,
            "old_entries": len(old_entries),
            "recent_entries": len(recent_entries),
        }

    if archive_only:
        # 仅归档模式：不调用 LLM，直接保留近期条目 + 归档旧条目
        compressed = {
            "key_judgments": "",
            "core_contradictions": "",
            "investment_thesis": "",
            "quarterly_summary": "",
        }
    else:
        # 用 LLM 压缩旧条目
        compressed = compress_with_llm(
            old_entries, recent_entries, entity_name, llm_client
        )
        if not compressed:
            return {"status": "error", "reason": "llm_failed", "lines": original_lines}

    compressed_content = build_compressed_content(
        frontmatter, sections, compressed, recent_entries, entity_name, len(old_entries)
    )
    compressed_lines = len(compressed_content.splitlines())

    # 归档旧条目
    archive_dir = wiki_path.parent / "archive"
    archive_path = (
        archive_dir
        / f"{wiki_path.stem}_timeline_{datetime.now().strftime('%Y%m%d')}.md"
    )
    archive_entries(old_entries, archive_path, entity_name)

    # 写入压缩后的内容
    wiki_path.write_text(compressed_content, encoding="utf-8")

    return {
        "status": "success",
        "original_lines": original_lines,
        "compressed_lines": compressed_lines,
        "old_entries_archived": len(old_entries),
        "recent_entries_kept": len(recent_entries),
        "archive_path": str(archive_path),
    }


def find_oversized_pages(
    threshold: int = 500, company_filter: Optional[str] = None
) -> List[Tuple[str, str, Path]]:
    """
    查找超过行数阈值的 wiki 页面

    Returns:
        [(entity_type, entity_name, wiki_path), ...]
    """
    targets = []

    # 公司 wiki
    companies_dir = WIKI_ROOT / "companies"
    if companies_dir.exists():
        for d in companies_dir.iterdir():
            if not d.is_dir():
                continue
            if company_filter and d.name != company_filter:
                continue
            wiki_dir = d / "wiki"
            if not wiki_dir.exists():
                continue
            for wiki in wiki_dir.glob("*.md"):
                if "_slides" in wiki.name:
                    continue
                if count_lines(wiki) > threshold:
                    targets.append(("company", d.name, wiki))

    # 行业 wiki
    if not company_filter:
        sectors_dir = WIKI_ROOT / "sectors"
        if sectors_dir.exists():
            for d in sectors_dir.iterdir():
                if not d.is_dir():
                    continue
                wiki_dir = d / "wiki"
                if not wiki_dir.exists():
                    continue
                for wiki in wiki_dir.glob("*.md"):
                    if "_slides" in wiki.name:
                        continue
                    if count_lines(wiki) > threshold:
                        targets.append(("sector", d.name, wiki))

    # 按行数降序排列
    targets.sort(key=lambda t: count_lines(t[2]), reverse=True)
    return targets


def main():
    parser = argparse.ArgumentParser(description="知识压缩机制")
    parser.add_argument("--company", type=str, help="只压缩指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只报告不执行")
    parser.add_argument(
        "--threshold", type=int, default=500, help="行数阈值（默认 500）"
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=RECENT_DAYS,
        help=f"保留近期条目的天数（默认 {RECENT_DAYS}）",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="仅归档旧条目，不调用 LLM 生成摘要",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  知识压缩（Phase 3）")
    if args.archive_only:
        print("  模式: 仅归档（无 LLM）")
    print("=" * 50)

    targets = find_oversized_pages(args.threshold, args.company)
    print(f"\n  超过 {args.threshold} 行的页面: {len(targets)}")

    if not targets:
        print("  无需压缩")
        return

    llm_client = get_llm_client() if not args.archive_only else None

    success = 0
    errors = 0
    skipped = 0
    total_original = 0
    total_compressed = 0
    reduction = 0.0

    for i, (etype, name, wiki) in enumerate(targets, 1):
        lines = count_lines(wiki)
        print(f"\n[{i}/{len(targets)}] {name}/{wiki.name} ({lines} 行)")

        result = consolidate_page(
            wiki, name, llm_client, dry_run=args.dry_run, archive_only=args.archive_only
        )
        status = result["status"]

        if status == "success":
            success += 1
            total_original += result["original_lines"]
            total_compressed += result["compressed_lines"]
            print(
                f"  -> OK | {result['original_lines']} -> {result['compressed_lines']} 行, "
                f"归档 {result['old_entries_archived']} 条, 保留 {result['recent_entries_kept']} 条"
            )
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | {result['original_lines']} -> ~{result['compressed_lines']} 行, "
                f"旧条目: {result['old_entries']}, 近期: {result['recent_entries']}"
            )
        elif status == "skip":
            skipped += 1
            reason = result.get("reason", "")
            print(f"  -> SKIP | {reason}")
        else:
            errors += 1
            reason = result.get("reason", "")
            print(f"  -> ERR | {reason}")

    print(f"\n{'=' * 50}")
    print(f"  完成: {success} 成功, {skipped} 跳过, {errors} 错误")
    if success > 0:
        print(f"  总行数: {total_original} -> {total_compressed}")
        reduction = (1 - total_compressed / total_original) * 100
        print(f"  压缩率: {reduction:.1f}%")
    print(f"{'=' * 50}")

    if not args.dry_run and success > 0:
        append_log(
            "consolidate",
            f"压缩 {success} 个页面, 总行数 {total_original} -> {total_compressed}, 压缩率 {reduction:.1f}%",
        )

    print("=" * 50)
    print("  知识压缩（Phase 3）")
    print("=" * 50)

    targets = find_oversized_pages(args.threshold, args.company)
    print(f"\n  超过 {args.threshold} 行的页面: {len(targets)}")

    if not targets:
        print("  无需压缩")
        return

    llm_client = get_llm_client()

    success = 0
    errors = 0
    skipped = 0
    total_original = 0
    total_compressed = 0

    for i, (etype, name, wiki) in enumerate(targets, 1):
        lines = count_lines(wiki)
        print(f"\n[{i}/{len(targets)}] {name}/{wiki.name} ({lines} 行)")

        result = consolidate_page(wiki, name, llm_client, dry_run=args.dry_run)
        status = result["status"]

        if status == "success":
            success += 1
            total_original += result["original_lines"]
            total_compressed += result["compressed_lines"]
            print(
                f"  -> OK | {result['original_lines']} -> {result['compressed_lines']} 行, "
                f"归档 {result['old_entries_archived']} 条, 保留 {result['recent_entries_kept']} 条"
            )
        elif status == "dry_run":
            print(
                f"  -> DRY | {result['original_lines']} -> {result['compressed_lines']} 行, "
                f"将归档 {result['old_entries']} 条, 保留 {result['recent_entries']} 条"
            )
        elif status == "skip":
            skipped += 1
            print(
                f"  -> SKIP | {result.get('reason', 'unknown')} "
                f"(旧:{result.get('old_entries', 0)}, 近:{result.get('recent_entries', 0)})"
            )
        else:
            errors += 1
            print(f"  -> ERR | {result.get('reason', 'unknown')}")

    print("\n" + "=" * 50)
    print("  压缩报告")
    print("=" * 50)
    print(f"  处理: {success} 成功, {skipped} 跳过, {errors} 错误")
    if total_original > 0:
        print(
            f"  行数: {total_original} -> {total_compressed} "
            f"(减少 {total_original - total_compressed} 行, "
            f"{(total_original - total_compressed) * 100 // total_original}%)"
        )

    if not args.dry_run and success > 0:
        append_log(
            "enrich",
            f"知识压缩: {success} 页面, {total_original} -> {total_compressed} 行",
        )


if __name__ == "__main__":
    main()
