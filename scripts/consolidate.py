#!/usr/bin/env python3
"""
consolidate.py — 知识压缩机制

当 wiki 页面过于庞大时（>500行），用 LLM 将时间线条目压缩为：
- 关键判断（5-10条）
- 核心矛盾（3条）
- 投资论点（1条）

旧条目归档到 archive/ 子目录，保持 wiki 页面在人类可读范围内。

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
from datetime import datetime
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
            fm = content[:end + 3]
            body = content[end + 3:].strip()
            return fm, body
    return "", content


def extract_timeline_entries(content: str) -> List[Dict]:
    """提取所有时间线条目"""
    entries = []
    pattern = re.compile(r'(### \d{4}-\d{2}-\d{2} \| .+?)(?=\n### |\n## |\Z)', re.DOTALL)
    for match in pattern.finditer(content):
        block = match.group(0).strip()
        # 提取日期和标题
        header_match = re.match(r'### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)', block)
        if header_match:
            entries.append({
                "date": header_match.group(1),
                "source_type": header_match.group(2),
                "title": header_match.group(3),
                "block": block,
            })
    return entries


def extract_sections(content: str) -> Dict[str, str]:
    """提取各 ## section 的内容"""
    sections = {}
    parts = re.split(r'^(## .+)$', content, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        section_name = header[3:].strip()
        sections[section_name] = body
    return sections


def compress_with_llm(entries: List[Dict], entity_name: str, llm_client) -> Optional[str]:
    """
    用 LLM 压缩时间线条目为结构化摘要

    Returns:
        压缩后的 markdown 文本
    """
    if not entries:
        return None

    # 构建条目摘要（限制 token 用量）
    entry_texts = []
    for e in entries[:100]:  # 最多取 100 个条目
        entry_texts.append(f"- [{e['date']}] {e['title']}")
    entries_str = "\n".join(entry_texts)

    prompt = f"""你是一名资深的上市公司研究分析师。以下是关于"{entity_name}"的 {len(entries)} 条时间线条目。

请将这些条目压缩为以下结构：

## 关键判断
列出 5-10 个最重要的判断/结论（每个一行，用 `- ` 开头）。这些应该是从时间线中提炼出的最核心的洞察，而不是简单的事实罗列。

## 核心矛盾
列出 2-3 个当前最值得关注的矛盾或分歧（每个一行，用 `- ` 开头）。例如：营收增长但毛利率下滑、订单饱满但产能不足等。

## 投资论点
用 1-2 段话总结当前的投资论点（看多或看空的核心逻辑）。

时间线条目：
{entries_str[:8000]}

请直接输出 markdown 格式，不要包含 ```markdown 代码块标记。"""

    try:
        response = llm_client.chat(prompt)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        print(f"  [LLM ERR] {e}")

    return None


def archive_entries(content: str, archive_path: Path) -> bool:
    """将时间线条目归档到指定文件"""
    entries = extract_timeline_entries(content)
    if not entries:
        return False

    archive_content = f"# 归档时间线条目\n\n> 归档时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n> 条目数: {len(entries)}\n\n"
    for e in entries:
        archive_content += e["block"] + "\n\n"

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(archive_content, encoding="utf-8")
    return True


def build_compressed_content(frontmatter: str, sections: Dict[str, str],
                             compressed: str, entity_name: str) -> str:
    """构建压缩后的 wiki 内容"""
    # 更新 frontmatter 中的 last_updated
    today = datetime.now().strftime("%Y-%m-%d")
    if "last_updated:" in frontmatter:
        frontmatter = re.sub(
            r'last_updated:\s*"?[^"\n]+"?',
            f'last_updated: {today}',
            frontmatter
        )

    # 保留非时间线 sections（核心问题、综合评估、相关页面等）
    parts = [frontmatter, ""]

    # 核心问题（保留）
    if "核心问题" in sections:
        parts.append("## 核心问题")
        parts.append(sections["核心问题"])
        parts.append("")

    # 压缩后的内容
    parts.append(compressed)
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

    # 添加归档说明
    parts.append("---")
    parts.append(f"> 本页面已压缩归档。原始 {len(extract_timeline_entries(sections.get('时间线', '')))} 条时间线条目已归档至 `archive/` 目录。")
    parts.append(f"> 压缩时间: {today}")

    return "\n".join(parts)


def consolidate_page(wiki_path: Path, entity_name: str, llm_client,
                     dry_run: bool = False) -> Dict:
    """
    压缩单个 wiki 页面

    Returns:
        操作结果字典
    """
    content = wiki_path.read_text(encoding="utf-8")
    original_lines = len(content.splitlines())

    frontmatter, body = extract_frontmatter(content)
    sections = extract_sections(body)
    entries = extract_timeline_entries(content)

    if not entries:
        return {"status": "skip", "reason": "no_entries", "lines": original_lines}

    # dry-run 时跳过 LLM 调用
    if dry_run:
        return {
            "status": "dry_run",
            "original_lines": original_lines,
            "compressed_lines": original_lines // 3,  # 估算压缩后行数
            "entries_archived": len(entries),
        }

    # 用 LLM 压缩
    compressed = compress_with_llm(entries, entity_name, llm_client)
    if not compressed:
        return {"status": "error", "reason": "llm_failed", "lines": original_lines}

    compressed_content = build_compressed_content(frontmatter, sections, compressed, entity_name)
    compressed_lines = len(compressed_content.splitlines())

    # 归档旧条目
    archive_dir = wiki_path.parent / "archive"
    archive_path = archive_dir / f"{wiki_path.stem}_timeline_{datetime.now().strftime('%Y%m%d')}.md"
    archive_entries(content, archive_path)

    # 写入压缩后的内容
    wiki_path.write_text(compressed_content, encoding="utf-8")

    return {
        "status": "success",
        "original_lines": original_lines,
        "compressed_lines": compressed_lines,
        "entries_archived": len(entries),
        "archive_path": str(archive_path),
    }


def find_oversized_pages(threshold: int = 500,
                         company_filter: Optional[str] = None) -> List[Tuple[str, str, Path]]:
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
    parser.add_argument("--threshold", type=int, default=500,
                        help="行数阈值（默认 500）")
    args = parser.parse_args()

    print("=" * 50)
    print("  知识压缩")
    print("=" * 50)

    targets = find_oversized_pages(args.threshold, args.company)
    print(f"\n  超过 {args.threshold} 行的页面: {len(targets)}")

    if not targets:
        print("  无需压缩")
        return

    llm_client = get_llm_client()

    success = 0
    errors = 0
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
            print(f"  -> OK | {result['original_lines']} -> {result['compressed_lines']} 行, "
                  f"{result['entries_archived']} 条目归档")
        elif status == "dry_run":
            success += 1
            total_original += result["original_lines"]
            total_compressed += result["compressed_lines"]
            print(f"  -> DRY | {result['original_lines']} -> {result['compressed_lines']} 行, "
                  f"{result['entries_archived']} 条目将归档")
        elif status == "skip":
            print(f"  -> SKIP | {result['reason']}")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('reason', 'unknown')}")

    print("\n" + "=" * 50)
    print("  压缩报告")
    print("=" * 50)
    print(f"  处理: {success} 成功, {errors} 错误")
    if total_original > 0:
        print(f"  行数: {total_original} -> {total_compressed} "
              f"(减少 {total_original - total_compressed} 行, "
              f"{(total_original - total_compressed) * 100 // total_original}%)")

    if not args.dry_run and success > 0:
        append_log("enrich", f"知识压缩: {success} 页面, {total_original} -> {total_compressed} 行")


if __name__ == "__main__":
    main()
