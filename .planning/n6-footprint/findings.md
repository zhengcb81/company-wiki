# N6-FOOTPRINT Findings

准备时已绿基线58b74d0；准确背景、接口、source路径与真实点见INPUT_CARD。本文件记录本线实测口径/分类表（INPUT_CARD 第1步要求），实现只依据该表。

## 实测口径（measurement definitions）

| 量 | 定义 | 备注 |
|---|---|---|
| `entries_seen` | 扫描到的全部目录条目（文件、目录、reparse/链接） | 预算停止时为已访问部分 |
| `directories_seen` | 实际进入的普通目录数 | reparse 目录不进入 |
| `files_measured` | 经 metadata 取得逻辑大小并计入合计与分类的文件数 | 只 stat，零正文读 |
| `logical_path_bytes` | Σ 文件逻辑大小（lstat `st_size`），按路径计量 | 硬链接/稀疏/压缩使其 ≠ 磁盘分配量 |
| `allocated_bytes` | 恒 `null` | 本平台无可靠 metadata-only 分配量 API；不用 cluster 估算，不用 GetCompressedFileSizeW 冒充 |
| `skipped_*` | 未跟随、未 hydrate 的 reparse/链接/云占位条目（样本 ≤20 条见 `skipped_samples`） | 不计入 files_measured 与分类，保留态=undetermined |
| `unknown_files` | 已实测但落入 unknown 类的文件数 | |
| `duplicate_path_links` | 仅用 st_dev+st_ino metadata 判定的同文件多路径 | 候选口径，未做内容验证，不计入任何“可删收益” |

一致性恒等式（Unit 断言）：`Σ categories.files == files_measured`；`Σ categories.logical_path_bytes == logical_path_bytes`；`skipped_links + skipped_cloud == skipped_files`。

## 分类表（互斥路径规则，自上而下首条命中；只作用于文件路径，root 相对 POSIX 路径）

| # | rule id | 命中条件 | 类别 |
|---|---|---|---|
| 1 | `auto_store_material` | 位于直接含有 `automation.*` 文件的目录之下（含该目录自身） | auto_recovery_materials（恢复中的AUTO任务材料） |
| 2 | `db_file` | basename 以 `.sqlite`/`.sqlite3`/`.db` 或其 `-wal`/`-shm`/`-journal` 组合结尾 | databases（数据库/WAL/SHM） |
| 3 | `tmp_tree` | 任一路径段 ∈ {tmp, .tmp, .tmp-e2e, __pycache__, .pytest_cache, .ruff_cache, .mypy_cache, .venv, node_modules, build, dist, .codegraph, .mimocode}，或 basename = `.coverage`，或 basename 以 `pytest-` 开头 | tmp_test_cache（tmp/测试/缓存） |
| 4 | `derived_index_sidecar` | root 级点文件：名字以 `.tmp` 开头，或以 `_index.json` / `_db.json` 结尾（gitignore 标注可重建/临时） | tmp_test_cache |
| 5 | `wiki_pages` | 任一路径段 = `wiki` | curated_final_summaries（精选/最终摘要） |
| 6 | `catalog_final_artifacts` | 路径以 `.source_catalog/derived/` 或 `.source_catalog/artifacts/` 开头 | curated_final_summaries |
| 7 | `raw_tree` | 首段 ∈ {companies, sectors, themes, future_lake, source_manifests, source_provenance} | raw_originals（raw/原始TXT/来源侧录） |
| 8 | `acquisition_staging` | 路径以 `.source_catalog/staging/` 开头 | raw_originals |
| 9 | `planning_docs_tree` | 首段 ∈ {.planning, docs} | plans_reports（计划/报告） |
| 10 | `operational_logs` | 首段 = `logs`，或 basename 以 `.log`/`.jsonl` 结尾，或 root 级文件名以 `log` 开头 / 含 `_log.` | plans_reports |
| 11 | `governance_evidence_dirs` | 首段 ∈ {artifacts, assurance, control, drills} | plans_reports |
| 12 | `plan_report_files` | basename 含 `task_plan`/`report`/`receipt`，或为 findings.md / progress.md / review_plan.md / review_queue.md / PLANNING_STATUS.md | plans_reports |
| 13 | `repo_code_tree` | 首段 ∈ {.git, .githooks, .github, src, scripts, tests, tools, web, config, configs, examples, benchmarks} | git_code（Git与已跟踪代码） |
| 14 | `repo_root_file` | root 级（无路径段）其余文件 | git_code |
| 15 | `unmatched` | 其余一切（非 root 级未匹配文件） | unknown（未知） |

原则：只凭可证的路径/manifest 类别分类；不按扩展名把业务原件判为废料；无法判断就 unknown。分类规则是存储维护层口径（报告内用 root+相对路径），不验证 git tracked 状态（写入 limitations），投资消费者仍走 SourceRef。

## 保留建议分桶（不执行任何处置）

| bucket | 覆盖 | 理由 |
|---|---|---|
| `keep_now`（现在保留） | raw_originals、curated_final_summaries、plans_reports、git_code、非 tmp 的 databases | 原件/来源侧录零删除；final 与计划报告是读取与审计材料；生产库与 WAL/SHM 属运行时 |
| `separate_disposal_review`（可另开处置） | tmp_test_cache；位于 tmp 树内的 databases | 仅逻辑字节上界，需另开处置审批与重建成本评估；本工具不执行 |
| `undetermined`（无法判断） | auto_recovery_materials、unknown、全部 skipped 条目 | active/retry/prepared/未ACK 无法只读证实终态，绝不凭 mtime 判；原件永不进入删除建议 |

## 已知背景（引用已提交事实，不复做）

- S5 收据 `harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json`：DB 3055841280→222408704 B、净释放 5659443210 B、原件删除 0、derived 归零。
- N5-DUP 的 7.27GiB 是跨根 exact-SHA 候选上界（仅 3 组 151MiB 实读），不等于本目录占用；本线不做 SHA 长测、不读正文。
- 真实扫描是 60 秒/100000 文件限额下的部分或完整结果，报告必须显式区分，不冒充文件系统原子快照；两线共享 Git 对象，扫描期间树可能变化。

## 真实限额扫描结果（2026-10-06 交付）

命令：`python tools/storage_footprint/run.py --project-root 'C:/Users/郑曾波/Projects/company-wiki' --max-files 100000 --max-seconds 60 --output <lane tmp>`（随后移入 handoff 目录、tmp 删除回原样）。

- `complete=true` / `stop_reason=complete`，窗口 `2026-10-06T22:19:19Z..22:19:42Z`（约 23.4 秒），`files_measured=54129`，`logical_path_bytes=24364743714`（≈22.7 GiB 逻辑量），`errors=0`，报告 13717 B ≤ 256KiB。
- 分布：raw_originals 23462933638 B（96.30%，32301 文件）> git_code 236179365 B > databases 292274960 B > tmp_test_cache 273801070 B（11809 文件）> plans_reports 86101872 B > unknown 6859579 B（3685 文件）> auto_recovery_materials 4591209 B > curated_final_summaries 2002021 B。
- 分桶：keep_now = raw/curated/plans/git_code + 非 tmp 数据库 247042048 B（11 文件）；可另开处置 = tmp_test_cache 273801070 B + tmp 内数据库 45232912 B（16 文件）；无法判断 = auto 4591209 B + unknown 6859579 B + 1007 个 skipped 条目。
- skipped 1007 条全部 kind=cloud（样本为 `companies/*/raw/**.PDF`，OneDrive UNPINNED 在线占位），不 hydrate、不计量；跳过量已在 limitations 与 skipped_samples 显式列出，不冒充全量。
- 身份口径：`identity_known_files=54128/54129`，唯一未知是根目录误建的 `nul` 设备伪文件（`st_ino=0`）；同文件多路径组 = 0（未发现硬链接别名），`allocated_bytes=null`。
- 保护前后（`real_scan_protection.json`）：config sha256、生产库 catalog.sqlite3/-wal/-shm stat、`.source_catalog` 目录列表、5 份跨公司原件 metadata 全部一致，原件内容读 0、calls 全 0。
- 这些是**当前目录的逻辑占用口径**，不是磁盘释放量，也不等于 catalog 登记量或 N5-DUP 候选上界。
