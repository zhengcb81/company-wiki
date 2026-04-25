#!/usr/bin/env python3
"""
批量补全 wiki 页面的综合评估。
扫描缺少评估的页面，用 LLM 基于时间线条目生成评估。
"""

import sys
import math
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from common import WIKI_ROOT

from llm_client import get_llm_client
from prompts import build_assessment_prompt
from graph import Graph


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
                if (
                    l
                    and not l.startswith("##")
                    and l not in ["（暂无）", "（待补充）", ""]
                ):
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
        main_assessment = section_body[: history_match.start()].strip()
        history_text = history_match.group(1)

        # 解析已有的历史条目: > **[date]** \n > content...
        entry_pat = (
            r"> \*\*\[(\d{4}-\d{2}-\d{2})\]\*\*[^\S\n]*\n(.*?)(?=\n> \*\*\[|\n*$)"
        )
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
            after_timeline = content[timeline_pos + len("## 时间线") :]
            next_section = after_timeline.find("\n## ")
            if next_section >= 0:
                insert_pos = timeline_pos + len("## 时间线") + next_section
                content = (
                    content[:insert_pos]
                    + "\n\n## 综合评估\n"
                    + assessment
                    + "\n"
                    + content[insert_pos:]
                )
            else:
                content = content.rstrip() + f"\n\n## 综合评估\n{assessment}\n"
        else:
            content = content.rstrip() + f"\n\n## 综合评估\n{assessment}\n"

    wiki_path.write_text(content, encoding="utf-8")
    return True


def extract_predictions(assessment_text: str) -> list:
    """
    从评估文本中提取可验证的预测。

    Returns:
        [{"prediction": str, "metric": str, "confidence": str}, ...]
    """
    predictions = []

    # 查找包含预测性关键词的句子
    prediction_keywords = ["预计", "预期", "有望", "可能", "或将", "目标", "计划"]

    lines = assessment_text.split("\n")
    for line in lines:
        line_clean = line.strip().lstrip("> ").strip()
        if not line_clean:
            continue

        # 检查是否包含预测关键词
        if any(kw in line_clean for kw in prediction_keywords):
            # 尝试提取数值
            import re

            numbers = re.findall(r"(\d+\.?\d*)\s*%?", line_clean)

            predictions.append(
                {
                    "prediction": line_clean[:200],
                    "metric": numbers[0] if numbers else "qualitative",
                    "confidence": "medium",
                }
            )

    return predictions[:5]  # 最多提取 5 个预测


def verify_predictions(wiki_path: Path) -> list:
    """
    验证 wiki 页面中之前的预测。

    Returns:
        [{"prediction": str, "actual": str, "deviation": str}, ...]
    """
    if not wiki_path.exists():
        return []

    content = wiki_path.read_text(encoding="utf-8")

    # 提取历史评估中的预测
    _, history_entries = _extract_old_assessment(content)
    if not history_entries:
        return []

    # 获取最新条目作为"实际结果"
    entries = extract_timeline_entries(wiki_path)
    if not entries:
        return []

    latest_entries_text = "\n".join(
        [
            f"{e['date']}: {e['title']} - {' '.join(e.get('points', []))}"
            for e in entries[-5:]  # 最近 5 个条目
        ]
    )

    verifications = []

    # 对每个历史评估条目，检查是否有预测被验证
    for history in history_entries[:3]:  # 只检查最近 3 个历史评估
        predictions = extract_predictions(history["text"])
        for pred in predictions:
            # 简单验证：检查最新条目中是否包含预测提到的数值
            if pred["metric"] != "qualitative":
                if pred["metric"] in latest_entries_text:
                    verifications.append(
                        {
                            "prediction": pred["prediction"],
                            "actual": f"在最新条目中找到相关数值 {pred['metric']}",
                            "deviation": "待详细对比",
                            "date": history["date"],
                        }
                    )

    return verifications


def calculate_time_weight(days_old: int, info_type: str = "general") -> float:
    """
    计算时间衰减权重。

    Args:
        days_old: 距离今天的天数
        info_type: 信息类型（financial/order/tech/strategy/risk）

    Returns:
        权重值 (0.0-1.0)
    """
    import math

    # 不同信息类型的半衰期（天）
    half_lives = {
        "financial": 90,  # 财务数据：90天
        "order": 180,  # 订单/产能：180天
        "tech": 365,  # 技术突破：365天
        "strategy": 730,  # 战略/管理层：730天
        "risk": 180,  # 风险事件：180天
        "general": 180,  # 默认：180天
    }

    half_life = half_lives.get(info_type, 180)
    weight = math.exp(-days_old / half_life)
    return max(0.1, min(1.0, weight))  # 最低保留 0.1 权重


def _detect_info_type(entry: Dict) -> str:
    """从条目内容检测信息类型"""
    text = entry.get("title", "") + " " + " ".join(entry.get("points", []))
    text_lower = text.lower()

    if any(
        kw in text_lower for kw in ["营收", "利润", "毛利率", "净利率", "eps", "财报"]
    ):
        return "financial"
    elif any(kw in text_lower for kw in ["订单", "合同", "中标", "产能", "产量"]):
        return "order"
    elif any(kw in text_lower for kw in ["专利", "技术", "研发", "突破", "创新"]):
        return "tech"
    elif any(
        kw in text_lower for kw in ["战略", "管理层", "ceo", "高管", "并购", "收购"]
    ):
        return "strategy"
    elif any(kw in text_lower for kw in ["风险", "下滑", "下降", "亏损", "警告"]):
        return "risk"
    return "general"


def generate_assessment(
    wiki_path: Path, entity_name: str, topic_name: str, core_questions: list, llm_client
) -> str:
    """用 LLM 生成综合评估（带时间衰减权重）"""
    entries = extract_timeline_entries(wiki_path)
    if not entries:
        return ""

    # 计算每个条目的时间权重
    today = datetime.now()
    weighted_entries = []
    for entry in entries:
        try:
            entry_date = datetime.strptime(entry.get("date", "2024-01-01"), "%Y-%m-%d")
            days_old = (today - entry_date).days
            info_type = _detect_info_type(entry)
            weight = calculate_time_weight(days_old, info_type)
            entry["weight"] = weight
            entry["days_old"] = days_old
            weighted_entries.append(entry)
        except (ValueError, TypeError):
            entry["weight"] = 0.5
            weighted_entries.append(entry)

    # 按权重排序，优先保留高权重条目
    weighted_entries.sort(key=lambda e: e.get("weight", 0), reverse=True)

    # 限制条目数量，避免超出 token 限制
    if len(weighted_entries) > 30:
        weighted_entries = weighted_entries[:30]

    # 在 prompt 中标注权重
    prompt = build_weighted_assessment_prompt(
        weighted_entries, entity_name, topic_name, core_questions
    )

    response = llm_client.chat_with_retry(
        prompt,
        "你是一个专业的上市公司研究分析助手。",
    )

    if response.success:
        assessment = response.content.strip()

        # 检查是否需要添加过时警告
        max_days_old = max((e.get("days_old", 0) for e in weighted_entries), default=0)
        if max_days_old > 90:
            latest_date = min(
                (
                    e.get("date", "")
                    for e in weighted_entries
                    if e.get("days_old", 0) == max_days_old
                ),
                default="",
            )
            stale_warning = f"> ⚠️ **信息时效性提醒**：本评估基于 {latest_date} 及之前的信息（距今 {max_days_old} 天），部分判断可能已过时。\n> \n"
            assessment = stale_warning + assessment

        return assessment
    return ""


def build_weighted_assessment_prompt(
    entries: list, entity_name: str, topic_name: str, core_questions: list
) -> str:
    """构建带权重的评估 prompt"""
    entries_text = ""
    for e in entries:
        weight = e.get("weight", 0.5)
        days_old = e.get("days_old", 0)
        weight_label = "🔥" if weight > 0.8 else "⚡" if weight > 0.5 else "📌"

        entries_text += f"\n[{weight_label} 权重: {weight:.2f} | {days_old}天前] {e['date']} | {e['title']}\n"
        for p in e.get("points", []):
            entries_text += f"  - {p}\n"

    core_q_text = "\n".join([f"{i + 1}. {q}" for i, q in enumerate(core_questions[:5])])

    return f"""请基于以下时间线条目，生成"{entity_name}"（{topic_name}）的综合评估。

【重要提示】
- 标记 🔥 的条目权重最高（近期重要信息），应作为判断的主要依据
- 标记 ⚡ 的条目权重中等（中期信息），作为辅助参考
- 标记 📌 的条目权重较低（远期信息），仅作背景参考
- 请优先基于高权重条目形成判断，不要平均对待所有信息

核心问题：
{core_q_text}

时间线条目（已按重要性排序）：
{entries_text}

请生成简洁的综合评估（2-4 段），包括：
1. 当前状态判断（基于最新高权重信息）
2. 关键趋势（注意时间衰减，远期信息权重降低）
3. 主要风险或机会
4. 对核心问题的回答

格式要求：
- 使用 markdown 引用块格式（每行以 > 开头）
- 只输出评估内容，不要输出标题"综合评估"
- 尽量简洁，不超过 300 字"""


def main():
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

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
                print(
                    f"  -> OK | {len(assessment)} chars, based on {len(entries)} entries"
                )
                # 添加到审核队列（低风险自动批准）
                try:
                    from review_queue import ReviewQueue

                    rq = ReviewQueue()
                    rq_id = rq.add_entry(
                        risk="low",
                        op_type="assess",
                        entity=name,
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
