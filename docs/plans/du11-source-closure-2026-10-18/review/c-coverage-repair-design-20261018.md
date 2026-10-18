# C 覆盖修复（方案 A）设计说明（2026-10-18）

用户已选 A：对未覆盖任务再发一次模型请求并合并摘要。本文件记录实现前发现的三条硬约束、两条可行路径与取舍，供实现与复审使用。

## 目标

首次摘要响应后，计算“已发送但未被任何 claim 覆盖的任务”；若仍有未覆盖任务且预算允许，再调用一次模型，只发送这些任务，合并两次 claims，最终摘要标记 `needs_review` 并记录诊断 `coverage_repair`。

## 发现的三条硬约束

1. **一次 attempt 一个 reservation**：`narrative_model_reservations` 以 `attempt_id` 为主键（migrations.py:243），同一 attempt 不能有第二次预扣。
2. **latest-attempt 不变量**：`_require_active_attempt` 要求 `attempt.attempt_no == MAX(attempt_no)`（store.py:287）；一旦为第二次调用插入新 attempt（no+1），worker 结束时对原 attempt 的 `finish_attempt` 会失败。
3. **每个文档一个 summarize job**：bundle 由 verify job 读取该 summarize 结果生成（narrative_batch.py:299/1065），新增第二个 summarize job 会破坏“一文档一摘要”的假设，必须插入到 verify 之前。

## 路径 A1：扩展 attempt 模型

- store：新增 `start_repair_attempt(parent, now)`（同 job、lease、generation，attempt_no+1）与 `finish_attempt_with_repair(parent, repair, result)`（先 `_update_finished_attempt(repair)`、再 finish parent、最后只做一次 job 迁移）。
- worker：`_execute_and_finish` 在结果里发现 `repair_attempt_id` 时改走新方法；否则保持原路径。
- caller：`generate(context, request, attempt=...)`；新增 `begin_repair` 与失败时的 repair attempt 收尾。
- handler：首次解码后计算未覆盖任务，构造只含未覆盖任务的请求（复用 `ScopedModelView.visible_keys`），合并 claims（第二个响应 claim_id 加后缀），重建 `NarrativeSummaryResult` 并校验。
- 风险：触碰付费准入与恢复（paid-response 绑定、settle、失败回滚）、attempt 语义（重试计数、快照）。
- 估计：2–3 轮实现 + 1 轮真实复验。

## 路径 A2：summarize 与 verify 之间插入 repair job（推荐）

- 任务图：select → summarize → **repair** → verify；repair 依赖 summarize 成功，verify 依赖 repair。
- repair handler：读取 summarize 结果（run store 的 attempt result），从 selection 重建视图，计算未覆盖任务，发一次只含未覆盖任务的请求（一次 attempt、一次 reservation，完全符合现有付费模型），合并 claims 后写最终 summary 结果。
- batch：为每个文档创建 repair job；verify 读取 repair 结果；receipt 记录 repair 的 usage（第二次请求的费用自然入账）。
- 风险：任务图与 bundle 选择、run store 的依赖结果读取、handler 版本注册。
- 优点：不触碰“一次 attempt 一次 reservation”和 latest-attempt 不变量；失败时 repair 自己重试/终止，summarize 结果仍可回退。
- 估计：2–3 轮实现 + 1 轮真实复验。

## 推荐

**A2**。它把“第二次调用”表达成独立的 job，完全复用现有付费准入、恢复与账本；A1 需要改 worker 的最终化路径，风险更高。

## 验收

- 单测：未覆盖任务触发 repair；repair 请求只含未覆盖任务；两次 claims 合并后 claim_id 唯一、总数 ≤ 40；repair 失败时保留首次摘要并标记 needs_review。
- 真实：CN/US 各一次 live，确认两次 POST 的 usage 都入账、receipt 的 budget 求和正确；随后交独立内容复审。
