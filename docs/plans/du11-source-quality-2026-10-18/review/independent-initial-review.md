# F1/F2 独立审查：CHANGES REQUIRED

已读冻结11文件、实际runtime diff、新测试、母计划和相关当前 owner。未审 allocator/F4（由另一独审负责），未改实现。

## 必须修复

1. **P2 审计对象词将程序目的晋升业务。** `Our audit procedures included testing revenue from software delivered to customers.`、第三人称独立审计师变体及中文审计检查交付凭证，实际均 `admitted=true,purpose=operating`。原因是对象+事件谓词优先于审计范围，只有窄 `We ...` 被提前保护。须按同一句动作/actor范围区分；保留真实 `We launched software for customers to automate audit procedures.`。
2. **P2 明确 RPO 转化遭误杀。** `Revenue allocated to remaining performance obligations was $90 million, and we expect to recognize 40% as revenue in the next twelve months.` 实际被 accounting_policy 拒绝，改 `next 12 months` 就保留。须在现共享时间/contract conversion owner覆盖常见拼写数词时间；裸 allocated/no conversion schedule 仍拒绝。
3. **P1 新表格处置原因未接 formal execution port。** 含 ambiguity 的计划产生 `unsupported/source_table_unresolved`，正式 `_report(plan.execution)` 实际抛 `execution source reason is invalid`。当前测试仅 compile，未走 wrap/parse。须有限枚举和 selected 对应卡原因一致性接通，补实际 wrapper/diagnostic 恢复链反控。
4. **P2 必需表头 context 歧义仍被当完整表格卡。** 合法 v2 operating_table task 中 clean support + ambiguity header/year context 实际 admitted。源卡应消费整个必需表格观察的质量，至少覆盖表格 task 的 required context；不能把无关表格上下文误用来删除独立业务 prose。

所有问题已给 ROOT；具体可复现输入、输出和初始绑定见 JSON。未更改响应、预算、质量结果或来源。

## 已核边界与未完成范围

当前 legacy 0.8 detector 保持，purpose 默认 unknown；source session 同 owner缓存并在预算失败时标 unassessed，未再次调用无预算识别器。生产 priority 附加只走当前 reading budget，不改旧 replay。新业务算法 hash/continuity version 及 v5 cards/port依赖进入缓存身份。默认 citation support 分开源 anchor 与 context，QA仍只把答复当事实。

唯一指代、真实跨页闭合、真实原生表格重放及正式三供应商 C/下游恢复仍 OPEN，不能据此声称全部质量完成，也不要求新的人工许可。

只执行紧凑纯 assessment/compile/正式 decoder 反控；未运行940大包、真实原件、模型、网络或密钥读取。作者940PASS/60.14s日志已读，不替代这些新增反例。等待修复冻结后作有限delta复审。
