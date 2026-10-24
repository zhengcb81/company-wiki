# 独立项目施工包（2026-10-24）

本目录是三张可分别交给不同 harness 的卡片总入口。三张卡分属三个独立 Git 仓库，产品代码路径互不重叠；不修改 company-wiki、filing-fetch、revenue-forecast、StockWiki 或 invest-quick-scan，也不依赖当前主线资料和供应商额度。三卡现均经 ROOT 核对最终交接、独立复审、测试/清理证据和代码 SHA 后接收：IR-REPORT-GENERATION、QA-RAG-SAFE-REBUILD、MC-OUTPUT-INTEGRITY。各外部仓库的作者分支仍独立保留；本次接收不代表已跨仓合并或推送。逐卡证据见[ROOT验收记录](../../review/market-family-upgrade-20261024/formal-v4-and-cards-root-acceptance-20261025.md)及 `dispatch.json`。company-wiki 主线现已跑完唯一 formal-v4 attempt、摘要持久化、恢复/cache 和 FF 复用；RF 内容消费、覆盖与业务质量仍开放，下一步先修选择/分批导致的 partial coverage 根因。

| 卡片 | 独立仓库与代码范围 | 建议工作目录 | 冻结起点 |
|---|---|---|---|
| [IR-REPORT-GENERATION](IR-REPORT-GENERATION.md) | industry-research：tools/report_generator.py 和新报告测试 | C:/Users/郑曾波/Projects/industry-research-report-generation | main 4a80f9988f9325fb0a348c8acd9e41d615005c5f；原仓干净；未显示 remote |
| [QA-RAG-SAFE-REBUILD](QA-RAG-SAFE-REBUILD.md) | QAbyLLM：只保护应用层 RAG 索引重建与发布；不改数据库引擎/schema、不迁移真实库 | C:/Users/郑曾波/Projects/QAbyLLM-rag-safe-rebuild | main ad389f84cd15e54207fc6fcfe4881f86edac63f；与 origin/main 一致且干净 |
| [MC-OUTPUT-INTEGRITY](MC-OUTPUT-INTEGRITY.md) | MeetingConverter：core/output.py 和 tests/test_output.py | C:/Users/郑曾波/Projects/MeetingConverter-output-integrity | master 8a33a7f96292af8e6574d98b959703c6d11919eb；origin/master；原仓已有 M .coverage，必须保留 |

每项应从指定冻结提交新建独立 worktree 与任务分支，不在原工作区切换分支。若建议工作目录已存在，先核对其身份与状态，不得覆盖。不同卡不共享缓存、数据库、测试输出或运行服务。

## 所有卡共同的完成与审查规则

1. 开始时重核冻结 HEAD、branch、status 和本卡允许路径；项目自身 AGENTS/README 与本卡冲突时报告总控，不扩大范围。
2. 测试只用合成输入和测试临时目录。记录测试根最初与最终的文件清单和 SHA，证明恢复原样。不得写真实配置、用户目录、生产知识库、音频或公司材料。
3. 实现和测试完成后先提交到任务分支，冻结最终 commit。随后必须调用未参与实现的独立审查 agent。审查者直接读本卡及完整 diff，独立运行验收命令，并自行增加至少一个反例；不能只读作者总结。
4. 审查发现的每个问题都必须修复。修复后重跑受影响测试，再让独立审查者检查最终 SHA。只有审查结论 PASS 且绑定 SHA 与最终 HEAD 一致、测试通过、测试数据清理证明完整，才可交接为 COMPLETE；否则标 INCOMPLETE，不得交接完成。
5. handoff.md/json 必须列出起止 HEAD、branch、精确变更路径、测试命令/退出码/日志、独审报告与绑定 commit、每个发现的修复证据、测试前后 inventory/SHA、原有脏文件保护情况、网络/API/模型/下载计数、交付体积和 remote/push 状态。
6. 仅做一次集中验收，不逐小步增加人工签收。完成后提交任务分支，不自行合并主线。仓库没有 remote 时如实写明，不猜地址。

## 隔离边界

- 三个项目目录与彼此及 CWP 主线均不重叠。
- Industry Research IN-02/T02 的 StockWiki/IQS 接线不是本卡范围；不得修改 skill 接线、StockWiki、IQS、company-wiki 或安装副本。
- QAbyLLM 的 config.yaml、vector_db、test_vector_db、output 和真实公司报告禁止触碰；只用 fake store 或卡内临时本地 store。
- MeetingConverter 的最近 CI fast-gate 工作已交付；本卡不改 workflow、push gate、batch/pipeline、ASR、翻译或真实 output。原仓 .coverage 修改不是本卡数据。
