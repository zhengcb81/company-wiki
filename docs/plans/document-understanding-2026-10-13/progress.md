# 进度

## 2026-10-13 ROOT

- 按用户要求启动设计调查；读取 PWF/PDF 技能和现有路由。
- 本轮0下载、0外部LLM调用、0原件写入。当前只增加本子计划；生产代码未改。
- 下一步：原件抽样与架构实证。

## 2026-10-13 调查完成

- 20文档原生扫描/重点抽读，4页图像目视；3文档真实parser0.1.1/selector0.8.0回放共21.956秒；恒锋同parse类型/预算对照确认仅调cap不能解决建设期漏选。
- 完成design.md、INTERFACES.md、implementation.md与三独立卡。保留当前存储/来源/Worker/配置模型责任；新增结构和profile，不加权限/签收。
- 原件0复制/改动，LLM0调用；四PNG已删除，原始观察压缩后删除自有JSON副本，摘要与压缩证据留本子计划。
- 当前只写文档/调查脚本；无生产代码、配置和其他仓库改动。尚未分发或启动任何harness。

## 2026-10-13 三包合并与跨层验收

- 三条 lane 全部交付并 merge 到 `codex/du-root-integration-20261013`：DU-PROFILES（150 测试）、
  DU-STRUCTURE（47）、DU-BENCH（65）、ROOT 适配/编排/选择桥/pipeline（68）。
  同一 pytest 调用下 **331 passed / 5 skipped**（26.1s）；`ruff check src tests/unit tools` 全绿。
- 新增 ROOT 端到端入口 `document_understanding.understand_units`（`du-pipeline/1`），把
  observation → route → profile → structure → dependency packages 串成一条链。
- 真实原件节点由 **10 skipped 变为 10 passed**（修复了测试里算错的仓库根路径），
  另 1 项真实 legacy-vs-new 对照也实际运行并通过。
- 合并阶段修掉 3 个只在"并成一条链"时才暴露的接线缺陷，详见
  `task_plan.md` 的"合并阶段发现并修掉的接线缺陷"：路由对编排是 no-op、两 lane fixtures
  同名导致四套件同跑收集失败（CI 的跑法）、四个测试模块仓库根路径算错导致真实节点静默 skip。
- 原件 0 复制、0 修改；本层仍未接入生产入口，生产切换按母计划另行执行。
