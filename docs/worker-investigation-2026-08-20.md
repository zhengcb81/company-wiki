# Source Catalog Worker 异常与性能调查报告

> 调查日期：2026-08-20（Europe/London）  
> 调查对象：`company-wiki` Source Catalog 后台 worker、supervisor、登录启动链、SQLite catalog 与相关运行状态  
> 调查方式：先进行完全只读的代码、日志、数据库查询计划和现场性能采样；在用户明确授权后，执行持久暂停和移除登录自启动  
> 报告状态：最终版，可供后续修复、验证和恢复运行时参考

## 1. 执行摘要

调查已经确认：2026-08-12 之后持续运行不正常的主要原因，不是文件解析器、LLM、SQLite 写锁、内存不足或 SSD 性能不足，而是 8 月 12 日引入的一条正常化队列 SQL 在生产数据规模上发生了严重查询计划退化。

提交 `0ee0d09dfcbc8d5bbac4f17666c09df910d17558` 于 2026-08-12 00:22:39 +01:00 为正常化队列增加了一个相关 `EXISTS` 子查询，用来跳过没有有效 `original_primary` 位置的文档。业务意图正确，但生产 SQLite 在没有统计信息、也没有匹配复合索引的情况下，为子查询选择了 `idx_locations_status(location_status)`，导致它对约 23,530 个文档反复遍历约 25,046 条 active location，并在最后使用临时 B-tree 排序。实际复杂度接近二次方。

现场证据表明：

- worker 长期停在 `normalizing / selecting next document`；
- `parser_pid=null`，说明文档解析尚未开始；
- 单个 worker 持续占用一个逻辑 CPU 核心的约 96.8%；
- 工作集只有约 90.9 MiB，内存不是瓶颈；
- 进程逻辑读取非常高，但物理磁盘利用率低于 3%，说明是 SQLite 在系统缓存中重复遍历，而不是 SSD 吞吐受限；
- 真实 worker 在队列选择上运行超过 902 秒仍未返回，被 watchdog 杀死；
- 同一生产库上，等价非相关查询只需 0.231 秒返回相同的前三个文档。

这个 SQL 回归又被三个控制面缺陷放大成永久重启循环：扫描状态只在完整周期末尾落盘、SQL 期间没有 heartbeat、进程存活超过 900 秒就清零连续失败次数。因此每次重启都会等待 120 秒、重新扫描约 46,600 个文件、在同一 SQL 上耗满一个核心 900 秒、被杀死，再以 5 秒延迟重启；实际产出为零。

在用户授权后，已完成以下隔离动作：

1. 使用项目控制面执行持久暂停，`desired_state=paused`；
2. 当前生产 worker 已停止；
3. supervisor 已退出；
4. launcher 记录退出原因 `persistent_pause`；
5. 已删除 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 下唯一的 `CompanyWikiSourceCatalog` 值；
6. 已复核：没有对应的计划任务或 Windows 服务。

因此，下次用户登录或开机后不会自动启动这个 worker。VBS、PowerShell 和 Python 脚本均未删除，未来修复并验证后可以按本报告第 17 节恢复。

## 2. 调查范围与约束

本次覆盖：

- 自动启动方式、启动时机和启动链；
- 生产 worker、supervisor、可能的 parser 子进程；
- 2026-08-12 前后的提交、运行记录、watchdog 和重启时间线；
- 正常化、扫描、指纹、章节、LLM 摘要、导出等阶段；
- CPU、内存、线程、进程逻辑 I/O、物理磁盘 I/O；
- SQLite 表规模、索引、查询计划和等价只读查询；
- 对源文件、外部目录、隐私、磁盘和维护任务的风险；
- 修复顺序、验收标准和恢复运行步骤。

调查期间遵守以下边界：

- 在用户授权暂停之前，不停止、不重启、不修改 worker；
- 不执行 `ANALYZE`、`PRAGMA optimize`、`VACUUM`、建索引或迁移；
- 不运行会写生产 catalog 的测试或项目命令；
- 不修改生产配置；
- 不生成 `task_plan.md`、`findings.md`、`progress.md`，避免与另一个任务冲突；
- 不触碰另一个任务产生的 `.coverage`、`coverage.json` 等文件；
- 只新增本报告一份文档。

## 3. 当前隔离后的状态

2026-08-20 22:43:39 左右执行持久暂停后，控制面返回：

```text
Auto-start : ON (current_user_run_registry)   # 这是删除注册表前的瞬时状态
User mode  : PAUSED
Process    : STOPPED
Supervisor : NOT RUNNING
Launcher   : exited | reason=persistent_pause | child_pid=23536 | attempt=44 | exit=2
```

随后删除了注册表自启动值。删除前的原值为：

```text
"C:\WINDOWS\System32\wscript.exe" //B //Nologo \
"C:\Users\郑曾波\Projects\company-wiki\scripts\source_catalog_worker_at_logon.vbs" \
"C:\Miniconda\python.exe" \
"C:\Users\郑曾波\Projects\company-wiki"
```

删除后：

- `CompanyWikiSourceCatalog` 注册表值不存在；
- 无匹配计划任务；
- 无匹配 Windows 服务；
- 当前没有生产 source-catalog worker 或 supervisor 进程。

暂停时发现 `.source_catalog/operation.lock` 仍记录已退出的 PID 23536，控制面判定为 `stale / not_live`。本次没有手工删除该锁。正常的锁获取逻辑应在未来启动时验证 PID 身份并处理 stale lock；如果未来恢复时仍受阻，应先用控制面状态和锁身份检查处理，不应盲目删除。

## 4. 系统启动链与是否每次开机运行

调查前，唯一的自动启动入口位于当前用户注册表：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
  CompanyWikiSourceCatalog = <上述 wscript 命令>
```

完整链路是：

```text
用户登录 Windows
  -> HKCU Run
  -> wscript.exe //B //Nologo
  -> scripts/source_catalog_worker_at_logon.vbs
  -> 登录 PowerShell 启动器
  -> scripts/source_catalog_worker.ps1 supervisor
  -> C:\Miniconda\python.exe
  -> company_wiki.source_catalog.cli worker
```

因此，原来的行为是“每次该用户登录后后台自动运行”，不是在登录前由 Windows 服务启动。worker 子进程还有 120 秒启动延迟。

调查没有发现：

- 对应的 Windows 服务；
- 对应的计划任务；
- 第二个 Startup 文件夹入口。

注册表项现已删除，所以未来开机/登录不会沿这条链路启动。

## 5. 生产配置与工作方式

关键配置来自 `config/source_catalog_worker.yaml`：

- schema：1.3；
- 扫描间隔：1 小时；
- 导出间隔：1 小时；
- 正常等待轮询：30 秒；
- 有生产性工作时轮询：2 秒；
- `require_user_idle=false`；
- `allow_processing_on_battery=false`；
- normalize batch：3；
- fingerprint batch：3；
- section batch：5；
- LLM summary batch：1；
- 文档 parser timeout：3,600 秒；
- parser heartbeat：15 秒；
- parser IPC 结果最大值：256 MiB；
- worker watchdog：900 秒；
- 登录启动延迟：120 秒；
- retention prune：90 天、每周一次。

生产扫描根来自 `config/source_catalog.yaml`，包括：

- 仓库内 `companies`；
- `../dayu-agent/workspace/portfolio`；
- `C:\Users\郑曾波\Dropbox\Stock`；
- future lake 目录。

worker 为单线程顺序流水线。项目规范明确说明 `LLMClient` 含有全局/限流状态，不是线程安全的；不能在不重构的情况下直接通过线程并发提高 LLM 吞吐。

## 6. 2026-08-12 回归时间线

### 6.1 代码变化

2026-08-12 00:22:39 +01:00，提交：

```text
0ee0d09dfcbc8d5bbac4f17666c09df910d17558
fix(fc-906-c): normalize queue skips docs without active primary location
```

该提交的背景是：生产库中约 9,506/23,521 个文档没有 active location，旧队列会反复选择它们并失败。修复增加了 active `original_primary` 的 `EXISTS` 过滤，功能方向正确，但没有生产规模的查询计划或耗时测试。

### 6.2 可见性能断点

从 `worker_runs.jsonl` 计算的周期间隔：

| 时间窗口 | 周期数 | 中位周期 | P90 | 最大值 |
|---|---:|---:|---:|---:|
| 8 月 12 日 00:00–01:30 | 82 | 54.4 秒 | 105.8 秒 | 548.5 秒 |
| 8 月 12 日 01:37–13:32 | 55 | 749.2 秒 | 957.7 秒 | 1,902.5 秒 |

8 月 11 日整体周期中位数约 33.9 秒、P90 约 76.3 秒。8 月 12 日新逻辑进入运行后，周期中位耗时上升约一个数量级。

### 6.3 最后一次完整成功周期

最后一个完整周期：

```text
周期开始：2026-08-12 13:20:49
状态/日志落盘：2026-08-12 13:32:25
总耗时：约 696 秒
```

分阶段重建：

| 阶段 | 证据时间 | 近似耗时 | 占比 |
|---|---|---:|---:|
| 扫描 46,575 个文件 | state 记录 38.39 秒 | 38.39 秒 | 5.5% |
| normalize 队列 SQL | 扫描结束至首个产物 13:31:37 | 约 610 秒 | 87.6% |
| 解析 3 个 HTML 文档 | 三个 artifact 在 13:31:37–13:31:38 创建 | 约 1 秒 | 0.1% |
| 1 个 LLM 摘要 | summary artifact 在 13:32:20 创建 | 约 42 秒 | 6.0% |
| 导出、状态和日志 | 最终落盘 13:32:25 | 约 5 秒 | 0.7% |

这证明慢的不是 parser；队列 SQL 在 parser 启动前已经消耗绝大部分时间。

### 6.4 进入持续失败

- 最后一次成功状态写入：2026-08-12 13:32:25；
- 新受监督 worker 会话于当日晚间启动；
- 第一次明确 `heartbeat_timeout`：2026-08-12 20:08:32；
- 此后持续重复 `normalizing / selecting next document` 超时。

相关日期的 watchdog timeout 数量显示它已经成为稳定模式：

| 日期 | timeout 数量 |
|---|---:|
| 2026-08-12 | 15 |
| 2026-08-13 | 38 |
| 2026-08-14 | 32 |
| 2026-08-16 | 6 |
| 2026-08-17 | 16 |
| 2026-08-18 | 14 |
| 2026-08-19 | 45 |
| 2026-08-20（暂停前） | 42 |

8 月 12 日之前也出现过少量 timeout，因此 watchdog/运行环境此前并非完全无异常；但从 8 月 12 日新查询进入生产后，失败阶段、进度文案和重启周期高度一致，形成了现在的持续故障。

### 6.5 同日另一项独立异常

8 月 12 日 01:35–13:37，某个 supervisor 会话反复启动短命子进程，stderr 明确记录：

```json
{"error":"source-catalog worker is already running","error_type":"RuntimeError","status":"failed"}
```

当时另一个持有实例锁的 worker 仍在产生成功周期。因此这是重复实例/控制面噪声，不是当前晚间以后持续卡死的主因。暂停前现场只存在一个生产 supervisor 和一个生产 worker，没有重复生产实例。

## 7. 根因 SQL、索引与查询计划

核心查询位于：

```text
src/company_wiki/source_catalog/normalizer.py:1560-1587
```

关键结构：

```sql
SELECT d.*, s.content_sha256, s.byte_size, s.mime_type,
       existing.metadata_json AS normalization_metadata_json
FROM documents d
JOIN sources s ON s.source_id = d.primary_source_id
LEFT JOIN artifacts existing
  ON existing.document_id = d.document_id
 AND existing.artifact_role = 'normalized'
 AND existing.generator_name = ?
 AND existing.generator_version = ?
WHERE EXISTS (
    SELECT 1
    FROM locations lp
    JOIN roots rp ON rp.root_id = lp.root_id
    WHERE lp.document_id = d.document_id
      AND lp.role = 'original_primary'
      AND lp.location_status = 'active'
)
AND (...existing artifact retry filter...)
ORDER BY <document priority CASE>, d.document_id
LIMIT 3;
```

生产表规模：

| 表/集合 | 行数 |
|---|---:|
| documents | 23,530 |
| locations | 46,606 |
| active locations | 25,046 |
| active original_primary | 16,989 |
| sources | 43,112 |
| artifacts | 7,962 |
| roots | 4 |

相关索引：

```text
idx_locations_document(document_id)
idx_locations_status(location_status)
idx_locations_root_role_status(root_id, role, location_status)
sqlite_autoindex_artifacts_2(document_id, artifact_role, generator_name, generator_version)
```

缺少：

```text
(document_id, role, location_status[, root_id])
```

数据库中也不存在 `sqlite_stat1`，说明没有可供 planner 使用的 `ANALYZE` 统计信息。

实际 `EXPLAIN QUERY PLAN`：

```text
SCAN d
CORRELATED SCALAR SUBQUERY 1
SEARCH lp USING INDEX idx_locations_status (location_status=?)
SEARCH rp USING roots primary key
SEARCH s USING sources primary key
SEARCH existing USING artifacts unique index (...) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

planner 没有选择 `idx_locations_document(document_id)`。由于 `active` 占 locations 的一半以上，这个选择非常差。对于每个外层文档，它可能扫描大量 active row；没有 active primary 的文档还会扫描完 active 集合。`ORDER BY ... LIMIT 3` 不能提前终止，因为所有候选必须先被过滤和排序。

## 8. 只读 SQL 对照实验

所有实验都通过 SQLite `mode=ro` 和 `PRAGMA query_only=ON` 或等价只读连接执行，没有创建索引或修改统计信息。

结果：

| 方案 | 查询计划核心 | 返回前三行耗时 |
|---|---|---:|
| 当前相关 `EXISTS` | 每个文档按 status 索引扫描 active location | 10 秒仍未完成，主动中断 |
| 强制已有 document 索引 | `lp.document_id=?` | 1.413 秒 |
| 改写为非相关 `IN`/半连接，保留 roots | active location 只构建一次候选集合 | 0.914 秒 |
| 非相关半连接，去掉多余 roots join | 一次 active candidate list + bloom filter | 0.231 秒 |
| 真实 worker | 原生产查询 | 902 秒仍未返回，被 watchdog 终止 |

所有完成的改写方案返回相同的前三个 document ID。队列选择核心存在至少数千倍的改进空间。

删除 `roots` join 之所以可行，是因为 `locations.root_id` 在 schema 中是指向 `roots(root_id)` 的外键，生产连接也启用了 `PRAGMA foreign_keys=ON`。若未来数据完整性允许绕过外键写入，则必须先验证孤儿 location 数量，不能只凭 schema 假设删除连接。

## 9. 现场 CPU、内存、线程和 I/O Profile

采样对象：第 43 次生产 worker，PID 20580；该 PID 后来按预期被 watchdog 终止。

采样时状态：

```text
worker_status = normalizing
progress_detail = selecting next document
parser_pid = null
current_path = null
```

5 秒 CPU/内存采样：

| 指标 | 结果 |
|---|---:|
| CPU 增量 | 4.844 秒 |
| 单核占用 | 96.8% |
| 总 CPU 时间 | 831.1 秒 |
| 工作集 | 90.9 MiB |
| 私有内存 | 81.9 MiB |
| 活跃线程 | 1 |
| handles | 133 |

5 秒进程 I/O 计数：

| 指标 | 结果 |
|---|---:|
| 逻辑读取 | 1,613.023 MiB |
| 逻辑写入 | 0 |
| 读取操作 | 412,934 |
| page faults 增量 | 0 |

同期物理磁盘计数：

- 读吞吐约 0.1–1.3 MiB/s；
- 写吞吐约 0.6–5.0 MiB/s，包含系统其他进程；
- `% Disk Time` 约 0.8–2.9%；
- 平均队列长度约 0.01–0.03。

解释：SQLite 调用了大量逻辑读，但数据主要由 Windows 系统缓存满足。CPU 用于重复 B-tree/row 遍历；SSD 没有饱和。这也是为什么单个 worker 看起来“很慢”，同时又长时间占用一个核心。

## 10. 当前重启循环的时间组成

典型一轮：

```text
启动延迟约 120 秒
  + 全量扫描约 148–588 秒（当日平均 208 秒）
  + normalizing SQL 900 秒
  + watchdog 杀进程
  + restart delay 5 秒
```

以平均值估算约 1,233 秒/轮：

| 部分 | 时间 | 占比 |
|---|---:|---:|
| 启动延迟 | 120 秒 | 9.7% |
| 重复扫描 | 208 秒 | 16.9% |
| 退化 SQL | 900 秒 | 73.0% |
| 重启延迟 | 5 秒 | 0.4% |

第 43 次真实进程 uptime 为 1,319.7 秒，其中 heartbeat 超龄 902 秒，与该模型一致。

## 11. 扫描阶段 Profile

暂停前第 44 次 worker 的完整扫描耗时 427 秒。通过读取现有 runtime 进度，按约 5–6 秒粒度采样，得到：

| 根/阶段 | 规模 | 近似耗时 |
|---|---:|---:|
| company_raw 枚举 | 244 家公司 | 约 245 秒 |
| company_raw 扫描/入库 | 16,570 个分组 | 约 81 秒 |
| dayu_portfolio | 637 个分组 | 约 12 秒 |
| Dropbox 枚举 | 约 429 个目录 | 约 47 秒 |
| Dropbox 扫描/入库 | 9,853 个分组 | 约 45 秒 |

该轮扫描报告：

```text
files_seen   = 46,600
files_reused = 46,599
files_hashed = 0
errors       = 1（已知空文件 quarantine）
```

因此，扫描耗时主要不是内容哈希，而是：

- `company_raw` 对 244 家公司的 `raw` 目录分别执行 walk 和排序；
- sidecar 查找与 JSON 读取；
- 文件属性观察；
- 分类、分组和状态维护；
- 对约 27,000 个逻辑分组执行数据库操作。

scanner 使用 `coalesced_transactions(max_operations=250)`，不是每个分组都单独打开/提交一个连接；但仍有大量逐分组 Python/SQLite 操作。

扫描进度回调在 worker 中以 0.5 秒节流，最多约每秒两次原子写 `worker_runtime.json`，这会产生少量额外写入，但不是 427 秒的主要来源。

### 11.1 重复扫描放大

`worker.py` 在扫描成功后只更新内存中的 `last_scan_at`，直到整个周期末尾才 `_write_state()`。worker 在 normalizing 阶段被杀后，磁盘状态仍停留在 8 月 12 日，于是每次重启都认为扫描到期。

2026-08-20 暂停前：

| 扫描状态 | 数量 | 累计时间 | 平均 | 最小 | 最大 |
|---|---:|---:|---:|---:|---:|
| completed_with_errors | 44 | 2.54 小时 | 208.1 秒 | 148 秒 | 588 秒 |
| interrupted | 1 | 0.17 小时 | 601 秒 | 601 秒 | 601 秒 |

本来每小时一次的扫描，变成了每次约 20 分钟重启时一次。

## 12. 控制面如何放大故障

### 12.1 SQL 期间无 heartbeat

worker 在调用 `catalog.normalize()` 前写一次：

```text
normalizing / selecting next document
```

下一次进度只会在 SQL 返回并进入具体文档后发生。SQLite `fetchall()` 运行 900 秒期间没有 heartbeat，supervisor 按规则判定失联并终止子进程。

### 12.2 状态只在完整周期末落盘

`last_scan_at`、扫描统计、下游阶段结果等只在 `run_cycle()` 末尾统一写入。任何后续阶段中断都会丢失本周期已经完成的扫描 checkpoint。

### 12.3 restart backoff 被错误重置

supervisor 当前逻辑：只要子进程 uptime 大于等于 `RestartResetSeconds=900`，就把 `ConsecutiveFailures` 清零，然后再加一。

退化查询恰好让进程活过 900 秒，所以每轮都被当作“运行足够久”，restart delay 永远回到 5 秒，而不是指数退避。

### 12.4 启动延迟重复支付

120 秒登录启动延迟本来只应支付一次。进入重启循环后，每个新子进程都再次支付这 120 秒，进一步降低有效占空比。

## 13. parser、LLM 与后续瓶颈

### 13.1 parser 不是当前故障根因

所有 watchdog 日志中的共同状态是：

```text
worker_stage=normalizing
progress_detail=selecting next document
parser_pid absent
current_path absent
```

最后一次成功批次的三个 HTML parser artifact 在一秒内创建。当前没有证据表明 parser 是 8 月 12 日以后持续卡死的原因。

但这个结论仅适用于“当前卡点”。修复 SQL 后，队列会开始处理 PDF、Word、Excel 等不同格式，parser 性能仍需逐格式 profile，不能用三个 HTML 样本推断所有文档。

### 13.2 LLM 会成为下一瓶颈

最后一次成功周期中，一个 LLM 摘要约耗时 42 秒。当前：

- distinct normalized 文档约 3,500；
- completed LLM summary：2,728；
- 当前可调度的 LLM pending：122；
- permanent LLM failure：650；
- normalize eligible（用非相关只读查询计算）：约 12,202；
- normalize batch：3；
- LLM batch：1。

正常化每轮新增最多 3 个文档，而 LLM 每轮只消费 1 个。如果始终顺序执行，正常化期间摘要 backlog 会以每轮净增最多 2 个。仅提高 `llm_batch_size` 但继续串行调用，能够平衡队列，却不一定改善总墙钟吞吐。

真正提速路径是：

- 将多个文档合并为一个受控批请求，保持清晰的逐文档输出契约；或
- 把 LLM client 重构为无状态/并发安全后进行有限并发；或
- 将 normalizing 与 LLM summary 设为不同预算和独立调度节奏；或
- 按 normalized content hash 复用摘要，避免重复内容再次请求。

## 14. 文件安全、外部目录与隐私

### 14.1 对源文件的写入风险

生产 worker 的 scan/normalize 路径读取源文件，主要写入：

- `.source_catalog/catalog.sqlite3`；
- `.source_catalog/derived`；
- `.source_catalog/artifacts`；
- `.source_catalog/index`；
- runtime、state、JSONL 日志；
- 仓库根目录的 `llm_cost_log.csv`。

没有发现生产 worker 自动删除、移动或覆盖 `companies`、Dayu portfolio、Dropbox Stock 等源文件的逻辑。`SourceManifest` 会解析真实路径并拒绝越出声明 root。手工 duplicate recycle/cleanup 是其他显式操作，不是本 worker 循环自动执行的步骤。

因此，当前主要风险是性能、派生数据和外部数据发送，而不是损坏其他目录源文件。

### 14.2 外部 LLM 数据发送

LLM summary 会把规范化后的原文内容发送给外部模型提供商，当前单文档输入上限约 120,000 字符，使用 MiniMax M3，并存在 MiMo fallback 配置。这不会修改源文件，但属于数据出境/隐私边界，应确认 Dropbox、财报、研报等内容允许发送给配置的第三方模型。

### 14.3 电池策略

配置为 `allow_processing_on_battery=false`，但电源 eligibility 判断发生在 scan 之后。因此即使在电池模式，完整扫描仍可能先运行，只有 normalize/LLM 等后续处理被阻止。对于笔记本性能和续航，这不符合一般用户对“电池时不处理”的直觉。

## 15. 容量、日志和其他维护风险

### 15.1 catalog 体积

调查时 `.source_catalog` 总体积约 92.16 GiB，其中：

- `catalog.sqlite3`：约 46.22 GiB；
- `catalog.sqlite3.pre-remediation-2026-08-09`：约 45.93 GiB；
- 数据库 WAL 模式；
- page size 4,096；
- page count 12,115,313；
- freelist count 0；
- auto_vacuum 0。

C 盘剩余空间约 98.9 GiB。主库加旧备份占用接近剩余空间量级。因为 freelist 为零，简单 `VACUUM` 未必能显著缩小主库；在没有表级容量分析之前不应假设它能解决问题。

`evidence_spans` 的 rowid 高水位达到 27,178,737；最近 1,000 行的 `raw_text + span_json` 平均约 9,746 字节，但该样本不能代表全表。当前 SQLite build 没有 `dbstat` 虚表，未在本次只读调查中得到可靠的逐表页占用。

巨大 evidence 表不是当前 normalize 队列查询的直接参与表，因此不是 8 月 12 日卡死的主因；但它会影响冷启动、备份、完整性检查、恢复时间和磁盘余量。

### 15.2 日志

调查时 `.source_catalog` 下约有 908 个 worker stdout/stderr 日志文件。日志总体只有约 14.79 MiB，不是容量主因，但没有明显的轮转/保留清理效果，会持续累积文件数量。

### 15.3 retention prune 缺陷

最后成功状态曾记录 retention prune 异常：

```text
AttributeError: 'SourceCatalogWorker' object has no attribute 'project_root'
```

constructor 保存的是 `_project_root`，prune 路径引用了 `project_root`。这会使设计中的每周 90 天清理失效。它不是本次 normalizing 卡死的原因，但会影响日志/派生产物治理。

### 15.4 live worktree 加载

worker 直接从当前工作树运行，而不是固定发布包。supervisor 每次重启都会加载磁盘上的新代码，因此另一个任务正在修改 worker 核心文件时，下一次自动重启可能加载未完成版本。

本次暂停前核对的 10 个关键模块，其运行时加载 hash 与当时磁盘 hash 全部一致；code version 为 Git HEAD `26a6b22`。调查时关键 worker 文件没有未提交修改。仓库其他已有改动不属于本调查。

### 15.5 `.env` 权限

仓库存在 `.env`，ACL 允许本机 `CodexSandboxUsers` 组 Modify。该权限可能是当前开发环境所需，但如果 `.env` 保存生产密钥，应将其纳入凭据权限和最小授权审计。此次没有读取或修改其中的秘密值。

## 16. 修复建议与具体实施步骤

### P0：保持隔离，防止继续消耗资源

当前已完成：

- `desired_state=paused`；
- worker 停止；
- supervisor 停止；
- 登录自启动删除。

在 P1 修复通过生产规模 canary 前，应保持该状态。不要通过延长 watchdog、缩短启动延迟或手工反复启动来“观察是否自己恢复”。

### P1：修复正常化队列查询

建议优先采用“查询改写 + schema 索引 + 生产规模测试”三件套。

#### 步骤 1：加入生产规模性能回归测试

测试夹具至少包含：

- 20,000–30,000 个 documents；
- 40,000–60,000 个 locations；
- active 占比大于 50%；
- 大量没有 active primary 的 documents；
- completed/partial/unsupported/failed artifact 混合；
- `LIMIT 3` 和真实 priority CASE。

验收：

- warm-cache 队列选择小于 2 秒；
- cold-ish 场景小于 10 秒；
- query plan 不得出现“外层全表文档 + 子查询按 `idx_locations_status` 反复扫描”的组合；
- 返回结果与旧业务语义一致。

测试必须使用临时 catalog 和临时配置，不得写 `config/source_catalog.yaml` 或生产 DB。

#### 步骤 2：改写为非相关候选集合

推荐形态：

```sql
WHERE d.document_id IN (
    SELECT lp.document_id
    FROM locations lp
    WHERE lp.role='original_primary'
      AND lp.location_status='active'
)
```

或使用等价 semi-join/CTE。若保留 `roots` join，应验证它的实际语义需求；若依赖外键完整性去掉它，应先检查 orphan location。

#### 步骤 3：增加匹配的覆盖/部分索引

候选：

```sql
CREATE INDEX idx_locations_document_role_status_root
ON locations(document_id, role, location_status, root_id);
```

或更小的部分索引：

```sql
CREATE INDEX idx_locations_active_primary_document
ON locations(document_id, root_id)
WHERE role='original_primary' AND location_status='active';
```

选择前应在生产副本上比较索引体积、建索引时间和 query plan。主库 46 GiB、可用空间约 99 GiB，不应在无空间预算时直接在生产库建大索引。

#### 步骤 4：统计信息作为辅助而非唯一修复

修复后可在维护窗口评估 `ANALYZE`/`PRAGMA optimize`，但不能把它作为唯一保障。统计信息会随数据分布变化；查询结构和索引应该在没有完美统计时也不会出现灾难性退化。

### P1：修复状态 checkpoint

扫描成功后立即原子持久化至少以下内容：

- `last_scan_at`；
- `last_scan_duration_seconds`；
- `last_scan_report`；
- `last_scan_stats`；
- scan retry 状态清零。

更稳健的方式是以 `scan_runs` 中最后一个 completed run 作为恢复事实源，而不是完全依赖 `worker_state.json`。验收：在 scan 成功后故意让 normalize 失败并重启，下一进程不得立即重复扫描。

### P1：修复 watchdog 可观测性

增加：

- `normalize_queue_select_started_at`；
- `normalize_queue_select_seconds`；
- `queue_rows_selected`；
- 每个 parser 的 wall/user/system time；
- 每个 LLM 请求耗时、输入字符和重试；
- 每个 scan root 的 enumerate/observe/DB 时间。

SQLite 可使用低频 `set_progress_handler`：

- 定期 heartbeat；
- 可检查 stop/pause；
- 超过明确 SQL budget 后主动中断并记录 `query_timeout`。

progress handler 不能替代 SQL 优化。推荐队列 SQL 正常预算低于 2 秒，异常预算远低于 900 秒。

### P1：修复 restart backoff

只有满足下列之一才重置连续失败计数：

- 至少一个完整周期成功落盘；
- 明确记录一个健康里程碑；
- 连续健康运行时间内 heartbeat 和业务进度均正常。

不能仅凭 uptime 大于 900 秒。对于相同 `stage + detail + reason` 的重复失败，应逐级退避并在达到阈值后停止自动重启、标记 degraded，避免永久资源循环。

### P2：优化扫描

依次考虑：

1. 按 root/公司记录增量扫描 checkpoint；
2. 缓存 sidecar 解析结果，key 使用 path、size、mtime；
3. 只对变化目录重新构造候选；
4. 避免不必要的 `resolve(strict=False)` 和重复路径规范化；
5. 批量查询/更新 locations 和 documents；
6. 测量每 250 operations commit 的实际耗时；
7. 评估 Windows USN Journal 或可靠 watcher，但必须保留周期性全量校验；
8. 把电源 gating 移到 scan 之前，确保电池模式下真正不启动重扫描。

### P2：平衡 normalizer、fingerprint 和 LLM

当前待处理概况：

- normalize eligible 约 12,202；
- fingerprint pending 约 1,589；
- LLM pending 122，后续会随 normalize 快速增长。

建议：

- 使用阶段时间预算而不只是固定 batch；
- 让 normalize 和 LLM 的生产/消费速率长期平衡；
- 使用 content hash 复用 summary；
- 对 permanent failure 650 条做原因分类，避免无意义重试；
- 先保持单线程安全，再决定是否重构并发；
- 把 LLM 从每个本地小批次的必经步骤中解耦，避免一个 42 秒网络请求阻塞所有本地处理。

### P2：容量和维护

- 先做可靠的逐表/逐索引容量分析；
- 明确 evidence span 的保留、压缩和重复文本策略；
- 审计 raw_text 与 span_json 是否重复保存大段文本；
- 评估旧 45.93 GiB remediation 备份的保留期限和恢复价值；
- 在删除任何备份前先确认恢复点和用户授权；
- 修复 retention prune 属性错误；
- 为 stdout/stderr JSONL 建立可审计轮转。

## 17. 修复后的验证与恢复运行 Runbook

### 17.1 修复前保持暂停

检查：

```powershell
& 'C:\Users\郑曾波\Projects\company-wiki\scripts\source_catalog_control.ps1' `
  -Action status `
  -PythonExe 'C:\Miniconda\python.exe' `
  -ProjectRoot 'C:\Users\郑曾波\Projects\company-wiki'
```

预期：

```text
User mode  : PAUSED
Process    : STOPPED
Supervisor : NOT RUNNING
Auto-start : OFF
```

### 17.2 在临时 catalog 上测试

- 使用临时 config、临时 catalog 和生产形状的数据；
- 运行 unit/contract/performance tests；
- 检查 `EXPLAIN QUERY PLAN`；
- 不写生产 `config/source_catalog.yaml`；
- 不直接在 46 GiB 主库上试验 migration。

### 17.3 生产库只读 canary

在保持 worker 暂停、自启动关闭的情况下：

- 对生产库用只读连接执行新旧查询结果对照；
- 记录 warm/cold 耗时；
- 验证 candidate document IDs、顺序和 retry 语义；
- 验证 active primary 外键和 orphan 数量。

### 17.4 单周期受控运行

建议先运行一次受控单周期，而不是恢复 supervisor 无限循环。验收：

- scan 不因 stale state 不必要重复；
- normalize queue select 小于目标预算；
- parser 能出现具体 `current_path` 和 `parser_pid`；
- 至少 3 个 normalize artifact 正常增加；
- worker_state 和 worker_runs 成功落盘；
- 没有 `heartbeat_timeout`；
- 外部 root 源文件 hash/mtime 不被 worker 改变。

### 17.5 暂不恢复登录自启动，人工运行观察

代码和单周期 canary 通过后，可人工执行：

```powershell
& 'C:\Users\郑曾波\Projects\company-wiki\scripts\source_catalog_control.ps1' `
  -Action resume `
  -PythonExe 'C:\Miniconda\python.exe' `
  -ProjectRoot 'C:\Users\郑曾波\Projects\company-wiki'
```

这会解除持久暂停并立即启动，但由于注册表项仍不存在，下次登录不会自动启动。至少观察：

- 连续 2 小时无 timeout；
- 连续 5 个以上完整周期；
- scan 按 1 小时间隔，而非每个周期；
- normalize、fingerprint、LLM backlog 单调按预期变化；
- CPU 不再长期单核满载；
- supervisor backoff 和退出行为正常。

### 17.6 最后恢复登录自启动

仅在上述验收完成后，按原值恢复：

```powershell
$run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$value = '"C:\WINDOWS\System32\wscript.exe" //B //Nologo "C:\Users\郑曾波\Projects\company-wiki\scripts\source_catalog_worker_at_logon.vbs" "C:\Miniconda\python.exe" "C:\Users\郑曾波\Projects\company-wiki"'
New-ItemProperty -LiteralPath $run `
  -Name 'CompanyWikiSourceCatalog' `
  -PropertyType String `
  -Value $value `
  -Force
```

恢复后重新读取注册表，并进行一次注销/登录验证。不要同时再创建计划任务或服务，避免重复启动入口。

## 18. 不建议采用的“修复”

以下措施不能解决根因：

- 把 watchdog 从 900 秒提高到 3,600 秒：只会让坏查询更久占用核心；
- 缩短或删除 120 秒启动延迟：只节省重启空等，不改变零吞吐；
- 只提高 normalize batch：当前查询有全量排序和相关过滤，batch 增加不解决复杂度；
- 只执行 `ANALYZE`：可能暂时改变计划，但没有结构性保证；
- 只加 heartbeat：会让 supervisor 不再杀进程，却让二次复杂度查询永久运行；
- 直接多线程调用现有 `LLMClient`：违反项目线程安全约束；
- 手工删除 stale lock 而不核对 PID/creation time：存在误删活锁风险；
- 在生产库上直接建大索引：46 GiB 主库和约 99 GiB 空闲空间需要先做空间与失败回滚预算。

## 19. 证据来源索引

代码：

- `src/company_wiki/source_catalog/normalizer.py:1539-1605`：队列 SQL 和 parser 前边界；
- `src/company_wiki/source_catalog/worker.py:508-630`：scan due、扫描状态、normalizing stage；
- `src/company_wiki/source_catalog/worker.py:835-851`：周期末统一状态落盘；
- `src/company_wiki/source_catalog/store.py:172-253`：locations/artifacts/evidence schema 与索引；
- `src/company_wiki/source_catalog/store.py:940`：coalesced transaction 行为；
- `src/company_wiki/source_catalog/scanner.py:272`：按 root 枚举；
- `src/company_wiki/source_catalog/scanner.py:790`：扫描/入库主循环；
- `src/company_wiki/source_catalog/scanner.py:1289`：coalesced scan wrapper；
- `src/company_wiki/source_catalog/control.py:547`：heartbeat runtime 原子写；
- `src/company_wiki/source_catalog/control.py:937-987`：stop/pause；
- `scripts/source_catalog_worker.ps1:351-405`：watchdog；
- `scripts/source_catalog_worker.ps1:457-481`：restart reset/backoff；
- `tests/contract/test_fc906c_normalize_queue_no_location.py:82`：仅两个文档的功能测试。

运行证据：

- `.source_catalog/worker_state.json`；
- `.source_catalog/worker_runtime.json`；
- `.source_catalog/worker_runs.jsonl`；
- `.source_catalog/worker_process_events.jsonl`；
- `.source_catalog/worker_launcher_events.jsonl`；
- `.source_catalog/scan_runs` 表（位于 `catalog.sqlite3`）；
- worker stdout/stderr per-session 日志；
- Git commit `0ee0d09dfcbc8d5bbac4f17666c09df910d17558`；
- Git HEAD `26a6b22f80ae964892d3f3f44fab364e65276583`。

## 20. 调查局限

- 本机没有 `py-spy`，因此未做 Python/native stack dump；但 runtime stage、无 parser PID、单线程单核占用、真实查询计划和等价 SQL 对照已经相互闭环，足以确定卡点位于 parser 前的 queue SELECT；
- SQLite build 没有 `dbstat`，未得到逐表页占用；
- 物理磁盘采样只有数秒，用于排除当前瞬时 SSD 饱和，不代表所有冷缓存场景；
- scan 分根耗时为 5–6 秒粒度现场采样，属于近似拆分；总扫描 427 秒来自数据库 run 记录，准确；
- 另一个任务同时在仓库工作，因此调查只核对关键 worker 文件 hash，没有尝试恢复或整理其他任务的改动。

## 21. 最终结论

1. 8 月 12 日持续异常的首要根因已经确定：FC-906-c 的相关 `EXISTS` 在生产 SQLite 上选择错误索引，导致 queue SELECT 近似二次复杂度。
2. parser 不是当前卡点；实际 parser 尚未启动。
3. CPU 是现场主要瓶颈，内存和物理磁盘不是。
4. watchdog、周期末状态落盘和错误的 backoff reset 把一次慢查询放大成永久重启循环。
5. 重复扫描是第二大浪费；当天 44 次扫描累计约 2.54 小时。
6. SQL 修好后，42 秒/文档的 LLM 摘要及 batch 生产消费不平衡会成为下一瓶颈。
7. worker 自动循环没有证据会删除或覆盖其他 root 的源文件，但会读取外部目录、写派生 catalog，并向外部 LLM 发送规范化文本。
8. 46.22 GiB 主库、45.93 GiB 旧备份、失效 retention prune 和外部 LLM 数据边界需要后续专项治理。
9. 当前已安全隔离：worker 持久暂停、进程和 supervisor 均停止、唯一登录自启动入口已删除。

