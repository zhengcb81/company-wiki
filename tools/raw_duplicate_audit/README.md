# raw_duplicate_audit — 原件重复空间只读盘点（N5-RAW-DUP）

> MAIN 2026-10-06集成修正：51项/9.09秒含两CLI绿；Windows分配量未知/null，历史报告该字段不能用作磁盘收益。硬cap逐块约束、partial字节计账、双输出与未知旧文件保护、独占.tmp、诊断无机器路径、非组列表也受1MiB上限。ACL反例采用PermissionError注入，不更改真实权限。生产历史3组实读证据保持，未新跑全量；原件删除0。deadline在操作边界协作检查，不能瞬间中断阻塞文件系统I/O。

回答一个问题：**catalog 已登记的原件里，还有多少完全相同的字节被重复存放，值不值得下一阶段去重。**
只读、只估算、只出建议；不删除、不移动、不硬链接、不复制原件，不实施对象存储迁移。

## 入口

```powershell
# metadata 候选扫描（0 字节实读）
PYTHONPATH=src python tools/raw_duplicate_audit/cli.py scan `
  --config config/source_catalog.yaml `
  --output .planning/n5-raw-duplicate-audit/raw_duplicate_report_scan.json

# 候选扫描 + 有限流式实读复核（默认最多 100 组、512MiB、300 秒）
PYTHONPATH=src python tools/raw_duplicate_audit/cli.py verify `
  --config config/source_catalog.yaml `
  --output .planning/n5-raw-duplicate-audit/raw_duplicate_report_e2e.json `
  --local-output "$env:TEMP/n5_raw_dup_local_paths.json" `
  --max-groups 3 --max-read-bytes 536870912 --deadline-seconds 300
```

`cli.py` 自己把仓库 `src/` 与 `tools/` 加进 `sys.path`，`PYTHONPATH=src` 是显式写法但非必需。

退出码：`0` = `succeeded`/`partial`（报告已写），`2` = `refused`（拒绝，部分场景不写文件）。

## 模块

| 文件 | 职责 |
|---|---|
| `core.py` | 只读原语：`Budget`（硬字节上限+截止）、`iter_chunks`/`hash_file`（最多1MiB流式SHA，最后一块受剩余额度限制）、路径归一化、物理身份、可选分配字节、云占位属性、独占随机临时文件原子写、"不覆盖未知旧报告"判定 |
| `catalog.py` | `load_catalog_config` 载入配置、`ReadOnlyReader`（`?mode=ro` + `immutable=1` 时更严的副作用策略）、locations/sources 读取、similar 组、protected 快照 |
| `classify.py` | `observe`（仅 stat，不追随未知外部目录）、`build_groups`、`enforce_containment`（只对候选组做 realpath 越界判定）、`account_group` 记账、`fill_allocations` |
| `verify.py` | 有界流式实读：变更检测、已登记 digest 比对、云占位跳过、预算中断 |
| `report.py` | 小组项组装、明细行上限、1MiB 报告上限、三方案建议、禁用措辞守卫 |
| `assessment.py` | 端到端编排、拒绝码、protected before/after |
| `cli.py` | `scan` / `verify` 两个子命令 |

## 四类识别（前三种不能都按重复副本累加）

| classification | 含义 | 逻辑重复字节 |
|---|---|---|
| `same_path_references` | 不同 source/version/location 指向同一路径 | 0 |
| `shared_physical_file` | 不同名字、同一物理文件（hardlink/别名） | 0 |
| `distinct_physical_copies` | 不同物理文件 + 已登记同 digest | `(副本数-1) × registered_size` |
| `similar_size_different_content` | 同 size、不同已登记 digest（单列 `similar_groups`） | 0 |

物理身份未知（`st_ino==0`、reparse point、越出已配置 root、ACL 拒绝、文件消失/变更中）
→ `uncertain` / `unresolved`，`logical_duplicate_bytes = null`，**不进上界，不伪算释放量**。

只有**实际打开并流式读取、且字节与已登记 digest 一致**后，才计入
`verified_duplicate_bytes`；其余归入 `verification.status`
（`metadata_sha_mismatch` / `changed` / `acl_denied` / `missing` /
`skipped_cloud_placeholder` / `not_attempted`）。

## 只读与副作用边界

- 生产 SQLite 只读打开：`?mode=ro` + `PRAGMA query_only=ON`；`-wal` 存在但缺 `-shm` 直接拒绝；
  无 `-wal` 时补 `immutable=1`，避免 SQLite 凭空创建 `-wal`/`-shm`。绝不实例化 `CatalogStore`。
- 只 stat/实读 **catalog 已登记的 location**，不做全盘扫描。
- 只在 `root / relative_path` 词法上位于已配置 root 内才 stat；候选组成员再做 realpath 越界复核，
  越界即标 `outside_configured_root` 并**不读**。
- `FILE_ATTRIBUTE_UNPINNED / OFFLINE / RECALL_ON_OPEN / RECALL_ON_DATA_ACCESS` 视为云占位，
  **不打开**（避免触发 hydrate 下载），单列 `skipped_cloud_placeholder`。
- 输出路径与 config、catalog 目录、任一 root 重叠 → `refused: report_path_overlaps_data`，且不写文件。
- 输出文件已存在且不是本工具的 `raw-duplicate-assessment/1` 报告 →
  `refused: output_exists_unknown`，原文件一字节不改。
- `deleted_bytes` 恒为 0；报告中禁止出现"已释放 / freed / reclaimed"措辞（`report.py` 内有守卫）。

## 报告 schema `raw-duplicate-assessment/1`

`catalog`（config sha + 只读 snapshot 标识，路径按 project 相对化）、`scan_scope`、
`limits` / `limits_hit`、`counts`、`duplicate_groups`
（每组 `reference_counts{sources,versions,documents,locations}`、`distinct_physical_copies`、
`logical_duplicate_bytes`、`locators` 只含 root-relative `relative_path`）、`similar_groups`、
`logical_duplicate_bytes_upper_bound`、`verified_duplicate_bytes`、
`physical_allocated_bytes`（不可得为 `null`，另给 `_partial` 与 `_unavailable_groups`）、
`deleted_bytes=0`、`protected_before/after` + `protected_unchanged`、`truncated`、
`recommendations`（保留现状 / SHA 对象化 / 文件系统硬链接，三方案对 source 版本、移动、引用、
可恢复性的影响；`binding=false`）、`notes`。

- 本机绝对路径只进 `--local-output`（schema `raw-duplicate-assessment-local-paths/1`），不进 Git 报告。
- 明细行 ≤ 5000、报告 ≤ 1MiB，超出显式 `truncated`。
- `status=partial` 只在 `deadline` 或 `read_bytes` 被截断时出现；
  `max_groups/detail_rows/report_bytes` 属于 scope 上限，只进 `limits_hit`。

## 限制与可调参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--max-groups` | 100 | 实际打开复核的组数上限 |
| `--max-read-bytes` | 536870912 (512MiB) | 流式实读字节上限 |
| `--deadline-seconds` | 300 | 整次运行墙钟上限 |
| `--max-detail-rows` | 5000 | 报告明细行上限 |
| `--max-similar-groups` | 100 | `similar_groups` 条数上限 |
| `--location-status` | `all` | `all` / `active` |
| `--hash-catalog` | 关 | 额外记录 catalog 数据库文件完整 SHA-256 |
| `--overwrite` | 关 | 仅覆盖同schema的本工具报告，未知文件始终不覆盖；main/local两输出均不得覆盖原件/配置/库或互相覆盖 |
| `--local-output` | 无 | 机器绝对路径独立输出（非 Git） |

## 测试

```powershell
# 集中一次（含生产 E2E）
python -m pytest tools/raw_duplicate_audit/tests -q
python -m ruff check tools/raw_duplicate_audit
```

- 单元：`test_raw_duplicate_audit_accounting.py`、`test_raw_duplicate_audit_budget.py`
- 集成：`test_raw_duplicate_audit_fixture_set.py`（真实 schema 隔离 DB + 真实文件/真实 hardlink，
  七类夹具：三引用同路径、hardlink 两名、不同物理副本同内容、同 size 不同字节、
  登记 SHA 错误、扫描后变更、ACL 拒绝）
- E2E：`test_raw_duplicate_audit_e2e.py`（`slow`+`real_data`+`e2e`，真实生产 catalog 只读）

日常 CI 只跑 `tests/`（`pytest.ini` 的 `testpaths`），本包不会进入日常 CI。

## 结论口径

`logical_duplicate_bytes_upper_bound` 是**未来可能减少的逻辑副本字节上界**，
不是已收回的空间；本次 `deleted_bytes=0`。是否在生产实施去重由 MAIN 依据真实收益与
引用兼容决定，本工具不修改任何架构、不删除任何文件。
