# G-D B3：旧派生归档与来源事实审计

本卡对应机器收据 [gd_b3_metadata_audit_2026-10-03.json](gd_b3_metadata_audit_2026-10-03.json)。只写本卡与该 JSON；没有改产品、共享 PWF、原文或生产库，没有删除文件或完整解压归档。

## 结论

全部原始 non-span 元数据已在当前 catalog 保存。旧 zstd 没有独占的 sources、documents、locations、元数据断言、实体关系、退休审计或来源版本事实。两个目标的主体是旧派生证据，可在明确旧证据不可用后独立精确退役；不需要 25M 条 span tombstone 或完整恢复演练。本结论不承诺能重现旧 span ID，也不宣称历史原文位置全部可读。

`scripts/retire_source_catalog_db.py:177–226` 的 `_make_shadow` 只对 evidence_spans 筛选 active，其他表整表复制并逐行 digest 比较。此次复核使用相同稳定 digest 编码及主键排序，16 张表与 prepared 的全行 SHA/行数相等；完整结果逐表保存在 JSON。catalog_meta 只比原有非 legacy 键，迁移增加的四个 legacy 键另列。

## 当前数据库与依据

| 对象 | 大小 B | 完整实读 SHA-256 |
|---|---:|---|
| `.source_catalog/catalog.sqlite3` | 3,055,800,320 | `30794a01e04a9e77ec13cd7b27a3f24bf9861bda9fc7c3c50a2b362830fbc823` |
| `retirement/20260926T170825Z-4a9c67e1/prepared.json` | 4,288 | `cebcc51daf0a13a5f583273a1f0c3218f265fbe845fd8656e38cd82a30805cd9` |
| `retirement/20260926T170825Z-4a9c67e1/retired.json` | 1,113 | `6f7f1b88b36aa93f22056627143fa3dd1c4bdd8d4ce3032ab1a1d4a78008b8e9` |

数据库 mtime_ns 为 **1790490231504738600**，审计前后 size/mtime 相同；WAL 不含提交帧，Worker desired_state 为 paused。所有 hash 为有界流式实读，没有重新 hash raw。

## scan_runs 的唯一新增行

原 480 行 digest 与 prepared 严格一致：

`b6caf11aafd7097c01d555c0960c34c9918ce92d4bb02de5741a67ad69331dae`

当前为 481 行，多出的记录：

- run_id：`scan-c4ae2c0090944c42b2b30ede8cb5eac6`
- started_at：`2026-09-27T06:16:27Z`
- completed_at：`2026-09-27T06:16:35Z`
- status：`completed_with_errors`
- report_json 全文保存在 JSON 的 `scan_runs.extra_rows`；错误为 company_raw 缺少 v2 adapter_id，`files_seen=files_hashed=files_reused=0`、`errors=1`。

历史筛选为 `started_at < '2026-09-26T18:30:01'`，按 run_id 排序。该新增扫描没有改变 sources/documents/locations，相关完整 digest 仍相等。

## 精确归档目标

| 项目相对路径 | B | 本次实读 SHA-256 |
|---|---:|---|
| `.source_catalog/retirement/20260926T170825Z-4a9c67e1/catalog.full.sqlite3.zst` | 6,198,704,362 | `1bc09746b8ee18db91fbbd14c97410241ad9a54d3f45a6468886692e763edd9e` |
| `source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` | 5,207,478,767 | `a3a6b2782350820cdf9a466e074685f9b377e2df46b42c11077a5c7ae1842109` |

合计 **11,406,183,129 B / 约 10.62 GiB**。zstd SHA/size 与 prepared/retired 相符；历史 prepared 已记录完整解压流长 49,677,344,768 B、SHA `69f498a23895c5a693621d9ee754b20bb9d6fbc199b684dc16e950d00b8fd7b7` 及 zstd_test=ok。本次只 hash 压缩文件字节，不解压、不复制。

旧 gzip 目录只有该文件，没有 `*.manifest.json`。本次 SHA 绑定精确候选身份，不是归档内容完整性的证明。`prune_retired_evidence.py:306–324` 只发现已发布 manifest，因此这件旧 gzip 不参与现行自动 prune 计划。

## 已实读的查询行为

前序有界抽样读取五条 gzip JSONL（单行上限 1 MiB），其 source/document 在当前库存在，document 均 retired。`EvidenceQueryService.lookup/list_spans` 共十次返回 `EvidenceQueryArchivedError`；一个 active 样本正常读取，unknown source 为 NotFound。样本不是全量 gzip/zstd 重合验证，也不作为全库 raw 可读证明。

调用路径是 `source_catalog.cli:1123–1134 → EvidenceQueryService.lookup/list_spans → _raise_if_archived:357 → EvidenceQueryArchivedError → cli:1571–1577 → structured_error`。

现有 error_type 为 `legacy_evidence_archived`、retryable=false、CLI exit 1。`evidence_query.py:381–383` 文案仍声称证据存在 verified cold snapshot；归档退役前应改为中性说明“non-active legacy evidence is unavailable in the active catalog; source identity is retained”，保留兼容 code。没有发现产品 cold reader。

## 实施接口建议

仅允许上述两个精确文件，绑定 SHA/size、依据小收据 SHA 和本审计；持久化 intent 后逐件 unlink，逐件记结果并最终发布 receipt，重复/中断恢复不得重计空间。来源事实、raw、当前库和历史 prepared/retired 留存。receipt 明确旧派生记录已丢弃，不保证恢复旧 locator/span ID。禁止目录递归删除、VACUUM、全量解压和 per-span tombstone。

一个小型真实 SQLite/raw/gzip/zstd 节点包验证 dry-run、apply、重复、中断恢复、SHA 漂移、raw/DB 路径和 reparse 拒绝；删除前后来源元数据和 raw 不变、active reader 正常、retired 旧证据明确不可用、unknown 仍 NotFound，测试根 finally 复原。无须重复全部消费者真样本。

`retire_catalog_snapshot.py:70–85,165` 的历史 B1 _basis 要求 zstd 仍存在，故 B3 后重新运行 B1 命令会拒绝。B1 已完成 receipt 保留并被 B3 引用即可；如实现回显优化，只允许“已有完成 receipt 且 snapshot 不存在”的分支，不能降低新删除的 archive 验证。
