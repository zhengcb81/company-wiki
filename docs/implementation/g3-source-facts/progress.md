# G3-SOURCE-FACTS — 进度日志（progress）

## Session 1（2026-10-07，UTC 11:5x–12:4x）

| 时间线 | 动作 | 结果 |
|---|---|---|
| 0 | 读卡、`git status`/`worktree list`，确认基线与他人 lane 未提交改动 | 互不包含 |
| 0 | `git worktree add -b codex/g3-source-facts <lane> 5930a64…` | worktree 就绪，HEAD=5930a64 |
| 0 | 记录生产 `config/source_catalog.yaml` SHA256 | `3d159a4e…e3f968` |
| 0 | 只读探 DB：8 样本 location/source/document、retire audit、roots 计数 | 见 findings §3 |
| 1 | 先写反例测试 + 实现 `tools/g3_source_facts/{budget,proposals,raw_space,catalog_probe,report,cli}` | `pytest tools/g3_source_facts/tests` → **47 passed**（随后 48） |
| 2 | `hash_and_cover.py`：9 份 stream hash + 封面/头部抽页（预算 75,886,072 B） | 9/9 SHA 与 `samples.json` 一致 |
| 2 | CNINFO 只读检索 8 次 + 重试 5 次；SZSE 官方 API 2 次 500 → 停止重试 | S01–S06 公开日核定；S07/S08 保留 unknown/conflict |
| 2 | 汇总证据 → `tools/g3_source_facts/data/evidence_input.json` → `cli.py proposals` | `metadata_proposals.json`：4 do_not_reactivate / 3 update_metadata / 1 unresolved / 1 register_new |
| 3 | SourceRef（S07 pathless）+ 零模型 skip 候选（P09 ir_policy）与九样本缺口 | 见 evidence_index §2/§3 |
| 4 | 离线夹具证明配置过滤（`test_rawdup_config_filter.py`） | `scan_scope.roots=[company_raw]`；外根文件 0 hash |
| 4 | scratch 调查配置（只含 company_raw、catalog_dir 绝对指生产库）→ RAW-DUP `scan` → `verify` | scan 49.457 s / verify 60.011 s，`succeeded`，`read_bytes=122,369,272` |
| 4 | `metadata_bound.py` 只读 SQL 聚合注册上界 | 52 组 / 98,845,393 B |
| 4 | `cli.py raw-space` → `raw_space_decision.json` | `no_migration_recommended`，`deleted_bytes=0` |
| 5 | 集中验证：责任测试 + 生产 config/原件/DB 复核 | `pytest -q tools/g3_source_facts/tests` → exit 0 / 55 passed / 7.2 s；config SHA 不变；9 样本 bytes+SHA 全一致；DB `total_changes=0`、8 样本状态不变 |
| 6 | `HANDOFF.md` + `evidence_index.md` + `handoff.json`，清理 scratch，分两次 commit | 见 HANDOFF §5 |

### 集中验证（Phase 5）
- 责任测试：`python -m pytest -q tools/g3_source_facts/tests` → **55 passed**，exit 0
- 生产配置字节：见 HANDOFF `protected_state`
- 九样本复核：见 HANDOFF `protected_state`
- DB 只读关键事实复核：见 HANDOFF `protected_state`

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| `rg` 不可用（bash） | 1 | 改用 Grep 工具 / python 脚本 |
| python `-c` 内 `C:\` 转义导致 SyntaxError | 2 | 改写成 scratch 内脚本文件执行（不重复同一失败动作） |
| 提案首次生成 3 项 `unresolved`（非预期） | 1 | 定位为 `official_size_kb` 证据缺 url 触发 `verified_evidence_missing_url`；补 6 条 url 后复现 3 update_metadata |
| `test_repeated_reads_are_charged_again` 语义自相矛盾（超预算既要求 raise 又要求计入） | 1 | 重新定义：超额 charge 抛 `BudgetExceeded` 且不计入 consumed；测试改为“重复读要记账、超预算即停” |
| CNINFO fulltext/hisAnnouncement 查不到 S07/S08 记录表；SZSE 官方 API 500 | 3 次有界尝试 | 按卡保留 unknown/conflict，停止重试，不下载整份 PDF 证明日期 |
| `truncated.dropped_groups_by_row_cap=3505`：报告只列 45/26 组 | 1 | 注册上界改由只读 SQL 元数据聚合提供（0 文件读），报告列示覆盖度与截断事实 |

## Files Created / Modified

- 新增（本卡写集）：`tools/g3_source_facts/**`（含 `tests/`、`data/evidence_input.json`）
- 新增：`docs/implementation/g3-source-facts/{task_plan,findings,progress,evidence_index,HANDOFF}.md`、`metadata_proposals.json`、`raw_space_decision.json`、`handoff.json`
- 临时（已清理）：`.planning/g3-source-facts/scratch/**`
- 未触碰：`src/**`、`config/**`、`tools/raw_duplicate_audit/**`、生产 `companies/**`、生产 SQLite/sidecar、ET 目录、总 PWF

## 集中验证结果（Phase 5 实测）

- `python -m pytest -q tools/g3_source_facts/tests` → **exit 0，55 passed，7.2 s**
- 生产 `config/source_catalog.yaml`：`3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`（前=后）
- 9 份原件：bytes/SHA 与 `samples.json` 前后全一致
- 生产 DB（mode=ro + query_only，单读事务）：schema 1.2.0、sources 43112、locations 46606、documents 23530、status active 25048/missing 6/quarantined 1/retired 21551、`total_changes=0`、db 222408704 B、`-wal` 0 B、`-shm` 32768 B；8 样本 location/document 状态与开工一致
- 外部效应：public_http_requests=15、downloads=0、read_bytes=236,198,380、model_posts=0、production_writes=0、raw_deleted=0
- 清理：`.planning/g3-source-facts/scratch` 已整目录删除；无原文/渲染/临时副本入库

## Next Step

交接完成；等待 MAIN 复核并经正式入口应用。
