#!/usr/bin/env python3
"""
review_queue.py — 审核队列

管理 LLM 生成内容的审核流程。所有高风险操作（评估修改、条目删除等）
进入审核队列，等待人工批准或拒绝。

数据存储: review_queue.md（项目根目录，human-editable markdown）

用法：
    python scripts/review_queue.py --list              # 列出待审核
    python scripts/review_queue.py --approve RQ-001    # 批准
    python scripts/review_queue.py --reject RQ-002     # 拒绝
    python scripts/review_queue.py --stats             # 统计
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Windows 控制台 UTF-8 编码
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# ── 常量 ──────────────────────────────

RISK_LEVELS = ("high", "medium", "low")
STATUS_PENDING = "⏳ 待审核"
STATUS_APPROVED = "✅ 已批准"
STATUS_REJECTED = "❌ 已拒绝"
SECTION_NAMES = {
    STATUS_PENDING: "待审核",
    STATUS_APPROVED: "已批准",
    STATUS_REJECTED: "已拒绝",
}


# ── 审核队列类 ─────────────────────────

class ReviewQueue:
    """审核队列 — 管理 review_queue.md"""

    def __init__(self, queue_path: Optional[Path] = None):
        self.queue_path = queue_path or WIKI_ROOT / "review_queue.md"

    def _ensure_file(self):
        """确保 review_queue.md 存在"""
        if not self.queue_path.exists():
            content = "# 审核队列\n\n> LLM 生成内容的审核入口。\n> 高风险操作进入待审核，人工批准后执行。\n\n## 待审核\n\n_暂无条目_\n\n## 已批准\n\n_暂无条目_\n\n## 已拒绝\n\n_暂无条目_\n"
            self.queue_path.write_text(content, encoding="utf-8")
            return content
        return self.queue_path.read_text(encoding="utf-8")

    def _parse_entries(self, content: str) -> Dict[str, List[Dict]]:
        """解析 review_queue.md 中的条目"""
        sections: Dict[str, List[Dict]] = {
            "待审核": [],
            "已批准": [],
            "已拒绝": [],
        }

        current_section = None
        current_entry = None

        for line in content.split("\n"):
            # 检测章节标题
            if line.startswith("## "):
                section_name = line[3:].strip()
                # 章节切换时，先保存当前条目
                if current_entry and current_section:
                    sections[current_section].append(current_entry)
                    current_entry = None
                if section_name in sections:
                    current_section = section_name
                else:
                    current_section = None
                continue

            # 检测条目开始
            entry_match = re.match(r'^### (RQ-\d+) \| (\d{4}-\d{2}-\d{2}) \| (\w+) \| (\w+) \| (.+)', line)
            if entry_match and current_section:
                if current_entry:
                    sections[current_section].append(current_entry)
                current_entry = {
                    "id": entry_match.group(1),
                    "date": entry_match.group(2),
                    "risk": entry_match.group(3),
                    "op_type": entry_match.group(4),
                    "entity": entry_match.group(5),
                    "fields": {},
                }
                continue

            if current_entry is None:
                continue

            # 解析字段
            field_match = re.match(r'\*\*(.+?)\*\*:\s*(.+)', line)
            if field_match:
                key = field_match.group(1).strip()
                value = field_match.group(2).strip()
                current_entry["fields"][key] = value

        # 最后一个条目
        if current_entry and current_section:
            sections[current_section].append(current_entry)

        return sections

    def _next_id(self, content: str) -> str:
        """生成下一个 RQ ID"""
        existing = re.findall(r'RQ-(\d+)', content)
        if not existing:
            return "RQ-001"
        max_num = max(int(n) for n in existing)
        return f"RQ-{max_num + 1:03d}"

    def add_entry(self, risk: str, op_type: str, entity: str,
                  description: str, content_text: str = "",
                  source: str = "") -> str:
        """
        添加审核条目。

        Args:
            risk: 风险等级 (high/medium/low)
            op_type: 操作类型 (ingest/assess/delete)
            entity: 实体名称（公司名或行业名）
            description: 操作描述
            content_text: 操作内容
            source: 来源文件路径

        Returns:
            条目 ID (如 RQ-001)
        """
        if risk not in RISK_LEVELS:
            risk = "medium"

        content = self._ensure_file()
        rq_id = self._next_id(content)

        # 构建条目文本
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry_lines = [
            f"### {rq_id} | {now[:10]} | {risk} | {op_type} | {entity}",
            f"**操作**: {description}",
        ]
        if content_text:
            entry_lines.append(f"**内容**: {content_text[:200]}")
        entry_lines.append(f"**状态**: {STATUS_PENDING}")
        if source:
            entry_lines.append(f"**来源**: {source}")
        entry_lines.append("")

        entry_block = "\n".join(entry_lines)

        # 插入到"待审核"章节
        placeholder = "## 待审核\n\n_暂无条目_"
        if placeholder in content:
            content = content.replace(placeholder, f"## 待审核\n\n{entry_block}")
        else:
            # 插入到第一个 ## 待审核 之后
            content = content.replace("## 待审核", f"## 待审核\n\n{entry_block}", 1)

        self.queue_path.write_text(content, encoding="utf-8")
        print(f"  添加审核条目: {rq_id}")
        return rq_id

    def list_pending(self) -> List[Dict]:
        """列出所有待审核条目"""
        content = self._ensure_file()
        sections = self._parse_entries(content)
        return sections.get("待审核", [])

    def get_stats(self) -> Dict:
        """获取队列统计"""
        content = self._ensure_file()
        sections = self._parse_entries(content)

        pending = sections.get("待审核", [])
        approved = sections.get("已批准", [])
        rejected = sections.get("已拒绝", [])

        risk_counts = {"high": 0, "medium": 0, "low": 0}
        for entry in pending:
            risk = entry.get("risk", "low")
            if risk in risk_counts:
                risk_counts[risk] += 1

        return {
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "total": len(pending) + len(approved) + len(rejected),
            "risk_counts": risk_counts,
        }

    def _move_entry(self, rq_id: str, target_section: str,
                    new_status: str, reason: str = "") -> bool:
        """
        移动条目到目标章节。

        Args:
            rq_id: 条目 ID
            target_section: 目标章节名
            new_status: 新状态标记
            reason: 原因（用于拒绝）

        Returns:
            True 如果成功
        """
        content = self._ensure_file()

        # 查找条目
        entry_match = re.search(
            rf'^### {re.escape(rq_id)} \| .+$\n(?:^\*\*.+$\n?)*',
            content,
            re.MULTILINE
        )

        if not entry_match:
            print(f"  未找到条目: {rq_id}")
            return False

        entry_block = entry_match.group(0)

        # 更新状态行
        if reason:
            entry_block = re.sub(
                r'\*\*状态\*\*: .+',
                f"**状态**: {new_status}",
                entry_block
            )
            entry_block += f"**原因**: {reason}\n"
        else:
            entry_block = re.sub(
                r'\*\*状态\*\*: .+',
                f"**状态**: {new_status}",
                entry_block
            )

        # 从当前位置移除
        content = content[:entry_match.start()] + content[entry_match.end():]

        # 追加到目标章节
        section_header = f"## {target_section}"
        section_placeholder = f"{section_header}\n\n_暂无条目_"

        if section_placeholder in content:
            content = content.replace(section_placeholder,
                                      f"{section_header}\n\n{entry_block}")
        else:
            # 在章节标题后插入
            content = content.replace(section_header,
                                      f"{section_header}\n\n{entry_block}", 1)

        self.queue_path.write_text(content, encoding="utf-8")
        return True

    def approve(self, rq_id: str) -> bool:
        """批准条目"""
        return self._move_entry(rq_id, "已批准", STATUS_APPROVED)

    def reject(self, rq_id: str, reason: str = "") -> bool:
        """拒绝条目"""
        return self._move_entry(rq_id, "已拒绝", STATUS_REJECTED, reason)


# ── CLI ─────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="审核队列管理")
    parser.add_argument("--list", action="store_true", help="列出待审核条目")
    parser.add_argument("--approve", type=str, help="批准条目 (RQ-XXX)")
    parser.add_argument("--reject", type=str, help="拒绝条目 (RQ-XXX)")
    parser.add_argument("--reason", type=str, help="拒绝原因")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--add", action="store_true", help="添加审核条目")
    parser.add_argument("--risk", type=str, default="medium",
                        choices=RISK_LEVELS, help="风险等级")
    parser.add_argument("--op-type", type=str, default="ingest",
                        help="操作类型")
    parser.add_argument("--entity", type=str, default="",
                        help="实体名称")
    parser.add_argument("--desc", type=str, default="",
                        help="操作描述")
    parser.add_argument("--source", type=str, default="",
                        help="来源文件")

    args = parser.parse_args()

    queue = ReviewQueue()

    if args.list:
        entries = queue.list_pending()
        print(f"\n待审核条目 ({len(entries)}):")
        print("=" * 50)
        if not entries:
            print("  (空)")
        for entry in entries:
            print(f"\n  {entry['id']} | {entry['risk']} | {entry['op_type']} | {entry['entity']}")
            for key, value in entry.get("fields", {}).items():
                print(f"    {key}: {value}")

    elif args.approve:
        success = queue.approve(args.approve)
        if success:
            print(f"  ✅ {args.approve} 已批准")
        else:
            print(f"  ❌ {args.approve} 批准失败")

    elif args.reject:
        success = queue.reject(args.reject, args.reason or "")
        if success:
            print(f"  ❌ {args.reject} 已拒绝" +
                  (f" (原因: {args.reason})" if args.reason else ""))
        else:
            print(f"  ❌ {args.reject} 拒绝失败")

    elif args.stats:
        stats = queue.get_stats()
        print("\n审核队列统计:")
        print("=" * 50)
        print(f"  待审核: {stats['pending']}")
        print(f"  已批准: {stats['approved']}")
        print(f"  已拒绝: {stats['rejected']}")
        print(f"  总计:   {stats['total']}")
        print(f"\n  待审核风险分布:")
        for risk, count in stats['risk_counts'].items():
            print(f"    {risk}: {count}")

    elif args.add:
        if not args.entity or not args.desc:
            print("错误: --add 需要 --entity 和 --desc")
            return
        queue.add_entry(args.risk, args.op_type, args.entity,
                        args.desc, source=args.source)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
