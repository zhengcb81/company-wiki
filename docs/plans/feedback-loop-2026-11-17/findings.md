# 设计依据

- [M3 验收](../module-boundaries-2026-11-11/review/m3-formal-t3-20261116.md)记有真实限额遗漏、候选证券身份缺失、供应商启动前的 Windows 临时目录写失败和预期损坏件拒绝。一次高层失败可涉及数个责任，一种失败字样也可指向不同修法。
- [共享读取预算](../module-boundaries-2026-11-11/review/cwp-cn-issuer-read-budget-20261115.md)说明 36 份文档约 126 MB 由重复的 64 MB 截断。应复现合法输入与真实预算耗尽的两面。记录预算 owner 和供应商是否开始，费用未知不能补零。
- [P1 原文视图](../du11-source-closure-2026-10-18/review/p1-business-quote-view-20261116.md)已证明指定四处引用能保留冻结检查点。自动选材、全新生成及 RF 消费仍需各自运行。将问句借给答句、遗漏股东信息来源、丢失建设条件都是退出成功也能查到的错误。
- [既有 I08](../module-boundaries-2026-11-11/interfaces.md)把诊断与业务终态隔开。FF 有持久 job 和关联 ID。ET 在选用的 stderr 协议中报告用量，SID 错误回复也占有固定输出通道。反馈旁路要兼容这些通道。CWP 的 AUTO outbox 属于来源生产；固定公司抽样、预算和四路审查沿用 Audit 的现有责任。
- RF Audit 保存原始 `(run_id, review_attempt, role, issue_id)` 并已把根因关联到修复和复测。`pool_progress.py` 能计划、恢复和应用观察，实际启动 agent 属于宿主。旧发现仅传引用。早期已知的公司池暂停条件不能被修复队列触发。
- 2026-11-17 只读普查发现 RF 有 9 个并行本地提交和 3 份在改运行资料；QA、IQS、Dashboard 都有活动项目；MeetingConverter 有 `.coverage` 修改。ET、SID、IR 状态和写范围适合独立实现。计划只追加归属清楚的模块文档。
- 三张卡已经分派。F3 使用本机已登录的 Codex 非交互端记录原生会话，并由总控记住 action ID。FF 本来支持同键重取、只读核对及独立 job ID。组合验收要核实 FF 作业数、原生尝试数和下载计数，同时复现总控回复丢失。现有 P1 引用视图接受指定 claim，自动业务选材和新摘要需要独立取证。
