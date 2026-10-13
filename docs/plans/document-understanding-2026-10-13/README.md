# 文档理解升级 — ROOT 总入口

2026-10-13：三包已实现并合并到 ROOT 分支，跨层验收通过（331 tests，含真实原件节点）；
**生产解析链尚未切换**。与原跨市场母计划相连；W08 RF/Audit 接收、真实 G2/G4/G5 保持开放。本目录不是新的许可或人工签收系统。

先读 [实证 findings](findings.md)、[设计](design.md)、[实施及测试](implementation.md)。三条线共用 [接口](INTERFACES.md)，各自拥有独立 checkout 和写入目录。ROOT 负责生产适配、并线、跨层测试、母计划状态。

| 施工卡 | 工作目录（各为独立 CWP worktree） | 独占产物 | 状态 |
|---|---|---|---|
| [DU-PROFILES：文档路由与阅读策略](cards/DU-PROFILES.md) | `C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/profiles` | `src/company_wiki/document_understanding/profiles/` | 已交付 150 测试，已合并 |
| [DU-STRUCTURE：跨页章节与语义单元](cards/DU-STRUCTURE.md) | `.../document-understanding-20261013/structure` | `src/company_wiki/document_understanding/structure/` | 已交付 47 测试，已合并 |
| [DU-BENCH：真实样本质量基准](cards/DU-BENCH.md) | `.../document-understanding-20261013/benchmark` | `tools/document_understanding_benchmark/` | 已交付 65 测试，已合并 |

各卡同时列出自己的 tests/fixtures/交接路径。施工期间不改对方代码，不改现有生产入口，不改母 PWF、依赖清单、hook/CI、生产配置。缺共享字段写入各自 `handoff.json`，由 ROOT 一次协调；不自创不兼容接口。三个包用冻结 JSON 夹具独立施工，不等待彼此；ROOT 接入阶段才依赖三包。

ROOT 的接线成果：`document_understanding/{observation_adapter,orchestration,selection_bridge,pipeline}.py`
与端到端入口 `understand_units`（`du-pipeline/1`）。合并阶段修掉的三个"只有并成一条链才暴露"
的接线缺陷记录在 [task_plan](task_plan.md) 中，其一（两 lane fixtures 同名）会导致 CI 的四套件
同跑直接收集失败。

## 样本和边界

- 20份原件：**15 PDF + 4 HTML + 1 TXT**，PDF共2390页。原件总约63.89MiB，均只读、未复制。
- `sample_manifest.json` 保存调查路径；`sample_observations.json.gz` 是有界抽读/路由观察；`selector_probe.json.gz` 是三份真实 selector 诊断；`routing_ablation.json` 是同一原件更改类型/上限的对照。
- `inspect_samples.py` 和 `probe_selector.py` 仅调查复现入口；不代表生产 SourceRef 读取规范，不能被业务模块导入。前者需要解压/输出 observations 的正常 JSON，后者生成诊断 JSON；运行后可按记录归档，禁止留下整篇文本副本。
- 原生文本扫描约7秒（第二次warm run）；三份生产解析/选择合计21.956秒。不是供应商摘要、完整召回率或普遍性能结论。
- 样本中的临时测试根可能将来不存在。DU-BENCH 必须按 SHA＋本机 bindings 解析，缺源显示 UNAVAILABLE；不能直接把本清单绝对路径固化进产品或 CI。

## 当前顺序

ROOT 先完成本目录方案；可分发三包。接收 W08 RF/Audit → 接收三包并完成章节适配/选择/摘要一体整合 → 合并原母计划真实 G2 → G4原三家公司 → G5新三家公司 → 后续审计循环。不会用这轮样本调查替代真实研究验收。
