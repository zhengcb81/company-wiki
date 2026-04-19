#!/usr/bin/env python3
"""
log_writer.py — 统一日志写入模块
所有脚本通过此模块写入 log.md，确保格式一致且可 grep。

格式: ## [YYYY-MM-DD HH:MM] {op_type} | {message}
用法: grep "^## \[" log.md | tail -5
"""

import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
LOG_PATH = WIKI_ROOT / "log.md"

VALID_OPS = frozenset({
    "init", "collect_news", "ingest", "lint", "query",
    "enrich", "download_reports", "graph_update", "index_regen",
})


def append_log(op_type: str, message: str, details: list = None,
               log_path: Path = None):
    """
    结构化追加日志到 log.md。

    Args:
        op_type: 操作类型（必须在 VALID_OPS 中）
        message: 一行摘要消息
        details: 可选的详细条目列表
        log_path: 可选，覆盖默认日志路径
    """
    if op_type not in VALID_OPS:
        print(f"Warning: unknown op_type '{op_type}', "
              f"expected one of: {', '.join(sorted(VALID_OPS))}",
              file=sys.stderr)

    path = log_path or LOG_PATH

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] {op_type} | {message}\n"

    if details:
        for d in details:
            entry += f"- {d}\n"

    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"

    content += entry
    path.write_text(content, encoding="utf-8")
