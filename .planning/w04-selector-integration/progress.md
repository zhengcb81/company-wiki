# W04 selector 并线准备进度

## 2026-10-11

- 收到 ROOT 只读并线准备任务，写域固定为本目录。
- 阅读 planning-with-files 技能，创建独立计划；不覆盖原共享计划。
- CodeGraph 已查询，返回 canonical 旧索引的分组结构；新 WIP 按已知文件直接读取。
- 已派只读依赖归纳子 agent，与本线程三方字节审计分工；双方不改源码或 Git。
- 尚未运行产品测试、provider、网络或 LLM。

## 只读盘点完成

- 旧树 HEAD35a9a645 与当前 main d75f0d42 的 Git blobs/冻结 target 三方盘点 25 行，Git HEAD/index/status 在盘点期间未改。
- 精确接收集 18 行（8 源、10 测试）；18 行 main 与 base 均无内容冲突，5 个前置源/既有测试早期 freeze 仍精确，Phase2 7 个产品 freeze 仍精确。
- 独立 G2 配置 4 行排除；CI 工具两行已在主线；CI 测试一行旧 target 缺 main 新的 6 个 OCR 回归正控，保留 main。
- 解析 18 文件 AST，27 个直接 source/test 导入条目：需要新内容的都在写集，其余 main 与旧依赖内容一致。无隐藏未提交 helper 依赖。
- 只读依赖子 agent 已交接并 STOP；验收出处落入 integration-manifest.json。
- 编写干净当前 main 新工作区三方接收步骤、一次 4 模块普通集成测试、独占 scratch 恢复、集中提交推送步骤。
- 不重跑 375/六原件，不执行产品测试；源码/Git/config/原件零写，provider/网络/LLM/费用零。
- 准备包完成，接收实施交给 ROOT，STOP。
