# N5-RAW-DUP HANDOFF — 原件重复空间只读盘点工具与实测

`lane_id` N5-RAW-DUP · `branch` codex/n5-raw-duplicate-audit（基线 `e46108b4f30d5b7e47bfc712e360f173c00b702c`） ·
`delivery_head` `a1418a0b901bd91146c69be3e1b28cde790d9908` · 2026-10-06

## 交付物

| 路径 | 说明 |
|---|---|
| `tools/raw_duplicate_audit/__init__.py` | 报告 schema 常量 |
| `tools/raw_duplicate_audit/core.py` | 预算/流式 SHA/路径与物理身份/云占位/原子写/不覆盖未知旧报告 |
| `tools/raw_duplicate_audit/catalog.py` | 配置载入、`ReadOnlyReader`、locations/sources/similar/protected |
| `tools/raw_duplicate_audit/classify.py` | observe（仅 stat）、分组、越界复核、四类记账 |
| `tools/raw_duplicate_audit/verify.py` | 有界流式实读复核与状态归类 |
| `tools/raw_duplicate_audit/report.py` | 报告组装、1MiB/5000 行截断、三方案建议、禁用措辞守卫 |
| `tools/raw_duplicate_audit/assessment.py` | 端到端编排与拒绝码 |
| `tools/raw_duplicate_audit/cli.py` | `scan` / `verify` CLI |
| `tools/raw_duplicate_audit/README.md` | 用法、四类口径、只读边界、参数表 |
| `tools/raw_duplicate_audit/tests/*` | 4 个测试模块 + hermetic conftest（31 项） |
| `.planning/n5-raw-duplicate-audit/{task_plan,findings,progress}.md` | 本线独立 PWF |
| `.planning/n5-raw-duplicate-audit/raw_duplicate_report_scan.json` | 生产只读 scan 收据（1,048,266 B） |
| `.planning/n5-raw-duplicate-audit/raw_duplicate_report_e2e.json` | 生产只读 verify 收据（1,046,591 B） |
| `docs/implementation/handoffs/N5-RAW-DUP/{HANDOFF.md,handoff.json}` | 本交接 |

写集之外零改动：`git status` 只有 `tools/raw_duplicate_audit/`、`.planning/n5-raw-duplicate-audit/`、`docs/implementation/handoffs/N5-RAW-DUP/`。

## 入口（精确命令）

```text
# metadata 候选扫描（0 字节实读）
PYTHONPATH=src python tools/raw_duplicate_audit/cli.py scan ^
  --config config/source_catalog.yaml ^
  --output .planning/n5-raw-duplicate-audit/raw_duplicate_report_scan.json ^
  --overwrite

# 有限流式实读复核（默认 100 组 / 512MiB / 300s；下例为本线 E2E 的 3 组口径）
PYTHONPATH=src python tools/raw_duplicate_audit/cli.py verify ^
  --config config/source_catalog.yaml ^
  --output .planning/n5-raw-duplicate-audit/raw_duplicate_report_e2e.json ^
  --local-output %TEMP%\n5_raw_dup_local_paths.json ^
  --max-groups 3 --max-read-bytes 536870912 --deadline-seconds 300 ^
  --overwrite
```

退出码 `0` = `succeeded`/`partial`（报告已写），`2` = `refused`。
`--local-output` 是**非 Git** 的机器绝对路径侧文件；不给该参数则报告里完全没有绝对路径。
报告 schema `raw-duplicate-assessment/1`；侧文件 schema `raw-duplicate-assessment-local-paths/1`。

## 真实 scope（生产 catalog，只读）

| 项 | 值 |
|---|---|
| catalog | `.source_catalog/catalog.sqlite3`，222,408,704 B，`mtime_ns=1791248158420833300`，schema `1.2.0`，`-wal`/`-shm` 均已存在 |
| config | `config/source_catalog.yaml`，866 B，sha256 `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968` |
| roots | `company_raw` / `dayu_portfolio` / `dropbox_stock` / `future_lake` |
| 参与评估的 location 行 | 46,605（`location_status=all`，JOIN `sources`） |
| 已登记 source / 字节 | 43,112 / 35,110,881,225 B（32.69 GiB） |
| 候选组（≥2 个同 digest location） | **3,531** |
| `logical_duplicate_bytes_upper_bound` | **7,804,167,537 B ≈ 7.27 GiB（占已登记 22.2%）** |
| `physical_allocated_bytes` | **7,804,167,537 B**（可得，非 null） |
| `verified_duplicate_bytes` | 158,223,532 B（复核前 3 组） |
| `deleted_bytes` | **0** |
| `similar_groups`（同 size 不同 digest，贡献 0） | 100（`--max-similar-groups` 上限） |
| `uncertain_groups` / `unresolved_groups` | 0 / 0 |
| scan | 66.839 s，读入 0 B，`status=succeeded` |
| verify | 74.594 s，读入 316,447,064 B / 6 文件，`status=succeeded` |
| 报告体积 | 1,048,266 B / 1,046,591 B（均 ≤ 1 MiB） |
| 建议 | `recommendations.verdict = needs_main_decision`（非约束，`binding=false`） |

收据 sha256（按仓库 blob 的 LF 字节）：
`fbdaeaed24f10a0d1b7ec190268e9cfcaaecac799611c595aa47b9f8d1234e3a`（scan）、
`ba057e5c2017ad628344901287935ea68caed9e84b868bdbe392a3caa14a2f33`（verify）。

## 未验证组与截断（明确边界）

- **只有 3 / 3,531 组做过实际字节复核**（`--max-groups 3`）。其余 3,528 组是
  metadata 级上界，**没有实读**，因此只进 `logical_duplicate_bytes_upper_bound`，
  不进 `verified_duplicate_bytes`。全量确认必须显式提高 `--max-groups`，
  并接受相应读入量与耗时。
- 报告按字节降序列出 **510 / 3,531** 组：`truncated.detail_rows = 1039`（上限 5000）、
  `dropped_groups_by_row_cap = 1043`、`dropped_groups_by_size_cap = 1978`、
  `dropped_groups_total = 3021`、`report_bytes = 1,046,591`（上限 1,048,576）。
  `counts.duplicate_groups_full = 3531` 保留全量口径。
- `limits_hit` 含 scope 类上限 `max_groups` / `detail_rows` / `report_bytes`；
  `status` 仍为 `succeeded`（只有 `deadline` 或 `read_bytes` 被截断才降级为 `partial`）。
- 已列出的 510 组全部是 `distinct_physical_copies`；`same_path_references`（1 组）与
  hardlink（0 组）因逻辑重复字节为 0 排在截断线之外，其判定由集成夹具覆盖。
- `similar_groups` 只列前 100 个 size 冲突，不构成去重对象。

## 四类识别口径（前三种不累加）

| classification | 判据 | 逻辑重复字节 |
|---|---|---|
| `same_path_references` | 不同 source/version/location 归一化到同一路径 | 0 |
| `shared_physical_file` | 不同路径、同一 `(st_dev, st_ino)` | 0 |
| `distinct_physical_copies` | 不同物理身份 + 已登记同 digest + 实读一致 | `(副本数-1)×registered_size` |
| `similar_size_different_content` | 同 size、不同已登记 digest | 0 |

物理身份未知（`st_ino==0`、reparse point、越出已配置 root、ACL 拒绝、文件消失、
扫描后变更、云占位）→ `uncertain` / `unresolved`，`logical_duplicate_bytes = null`，
**不进上界、不伪算释放量**。只有实际打开并流式读完、且字节等于已登记 digest，
才计入 `verified_duplicate_bytes`。

## 只读与保护（实测）

- 打开方式：`?mode=ro` + `PRAGMA query_only=ON`；有 `-wal` 无 `-shm` 直接拒绝；
  无 `-wal` 时补 `immutable=1`，**不创建** `-wal`/`-shm`（官方 `ReadOnlyCatalogReader`
  实测会在缺失时凭空创建并保留，故本包用等价 API + 更严策略）；从不实例化 `CatalogStore`。
- 只 stat/实读 catalog 已登记的 location，不做全盘扫描；候选组成员再做 realpath 越界复核，
  越界标 `outside_configured_root` 且不读。
- 云占位（`UNPINNED/OFFLINE/RECALL_ON_OPEN/RECALL_ON_DATA_ACCESS`）不打开；
  `companies/` 下实测 1,007 个 `0x100020` 文件因此被跳过。
- E2E 前后逐项比对：被复核原件的 SHA-256/size/mtime 不变；config sha256 不变；
  catalog `byte_size`+`mtime_ns` 不变；catalog 目录文件清单不变；
  `protected_before == protected_after`，`protected_unchanged = true`。
- 输出路径与 config/catalog/root 重叠 → `refused: report_path_overlaps_data`（**不写文件**）；
  已存在的非本工具报告 → `refused: output_exists_unknown`（原文件一字节不改）。
- 写集之外零改动；源仓与本 worktree 的原件从未复制、移动、硬链接或删除。

## 测试

| 命令 | 结果 |
|---|---|
| `python -m pytest tools/raw_duplicate_audit/tests -q --no-header -p no:cacheprovider` | **31 passed / 0 failed / 0 skipped / 150.40 s** |
| `python -m ruff check tools/raw_duplicate_audit` | All checks passed |
| `git diff --check` / `git diff --cached --check` | 干净 |

分层：

- 单元 18：`test_raw_duplicate_audit_accounting.py`（12，四类记账与上界排除）、
  `test_raw_duplicate_audit_budget.py`（6，1MiB 分块、字节上限、截止、limits_hit）。**先 RED 后 GREEN。**
- 集成 11：`test_raw_duplicate_audit_fixture_set.py` —— 当前真实 schema 隔离 DB +
  真实文件 + 真实 `os.link` hardlink（不支持则 `pytest.skip`）。七类夹具齐全：
  同一文件 3 条 location 引用、hardlink 两名、不同物理副本同内容、同 size 不同字节、
  登记 SHA 错误、扫描后变更、ACL 拒绝（Windows `icacls /deny` 实测，恢复在 `finally`）。
  另覆盖：无候选合法结果、字节上限 partial、截止 partial、两个拒绝码、
  原件+config+catalog 前后不变、报告 1MiB/5000 行上限。
- E2E 1：`test_raw_duplicate_audit_e2e.py`（`slow`+`real_data`+`e2e`），真实生产 catalog。

无既有失败；未改 `tests/`、`pytest.ini`、`pyproject.toml` 或任何 CI 配置，
本包不进入日常 CI（`testpaths=tests`）。

## 只读运行时预算

- 默认 `--max-groups 100`、`--max-read-bytes 536870912`、`--deadline-seconds 300`。
- 生产实测：scan 66.839 s / 0 B；verify（3 组）74.594 s / 316,447,064 B / 6 文件。
  冷缓存首跑为 101.761 s / 96.715 s，同样在 300 s 内。
- 截止或字节上限触发时停止并保留部分报告（`status=partial`），
  不会为了完成而突破上限。

## 假已执行边界

- 本包**只交付能力与实测证据**，没有在生产删除/移动/硬链接任何文件，
  没有生成清理清单，没有改架构、schema、配置、公共合同或总 PWF。
- `logical_duplicate_bytes_upper_bound = 7,804,167,537` 是**未来可能减少的逻辑副本字节上界**，
  不是已收回的空间；报告 `deleted_bytes = 0`，且有守卫禁止"已释放 / freed / reclaimed"措辞。
- 是否在生产实施去重（保留现状 / SHA 对象化 / 文件系统硬链接）由 **MAIN**
  依据真实收益与引用兼容决定；外线不自动删除。
- `recommendations` 是非约束建议（`binding=false`），只比较三方案对
  source 版本、移动、引用、可恢复性的影响。

## 临时 root

- pytest basetemp 由根 `conftest.py` 管理，会话后清理。
- E2E 的机器绝对路径侧文件写在 pytest `tmp_path`（随会话清理），不进 Git。
- 历史运行遗留的 `%TEMP%\n5-raw-dup-*` 已全部删除；当前 `absent → absent`。

## open items

1. 3,528 组未实读：要全量确认需提高 `--max-groups`，并接受 GB 级读入与更长耗时。
2. 报告只列 510 组；如需完整组清单，需要一个非 Git 的明细输出（当前仅 `--local-output` 含绝对路径）。
3. hardlink 与 ACL 两条集成断言在不支持 `os.link` / `icacls` 的平台会 skip（本机均实测通过）。
4. 生产去重是否实施、按哪种方案，待 MAIN 决策；本包不提供删除清单或迁移方案。
