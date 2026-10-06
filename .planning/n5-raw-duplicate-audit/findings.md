# N5-RAW-DUP findings（实测，非估计）

所有数字来自本包工具在真实生产 catalog 上的只读运行，
报告见 `.planning/n5-raw-duplicate-audit/raw_duplicate_report_{scan,e2e}.json`。

## 1. 生产 catalog 规模

- `locations` 46,605 行参与本次评估（JOIN `sources`，`source_id` 非空）；
  全表 46,606 行（1 行无 source 关联）。
- `sources` 43,112，`registered_bytes` 35,110,881,225 B（32.69 GiB）。
- roots 4：`company_raw`、`dayu_portfolio`、`dropbox_stock`、`future_lake`。
- catalog schema `1.2.0`；config sha256 `3d159a4e…446e3f968`；
  数据库 222,408,704 B，`mtime_ns=1791248158420833300`，`-wal`/`-shm` 均已存在。

## 2. 重复空间答案

| 指标 | 值 |
|---|---|
| 候选组（≥2 个同 digest location） | **3,531** |
| `logical_duplicate_bytes_upper_bound` | **7,804,167,537 B ≈ 7.27 GiB** |
| 占已登记原件比例 | **22.2%** |
| `physical_allocated_bytes` | **7,804,167,537 B**（可得，非 null） |
| `deleted_bytes` | **0**（本次未删除任何文件） |
| `similar_groups`（同 size 不同 digest，贡献 0 字节） | 100（上限） |
| `uncertain_groups` / `unresolved_groups` | 0 / 0 |
| `verified_duplicate_bytes`（复核前 3 组） | 158,223,532 B |

复核口径：`--max-groups 3`，实读 6 个文件、316,447,064 B，
`verified_groups=3`，`status=succeeded`。

**结论方向**：上界 7.27 GiB、占 22.2%，远高于 256MiB 建议阈值，
`recommendations.verdict = needs_main_decision` —— 值得由 MAIN 结合引用兼容性
决定是否实施；本包只出建议，不改架构、不删文件。

## 3. 四类识别在生产上的分布

已列出的 510 组（受 1MiB/5000 行截断）全部是 `distinct_physical_copies`；
`same_path_references` 1 组、`shared_physical_file`（hardlink）0 组在探针中确认，
但因逻辑重复字节为 0，在按字节降序的列表里排在截断线之外。

跨 root 是主要形态：`company_raw` ↔ `dropbox_stock` 同一份 PDF 两处各存一份
（例如 `合盛宝业` 2025 年报 79,925,886 B ×2、`三花智控` 40,776,744 B ×2 等）。

## 4. 运行成本与上限

| 运行 | elapsed | read_bytes | read_files | limits_hit | status |
|---|---|---|---|---|---|
| `scan`（冷缓存首跑） | 101.761 s | 0 | 0 | `detail_rows`, `report_bytes` | succeeded |
| `verify`（冷缓存首跑，max-groups 3） | 96.715 s | 316,447,064 | 6 | `max_groups`, `detail_rows`, `report_bytes` | succeeded |
| `scan`（随包提交的报告，热缓存） | 63.461 s | 0 | 0 | `detail_rows`, `report_bytes` | succeeded |
| `verify`（随包提交的报告，热缓存） | 65.154 s | 316,447,064 | 6 | `max_groups`, `detail_rows`, `report_bytes` | succeeded |

四次均在默认 300 s 截止内完成。提交的两份报告 1,048,266 B / 1,046,591 B，均 ≤ 1 MiB。

## 5. 只读与保护实测

- 两次运行后：原件 SHA-256 / size / mtime 全部不变（E2E 对前 3 组所有 locator 逐一比对）。
- config sha256 不变；数据库 `byte_size`+`mtime_ns` 不变；
  catalog 目录文件清单不变（**没有新建 `-wal`/`-shm`**，靠 `immutable=1` 策略）。
- `protected_before == protected_after`，`protected_unchanged = true`。
- 报告中无"已释放 / freed / reclaimed"措辞，`deleted_bytes = 0`（`report.py` 守卫）。

## 6. 关键实现事实

- **副作用坑**：官方 `ReadOnlyCatalogReader` 在 `-wal` 缺失时会凭空创建
  `-wal`/`-shm` 并在关闭后保留（实测复现）。因此本包用 `ReadOnlyReader`
  等价 API + 更严策略：无 `-wal` 时 `immutable=1`，有 `-wal` 无 `-shm` 直接拒绝。
- **性能坑**：对 46,605 个 location 逐个 `realpath` 约 42 s。改为只对
  **多引用组成员**做 realpath（`enforce_containment`），observe 只做词法包含 +
  `lstat`，verify 单次运行从 222 s 降到 96 s。
- **报告体积坑**：`apply_size_cap` 必须用与 `write_json` 完全一致的序列化参数
  （`indent=1, sort_keys=True`）度量，并且必须是**写入前最后一次变更**；
  否则后续字段微增会把报告顶过 1MiB。现用"带 13 位占位符的二分搜索 + 写前收尾"。
- **云占位**：`companies/` 下 1,007 个文件 `st_file_attributes = 0x100020`
  （`UNPINNED|ARCHIVE`），读取会触发 hydrate；工具按属性跳过不打开。
- `GetCompressedFileSizeW` 在本机可取分配字节，因此
  `physical_allocated_bytes_available = true`（不是 null）。

## 7. 未覆盖 / 交给 MAIN

- 只复核了逻辑字节最大的 3 组（`--max-groups 3`）；其余 3,528 组为 metadata 级上界，
  未实读。要全量确认需显式提高 `--max-groups` 并接受相应读入量与耗时。
- 报告受 1MiB/5000 行限制只列 510 组；`counts.duplicate_groups_full = 3531`
  与 `truncated.*` 记录了截断量。
- 是否实施生产去重（SHA 对象化 vs 硬链接 vs 保持现状）由 MAIN 决策；
  本包不提供删除清单、不提供迁移方案。
- E2E 只跑一次集中责任包；未扩日常 CI 矩阵。
