# N6-FOOTPRINT HANDOFF — 实际空间占用与保留状态只读盘点工具

lane_id: `N6-FOOTPRINT` · branch: `codex/n6-footprint`（base `ec7a573`，其上为卡基线 `58b74d07dd4f8b589c134ef9060a689864a8c089` 的 INPUT_CARD/PWF 启动提交）· delivery_head: `ba195710b95878ededbe1a60ca0bc569bf740bcc` · worktree: `C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-footprint` · date: 2026-10-06

**done 的含义**：工具可信 + 一次真实限额扫描 + 小报告交付。**不等于空间已释放**（`deleted=0`，本工具不执行任何处置）。

## 交付物

- `tools/storage_footprint/` — `core`（预算/身份/reparse/原子写/截断）、`classify`（互斥路径规则 + 保留分桶）、`scan`（确定性 DFS、只读 metadata）、`report`（schema 组装/校验/256KiB 阶梯截断）、`runner`（拒绝/失败语义）、`run`（CLI）、`README.md`（口径与分类表）
- `tools/storage_footprint/tests/` — 28 unit 反例 + 4 fixture integration + 8 子进程 E2E（含 `e2e_hook/sitecustomize.py` audit-hook 零正文读证明）、静态小 fixture（7 个文件，`raw`/`tmp`/`*.pdf` 全避开 gitignore）
- `docs/implementation/handoffs/N6-FOOTPRINT/real_scan_report.json` — 真实限额扫描报告（13,717 B ≤ 256 KiB）
- `docs/implementation/handoffs/N6-FOOTPRINT/real_scan_protection.json` — 扫描前后保护指纹收据
- `.planning/n6-footprint/{task_plan,findings,progress}.md` — 三 PWF（口径/分类表、真实结果、错误台账）

## 入口（精确命令）

```text
python tools/storage_footprint/run.py --project-root 'C:/Users/郑曾波/Projects/company-wiki' --max-files 100000 --max-seconds 60 --output '<新报告.json>'
```

退出码：`0` = 报告已写（`complete` 或显式 `partial`）；`2` = refused（root 缺失 / 限额 ≤0 / 输出与 root 重叠 / 输出已存在且非本工具 schema，**不写任何文件**）；`1` = 内部失败（临时文件清理、目标不存在）。stdout 为单行 JSON。

## 测试 / RED / GREEN

| 项 | 结果 |
|---|---|
| RED（实现前，Unit） | `collected 0 items / 1 error` — `ImportError: cannot import name 'classify'`，0.43 s |
| GREEN（Unit 28 项） | 28 passed / 2.14 s |
| 收口全量 | `40 passed / 2.53 s`（final 复跑同命令） |
| `ruff check tools/storage_footprint` | All checks passed |
| `git diff --check` | OK |
| 真实限额扫描 | exit 0，23.363 s（窗口 2026-10-06T22:19:19Z..22:19:42Z） |

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CW_BASETEMP_FALLBACK_ROOT=$PWD/tmp python -m pytest -p no:cacheprovider --basetemp tmp/n6ft tools/storage_footprint/tests
python -m ruff check tools/storage_footprint
```

未改 `tests/`、`pytest.ini`、`pyproject.toml`、CI 或任何 src/；不测试真实 ACL（权限错误用 mock 注入）。

## 报告 schema

`cwp-storage-footprint/1`（≤256 KiB）：`scope{project_root,started_at,finished_at,complete,stop_reason}`、`limits`、`totals`（`allocated_bytes` 恒 null）、`categories`（8 类固定）、`top_directories`(≤25)、`retention_notes`、`errors`(≤200、路径 300 字符硬截断、诊断无机器绝对路径)、`skipped_samples`(≤20)、`calls`(恒 0)、`limitations`、`duplicate_path_links`。保护收据 schema `cwp-storage-footprint-protection/1`。

## real vs fixture

- **真实**：`C:/Users/郑曾波/Projects/company-wiki` 单根，`complete=true`、`stop_reason=complete`（100000 文件与 60 秒预算均未触顶）、`entries_seen=58309`、`files_measured=54129`、`logical_path_bytes=24364743714`、`errors=0`。
- **fixture**：静态 7 文件 + 运行时 11 文件树，全部在 pytest basetemp 内构建/读取，测试后随会话清理；E2E 以真实子进程跑 CLI。

## 完整 / partial 口径

本次为**完整扫描**（`complete=true`）。若触预算则 `stop_reason=budget`、`complete=false`，totals 只覆盖已访问部分并在 limitations 标 `partial scan`，绝不外推成全量。目录遍历错误 → `stop_reason=errors` + `complete=false`。报告声明测量窗口，**不是文件系统原子快照**（两线共享 Git 对象，树可并发变化）。

## 分类与分桶（本目录实测）

| 类别 | 文件 | 逻辑字节 | 分桶 |
|---|---|---|---|
| raw_originals 原件/来源侧录 | 32301 | 23462933638 | 现在保留 |
| curated_final_summaries 精选/最终摘要 | 45 | 2002021 | 现在保留 |
| databases（非 tmp / tmp 内） | 11 / 16 | 247042048 / 45232912 | 现在保留 / 可另开处置 |
| auto_recovery_materials AUTO 材料 | 272 | 4591209 | 无法判断 |
| tmp_test_cache tmp/测试/缓存 | 11809 | 273801070 | 可另开处置 |
| plans_reports 计划/报告 | 930 | 86101872 | 现在保留 |
| git_code Git与代码 | 5060 | 236179365 | 现在保留 |
| unknown 未知 | 3685 | 6859579 | 无法判断 |

收益口径：`separate_disposal_review` 合计 **273801070 + 45232912 = 319033982 逻辑字节上界**（allocated 未知、无内容/重复验证、非已确认可删）；成本 = 需独立处置审批与重建/可用性评估。**不自动执行**。

## 保护与只读

- 前后指纹一致（`real_scan_protection.json`）：`config/source_catalog.yaml`+`config.yaml` sha256、`.source_catalog/catalog.sqlite3{-wal,-shm}` stat、`.source_catalog` 目录列表、5 份跨公司原件 metadata（`Alphabet/AMD/Apple/MICROSOFT/MongoDB`）全部 unchanged。
- `original_body_reads=0`（原件只取 metadata）；E2E 用 audit-hook 证明扫描进程对 root 内普通文件 `open` 事件为 0；生产 SQLite 从不 `connect`；reparse/云占位不跟随不 hydrate（1007 条 kind=cloud 已列样本）；不读 `.env`/环境密钥。
- `calls` 恒 0：`original_body_reads/llm/network/deleted` 全 0；原件删除 0。

## 清理

- `tmp/n6-footprint/` 已删除回原样；pytest basetemp 由根 conftest 会话后清理；无 `*.tmp` 残留（写入为临时文件+原子 replace，失败即清理）。
- 源仓与 owner 生产文件零写（本线曾在源仓误建 fixture 目录，已即时删除并复核 `git status`）；其他 worktree / RF / ET / StockWiki / IQS / Dayu 零写。
- 未新增常驻监控、自动化、清理命令或状态库；无新许可/签收。

## open_items（MAIN 验收后决定）

1. 是否为 `tmp_test_cache`（273,801,070 B）+ tmp 内 databases（45,232,912 B）另开处置审批；本工具只给上界与成本，不执行。
2. 1007 条 OneDrive UNPINNED 云占位 PDF 未计量（不 hydrate），其本地占用/逻辑量是否另行补齐需产品决定。
3. `unknown` 3,685 文件（6,859,579 B）与 `.state`/`.ingested`/`.verification` 等布局可随存储层演进补充规则，本线不外推。
4. 根目录误建的 `nul` 设备伪文件（0 B、`st_ino=0`）属源仓杂物，不在本线处置范围。
5. 本工具不阻候选/预算两线质量节点；`allocated_bytes` 仍为 null，任何磁盘收益结论需另有实证 API。
