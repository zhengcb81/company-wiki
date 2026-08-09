# ADR-010：FCAP 数据湖契约单一所有权冻结

- 状态：Proposed（2026-08-09，FC-101 实施者回执；待独立 reviewer 转 Accepted）
- 关联：`audit_review/2026-08-09_full_completion_assurance_plan/`（FCAP-2026-08-09-r2）、`revenue-forecast/compatibility/contract_registry.json`（机器可读单一所有权源）
- 适用范围：遵守 `docs/adr/README.md` 的 ADR scope note。**本 ADR 影响多个 source contract 的 schema version 与兼容窗口**（见下表），但仅声明所有权与版本/兼容/删除窗口，不改产品逻辑（产品接线由 FC-201~905 分阶段实施）。

## Context

FCAP r2 的中央完整性不变量是：七个数据湖契约各只有一个 owner。历史上 filing-fetch、revenue-forecast 与 company-wiki 各自出现过第二套 root policy / allowlist、identity、latest、artifact 或 admission 逻辑，造成"配置有 Dropbox 但 resolver MISSING"、`download_calls` 由 handle 存在推断、artifact source-bound=0 等伪绿问题。本 ADR 把所有权冻结到单一 owner，并把机器可读登记表放到跨仓总门 revenue-forecast，使 receipt/closure validator（FC-103）能机器校验"同一字段只有一个 owner"。

## 决策：七个契约的 owner、版本、兼容窗口、删除期限

| 契约 | Owner | 版本 | 引入 FC | N-1 支持 | 删除期限（FC 门） |
|---|---|---|---|---|---|
| RootPolicySnapshot | company-wiki | 2.0 | FC-301 | 1.x kind-based | FC-705 + Phase 14 R9 |
| NormalizedFilingMetadata | company-wiki | 2.0 | FC-402 | acquisition/dayu_meta 容器 | FC-701 + FC-705 |
| ResolutionEnvelope | company-wiki | 1.0 | FC-704 | 不适用（新；旧库显式 unavailable） | 不删除（破坏性变更须新 FC + N-1 窗口） |
| AcquisitionTrace | company-wiki | 1.0 | FC-704 | 不适用（取代推断式 download_calls） | 不删除（破坏性变更须新 FC + N-1 窗口） |
| SourceBundle | company-wiki | 1.0 | FC-902 | 不适用（此前仅 test/CLI） | 不删除（破坏性变更须新 FC + N-1 窗口） |
| ArtifactHandle | company-wiki | 2.0 | FC-901 | 1.0 legacy_unbound（source-bound=0） | FC-901 dry-run ledger + 未来授权清理 FC |
| ActivationSnapshot | company-wiki | 1.0 | FC-201 | 不适用（取代硬编码 flags/dict） | FC-201（被替换的硬编码 flags/dict 在 FC-201 删除） |

字段级定义以 `audit_review/2026-08-09_full_completion_assurance_plan/architecture_target.md` 对应小节为准（RootPolicy 第 3 节、NormalizedFilingMetadata 第 4 节、激活/回滚第 5 节、SourceBundle/artifact 第 6 节）。本 ADR 不复制字段定义，避免与 architecture_target 漂移。

## 策略源不变量

company-wiki 是上述七个契约的**唯一所有权与策略源**。filing-fetch 与 revenue-forecast 只消费，并且：

- 不得重新声明任何契约的 owner；
- 不得实现第二套 root policy / `allowed_handle_roots` allowlist、identity、latest、artifact 或 admission 逻辑；
- filing-fetch 只校验 company-wiki 返回的 policy snapshot hash；
- revenue 只调用 selector 消费 SourceBundle，不重建收入/产物链。

任何契约出现第二个 owner_repo 条目，即被定义为**禁止的第二策略源**，由 `tests/test_contract_registry.py`（revenue）和 receipt/closure validator（FC-103）机器拒绝。

## 后果

- **正**：契约字段只有一个 owner，跨仓冲突可机器检测；receipt validator 可拒绝伪 owner 与重复策略源；后续 FC-201~905 各阶段在已冻结的版本号上接线。
- **负**：本 ADR **不**意味着产品代码已完成接线 —— 当前生产链尚未使用 RootPolicy 2.x、normalized-only resolver、生产 SourceBundle 或 ActivationSnapshot；这些由后续阶段实现并在 Phase 15 独立验收。把所有权先冻结，是为了让后续实施有不变的契约靶心。
- **待办**：FC-103 落地后，本 ADR 与 `contract_registry.json` 的 hash 写入 triplet manifest（FC-104）；FC-201~905 按本表版本实施；任何破坏性 schema 变更必须新开 FC 并声明 N-1 窗口。

## 不变量保持

- 单一 owner：每个契约的 `owner_repo` 是单个 repo（company-wiki），不得为列表。
- 闭合集合：注册表只含这七个契约；新增第八个须新 FC 扩展 `MANDATORY_CONTRACTS`。
- 不删历史：本 ADR 不删除任何既有代码、assertion、artifact 或真实文件；所有权冻结是声明性的。
- 与 scope note 一致：本 ADR 不恢复投资研究 writer、估值链或跨仓写入；BOUNDARY-0 仍然有效。
