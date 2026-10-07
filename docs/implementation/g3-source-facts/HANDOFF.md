# G3-SOURCE-FACTS — 交接（HANDOFF）

**Lane**: `G3-SOURCE-FACTS` · **Card**: `docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g3_source_metadata_and_raw_space.md`
**Base**: `5930a644453ed46494c2c83c5ecfb97767fa9492` · **Branch**: `codex/g3-source-facts` · **Worktree**: `C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki`
**性质**：只读调查包。生产 0 写、raw 删除 0、无 apply/DELETE/UPDATE、无 receipt/authorization/token/expiry。

> MAIN 请先复核当前事实，再经**正式有限写入口**应用；不得直接执行本报告内容，也不要把本报告里的文件路径传给下游研究层。

---

## 1. 可直接应用的提案（`action=update_metadata`，3 项）

数据源：`metadata_proposals.json`（schema `g3-metadata-proposals/1`，观察时间 `2026-10-07T12:30:35Z`）。

| sample | 生产 ID（不换） | 建议变更 | 一手证据 |
|---|---|---|---|
| S05 | source/document `sha256:cd803fe9…3595b` | `document_kind: other → equity_offering_prospectus`；`source_type: other → prospectus`；`security_id: 三角防务 → 300775`；`published_date: null → 2022-11-30` | 封面标题+代码 300775；CNINFO `announcementId=1215243407`；security master |
| S06 | `sha256:c6ed5666…5ca0a1` | `document_kind: other → convertible_bond_prospectus`；`source_type: other → prospectus`；`security_id: 华锐精密 → 688059`；`published_date: null → 2022-06-22` | 封面标题+代码 688059；CNINFO `announcementId=1213777070`；security master |
| S07 | `sha256:221467c1…6466d7` | `security_id: 万润股份 → 002643`（`market=CN` 已正确） | 封面 证券代码 002643 + security master；`published_date` 保持 unknown，不提议 |

- 分类只用已发布 R1 正式融资族枚举（`equity_offering_prospectus` / `convertible_bond_prospectus`，`SourceType.PROSPECTUS` 族），不新造值。
- 身份只用现行规则（`backfill_v2._is_strong_security`：显示名=弱身份 → `unprovable`；官方快照 `.source_catalog/security_master/cn.json`）。
- **不换 `source_id`/`document_id`、不重下载**；建议通过既有 scanner/metadata 迁移入口（R2/R3 归口）执行，本卡不写生产。

## 2. 可直接消费的结构化建议（不含写操作）

| 产物 | 内容 |
|---|---|
| `metadata_proposals.json` | 9 项：`do_not_reactivate` ×4（S01–S04）、`update_metadata` ×3（S05–S07）、`unresolved` ×1（S08）、`register_new` ×1（S09）；另有 `problems`（4×`retired_without_restore_record`）、`conflicts`（1×`activity_date_vs_published_date`）、`unknowns`（6） |
| `raw_space_decision.json` | `decision=no_migration_recommended`；`registered_upper_bound_bytes=98845393`、`verified_distinct_copy_bytes=36191979`、`allocated_bytes=null`、`releasable_bytes=null`、`deleted_bytes=0` |
| `evidence_index.md` | 每样本字段级证据（url/locator/状态）、**S07 pathless SourceRef 建议**、**零模型 skip 候选（P09）+ 九样本缺口**、预算与 RAW-DUP 输入 sha |
| `findings.md` / `task_plan.md` / `progress.md` | 基线、方法、错误表、验证数字 |

### S07 pathless SourceRef（已登记才有 ID，SourceRef 本身不含路径）
`{schema_version:"2.0", document_id:"urn:company-wiki:document:sha256:221467c1…6466d7", source_id:"urn:company-wiki:source:sha256:221467c1…6466d7", content_sha256:"221467c1…6466d7", byte_size:153851, mime_type:"application/pdf"}` —— 由 `source_reader.SourceRef` 消费；不改 locations。

### 零模型 skip 候选（已存在，无需迁移）
`中微公司/raw/investor_relations/中微公司：投资者关系管理办法（2025年8月）.pdf`（`active`、sha `76e14698…b678`、167,252 B）→ `classify_document_kind` → `ir_policy` ∈ `_EMPTY_SKIP_KINDS` → `skipped_no_narrative`（无 `source.narrative_summarize` 模型任务）。
**九样本内无候选**（S07/S08 均为 `investor_relations`，不 skip）；不为凑样本把 S08 当无价值。

### S09 最小 ET 导入请求（不执行）
入口定位：`company-wiki-transcript-import` → `transcript_import_cli:main` → `run_import` → `transcript_import.import_transcript_tool_result(raw_result, request=SourceRequest(entity="Microsoft", document_kind="investor_call_transcript", market="US", security_id="MSFT", fiscal_year=2026, fiscal_period="Q4", language="en"), candidate=DownloadCandidate(...), writer=CanonicalSourceWriter(...), now=...)`；读取侧 `source_reader.lookup_transcript_import`（`source_query_cli`）。
最小载荷：TXT 66,324 B / `4ac3b4f0…7852a` / `text/plain`，`source_url` 用 header 自带 fool.com 链接，会议日 2026-07-29。
**结构性缺口**：同目录无任何 provider 回执/sidecar → `provider_receipt=legacy_unverified`，`DownloadReceipt` 无法从历史构造；由 MAIN 决定走正式 legacy 登记路径或重新授权获取（**不补写假回执、不翻译、不重抓**）。

## 3. 保持 unknown / conflict（不得转 ready）

| 项 | 状态 | 原因 |
|---|---|---|
| S07 `published_date` | unknown | CNINFO SZSE 公告通道 2026-05-15~2026-07-31（17 条）无该记录表；SZSE 官方 API 500，重试有界后停止 |
| S08 `published_date` | **conflict** | 登记 `2023-12-31` vs 原件活动 `2023-06-26/27/28`；一手公开日 unknown → `action=unresolved`（`security_id 002867` 的身份修复需先解冲突或经正式入口豁免） |
| S09 `provider_receipt` / `published_date` | legacy_unverified / unverified | 文件内自述（Scraped 2026-09-03）与 URL 路径日期均非一手回执 |
| S01–S04 | do_not_reactivate | 退休原因已知（`legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)` + 2026-08-07 reconcile），**无 restore/supersession 记录**；“文件仍在”≠“可复活”。恢复须走正式 restore 入口，并可附本卡已核的 source_url 与公开日（2026-03-31 / 2025-08-29 / 2026-04-28 / 2019-07-16） |
| company_raw `allocated_bytes`/`releasable_bytes` | null | Windows `allocation_size()` 返回 null；35/52 组未实读（`max_groups=20`、`max-detail-rows=100` 截断） |
| RAW-DUP `registered_*`/`protected_*`/`unknown_root` | whole_database 口径 | 全库诊断，非 company_raw 统计 |

## 4. 空间结论（成本收益）

- **`decision = no_migration_recommended`**：company_raw 内部注册逻辑上界 **98,845,393 B（94.3 MiB）** 已低于 256 MiB（268,435,456 B）收益阈值 → 即便 100% 实读也不可能达标；实读确认 **36,191,979 B**（占上界 36.6%）。
- allocation/释放均不可证（`null`），**`deleted_bytes=0`**；历史已清 5.66 GB 与原 46 G **不得**与本包相加。
- 覆盖：候选 52 组（注册）/ 21 组见于报告 / 17 组实读；5 组与 `dropbox_stock` 同 hash（列示者）只计内部多余副本；same-path 4 组不计。
- 若 MAIN 日后重开问题：重跑记录在 `raw_space_decision.json.actual_command` 的同一有界命令，并保持所有 `SourceRef`/`locations` 引用（**本卡不实施任何迁移**）。

## 5. 验证与只读边界

| 检查 | 结果 |
|---|---|
| `python -m pytest -q tools/g3_source_facts/tests` | **exit 0，55 passed，7.2 s** |
| 生产 `config/source_catalog.yaml` SHA256（前后） | `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`（不变） |
| 9 份原件 bytes/SHA vs `samples.json`（前后） | 全部一致 |
| 生产 DB | schema 1.2.0、sources 43,112、locations 46,606、documents 23,530、status active 25,048/missing 6/quarantined 1/retired 21,551；`PRAGMA query_only` 会话 `total_changes=0`；db 222,408,704 B、`-wal` 0 B、`-shm` 32,768 B |
| 8 样本 location/document 状态 | 与开工时一致（S01–S04 retired、S05–S08 active、S08 `published_date=2023-12-31` 未被改写） |
| 本卡写入生产 | **0**；与 MAIN/其他 lane 的并发边界：主工作树另有他人未提交改动（`config/source_acquisition.yaml` 等），本卡未触碰、未锁库 |
| 清理 | `.planning/g3-source-facts/scratch`（夹具、抽页、临时分析脚本、RAW-DUP 原始报告）**已整目录删除**；无 tmp/渲染副本残留；无原文 PDF/TXT/HTML 入库 |
| 提交范围 | 仅 `tools/g3_source_facts/**` 与 `docs/implementation/g3-source-facts/**`；不推 master、不合 master |

## 6. 外部效应

`public_http_requests=15`（CNINFO 13 + SZSE 2，累计 <100 KiB，单次 ≤12 KiB）、`downloads=0`（整份 PDF）、`read_bytes=236,198,380`（≤512 MiB）、`model_posts=0`、`production_writes=0`、`raw_deleted=0`。

> 读取合计口径：hash+封面抽页 75,886,072 B + Phase-5 复核重 hash 37,943,036 B + RAW-DUP verify 122,369,272 B = **236,198,380 B（225.2 MiB）**；RAW-DUP scan `read_bytes=0`；两轮 RAW-DUP 合计 122,369,272 B ≤ 268,435,456 B/轮。以 `handoff.json.external_effects.read_bytes` 为准。
