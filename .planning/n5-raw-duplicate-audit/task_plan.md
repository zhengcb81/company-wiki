# N5-RAW-DUP 原件重复空间只读实证与工具 — 施工计划

任务卡：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/n5_raw_duplicate_audit.md`
总包：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/n5_parallel_packages_2026-10-06.md`
分支 `codex/n5-raw-duplicate-audit`（基线 `e46108b4f30d5b7e47bfc712e360f173c00b702c`），
worktree `C:/Users/郑曾波/Projects/cwp-lanes-20261006/raw-duplicate-audit`。

写集仅：`tools/raw_duplicate_audit/`（含测试与说明）、`.planning/n5-raw-duplicate-audit/`、
`docs/implementation/handoffs/N5-RAW-DUP/`。不改 src/scripts/ 现有 tools、生产配置、公共合同、总 PWF 或其他包目录。

## 关键事实（desk survey）

- schema 主文件 `src/company_wiki/source_catalog/store.py` `_DDL`（v1.2.0）：
  `locations(root_id, relative_path, absolute_path, source_id, document_id, role,
  location_status, observed_size, observed_mtime_ns, ...)`、
  `sources(source_id, content_sha256 UNIQUE, byte_size, ...)`、
  `roots(root_id, path, kind, priority, ...)`。
  `locations` 无 sha 列；已登记 sha/size 在 `sources` 上，按 `source_id` 关联。
- 生产 catalog `.source_catalog/catalog.sqlite3`（222,408,704 B，WAL+SHM 均存在，schema 1.2.0）。
  只读打开必须 `?mode=ro` + `PRAGMA query_only=ON`；有 WAL 时不得 `immutable=1`，
  无 WAL 时补 `immutable=1` 避免新建 `-shm`。绝不实例化 `CatalogStore`（会 mkdir/WAL/DDL/迁移）。
- 生产规模实测（只读查询）：`locations` 46,606（active 25,048 / retired 21,551 / missing 6 / quarantined 1）、
  `sources` 43,112、`roots` 4（company_raw、dayu_portfolio、dropbox_stock、future_lake）。
  `source_id` 关联 location >1 的有 3,531 组。
- 预研（不写入任何文件的只读探针）：按 normalized path + (st_dev, st_ino) 去重后，
  同内容不同物理副本 3,530 组，同路径多引用 1 组，hardlink 0 组，
  逻辑重复字节上界约 7.44 GiB，已登记原件总量约 32.70 GiB。**该数字仅为设计参考，正式结论以工具实测报告为准。**
- 云占位风险实测：`companies/` 下 1,007 个文件 `st_file_attributes = 0x100020`
  （`FILE_ATTRIBUTE_UNPINNED | ARCHIVE`），属云端未水合文件；读取会触发 hydrate 下载。
  必须识别 `UNPINNED(0x100000)/OFFLINE(0x1000)/RECALL_ON_OPEN(0x40000)/RECALL_ON_DATA_ACCESS(0x400000)`
  并跳过实读，只做 stat 元数据。
- Windows 无 `st_blocks`；已验证 `GetCompressedFileSizeW` 可取分配字节（>4GiB 需高低位合并）。
  取不到则按卡要求 `physical_allocated_bytes = null`。
- 只读连接样板与原子写：`tools/legacy_storage/core.py::read_connection` / `write_json`（本线自包含副本，不跨工具耦合）。
- 交接格式取 N5 总包 `cwp-independent-handoff/1`（非 P5 的 `cwp-parallel-handoff/2`）。

## 四类识别（必须分开记账，前三种不能都按重复副本累加）

1. `same_path_references`：不同 source/version/location 指向同一 normalized path → 物理副本 1，逻辑重复 0。
2. `shared_physical_file`：不同路径但同一物理身份（hardlink/junction 别名）→ 物理副本 1，逻辑重复 0。
3. `content_duplicate`：不同物理文件 + 已实读字节相同 → 物理副本 n，逻辑重复 `(n-1) × registered_size`。
   未实读只叫候选，实读并匹配已登记 sha 后才可称 exact duplicate。
4. `similar_size_different_content`：同 size 不同已登记 sha → `similar_groups`，逻辑重复 0。

物理身份未知（`st_ino == 0`、reparse point、越出已配置 root、ACL 拒绝、文件消失/变更中）→
归 `uncertain`/`unresolved`，`logical_duplicate_bytes = null`，不进入
`logical_duplicate_bytes_upper_bound`，不伪算释放量。

## 报告 `raw-duplicate-assessment/1`

`catalog/config sha 或只读 snapshot 标识`、`scan_scope`、`elapsed`、`limits_hit`、
`candidate/verified/unresolved` 计数、重复组（每组保留 source/version/location 引用计数、
distinct physical copies、`logical_duplicate_bytes`）、顶层
`logical_duplicate_bytes_upper_bound`、`physical_allocated_bytes`（可得否则 null）、
`deleted_bytes = 0`、`protected_before/protected_after`。
小组项只写 ID/hash/size + root-relative locator；本机绝对路径只进 `--local-output` 独立非 Git 文件。
Git 报告 ≤1MiB，详细行 ≤5000 且显式截断。措辞必须是“未来可能减少的逻辑副本字节”，
禁止“已释放 X GB”。`recommendations` 至少比较保留现状 / SHA 对象化 / 文件系统链接三方案对
source 版本、移动、引用、可恢复性的影响；收益过小直接建议不做。

## 步骤

1. [x] 建 worktree/分支 + 本 PWF；desk survey（schema/reader/只读连接/生产只读探针）。
2. [x] RED：算账 12 例 + 读入预算/截止 6 例（先失败后转绿）。
3. [x] 实现 `raw_duplicate_audit/{core,catalog,classify,verify,report,assessment,cli}.py`：
   只读扫描、有限流式实读（1MiB）、deadline/byte cap 前停止并保留部分报告、
   输出原子写且不覆盖未知旧报告、不产生生产 DB/WAL/cache/清理清单副作用。
4. [x] Integration：真实 schema 隔离 DB + 真实文件/hardlink（11 项，含七类夹具、
   ACL 拒绝、预算/截止 partial、拒绝码、原件与 catalog 不变）。
5. [x] E2E：真实生产 catalog 只读筛候选 3,531 组、复核前 3 组（6 文件 / 316,447,064 B /
   96.7 s），原件 SHA/size/mtime、config sha、catalog 大小与 mtime、目录清单全部不变。
6. [x] finally 恢复本 worktree 测试目录原状；两份小报告留在
   `.planning/n5-raw-duplicate-audit/`，原件从未复制/删除；0 LLM/HTTP/provider。
7. [x] 一次集中 Unit/Integration/E2E + ruff + `git diff --check`，未扩日常 CI。
8. [x] 提交代码与 `docs/implementation/handoffs/N5-RAW-DUP/HANDOFF.md`、`handoff.json`。

## 边界

- 不删除、不移动、不硬链接、不复制原件进 Git；不实施对象存储迁移。
- 生产 SQLite 仅 `mode=ro`，不实例化 writer，不拿写锁，不 VACUUM。
- 不扫描 catalog 之外的磁盘；不追随未知外部目录；不触发云端 hydrate 下载。
- 0 LLM / 0 HTTP / 0 provider；不用本线 LLM 预算。
- 生产去重是否实施由 MAIN 依据真实收益与引用兼容决定，外线不自动删除。
