# 当前交接 — P2 已并线；D4/D5 已按范围验收；ROOT 复验 source-facts 并清理工作区

**唯一入口**：先读 [CURRENT_STATUS.md](CURRENT_STATUS.md) 和 [CURRENT_STATUS.json](CURRENT_STATUS.json)，再按 [task_plan.md](task_plan.md) 执行。长期目标只看 [MAINLINE_LOOP_GOAL.md](MAINLINE_LOOP_GOAL.md)。截至 2026-11-10，Dashboard P2 已进入 CWP、FF、RF 各自主线；D4/D5 在已冻结的接口和组合验收范围内接受。模块解耦不等同“零依赖”，也不等于 Dashboard P3/P4 完成。

## 最近确认

- P2 三仓主线：CWP `0fc56b25b89da9f3da5921ba64122d9745e1752d`（当前更后续提交已包含）、FF `f65e6ca75fbce0616e65870f0aea78b793ef883c`、RF `b005a179280ee19695578bdba9427b4dd44cdd73`。按 owner 分别发布，不重复 cherry-pick；E2E 见 [P2 收据](../dashboard-owner-integration-2026-11-09/validation/p2_cross_market_e2e_receipt.json)。
- 上次代码/测试整理发布点是 `f01ba7411908d7a6a38451781ce5f9f18600bf9b`；后续只会再发布本次状态文档核账。该 SHA 是代码修订点，不代表当前文档 HEAD。本机仍有大量历史未跟踪项和未核销 worktree/ref，不能称已清理完成；逐项状态见 [workspace reconciliation](../dashboard-owner-integration-2026-11-09/review/local_workspace_reconciliation-2026-11-10.md)。
- Source-facts 候选仍在 detached worktree，不接受其源码为已并线代码。五份关键 JSON 收据已复制并以 SHA-256 核实；guard 结果需在当前主线复验，见 [source-facts 对账](review/source-facts-reconciliation-20261110/README.md)。
- CWP 定向测试曾因旧集成测试 monkeypatch 已退役的 `select_budget_items` 而 202/203 失败；改为观察现行 `plan_budget_items` 后，同一组定向测试 203 passed（6.72 秒）。修订已提交并推送：`f01ba7411908d7a6a38451781ce5f9f18600bf9b`；推送时 fixed smoke 为 18/18，完整远端 CI 尚未在本记录中核实。

## 已验收的 D5

- CWP producer port：`a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki consumers：`6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两个候选版本均通过快进进入各自主线。
- CWP/StockWiki/FF 固定组合套件 `run-6`：18 passed，0 skipped/failed/errors；包含 13 个 CWP contract 用例、StockWiki 三入口和真实样本 E2E、FF V2/V1 路由边界。
- 真实 PDF SHA/大小/mtime 稳定；隔离 scratch 已清理；候选 worktree 运行前后干净；StockWiki transport 内容匹配被审查 commit（按 Git clean-filter blob 比较，正确处理 Windows CRLF/LF）。
- ROOT runner 范围单测 15 passed，Ruff 通过；主线 CWP 合并后 contract suite 13 passed。最终独立审查 PASS。
- 证据入口：[ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)；机器测试收据 [run-6/report.json](review/decoupling-recheck-20261104/root-d5-final/run-6/report.json)。
- StockWiki 仓库没有 Git remote，记录为本地并线；不得把本地并线说成已推送。CWP push/精确 CI 状态以 closeout 的发布字段为准，没核实就不要填绿。
- CWP ROOT 接收 commit `c28b122075748d99547fb0a7e2fd4adcd7490269` 与本机 `origin/master` tracking ref 相同；本次未能直接查询实时远端或该 head 的 exact CI。`e7469d68` 的已知 CI 只绑定 D4 head，不能冒作 c28 的 CI。

## 当前 ROOT 唯一下一步：当前主线复验与本地核销

1. 对当前主线做小范围、零模型 source-selection replay，核验候选观察中的 10/10 coverage 与 8/10 native-prose 差异。若当前主线不复现，记录原因后不合入候选代码；若复现，在来源语义 owner 写泛化 RED/正例，修复共因并跑受影响测试。
2. 只有复现后仍相关时，才解释候选 101→102 native-member 差异并校验 locator/context；避免在候选版本上继续扩展与主线无关的验收。
3. 按 PWF 和 Git 证据逐一核销剩余 CWP worktree/ref 与本地未跟踪目录。仅删除已证明代码/交付物已被主线或 canonical PWF 覆盖的 checkout；独有证据、部署绑定、模型资产先归档或明确保留。不得 bulk reset/clean。
4. 当前主线问题闭环后，按 task_plan 顺序恢复新版真实摘要、缓存恢复、RF 实际采用。每个大节点再做一次独审，不增加小节点签收。

## 接下来仍未完成的工作

T4/SEM 通过后，按 task_plan 顺序实施新版真实摘要与内容召回验收；随后做付费中断/同 run/跨 run 缓存恢复，再验证 Revenue Forecast 实际消费同一份摘要 artifact，最后恢复固定公司审查循环。各阶段分别记录真实范围、预算、证据、测试恢复和独立大节点审查。D5 组合测试不等价于这些产品验收。

## 明确未声称的能力

D5 没有建立第二套缓存，也没有证明存在可复用的通用 CWP normalized-unit 持久缓存；当前 port 按请求读取/解析。缓存恢复仍是后续独立任务。D5 测试使用一份真实本地材料，但不代表市场/文种读取策略或八家公司循环已验收。

## 边界

只修改职责 owner 的范围；始终保留公司原始文档。StockWiki 继续拥有投资语义，CWP 只负责来源和通用解析，FF 的 V1 继续显式隔离兼容。除逐项核销明确属于其他仓的工作树外，不改 Dayu/IQS 或其它仍在施工的外部项目。
