# 修复计划 — dayu portfolio "已索引但不可被 filing-fetch 复用"

> **2026-08-09 状态覆盖：`superseded_closed`。** Strategy A 的 Phase 0–6 历史实现/实验保留，但后续已回滚或由 Strategy B 取代。本文件所有未回填空框均不再是活动待办；Phase 7 不再 pending，已由 `portfolio-reuse-automatic` 的窄范围 Strategy B 和 FCAP r2 的通用多根方案取代。

> **状态：✅ 整体完成（2026-08-03，commit 7ce2774）**。Phase 0–6 全部 completed，Phase 7（Strategy B）默认跳过。
> 决策归档：`docs/adr/ADR-007-portfolio-promotion.md` + `docs/OPERATIONS.md §一点五`；最终结果见同目录 `progress.md`。
> 本目录原地保留作历史参考，不再作为活动任务。

## 2026-08-09 关闭处置

- [x] Phase 0–6 作为 Strategy A 的历史实现/实验记录关闭；其结果后来已回滚或被替代，不代表当前生产能力。
- [x] Phase 7 不再等待执行，已由后续 Strategy B 的窄范围实现及 FCAP r2 的通用多根方案取代。

- **目标**：让 `filing-fetch`（及 revenue-forecast / invest-* / industry-research）能复用已在
  `dayu-agent/workspace/portfolio` 中、且已被 catalog 索引的财报，**不再重复下载**；同时不破坏
  company-wiki 的单一写者 / 不可变溯源 / 路径围栏不变量。
- **根因**：见同目录 `findings.md` 与 `ROOT_CAUSE_portfolio_reuse.md`。portfolio 作为只读检索 root 已入库，
  但规范复用管线（`resolver.py` 的 `company_raw` 过滤 + `filing-fetch` 的 companies/ 路径围栏）刻意排除它，
  且无 portfolio→company_raw 桥接命令。
- **主仓库**：company-wiki（Strategy A 全部在此）。filing-fetch 在主方案下**零改动**。
- **状态图例**：`pending` → `in_progress` → `completed` / `blocked`。行号会漂移，动手前以实际代码为准。

---

## 选型决策（已定）

**采用 Strategy A（导入/提升）**：新增"把 portfolio 文档提升为 company_raw 规范来源"的能力——
经 staging_root 复用现有 `CanonicalSourceWriter.import_staged()`，文件最终落入
`companies/{entity}/raw/{kind}/...` 并写不可变 `.source.json`（保留原始 HKEX/SEC URL），
resolver 自然返回 capture_ready handle，filing-fetch 复用。

Strategy B（放宽 resolver + filing-fetch 契约做只读复用）记入 Phase 7，**默认不做**，仅在证明磁盘拷贝
不可接受时再评估。

理由：A 全部落在 company-wiki、完整保留不变量、最大化复用已验证代码、filing-fetch 不动；B 跨两仓、
要放宽路径围栏并处理 portfolio 增删改导致的陈旧 handle，风险显著更高。

---

## Phase 0 — 范围与不变量确认 — 状态：completed

- [x] 确认根因（resolver.py company_raw 过滤 + filing-fetch 路径围栏 + 无桥接命令）。
- [x] 确认主仓库 = company-wiki；主方案下 filing-fetch 不改动。
- [x] 确认必须尊重的不变量：ADR-005 单一写者、不可变 `.source.json` 溯源、字节 sha256、companies/ 路径围栏。

---

## Phase 1 — 实施前 Spike（验证关键假设） — 状态：completed ✅

> 结果：**全链路验证通过**——portfolio PDF → staging → `import_staged()` → canonical 文件落
> `companies/金山雲/raw/...` → resolve `REUSED_EXACT` → filing-fetch 只读复用 `capture_ready`（零下载）。
> 金山云 FY2025 + FY2024 两份 + 幂等性全部 PASS。详见 `findings.md` 发现 8。

### 1.1 任务（完成情况）
- [x] **S1 提升机制**：`spike_promote.py` 走真实 `import_staged`，文件落 `companies/金山雲/raw/financial_reports/annual/`。
- [x] **S2 resolve**：`reused_exact` + capture_ready=True + canonical_path 在 companies/ 内。
- [x] **S3 filing-fetch 端到端**：FY2025/FY2024 只读请求均返回 `capture_ready`、`missing_capture_fields=[]`、零下载。
- [x] **S4 字段映射**：丰富溯源在 portfolio `meta.json`（`.pdf.source.json` 仅 3 字段最小标记）；
      映射表落盘 `findings.md`（source_language→language、ticker→经身份解析→security_id 等）。
- [x] **S5 受影响测试盘点**：待 Phase 5 执行时补全清单（既有 company_raw 护栏测试保持不动）。

### 1.2 Spike 暴露的三个 gap 与修复
- [x] **G1**：sidecar 顶层缺 `market` → prefer-new 合并不触发 → **已改生产代码**
      `canonical_writer.py::_write_provenance` 增 `"market": request.market`。
- [x] **G2**：security_id 词汇表（portfolio "3896" vs 规范 "03896"）→ **原型已解决**：先 `SecurityIdentityResolver`
      归一化（`promote_prototype.py` 实现）。
- [x] **G3**：合成 candidate/receipt 必须读 `meta.json`（非 `.pdf.source.json`）。

### 1.3 产物
- `spike_promote.py`（首版 spike，FY2025 单条）、`spike_diag.py`（诊断）、
  `promote_prototype.py`（**Phase 2 实现内核**：参数化 + 身份解析 + dry-run，FY2024 全新导入 PASS）。

---

## Phase 2 — 实现 portfolio 提升能力（Strategy A 核心） — 状态：completed ✅

> **完成**：`src/company_wiki/source_catalog/portfolio_promoter.py`（T1-T6 正式模块）+
> `cli.py import-portfolio` 子命令（T7-T9）。真实环境验证：金山云 7 份财报 `--all` 提升，
> FY2022/2023/H1/Q1×2 为 `imported_new`，FY2024/2025 为 `deduplicated`；filing-fetch 只读复用
> FY2023/2024/2025 全部 `capture_ready` 零下载。`_write_provenance` 的 `market` 修复已在 Phase 1 落地。

### 2.1 正式模块（把原型搬进 source_catalog）
- [ ] **T1** 新建 `src/company_wiki/source_catalog/portfolio_promoter.py`：
      `promote_from_portfolio(catalog, identity, doc_id, ...)` —— 即 `promote_prototype.py` 主流程去 CLI 化；
      入参 = 已解析 identity（market/security_id/canonical_name）+ portfolio doc 定位。
- [ ] **T2** 解析 portfolio `meta.json`（注意：**非** `.pdf.source.json`）：absolute_path、content_sha256、
      byte_size、source_url(https)/source_provider/source_id/form_type/fiscal_year/fiscal_period/
      source_language/filing_date/first_ingested_at。
- [ ] **T3** 原子拷贝 portfolio PDF → staging_root（唯一临时文件名）。
- [ ] **T4** 合成 `DownloadCandidate` + `DownloadReceipt`（字段映射见 `findings.md` 发现 8 词汇表），
      通过 `_validate_staged` 全部校验。
- [ ] **T5** 调用 `CanonicalSourceWriter.import_staged()`（复用去重/destination/atomic_copy/sidecar/重扫/
      REUSED_EXACT 断言）。
- [ ] **T6** 身份解析：entity 定位走 `SecurityIdentityResolver`（与 filing-fetch 同源），
      用规范 security_id（如 `03896`）构建 request —— 这是 G2 的正式落地。

### 2.2 CLI 子命令
- [ ] **T7** `cli.py` 新增 `import-portfolio` 子命令：
      `--company-query`/`--market`/`--document-kind`/`--fiscal-year`（或 `--document-id`）、`--as-of-date`、
      `--dry-run`、`--all`。
- [ ] **T8** `--dry-run`：只解析+打印将提升的文档与目标 canonical_path，不写盘（原型已支持）。
- [ ] **T9** `--all`：遍历该 entity 在 dayu_portfolio 根下的全部 original_primary，逐个 promote（幂等）。

### 2.3 验证
- [ ] 单条：`import-portfolio --company-query 金山云 --market HK --document-kind annual_report --fiscal-year 2025`
      → `imported_new`（或 `deduplicated`），canonical_path 在 companies/ 内。
- [ ] 幂等：再跑 → `deduplicated_after_download`。
- [ ] `--all` 批量：金山云 portfolio 全部财报提升，resolve 全部 REUSED_EXACT。

---

## Phase 3 — 复用链路端到端验证 — 状态：completed ✅

> **完成**：金山云 FY2023/FY2024/FY2025 经 filing-fetch 只读请求全部返回 `capture_ready`、
> `missing_capture_fields=[]`、零下载（真实环境）。

### 3.1 任务
- [ ] **T10** 提升后 `resolve`（company-wiki CLI）金山云 FY2025 → `REUSED_EXACT`，handle 在 companies/ 内。
- [ ] **T11** filing-fetch 只读请求金山云 FY2025 → `capture_ready`，**零下载**。
- [ ] **T12** 用 revenue-forecast 据此 handle 构建 source/capture 记录（`company_wiki_source.py`），确认链路通。

### 3.2 验证
- [ ] 金山云、再挑一个 portfolio 已有的港股/美股 entity（如 neon-planet 提到的 MSFT）各跑一遍，
      均复用成功、零下载。

---

## Phase 4 — 去重 / 一致性 / 陈旧处理 — 状态：completed ✅

> **完成**：T13/T15 由 `import_staged._existing_original`（content-address + company_raw-only）保证，
> 幂等测试验证二次提升 `deduplicated_after_download` 且 canonical 目录仅 1 份 PDF；T14 语义文档化
> （提升=拷贝+独立溯源，非软链接，portfolio 源变动不影响 canonical 副本）。

### 4.1 任务
- [ ] **T13** 跨 entity 字节相同文档：`_existing_original` 已按 content_sha256 全局去重 → 验证不重复落盘。
- [ ] **T14** portfolio 源文件被 dayu-agent 删除/改动后的行为：提升后的 company_raw 副本**独立**（已是规范来源），
      不受 portfolio 变动影响——文档化此语义（提升=拷贝+独立溯源，非软链接）。
- [ ] **T15** 若已存在 company_raw 同 sha256（例如之前已下载）→ `import_staged` 走 `deduplicated_after_download`，
      不覆盖既有 canonical_path（验证不破坏既有来源）。

### 4.2 验证
- [ ] 上述三种情形各一个用例通过。

---

## Phase 5 — 测试 — 状态：completed ✅

> **完成**：`tests/contract/test_portfolio_promoter.py` 8 项（提升/幂等/dry-run/G1G2 元数据回归/
> 过滤/三个 fail-fast 全通过）；既有相关测试 53 项全绿（canonical_writer 6、resolver 13、acquisition 5、
> canonical_ingest 12、architecture_gate 3、dayu_adapter 4、identity_resolver 10）。
> 既有 `no_canonical_company_raw_location` fail-closed 语义未改动（resolver 过滤未动）。

### 5.1 新增
- [ ] **T16** `tests/source_catalog/test_portfolio_promotion.py`：
      - 合成 candidate/receipt 正确性（字段映射、sha256/size 一致）。
      - `promote_from_portfolio` → `import_staged` → canonical_path 在 companies/ + sidecar 字段。
      - 幂等（二次 = dedup）；跨 entity 字节相同去重。
      - `--dry-run` 不写盘；`--all` 批量。
- [ ] **T17** `tests/source_catalog/test_resolver.py` 增：提升后 portfolio-only 文档变为 REUSED_EXACT。
- [ ] **T18** 集成测试：`ensure`/`resolve` 在提升后返回 capture_ready，且不调用 adapter 下载（可 spy/桩 adapter）。

### 5.2 更新（避免误删既有护栏）
- [ ] **T19** 复核 S5 盘点的"仅 company_raw 可复用"测试：这些断言**仍然正确**（portfolio 未经提升时依旧不可复用），
      只新增"提升后可复用"的正面用例，**不改既有 fail-closed 语义**。
- [ ] **T20** filing-fetch `test_fetch_filing.py`（含 :648 路径围栏用例）：主方案下**不动**；仅在 Phase 7 才改。

### 5.3 验证
- [ ] `pytest tests/` 全绿；新增测试覆盖 T16-T18。

---

## Phase 6 — 文档与变更记录 — 状态：completed ✅

> **完成**：`docs/adr/ADR-007-portfolio-promotion.md`（T21）、`docs/OPERATIONS.md` 新增
> 「一点五、portfolio 提升为可复用来源（import-portfolio）」+ `filing-fetch/SKILL.md` 工作流与 Notes
> 补充提升前置说明（T22）、本计划三件套已更新（T24）。
> 注：company-wiki 无根级 CHANGELOG（有 log.md/audit_worklog），未新建（T23 以 OPERATIONS+ADR 覆盖）。

- [ ] **T21** 新增 ADR（如 `docs/adr/ADR-007-portfolio-promotion.md`）：记录决策——portfolio 为只读检索 root，
      提升是桥接；不放宽路径围栏/单一写者；Strategy B 不采纳的理由。
- [ ] **T22** 更新 `filing-fetch/SKILL.md` 与 company-wiki README/OPERATIONS：说明 portfolio 已索引、
      需复用时用 `import-portfolio` 提升一次（或批量），之后自动复用。
- [ ] **T23** CHANGELOG（company-wiki）记录新命令与语义。
- [ ] **T24** 在 `docs/plans/portfolio-reuse-fix/progress.md` 记最终结果。

---

## Phase 7 —（历史可选项）Strategy B 只读复用 — 状态：superseded（由后续 Strategy B 计划与 FCAP r2 接管）

> 仅当 Phase 1/2 证明磁盘拷贝成本不可接受时才启动。需跨 company-wiki + filing-fetch 两仓。

- [ ] **B1** `resolver.py`: 把 `company_raw_root_ids` 过滤改为"允许的复用 root kind 集合"（含 `dayu_portfolio`），
      受配置开关控制，默认关。
- [ ] **B2** `filing-fetch/scripts/filing_contracts.py`: 路径围栏放宽为"允许 company_raw root 或 dayu_portfolio root"，
      受同一开关控制。
- [ ] **B3** 陈旧性处理：portfolio 文件被删/改后，resolve 不能返回失效 handle（需 location 存在性复核 + 失效降级）。
- [ ] **B4** 更新两仓测试（含 test_fetch_filing.py:648）与 ADR。
- [ ] **风险**：放宽路径围栏削弱篡改证据；portfolio 可变性破坏"规范来源不可变"假设；blast radius 大。

---

## 文件变更清单（Strategy A，预期）

| 仓库 | 文件 | 变更 |
|---|---|---|
| company-wiki | `src/company_wiki/source_catalog/canonical_writer.py`（或新 `portfolio_promoter.py`） | 新增 `promote_from_portfolio`；`_write_provenance` 增可选来源字段 |
| company-wiki | `src/company_wiki/source_catalog/cli.py` | 新增 `import-portfolio` 子命令 |
| company-wiki | `tests/source_catalog/test_portfolio_promotion.py`（新） | T16 |
| company-wiki | `tests/source_catalog/test_resolver.py` | T17（增正面用例，不改既有） |
| company-wiki | `docs/adr/ADR-007-portfolio-promotion.md`（新） | T21 |
| company-wiki | `README.md` / `docs/OPERATIONS.md` | T22 |
| company-wiki | `CHANGELOG.md` | T23 |
| filing-fetch | （主方案无改动） | 仅 Phase 7 才动 |

## 风险与回滚
- **风险**：identity/metadata 缺失导致提升后非 REUSED_EXACT → 缓解：Phase 1 S4/S5 盘点 + 提升时补齐/identity_enrich。
- **风险**：批量 `--all` 误提升大量文件 → 缓解：`--dry-run` 先预览；默认非 `--all`。
- **回滚**：提升本质是 companies/ 下新增文件 + catalog 重扫；回滚 = 删除新增 canonical 文件 + sidecar + 重扫。
  不触及 portfolio 原文件，零破坏性。

## 整体验收标准
1. `import-portfolio` 单条/批量/幂等/dry-run 全部正确，单测集成测全绿。
2. 金山云 FY2025（及另一港股/美股 entity）经一次提升后，filing-fetch 只读复用、**零下载**。
3. 既有"仅 company_raw 可复用 / companies/ 路径围栏"护栏测试不被削弱。
4. ADR + 文档 + CHANGELOG 完成。
