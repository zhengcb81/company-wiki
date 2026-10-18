# 正式 C 内容覆盖：测量、约束与三条路径（2026-10-18）

## 已证明的部分

- 工程链：CN（MiMo）与 US（MiniMax）各 1 次真实 POST，`activation_recovery` PASS（同 attempt、无新增扣费），`cross_run_zero_POST=true`，FF 复用与 RF 读取均通过；HK 因 `DEEPSEEK_API_KEY` 401 未跑。
- 内容：CN required **8/10**（critical 5/7），US **2–4/8**；上一轮 CN 的 5 个 P1 已全部关闭，只剩"未来五年 60%/70%"与"当前超 30% 覆盖"两条（同一段 t13）。

## 测量（全部真实计费，均可回放）

| 配置 | claims | 覆盖的 required 缺口 |
|---|---|---|
| 20 条上限、target 15 | 15 | 缺 InP（30/60 覆盖） |
| 40 条上限、target 36（已推送 4.0.6） | 22 | 缺 30/60（PD5、InP 覆盖） |
| 业务优先排序 | 26 | 缺 PD5 |
| 60 条上限 | 21 | 缺 InP |
| 材料优先 + 截断 36 | 28 | 缺 InP（任务排第 40，被截断） |
| 材料优先 + 截断 40 | 21 | 缺 InP（模型自己跳过） |

结论：MiMo 每次自选 20–28 条，MiniMax 只写 5–8 条；`max_claims` 从 20 提到 40/60 不增加产出量，排序与截断只改变"漏哪一条"。**单次调用 + 模型自选**是结构瓶颈。

## 架构约束

`NarrativeModelCaller` 的模块注释写明 "Durable admission and metering around exactly one model attempt"：每个 job 一次模型调用，围绕它做 reservation、settlement、paid-response 恢复。覆盖修复的第二次调用不是加循环，而是要改这组不变量。

## 三条路径

### A. 覆盖修复：第二次有界尝试（推荐，但改动最大）

- 在 `NarrativeSummarizeHandler` 解码后计算未覆盖 task；若仍有预算且未覆盖 ≥1，构造只含未覆盖 task 的请求，target 为剩余额度，再调用一次 `model_caller`。
- 两次调用各自 reservation/settlement；合并 claims（claim_id 加 `-b` 后缀）；第二次失败不推翻第一次结果，但标记 `needs_review` 并记录诊断。
- 需改：`narrative_model_caller`（一次尝试 → 每 job ≤2 次，attempt_no 递增）、`narrative_run_store`（多 attempt 定价）、缓存键（两次请求）、receipt attempts 断言、大量单测/集成测。
- 预期：CN 9–10/10；US 从 ~8 条升到 ~16 条。
- 风险：中高；触碰付费准入与恢复，需独立审查。

### B. 任务合并：section 级 summary task

- 把相邻 citation view 按 origin group/章节合并成 15–20 个 section 任务，每个任务多条 span；一条 claim 可覆盖该节多个事实。
- 改动集中在 `summary_tasks.build_summary_task_plan` 与 coverage/claim 语义，不动付费架构。
- 预期：20 条 claim ≈ 每节一条，覆盖提升；但单条 claim 280 字上限意味着合并后可能丢细节。
- 风险：中；需重写任务/覆盖测试。

### C. 换模型

- US 改用 MiMo（或 CN 也换），改 metadata 的 provider 映射。
- 预期：US 接近 CN 的 8/10，但仍非 10/10；且"三供应商"实际只用两家。
- 风险：低实现、高语义偏差。

### D. 调整验收标准

- critical 全中 + normal ≥80%。CN 目前 critical 5/7，不达标，等于不改。

## 建议

先做 **B（任务合并）**：它直接消除"64 个任务对 20–28 条 claim"的粒度错配，不动付费架构，风险可控；若合并后 CN 仍缺 critical，再做 **A** 的第二次尝试。

## 需要拍板

选 A / B / C / D 中的哪一条（或组合）。选定后按 PWF 流程实现、重跑 CN/US、交独立内容复审，再交接。
