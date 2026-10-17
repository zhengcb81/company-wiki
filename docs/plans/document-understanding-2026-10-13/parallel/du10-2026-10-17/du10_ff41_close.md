# DU10-FF41-CLOSE — 完成 filing-fetch 固定 41 例端到端矩阵

## 工作区与目标

- 仓库：`C:/Users/郑曾波/Projects/filing-fetch`
- 独立 worktree：`C:/Users/郑曾波/Projects/filing-fetch-du10-41-matrix`
- 起点：`main` / `c7c8867da35cd19d4f419fa70947332615e8e9c0`
- 建议分支：`codex/du10-ff41-close`
- PWF：`docs/plans/du10-ff41-close-2026-10-17/`
- 背景：[DU8 接收记录](../../review/du8_reception.md) 和 [原 FF 矩阵卡](../du8-2026-10-16/du8_ff_matrix_completion.md)。本卡从当前 main 开始；旧作者 worktree/旧提交只读，不复用作施工目录。

关闭当前确切 OPEN：既有 41 例记录为 `20 PASS / 4 PARTIAL / 17 NOT_RUN`；完整矩阵中断后重启恢复为 `NOT_RUN`。最终必须按固定 case 定义、oracle、预算和并发上限实跑一次，不以单元测试、CI 绿或历史 replay 代替。

## 范围与接口

可修改：`tools/offline_contract_matrix/` 内完成矩阵所需的最小根因代码；本卡新增 `tests/test_du10_ff41_*.py` 和专属小型 fixtures；本卡 PWF 与 receipts。开工先盘点当前 main 的真实实现，按证据更新旧卡建议，不照搬已合并旧支线实现。

固定：原 41 个 case 和 oracle、下载/复用/失败后 retry 的因果关系、case ≤30s、batch ≤180s、最多 2 workers、原 proof reserve。不得提高限额、删/替换 case、改 oracle、用较弱样例、把未知费用或副作用吞掉、以“重跑到绿”挑结果。CWP 和 ET 仅使用固定提交 `900dbf6489f3b995a0bfb7fcbb8a001a68df241d` 与 `7d06777e250ee3f7ae58f0be2cee62944bd2c104` 的只读依赖；测试前后记录依赖 HEAD，不随支线漂移。

不碰 `config/FMP_API_KEY.txt` 或任何密钥内容；不改 CWP、ET、Dayu、provider 配置/下载生产脚本。没有真实网络/供应商/LLM 请求。测试及报告写入本卡独立 owned temp，验证结束清理；原主树现有未跟踪文件保持字节不变。

## A/B/C 节点

### A — 固定基线与失败复现

记录 41 个 case ID、目前状态与历史 findings；用 fake clock/离线 fixtures 复现预算尾部遗漏、启动重复或恢复错误的实际根因。测量启动/准备/各阶段时间，区分墙钟与并发累计时长。先保留 RED，不改 case 分母或 time cap。

### B — 根因修复

在 `tools/offline_contract_matrix/` 内消除确证的重复准备、调度饥饿或恢复问题，复用现有执行/进程 transport；不复制一套 subprocess 管理器。加入针对实际问题的窄回归。中断恢复必须基于本次唯一 attempt，失败产物不能伪装成功或重复不可重放副作用。

### C — 完整端到端与恢复

在新的独立测试根串行跑完整 41 例一次，保存每个 case 的真实 PASS/PARTIAL/FAIL/NOT_RUN、总耗时和必要分阶段摘要；再做受控中断、重启、继续/停止和清理 E2E。只有 `41/41 PASS`、恢复行为通过、sentinel/原目录准确恢复，才标记卡完成。否则保留真实结果，按根因修复后重跑受影响的大节点；不删失败。

## 独立最终审查

冻结最终 HEAD 后另派独立审查 agent，不由作者兼任。审查员复核完整 diff 和保护边界、41 case 分母/oracle、预算没有上调、原始失败没有被改写、重启属于本次 attempt、日志/cleanup 真实性；抽查核心代码和测试并确认 RED 均由根因修复。作者修复审查发现并运行受影响测试后，审查员按最终 SHA 再复核。零未解决问题才写 `COMPLETE` 并交接；不能取得独立 agent 时不交接。

## 交接

交付完整 commit、PWF、`handoff.md/json`、紧凑 receipts：最终 HEAD、精确 41 个 case 结果、命令/退出码/耗时、固定 CWP/ET HEAD、恢复结果、测试目录清理与 sentinel 前后 SHA、独审所审 SHA/报告、finding 修复映射。不得声称真实 provider/财报质量通过。
