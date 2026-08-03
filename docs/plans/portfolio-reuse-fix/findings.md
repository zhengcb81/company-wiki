# 研究发现 — portfolio 复用根因与修复落点

> 关联根因文档：`C:\Users\郑曾波\projects\Research\kingsoft-cloud-revenue\ROOT_CAUSE_portfolio_reuse.md`
> 本文件记录为制定修复方案而做的代码核查事实。**行号会随代码漂移，实施前务必以实际代码为准。**

## 发现 1：portfolio 确实已配置并已扫描入库（用户原始意图已实现"一半"）

- `config/source_catalog.yaml` 列了三个 root：`company_raw`(companies/)、`dayu_portfolio`(dayu-agent/workspace/portfolio)、`dropbox_stock`(Dropbox/Stock)。
- catalog DB 实测三者都已扫描：company_raw 33,074 locations、**dayu_portfolio 3,591 locations**、dropbox_stock 9,899。
- 金山云 3896 的全部 7 份财报（含 FY2025 年报 `fil_cn_48ec0d41…pdf`）均在 catalog，`location_status=active`、`role=original_primary`，挂在 `dayu_portfolio` 根下。
- 含 `_docling.json`（已解析）、`.pdf.source.json`（溯源，带 HKEX 原 URL `https://www1.hkexnews.hk/.../2026042301428_c.pdf`、`pdf_sha256`、`filing_date`）。
- 结论：**扫描/检索层**已纳入；**规范复用层**没有。先前"未注册"的说法已更正为错误。

## 发现 2：复用断点在 resolver，且是有意设计

`src/company_wiki/source_catalog/resolver.py` 的 `SourceResolver.resolve()`（约 393-545 行）：
- 405-412 行：`company_raw_root_ids = {r.root_id for r in roots if r.kind=="company_raw"}`。
- 506-513 行：候选 document 的 canonical locations 必须有 ≥1 个 `root_id in company_raw_root_ids`，否则 `trace.append("no_canonical_company_raw_location")` 并 `continue`。
- 金山云 FY2025 唯一活动 location 在 dayu_portfolio → 命中该分支 → 不产出 handle → filing-fetch 报 `no_existing_source_satisfies_request` → 重下。
- 注释明说是有意为之（"filing-fetch rejects such handles"）。

## 发现 3：另一道闸在 filing-fetch handle 契约（companies/ 路径围栏）

- `filing-fetch/scripts/filing_contracts.py:131`、`SKILL.md:36`、`tests/test_fetch_filing.py:648`：handle 的 `canonical_path` 必须在 company-wiki `companies/` 子树内，否则拒绝。
- 即便 resolver 放行 portfolio 路径，filing-fetch 仍会拒收。两道闸共同锁死"不可复用"。

## 发现 4：规范写入只有一条受验证的入口 — `CanonicalSourceWriter.import_staged()`

`src/company_wiki/source_catalog/canonical_writer.py:136` `import_staged(request, candidate, receipt)`：
1. `_validate_staged`：校验 staged 文件在 `staging_root` 内、字节大小/sha256 与 receipt 一致。
2. `CatalogOperationLock(operation="canonical_import")` 加锁。
3. `_reactivate_if_retired`：若同 sha256 的 document 被 retired，重新激活。
4. `_existing_original(content_sha256)`：去重查找，**只查 `kind='company_raw'`**（274-289 行，与 resolver 同源逻辑）。
5. `_destination()`：算出 `companies/{entity}/raw/{subdir}/{filename}`（`_destination_subdirectory` 把 annual_report→financial_reports/annual 等）。
6. `_atomic_copy(staged, destination, receipt)`：原子拷贝。
7. `_write_provenance(destination+".source.json", ...)`：写不可变溯源 sidecar（337 行起；374 行有冲突保护）。
8. `scan_catalog(root_ids={company_root})`：重扫 company_raw。
9. 重新 `resolve` 并断言 `REUSED_EXACT`，否则报错。
- 输入必须是 `DownloadCandidate` + `DownloadReceipt`（来自 adapter 下载流）。`acquisition_service.ensure()`(76) → `import_staged`(138) 是现有 ensure→下载→入库链路。
- **关键复用点**：只要能把 portfolio 的 PDF 先"放进 staging_root"并合成一对 candidate/receipt，就能直接复用 `import_staged` 全部受验证逻辑。

## 发现 5：SourceHandle 能从 portfolio location 正常构造（只差放行）

`resolver.py:208` `SourceHandle`：含 `canonical_path`、`snapshot_sha256`、`https_url`、`capture_ready` 等。
`_handle` 构造（约 700-753 行）：从 location 的 `absolute_path` + `content_sha256` + metadata 里的 `source_url`（须 https）拼 handle；`capture_ready = not missing`。
→ portfolio location 的 absolute_path、content_sha256、source_url(HKEX https) 都齐全，理论上能造出 `capture_ready=True` 的 handle。**唯一拦路是发现 2 的 root-kind 过滤 + 发现 3 的路径围栏。**

## 发现 6：CLI 没有任何 portfolio→company_raw 桥接命令

source_catalog CLI 子命令：scan / normalize / summarize / fingerprint_backfill / derived_audit / status / focus_cleanup / documents(retire/restore) / identity_enrich / identify / query / evidence / extraction_quality / duplicates / resolve / ensure / run / worker。代码里 `promote` 命中均为 wiki proposal/gold review，与来源无关。**缺失"导入/提升"特性。**

## 发现 7：设计不变量（修复必须尊重）

- ADR-005 单一写者：company-wiki 只在 `companies/{entity}/raw/` 做规范、不可变写入。
- 不可变溯源 sidecar（`.source.json`）+ 字节级 sha256 + 路径围栏 = 篡改证据。
- portfolio 由 dayu-agent 拥有、可随时增删改 → 不能直接当规范来源（破坏不可变性假设）。

## 决策：推荐 Strategy A（导入/提升），B 作为可选

| | Strategy A：导入/提升（拷贝入 companies/） | Strategy B：只读复用（放宽两道闸） |
|---|---|---|
| 改动仓库 | **仅 company-wiki** | company-wiki(resolver) + filing-fetch(契约) |
| 磁盘 | 拷贝一份（可接受，财报 PDF 量级 MB） | 0 拷贝 |
| 不变量 | **全部保留**（文件落入 companies/，单一写者/路径围栏/不可变 sidecar 自然满足） | 需放宽路径围栏 + 处理 portfolio 增删改导致的陈旧 handle，**风险高** |
| 复用现有代码 | 直接复用 `import_staged` | 要改 resolver 过滤 + filing-fetch 契约 + 加陈旧检测 |
| 推荐 | ✅ 主方案 | ⏸ 仅当磁盘拷贝不可接受时再考虑 |

**推荐 Strategy A**：把 portfolio 的 PDF 经 staging_root 喂给 `import_staged`，文件最终落在 `companies/{entity}/raw/...` 并带不可变 `.source.json`（保留 HKEX 原 URL），resolver 自然返回 capture_ready handle，filing-fetch 复用——**filing-fetch 零改动**。

## 发现 8：Phase 1 spike 实测结果（2026-08-03，全部验证通过）

**验证链路**：portfolio PDF → staging → `import_staged()` → canonical 文件落 `companies/金山雲/raw/...` + 溯源 sidecar → resolve `REUSED_EXACT` → filing-fetch 只读复用 `capture_ready`（**零下载**）。

| 验证项 | 结果 |
|---|---|
| FY2025 提升 → resolve | ✅ `reused_exact`, capture_ready=True, canonical_path 在 companies/ 内 |
| FY2024 全新提升（走身份解析） | ✅ `imported_new` → `reused_exact`, capture_ready=True |
| filing-fetch 只读复用 FY2025 | ✅ capture_ready, missing_capture_fields=[] |
| filing-fetch 只读复用 FY2024 | ✅ capture_ready, missing_capture_fields=[] |
| 幂等（重复提升） | ✅ `deduplicated_after_download`，resolve 仍 PASS |

**Spike 暴露的三个 gap 与修复**（Phase 2 必须包含）：

1. **portfolio 丰富溯源在 `meta.json`，不在 `.pdf.source.json`**：`.pdf.source.json` 只是 88 字节的
   `{market, security_id, source_title}` 最小标记；`source_url`/`pdf_sha256`/`source_provider`/`source_id`/
   `filing_date`/`fiscal_year`/`form_type`/`source_language` 全在 `meta.json`。合成 candidate/receipt 必须读 `meta.json`。
2. **合并是"全有或全无"，且要求 sidecar 顶层带 `market`+`security_id` 才 prefer-new**（scanner.py:1045-1054）：
   dayu_meta 已含 source_url，故条件(a)不触发；`_write_provenance` 原本只写顶层 `security_id`、`market` 嵌在
   request/candidate 里 → 条件(b)不触发 → 新 acquisition 被丢弃。**修复（已改生产代码）**：
   `canonical_writer.py::_write_provenance` 增顶层 `"market": request.market`。改后 prefer_new 触发，
   acquisition 替换文档元数据，resolver 拿到 language/provider/pdid/source_url/security_id。
3. **security_id 词汇表归一化**：portfolio ticker=`"3896"`，身份解析规范形式=`"03896"`（带前导零），
   resolver 字符串比较 → conflict。**修复（原型已实现）**：提升路径先走 `SecurityIdentityResolver`
   （与 filing-fetch 同源），用规范 security_id 构建 request/sidecar。附带：security master 无
   `HKEX:1000180012`（03896 的 org 是 `6949`），Phase 15.4 丰富对该 doc 失效 → 提升自带身份即可，不依赖它。

**词汇表映射（dayu meta.json → resolver 期望键）**：
| dayu meta.json | resolver 期望 | 说明 |
|---|---|---|
| `source_language` | `language` | candidate.language 传递（已做） |
| `ticker`（"3896"） | `security_id`（"03896"） | 必须经身份解析归一化 |
| `company_id`（"3896_HKEX"） | `market` | 经身份解析得 `HK` |
| `source_provider`（hkexnews） | `provider` | 直接映射 |
| `source_id`（"12118317"） | `provider_document_id` | 直接映射 |
| `source_url` | `https_url` | 直接映射 |

**已落盘的原型**：`promote_prototype.py`（参数化 + 身份解析 + dry-run），即 Phase 2 正式 CLI 的实现内核。
**已改生产代码**：`canonical_writer.py::_write_provenance` 增顶层 `market`（最小、正确、向后兼容）。

## 待实施前需复核的假设（Phase 1 spike 已基本完成，剩余项）
- [ ] 手动把金山云 FY2025 PDF 拷进 `companies/金山云/raw/financial_reports/annual/` + 造 `.source.json` 后，`resolve` 是否返回 REUSED_EXACT？（验证"拷贝即生效"）
- [ ] SourceHandle 从 portfolio location 构造时 `https_url`/`snapshot_sha256` 是否齐全？（验证发现 5）
- [ ] 哪些测试硬断言"仅 company_raw 可复用"？需在 Phase 5 同步更新而非误删。
- [ ] `.source.json` 规范字段集（company_raw 版）vs portfolio `.source.json` 字段差异，决定合成 receipt 的字段映射。
