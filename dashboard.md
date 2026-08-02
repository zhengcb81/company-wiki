# 真实的知识库控制面板

> 生成时间: 2026-05-19 21:35:15
> 状态: 核心重建 Phase 4 已完成

## 系统真实健康度: 🔴 0/100
*(注: 如果无 LLM 调用或无 Wiki 重写，健康度将严重告警)*

## 投研大脑状态 (LLM)
- **累计 LLM 调用次数**: 0 次
- **累计消耗 Tokens**: 0 
- *(详细日志见 `log.md`)*

## 资产质量统计
- **成功解析的高质量文档 (Layer 2)**: 0 份 (财报、招股书、IR等)
- **经 LLM 深度重写的 Wiki 页面**: 0 页

## 系统架构与模块精简报告
- 🗑️ 已彻底删除伪装闭环的 `event_bus.py`, `job_queue.py`, `repair_planner.py`
- 🗑️ 已彻底删除低质量新闻污染源 `collect_news.py`
- 🗑️ 已用 LLM 重写了伪研判逻辑 `investment_judgment.py`
- ✅ 启用了基于 `pdf_extract_v3.py` 的多策略+LLM辅助分类。
- ✅ 启用了 `stage6_synthesize.py` 摒弃 Append-Only，实现全量综合演进。
