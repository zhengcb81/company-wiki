# DU3-DEPENDENCIES：选择决策依赖与局部失效纯组件

## 直接启动

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/dependencies`。
分支：`codex/du3-dependencies-20261014`。读本卡、`../INTERFACES.md`及工作树`.planning/du3-dependencies/task_plan.md`实际base。现在可开始，不等ROOT或其他卡。

背景：共享DU已完成实际采用策略指纹；生产接线尚未完成。仅hash最终送出的策略无法保证选择缓存：旧未选但参与决策的候选改优先级/匹配信号，可能成为新赢家。ROOT将改正式两阶段generation，交给你的是**纯内容身份与差异判断组件**。

## 排他写范围

- `src/company_wiki/document_understanding/decision_dependencies/**`；
- `tests/unit/document_understanding_decision_dependencies/**`；
- `tests/fixtures/document_understanding_decision_dependencies/**`；
- `.planning/du3-dependencies/**`。

不改父包__init__、profiles/registry/router、structure、selection_bridge/summary_input、任何source_catalog或automation/generation、Store/SQL、ROOT PWF、其他tests、依赖/CI/config/安装。模块互不导入另外两包，无网络/原文件/模型/系统时间读取。

## 冻结接口

公开`freeze_decision_dependencies(trace, *, limits=None)`和`compare_decision_dependencies(frozen,current,*,limits=None)`，wire严格按DU3/1。JSON可序列化，稳定排序与完整digest。输入是caller提供的本源决策域scope、实际查验components、候选membership/eligible和算法版本；**你不负责发现真实候选**，不在包里再实现router/selector。

1. 覆盖父/子scope、已查验未匹配与匹配败选者、matcher/full content版本、完整候选集合与算法版本；新增/删除/移入范围等有因果差异。
2. 数组顺序不影响identity；相同ID不同内容冲突、错误类型、悬空引用明确拒绝，不静默去重/截断后给same。有效same只对完整inventory成立。
3. 缺trace/legacy/incomplete或工作预算到限返回unavailable/partial，不形成复用证据。比较equal不等于CACHE_HIT，ROOT仍做原文/locator读取校验。
4. 无关域不在本输入内，不能自动加入whole catalog；同时不能允许caller用最终winner清单冒充完整决策inventory。文档说明caller责任和不可认证的外部漏报。
5. full SHA256作内容身份，短profile版本仅展示；不把API密钥/env名、路径、run ID、当前时间、费用/timeout等非内容字段纳入manifest，不保存政策正文/原文/DOM/all-units。
6. 默认最多64scopes/512components/4096candidates/2MiB输入/200000work，可下调。每个循环/大容器都计实际工作，超限停止，不产生半图complete。序列化多文档体积实测。

## A/B/C（只有三个大节点）

**A：TDD。** manifest_contract/dependency_mutations反例先RED：败选者priority/alias/content变化、zero-match matcher变化、新候选加入/移入/删除、child范围、版本变化都改变；只调数组顺序不改变；无关域正文不需要加入当前trace。

**B：实现与工程。** compare/serialization_limits集中测试：严格schema与finite JSON、跨进程digest稳定、输入未改、duplicate/scope引用错、缺inventory/零work/小byte cap不得same；100-source manifest编码体积报告。模块不调用selector、registry或Store。

**C：独立快照回放。** 使用现有catalog的只读测试快照构造明确scope/candidate inventory，实际执行相关/无关变化矩阵，留小收据。可用synthetic合法scope，不需ROOT正式trace；明确真实catalog快照与合成scope的界限。正式0POST/CAS/恢复由ROOT B验收，你不能只因compare绿认证它们。

临时fixtures/目录用TemporaryDirectory与sentinel恢复；0模型/网络/原件/生产配置写入。沿已有JSON/hash方法但不添加新的授权/签收文件。测试有真实内容变更的正反例，不能只断言字段存在或镜像实现计算hash。

## 交付与ROOT接线缝

正常提交本branch，按DU3/1写小handoff包，列A/B/C命令、exit、耗时、正确/不完整情况、字段和资源上限。STOP等ROOT。

明确当前registry.policy_components只有adopted组件；本包不能凭它证明败选候选。ROOT会在实际router/registry/选择处记录完整trace、提供当前同域inventory、将指纹接AUTO既有Store/CAS，再做真实reuse/recovery。不要为“帮ROOT接完”越界改这些文件。
