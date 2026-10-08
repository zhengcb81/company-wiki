# Phase 6 三条独立施工线（2026-10-08）

本轮新施工卡，针对三市场实测的未解决根因。不是之前已完成的 G/P/N/W 卡重发。MAIN 是唯一总集成者，维护共享 PWF、主线和安装副本；各 harness 只维护自己的分支、测试与交接。无需每个小节点人工签收。

**当前状态：三卡已交付、MAIN已查收并合入远端主线（2026-10-08）；不重复开工。原工作目录保留供追溯，MAIN恢复负责各仓接线。** MAIN 保留独占边界，不重复派发。卡文件是上下文入口，工作目录是对应独立 checkout；两类路径用途不同。实际运行进度以后续分支/交接为准，不把分派意图冒充正在运行的进程。

## 已交付的分工（历史施工边界）

| 线 | 独立卡 | 项目及工作目录 | 工作量和交付 | MAIN 不同时修改的范围 |
|---|---|---|---|---|
| R6-FORMAT | [cwp_format_normalization.md](cwp_format_normalization.md) | company-wiki；`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/cwp-formats` | 较大：HTML/PPTX 确定性解析、原文定位回放、图片缺口与资源上限 | 新 `src/company_wiki/document_normalization/`、`tests/document_normalization/` 及该线 docs |
| R6-RF-INPUT | [rf_input_semantics.md](rf_input_semantics.md) | revenue-forecast；`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-inputs` | 较大：单位/目标口径、证据角色和实际输入依赖，共用构建及正式计算验证 | RF 全部源码、测试和说明；MAIN 仅只读运行当前已发布 RF |
| R6-FF-CAUSE | [ff_provider_diagnostics.md](ff_provider_diagnostics.md) | filing-fetch；`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/ff-diagnostics` | 中等：真实上游失败原因、安全传播、重试边界与公开 CLI 验收 | FF fetch/公开错误封装及该线测试/docs；已发布 transcript 运行文件冻结 |

三个实际工作目录彼此独立。R6-FORMAT 与 MAIN 同属 CWP 仓，但**写入子目录不相交**：该线不改现有 source_catalog、automation、source_contract；MAIN 在这些现有目录集成。另两线分别独占 RF、FF 工程改动。禁止在三个 canonical 主目录施工；主目录保留 owner WIP。

## 已稳定的输入

- RF main `72ce94c160bbb5b9399c8716307588b443a72a83`：stable-fsum/1 已通过原三公司 full，经济结果不变、US 多 seed 强校验修复。
- FF main `697af966475a4aa7bb0687c78bfb81a7edb54f21`：0 增量费用请求交 ET；公共 v2 保留实际 HTTP 用量。ET main `282e8908e98196447e3ac72d95a4c7425a3aa322`。费用/能力升级已并线推送，源码责任和跨仓离线链通过；当前 FMP 账户真实 entitlement 拒绝仍单列。
- CWP 的 raw-only bounded Dayu 桥已经真实三市场验收；本线开始基准由 worktrees.json 精确登记，不要求其他 harness 等后续 MAIN commit。
- SourceRef/SourceExport v2、EvidenceSpan 和原 PDF/TXT 的已发布回放合同保持。跨仓只交换现有逻辑引用和版本接口，不暴露目录、不共享可写数据库。

## 接口与集成顺序

1. FORMAT 的纯解析 API 在卡中固定；MAIN 可同时补现有 Worker 路由、资格/公开日诊断及预算内图片处理，暂用同接口小夹具，最终换真实解析器。解析线不调用模型、不决定投资含义。
2. RF 输入线消费现有来源/叙述引用，不依赖新的 HTML/PPTX 实现；用原 PDF/TXT 或人工构造的小证据包测试。新格式处理后 MAIN 再做真实 NarrativeRef→claim→参数全链。
3. FF 诊断线读取 CWP 已发布错误接口；先用实际 CLI/坏配置等确定性反例，不要求 MAIN 同时改 CWP。发现缺失机器字段，交接口差异清单给 MAIN，不私自跨仓写。
4. 每线先记录 RED，再实现，最后仅一个集中责任层/集成/隔离 E2E 节点。harness 提交自己的分支和交接；MAIN 接收后复核差异、合并、定点安装及集中原三公司回归。
5. 三线接通后 MAIN 执行完整新研究和另一组三公司的独立执行/审查。离线 fixture、金额相同或文件存在都不能冒充真实模型消费/事实正确。

## 共用交接接口

见 [handoff_interface.md](handoff_interface.md)。每线自己的 docs 内保存 `task_plan.md / findings.md / progress.md / HANDOFF.md / handoff.json`，不写本目录共享计划。交付只需 Git commit、小结果和重现入口；不交几百 MB 的临时转换库。

## MAIN 接续工作

FF/ET 费用发布收尾 → 来源资格/公开日与有界诊断 → Worker 新格式接线、统一选片与版本回放 → 按接口接收三线 → 原三公司真实全链与独立复查 → 新三家公司泛化验收。各线完成顺序不固定，先到先接；最后的大节点不省略。


查收与合并后问题见 [r6_handoff_intake.md](../phase6/r6_handoff_intake.md)。当前未分派新包。
