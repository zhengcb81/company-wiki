# G-CWP-01 交接：CWP 全文种逻辑资料公共 browse（owner 交付）

- 交付日期：2026-10-27
- 承包 harness：ZCode 外部会话（EX-CWP-01）
- 状态：**COMPLETE（待 D00 验收）**——本包范围要求全部实现，独立审查发现 F-01..F-04 已全部修复并复审关闭（复审报告见同目录 `review-report.md`，绑定最终候选 commit）。

## 1. 绝对位置与提交

| 项 | 值 |
|---|---|
| worktree（绝对） | `C:/Users/郑曾波/Projects/dashboard-owner-cwp` |
| 分支 | `codex/dashboard-cwp-public-browser`（未合并、未 push owner main） |
| base commit | `0c988e8d70e22a436126e6ae31ad4fa8172a4222`（owner master HEAD @ 2026-10-27；卡内 D03 只读基线 `65f42d41` 是其祖先，已按协议重核为当前稳定基线） |
| 实现 commit | `7ef04c9c06cd2bc7c532ec18ba0dde92dad0318a` |
| 返修 commit | `214c53796bd7f8e2c8fa0542f3ea713adebaf78d`（审查 F-01..F-04） |
| 最终候选 | `214c5379`（后续提交仅含本 handoff/审查报告，无产品影响） |

owner 主工作区在途文件（PDF-C3/摘要/loop PWF 等）未触碰；本包与在途文件零重叠（仅新增 3 个文件）。worktree 内 `.githooks/pre-push` 有 Windows 文件模式（755→644）环境性变化，**未入库**。

## 2. 交付文件（全部新增）

| 文件 | 内容 |
|---|---|
| `src/company_wiki/source_catalog/public_document_browser.py` | 核心模块：`PublicDocumentBrowser.browse()`、`reopen_document_version()`、`document_version_id()`；零写（仅 `catalog.reader` 只读连接） |
| `src/company_wiki/source_catalog/public_document_browser_cli.py` | 传输 CLI：stdin JSON → stdout 单行 JSON；错误信封 stderr + exit 2 |
| `tests/contract/test_public_document_browser.py` | 15 项 focused contract 测试 |

未改任何既有文件（`git show --stat` 佐证）；未注册 console-script（避免动 pyproject），调用方式 `python -m company_wiki.source_catalog.public_document_browser_cli`。

## 3. 公共 schema 与调用样例

### 3.1 browse 请求（stdin，字段精确集，拒绝重复 JSON key，≤64KiB）

```json
{"schema_version":"company-wiki-public-document-browse-request/1",
 "canonical_entity_id":"ent-acme",
 "market":null,"document_kinds":null,"fiscal_years":null,
 "language":null,"source_statuses":null,
 "limit":50,"cursor":null,"snapshot_id":null}
```

- `canonical_entity_id` 必填（null/空 → blocked `invalid_canonical_entity_id`）。匹配双通道：`document_entities.entity_id`（扫描器派生，如 `ticker:ACME`/`company-name:…`）或声明的 `canonical_entity_id` 捕获字段（`$.acquisition.*`/`$.dayu_meta.*`）。
- 过滤器全部可选；列表在 seam 排序（集合语义，重放与顺序无关）；空列表=不过滤。`limit`∈[1,500] 默认 50。
- `snapshot_id`/`cursor` 为不透明 base64url token；翻页用 `page.next_cursor`；固定快照重放传 `snapshot_id`（过滤器须与 pinned 一致或省略）。

### 3.2 browse 响应（stdout 单行紧凑 JSON）

```
{schema_version:"company-wiki-public-document-browse/1",
 state:"available|empty|partial|stale",
 reason_codes:[...],        // entity_not_indexed / no_documents_match_filters /
                            // some_versions_not_resolvable / snapshot_stale+
                            // catalog_revision_changed / page_offset_beyond_total
 canonical_entity:{requested_key, canonical_entity_id, display_name, market},
 items:[DocumentVersionItem...],
 page:{next_cursor, snapshot_id, total, total_status:"exact"},
 facets:{document_kind,language,source_status,market,fiscal_year},  // 只统计过滤后快照
 catalog_revision:"<sha256 hex>"}    // 实体域投影内容寻址摘要；内容不变则不变（迁根不变）
```

`DocumentVersionItem`（pathless）：`document_version_id`（`cwpdv1-`+43 字符，sha256(document_id+source_id+content_sha256)，同 triple 恒等、异 source/hash 必异）、`document_id`、`title`、`document_kind`、`published_at`、`period_start/period_end`、`fiscal_year`、`language`、`market`、`version_label`（组内序号）、`is_current_version`、`processing_state`（documents.source_status）、`location_roles`、`first_seen_at`、`storage_state`（`resolvable|not_resolvable`，按当前 config 根可解析性）、`source_ref`（完整六字段 v2：document_id/source_id/content_sha256/byte_size/mime_type/schema_version="2.0"）。

版本集合 = locations 中 role∈{original_primary, original_attachment, indexed_only} 的 source ∪ primary_source_id（sidecar/derived 的 `metadata`/`processed_docling` 角色排除）。

### 3.3 reopen 请求/响应

```json
{"schema_version":"company-wiki-public-document-version-request/1",
 "document_version_id":"cwpdv1-AbC…"}
```
→ `state:"available"` + `document`（与 browse item 逐字节同构）；未知 ID → `state:"not_found"`（exit 0）；畸形 ID → blocked exit 2。重开为有界无 spill 全表扫描（实测 23k docs / ~10 万 locations 约 2.7s），无注册表、零写。

### 3.4 CLI 命令行

```
python -m company_wiki.source_catalog.public_document_browser_cli --config <path> < request.json
```
退出码：0=成功（含 empty/partial/stale/not_found）；2=blocked（非法请求/token）或 unavailable（catalog 不可开/配置错），stderr 单行 `{"schema_version":…,"state":…,"reason":…}`。**不声称 Range/206/取消——大原件流属 G-CWP-02。**

## 4. 测试记录

### 4.1 合成测试（focused，15/15 GREEN）

命令：`pytest tests/contract/test_public_document_browser.py -q`（owner venv python 3.14.2）
结果：**15 passed**。覆盖：跨文种/多版本（同 document_id 双 source）、固定快照分页/排序/重放、内容变更→stale、同名不同字节、双 source/hash 版本键互异+精确重开、迁根（revision 不变 + owner reader `verify_version` 解析同 SourceRef）、缺 catalog→unavailable、部分根缺失→partial、空/过滤空、非法请求族、CLI 端到端（browse→翻页→reopen→bad→重复 key→null entity）、零路径泄漏（响应体+cursor+snapshot token）。

### 4.2 相邻回归（owner 既有测试）

`pytest tests/contract/test_source_version_reader.py tests/contract/test_source_export_v2_cli.py -q` → **40 passed**。
`tests/contract/test_cross_root_dedup_fc603.py::test_fc603_ex06_amended_original_stable_revision_rule` → **基线固有失败**（已在 owner 原仓 HEAD `0c988e8d` 独立复现为同样失败，非本包引入）。

### 4.3 真实 catalog 只读 smoke（生产数据，零写）

- 实体 `company-name:Alphabet Inc`：browse 0.08s，8 个 annual_report 版本，`state=partial`（部分版本的根不在当前 config——如实报告），facets 正确；取 item[0] reopen → 2.71s，source_ref 与 browse 逐字节一致；响应全量 JSON 泄漏扫描（relative_path/absolute_path/.source_catalog/catalog.sqlite3/tmp 路径）零命中。
- 生产 catalog 观察：schema=1.2.0 而代码 fail-closed 支持 1.4.0（`schema_version()` 显式校验时；browse 与既有 v2 读路径一致，不在每次读时校验）。owner 在途 loop 重扫后会迁移，非本包范围。

### 4.4 环境发现（对 D03/owner 有用）

本机 %TEMP% 路径含非 ASCII 字符（中文用户目录）时，SQLite 需要**落盘临时 B-tree** 的查询（大结果 DISTINCT/GROUP BY/ORDER BY spill）会报 `unable to open database file`（可复现：生产 catalog 上 `entities JOIN document_entities GROUP BY`）。本模块全部 SQL 已去 spill 化（Python 侧去重/排序）。owner 既有工具（如 `entities_like` 的 GROUP BY）在该机器上可能同样受影响——**owner 侧问题，本包未改动**。

## 5. 独立审查（用户要求，2026-10-27）

- 审查者：独立 general-purpose agent（非实现作者），审查 commit 范围 `7ef04c9c` → 复测 `214c5379`。
- 首轮：22/23 项 smoke+边界通过；4 项发现（F-01 MAJOR / F-02 MINOR / F-03、F-04 NIT），逐项结论表见 `review-report.md`。
- 返修：F-01..F-04 全部修复（commit `214c5379`），每条保留 RED 复现（CLI 级 null-entity 信封断言、顺序无关重放、伪造 offset、空列表语义），RED→修复→GREEN 证据见 §4.1 与 review-report.md。
- 复审：审查者按原反例逐条复测 GREEN，最终判定与逐项结论见 `review-report.md`（绑定最终候选 commit）。

## 6. 清理与 NOT_RUN

- 清理：worktree 内测试临时目录（`tmp*`/`pytest-of-*`）已删除；无生产 config 写入（R4.1：全程 tmp 夹具）；owner 主工作区未动。
- NOT_RUN / 明示不支持：
  - Range/206/取消（G-CWP-02 范围）；
  - 未合并 owner main、未 push、未注册 console-script、未改 pyproject；
  - 未做 Dashboard 仓任何适配（D03 职责）；
  - `document_kinds` 过滤值未按 13 值闭集强校验（按目录实际值匹配，正则级校验）——如实声明而非缩小要求。
