# R2 两 attempt 恢复分诊（2026-10-21）

结论：**R2 仍未验收；已在当前产品代码复现最终输出结算冲突，另证实付费响应恢复的多 operation 限制。二者是不同路径。** 本次只做隔离分诊，无产品修改、提交、联网、下载或付费；未读取密钥、修改生产配置/原件/历史账，也未触碰 R1 药明康德运行。后续由 ROOT/专家统一排程。

版本：HEAD `feaef48accdee0e076d2ecd3108718b06203b3ca`，产品代码提交 `a5214bda`。精确源码/反例/收据 SHA-256 及结果在[机器报告](r1-r2-recovery-triage-20261021.json)。独占记录与反例位于 `.planning/r1-r2-triage/`。

## 已证：激活恢复把首轮 0 输出改成最终正输出

真实 AUTO、`JobExecutionContext.from_snapshot`、真实 summarize handler、真实 `BudgetedNarrativeCaller`/`NarrativeRunStore`，配有限内存模型：

1. 首轮只覆盖 t1，真实 handler 返回 `SUMMARY_COVERAGE_PARTIAL / retryable`；真实 `finish_attempt` 将该笔 `output_bytes=0`，保留已知 73+19 tokens。
2. native retry attempt 的 context 从 AUTO 读到 prior partial；第二次请求仅含 t2，真实 handler 合并为 `t1-1,t2-r1 / succeeded`。两笔 reservation 的 request hash 不同，首笔输出 0、次笔未结算。
3. verify 的效果、outbox claim/ack 均经真实 AUTO。最终工件的 visibility/read port 为显式测试替身；首次 `_final_documents` 观察 `activation_pending`。
4. 重开 AUTO/run store，放行同一最终工件可见性，再调用真实 `_final_documents`：

```text
narrative_batch.py:2268  _final_documents -> runs.settle_output
narrative_run_store.py:1112 -> _settle_output_in_transaction
narrative_run_store.py:429  ReservationConflictError:
    final output differs from its durable receipt
```

触发点是 `narrative_batch.py:2263–2274` 按 `job_id` 和 reservation 的 `error_code is None` 遍历付费记录。首轮 transport 成功，reservation.error_code 为 null；其 handler 结果虽为 partial，仍被当作最终输出承载者，试图把已封存的 `(0,None)` 改成 `(37,final_sha)`。`_settle_output_in_transaction` 的不可覆写保护正确拒绝。异常前后 reservation 字段一致，模型派发数仍为 2。

这不是重新计算请求 hash 的异常，也不经过 `reopen_paid_output`。不能用“允许同一 attempt 复用请求 hash”、吞掉冲突、覆写旧 0 或过滤全部 0 输出来代替所有者语义。

原始观察：[activation-resume-observed.json](../../../../.planning/r1-r2-triage/activation-resume-observed.json)；完整反例：[test_r2_recovery_red.py](../../../../.planning/r1-r2-triage/test_r2_recovery_red.py)。这是组件集成反例，未冒称完整生产子进程、真实 catalog 工件写入或付费端到端复验。

## 历史事实与本次复现的关系

只读找到 `live-cn-h1-b2v5i-20261018 / phaseC-090-05b8bacea453` 的原生导出：

| attempt | request hash 前缀 | tokens | micro-USD | output_bytes | paid_response_json |
|---|---|---:|---:|---:|---|
| `0a0a3a1b…` | `086f9bfe…` | 15,755 | 2,896 | 0 | null |
| `4f05ba4e…` | `2a1a365e…` | 12,290 | 2,238 | null | null |

主输出为 `activation_pending`，恢复输出为 `NARRATIVE_BATCH_ReservationConflictError`，总计 28,045 tokens / 5,134 micro-USD。恢复 stderr 为空，未保存异常堆栈；历史 AUTO 路径当前不存在。因此：**历史账的状态与当前已复现的 0→正输出冲突吻合，但不能宣称本次重新执行了历史 DB 或确定了历史异常栈。** 历史 fingerprint 为 `0552f1dc6e5504aaeeb77b424a2c2b9d8380fe17` 且 `tracked_source_dirty=true`，不能把它当作可完全复原的干净提交。

旧文档“请求 hash/reopen 冲突”的解释缺少该原生栈支持。本次提供的机制比旧解释更具体；保留原历史记录，不回写账或重新签收。

## 已证：付费恢复仍把 job 当作单一 operation

`narrative_worker_factory.py:355` 仅在 extractive projection 存在时配置 paid-response persistence；当前 scoped v4 的实际 R2 路径 `paid_responses=None`。以下是**真实 paid 对象库/API 的兼容性探针**，不是声称历史 v4 故障由 `_recover` 引起。

- 给 scoped v4 caller 注入真实 paid-response port：首轮正常付费并保存 pin；修复请求在 `_recover` 被当作首轮的身份不匹配，第二次模型派发未发生。handler 捕获 `NarrativeBudgetCallError` 后回退首轮，最终却为 `succeeded`，只剩 `t1-1`。这证明“最终成功”不足以证明补写执行。
- 通过 native reservation + `PaidResponseArtifacts.put/attach_paid_response` 构造两笔合法不同 operation pin，保持第二 attempt 活跃。重放恰好匹配第二请求仍被 `len(charged)!=1` 拒绝，观察为 `MODEL_PAID_RESPONSE_UNAVAILABLE`，两笔原账与派发数不变。
- 两笔都有 pin、均以原生失败结果封存、无 succeeded attempt/effect 时，`retry_paid_narrative_summary` 仍因 `len(rows)!=1` 拒绝指定的第二请求。`_paid_summary_recovery_candidates` 同样按 `len(paid)==1` 筛选（静态证据，未另跑此候选筛选器）。
- 单 operation paid replay 控制 PASS：只派发 1 次，响应和 metrics 相同，reservation/费用不变。

`reopen_paid_output` 负责验证原 paid bytes/request、当前 job/lease/generation、无既有成功/effect及输出预算。这些保护不应放宽。它本身没有 `len(records)==1` 条件；本次未发现需要单独放宽该函数的证据，也未把它当成历史激活错误位置。

## 测试结果与已有缺口

本次最终运行 **4 个预期 RED、1 个控制 PASS，退出码 1**；日志/XML及五份原生观察均已封存，未据此声明修复。

```text
.venv/Scripts/python.exe -m pytest .planning/r1-r2-triage/test_r2_recovery_red.py -q
  --basetemp C:/Users/郑曾波/Projects/company-wiki/.planning/r1-r2-triage/t2
  --junitxml .planning/r1-r2-triage/red-results.xml
```

最初 sandbox 阻挡对象库 `os.link`（WinError 5）；经工具授权在独占工作区短 TEMP 复跑后，真实 paid 对象库路径通过。初始环境失败日志保留，不计为产品 RED。最终 paid replay RED 的原始 pytest 栈还显示 frozen exception 的 `__traceback__` 二次包装错误；机器观察已在抛出前记录原始 `MODEL_PAID_RESPONSE_UNAVAILABLE`，该旁支未扩展调查。

已有 `test_narrative_summary_coverage_repair.py` 的两个测试用 `_Caller/_BadCaller` 替代准入与账本，只覆盖子集请求、合并及失败回退；未经过真实 paid caller/store、finish-output 生命周期和激活恢复。`test_phase_c_activation_recovery.py` 明确断言只有 1 个 native attempt/POST。`du11_paid_response/test_paid_response.py` 的重放和 reopen 用单笔 paid operation。这些测试与本次 RED 可同时成立。本次未重跑旧脚本、网络/loopback测试或全量套件。

## 建议的最小共享责任层方案

根因是三个身份没有一致表达：job 是文档摘要工作，operation 是一次冻结请求，输出 slot 是该 job 的单一最终工件。当前部分代码把它们合成“job 恰有一笔付费记录”，激活又把所有无 transport 错误的记录当作最终所有者。

建议由 native run/accounting 层集中定义 operation 解析和 final-slot 结算，caller、retry candidate/AUTO retry、激活共用；沿用现有 AUTO/预算/lease，不增加第二任务库。实现前需选择并冻结一个明确的 slot contract：

1. 新的修复 operation 必须由 durable prior-partial、未覆盖任务、初始选择/请求与有限次数证明授权；相同 operation 的恢复必须绑定原 attempt/pin。不能把“hash 不同”直接当作允许再次付费，也不能在缺 pin/unknown usage 时盲重发。
2. 精确选择某个 operation，而非先取 `charged[0]`、要求整个 job 只有一笔。保留所有已知/unknown 历史费用，逐 pin 校验字节；当前 lease/generation 只控制新结果发布。
3. 单 job 的最终输出 slot 应绑定实际被 verify 消费的最终 summary result 与参与 operation；不能仅凭 transport `error_code` 判所有者。成功 repair、repair 失败回退首轮、paid replay无新 reservation都必须有确定所有者。可在现有 `narrative_run_jobs` 中保存一个原子 final-slot 收据/绑定；或提供等价的确定性所有者映射。不要先选“latest reservation”或“跳过 0”再补例外。
4. 首轮的明确无最终输出收据保持不可变；final-slot 使用一次结算、重复同 pin 幂等、不同 pin 冲突。输出预算按 job slot 计一次，token/费用按所有真实 operation 求和，恢复不新增收费 allowance。

最小验收矩阵：两 operation 正常合并→付费后激活前中断→重开恢复零新派发；repair失败回退首轮；第二响应保存后未解码中断→仅重放第二operation；两pin精确retry；单operation兼容；篡改/缺失pin及unknown不重发；旧lease/generation拒绝发布；重复激活幂等且费用/输出预算不漂移。先做 native组件回归，再由ROOT安排大节点独审与必要真实复验。默认开关继续由现行配置保持关闭。

## 未知与范围

- 未重放历史 AUTO（原路径不存在），未复原历史 dirty 源码，未对 CN/HK/US 继续付费。
- 未证明开启 R2 于当前 extractive/v5 的完整运行行为，也未擅自更改其协议或默认开关。
- 产物是分诊及实施建议，不是产品修复、R2 PASS、真实费用核销或旧 C 内容覆盖重签。
