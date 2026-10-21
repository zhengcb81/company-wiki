# R1 W04 摘要运行恢复与实验补写退役

唯一总控入口仍是母仓 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md`；本文件仅记录 ROOT 已派 W04 的独占实现。

## 范围和进度

1. **完成：** 阅读 shared_contract/W04 与封存 R2 诊断；确认 automation 独占、0 网络/模型/下载，不改原件、生产配置、历史账或其他仓库。
2. **完成：** 先写退役负例与真实 Catalog/AUTO/verify/outbox 激活缺口的 RED，然后在现有 run ledger 修复最终输出所有权，删除新实验补写派发。
3. **完成：** 新/改 15 项与相关既有 114 项在最终产品上合计 **129 PASS/61.42s**，ruff 与正常提交静态检查通过；保留原始 RED、纠正的夹具失败和完整日志。
4. **待 ROOT：** 集中独立审查本包实际代码/证据，再整合至主线；不得把本页当独立质量签收或主线发布。
5. **待 W07：** 当前配置的真实 0.9 `/5` 付费响应保存后、激活前中断恢复，同/跨 run 缓存与 RF 实际 context 消费、四路内容审查。有限离线 provider 与 loopback 控制不代签真实付费。

## Next Step

ROOT 对本分支做一次集中独立质量审查；发现问题修复后正常合入。W03 可在整合 W04 后接线；本包不改变 selector 默认值或旧 generation。

## 固定兼容边界

- `CW_SUMMARY_COVERAGE_REPAIR=1` 不再创建新 partial/retry/第二 scoped operation；raw、official JSON 均只有一次模型派发，覆盖不完整仍 `needs_review`。
- 旧 prior_partial/snapshot DTO 保留；合法 partial-only 返回具名 `LEGACY_PARTIAL_SUMMARY_AVAILABLE` 并保留 payload，不付费、不伪造 succeeded final。损坏 partial 具名 INVALID，原历史记录不改。
- 真实已成功 merged final：由 verify 成功结果、精确工件、同 run/DAG 与该成功 summary 对应的 native model receipt 决定唯一输出 owner；首轮 failed output=0 不可改写。普通单 operation paid replay 可沿唯一已证明的原 paid reservation 结算。
- 未完成多 pin 不扩能力：仍 `MODEL_PAID_RESPONSE_UNAVAILABLE`、零新 POST。旧 fallback 无合法 final slot 返回 `output_accounting_unresolved / LEGACY_FINAL_OUTPUT_OWNER_UNRESOLVED`，精确工件仍可读，所有费用与零收据保留。不能声称这些状态已恢复完成。
- 不新增 operation/任务/预算数据库、不改 R5 零输出保护、不吞冲突、不按 latest reservation 猜 owner。
