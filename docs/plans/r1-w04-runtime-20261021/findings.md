# W04 已证根因与实现

## 根因与收敛

旧 `_final_documents` 把同 summary job 下每条 `error_code=None` reservation 都写成最终正输出。transport 成功不代表最终输出归该笔，旧首轮 partial 已由 native finish 写成 immutable output=0；恢复便触发 ReservationConflictError。修复集中到 `NarrativeRunStore.settle_published_summary_output`，batch 不再自行枚举并结算所有付费记录。

新 helper 在原 BEGIN IMMEDIATE 事务内核同 run/DAG 的 succeeded summary 与 verify、已确认 effect/outbox，以及 verify 实际消费的 summary 和精确工件 hash/size；成功 summary 自己的 provider receipt 优先构成 owner 证明，并非选最新 reservation。普通 paid replay 只有原生 caller 支持的唯一 charged operation/paid pin 才可沿旧 reservation 恢复；不以相同 response SHA 猜多 operation 的归属。terminal compaction 后只按已存在的 exact final receipt 做幂等读取，不重写旧账。

实验补写默认关闭且新共享引擎已有 source-owned extractive 路径。为补两个覆盖项扩建多 operation 收费协议收益低，故按已接受方案退役 handler 中的 env 开关、第二 only_tasks 请求、merge 与自动 fallback；保留 scoped renderer 的通用只读协议能力和历史 DTO。registry 中旧错误名仅为读取历史兼容，生产 handler 不再发出该 retry。

## 证据强度

- 原始封存 `.planning/r1-r2-triage` 不改。本包新真实 Catalog/AUTO/verify/outbox/activation 测试先 3 RED+1 控制 PASS，失败是原生 immutable-zero 冲突；已不使用原分诊的 synthetic visibility port。
- 退役负例原先 5 FAIL 中有 1 个 official JSON 夹具跨 parent 的测试编写错误，单独保留；改成每个 parent 独立 group 后 5 个真实行为 RED，再实现。
- 最终新增/改造 15 项：两笔旧 v4/两历史 pins 的成功 final 恢复；首笔0/费用全保留、slot计一次、重复幂等/不同 pin冲突；read-only不写；旧 fallback/全0不可猜 owner；普通 paid单 operation 在结果中断后重新 claim、复用原 paid reservation、真实激活恢复；未完成两 pin 不新派发；raw/official新 env无补写及旧 partial只读兼容。最后一项先RED指出无模型时旧partial被MODEL_NOT_CONFIGURED遮蔽，修后历史只读不再依赖新模型或新generation。
- 114 个既有受影响测试涵盖 caller、27 paid-response 控制、extractive production、run store、terminal receipts、batch。真实网络供应商调用为 **0**；本包有限 provider 的92/184 tokens是fixture会计，不计入真实母账，不声称真实付费完成。

## 历史不可复原范围

只读确认既有 R2 诊断记录的原 AUTO 路径不存在；旧真实两 attempt 原生导出与输出仍在原处，未改/未签成新 PASS。新测试证明当前责任层能恢复相应原生状态，不声称重放缺失的历史数据库或 dirty 源码。没有 final、无 pin、多 pin 未完成、fallback 所有 slot 已0的状态保持具名；不会新付费“修好”。

## 空间与清理

仅提交小型源码/测试/日志/XML；无生产原件复制、下载、模型 response 复制或整个数据湖副本。测试目录初始不存在；pytest大多数自动清理，但128/129项两次日志如实出现removed=false，随后仅对已结束、本包新建的绝对owned TEMP做原生清理，收据见cleanup.json，不把原日志改绿。过程中一次实测117文件/5,171,825字节，仅为采样下界，不是独立物理峰值；W07真实节点负责峰值验收。工区开始已有 `.planning/du11-*` 未跟踪记录完整保留。
