#!/usr/bin/env python3
"""
generate_dashboard.py — 真实的系统仪表盘

直接读取真实数据（而不是假监控）：
- 从 extracts/ 目录统计提取的高质量文档数。
- 从 log.md 中统计 LLM 调用和 Token 消耗。
- 从 wiki/ 目录统计重写的 Wiki 页面数。
"""

import re
from pathlib import Path
from datetime import datetime

# 项目根目录
WIKI_ROOT = Path(__file__).parent.parent
DASHBOARD_PATH = WIKI_ROOT / "dashboard.md"
LOG_PATH = WIKI_ROOT / "log.md"

def generate_dashboard():
    now = datetime.now()

    # 1. 统计高质量文档数 (提取成功的 .md 文件)
    extract_files = list(WIKI_ROOT.rglob("companies/*/extracts/**/*.md"))
    valid_extracts = len(extract_files)

    # 2. 统计重写的 Wiki 页面数
    wiki_files = list(WIKI_ROOT.rglob("companies/*/wiki/*.md"))
    rewritten_wikis = len(wiki_files)

    # 3. 从 log.md 统计 LLM 调用和消耗
    llm_calls = 0
    total_tokens = 0
    if LOG_PATH.exists():
        log_content = LOG_PATH.read_text(encoding="utf-8")
        # 假设 LLM 调用记录为: LLM call | tokens: 1234
        for line in log_content.split('\n'):
            if "LLM" in line or "chat" in line.lower():
                llm_calls += 1
            token_match = re.search(r'tokens?:\s*(\d+)', line, re.IGNORECASE)
            if token_match:
                total_tokens += int(token_match.group(1))

    # 计算健康度
    # 如果 llm_calls == 0，说明大脑宕机，健康度必须为红灯 0/100
    health_score = 100
    health_icon = "🟢"
    
    if llm_calls == 0 and valid_extracts == 0:
        health_score = 0
        health_icon = "🔴"
    elif llm_calls == 0:
        health_score = 20
        health_icon = "🔴"
    elif rewritten_wikis == 0:
        health_score = 50
        health_icon = "🟡"

    dashboard_md = f"""# 真实的知识库控制面板

> 生成时间: {now.strftime("%Y-%m-%d %H:%M:%S")}
> 状态: 核心重建 Phase 4 已完成

## 系统真实健康度: {health_icon} {health_score}/100
*(注: 如果无 LLM 调用或无 Wiki 重写，健康度将严重告警)*

## 投研大脑状态 (LLM)
- **累计 LLM 调用次数**: {llm_calls} 次
- **累计消耗 Tokens**: {total_tokens} 
- *(详细日志见 `log.md`)*

## 资产质量统计
- **成功解析的高质量文档 (Layer 2)**: {valid_extracts} 份 (财报、招股书、IR等)
- **经 LLM 深度重写的 Wiki 页面**: {rewritten_wikis} 页

## 系统架构与模块精简报告
- 🗑️ 已彻底删除伪装闭环的 `event_bus.py`, `job_queue.py`, `repair_planner.py`
- 🗑️ 已彻底删除低质量新闻污染源 `collect_news.py`
- 🗑️ 已用 LLM 重写了伪研判逻辑 `investment_judgment.py`
- ✅ 启用了基于 `pdf_extract_v3.py` 的多策略+LLM辅助分类。
- ✅ 启用了 `stage6_synthesize.py` 摒弃 Append-Only，实现全量综合演进。
"""

    DASHBOARD_PATH.write_text(dashboard_md, encoding="utf-8")
    print(f"-> 真实的 Dashboard 已生成: {DASHBOARD_PATH}")

from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    generate_dashboard()
