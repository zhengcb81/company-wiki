# MAIN：官方 JSON 接入同一叙述 Worker

## 状态与责任

计划已依据三卡验收和独立只读接线调查细化，待 MAIN 冻结共同接口后 TDD 实施。当前不是功能完成。只由 MAIN 持有下述 AUTO 共享写集；外包 M3-JSON/W02、M3-USAGE/W06、M3-FLOW/W07 已验收并发布，不重开同写集施工。根 PWF 由 MAIN 更新，本目录不写 `.planning/.active_plan`。

依据：[三卡验收](../m3_acceptance_2026-10-10/ACCEPTANCE.md)、[完整实施细则](IMPLEMENTATION.md)。旧 157 问题包、旧公司研究及失败记录均保留。

## 目标

官方多公司、多页 JSON 原件，经已有投影 parser → 统一有限 AUTO select/summary/verify → 发布 → 公开 read → 精确零模型调用复用。各摘要保留真正母页来源、字段定位、公司和 as-of，原语言，不翻译。旧 PDF、TXT/FMP JSON 和旧版本恢复/读取继续成立。

## 大节点

1. **接口与失败测试：in_progress**。统一内部 subject/view，先写路由、角色、多发行人、多母页、generation/reuse、终态 receipt/compaction 的 RED。显式新公共版本限于旧严格 DTO 无法表达的投影；不逐 helper 创建协议。
2. **同一责任层实现及集成：pending**。已有 projection port 负责实读验真；AUTO 各层仅对自身责任负责，贯通 item 身份。复用现有 store/lease/outbox/预算，不增任务库或授权链。
3. **一次集中大节点验收与发布：pending**。隔离公共 CLI import→project→AUTO→publish→read→reuse，加恢复和兼容正负控；独立审查关键不变量后正常 commit/push、精确 CI。真实供应商/公司研究另按根计划执行，工程 stub 不冒充研究。

## Next Step

基础subject与public official已164PASS及独立审查通过；按INTERFACES.md在隔离树先写batch/event/context失败测试，内部sourceadapter/store/generation不同写集同时TDD。独立只读审查关注 store compaction、effect target、artifact pin 和共享母页的准确读取，不能只验 select 函数。

## 保留约束

- 原件、生产配置和旧 sealed 报告不改；Dayu 外部仓零改动。
- 累计 USD20 / 2M tokens，包括旧 unknown；责任测试和本地 stub 不产生供应商调用。
- 下载/模型意图沿已有授权与配置执行；不添加人工许可、签收或 canary。
- 测试仅 owned TEMP，结束恢复原样；不做完整资料湖恢复演练。
- 不重复嵌入整页 JSON 或 projection records 到 request/event/binding；空间增长只来自小描述、精选片段和必要回执。

## P7外包边界（2026-10-10）

[三卡总入口](../p7_parallel_handoff_2026-10-10/README.md)已准备，可立即独立启动。MAIN禁止并行修改 source_catalog/official_json_projection.py/new official_json_snapshot.py；该确定性/深快照/旧回放叶责任归P7-CWP-PROJECTION。MAIN先按原1.0.1默认API接线，最终选opt-in1.0.2。RF校准/audit技能也独占外包，MAIN仅最后跨仓集成/版本安装。MAIN的AUTO统一subject/view/store/generation/transport/CLI和责任tests不交叉。无需等待三卡才能写MAIN RED；外包完成后在一个大节点验收接线。
