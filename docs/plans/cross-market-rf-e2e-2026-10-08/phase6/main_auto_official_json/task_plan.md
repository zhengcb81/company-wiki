# MAIN：官方 JSON 接入同一叙述 Worker

## 后续接收 2026-10-10T23:53:17.615142+00:00

P7-RF已正式发布/安装验收，详见[P7 RF验收](P7_RF_ACCEPTANCE.md)。W04内部责任源码stable，独立集中复核进行；W03pure责任/真实原件回放绿，显式新策略/default旧策略待ROOT冻结版本接线与大节点公共AUTO/replay/reuse测试。既有MAIN M1–M3工程发布结论不变。Next Step：提交已完成进度、W03 shared TDD接线，随后真实原三家四审和新三家。

## 状态与责任

计划已依据三卡验收与独立调查细化，共同接口已冻结，MAIN正在隔离树TDD实施。同一AUTO功能与集中工程验收已通过，已正常主线发布accdeccc且精确CI38094790883成功。只由 MAIN 持有下述 AUTO 共享写集；外包 M3-JSON/W02、M3-USAGE/W06、M3-FLOW/W07 已验收并发布，不重开同写集施工。根 PWF 由 MAIN 更新，本目录不写 `.planning/.active_plan`。

依据：[三卡验收](../m3_acceptance_2026-10-10/ACCEPTANCE.md)、[完整实施细则](IMPLEMENTATION.md)。旧 157 问题包、旧公司研究及失败记录均保留。

## 目标

官方多公司、多页 JSON 原件，经已有投影 parser → 统一有限 AUTO select/summary/verify → 发布 → 公开 read → 精确零模型调用复用。各摘要保留真正母页来源、字段定位、公司和 as-of，原语言，不翻译。旧 PDF、TXT/FMP JSON 和旧版本恢复/读取继续成立。

## 大节点

1. **接口与失败测试：completed（责任层）**。统一内部 subject/view，先写路由、角色、多发行人、多母页、generation/reuse、终态 receipt/compaction 的 RED。显式新公共版本限于旧严格 DTO 无法表达的投影；不逐 helper 创建协议。
2. **同一责任层实现及集成：completed**。已有 projection port 负责实读验真；AUTO 各层仅对自身责任负责，贯通 item 身份。复用现有 store/lease/outbox/预算，不增任务库或授权链。
3. **一次集中大节点验收与发布：completed（工程验收与normal发布/精确CI PASS）**。隔离公共 CLI import→project→AUTO→publish→read→reuse，加恢复和兼容正负控；独立审查关键不变量后正常 commit/push、精确 CI。真实供应商/公司研究另按根计划执行，工程 stub 不冒充研究。

## Next Step

本包工程节点已完成：normal push3020PASS、远端accdeccc精确CI success。根计划继续RF接收修复/版本/安装，并按[W04续行](W04_CONTINUATION.md)和[W03续行](W03_CONTINUATION.md)实施，随后真实研究复验。工程不冒称研究通过；原失败历史不覆写。

## 保留约束

- 原件、生产配置和旧 sealed 报告不改；Dayu 外部仓零改动。
- 累计 USD20 / 2M tokens，包括旧 unknown；责任测试和本地 stub 不产生供应商调用。
- 下载/模型意图沿已有授权与配置执行；不添加人工许可、签收或 canary。
- 测试仅 owned TEMP，结束恢复原样；不做完整资料湖恢复演练。
- 不重复嵌入整页 JSON 或 projection records 到 request/event/binding；空间增长只来自小描述、精选片段和必要回执。

## P7外包边界（2026-10-10）

[三卡总入口](../p7_parallel_handoff_2026-10-10/README.md)用户已发出；CWP source已独立验收合隔离树，其余RF/AUDIT外部施工中。MAIN禁止并行修改 source_catalog/official_json_projection.py/new official_json_snapshot.py；该确定性/深快照/旧回放叶责任归P7-CWP-PROJECTION。MAIN先按原1.0.1默认API接线，最终选opt-in1.0.2。RF校准/audit技能也独占外包，MAIN仅最后跨仓集成/版本安装。MAIN的AUTO统一subject/view/store/generation/transport/CLI和责任tests不交叉。无需等待三卡才能写MAIN RED；外包完成后在一个大节点验收接线。

## W04/W03后续源码节点 2026-10-11T00:03:32.361246+00:00

W04 source+独立6probe已接受；W03 pure source/实际原件回放已接受，default0.6保留。共享接线按[W03_SHARED_CONTINUATION](W03_SHARED_CONTINUATION.md)TDD实施，由ROOT最后切默认与一次公开集中大节点。当前源码责任节点先normalcommit归档，不冒称全部AUTO/真实研究完成。
