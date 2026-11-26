# F4 宿主与 filing-fetch 第二次独立复审

## 判定

FF 第二冻结候选的定向修复通过。F4 对账与补投职责仍耦合，两个出箱同时不可用后缺少真实宿主可调度的补投入口。当前真实跨仓离线补充矩阵完成代码绑定和隔离，两个选例均到原单例时限，模块验收待完成。

F4 同址公开调用专项通过，恢复时的环境隔离仍有实证缺口。全部试验使用合成输入、隔离账本和本机正常进程或进程替身。

## filing-fetch 候选和四条复验

基线 `7651f70d06b5ee411b4e9221751f5db3f7fd7526`。补丁 SHA-256 `10c0e6c1f58f4936246894793f57e8a42b7daf671349f32cd952d33f8a9b154a`，清单的 bundle 值 `1881f0d4f6151e491b309a40140a0560272a5d60616c2514eb21bd3261086c91`，清单文件自身 SHA-256 `614969cb4fbf1adaeaca4fc310e7ceac49227750a904a173df3a0d5c893cd895`。30 条候选文件哈希全部匹配，源仓 `git apply --check --whitespace=error-all` 通过。

| 上轮退回范围 | 本轮独立结果 |
|---|---|
| 显式 sidecar、普通成功时的隐含写入 | 旧 `test_ff_job_reference_keeps_its_established_lookup_beside_slot_records` 随 15 项定向组全绿。原普通成功和原费用回执可读，显式传输保持既有状态树。 |
| 附属日志、原执行结果、双详情位置 | 真实子进程覆盖启动日志、终态日志、对账日志拒写，按原作业可查一次运行的动作与费用。用隔离三表真实入口阻断两处 `.cause.json`，业务 exit 0、`complete`、仅一次原请求。恢复两个位置后，纯查询 `get-statement-run` 可查原 trace，终态观察未被写入。两次 F4 reconcile 得到同一结论并写出原包，`get-diagnostic` exit 0。 |
| 仅持原 run/attempt、去凭据输入和版本 | 同版公开 `get-direct-run` 和 `get-statement-run` 测试均通过。另用短财报的正常入口提交带合成凭据及 opaque continuation 的请求，已知请求拒绝 exit 2，原 provider 次数为 0，费用为 `not_applicable`。两次冷查逐字节相等，保留上市地、期次、可用授权字段和源码摘要。两个合成值均未出现在 stdout 或原生直接运行收据，`withheld` 明确指出省略项。 |
| 查询与显式补投分工 | `get_status` 经原状态树前后字节对比确认纯读，`reoffer-job` 恢复原 job 观察且无再采集。三表 `get-statement-run` 同样纯读。F4 的 `method=lookup` 对账仍走下列带写入分支，整体分工待修。 |

三表另外用 Git 基线归档重跑三组真实 CLI，正常 complete 与 partial 均 exit 0 且各 1 次合成上游请求，非法上市地 exit 2 且 0 次。r2 的三个机器 stdout 字节分别与旧版完全一致，SHA-256 依次为 `63f82bda5419404e6ba70e6223a2a8e33e76b623e065f97721c43bc41f1b1e4f`、`836a79452a268bec5d057ceff2835a693bf675e9f4446edb570013e907409d47`、`839e7ffb876c3ffe101ad36aa145ad097c756a8f72a604a9dd7a746e7e5860f3`。

### 仍待修的 owner 边界

- F4 的对账调用在公开层是 `method=lookup`。FF 的 `reconcile_direct_run` 查询直接执行 `_reoffer`，现有隔离探针在两处详情目录修复后可实证从无终态包变为有原终态包。应将纯读查询与诊断补投由各自入口负责。
- 两处完整出箱都不可写时，r2 的原生直接运行收据仍存在，按原 run/attempt 可手动冷查结果。该回归也确认了业务结果仍在。两处出箱都没有起始观察时，真实 F4 配置的 FF actions 仅有 `reconcile` 与 `report`，没有能主动查找此原收据的补投路由。应通过 FF 的公开恢复端口向现有宿主 `flush_observations` 提供可恢复原记录，仍由 FF 所属层把同一项原观察投递到出箱。收件路由沿原调用身份去重。

### 公开矩阵与完整 CI

从候选 FF 的 `tools/offline_contract_matrix/run.py` 经公开组合入口选 `chainA_download_reuse,fin_cn_annual_fetch`，绑定实际 CWP 工作区和正式 ET `7f4c1e7d`。两条各进入 FF CLI 后达到原 30 秒单例时限，报告均为 `PARTIAL`，其中电话会尚未观察到 ET supervisor worker。未取得零重发链完整真矩阵收据。源绑定通过，外网尝试 0，翻译尝试 0，保护源元数据保持一致，临时工作根和字节缓存完整收回。未提高时限，未重复矩阵。

本次同版完整 CI 路径 `t/ff-final-ci.txt` 与 `t/ff-final-ci.exit` 在候选及本地证据根未见。本轮独立执行定向组，15 项全部通过。完整 CI、生产 Windows 排程与受管安装的实际采用保持待证。[两节点矩阵原报告](/C:/Users/郑曾波/Projects/company-wiki/.planning/r25/vmat/o/attempt-a564fab4a12d465db04c5aff06bf68d3/report.json)

## F4 同址调用与恢复

实际 `host.py` SHA-256 `c3d6152ea10e3f1004ea06f4ed189a03fda9ba9592be2f1320d7838011464544`，`local_host.py` SHA-256 `f8b65e3199d7cc70a4eea9ee64e1f40223d00dc38fea0bd92253086acd5fb062`。单独运行同址查询与提交、worker 明确环境透传、Windows GUI 名称等价及公开 owner reader 无窗口、并行 owner 恢复范围共 4 项全绿。只读原进程丢失恢复和 SQLite 终态账本仍有 S1–S5 首轮的两条独审收据。直接使用 `LocalHost.handle` 时没有多余的 RPC 子解释器，非同址路线仍走外部 RPC。

新独立探针覆盖已登记仍未领取的 action。首次直接 handle 获得原 `pending`，唤醒替身仅收到明确允许的合成 `TEST_R25_ALLOWED`。随后按原 owner 执行 `LocalHost.recover`，收到一次原 action 的唤醒，但该进程环境额外包含未声明的合成 `TEST_R25_PRIVATE`。根因是重启的 `_recover_queued` 调用 `_wake` 时依赖默认父环境，原动作的允许名单没有在该分支使用。普通同址 RPC 优化没有引入这条旧分支，完整恢复验收须独立修正。探针不启动真正的 triage worker。

### 定向重跑

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
Remove-Item Env:RESEARCH_FEEDBACK_DIR -ErrorAction SilentlyContinue
Remove-Item Env:RESEARCH_FEEDBACK_OUT -ErrorAction SilentlyContinue
C:/Miniconda/python.exe -B -m pytest -q -p no:cacheprovider --basetemp ../v2ff tests/test_ff_runtime_lifecycle.py tests/test_ff_slot_feedback_lookup.py::test_ff_job_reference_keeps_its_established_lookup_beside_slot_records
```

从 company-wiki 根重跑下面两个独立探针。FF 应保持原一次调用与机器输出，单独的公开读不应写包。F4 重启应与首次采用同一环境边界。

```powershell
$env:PYTHONPATH = (Get-Location).Path + [IO.Path]::PathSeparator + (Join-Path (Get-Location) 'src')
$probe = 'docs/plans/feedback-loop-2026-11-17/s1-s5-remediation-20261125/reviews/host-ff-probes.py'
C:/Miniconda/python.exe -B $probe ff-direct-detail
C:/Miniconda/python.exe -B $probe host-restart-environment
```

[隔离探针](host-ff-probes.py) · [第一次独审及修复复验](host-ff-first-pass.md)
