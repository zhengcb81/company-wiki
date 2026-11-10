# 当前状态 — P2 已并线；D4/D5 范围验收通过；误拒根因已对账；source-facts 主线复验与工作区核销未完成

唯一入口：[当前状态](CURRENT_STATUS.md) / [机器状态](CURRENT_STATUS.json)；详细顺序见 [task_plan](task_plan.md)，交接见 [HANDOFF](HANDOFF.md)，固定长期目标见 [MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

**截至 2026-11-10：P2 已分别并入 CWP/FF/RF 主线并推送；D4/D5 解耦按冻结范围 ACCEPTED。** D4/D5 的含义是 owner 通过版本化公开接口协作，且既有接口边界和组合样本测试通过；不是零依赖，也不是 Dashboard 全计划完成。D5 跨仓套件为 18 passed、0 skipped、0 failed/errors，独立审查 PASS。P3 Reader/PDF 端口和 P4 Dashboard 实际切换仍 OPEN。P2 与解耦结果的细节见 [Dashboard owner plan](../dashboard-owner-integration-2026-11-09/task_plan.md)；D5 证据见 [ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)。

**同名 P2 需要区分：**上述“已完成”是 Dashboard owner 接线 P2；本计划 `remaining_stages.P2` 是后续证明 RF 实际消费同一份已接受摘要 artifact，仍为 OPEN，依赖 P1 完成。模块化并非整个 Dashboard/RF 工作流已全部完成。

**工作区核销仍在进行（2026-11-10 20:49 UTC 代码快照）：**本次盘点基线 CWP `master == origin/master == 5d4b4f4b6ea70f703ca7710d65e3a27d158f62a5`，跟踪文件干净；有 13,279 个未跟踪文件，逻辑大小 198,372,372 bytes（189.19 MiB），9 个注册工区（含根目录）、23 个本地分支，其中 17 个非祖先。根下识别的 269 个缓存路径中，268 个是可重建缓存（8,349 文件、182,104,966 logical bytes）；一个同名 `.pytest_cache` 实际是已跟踪测试夹具，已按 index checkout 字节恢复并保留。加上此前清掉的 `.planning` 缓存，本仓净移除约 324.58 MiB 缓存逻辑数据。没有删除原始公司文档、生产配置或模型环境；逻辑字节不等于实际释放的磁盘空间。本状态提交只更新 PWF，不改产品代码。逐项证据见 [工作区核销记录](review/workspace-reconciliation-20261110/README.md)。

**误拒根因核对（2026-11-10）：**历史审计归并了 10 类根因而非 10 次运行；确认 4 个真实结果被观察/审计错误挡住，另有 1 个合法公共错误 DTO 被旧消费者拒绝。窄口径有 2 个明确过度设计门槛（mtime 与任意 300 KB 上限）；把错误 registry predicate 也算进去是 3 类门禁误拒；再把观察器 KeyError 耦合算入则宽口径共 4 类。R7 已移除或修正这些限制。真实预算、原文身份/哈希/期次、数值和付费恢复约束保留。分类、证据与当前代码核对见 [误拒根因对账](review/failure-root-cause-reconciliation-20261110.md)。

**当前唯一下一步：**在当前主线精确复验 source-facts 候选所报告的遗漏，并完成本地 worktree/分支核销。候选观察显示 coverage guard 10/10、native-prose guard 8/10（漏两个指定业务事实），当次预算未耗尽且没有模型调用；但观察绑定 detached worktree 的源码，不能升级为主线通过或失败。先对当前 `master` 做小范围零模型重放，只有缺口复现才改生产 owner 层。此前 H1 的 102 对 101 个 native-member 差异、locator/context 对齐、最终独审和 scratch 恢复仍未完成。通过当前主线复验与修复后才恢复新版真实摘要、缓存恢复、RF 实际采用及固定公司循环。

## T4/SEM-QUAL-01 候选观察（不是当前主线验收）

- detached candidate worktree 中有 11 个 tracked 文件修改和 12 个 untracked 开发/测试/收据文件；改动横跨来源语义、解析、只读观察和测试工具。它不是一项可直接快进的单一补丁，且未绑定当前主线复验。
- 最近一次相关测试记录：note-scope 91 passed；source-case-runner 20 passed；decoder/source-frame/summary 组合 271 passed；qualifier 专项 17 passed。这些来自不同测试命令，可能有覆盖重叠，不能相加成总数。最终 Ruff 与大节点独审还未完成。
- H1/selection 收据原先只在 detached candidate worktree 的 `.planning` 下；已把五份关键 JSON 收据复制到 `review/source-facts-reconciliation-20261110/`，且五份归档 JSON 的 SHA-256 均与候选 worktree 原件一致。运行状态为 `OBSERVED_NOT_COMPANY_OR_ECONOMIC_ACCEPTANCE`，不能当成公司或财报质量验收。
- 与先前基线相比 native-member 数为 102 对 101；这不自动判失败，也不能忽略，需在收口时解释映射差异并检查 12 个成员/locator。
- 第一次 observer 尝试在读取原件前因 Windows `os.link` WinError 5 失败；改为 Windows 同目录原子 `os.rename` 首次发布后重跑成功。该失败不涉及来源、网络或模型调用。

## D5 接收结果

- 候选实现版本：CWP `a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki `6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两者均通过快进并入本地主线；StockWiki 当前无 Git remote，无法推送远端。
- ROOT D5 接收 commit 为 CWP `c28b122075748d99547fb0a7e2fd4adcd7490269`；本次 PWF 对账 commit `bd2c9ee328831f80626a216a99a7d503cebcfdd5` 已推送，推送后本机 `master` 与 `origin/master` tracking ref 一致。c28 与 bd2 的 exact-head CI 均未在本次新鲜核实；已知 D4 CI head `e7469d68` 不代替它们的 CI 记录。
- run-6 固定跨仓套件：CWP 13 个处理 port 合同用例、StockWiki 三入口消费与真实样本 E2E 2 例、FF V2/V1 路由 3 例；合计 **18 passed**，无跳过、失败或错误。ROOT runner 定向单测 **15 passed**，Ruff 通过；合并后 CWP 合同测试再跑 **13 passed**。
- 真实只读原件：中大力德投资者关系记录 PDF，113,954 bytes，SHA-256 `ef78655e0980ce0ae50a5c9ab77457a024a9a5999ab4c0dff0556dc144efa4ef`，测试前后 SHA/大小/mtime 一致。隔离 scratch 已恢复。
- StockWiki transport 配置 `config/cwp_source_index.transport.json` 在测试期间 SHA 稳定，并以 Git clean-filter blob 比较确认内容与审查 HEAD 一致；Windows CRLF/LF 转换不误报，真实内容修改仍被回归测试拒绝。候选工作树运行前后均干净。
- 独立最终审查绑定上述准确 HEAD 与 `run-6/report.json`，结论 PASS。审查静态检查 runner 门与报告；runner scope 单测由 ROOT 独立运行 15 项通过。
- D5 没有新建第二套缓存；本次没有证明存在可复用的通用持久化 normalized-unit cache。跨请求/跨运行缓存恢复仍 OPEN，按主线顺序后续验收。

## 以前已关闭

- P0 CI 根因修复：已完成并发布；当前不因历史 CI 失败而重跑长时间全量套件。
- P0-D / D4-01～D4-06：按冻结范围完成，独立审查及强制组合通过。范围详情和历史收据保留在 [D4 closeout](review/d4-closeout-20261104/README.md)。D4 本身不等于 D5；现在 D5 也已经独立验收。

## 后续状态

| 阶段 | 状态 | 顺序与边界 |
|---|---|---|
| D4 + D5 解耦 | **COMPLETE / ACCEPTED** | 只在冻结接口范围内声明通过；版本化接口是预期协作合同，不代表模块零依赖 |
| T4 + SEM-QUAL-01 | **IMPLEMENTED LOCALLY / H1 OBSERVED / FINAL REVIEW OPEN** | 先解释 member 差异、核对 H1 证据，完成一次大节点独审与 scratch 恢复 |
| 新版真实摘要与质量验收 | OPEN / 等 T4 接受 | 用真实材料核查召回、归属限定、财务碎片/套话占位、业务信息遗漏 |
| 缓存恢复 | OPEN / 等新摘要基线 | 付费中断、同 run 与跨 run 恢复；按实际配置记账，不声称 D5 已验证 |
| RF 实际采用 | OPEN / 等新摘要和恢复 | 证明同一摘要 artifact 进入 RF 参数、公式与报告 |
| 固定公司审查循环 | OPEN / 最后 | 依长期目标完成固定名单与新公司泛化，不以局部工程测试替代完整审查 |

继续保留原始文件、历史失败和未跟踪 WIP；D5 的已跟踪代码已在 CWP 主线，StockWiki 已本地并线但无 remote。当前 T4/SEM 改动仍在工作区，不清理其它历史产物，不修改 Dayu/IQS。后续仍只在大节点做独审和组合测试，避免逐小节点增加审查。
