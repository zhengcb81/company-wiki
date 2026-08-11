# FC-906-b Decision Request — markdown / consumer_analysis producer spec gap

> 2026-08-12。FC-906-a accepted 后，FC-906-b 预检发现：**"产出这俩角色"无 spec 依据**，且契约证据指向相反方向。按 runbook §10（数据模型/写入目标/用户可见行为变更必须 decision request），停下记录。

## 证据

### consumer_analysis（DAG: ← summary；触发器标 llm 事件）
- revenue `tests/test_bundle_e2e_d01.py` E2E-D06（已有契约）：artifact metadata 为 `engine/model/prompt/input_bundle_hash`，content 是消费者分析 JSON（`{"finding": "revenue 1000"}`）；复用条件 = 这四个 provenance 字段全部匹配。
- `scripts/company_wiki_source.py:178,210`：`expected_provenance` 由**消费者**提供；consumer_analysis 只有 provenance 匹配才复用。
- **解读**：该 artifact 是"消费者分析系统"（revenue/invest-* 链）生产的分析结果，company-wiki catalog **不是它的 producer**。catalog 只负责存取与复用。store 触发器的 llm 标记指消费者的 LLM，不是 catalog 的 llm_summarizer。

### markdown（DAG: ← normalized）
- company-wiki 内**零 spec**：无 producer、无格式定义、无消费方测试（revenue 仅把角色名列在 `select_artifact_roles` 默认元组）。
- normalizer 产出的 `normalized` artifact 本身就是 `text/markdown`（normalizer.py INSERT mime_type="text/markdown"）。再造一个 `markdown` 角色 artifact 与 normalized 内容重复。
- **解读**：该角色在 catalog 侧无独立存在意义；疑似是 DAG 里的"占位/历史"角色。

### FCAP task_plan Phase 9 原文
> "normalized、markdown、sections、summary、consumer_analysis 各至少一个真实 bound 样本；**角色不适用必须有合同说明**。"

即：若调研证明角色不适于 catalog producer，合法路径是**合同说明 + 不产出**，canary 覆盖真实存在的角色。

## 用户决策②的原始语境
2026-08-11 用户在 FC-906 预飞后选"先产出这俩角色"——当时前提是"存在这样的 producer 工作"。本轮预检（spec 调研）证明前提不成立：无 spec、且契约证据显示 producer 归属消费者侧。

## 选项
- **A（推荐）**：FC-906-b 改为"角色适用性合同说明"FC——为 markdown/consumer_analysis 各写一份合同说明（consumer_analysis: 消费者侧生产；markdown: 无独立角色、与 normalized 重复），加测试钉住"catalog 侧无这两个 producer 的写路径"，然后 FC-906-c 的 canary 只覆盖 normalized/summary/sections 三个真实角色。符合 task_plan"角色不适用必须有合同说明"。
- **B**：用户给出新 spec（markdown=X、consumer_analysis=Y 的内容/格式/producer），按 spec 实现。注意：没有任何消费者请求这两个 artifact，存在伪需求风险。
- **C**：consumer_analysis 由消费者（invest-*/revenue 分析链）回写 company-wiki——跨仓 producer FC（invest-* 侧无 producer 现状，工作量大）。
