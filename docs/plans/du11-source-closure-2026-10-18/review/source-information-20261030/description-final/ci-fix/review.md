# 0.8 来源描述兼容边界独立终审

结论：**PASS，修复范围内 OPEN=0**。4 文件实际 raw/LF SHA-256 全量列于 `review.json`、`final-hashes.json`；最终测试前冻结并在签署时复核一致。

独立 **9 passed / 0 failed / 0 skipped，pytest 1.41 秒，命令 3.35 秒**，见 `final-r2.log/xml`。此前同范围 8P/1.75 秒与 7 个短 probe 不相加；ROOT 的 136P、65 原证据单元、71 正式描述用例，以及最终扩展域 3525P/11skip/75.37秒、397源mypy/ruff，均为单独报告。ROOT 最新保存源重选的15spans／8卡／8输入检查点未在本短修复范围独立重读。

共因是默认 0.8 的 `_operating_fact` 无版本隔离地合并 0.9 新描述关系，静态构成／定义经 eligible 和 operating_mechanism 捐入旧动态选择。当前修法正确地只在 0.8 适配器显式关闭 source descriptions；共享 prepared `function_or_event` 语法 family 与 material 强弱分开。没有按 reason 字符串或旧测试全文做白名单，也没有全局拒绝定义。

不能对整份 reading 施加 raw material gate：独立探针证明付费席位数量和 usage billing 的 raw role payload 都可为 None，但它们已有真实计量／计费关系证明。最终公共默认选择检查保住这两类与客户认证事件；三个旧 CI 静态输入均恢复不入选。0.9 的具体未知产品构成仍支持，未知单项仍 unresolved；多类／配套的泛修饰不再成为独立 payload。原事实、milestone/planned/resource 分支未被统一 gate 删掉，policy/26 保持缓存语义依赖。

原六文件工程 PASS 保留为历史，不代签后来暴露的兼容失败。CI40996278861 已观测 failure，本独审只证明当前本地修复，不把原失败 run 或未来精确 CI 写成绿色。受影响域、正式摘要、恢复／跨run缓存、FF/RF、W21、holdout 与总循环未代签。

清理：只写此 ci-independent 目录；未改产品、作者测试、PWF 或配置。config diff 为空，原 pre-push 仍为 0/0 内容变更的 mode WIP；Python `-B`、pytest `no:cacheprovider`，目录无缓存子目录。探针／日志／XML 保留，未读原件、SDK、密钥，0 外部调用、0 下载、0 其他仓写入。
