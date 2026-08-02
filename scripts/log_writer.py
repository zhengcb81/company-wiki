#!/usr/bin/env python3
"""
log_writer.py -- 统一日志写入模块
所有脚本通过此模块写入 log.md，确保格式一致且可 grep。

格式: ## [YYYY-MM-DD HH:MM] {level} {op_type} | {message}

新增功能：
- 日志级别：INFO / WARN / ERROR（默认 INFO）
- 自动轮转：超过 MAX_LOG_SIZE 时自动分割
- 归档清理：保留最近的 MAX_ARCHIVES 个归档
"""

import shutil
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT

LOG_PATH = WIKI_ROOT / "log.md"

# 轮转配置
MAX_LOG_SIZE = 500 * 1024  # 500KB 触发轮转
MAX_ARCHIVES = 10          # 保留最近 10 个归档

VALID_OPS = frozenset({
    "init", "collect_news", "ingest", "lint", "query",
    "enrich", "download_reports", "graph_update", "index_regen",
    "distill", "assess", "detect", "discover", "evolve",
})

LOG_HEADER = """# 知识库操作日志

> Append-only 日志，记录所有 ingest、query、lint 操作。
> 格式：`## [YYYY-MM-DD HH:MM] {LEVEL} {操作类型} | {描述}`
"""


def _rotate_if_needed(log_path: Path):
    """当日志超过大小时自动轮转"""
    if not log_path.exists():
        return
    size = log_path.stat().st_size
    if size < MAX_LOG_SIZE:
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = log_path.with_name(f"log_{date_str}.md")

    # 避免覆盖同日归档
    counter = 1
    while archive_path.exists():
        archive_path = log_path.with_name(f"log_{date_str}_{counter}.md")
        counter += 1

    shutil.move(str(log_path), str(archive_path))
    log_path.write_text(LOG_HEADER, encoding="utf-8")

    # 清理旧归档
    _clean_old_archives(log_path)


def _clean_old_archives(log_path: Path):
    """只保留最近 MAX_ARCHIVES 个归档"""
    archives = sorted(
        log_path.parent.glob("log_*.md"),
        reverse=True,
    )
    for old in archives[MAX_ARCHIVES:]:
        try:
            old.unlink()
        except Exception:
            pass


def append_log(op_type: str, message: str, details: list = None,
               log_path: Path = None, level: str = "INFO"):
    """
    结构化追加日志到 log.md。

    Args:
        op_type: 操作类型（推荐在 VALID_OPS 中，非强制）
        message: 一行摘要消息
        details: 可选的详细条目列表
        log_path: 可选，覆盖默认日志路径
        level: 日志级别（INFO / WARN / ERROR），默认 INFO
    """
    path = log_path or LOG_PATH

    # 自动轮转
    _rotate_if_needed(path)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    level_tag = level.upper()
    entry = f"\n## [{now}] {level_tag} {op_type} | {message}\n"

    if details:
        for d in details:
            entry += f"- {d}\n"

    if not path.exists():
        path.write_text(LOG_HEADER, encoding="utf-8")

    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
