# FC-906-b Change Contract — 角色适用性合同说明（markdown / consumer_analysis）

> FC-906 子链 2/4。2026-08-12 用户决策 A：**角色不适用必须有合同说明，catalog 侧不产出这两个角色**。本文件是机器校验的合同依据（`tests/contract/test_fc906b_role_producer_contract.py` 读取）。
> 本 FC 零生产代码改动（纯文档 + 护栏测试）；FC-906-a 已让 3 个注册 producer 产出 v2 可绑定 artifact。

## 合同裁决总表

| 角色 | DAG 依赖 | Catalog 侧 producer | 裁决 | 依据 | Consumer 归属 |
|---|---|---|---|---|---|
| `markdown` | ← `normalized` | **无**（现状，钉住） | **catalog 侧不产**——无独立角色存在意义；normalized artifact 已是 `text/markdown` | 见 §1 | 无（建议从 ROLE_DEPENDENCIES 移除，FC-1203 候选，不动冻结契约） |
| `consumer_analysis` | ← `summary` | **无**（现状，钉住） | **catalog 侧不产**——由消费者分析链（revenue/invest-*）生产并回写；catalog 只存取/复用 | 见 §2 | revenue/invest-* 分析系统（未来 FC 注册 generator 后进 GENERATOR_REGISTRY） |

## 1. `markdown` 角色 — 不适用（无独立角色）

- **DAG**：`ROLE_DEPENDENCIES["markdown"] = ["normalized"]`（artifact_dag.py:12）。
- **内容重复**：normalizer 产出的 `normalized` artifact 本身就是 markdown 全文（INSERT mime_type=`"text/markdown"`，normalizer.py:1619；`text_fingerprint` 同源）。再造一个 `markdown` 角色 artifact = 与 normalized 内容逐字节重复、无额外信息。
- **无 spec**：company-wiki 全仓无 markdown 角色 producer/格式定义；revenue `select_artifact_roles` 默认元组仅列角色名（company_wiki_source.py:149），无消费方测试。
- **GENERATOR_REGISTRY**（source_bundle.py:49）不含任何 markdown generator——绑定门 `validate_artifact` 对未注册 generator fail closed（`artifact_generator_unregistered`），catalog 侧无法产出可复用 markdown artifact。
- **对 FC-906 canary 的影响**：canary 样本不覆盖 `markdown` 角色（角色不适用合同说明，task_plan Phase 9 允许）。
- **后续建议**：从 `ROLE_DEPENDENCIES` 与消费者 roles 元组移除（属 FC-1203 清理；当前为冻结契约不动）。

## 2. `consumer_analysis` 角色 — 不适用（消费者侧生产）

- **DAG**：`ROLE_DEPENDENCIES["consumer_analysis"] = ["summary"]`（artifact_dag.py:15）。
- **Provenance 契约证明消费者归属**：revenue E2E-D06（tests/test_bundle_e2e_d01.py:384）——consumer_analysis artifact metadata 为 `engine/model/prompt/input_bundle_hash`，content 为消费者分析 JSON；复用条件 = 消费者提供的 `expected_provenance`（company_wiki_source.py:178,210）四字段全部匹配，任一变化即不复用。这些字段是**分析系统**的 provenance（模型/提示词/输入 bundle），不是 catalog producer 的。
- **触发器已预期消费者 LLM**：`trg_artifact_producer_event` 将 `consumer_analysis` 事件类型映射为 `llm`（store.py:351）——指消费者侧 LLM，与 `llm_summarizer`（只写 `summary`）无关。
- **无 catalog producer**：company-wiki 无 consumer_analysis 写路径；GENERATOR_REGISTRY 无对应 generator。
- **对 FC-906 canary 的影响**：canary 样本不覆盖 `consumer_analysis`（角色不适用合同说明）。未来消费者分析链回写时：注册 generator → 进 GENERATOR_REGISTRY → 复用链自动生效（D06 契约已冻结）。

## 3. 护栏测试（钉住"catalog 侧无这两个 producer"）

- `test_catalog_producers_write_only_registered_roles`：断言 3 个注册 producer（normalizer/llm_summarizer/section_extractor）的 INSERT 角色值集合 == `{"normalized","summary","sections"}`，且 `GENERATOR_REGISTRY` 的 generator 集合与 producer 一一对应（无 markdown/consumer_analysis producer 路径）。现状即绿（护栏）。
- `test_role_contract_document_is_valid`：本文件存在、schema 字段齐全（角色、裁决、依据、consumer 归属、canary 影响）。RED（文件缺失）→ 写文档后 GREEN。

## 4. 不变量

1. catalog producer 写路径只产出 `normalized` / `summary` / `sections` 三角色（钉住，防回归）。
2. `markdown` / `consumer_analysis` 角色在 catalog 侧无 producer（合同说明 + GENERATOR_REGISTRY 无 generator 共同背书）。
3. 冻结契约不动：`ROLE_DEPENDENCIES`、`GENERATOR_REGISTRY`、`validate_artifact`、revenue `select_artifact_roles` 默认元组均不改（移除属 FC-1203）。

---

## Addendum（2026-08-12，FC-1203）

> FC-1203 裁决（findings 59 + `assurance/fc/FC-1203/03_change_contract_fc1203.md`）：**extractive summarizer 注册为 summary 角色的第二个 generator**（`source_catalog_extractive_summary`）。
>
> 依据：`summarize_catalog` 有生产入口（`SourceCatalog.summarize` → CLI `summarize` + run pipeline），其产物此前因 schema_version 列 NULL / generator 未注册 / created_at 非 ISO-Z 而**永不可绑定**——「有生产入口但产物必然 rejected」比「无 producer」更坏。注册 + v2 元数据修复使其与 llm_summarizer 同构可绑定。
>
> 本合同 §1 的「markdown / consumer_analysis 不产」裁决不变；summary 角色允许多 generator（validate_artifact 按 generator 注册表校验，角色-生成器非一一映射）。守卫测试按本合同协议修订（EXTRA_PRODUCER_GENERATORS + summarizer.py 入 producer_modules）。

