# MAIN：跨 run 默认复用同一来源的叙述派生

状态：待实施；主线 Phase6，完成后才能进入两组三市场研究大节点。不是公司池新一轮抽样。

## 根因和职责

现请求 input_hash 含 run_id/预算，流入 event.policy_version/job_key；同一来源不同 run 会重新执行三个任务和 POST。现对象存储只是响应生成后去重，不能避免模型重复调用。不要直接从 job_key 删 run：现 narrative_run_jobs.job_id UNIQUE，run store 明确拒绝把别的 run 的 job 借来作为本 run。

复用属于 CWP 现 AUTO/来源派生责任；消费者不自己建立缓存、读取物理路径或另建任务/费用库。原始资料与旧事件、费用账保持；原件不翻译，不写研究结论。当前主线已包含 W03 来源入库及实际 carrier 路由。

## 实施顺序

1. 用 CodeGraph 阅读 NarrativeBatchRequest、run store、job/effect/artifact key、模型和 public reference/read 的现绑定。核清单 source 生成 key 的输入及已有 binding_json，先在包内写设计和失败用例。
2. 定义来源派生稳定 identity：实际 raw SHA、选择与解析/locator版本、prompt/schema版本、有效 profile/model 和会影响正文处理的参数、输入来源处理元数据。run_id、预算数额、目录物理位置和本次审计标识不成为内容 identity。影响生成的真实字段必须保留，不能粗略只按 raw SHA 复用。
3. 默认先找同 identity 的完整且可见 artifact，按现 byte/hash/replay/SourceRef 机制打开。成功后为当前 run 用现有 binding 保存来源与 artifact pin，历史 origin run 可以保持；不把他人的 job 改归当前 run、不迁移或重记历史收费。当前 run 本次 supplier 费用/调用为实际零。
4. 找不到完整派生才使用既有 AUTO 任务、lease/generation/outbox。并发相同 identity 的请求不能同时发同一 POST；使用现有可恢复锁/任务状态，等待/引用已有进行中的 generation，失联按原恢复机制处理。不增加第二套调度器、数据库或收费账。
5. 显式 refresh 才新生成；定义它与 generation 的确切语义，失败不覆盖旧可用结果、不污染默认可见版本。不能重建许可/人签/canary。默认 reuse 不能被因无本次模型额度而阻断。
6. public batch/reference/read 及 source-only consumer 向后兼容；复用状态/本次计量真实反映，不把元数据引用叫实际读入。旧 artifacts 保留原版本，不静默重解旧 locator。

## TDD / 一个集中验收节点

- 不同 run 同来源/同配置：真实 configured finite launcher、loopback模型，仅一次实际 POST；第二 run 公共 read 能 verified replay 同来源/span/claim/hash，无新 reservation/收费。
- source 字节、parser/selector/prompt/schema或实际模型改变必须 miss；仅换物理根/合法预算/run_id 应 hit。坏/缺对象或失败 generation 不能复用成成功。
- refresh 确有第二 POST；refresh 失败后旧 artifact 仍可读，失败/未知费用保留。
- 两并发 run 同 identity 不重复 POST；worker失联/lease恢复/outbox恢复后不会丢结果或无根据计零。测试使用现有可控本地模型/故障夹具，不能联网/付费。
- PDF/TXT与HTML至少各一例；多 span 一次解析，原语言，financial tables筛选保持。当前六字段 expected_source、SourceRef/NarrativeRef合同不新增身份许可。
- 原有批次的 run 可重入/冲突/费用责任测试保持；修改旧 cross_run_e2e 的三POST预期时先增加明确新的效率失败证据，不能删除质量检查。
- 全部资料在短 owned TEMP，finally恢复初始状态。只保存小型命令/usage/SHA/locator/状态证据，不复制全量原件/图片/MD。

## owner / 交接

MAIN 指定唯一隔离 CWP worktree，代码只在那里写；另条 OCR 线拥有 document_normalization parser/OCR代码，本线不写它们。共享 narrative_formats 若需要，由 MAIN 接线。RF/FF/Dayu/StockWiki/IQS/main/安装/生产配置/原件不写。先完成独立调查报告的实际结构建议，再实施。

本线写 docs/implementation/main-cross-run-narrative-reuse/{task_plan,findings,progress,HANDOFF}.md 与 handoff.json，列 base/head、精确路径/SHA、RED/GREEN/actual public CLI/并发故障证明、旧原件和TEMP保护、已知/未知费用、接口和剩余限制。正常精准commit，MAIN审读后合并/推送/定点安装；不在每个小节点重跑全套。当前累计供应商授权$20/2M不重置，本包工程调用为0。
