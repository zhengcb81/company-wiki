# storage_footprint — 实际空间占用与保留状态只读盘点（N6-FOOTPRINT）

回答一个问题：**这个 project root 现在究竟多大、哪些类别在占、哪些是原件/可恢复材料？**

只读、只测量、只给处置建议；不清理、不删原件、不迁移、不硬链接、不改运行时，
不读任何被扫描文件的正文，不打开数据库，不联网、不调模型。

与 N5-DUP 的分工：N5 回答“登记原件里有多少完全相同字节”（跨根 exact-SHA 候选），
本工具只用**目录 metadata** 回答“本目录当前占用多少、分布在哪里”，两者都不等于已释放空间。

## 入口

```powershell
python tools/storage_footprint/run.py `
  --project-root 'C:/Users/郑曾波/Projects/company-wiki' `
  --max-files 100000 --max-seconds 60 `
  --output "$env:TEMP/cwp-footprint-report.json"
```

- 四个参数全部显式必填：只扫这一个 root，不走外部根/其他 worktree，不复制原件。
- stdout 输出一行 JSON（status/schema/complete/stop_reason/计数/report_bytes）。
- 退出码：`0` = 报告已写（`complete` 或显式 `partial`）；`2` = refused（不写任何文件）；
  `1` = 内部失败（临时文件已清理，目标不存在）。
- 拒绝场景：root 不存在、限额 ≤0、输出路径与 root 重叠、输出已存在且不是本工具的报告。

## 实测口径

| 量 | 定义 |
|---|---|
| `entries_seen` | 扫描到的全部目录条目（文件、目录、reparse/链接） |
| `directories_seen` | 实际进入的普通目录数（reparse 目录不进入） |
| `files_measured` | 经 metadata 取得逻辑大小并计入合计与分类的文件数（只 stat/lstat，零正文读） |
| `logical_path_bytes` | Σ 文件逻辑大小（`st_size`），按路径计量；硬链接/稀疏/压缩使其与磁盘分配量不同 |
| `allocated_bytes` | 恒为 `null`：本平台无经实证的 metadata-only 分配量 API；不用 cluster 估算、不调用系统压缩尺寸 API 冒充 |
| `unknown_files` | 已实测但归入 unknown 类的文件数 |
| `skipped_files` / `skipped_links` / `skipped_cloud_placeholders` | 未跟随、未 hydrate 的 reparse/链接/云占位条目（样本见 `skipped_samples`）；不计入分类，保留态=无法判断 |
| `duplicate_path_links` | 仅 `st_dev+st_ino` metadata 判定的同文件多路径；候选口径，未做内容验证，绝不计入“可删收益” |

恒等式（Unit 断言）：`Σ categories.files == files_measured`、
`Σ categories.logical_path_bytes == logical_path_bytes`、
`skipped_links + skipped_cloud_placeholders == skipped_files`。

预算语义：`--max-files` 是**文件条目**硬上限，精确停在该计数；`--max-seconds` 必须为有限正数，在每个
操作边界及目录枚举期间检查（OS 单次调用不可抢占）。触顶即 `complete=false, stop_reason="budget"`，部分数字如实保留并注明
partial，不外推、不冒充全量。目录遍历错误 → `stop_reason="errors"` 且 `complete=false`。

## 分类表（互斥路径规则，自上而下首条命中；只作用于 root 相对文件路径）

MAIN 验收修正后的优先级：已知 `companies/sectors/themes/future_lake/source_manifests/source_provenance` 原件树，以及 `.source_catalog/staging/`，先于下表的 AUTO、DB 和 tmp 规则。原件树的 `wiki` 仍是兼容页面；其他原件即使目录叫 tmp/build 或后缀为 .db，也必须保留。AUTO 仅识别非根目录内准确的 `automation.sqlite3/-wal/-shm` 名称；根目录标记不能将整仓重归类。显式扫描根及其父路径中的 reparse/云占位拒绝扫描。

| # | rule id | 命中条件 | 类别 |
|---|---|---|---|
| 1 | `auto_store_material` | 位于非根、直接含 `automation.sqlite3/-wal/-shm` 文件的目录之下（原件规则优先） | `auto_recovery_materials` 恢复中的AUTO任务材料 |
| 2 | `db_file` | basename 以 `.sqlite`/`.sqlite3`/`.db` 或 `-wal`/`-shm`/`-journal` 组合结尾 | `databases` 数据库/WAL/SHM |
| 3 | `tmp_tree` | 任一路径段 ∈ {tmp, .tmp, .tmp-e2e, \_\_pycache\_\_, .pytest_cache, .ruff_cache, .mypy_cache, .venv, node_modules, build, dist, .codegraph, .mimocode}，或 basename = `.coverage`、以 `pytest-` 开头 | `tmp_test_cache` tmp/测试/缓存 |
| 4 | `derived_index_sidecar` | root 级点文件：`.tmp*` 或 `*_index.json` / `*_db.json`（gitignore 标注可重建/临时） | `tmp_test_cache` |
| 5 | `wiki_pages` | 任一路径段 = `wiki` | `curated_final_summaries` 精选/最终摘要 |
| 6 | `catalog_final_artifacts` | 以 `.source_catalog/derived/` 或 `.source_catalog/artifacts/` 开头 | `curated_final_summaries` |
| 7 | `raw_tree` | 首段 ∈ {companies, sectors, themes, future_lake, source_manifests, source_provenance} | `raw_originals` raw/原始TXT/来源侧录 |
| 8 | `acquisition_staging` | 以 `.source_catalog/staging/` 开头 | `raw_originals` |
| 9 | `planning_docs_tree` | 首段 ∈ {.planning, docs} | `plans_reports` 计划/报告 |
| 10 | `operational_logs` | 首段 = `logs`，或 basename 以 `.log`/`.jsonl` 结尾，或 root 文件名以 `log` 开头 / 含 `_log.` | `plans_reports` |
| 11 | `plan_report_files` | basename 含 `receipt`；或 root 文件名含 `task_plan`/`report`/`plan`，或为 findings.md / progress.md / review_plan.md / review_queue.md / PLANNING_STATUS.md | `plans_reports` |
| 12 | `governance_evidence_dirs` | 首段 ∈ {artifacts, assurance, control, drills} | `plans_reports` |
| 13 | `repo_code_tree` | 首段 ∈ {.git, .githooks, .github, src, scripts, tests, tools, web, config, configs, examples, benchmarks} | `git_code` Git与已跟踪代码 |
| 14 | `repo_root_file` | root 级其余文件 | `git_code` |
| 15 | `unmatched` | 其余一切 | `unknown` 未知 |

原则：只凭可证的路径/manifest 类别分类；**不按扩展名把业务原件判为废料**；无法判断就
`unknown`。分类是存储维护层口径（报告里只用 root+相对路径），不验证 git tracked 状态
（已写入 limitations）；投资消费者仍走 `SourceRef`，不引入路径耦合。

## 保留建议（只建议，不执行）

| bucket | 覆盖 | 收益口径 / 成本 |
|---|---|---|
| `keep_now` 现在保留 | `raw_originals`、`curated_final_summaries`、`plans_reports`、`git_code`、非 tmp 的 `databases` | 无释放可计；原件永不进删除建议 |
| `separate_disposal_review` 可另开处置 | `tmp_test_cache`、tmp 树内的 `databases` | 收益口径 = `logical_path_bytes` 逻辑字节上界（allocated 未知、未做内容/重复验证）；需确认可重建且没有正在使用；此枚举沿用 schema 名称，不要求人工签收 |
| `undetermined` 无法判断 | `auto_recovery_materials`、`unknown`、全部 skipped 条目 | active/retry/prepared/未ACK 无法只读证实终态，**绝不凭 mtime 判断** |

本工具不实现 purge/hardlink/delete，不建状态库、不做审批签收。

## 报告 `cwp-storage-footprint/1`（≤256 KiB）

顶层键：`schema_version`、`scope`(project_root/started_at/finished_at/complete/stop_reason)、
`limits`、`totals`、`categories`(8 类固定)、`top_directories`(≤25，按子树逻辑字节降序)、
`retention_notes`(按 类别×分桶 聚合，含 reason/gain_basis/cost_or_condition)、
`errors`(≤200 条，路径硬截断 300 字符，诊断只含类型+errno，无机器绝对路径)、
`skipped_samples`(≤20 条，kind=reparse|cloud)、`calls`(恒为 0：original_body_reads/llm/network/deleted)、
`limitations`、`duplicate_path_links`。

超过 256 KiB 时按固定阶梯截断（错误列表 → top_directories → 理由文本 → 精简载荷）并在
`limitations` 追加 `report truncated ...`；仍超限则失败退出并清理临时文件。
写入是“临时文件 + 原子 replace”，且**绝不覆盖**非本工具 schema 的既有文件。

## 只读与副作用边界

- 只用 `os.scandir` + `lstat` 类 metadata；零 `open()` 被扫描文件（E2E 由 audit-hook 证明）。
- reparse（symlink/junction）与云占位（OFFLINE/RECALL_*/UNPINNED）不跟随、不 hydrate、不计量。
- 生产 SQLite 只按文件字节计量，从不 `sqlite3.connect`（Unit 有反例钉住）。
- 不读 `.env`、不读环境变量密钥；报告不落任何正文。
- 路径越界防护：输出路径与 root 重叠 → refused；不跟随任何出 root 的链接。

## 测试

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CW_BASETEMP_FALLBACK_ROOT=$PWD/tmp \
  python -m pytest -p no:cacheprovider --basetemp tmp/n6ft tools/storage_footprint/tests

python -m ruff check tools/storage_footprint
```

- `tests/test_storage_footprint_unit.py` — 口径/分类/预算/拒绝/截断/零正文读反例
- `tests/test_storage_footprint_fixture_integration.py` — 静态与运行时 fixture 精确合计
- `tests/test_storage_footprint_cli_e2e.py` — 真实子进程 CLI、audit-hook 零正文读、原状恢复

## 真实限额扫描

交付的真实小报告：`docs/implementation/handoffs/N6-FOOTPRINT/real_scan_report.json`
（保护前后指纹：同目录 `real_scan_protection.json`）。报告内 `scope` 标明测量窗口；
文件树在窗口内可能被其他并行 harness 改动，这不是文件系统原子快照。
