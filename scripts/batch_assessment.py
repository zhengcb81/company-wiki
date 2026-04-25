#!/usr/bin/env python3
"""
批量补全 wiki 页面的综合评估。
扫描缺少评估的页面，用 LLM 基于时间线条目生成评估。
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from llm_client import get_llm_client
from prompts import build_assessment_prompt
from graph import Graph

WIKI_ROOT = Path(__file__).resolve().parent.parent


def has_assessment(wiki_path: Path) -> bool:
    """检查 wiki 是否已有综合评估"""
    if not wiki_path.exists():
        return False
    content = wiki_path.read_text(encoding="utf-8")
    if "## 综合评估" not in content:
        return False
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "## 综合评估":
            for j in range(i + 1, min(i + 5, len(lines))):
                l = lines[j].strip()
                if l and not l.startswith("##") and l not in ["（暂无）", "（待补充）", ""]:
                    return True
            return False
    return False


def is_assessment_stale(wiki_path: Path, stale_days: int = 60) -> bool:
    """
    检查综合评估是否过时（基于 frontmatter 的 last_updated）

    Args:
        wiki_path: wiki 文件路径
        stale_days: 超过多少天算过时

    Returns:
        True 如果评估过时
    """
    if not wiki_path.exists():
        return True
    content = wiki_path.read_text(encoding="utf-8")

    # 从 frontmatter 提取 last_updated
    import re
    match = re.search(r'last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
    if not match:
        return True

    last_updated = match.group(1)
    try:
        last_date = datetime.strptime(last_updated, "%Y-%m-%d")
        days_old = (datetime.now() - last_date).days
        return days_old > stale_days
    except ValueError:
        return True


def extract_timeline_entries(wiki_path: Path) -> list:
    """从 wiki 提取时间线条目"""
    content = wiki_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    entries = []
    current = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            if current:
                entries.append(current)
            parts = stripped[4:].split(" | ")
            date = parts[0] if parts else ""
            title = parts[2] if len(parts) > 2 else stripped[4:]
            current = {"date": date, "title": title, "points": []}
        elif current and stripped.startswith("- "):
            current["points"].append(stripped[2:])
        elif stripped.startswith("## ") and not stripped.startswith("### "):
            if current:
                entries.append(current)
                current = None

    if current:
        entries.append(current)

    return entries


def _extract_old_assessment(content: str) -> tuple:
    """
    从现有内容中提取旧的综合评估文本和历史评估条目。

    Returns:
        (old_assessment_text, history_entries)
        - old_assessment_text: 旧的评估文本（引用块格式）
        - history_entries: list of {"date": str, "text": str} 已有的历史条目
    """
    import re

    pattern = r"(## 综合评估\n+)([\s\S]*?)(?=\n## |\Z)"
    match = re.search(pattern, content)
    if not match:
        return "", []

    section_body = match.group(2)

    # 检查是否有历史评估子节
    history_pat = r"### 历史评估\n+([\s\S]*)"
    history_match = re.search(history_pat, section_body)
    main_assessment = section_body
    existing_entries = []

    if history_match:
        main_assessment = section_body[:history_match.start()].strip()
        history_text = history_match.group(1)

        # 解析已有的历史条目: > **[date]** \n > content...
        entry_pat = r"> \*\*\[(\d{4}-\d{2}-\d{2})\]\*\*[^\S\n]*\n(.*?)(?=\n> \*\*\[|\n*$)"
        for entry_match in re.finditer(entry_pat, history_text, re.DOTALL):
            date = entry_match.group(1)
            text = entry_match.group(2).strip()
            # 移除 > 引用标记
            text = "\n".join(
                l[2:] if l.startswith("> ") else l[1:] if l.startswith(">") else l
                for l in text.split("\n")
            ).strip()
            existing_entries.append({"date": date, "text": text})
    else:
        main_assessment = section_body.strip()

    return main_assessment, existing_entries


def _build_history_block(history_entries: list, max_history: int = 5) -> str:
    """
    根据历史条目构建历史评估 markdown 块。

    Returns:
        完整的 "### 历史评估\\n..." 字符串，若无条目则返回空字符串
    """
    if not history_entries:
        return ""

    parts = ["\n### 历史评估\n"]
    for entry in history_entries:
        parts.append(f"> **[{entry['date']}]**\n")
        for line in entry["text"].split("\n"):
            stripped = line.strip()
            if stripped:
                if stripped.startswith(">"):
                    parts.append(stripped + "\n")
                else:
                    parts.append(f"> {stripped}\n")
            else:
                parts.append(">\n")
        parts.append("\n")
    return "".join(parts)


def add_assessment_section(wiki_path: Path, assessment: str) -> bool:
    """在 wiki 中添加综合评估 section（带历史归档）"""
    if not wiki_path.exists():
        return False

    content = wiki_path.read_text(encoding="utf-8")

    # 确保评估以引用块格式
    assessment = assessment.strip()
    if not assessment.startswith(">"):
        lines = assessment.split("\n")
        assessment = "\n".join(f"> {l}" if l.strip() else ">" for l in lines)

    # 如果已有综合评估 section，先归档旧评估
    if "## 综合评估" in content:
        old_text, history_entries = _extract_old_assessment(content)

        # 当前旧评估作为最新历史存档
        if old_text:
            today = datetime.now().strftime("%Y-%m-%d")
            history_entries.insert(0, {"date": today, "text": old_text})

        # 限制历史条目数
        history_entries = history_entries[:5]

        # 构建新 section
        history_block = _build_history_block(history_entries)
        new_section = assessment + "\n" + history_block

        # 替换
        import re
        content = re.sub(
            r"(## 综合评估\n+)[\s\S]*?(?=\n## |\Z)",
            lambda m: m.group(1) + new_section + "\n",
            content,
            count=1,
        )
    else:
        # 在时间线之后添加（不带历史）
        timeline_pos = content.find("## 时间线")
        if timeline_pos >= 0:
            after_timeline = content[timeline_pos + len("## 时间线"):]
            next_section = after_timeline.find("\n## ")
            if next_section >= 0:
                insert_pos = timeline_pos + len("## 时间线") + next_section
                content = (
                    content[:insert_pos] + "\n\n## 综合评估\n" + assessment + "\n" +
                    content[insert_pos:]
                )
            else:
                content = content.rstrip() + f"\n\n## 综合评估\n{assessment}\n"
        else:
            content = content.rstrip() + f"\n\n## 综合评估\n{assessment}\n"

    wiki_path.write_text(content, encoding="utf-8")
    return True


def generate_assessment(wiki_path: Path, entity_name: str, topic_name: str,
                        core_questions: list, llm_client) -> str:
    """用 LLM 生成综合评估"""
    entries = extract_timeline_entries(wiki_path)
    if not entries:
        return ""

    # 限制条目数量，避免超出 token 限制
    if len(entries) > 30:
        entries = entries[-30:]

    prompt = build_assessment_prompt(entries, entity_name, topic_name, core_questions)

    response = llm_client.chat_with_retry(
        prompt,
        "你是一个专业的上市公司研究分析助手。",
    )

    if response.success:
        return response.content.strip()
    return ""


def main():
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    graph = Graph(str(WIKI_ROOT / "graph.yaml"))
    llm_client = get_llm_client()
    llm_client._timeout = 120

    print("=" * 50)
    print("  Batch Assessment Generation")
    print("=" * 50)

    # 扫描所有缺少评估的 wiki
    targets = []

    # 公司 wiki
    for d in (WIKI_ROOT / "companies").iterdir():
        if not d.is_dir():
            continue
        wiki_dir = d / "wiki"
        if not wiki_dir.exists():
            continue
        for wiki in wiki_dir.glob("*.md"):
            if "_slides" in wiki.name:
                continue
            if not has_assessment(wiki):
                targets.append(("company", d.name, wiki))

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
                targets.append(("sector", d.name, wiki))

    print(f"\nPages needing assessment: {len(targets)}")

    success = 0
    skipped = 0
    errors = 0

    for i, (etype, name, wiki) in enumerate(targets, 1):
        print(f"\n[{i}/{len(targets)}] {wiki}")

        entries = extract_timeline_entries(wiki)
        if not entries:
            print(f"  -> SKIP | No timeline entries")
            skipped += 1
            continue

        # 获取核心问题
        if etype == "company":
            company = graph.get_company(name)
            questions = company.get("questions", []) if company else []
            topic = "公司动态"
        else:
            sector = graph.get_sector(name)
            questions = sector.get("questions", []) if sector else []
            topic = name

        try:
            assessment = generate_assessment(wiki, name, topic, questions, llm_client)
            if assessment:
                add_assessment_section(wiki, assessment)
                print(f"  -> OK | {len(assessment)} chars, based on {len(entries)} entries")
                # 添加到审核队列（低风险自动批准）
                try:
                    from review_queue import ReviewQueue
                    rq = ReviewQueue()
                    rq_id = rq.add_entry(
                        risk="low", op_type="assess", entity=name,
                        description=f"批量更新综合评估: {wiki.name}",
                        source=str(wiki.relative_to(WIKI_ROOT)),
                    )
                    rq.approve(rq_id)
                except Exception:
                    pass
                success += 1
            else:
                print(f"  -> SKIP | LLM returned empty")
                skipped += 1
        except Exception as e:
            print(f"  -> ERR | {e}")
            errors += 1

    print("\n" + "=" * 50)
    print(f"Done. Success:{success} Skipped:{skipped} Errors:{errors}")
    print("=" * 50)


if __name__ == "__main__":
    main()
