# 改进计划 — portfolio 复用自动化（系统性修复，非手动驱动）

> **状态：✅ 整体完成（2026-08-06）**。方案已按用户决策定为 Strategy B（config-driven 只读复用，commit cb2305c）；
> Strategy A（ensure 自动提升）实现后弃用并回滚，Phase 0–6 全部 completed。
> 决策归档：`docs/adr/ADR-008-portfolio-auto-promotion.md` + `docs/OPERATIONS.md §一点五`；两项收尾候选
> （存量重扫 re-enrich、读连接 busy_timeout 5000→30000）已完成，见 `progress.md`。
> 本目录原地保留作历史参考，不再作为活动任务。

创建：2026-08-04 · 关联：`findings.md`（三层根因）、`progress.md`（进度）
前置：`../portfolio-reuse-fix/`（手动桥接，commit 7ce2774）——本计划将其**从手动升级为自动**，
并补齐锁健壮性。

## 目标

让 `filing-fetch`（及所有走 `ensure --allow-download` 的消费者：revenue-forecast / invest-* /
industry-research）在**触发下载前自动复用** `dayu-agent/workspace/portfolio` 中已索引的财报：
resolve 未命中 → **自动**查 portfolio → 命中则提升（`import_staged`）并返回 canonical source
（零下载）；未命中才走 adapter 下载。**无需任何手动步骤**，对 CN/HK/US 全部市场、全部
document_kind 一般性生效，且锁健壮、不变量全保留。

## 三层根因（见 findings.md，本计划逐一解决）

| # | 根因 | 本计划对策 |
|---|---|---|
| R1 | 已提交功能是"孤儿"手动命令，全系统无自动调用点 | **Phase 1**：自动提升集成进 `ensure`（acquisition service），所有消费者自动获益 |
| R2 | 手动调用被 worker 的 catalog 锁挡住（无 pause-around/重试） | **Phase 2**：锁健壮性——filing-fetch 路径免费受 `PausedWorkerScope` 保护；直接 ensure/import-portfolio 加 catalog_locked 重试（对齐 filing-fetch 退避模式） |
| R3 | "自动跳过"的端到端行为在架构上从未接线 | **Phase 1 + 6**：获取路径内建自动提升 + E2E 验证 |

## 设计决策（已定）

1. **集成点 = company-wiki 的 `ensure`（acquisition service）**，不是 filing-fetch。
   - 理由：company-wiki 拥有身份解析、目录、写入（单一写者）；ensure 是所有下载流量的唯一汇聚点；
     filing-fetch 保持零改动（延续 Strategy A 主仓库原则），下游 skill 全部自动获益。
2. **触发条件（严格）**：`resolve 返回 MISSING` **且** 请求显式 `--allow-download`。
   只读 `resolve` 永不提升（既有 fail-closed 语义不变）。
3. **匹配条件（一般性）**：身份 verified/active + `document_kind` + `fiscal_year`（如提供）+
   `published_date <= as_of_date`；从 portfolio `meta.json`（非 `.pdf.source.json`）读字段。
4. **提升复用 `import_staged`**：文件落 `companies/{entity}/raw/...` + 不可变 sidecar，
   保留 HKEX/SEC 原 URL；`_existing_original` 全局去重（幂等）。
5. **失败降级**：任何提升失败（缺元数据/导入错误/锁竞争）→ 记日志并**降级走 adapter 下载**，
   绝不阻塞下载（与 today 行为一致）。
6. **锁**：filing-fetch v1.4.0 的 `PausedWorkerScope` 已包裹 ensure → 自动提升免费受保护；
   直接 ensure CLI 与手动 import-portfolio 用 Phase 2 的通用锁重试。
7. **保留 import-portfolio CLI** 作为批处理/巡检工具（`--all`），但获取流程不再依赖它。

## Phase 0 — 前置核查 — 状态：completed

- [ ] 0.1 读 `acquisition_service.ensure()` 全流程：resolve MISSING 判定点、adapter 分发点、
      已有锁处理（是否已对 catalog_locked 重试）、`CanonicalImportResult` 各状态。
- [ ] 0.2 确认 resolver MISSING 语义：无 company_raw 匹配 → MISSING（允许下载）的确切返回结构。
- [ ] 0.3 盘点 portfolio `meta.json` 字段 → `DownloadCandidate/DownloadReceipt` 映射（复用
      portfolio-reuse-fix findings.md 发现 8 词汇表），确认 document_kind/fiscal_year 解析覆盖
      annual/semi_annual/quarterly。
- [ ] 0.4 记录基线：当前 ensure 对 6082（portfolio 有、company_raw 已有同 sha）与一个
      portfolio 有、company_raw 无的实体（如金山云 FY2022）的行为。
- [ ] 0.5 核查 acquisition config 是否已有开关机制（`source_acquisition.yaml`），规划
      `auto_promote_portfolio: true` 开关的落点。

## Phase 1 — 自动提升集成（核心） — 状态：completed

- [ ] 1.1 在 `acquisition_service.ensure()` 的 resolve-MISSING + allow_download 分支、
      adapter 分发**之前**插入 `_try_promote_portfolio(request, identity)`：
      - 查 `dayu_portfolio` root 下该 entity 的 portfolio 文档（`find_entity_doc_dirs`）；
      - 按 document_kind / fiscal_year / published_date≤as_of_date 过滤；
      - 精确匹配 ≥1 → 取第一个（按最新 filing_date）→ `promote_from_portfolio` → 返回
        `CanonicalImportResult`（imported_new / deduplicated_after_download）；
      - 成功 → **跳过 adapter**，把结果作为 ensure 的 resolution 返回；
      - 无匹配或失败 → 日志 + 降级走 adapter（today 行为）。
- [ ] 1.2 开关：`source_acquisition.yaml` 增 `auto_promote_portfolio`（默认 true），CLI/配置可关。
- [ ] 1.3 身份传递：复用 ensure 已解析的 identity（verified/active + 规范 security_id），
      不重复解析（G2 语义：portfolio "3896" → 规范 "03896" 已在 promoter 内处理）。
- [ ] 1.4 确认 ensure 返回契约不变：file-fetch 侧零改动即可消费自动提升结果
      （resolution schema / status 与下载路径一致）。

**验证**：`ensure --allow-download`（filing-fetch 调用）对"portfolio 有、company_raw 无"的实体
→ 自动提升 → capture_ready、**零 adapter 调用**（spy 桩验证）；对"两者都无"→ 走 adapter（today）。

## Phase 2 — 锁健壮性（一般性解决 R2） — 状态：completed

- [ ] 2.1 核查直接 ensure CLI 在锁竞争下的行为（是否已有 catalog_locked 重试）——
      若无，给 acquisition service 的 canonical_import 段加**指数退避重试**
      （对齐 filing-fetch `_run_company_wiki_json_retry`：5s、×2、deadline 内）。
- [ ] 2.2 `import-portfolio` CLI 同样获得锁重试（或包装成同一 helper）。
- [ ] 2.3 文档化：filing-fetch 路径由 `PausedWorkerScope` 保护，无需额外处理；
      直接 CLI 路径由 2.1/2.2 的退避保护。
- [ ] 2.4 （可选远期，记入 ADR）worker 按文档粒度锁 / 协作 yield——本期不做，注明理由
      （改动大、跨周期）。

**验证**：worker 跑批时直接调 `ensure --allow-download` 与 `import-portfolio` → 退避后成功，
不再 `CatalogOperationLockedError` 秒败。

## Phase 3 — 语义与护栏 — 状态：completed

- [ ] 3.1 只读 `resolve` 永不提升（resolver 过滤不动，fail-closed 语义不变）。
- [ ] 3.2 仅显式 `--allow-download` 触发自动提升（未授权请求绝不写 companies/）。
- [ ] 3.3 `published_date > as_of_date` 的 portfolio 文档**不**提升（信息集纪律）。
- [ ] 3.4 身份未 verified/active → 不提升。
- [ ] 3.5 幂等/去重：`_existing_original` 全局 content-address 去重；重复提升 =
      `deduplicated_after_download`，不覆盖既有 canonical。
- [ ] 3.6 审计：自动提升写一条日志（entity / doc / source_url / 结果），便于追溯。

**验证**：上述每种情形一个用例通过；既有"仅 company_raw 可复用"护栏测试不被削弱。

## Phase 4 — 测试 — 状态：completed

- [ ] 4.1 `tests/contract/test_source_catalog_auto_promote.py`（新）：
      - 提升成功（spy adapter 零调用）；无匹配 → adapter 被调；匹配但提升失败 → 降级 adapter；
      - 只读 resolve 不提升；未授权 ensure 不提升；as_of_date 过滤；幂等；
      - 身份未验证不提升；`auto_promote_portfolio: false` 开关关闭行为。
- [ ] 4.2 锁竞争：worker 占锁时直接 ensure/import-portfolio → 退避重试成功（mock 锁）。
- [ ] 4.3 回归：portfolio-reuse-fix 的 8 项 promoter 测试、resolver/acquisition/canonical_writer
      既有测试全绿。
- [ ] 4.4 filing-fetch 侧：契约测试零改动通过（filing-fetch 零改动原则）。

## Phase 5 — 文档 — 状态：completed

- [ ] 5.1 `docs/adr/ADR-008-portfolio-auto-promotion.md`（或更新 ADR-007）：记录自动提升决策、
      触发条件、降级语义、锁策略；注明 Strategy B（放宽 resolver）仍不采纳。
- [ ] 5.2 `docs/OPERATIONS.md` §一点五改写：从"手动 import-portfolio"升级为"自动复用（默认开启），
      手动命令仅用于批处理/巡检"。
- [ ] 5.3 `filing-fetch/SKILL.md` Notes：说明下载路径会自动复用 portfolio 已索引文件（零改动消费）。
- [ ] 5.4 本计划三件套更新（progress.md 记最终结果）。
- [ ] 5.5 若用户希望：把本计划与 portfolio-reuse-fix 的关键内容合并进主目录三份文档。

## Phase 6 — 端到端验证 — 状态：completed

- [ ] 6.1 挑一个"portfolio 有、company_raw 无"的实体（如金山云 FY2022 或新实体）：
      删/确认无 company_raw 副本 → filing-fetch `--allow-download` → **自动提升 + capture_ready +
      零下载**（对照 today：dayu 重下）。
- [ ] 6.2 6082：portfolio 与 company_raw 同 sha → 自动提升走 deduplicated，不写新文件。
- [ ] 6.3 直接 ensure CLI（不经 filing-fetch，worker 跑批中）→ 锁退避后成功。
- [ ] 6.4 回归：完整测试套件 + 既有 E2E（worker pause-around、并发、失败注入）全绿。

## 验收标准（全部满足）

- [ ] 无任何手动步骤：filing-fetch `--allow-download` 自动复用 portfolio 已索引文件，零下载。
- [ ] CN/HK/US 与全部 document_kind 一般性生效（同一代码路径，无 per-company 特判）。
- [ ] worker 跑批时直接 ensure/import-portfolio 不再秒败（退避重试）。
- [ ] 只读 resolve / 未授权请求 / as_of 之后 / 身份未验证 → 一律不提升。
- [ ] 提升失败降级 adapter，下载永不阻塞。
- [ ] 既有 fail-closed 护栏与全部测试不回归；ADR + 文档完成。

## 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 自动提升误匹配（meta 字段不全） | 提升错误文档 | 匹配严格（kind+year+as_of+身份）；失败降级 adapter |
| 自动提升成为隐藏下载替代 | 无（提升零网络） | 提升=本地拷贝+sidecar，无网络调用，天然比下载便宜 |
| 锁竞争仍失败（退避不够） | 直接 CLI 卡顿 | deadline 内退避；filing-fetch 路径已由 PausedWorkerScope 保护 |
| 提升的文档被 dayu 后续增删改 | canonical 副本独立 | 提升=拷贝+独立 sidecar（ADR-007 已文档化） |
| 用户不想自动提升 | 行为改变 | `auto_promote_portfolio: false` 开关 |

## 文件变更清单（预期）

| 仓库 | 文件 | 变更 |
|---|---|---|
| company-wiki | `src/company_wiki/source_catalog/acquisition_service.py` | `_try_promote_portfolio` 集成（核心） |
| company-wiki | `src/company_wiki/source_catalog/acquisition_config.py` | `auto_promote_portfolio` 开关 |
| company-wiki | `src/company_wiki/source_catalog/portfolio_promoter.py` | （可能小改：返回 CanonicalImportResult 适配） |
| company-wiki | `src/company_wiki/source_catalog/cli.py` | import-portfolio 锁重试（Phase 2.2） |
| company-wiki | `tests/contract/test_source_catalog_auto_promote.py`（新） | Phase 4 |
| company-wiki | `docs/adr/ADR-008-*.md` / `docs/OPERATIONS.md` | Phase 5 |
| filing-fetch | （零改动） | 仅 SKILL.md Notes 说明 |
