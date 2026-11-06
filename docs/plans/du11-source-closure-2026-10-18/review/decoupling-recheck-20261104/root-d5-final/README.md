# ROOT D5 最终接收 — 2026-11-06

**结果：ACCEPTED。** CWP 的通用规范化解析 port、StockWiki 三个默认 consumer、FF V2/V1 边界和真实样本组合已通过固定套件；独立最终审查 PASS。此结论只关闭 D5 全局解耦，不代表新版摘要、缓存恢复、RF 实际采用或公司循环已完成。

## 接收版本与并线

| 仓库 | 已审查交付版本 | ROOT 接收后的主线 | 并线情况 |
|---|---|---|---|
| company-wiki | `a28692a6c49125143d2240b4a6d6df2ba29a28a1` | `master` 快进至 `a28692a6c49125143d2240b4a6d6df2ba29a28a1` | 本地已并线；root验收与PWF提交后更新发布记录 |
| StockWiki | `6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e` | `master` 快进至 `6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e` | 本地已并线；仓库无 remote |

两个候选版本已核对无冲突；StockWiki 的 6 个既有未跟踪路径均保留，且与交付文件不重叠。CWP 主线既有历史运行产物未清理。

## 固定跨仓验收

完整机器收据：[run-6/report.json](run-6/report.json)。命令通过 `tools/run_source_system_tests.py --d5-final` 执行，测试选择不可被 `--tests` 覆盖，并绑定上述候选 HEAD。

- 总计 **18 passed，0 skipped，0 failed，0 errors**：13 个 CWP `processed_document` contract 用例；StockWiki 三个业务入口消费及真实本地样本回放 2 例；FF V2/V1 路由边界 3 例。
- `scratch_restored=true`。本地原件 `中大力德：2026年4月28日2025年度业绩说明会投资者关系活动记录表.pdf` 为 113,954 bytes；SHA-256 前后均为 `ef78655e0980ce0ae50a5c9ab77457a024a9a5999ab4c0dff0556dc144efa4ef`，mtime 也一致。
- StockWiki `config/cwp_source_index.transport.json` 测试前后原始 SHA-256 一致；Git clean-filter blob `f4406252702b5c2c83e8e2bc5ea16a8eabe717f8` 与 reviewed commit 一致。工作区 CRLF 与提交 LF 差异已正确归一；回归测试证明实质内容变化仍会不匹配。
- CWP/StockWiki 候选工作树测试前后均 clean；测试输入、配置与真实 PDF 之外没有写入生产资料。
- 接收后 ROOT 在主线再次运行 CWP contract suite：13 passed；`tests/unit/test_source_system_runner_scope.py` 为 15 passed；相关 Ruff 检查和 `git diff --check` 通过。
- run-6 pytest 有一条既存且非阻断的 `Unknown config option: asyncio_mode` 提示；所有实际测试均运行完成，没有用 warning 或 skip 替代验收。

## 独立最终审查

独立审查绑定本表中的两个 reviewed HEAD 与 `run-6`，结论 **PASS**。审查核对 JUnit 与 JSON 数量一致、固定套件不可被替换、CWP/StockWiki HEAD 和 clean 状态、传输配置 commit blob、原件完整性及 scratch 清理。审查对代码逻辑作静态检查；runner scope 单元测试由 ROOT 单独实际运行 15 项通过。

## 已知边界

D5 没有新造另一套缓存。当前没有证据表明 CWP 有可复用的通用持久化 normalized-unit cache；port 当前按请求读取/解析。缓存复用/恢复仍按主线后续阶段单独验证，不属于本次 D5 通过声明。真实样本是一次职责/接口组合验证，不代表多市场、多文种阅读策略或完整公司审计循环完成。

## D5 接收时的下一步（2026-11-06，后续状态见下方对账）

按 [task_plan.md](../../../task_plan.md) 恢复 T4 source-note-parent + SEM-QUAL-01；先写根因回归测试，再实施所属层修复，并以一份隔离真实 H1 做大节点验收。

## 发布与当前进度对账（2026-11-06）

- ROOT 接收/PWF 提交为 CWP `c28b122075748d99547fb0a7e2fd4adcd7490269`。本机 `master` HEAD 与本地 `origin/master` tracking ref 相同；本次直接 `git ls-remote` 因 DNS worker 无法启动而未取得实时远端确认。
- 已知 exact-head CI 记录 `41919818618` / `41919818624` 绑定 D4 ROOT head `e7469d684b10a4cd37772e045eb3e588254c5ab8`，**不**绑定 D5 接收 commit `c28b122075748d99547fb0a7e2fd4adcd7490269`。本次未重新确认 c28 的 GitHub CI，机器状态按“未新鲜核实”记录，不沿用旧运行标绿。
- D5 技术状态仍为 **ACCEPTED**；CWP commit 的远端实时存在性/exact CI 观察是单独的发布证据状态，不改变已通过的冻结范围内解耦验收结论。
- T4/SEM-QUAL-01 已在 ROOT 本地完成 RED→GREEN 根修与聚焦测试，并成功观察一份真实 H1；但 102 对基线 101 的 native-member 差异、独立审查、最终 Ruff、持久化证据和 scratch 恢复仍 OPEN。当前唯一下一步见 [CURRENT_STATUS](../../../CURRENT_STATUS.md) 与 [HANDOFF](../../../HANDOFF.md)，不再从本节的历史指令重新执行 RED/实施。
