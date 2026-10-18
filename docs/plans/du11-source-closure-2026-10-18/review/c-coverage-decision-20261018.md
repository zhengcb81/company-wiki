# 正式 C 内容覆盖：测量、约束与四条路径 A–D（2026-10-18）

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

### A. 覆盖修复：第二次有界尝试（已实现，实验性、默认关闭）

**2026-10-18 实测结论：** 不新增 job/表/预扣，复用 retry（两次 attempt、两次计费）；`CW_SUMMARY_COVERAGE_REPAIR=1` 启用。CN 真实运行两次 POST 并合并成功、进入 `activation_pending`。未解决：`activation-resume` 与重试 attempt 的 `reopen_paid_output` 冲突；MiMo 首响应 JSON 约 1/3 失败。默认关闭。

- 在 `NarrativeSummarizeHandler` 解码后计算未覆盖 task；若仍有预算且未覆盖 ≥1，构造只含未覆盖 task 的请求，target 为剩余额度，再调用一次 `model_caller`。
- 两次调用各自 reservation/settlement；合并 claims（claim_id 加 `-b` 后缀）；第二次失败不推翻第一次结果，但标记 `needs_review` 并记录诊断。
- 需改：`narrative_model_caller`（一次尝试 → 每 job ≤2 次，attempt_no 递增）、`narrative_run_store`（多 attempt 定价）、缓存键（两次请求）、receipt attempts 断言、大量单测/集成测。
- 预期：CN 9–10/10；US 从 ~8 条升到 ~16 条。
- 风险：中高；触碰付费准入与恢复，需独立审查。

### B. 任务合并：section 级 summary task（已实测失败，2026-10-18）

- 实现并单测通过（64→40 任务、96 span 恰好定义一次、103 测试绿），但两次真实 CN 都是 `MODEL_RESPONSE_INVALID`（模型返回畸形 JSON）：多成员任务的 parts/support_parts 结构让 MiMo 失稳。
- 已 revert（`12914f62`），不再作为候选。

### C. 换模型

- US 改用 MiMo（或 CN 也换），改 metadata 的 provider 映射。
- 预期：US 接近 CN 的 8/10，但仍非 10/10；且"三供应商"实际只用两家。
- 风险：低实现、高语义偏差。

### D. 调整验收标准

- critical 全中 + normal ≥80%。CN 目前 critical 5/7，不达标，等于不改。

## 建议（2026-10-18 更新）

B 已实测失败；prompt/上限/排序类实验也已证明只能"换一条漏项"（4.0.8 甚至把覆盖降到 6/10）。剩余只有 **A（覆盖修复二次调用）** 能真正补上缺口，但它要改 `NarrativeModelCaller` 的 "exactly one model attempt" 付费准入；若不动架构，只能选 **C（换模型）** 并把"三供应商"口径调整为"已配置供应商中至少两家可用"。

## 2026-10-18 追加：模型文本缺陷

CN 4.0.8 的 t45-1 在原文断行处插入了 `te`（`上\nte海临港`）。核对 `materials/*.response.json.gz` 确认是模型输出，不是切片/解码；任何换模型方案都应把"不插入原文没有的字符"列为验收项。

## 需要拍板

**已拍板（2026-10-18）**：选 **A（覆盖修复二次调用）** 实现为实验性能力（`CW_SUMMARY_COVERAGE_REPAIR=1`，默认关闭）；C 内容按 **CN 8/10** 收尾（用户决定，不再追最后 1–2 条事实）；C（换模型）留作后续模型评估课题。（B 已实测失败，D 的阈值下 CN 仍不达标。）
