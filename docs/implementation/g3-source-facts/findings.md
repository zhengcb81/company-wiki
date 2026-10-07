# G3-SOURCE-FACTS — 调查发现（findings）

> 只读调查；所有原文读取均记账到本卡 512 MiB 预算。生产 0 写。

## 1. 基线与边界

| 项 | 值 |
|---|---|
| CWP 基线 master | `5930a644453ed46494c2c83c5ecfb97767fa9492` |
| 本卡 worktree | `C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki`，分支 `codex/g3-source-facts` |
| 生产 `config/source_catalog.yaml` SHA256 | `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`（运行前后需复核） |
| 目录配置 | `catalog_dir: ${PROJECT_ROOT}/.source_catalog`；roots=company_raw/dayu_portfolio/dropbox_stock/future_lake |
| 生产 DB | `.source_catalog/catalog.sqlite3`（222,408,704 B，schema `1.2.0`，`-wal` 0 B，`-shm` 32,768 B） |
| DB 打开方式 | `file:...?mode=ro` + `PRAGMA query_only=ON`，单读事务，`total_changes=0` |
| 主 CWP 工作树状态 | 另一 lane 有未提交改动（`config/source_acquisition.yaml`、`src/.../acquisition*.py`、`close_gap.py`、`tests/contract/test_single_intent_latest_acquisition.py`）——与本卡无关，本卡未触碰 |

## 2. 九样本原文事实（stream hash + 封面抽页）

预算记账：hash 一遍 + 封面/头部抽页一遍 = **75,886,072 B（72.4 MiB）/ 512 MiB**，`status=complete`。
九份 `content_sha256`、`byte_size` 与冻结 `samples.json` **全部一致**（含 S09 TXT 66,324 B）。

| sample | 原件（live 根） | bytes | SHA vs 登记 | 封面/正文关键事实 |
|---|---|---|---|---|
| S01 | 中微公司 2025年年度报告.pdf | 9,165,875 | ✅ | 封面仅标题，259 页 |
| S02 | 中微公司 2025年半年度报告.pdf | 6,361,468 | ✅ | 公司代码 688012 / 简称中微公司 |
| S03 | 中微公司 2026年第一季度报告.pdf | 217,264 | ✅ | 证券代码 688012；正文含 2026Q1 数据 |
| S04 | 中微公司 招股说明书.pdf | 11,211,796 | ✅ | 科创板 IPO 招股说明书，429 页，封面无日期 |
| S05 | 三角防务 增发募集说明书（注册稿）.PDF | 5,595,592 | ✅ | **股票代码 300775**、债券代码 123114；封面“二〇二二年十月”（签署月，非公开日） |
| S06 | 华锐精密 可转债募集说明书.PDF | 4,756,322 | ✅ | **股票代码 688059**；封面“二〇二二年六月” |
| S07 | 万润股份 IR活动记录表20260515.pdf | 153,851 | ✅ | **证券代码 002643**、编号 20260515；活动 2026-05-15 15:00-16:30（山东辖区网上集体接待日） |
| S08 | 周大生 IR活动记录表2023-06-26~28.pdf | 414,544 | ✅ | **代码 002867**、编号 2023-022；时间 2023-06-26/27/28（电话会议） |
| S09 | MSFT_Q4_2026_earnings_call.txt | 66,324 | ✅ | Ticker MSFT、Quarter Q4 2026、Source motley_fool、URL `fool.com/earnings/call-transcripts/2026/08/07/...`、Scraped 2026-09-03、正文“Wednesday, July 29, 2026 at 5:30 p.m. ET”、英文正文、340 行 |

## 3. 生产目录事实（只读，来自 `.source_catalog/catalog.sqlite3`）

- 8 份 company_raw 样本**全部已登记**（location→source→document 三层齐全，`content_sha256` 与原件一致）；S09（earnings_transcripts 根）**未登记**——目录 roots 中不存在 ET 根。
- `location_status`：S01–S04 = `retired`，S05–S08 = `active`；`source_status` 同步。
- **retired 追溯（S01–S04）**：每份各有 2 条 `document_retire_audit`，无 `document_restore_audit`：
  1. `legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)` — `phase-15.6-governance`，2026-08-01
  2. `phase-15.6 audit reconciliation (reconcile-retire)` — `reconcile-retire-20260806`，2026-08-07
  → 定性：**旧派生退休（治理批处理）**，不是真正撤回/被替代；文件仍在盘上、digest 与登记一致、无 supersession/restore 记录。“文件尚在”≠“可复活”，本卡不提 active 恢复。
- **retired 原因不是 unknown**：都有正式 reason 文本，因此 S01–S04 动作为 `do_not_reactivate`（缺 restore 记录），`retired_reason` 原样带出。
- `documents.published_date` 现状：S01–S07 = `NULL`；**S08 = `2023-12-31`**（与活动日 2023-06-26~28 冲突）。
- `documents.metadata_json.acquisition.security_id` 现状：S01–S04 = `688012`（强）；**S05 三角防务 / S06 华锐精密 / S07 万润股份 / S08 周大生 = 证券中文名（弱身份）**。`market=CN` 均已写。
- `document_kind` 现状：S01 `annual_report`、S02 `semi_annual_report`、S03 `quarterly_report`、S04 `prospectus`、**S05/S06 `other`**、S07/S08 `investor_relations`。
- 全库快照：`sources` 43,112；`locations` 按根 company_raw 33,092 / dayu_portfolio 3,660 / dropbox_stock 9,853 / future_lake 1（=46,606，其中 1 条 `source_id IS NULL` 不入 RAW-DUP 统计）。

## 4. 一手公开来源核到的公开日（CNINFO，只读查询，0 PDF 下载）

查询入口：`http://www.cninfo.com.cn/new/fulltextSearch/full`（GET）与 `http://www.cninfo.com.cn/new/hisAnnouncement/query`（只读检索）。公开日取 `adjunctUrl` 路径日期（= announcementTime 的北京时间日期，两者在全部 6 条一致）。单次响应 ≤12 KB，累计网络响应 **<100 KB**，下载整份 PDF **0 次**。

| sample | 官方标题（cninfo） | 公开日 | announcementId | adjunctUrl | 官方 KB vs 本卡原件 |
|---|---|---|---|---|---|
| S01 | 中微公司：2025年年度报告 | **2026-03-31** | 1225062431 | finalpage/2026-03-31/1225062431.PDF | 8,952 KB vs 9,165,875 B ✅ |
| S02 | 中微公司：2025年半年度报告 | **2025-08-29** | 1224606011 | finalpage/2025-08-29/1224606011.PDF | 6,213 KB vs 6,361,468 B ✅ |
| S03 | 中微公司：2026年第一季度报告 | **2026-04-28** | 1225215453 | finalpage/2026-04-28/1225215453.PDF | 213 KB vs 217,264 B ✅ |
| S04 | 中微公司：首次公开发行股票并在科创板上市招股说明书 | **2019-07-16** | 1206447929 | finalpage/2019-07-16/1206447929.PDF | 10,950 KB vs 11,211,796 B ✅ |
| S05 | 三角防务：…向特定对象发行股票并在创业板上市募集说明书（注册稿） | **2022-11-30** | 1215243407 | finalpage/2022-11-30/1215243407.PDF | 5,465 KB vs 5,595,592 B ✅ |
| S06 | 华锐精密：向不特定对象发行可转换公司债券证券募集说明书 | **2022-06-22** | 1213777070 | finalpage/2022-06-22/1213777070.PDF | 4,646 KB vs 4,756,322 B ✅ |
| S07 | — | **unknown** | — | — | CNINFO SZSE 公告通道 2026-05-15~2026-07-31 共 17 条，无该记录表；SZSE 官方 API 500 |
| S08 | — | **unknown** | — | — | CNINFO SZSE 2023-06-25~2023-07-31 无该记录表；SZSE 官方 API 500 |

日期语义（本卡明确区分）：**公开日**（official announcement，上表）≠ **活动日**（S07 2026-05-15、S08 2023-06-26~28，来自原件正文）≠ **封面/签署日期**（S05 2022-10、S06 2022-06，来自封面）≠ **下载日/mtime**（S05 mtime≈2022-12、S08 mtime≈2026-05，不作证据）。

## 5. 身份规则与正式枚举（来自仓内现行实现，不新造）

- 强身份：`backfill_v2._is_strong_security` —— ticker 形（ASCII、alnum、含数字、≤10、且不等于公司中文名）；显示名 security_id 落 `unprovable`。`evidence_hint_only`（仅文件名/标题）永远不能 capture-ready。
- 本卡用的官方身份快照：`.source_catalog/security_master/cn.json`（`source_name=cninfo`，`source_url=https://www.cninfo.com.cn/new/data/szse_stock.json`，record_count 6137）：中微公司→688012、三角防务→300775、华锐精密→688059、万润股份→002643、周大生→002867，market=CN。
- R1 正式融资族枚举（不造新值）：`document_kind ∈ {equity_offering_prospectus, convertible_bond_prospectus}`，`source_type=prospectus`（`scanner.py:139-140`；`tests/integration/test_financing_scanner_cli.py` 已把 S05/S06 映射到这两个值）。
- 身份与分类建议只改 `metadata_json.acquisition.security_id` / `document_kind` / `source_type`，**不换 source_id/document_id、不重下载**。

## 6. S09 电话会登记事实

- 未登记：`locations/sources/documents` 均无该 TXT；catalog roots 无 `earnings_transcripts` 根。
- 正文头部（原件自带，original_document 证据）：Ticker `MSFT`、Quarter `Q4 2026`、Source `motley_fool`、URL `https://www.fool.com/earnings/call-transcripts/2026/08/07/microsoft-msft-q4-2026-earnings-call-transcript/`、`Scraped: 2026-09-03T22:44:45.464617`、会议时间 `Wednesday, July 29, 2026 at 5:30 p.m. ET`、语言 en（英文正文，340 行）。
- 同目录只有 `MSFT_Q4_2026_{earnings_call.txt,bilingual.json,interleaved.txt}`，**没有任何 provider 回执/`.source.json`/sidecar** → 下载回执保持 `legacy_unverified`，不补写假历史回执；不因存在译文文件而拒绝登记，也不在本卡执行导入/翻译。
- `published_date` 不提议（fool.com URL 路径日期 2026-08-07 属弱证据，非一手公开记录）；会议日期 `call_date=2026-07-29` 作为 original_document 证据单列。

## 7. 零模型 skip 候选与缺口

- 现行零模型 skip 只认 `narrative_routing._EMPTY_SKIP_KINDS = {ir_policy, meeting_notice}`（`empty_result_may_skip` → `skipped_no_narrative` → 无 `source.narrative_summarize` 模型任务）。
- 九样本中**没有**一份落到这两个 kind（S07/S08 都被标题规则归为 `investor_relations`，不 skip）→ **九样本内零模型 skip 候选缺口**，不把 S08 这类带事实问答的业务文档误判为无价值。
- 仓内已有合格候选（不在九样本内，不需下载）：`中微公司/raw/investor_relations/中微公司：投资者关系管理办法（2025年8月）.pdf` —— 已登记 `active`、sha `76e146985388…`、167,252 B；标题命中 `投资者关系管理办法` → `classify_document_kind` 返回 `ir_policy` ∈ `_EMPTY_SKIP_KINDS`，现有路由即可零模型 skip，**不需要任何 metadata 迁移**。

## 8. RAW-DUP 工具事实（供 Phase 4 使用）

- CLI 参数：`scan|verify --config --output [--local-output] [--project-root] [--max-groups 100] [--max-read-bytes 536870912] [--deadline-seconds 300] [--max-detail-rows 5000] [--max-similar-groups 100] [--location-status all|active] [--hash-catalog] [--overwrite] [--quiet]`；无 `--root-id` 过滤。
- 配置 key 封闭（`schema_version/catalog_dir/roots/reusable_root_kinds`），root key 封闭；**过滤只能靠“配置里只写 company_raw”**；`catalog_dir` 用 `${PROJECT_ROOT}` 展开 → 需绝对定位到 live `.source_catalog`。
- 分类枚举：`same_path_references / shared_physical_file / distinct_physical_copies / uncertain_physical_identity / similar_size_different_content / unresolved`；路径态 `unknown_root/root_missing/outside_configured_root/missing/acl_denied/not_a_file/reparse_point`；验证态 `verified/verified_identical/not_attempted/metadata_sha_mismatch/changed/acl_denied/missing/open_error/skipped_cloud_placeholder/unread_path/...`。
- `registered_*`、`protected_*`、`roots[]`、`unknown_root` 诊断**恒为全库口径**（`registered_totals(reader)` 无 WHERE 过滤）→ 必须标 `whole_database`，不当 company_raw 统计。
- `physical_allocated_bytes` 在当前代码 Windows 下返回 `None`（`core.allocation_size`）→ `allocated_bytes/releasable_bytes` 预期 `null`；`deleted_bytes` 恒 0。
- 报告 Git 输出已无本机绝对路径（config/database 相对化、locator 只有 relative_path）；机器绝对路径只进 `--local-output`。

## 9. 网络与读取记账

- 公开网请求：CNINFO fulltext/hisAnnouncement 检索 13 次 + SZSE API 2 次（均 500，已停止重试）+ 无其他；单次响应最大 12 KB，累计 **<100 KiB**（上限 50 MiB）；**下载整份 PDF 0 次**；无 LLM、无付费、无密钥。
- 原文读取：75,886,072 B / 536,870,912 B（hash 36.19 MiB + 封面抽页 36.19 MiB）；剩余供 RAW-DUP 两轮的上限 = min(剩余, 268,435,456)。
- 本卡未写：生产 companies、生产 SQLite/sidecar/ET、仓内 `config/**`、src、RAW-DUP 工具、总 PWF。
