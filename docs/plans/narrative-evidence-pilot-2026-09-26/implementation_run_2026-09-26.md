# 实施运行卡：旧主库提前退役与后续选择性来源迁移

> **状态：本轮 F0–F5 已完成，run `20260926T170825Z-4a9c67e1`。** 用户授权并明确**不做完整落盘恢复备份演练**。本卡保留本次运行的原门禁与命令，收据结果见下节；后续 W/D 的审查节奏以 [G0–G4](milestone_review_cadence.md)为准。完成 F5 不等于 W/D 已实施。

## 0. 完成收据与剩余边界

- `prepared.json`：旧库 49,677,344,768 B / SHA `69f498a2…`；新库 3,055,796,224 B / SHA `63c359aa…`；完整 zstd 6,198,704,362 B / SHA `1bc09746…`。`zstd -t`、全量解压流 SHA/长度相等、逐表 digest、FK/quick_check 均通过。
- `evidence_audit.json` 与 `consumer_audit.json`：31 active、25 retired、5 其他非活跃 evidence 样本，6 组 query 与 12 组 no-download resolve 对照通过；18 个本仓/跨仓合同文件 SHA 冻结。真实下游业务流程未运行，不能把差分扩称全业务验收。
- `cutover.json`、`smoke_1.json`、`smoke_2.json`、`retired.json`：生产切到 active-only，烟测相隔 658.450 秒；旧库和原零 WAL/SHM 已按精确路径删除，Worker 仍 paused。准备前到清理后同卷可用空间净增 **37.630 GiB**。生产旧库真实切回未做，仅临时夹具验证回滚工具；完整备份落盘恢复按用户要求未做。
- 本轮在 46 GB 主库上多次全文件重哈希耗时偏高。未来同类迁移的审查频率已由 [大节点规则](milestone_review_cadence.md)精简；不能倒改本轮收据。

## 1. 本次范围与不可跨越项

- 操作根为当前 `C:/Users/郑曾波/Projects/company-wiki`；生产主库仅 `.source_catalog/catalog.sqlite3`，当前长度 49,677,344,768 B。保留 `.source_catalog/` 下控制、日志、`derived/`、`index/`、`source_manifests/`、`companies/` 全部原样；Worker 保持 `paused`。
- 另建同卷 `.source_catalog/retirement/<run_id>/`，含 `manifest.json`、版本化收据、完整压缩快照和影子库。不能把这一路径加入扫描输入根，不能触碰既有脏文件 `CLAUDE.md`、根 `README.md`、`artifact_dag.py`、`dayu_cli_adapter.py`。
- 备份验证只用：源库完整 SHA-256/长度、压缩文件 SHA-256/长度、`zstd -t`、**全量解压流** SHA-256/长度等于源库，以及对仍在原路径的源库只读 `PRAGMA quick_check` 和样例查询。解压流只进入 SHA 计算器，不写完整恢复文件。此法不验证未来机器的落盘恢复条件，收据必须明说。
- 所有文件切换/删除使用规范化绝对路径白名单、文件长度和 SHA，重读 Worker desired_state、WAL/SHM、operation.lock、源文件 stat；源有变化即停。F4 前必须有可执行的旧文件切回步骤和独立 query/CLI/下游差分。F5 仅在 F4 两次烟测、保留窗口、备份字节同一、旧文件身份不变后执行。

## 2. 任务顺序与收据

| 阶段 | 实施动作 | 必存证据/失败处理 |
|---|---|---|
| I0 计划与现状 | 更新 F2 无落盘恢复门禁；读取 Git dirty、配置、Worker pause、DB/WAL/SHM、operation.lock、schema/table/index 清单、源/文档状态、C 空间；固定 `run_id` | 任一 writer/锁/WAL 状态不明、pause 失效、schema 不符即停。原库只读不清理控制文件 |
| I1 读合同 | 在 `EvidenceQueryService` 增加 active-only 标记识别；对已存在但未复制的 non-active 文档/source 返回显式 `legacy_evidence_archived`（CLI 非重试错误），active 真缺失仍为 not found；用临时 SQLite 验证 | 不能把 retired 旧 locator 伪装成空结果。原 v1 完整库行为不变 |
| I2 影子库工具 | 新建版本化只读源/只写候选目标的 CLI；复制全部非 span 表、active span、原 DDL/索引，加入 `catalog_meta` 保留标记；逐表 row digest、active span digest/计数、FK/quick_check | 输入输出哈希/源 stat 稳定，主键与 active span 逐行一致；失败候选保持隔离并不切换 |
| I3 备份 | 在无写窗口向唯一 `.partial` 压缩，flush/fsync；源/压缩 SHA；`zstd -t` 和解压流长度/SHA；原库只读 `quick_check`；再原子发布压缩文件与 manifest | 不创建完整恢复库。源 stat/哈希或 WAL 变更、任一校验失败即停，不删旧库 |
| I4 差分 | 对完整旧库与影子库做目录、resolve、query、filing-fetch、active evidence 和 retired fail-close 的相同输入对照；检查 StockWiki/revenue-forecast/invest-quick-scan 当前消费合同 | 任何 active 身份/locator/正文不一致或 non-active 被报 not found 即停；差异原因和消费者读路径入收据 |
| I5 切换 | 逐项重验 I0–I4；写 `cutover-intent.json` 后精确 rename 零字节 WAL/SHM、旧 DB 为 `catalog.sqlite3.retiring.<run_id>`，再将 shadow rename 为主库；失败按反向顺序切回；运行两次间隔至少 10 分钟的烟测 | Worker 仍 paused，WAL/SHM 无意外，evidence/query/resolve 均正确；中断后依 intent 显式 rollback，不能静默续切 |
| I6 清理 | 再验旧文件绝对路径、长度、SHA 与冻结 manifest 一致，压缩包仍在且完整；写 `delete-intent.json` 后仅删除精确旧 DB 与其原侧文件；核实际同卷可用空间，写不可覆盖 receipt | 不能通配符/递归删除；若 unlink 后中断，用同一 intent 验证后只补清 sidecar/收据，不重新迁移；任何变化即停 |

## 3. 回滚、故障与验收

- I5 前回滚只需停用候选库；旧生产 DB/Worker 状态从未变。I5 后、I6 前，暂停读/写并把旧文件按 manifest 精确切回，影子库保留；不得覆盖仍打开的 SQLite 句柄。I6 后完整旧 DB 仅在压缩包里，恢复时须先按收据另外安排空间；本轮按用户要求不做落盘恢复演练。
- 必测：错误 source SHA、schema drift、WAL 出现、Worker 被恢复、锁占用、备份截断/单字节损坏、压缩流不匹配、影子库少 1 条 active span、retired 旧 locator、rename 中断、两次 F4 烟测间身份变化。F5 前至少运行实际可触发的失败关闭夹具；全库不可任意注入故障时用临时 DB。
- 通过收据含：输入/输出文件 path、size、SHA，schema/index/table row/digest，active span count/digest，FK/quick_check，备份 `zstd -t`/解压流 length/hash，Worker pause/WAL/锁，query/下游差分，C 盘前后空闲，命令/退出码和时间；审查者按真实收据确认。**没有完整落盘恢复测试**需在风险栏保留。
- I6 完成仅解决旧 DB 占用。新 pipeline 要在 W0 冻结质量/空间合同后按 W1–W7 做小样本与多文档 Worker；不重要来源的原文删除继续按 D0–D5，不自动跟随 F6 或 `skipped_*`。

## 4. 本轮可执行命令与停机点

**以下是已执行的历史命令记录，不得重跑同一 run。** `run_id=20260926T170825Z-4a9c67e1` 的各收据已发布，旧库已删除。执行时每个命令只在前一个收据存在、`status=passed` 且输入 SHA 相同后运行；工具 stdout JSON 未代替落盘收据。用户排除完整恢复演练，没有执行任何 `zstd -d -o <46GiB 文件>` 步骤。

```powershell
python scripts/retire_source_catalog_db.py --project-root . --run-id 20260926T170825Z-4a9c67e1
python scripts/audit_catalog_retirement.py .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json --output .source_catalog/retirement/20260926T170825Z-4a9c67e1/evidence_audit.json
python scripts/audit_catalog_consumers.py .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json
python scripts/cutover_source_catalog_db.py cutover .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json
python scripts/cutover_source_catalog_db.py smoke-1 .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json
# 至少间隔 10 分钟，期间重核 Worker paused、WAL 与读路径；不可立即制造第二张烟测收据。
python scripts/cutover_source_catalog_db.py smoke-2 .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json
python scripts/cutover_source_catalog_db.py retire .source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json
```

- F0–F2 脚本只创建隔离候选和压缩备份；`prepared.json` 最后才发布，失败不得切换。F3 审计遇到 active 内容差异、retired 无明确归档错误、resolver/query 差异或 StockWiki provider 状态变化，停止并保留旧主库；不得手写 `passed` 收据。
- `cutover-intent.json` 存在而 `cutover.json` 不存在，或者切换烟测失败时，先核确切路径与文件 SHA，再运行 `python scripts/cutover_source_catalog_db.py rollback <prepared.json>`。切回后此 run 不得再次用于切换，另起新 run 重新准备。
- `delete-intent.json` 一旦出现，禁止执行 rollback；如果旧 DB 已删除而 `retired.json` 缺失，只能按相同 `retire` 命令继续核对压缩备份、新主库、侧文件并补齐收据。任何路径/哈希不符时停，不手动通配符清理。
- 预切换测试：`python -m pytest tests/unit/test_retire_source_catalog_db.py tests/contract/test_source_catalog_evidence_query.py tests/unit/test_error_taxonomy.py -q`；生产读路径与备份按实际 F2/F3 收据复核。夹具测试只证明工具故障行为，不能替代真实来源差分。
