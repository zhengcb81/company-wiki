# Revenue-forecast 独立复审

复核版本为 F4 专用检出 `C:/Users/郑曾波/Projects/revenue-forecast/.worktrees/f4rd` 的 `49a4013dbcdc12821d8b8de80df8d8c702633142`，与本地远端跟踪引用 `origin/main` 一致。检出为 detached HEAD，状态干净，sparse 范围为 `scripts`。用同一提交的 Git archive 补齐 CI 所需目录及顶层文件，在 Windows Python 3.13.9、pytest 9.1.1 下运行。进程测试使用隔离 owner 根、反馈根和本地 CWP/FF 替身。实际供应商调用、付费和生产写入均为零。远端 Ubuntu 同版状态沿用 S5 台账，当前验收补充 Windows 运行证据。 [审查口径](../review_contract.md) · [S5 台账](../../../s5-verification-20261125.md) · [RF 49a4013d](https://github.com/zhengcb81/revenue-forecast/tree/49a4013dbcdc12821d8b8de80df8d8c702633142)

## S1–S5 判定

| 阶段 | 判定 | 证据及未验范围 |
|---|---|---|
| S1 | **部分** | S1-06 原 FF 非零退出和非法 JSON 的变更由 S5-02 恢复。在真实 Windows 子进程的 UTF-8 对照中，直接 FF 客户端保留退出 2 和一行 JSON，source preparation 保留退出 3、producer exit 7 和 F4 冷读。现行严格解码碰到单字节非 UTF-8 会破坏直接 stderr JSON，连带丢失 FF 原退出，见 RF-01。作业围栏仍以 `raise … from exc` 保存 compute 不可读的因果，但该分支将原 traceback 发往外层 logging，耐久 stage view 不呈现 `error_detail`，对该分支的日志脱敏仅作源码复核（`rf_job_facade.py:969–984,1169–1178`）。 |
| S2 | **部分** | 现行 RF 公开作业从同一 ID 冷读 source/compute/publication 三段，正常三段各执行一次，费用 USD 0.00。执行开始先持久化阶段，再投阶段收据（`rf_job_facade.py:911–938,1042–1071`）。现有定向回归验证可重投 outbox、坏目标不覆盖原结果、结构化 FF 故障和来源费用未知时保守地禁止重放。真实强停暴露可恢复性和同一尝试查回缺口，见 RF-02、RF-03。日周 CLI 实测有正常终态与故障收据，强停和部分失败仍无足够过程证据，见 RF-04。 |
| S3 | **部分** | 本轮核实 daily 用 CWP 公开 `status`、指定来源走公开 export-v2，weekly 用 FF `ff_t3_receipt.py get`，SLO 调用公开 resolver。保留来源正文冷读通过正向新进程回归。报告目录中 RF job 已入册来源的冷查仍加载准入实现，两个其他延迟导入环也保留，见 RF-05。 |
| S4 | **部分** | 从工作流实际选用的 `CI_TESTS` 收集，69 个目标、66 个文件、914 个节点，退出 0。此前新增场景有实际 CI 节点。固定清单仍遗漏审计工具测试，缺少覆盖运行竞态、坏编码反例及目录实际运行环的约束，见 RF-06。 |
| S5 | **部分** | S5-02 由 `2a534a78/cfc41323/11635b2b` 恢复诊断并纳入 CI，S5-07 公开依赖和平台处理落在 `2a534a78/1577be3c`，S5-08 retained-source 拆分落在 `49a4013d`，S5-10 专用检出及非配置安装字节已复核。完整关闭仍受 RF-01 至 RF-06 限制。受管 Windows SYSTEM 的当前日周任务实际指向、真实账单与旧回告终态重验仍未证。 |

## 主要发现

### RF-01 · 子进程编码错误破坏 S1 机器接口（P1）

在真实 `filing_fetch_client.py` 和 `source_preparation.py` 各运行一条合成 FF 请求。替身每次只执行一次，固定退出 7 并在 stdout 写 `{not-json`。对照 stderr 使用 ASCII 文本，直接端退出 2，stderr 为一行 JSON，`producer_exit_code=7`。source preparation 退出 3，一行 JSON，F4 `get-failure` 和 `reconcile` 可冷读相同原码，原因为 `filing_fetch_invalid_error_document`。

只改 FF stderr 为一个 `0xFF` 字节时，直接端仍退出 2，stdout 空，stderr 变为 14 行，包含线程 `UnicodeDecodeError` traceback，无法整体解析为机器 JSON，原 producer 退出码丢失。source preparation 仍退出 3 并返回一行 JSON，冷读原因退化为 `upstream`，同样丢失原码。对照和反例各两次本地 FF 调用，均由两条显式入口产生，对账未追加调用。

根因是 `scripts/filing_fetch_client.py:344–361` 在 `subprocess.run` 中对两流使用 `text=True, errors="strict"`，读线程一旦解码失败，完成的子进程及其退出信息不能作为原 `CompletedProcess` 交给 `362–402` 归因。后续验收可用字节管道先保留退出与两流，再分别进行机器输出解析和 stderr 安全诊断。验收应覆盖坏 stdout/坏 stderr、非零/零退出和 Windows 双管道，保留原机器信封及冷读的原 FF 退出。

### RF-02 · 父进程强停后旧计算可覆盖已恢复产物（P1）

复用 `tests/test_rf_job_facade_cli.py:30–80` 的 source 夹具及 `tests/test_rf_job_facade.py:56–72` 的三个阶段输入。正常对照用正式 `rf_job_cli.py submit`，退出 0，`succeeded`、`cost_state=known`、USD 0.00，执行数为 `[1, 1, 1]`。反例在首次 orchestration 的隔离 launcher 中仅置换 `rf_job_facade._COMPUTE_SCRIPT`。首个 compute 子进程写 marker 后等待释放，释放时和正式计算写入同一个 `--output`，随后退出。FF、source reader 继续用上述本地夹具，其余 RF 路径使用同版源码。

| 公开操作或事件 | 实际结果 |
|---|---|
| 子进程已写 marker，父进程还在等待，`get-status` | `running` |
| Windows `Popen.kill()` 只杀本轮测试的 orchestrator，退出 1，再冷读同一个 job | `interrupted`，允许 `resume`、`reconcile`，费用 `unknown` |
| 正式 CLI 执行 `act reconcile`，随后 `act resume` | `source-1 completed`、`compute-1 interrupted`、`compute-2 completed`、`publication-1 completed`。作业成功，原费用未知保留。 |
| 释放仍存活的旧 compute 子进程 | 旧进程写入不同的 `result.json` 字节，SHA 改变。冷读作业和 compute 从成功回到 `interrupted`。 |

`rf_job_facade.py:579–623` 的直接子进程只受父进程等待/超时管理，父进程持有 job lock。`1117–1124,1441–1452` 用该锁区分存活和中断。`758–769` 对不同 compute 尝试使用固定输入/输出/报告和 registry 路径。结果 SHA 检查在覆盖发生后才报告问题。路径隔离、结果提交代次和进程所有权须一起验证。验收应保留 `compute-1` 的历史写入，无论旧子进程先结束、迟到或从两次读取之间退出，冷查始终使用被选定的 `compute-2` 结果。恢复期间仍要保护可能触发 provider 的 source，现行未知状态约束应在正对照中继续成立。

### RF-03 · 恢复后原尝试 F4 收据失联（P1）

在 RF-02 的同一进程实验中，使用 `tests/test_f4_failure_coverage.py:31–59` 对原 `compute-1/action-started` 行构造正式 `feedback-action/1`，始终使用原 `run_id`、`attempt_id`、`step_id` 和 `evidence_ref`。父进程强停后，RF 本地对账把旧记录持久化为 interrupted，F4 查回 `done/interrupted/cost_unknown`。此时仍为 0 条 `compute-1/stage-outcome`。第二次计算完成后，同一原始请求变为 `{"state":"unknown","code":"native_attempt_mismatch"}`。原尝试仍可在公开 job view 中查到。

`scripts/rf_job_feedback.py:139–155` 只认可阶段最后一个 attempt，并以现时 job 状态和费用回报。`scripts/rf_job_facade.py:1399–1436` 修复本地状态时没有补投原终态。开始/结束投影的外层运行与尝试身份取自当次进程环境（`rf_job_feedback.py:25–51`），job attempt 记录缺少同一关联身份的持久字段（`rf_job_facade.py:912–930`）。真正的重建应按原 attempt 带时间、代码和原因查回。不能确定的费用继续保留 unknown。覆盖同一历史 F4 row 在冷读、恢复和再次冷查时的一致性，并确认不存在第二次 source 或 FF 工作。

### RF-04 · 日周读取强停缺启动证据，周运行丢失启动异常类型（P2）

实际 CLI 指向本地替身，显式给定 `--ledger`、`--alerts` 和隔离树。日对照指定 CWP 本地 `-m company_wiki.source_catalog.cli … status`，四个有效计数为零，正常退出 0。CWP 结构化 `catalog_missing` 故障保留具名原因，日跑退出 2。周对照走 `ff_t3_receipt.py get --run-id ff-synthetic-original`，四项均通过的合成已完成收据，周跑退出 0。周 FF 替身在输出 JSON 前抛 `PermissionError(13, ...)`，FF 退出 1，周跑退出 2。周报告只剩 `owner_lookup_unavailable` 和 owner exit 1，原异常类型和位置不可查（`tools/weekly_t3_assurance.py:218–239`）。

分别让 owner 替身触及 marker 后等待，再结束当前测试的 daily/weekly 外层进程并释放替身。两次外层均退出 1，原绿色 ledger 和 alerts 字节一致，F4 ready 为 0。日子进程后来落下一个脱离 ledger 的 `report.json`。周运行没有新报告。`tools/daily_t2_schedule.py:158–187` 在完成后才把本次身份连到 ledger。`tools/weekly_t3_schedule.py:60–76` 先同步查 owner 再生成 RF run ID。计划任务继续需要只读核对实际可执行位置。复验宜分开展示原绿色报告与本次已开始/未结束状态。使用同一 ID 关联公开 owner 请求和安全本地原因，避免在已中断交付中报当前成功。

### RF-05 · 公开 owner 边界改善，RF job 入册读写仍相互耦合（P2）

- 日跑通过 `tools/cwp_catalog_status.py:58–92` 调 CWP 的公开命令，`tools/daily_t2_runner.py:59–85` 用公开 export 检查精确原件。周跑经 `tools/weekly_t3_assurance.py:209–244` 只查 FF 指定或最新的现有收据。SLO 的 `tools/slo_probe.py:41–51,87–110` 使用显式 CWP 配置与公开 resolver，非零退出留下具名失败。旧 SQLite canary 的执行入口为退役诊断，安装无旧 canary。日、周默认目录仍从相邻 repo 推导（`daily_t2_runner.py:17–19`、`weekly_t3_assurance.py:15–16`）。若将调度改指 F4 sparse worktree 并沿用默认参数，解析基准变成 `.worktrees`，需通过部署参数确认。现有 SYSTEM 任务的注册位置本次未查。
- `49a4013d` 的保留来源冷读回归 `tests/b37_publication_sources/test_sources.py::test_sealed_source_cold_read_does_not_load_publication_admission` 已运行。只读 lineage 调 `report_catalog_retained_source.py`，保留 hash 与路径检查。所修的是这一条源码依赖。
- 仍有真实运行环。`report_catalog_cli.py:146` 的公开 `get-attempt` 调 `report_catalog.py:463–468`。对 RF job 已入册的尝试，`report_catalog.py:300–328` 延迟加载 `report_catalog_rf_job_import._validate_job_attempt`。后者反向导入 `ReportCatalog`、读取 `catalog._read_artifact`，入册重放再直接操作 `catalog._index`、`_validate_attempt_source`、`_validate_report_artifact`（`report_catalog_rf_job_import.py:25–37,522–535,702–722`）。效果是这类历史冷读仍依赖写入模块及其导入闭包。该组给出实际生产调用路径的源码证据，本轮未执行整条入册组合。
- 另有 `report_catalog_research_publication.py:894,1179` 与 `report_catalog_research_publication_sources.py:53,75` 的实际准入互调，以及 `report_catalog_research_attempt.py:845,977` 与 `report_catalog_research_identity.py:88,240` 的真实校验反向边。注解专用导入 `report_catalog_research_attempt.py:25–26`、`report_catalog_research_identity.py:19–20` 不计。身份模块中拟执行的固定公开探针字符串和历史证据验证（`report_catalog_research_identity.py:23–32,155–191`）另有代码路径指纹耦合，源码没有显示这里在读 CWP 私表。下一次破环可将已入册尝试的封存验证归入读取层，用新进程证明公开冷读不会导入准入模块，并保留原件完整性、重复入册及老格式断言。

### RF-06 · 日常 CI 无行为范围棘轮，Windows 独占路径仍缺持续执行（P2）

`.github/workflows/quality.yml:13–42` 的工作流只选 Ubuntu / Python 3.12，`tools/pre_push_gate.py:78–147,184–195` 传固定目标。本机在提交的同目录集合上，禁用上级 workspace pytest 配置后，实际收集 69 个目标、66 文件和 914 节点。其中 S1 2，F4 故障 15，多根 6，daily 来源 11，weekly 收据 15，boundary 15，release readiness 12，SLO 5，恢复 11，retained-source 1。定向运行先有 98 通过，三项缺 `.gitignore` / `CHANGELOG.md`；补齐 Git archive 根文件后这三项均通过。该缺件来自本轮归档命令。

`tools/tests/test_audit_baseline.py` 在 `db4f8c7a..b9e59db4` 有变更，CI 收集为零。额外执行观察到四个用例通过，`ArchivedReplayTests::test_legacy_replay_stops_before_traversal_or_owner_use` 需要 CI sparse 范围外的存档收据，缺件退出。公开私表保护测试 `test_explicit_catalog_does_not_open_private_sqlite` 可独立运行。现有 `test_ci_smoke_plan.py:57–71` 将执行参数与同一份固定集合相比，能防止指定节点丢失，无法发现新用例或新绕行未纳入。Ubuntu 也不会执行有 `os.name == "nt"` 标记的长路径两项（`tests/test_f4_failure_coverage.py:238–270`）。当前运行环和真实强停后的产物竞态均能与该 CI 集合并存。补充可在精简树运行的真实回归，保留依赖确有历史留存的独立场次，增加 Windows 小集合与针对目录读写的允许边/反例，按实际收集节点验收。

## 复现索引

- 测试从 `49a4013d` 用 `git archive` 提取 `scripts tests tools e2e compatibility references config examples agents .github .ruff.toml SKILL.md CHANGELOG.md .gitignore mypy.ini`。将 PATH 沿用宿主 Python，把 `LOCALAPPDATA/XDG_STATE_HOME`、`RESEARCH_FEEDBACK_DIR` 和 pytest basetemp 指到空目录，禁用 dotenv 和自动插件。精确收集从 `tools/pre_push_gate.py` 读 `CI_TESTS`，保持目标顺序，运行 `python -m pytest -c <隔离的空 pytest.ini> --rootdir . --confcutdir . -q -p no:cacheprovider --collect-only <目标>`。
- RF-01 可在 `tests/test_f4_failure_coverage.py:277–325` 的夹具替换 FF stderr 写入为 `sys.stderr.buffer.write(bytes([0xff]))`，保留它的 `raise SystemExit(7)`。两个真实 CLI 分别执行并捕获 stdout、stderr；按同文件 `43–59` 取 F4 原请求做冷查。应先复核原夹具的 UTF-8 对照，再运行坏字节反例以区分传输和业务。
- RF-02 与 RF-03 的隔离 launcher 用 `tests/test_rf_job_facade_cli._deployment` 写本地 FF/reader，`_request` 传 stdin。临时 launcher 从提交的 `scripts` 导入 `rf_job_cli` 与 `rf_job_facade`，设置 `_COMPUTE_SCRIPT=Path(__file__).with_name("compute_fixture.py")`，随后 `raise SystemExit(rf_job_cli.main())`。在 `compute_fixture.py` 开始处写一个 marker，在收到释放文件前轮询且最多 50 秒，随后将 `{"synthetic_orphan": true}` 写往 argv 的 `--output` 并写完成 marker。只在确认 marker 后对 launcher 自己的 Popen 调 `kill()`。正式 `rf_job_cli.py --owner-root <临时 owner> --deployment-config <夹具> get-status/act --job-id <原 ID>` 冷读、对账与恢复。先确认新尝试成功并保存结果 SHA，再写释放文件和查 SHA。F4 原始 `compute-1/action-started` 行通过 `test_f4_failure_coverage.reconcile_observation` 在恢复前后分别查一次。
- RF-04 使用 `tools/daily_t2_schedule.py --ledger <临时账本> --alerts <临时告警> run-daily --config <合成配置> --report-root <临时报告>`，在隔离 PYTHONPATH 放唯一 `company_wiki.source_catalog.cli` 替身。周用 `tools/weekly_t3_schedule.py --ledger <临时账本> --alerts <临时告警> run-weekly --filing-fetch-root <合成 FF 根> --run-id ff-synthetic-original`。基线用公开计数或精确收据结束，反例在替身收到请求后等待释放并做有界超时，结束各自外层，再释放并比较 ledger/alerts 字节、报告与 ready 数。
- S5-10 对 Git 的 `scripts/`、`references/`、`agents/` 和三份已声明根文件按安装清单排除两份退役脚本。四个逻辑安装路径 `.agents`、`.codex`、`.claude`、`.gemini/config` 各核对 141 份非配置文件，缺失、SHA 漂移均为零。`.claude` 的技能目录为指向 `.agents` 的 junction。四个入口均无已退役的 `processed_artifact_canary.py`，分别在新进程运行 `rf_job_cli.py --help`，退出 0，可见 `get-status`，stderr 空。安装配置只检查文件名存在，未读取内容。实际已有报表和对账路由的现场核查沿用 S5 发布台账。
