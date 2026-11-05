# 当前状态 — D4 范围验收通过；D5 全局解耦仍 OPEN，主线暂停

唯一入口：[当前状态](CURRENT_STATUS.md) / [机器状态](CURRENT_STATUS.json)；交接：[HANDOFF](HANDOFF.md)；完整计划：[task_plan](task_plan.md)。

**截至 2026-11-05：D4-01～D4-06 按原范围完成并通过总体验收，但全局解耦尚未完成。** 后续复核确认 CWP→StockWiki 的通用 PDF/Office 解析职责仍可能分叉。ROOT 的调用方盘点显示当前 RF production preparation 走 SourceRef v2/pathless，没有发现活跃内部生产 V1 caller；FF 的 `canonical_path` 是显式 V1 兼容合同。ROOT 的 V2/V1 路由测试现已通过：3 passed、0 skipped；测试证明 schema 2.0 自动走 pathless V2、V2 不触发 V1 文件校验器，V1 仍独立回归。最终按外部交付版本重核 caller 和全局组合。D5 尚须完成 CWP→StockWiki 生产者/消费者实现及跨仓组合验收。用户已明确要求：先把解耦工作完整实施并验收，再继续其他主线。因此 T4/SEM、真实摘要、缓存恢复、RF 实际采用和公司循环当前全部暂停。

当前唯一工作是 [D5 全局解耦](review/decoupling-recheck-20261104/harness_lanes/D5-CWP-STOCKWIKI-PROCESSED-READING.md)：外部单一 harness 负责 CWP pathless 规范化文档 port 与 StockWiki 三入口消费；ROOT 已完成 FF V1/V2 只读调用方盘点和路由测试。**截至本次复核，主线尚未收到 D5 正式交付；ROOT 的 FF 边界测试已完成，整体 D5 仍 OPEN。** 单独的 `StockWiki-v2-reader` 目录包含 opt-in SourceExport v2 reader，但其默认来源模块仍调用本地 `documents.read_document_excerpt`，没有覆盖 D5 约定的 CWP 规范化文档合同和三入口迁移，不作为完成证据。

## D4 已完成

- **D4-01 StockWiki 来源虚拟化：** CWP company source index 与 StockWiki 默认公司工作流接线已合入 StockWiki 本地主线；StockWiki 当前 HEAD `23d84586`，仓库没有 remote，按本地交付记录。
- **D4-02 RF 摘要实际消费：** 摘要进入 claim、used parameter、formula 和 report 的消费链已在 RF main；D4 测试代码提交 `96713029`，D4 收口后最新 PWF-only 提交 `90c562ac` 已推到 origin/main。
- **D4-03 CWP 纯文档层：** 文档模型不再反向载入 catalog runtime，已合入 CWP master。
- **D4-04 CWP 电话会 wire：** 导入 wire 使用明确的 v2 projection，不再依赖内部 dataclass 字段反射，已合入 CWP master。
- **D4-05 FF native 结果：** 大 stderr 诊断不再把已 flush 的合法 native 成功结果改判为失败，已推到 FF main，HEAD `bf7e1dab`。
- **D4-06 ROOT/AUDIT 归位与组合：** 两项 AUDIT producer→importer 测试归入 CWP ROOT integration；AUDIT 仓只删除这两项跨仓测试，仍保留本仓 portable tests。AUDIT 的 D4 测试迁移提交 `2449df4a`、PWF-only 更新提交 `3589b69` 均在本地；无 remote。

## 统一验收证据

[最终验收说明](review/d4-closeout-20261104/README.md)及 [完整运行收据](review/d4-closeout-20261104/run-1/report.json)：提交后 CWP HEAD `e7469d68`；六个消费仓源码快照开始/结束一致；`--d4-final` **27 passed、0 skipped、0 failed，46.623 秒**；RF、FF、ET、StockWiki、AUDIT 五个消费者均有实际通过用例，AUDIT 两个必需 node id 均执行；隔离 scratch 已清理；仅使用合成数据/离线 fixture，没有真实供应商调用。仅有一个非阻塞 `asyncio_mode` 未知 pytest 配置提示。

独立审查结论 PASS，报告已记录于验收说明。审查指出的测试集覆盖假阳性、路径穿越误标、未绑定 ET 根级 Python 模块、跨仓导入 ET 私测 fixture 和缺少 source SHA 直接断言均已修复并由针对性测试覆盖。ET 集成仍通过 ET 的私有 worker 注入缝替换 provider session；它验证真实处理/入库/复用链，但不声称覆盖 ET 正常 provider 配置路径。

CWP D4 合并和 ROOT 测试提交 `e7469d68` 已推到 `origin/master`；push hook 的固定 smoke 为 17 passed / 11.80 秒。GitHub exact-head CI #41919818618 与 Source system integration #41919818624 均成功（head `e7469d68`）；本地 push smoke 不代替此远端证据。

## 当前唯一下一步

完成 D5 卡中的 CWP/StockWiki 实现与交付；ROOT 在实现版本上重跑 V2/V1 边界、三入口组合、真实只读样本、测试目录恢复及最终独立审查。当前 FF 子节点收据见 [root-d5-ff-route](review/decoupling-recheck-20261104/root-d5-ff-route/README.md)。全部 D5 条件通过后，才恢复既有 **T4 source-note-parent + SEM-QUAL-01**；后续再按 task_plan 顺序推进真实摘要、缓存恢复及 RF 实际采用。RF/AUDIT 业务计划不得提前派发或启动公司循环。

三表输出容量、local_prepare扩展兼容、Sina provider泛化和组合CI触发范围另列能力限制，不冒真实生产故障，也不扩成额外阻塞。原件/生产配置/DB/封存与已有WIP保留；Dayu/IQS/Dashboard不动。只在大节点独审，不重复超时全量测试。
