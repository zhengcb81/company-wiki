# FC-906-a：v2 producer 绑定元数据（FC-906 子链 1/4）

> 创建 2026-08-11（FC-906 预飞完成后）。这是 FC-906 子 FC 链的第一个，由 FC-906 预飞发现驱动（findings 43/44，`revenue-forecast/audit_review/2026-08-09_full_completion_assurance_plan/fc_906_preflight_blocker.md`）。
> 状态：`pending`（WU 卡片就绪，待下一会话从 RED 起执行 16 步生命周期）。

## 背景（为什么需要这个 FC）

FC-906 预飞只读跑 FC-901 生产 dry-run（首跑）：input 7718 → **bindable 0 → legacy_unbound 7718**。失败原因 `artifact_schema_unsupported` 7579。根因：生产 producer 写 artifact 时从不打 v2 `schema_version`，而 `validate_artifact`（artifact_handle.py:90-92）要求 `artifact["schema_version"] == ARTIFACT_HANDLE_SCHEMA_VERSION`（"1.0"），缺席即拒绝。

**本 FC 不修历史 7718**（按路径 C 决策，遗留诚实保留 legacy_unbound）。本 FC 只让 producer 未来产出可绑定 artifact，为 FC-906-b/c 的 canary 语料打基础。

## WU 卡片（runbook §4）

- **Owner repo**：company-wiki
- **Base triplet**（待执行时重验）：revenue `c79d7cc` / filing `6b61771` / wiki `0c9adac`（wiki dirty: `llm_cost_log.csv`）
- **Dependency receipts**：FC-905-a/b accepted（producer_events 触发器 + envelope 已就位）；FC-901 accepted（dry-run 工具 + 绑定门）；FC-902 accepted（GENERATOR_REGISTRY + validate_artifact 单一来源）
- **Allowed files**（待 reviewer 预批 + CodeGraph impact 确认）：
  - `src/company_wiki/source_catalog/normalizer.py`（artifact metadata_json 构造处，~1602+）
  - `src/company_wiki/source_catalog/llm_summarizer.py`（~425-445，generator `source_catalog_llm_summary`）
  - `src/company_wiki/source_catalog/summarizer.py`（~245-265，若仍为活路径——执行时确认 llm_summarizer vs summarizer 哪个写生产 summary）
  - `src/company_wiki/source_catalog/section_extractor.py`（~300-320，generator `source_catalog_section_extractor`）
  - 新增/更新对应 producer 测试（`tests/` 下）
  - 本证据目录 `assurance/fc/FC-906-a/`
- **Forbidden files/roots**：`artifact_handle.py`（绑定门，不改——schema_version 契约已冻结）；`artifact_backfill.py`（FC-901 工具，不改）；revenue/filing 仓（零改）；生产 catalog（只读）
- **Intended behavior delta**：每个 producer 写 artifact 时，artifact 的 `metadata_json` 包含 `"schema_version": ARTIFACT_HANDLE_SCHEMA_VERSION`（"1.0"），使 `validate_artifact` 在其余门通过时返回 `reusable=True`。
- **Contract/schema delta**：无 schema 版本变化（artifact handle schema 仍 1.0）；只是 producer 开始正确填写既有契约字段。无消费者迁移（envelope/bundle 读取不变）。
- **Expected call-edge delta**：无新增/消失 production edge；纯数据填写。
- **Data migration**：none（不碰历史 artifact；只改 producer 代码，影响未来产出）。FC-906-c 才在 canary 上 apply。
- **Side-effect budget**：discover/fetch/write/parser/LLM 全 0（纯代码 FC，测试在 temp catalog）。
- **Max diff budget**：≤4 生产文件 + 测试；每文件 < 10 行（加一个 dict key + 可能的常量 import）。
- **Production callers before**：4 producer INSERT 点；validate_artifact caller 不变。
- **Scenario IDs**：AR-01（artifact 可复用）、MIG-01（绑定门有效）、SAFE-04（无伪造）
- **RED command / expected failure**：新增 producer 单测——对每个 producer 在 temp catalog 产出 artifact 后，`validate_artifact(artifact, source=<该文档 primary_source lineage>, registry=GENERATOR_REGISTRY, allowed_roots, now)` 返回 `reusable=False, reason="artifact_schema_unsupported"`。RED 前确认 producer 确实没打 schema_version（生产已证 0/7718）。
- **Implementation steps**：
  1. 在 4（或确认后的 3）个 producer 的 artifact metadata_json `canonical_json({...})` 字典里加 `"schema_version": ARTIFACT_HANDLE_SCHEMA_VERSION`（从 `artifact_handle` import）。
  2. （可选，建议同 FC）加 `"source_sha256": <源 content_sha256>`，强化 mismatch 检测——producer 已知输入源 hash。若增加复杂度超 budget，拆 FC-906-a2。
  3. RED 转绿。
- **Focused commands**：`python -B -m pytest tests/contract/test_source_catalog_<producer>.py -q`（4 个 producer 各自）
- **Repo commands**：`python -B -m pytest tests/ -q`（全量 wiki 套件，~7min，2209 passed 基线，2 pre-existing PORT-01 失败不计）+ ruff + compileall + coverage
- **Cross-repo commands**：无（纯 company-wiki FC）；revenue/filing 不受影响（envelope 契约不变）
- **Negative/fault-injection command**：mutation——删掉某 producer 的 schema_version 填写 → 其 RED 测试必须回到 `artifact_schema_unsupported`。
- **Mutation**：M1 = 移除 normalizer 的 schema_version stamp → normalizer RED 失败；M2 = 同 for llm_summary；M3 = 同 for section_extractor。每个必死。
- **Real-data tier**：T0（unit）/ T1（contract）；T2 生产只读复核（dry-run 证明新 fixture artifact bindable，历史仍 0——后者是预期，不是回归）
- **Rollback**：纯代码 revert（git）；无数据副作用。
- **Acceptance**：4 producer 各有 RED→GREEN；3 mutation killed；全量 wiki 套件零新失败；独立 reviewer 干净 checkout 复跑；can_accept gate exit 0。
- **Stop conditions**：producer 布局与预期不符（如 summarizer.py 是死代码、实际只有 llm_summarizer 活）；schema_version 应写 column 而非 metadata_json 的合同争议；diff 超 budget → 拆 FC-906-a2。

## 执行前必做（下一会话）
1. planning-with-files 五问重启 + 重验 triplet + plan hash。
2. CodeGraph `codegraph_impact` 确认 4 个 producer INSERT 点无遗漏（注意 summarizer.py vs llm_summarizer.py 哪个活）。
3. 确认 `summarizer.py` 是否死代码（若是，不在 allowed files；记 FC-1203 清理）。
4. 决定 source_sha256 是否纳入本 FC（建议纳入——producer 已知源 hash，且让 binding 更强；若超 budget 则拆 a2）。

## 预检实测更新（2026-08-11，执行中）
- **summarizer.py（extractive）OUT OF SCOPE**：generator `source_catalog_extractive_summary` **不在 GENERATOR_REGISTRY**（FC-902 只注册 normalizer/llm_summary/section_extractor），且生产 0 artifact（2910 summary 全是 source_catalog_llm_summary 2675 + 235 空 generator_name）。即便打 schema_version 也会 `artifact_generator_unregistered`。是否注册它属 FC-902 合同决定，记 FC-1203 候选。**FC-906-a 只覆盖 3 个注册 producer：normalizer / llm_summarizer / section_extractor。**
- **隐藏缺陷 created_at 格式**：3 个 producer 都用 `datetime('now')` 写 created_at（"YYYY-MM-DD HH:MM:SS" 空格格式，生产 0/7718 ISO）。`validate_artifact` `_UTC_RE` 要求 `YYYY-MM-DDTHH:MM:SSZ` → 修完 schema_version 后下一个失败是 `artifact_created_at_malformed`。**FC-906-a 必须同时修 created_at**（`datetime('now')` → `strftime('%Y-%m-%dT%H:%M:%SZ','now')`）。两者都是 v2 binding gate 必需——同一行为单元。
- **RED 测试**断言端到端契约：每个 producer 产出后 `validate_artifact(...).reusable is True` + metadata `schema_version=="1.0"`。RED 失败（schema_version 缺 + created_at 畸形）；GREEN 修两处后通过。harness：external-root catalog（normalize+sections，仿 test_source_catalog_section_extractor）+ focus-root catalog（LLM summary，仿 test_source_catalog_focus_admission 的 _Client/_Response）。
