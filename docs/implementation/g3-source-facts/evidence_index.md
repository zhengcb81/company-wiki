# G3-SOURCE-FACTS — 证据索引（evidence_index）

观察时间（UTC）：`2026-10-07T12:30:35Z`（`metadata_proposals.json.observation_time`）。
公开网查询窗口：同一会话内 2026-10-07T12:0x–12:3xZ（CNINFO 13 次 + SZSE 2 次，单次响应 ≤12 KiB，累计 <100 KiB，**下载整份 PDF 0 次**）。
本文件不含本机绝对路径、不含原文 PDF/TXT、不含密钥；locator 只记页码/段落/元数据字段。

---

## 1. 每样本证据（字段 / 一手来源或原文定位 / 观察值 / 状态）

### S01 中微公司 2025年年度报告（retired）
| 字段 | url | locator | 观察值 | 状态 |
|---|---|---|---|---|
| content_sha256 | — | `loc:stream-sha256` | `d64c410832f2…fd3aa5` | verified（与登记一致） |
| published_date | `http://static.cninfo.com.cn/finalpage/2026-03-31/1225062431.PDF` | `cninfo:announcementId=1225062431` | 2026-03-31 | verified |
| security_id | `https://www.cninfo.com.cn/new/data/szse_stock.json` | `security_master:cn/688012` | 688012 | verified |
| source_url | 同 published_date | `cninfo:announcementId=1225062431` | 该公告 URL | verified |
| period_label | — | `cover:S01-p1` | 2025年年度报告 | verified |
| source_status | — | `catalog:document_retire_audit` | retired ×2（2026-08-01 F13、2026-08-07 reconcile） | verified |
| 官方体积对照 | — | `adjunctSize` | 8,952 KB vs 原件 9,165,875 B | verified |

### S02 中微公司 2025年半年度报告（retired）
published_date **2025-08-29**（`cninfo:announcementId=1224606011`，6,213 KB vs 6,361,468 B）；security_id 688012（`cover:S02-p1`）；retire 同 S01。

### S03 中微公司 2026年第一季度报告（retired）
published_date **2026-04-28**（`cninfo:announcementId=1225215453`，213 KB vs 217,264 B）；security_id 688012（`cover:S03-p1`，正文另含 2026Q1 数据）；retire 同 S01。

### S04 中微公司 招股说明书（retired）
published_date **2019-07-16**（`cninfo:announcementId=1206447929`，10,950 KB vs 11,211,796 B）；security_id 688012（security master）；retire 同 S01。

### S05 三角防务 增发募集说明书（注册稿）（active）
| 字段 | url | locator | 观察值 | 状态 |
|---|---|---|---|---|
| document_title | — | `cover:S05-p1` | 向特定对象发行股票并在创业板上市募集说明书（注册稿） | verified |
| security_id | — | `cover:S05-p1` | 300775 | verified |
| security_id | `https://www.cninfo.com.cn/new/data/szse_stock.json` | `security_master:cn/300775` | 300775 | verified |
| published_date | `http://static.cninfo.com.cn/finalpage/2022-11-30/1215243407.PDF` | `cninfo:announcementId=1215243407` | 2022-11-30 | verified |
| cover_date | — | `cover:S05-p1` | 2022-10（签署月，**不是公开日**） | verified |
| 官方体积对照 | — | `adjunctSize` | 5,465 KB vs 5,595,592 B | verified |

### S06 华锐精密 可转债募集说明书（active）
published_date **2022-06-22**（`cninfo:announcementId=1213777070`，4,646 KB vs 4,756,322 B）；security_id 688059（封面 + security master）；cover_date 2022-06；document_title `cover:S06-p1` = 向不特定对象发行可转换公司债券募集说明书 → R1 族 `convertible_bond_prospectus`。

### S07 万润股份 投资者关系活动记录表 20260515（active，有价值 IR）
| 字段 | url | locator | 观察值 | 状态 |
|---|---|---|---|---|
| security_id | — | `cover:S07-p1` | 002643 | verified |
| security_id | `https://www.cninfo.com.cn/new/data/szse_stock.json` | `security_master:cn/002643` | 002643 | verified |
| activity_date | — | `activity:2026-05-15` | 2026-05-15（15:00-16:30，山东辖区网上集体接待日） | verified |
| document_title | — | `cover:S07-p1` | 编号 20260515 | verified |
| published_date | — | `cninfo:hisAnnouncement/query?stock=002643&seDate=2026-05-15~2026-07-31`（17 条全览，无此记录表）；SZSE 官方 API 返回 500 后停止 | — | **unknown** |

### S08 周大生 投资者关系活动记录表 2023-06-26~28（active，冲突）
| 字段 | url | locator | 观察值 | 状态 |
|---|---|---|---|---|
| security_id | — | `cover:S08-p1` | 002867 | verified |
| security_id | `https://www.cninfo.com.cn/new/data/szse_stock.json` | `security_master:cn/002867` | 002867 | verified |
| activity_date | — | `activity:2023-06-26/2023-06-28` | 2023-06-26（另 06-27、06-28，电话会议） | verified |
| published_date（登记值） | — | `catalog:documents.published_date` | **2023-12-31** | unverified |
| published_date（一手） | — | `cninfo:hisAnnouncement/query?stock=002867&seDate=2023-06-25~2023-07-31` 无该记录表；SZSE API 500 后停止 | — | **unknown** |
| 冲突 | — | `activity_date_vs_published_date` | 活动窗口与登记公开日不相容 | **conflict**（保留，不转 ready） |

### S09 MSFT Q4 FY2026 电话会 TXT（未登记）
| 字段 | url | locator | 观察值 | 状态 |
|---|---|---|---|---|
| content_sha256 | — | `loc:stream-sha256` | `4ac3b4f0fa1be928…68d7852a` | verified |
| security_id | — | `txt:header` | MSFT | verified |
| fiscal_period | — | `txt:header` | Q4 2026 | verified |
| language | — | `txt:body` | en（英文正文 340 行） | verified |
| call_date | — | `txt:body` | Wednesday, July 29, 2026 at 5:30 p.m. ET → 2026-07-29 | verified |
| source_url | `https://www.fool.com/earnings/call-transcripts/2026/08/07/microsoft-msft-q4-2026-earnings-call-transcript/` | `txt:header:url` | 第三方抓取源 | unverified |
| published_date | — | `txt:header:url-path` | 2026-08-07（URL 路径日期，弱证据，**不提议**） | unverified |
| provider_receipt | — | `txt:header:Scraped=2026-09-03T22:44:45.464617` | 文件内自述，无独立回执/sidecar | **legacy_unverified** |

---

## 2. 可应用的 pathless 生产 SourceRef 建议（S07，已登记才有 ID）

按 `source_reader.SourceRef`（schema `2.0`）字段，全部取自生产只读事实 + 已核原件字节：

```json
{
  "schema_version": "2.0",
  "document_id": "urn:company-wiki:document:sha256:221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7",
  "source_id": "urn:company-wiki:source:sha256:221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7",
  "content_sha256": "221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7",
  "byte_size": 153851,
  "mime_type": "application/pdf"
}
```

- 路径无关：SourceRef 不含 location/path；同一 source 的 locations（company_raw 下 1 处）保持不变。
- 前置 metadata 提案：`security_id 万润股份 → 002643`（`action=update_metadata`）；`published_date` 仍 unknown，**不阻塞** SourceRef（SourceRef 不含日期）。
- S09 因未登记**不能**出 SourceRef（source_id/document_id 为 null），只能给 register_new + 下方最小请求。

## 3. 零模型 skip 候选与九样本缺口

- **已有候选（不在九样本内，无需下载）**：`中微公司/raw/investor_relations/中微公司：投资者关系管理办法（2025年8月）.pdf`
  - 生产事实：location `active`、document `active`、`source_id=urn:company-wiki:source:sha256:76e146985388c926f2683e24af47e6a1ab0ce8a156864fb16e7df9a2cc99b678`、167,252 B、`application/pdf`。
  - 现有零模型路径：`classify_document_kind("…投资者关系管理办法…") → ir_policy` ∈ `narrative_routing._EMPTY_SKIP_KINDS` → `empty_result_may_skip` → `skipped_no_narrative`，不产生 `source.narrative_summarize` 模型任务。
  - **不需要任何 metadata 迁移**（路由按标题现算），可直接作为纯流程零模型 skip 候选。
- **九样本缺口**：S01–S09 中没有一份命中 `ir_policy`/`meeting_notice`（S07/S08 都是 `investor_relations`，不 skip）。九样本内**没有**零模型 skip 候选；不把 S08（含事实问答）当作无价值来凑数。

## 4. 原文/网络/预算记账

| 类别 | 数值 |
|---|---|
| 原文读取（hash 9 份 + 封面/头部抽页） | 75,886,072 B / 536,870,912 B（72.4 MiB），`status=complete` |
| RAW-DUP scan | `read_bytes=0`，49.457 s |
| RAW-DUP verify | `read_bytes=122,369,272`（40 文件），60.011 s，`status=succeeded` |
| 本卡合计实读 | 198,255,344 B ≈ 189.1 MiB ≤ 512 MiB；两轮 RAW-DUP 合计 122,369,272 B ≤ 268,435,456 B/轮 |
| 公开网 | 15 次请求、累计 <100 KiB、下载 PDF 0 次、LLM 0、付费 0 |
| 模型调用 | `model_posts=0`；生产写 `production_writes=0`；raw 删除 `raw_deleted=0` |

## 5. company_raw 空间证据（RAW-DUP 复用，未改工具）

调查配置（自身 scratch，已记录 SHA）：
`investigation_source_catalog.yaml` sha256=`a77b9e0bbf396c4fbf1785522009695e7ec205442d5d0a779a849bac80f02bca`
— 只含 `company_raw` 根，`catalog_dir` 绝对定位生产 `.source_catalog`，**不是生产配置更新**。

| 输入 | sha256 | 关键事实 |
|---|---|---|
| `rawdup_scan_report.json` | `b828f3cb96189fdaadea33edf5ad2c3ce282bb73e1809576b3e5e98484498b1f` | `status=succeeded`，`scan_scope.roots=[company_raw]`，`read_bytes=0`，`candidate_groups=3531`（全配置口径），`limits_hit=[detail_rows]` |
| `rawdup_verify_report.json` | `9fdcd53e44aa5000f92cdbd9c4bc98c88adddc0e96dec3b975b25e72bfe360ce` | `status=succeeded`，`read_bytes=122,369,272`，`verified_groups=17`，`physical_allocated_bytes=null`，`deleted_bytes=0`，`limits_hit=[max_groups,detail_rows]`，`truncated.dropped_groups_by_row_cap=3505` |
| `metadata_bound.json`（只读 SQL 聚合，0 文件读） | `e4987f2648e8af8ab95a52b9856d454ba28ccd77fa92e55c8f476ec697f92859` | company_raw 内部 ≥2 副本的 content hash **52 组**，注册逻辑上界 **98,845,393 B**；其中与外根同 hash 的 17 组 / 54,827,575 B（只计内部多余副本，不把跨根副本算节省） |

分类与读取结果（只统计 `root_id=company_raw` 全成员组）：
- 候选（注册）52 组 / 上界 98,845,393 B；报告列出的内部 distinct 组 21（`max-detail-rows=100` 截断，`dropped_groups_by_row_cap=3505`）
- 已实读并 digest 一致：17 组 → **verified 36,191,979 B**（占上界 36.6%）
- 未读（`max_groups=20` 截断）：35 组 → 保持 unknown，不计 verified
- same-path 4 组（列出者）、mixed with `dropbox_stock` 5 组（列出者）→ **不计内部多副本**
- `allocated_bytes=null`、`releasable_bytes=null`（Windows `allocation_size()` 返回 null）、**`deleted_bytes=0`**

## 6. 未知 / 冲突登记（不得转 ready）

1. S07 `published_date=unknown`（一手公告通道查无记录表；SZSE API 失败已停）。
2. S08 `published_date` 登记 2023-12-31 vs 活动 2023-06-26~28 → **conflict**；一手公开日 unknown。
3. S09 `provider_receipt=legacy_unverified`；`published_date` 仅 URL 路径弱证据 → unverified、不提议。
4. S01–S04 `retired_without_restore_record`：文件尚在 ≠ 可复活；恢复需正式 restore 入口。
5. company_raw `allocated_bytes/releasable_bytes` unknown（平台不可证）；35 组未实读。
6. RAW-DUP 全库诊断（`registered_sources=43112`、`registered_bytes=35,110,881,225`、`unknown_root`/`protected_*`）为 **whole_database** 口径，不是 company_raw 统计。
