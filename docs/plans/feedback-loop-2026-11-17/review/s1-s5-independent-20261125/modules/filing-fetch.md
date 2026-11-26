# filing-fetch 独立复审

2026-11-25。实际执行根为 `C:/Users/郑曾波/Projects/filing-fetch`，`HEAD` 和本地 `origin/main` 均为 `7651f70d06b5ee411b4e9221751f5db3f7fd7526`。现场 F4 配置中的工作目录、公开状态及对账入口指向此检出，订阅主仓和两个物理技能目录。运行源码、测试、工作流、受管引用和生产配置无 Git 改动。原工区已有三份在途 PWF 和未跟踪的状态、工具、配置及交接路径，沿用原状。测试使用 Windows、CPython 3.13.9、pytest 9.1.1 和临时隔离状态，真实供应商、外发和费用均为零。未查看凭据内容。 [现场路由](</C:/Users/郑曾波/Projects/company-wiki/.planning/shared-reading-production/feedback-host/settings.json:30>) · [S5 台账](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/s5-verification-20261125.md:11>)

## S1–S5 判定

| 项 | 状态 | 已核范围与剩余缺口 |
|---|---|---|
| S1 | **已验**，原卡范围 | 原 Windows tick 双流黑洞已修。真实替身子进程非零退出时，保留原退出值、脱敏的 stderr 形状、可识别的自定义异常类和末帧。原始 stdout 和 stderr 敏感正文未进入冷读，旧日志原字节保留。配置未启用的正常 tick 仍退出 0，零失败日志。原异常链的内部帧、原生崩溃正文与启动错误的具体内容超出当前投影。 [Windows 启动器](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_scheduled_windows.py:161>) · [回归](</C:/Users/郑曾波/Projects/filing-fetch/tests/test_s1_windows_tick_logging.py:48>) |
| S2 | **部分** | 短财报有开始/终态，作业和定时有原生账本，T3 有逐项收据。统一日志原生失败分支、旋转、半行恢复和旁路告警通过。三表成功及强停失踪、次级日志阻断终态、详情失败后误确认三类缺口见下。当前本机记录偏差、未知和显式拒绝，正常过程仍需从各入口的原生收据重建，无法覆盖所有入口。 [轮转实现](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_runtime_log.py:98>) · [投递实现](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_runtime_feedback.py:192>) |
| S3 | **部分** | 生产调用有显式 CWP 命令和 ET 公开传输，矩阵播种改成 CWP CLI，电话会及原件用公开 SourceRef 读回，RF 周测有 FF 公开 T3 收据。以真实调用验证了跨仓命令和原 CRLF 字节。仓内 JobStore 仍会发观察并进 runner 依赖环，终态受次级日志 I/O 影响。短财报入口仍 2,112 行，还承担准备、预算、校验、路由和反馈。 [CWP 连接](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_company_wiki_connection.py:62>) · [矩阵播种](</C:/Users/郑曾波/Projects/filing-fetch/tools/offline_contract_matrix/seed_batch.py:23>) · [T3 接口](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_t3_receipt.py:393>) |
| S4 | **部分** | `quality.yml` 的 Ubuntu 3.12 运行 `ci_tests.py`，名单实际包括日常日志、三表子进程、作业/slot 对账、T3 和矩阵边界。矩阵从硬编码四个文件改为递归扫描，查静态 import 和可解析的内联脚本，动态构造仍需行为测试。Windows 三条启动器运行回归被 Ubuntu skip，原生端到端属本次 Windows 定向。当前正向测试接受次级日志无影响的轮转路径，缺本报告所验的主作业日志和详情通道独立故障。 [工作流](</C:/Users/郑曾波/Projects/filing-fetch/.github/workflows/quality.yml:8>) · [CI 名单](</C:/Users/郑曾波/Projects/filing-fetch/tools/ci_tests.py:14>) · [矩阵扫描](</C:/Users/郑曾波/Projects/filing-fetch/tests/test_s3_matrix_owner_boundary.py:20>) |
| S5 | **部分** | `0b5b757` 的自定义异常、T3 诊断、旁路警告及 CLI 播种，与 `7651f70` 的 owner 轮转均在现场源中。仓库记录同版远端 CI 通过。四个技能逻辑入口映射两套物理包，脚本一致。安装器全包 `--check` 仍退出 1，两个引用文档只有 LF/CRLF 字节差异，规范化内容相同。三项新实测缺口尚在当前版本。 [分仓 S5 施工与复验](</C:/Users/郑曾波/Projects/filing-fetch/docs/plans/feedback-loop-2026-11-17/S2-FF-windows-logging.md:21>) |

## 正常路径与预算

- **短财报。** malformed JSON 的真实 `fetch_filing.py` 单进程退出 2、stdout 为 `request_error`，同 run/attempt/step/evidence 有五项观察，包含开始、终态、未启动 provider、用量和下载计数。原因链为 `FilingFetchError ← JSONDecodeError`。短财报观察缺运行版本、时间和持久输入定位；`ff-short/1/<operation>` 标识发生而不绑定可重建的请求。财报 v2 单调截止取 CLI 窗口和原采集秒数中的小值，字节、时间与费用限额传至 CWP。电话会独立限额和用量，已观测的 provider 次数不会替代费用证明。 [短财报观察](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_short_feedback.py:84>) · [限额](</C:/Users/郑曾波/Projects/filing-fetch/scripts/fetch_filing.py:127>) · [原截止](</C:/Users/郑曾波/Projects/filing-fetch/scripts/fetch_filing.py:1382>) · [ET 传输](</C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_tool_transport.py:670>)
- **三表与后台作业。** 三表直启将采集限额送入 CWP stdin，FF 有独立进程时限和响应字节上限。持久作业提交时记录请求 hash，启动及终态有原 ID、尝试、时间、结果、计数和费用证据。丢失进程后按原 job id/attempt 对账，财报限制到 catalog，三表与电话会切换 `reuse_only`，旧费用仍按一次原支出证据，读回增量独立为零。机器 stdout 的业务 `partial` 可以伴随作业执行终态 `succeeded`。这两个字段对应不同的既有合同。 [三表传输](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_financial_statements.py:152>) · [作业提交](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_store.py:130>) · [原费用](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_runner.py:482>) · [三表只读对账](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_runner.py:625>)
- **定时。** Windows 启动器转发 tick 原退出值，成功时正常 stdout 仍为计划任务的弃置通道。实际 tick 的 slot、阶段、外部工作准入及结果由 RefreshStore 出收据。`runs` 可补投已落盘的失败/终态，`reconcile` 校验原 slot、作业和费用。已验历史旧批次成本为 unknown，原破损细项无回补。launcher 级异常的证据 ID 与有业务 slot 的原生发生各自可读，当前没有通用的父子步骤绑定。 [tick](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_scheduled_windows.py:202>) · [slot 阶段](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_refresh_runner.py:143>) · [重投](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_feedback.py:76>) · [F4 历史冷读](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/f4-resume-runtime-20261125.md:11>)
- **T3。** owner 显式 `run-live` 以原 run ID 占位、记录 Git 版本、四个用例的部分和最终结果。RF 周测走公开 `get --run-id` 或 `get --latest`，从新进程冷读，离线模式与真实验收的退出码有区别。同 ID 已失联时可读原部分收据，避免重新执行。信封带测试状态、开始结束和原因，机器 stdout 保持单 JSON。原 T3 隔离用例的 50 MiB、180 秒和零增量费用上限仍在，原测试四项按本次离线范围未触发。已核 RF 的软件接线与历史组合回归，实际 Windows 周任务的登记和一次自然触发本轮未查。 [T3 持久化](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_t3_receipt.py:236>) · [原用例限额](</C:/Users/郑曾波/Projects/filing-fetch/tests/test_e2e_download.py:56>) · [周测组合复验](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/s3-s4-owner-rollout-20261125.md:92>)
- **矩阵。** 原完整 41/41 PASS 绑定 FF `4b3dd4f45edc391a6cccaf3468b711c9675a0433`、CWP `bbcee7ba26080a3261459e8377dcd09524fb2ea3`、ET `2fc8f92eaf1f8a5406ec63fbf384fc51ab72b4f9`，Ubuntu 48.5085 秒，42 次合成请求、28 组核验，真实请求和费用为零。报告 SHA-256 为 `f86ca492629eb2db5a066c51fca7e9bba03d62f07eaedcef2dec71f96b54b7bb`，归档 SHA-256 为 `bc4bbaa7851dbdfae52590934282c719119fbeab22cb450039694261737a0b29`。后续 S5 三市场复用验证记录绑定 FF `1d3e0ca`，当前版复核了定向用例。完整 41 例沿用历史版本证据。 `seed_batch` 和最终验真走公开 CWP CLI，repo/模块路径绑定、运行 stdout/stderr 原字节、结果 oracle 和清理均有独立记录。 [41 例正式验收](</C:/Users/郑曾波/Projects/filing-fetch/docs/plans/mb11-ff-2026-11-11/S3-offline-matrix-owner-ports.md:76>) · [矩阵原文证明](</C:/Users/郑曾波/Projects/filing-fetch/tools/offline_contract_matrix/source_proofs.py:18>)

## 关键发现与复现

### P1 · 作业次级日志失败丢失已收业务结果

**实际执行。** 用临时 `company_wiki.json` 配置 `connection.cwd` 和 `commands.financial_statements = [python, "-B", fake.py]`，真实 `ff_job.py --jobs-dir <隔离目录> submit` 接收 `ff-job/1`、`kind=statements.acquire`。请求为 `financial-statements-request/1`、CN、`fetch_if_missing`、`income_statement`、限额 99999 字节/15 秒/0 美元。用不同 idempotency keys 各 `run --owner-job-id <id> --config <配置>` 一次。替身从 stdin 读请求并累计调用，在两次均返回同一 `complete` 和合成用量 1 请求、315 字节、0 美元。反例中替身先验证本次 `--jobs-dir/logs/<id>.log` 已记录 `run_started`，将该日志改名保留，在原路径创建目录，再输出完整 JSON。两种情况均在 run 退出后启动新进程 `get_status --owner-job-id <id>`，无需启动 provider。

| 同条件结果 | 正常 | 只阻断次级日志 |
|---|---|---|
| `run` 退出与机器状态 | 0，`ok` | 1，`fatal`，轮转日志记录 `PermissionError` |
| 冷读退出与原作业状态 | 0，`succeeded/complete` | 0，`unknown/run_lost`，无业务结果 |
| 尝试 / 已结束执行计数 / 原费用 | 1 / 1 / known | 1 / 0 / unknown |
| 本次替身调用 / 冷读增量 | 1 / 0 | 1 / 0 |

**根因。** `_land_terminal` 已计算出终态、结果和用量，先调用 `store.append_log`，后写 owner 原子收据。追加失败抛出 I/O 异常，原业务收据留在 running。之后冷读按失联规则正确保守投影 unknown，却只能从不完整的账本判断。runner 的启动和对账路径也在主记录写入前追加日志，属源码同类风险。**复验条件**是启动、终态、对账各自注入日志 I/O 故障，原业务持久化和已得的调用/费用维持一致，原错误可查，同一尝试无再次采集。 [终态顺序](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_runner.py:373>) · [次级日志](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_store.py:349>) · [失联写入](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_store.py:285>)

### P1 · 三表直启没有可对账的开始，正常成功也不留原发生

**实际执行。** 同样用 `connection.commands.financial_statements` 启动无网络替身，显式 `RESEARCH_FEEDBACK_DIR`、run ID 及 attempt 1。运行 `python -B scripts/fetch_statements.py --config <隔离配置> --request-file <JSON> --timeout-seconds 15`。请求使用 `balance_sheet`、`income_statement`、`fetch_if_missing`、限额 100000 字节/15 秒/0 美元。替身断言收到三个限额，在不同模式把调用标记写盘并 fsync。complete 和 partial 的合成用量均为 1 请求、315 字节、0 美元。partial 中 balance sheet 给 `unavailable/provider_unavailable`、coverage `provider_error`，income statement 完成。强停模式在写完标记后等待 5 秒；观察到标记且 FF 父进程仍运行后，用 `Popen.kill()` 终止 FF，等退出并读相同隔离目录。

| 模式 | 实得 |
|---|---|
| complete | 退出 0，单份 JSON 保留原用量，F4 和本机均零条。 |
| partial | 退出 0，F4 只有 execution、两个 statement 和 usage 四项结果；没有开始、原执行时间、Git 版本和输入定位，version 值是响应 schema。本机详情只有 schema 与 reason。按 `details_ref` 执行 `ff_job_feedback.py get-diagnostic <ref> --observations-dir <隔离>` 两次均退出 0，原 run ID 和原用量一致，替身计数无增量。 |
| 强停 | Windows 退出 1，stdout/stderr 各 0 字节；替身已收一次，强停前后 F4 和本机均零条，未生 FF 作业。 |

**根因。** 三表入口在获取响应及写 stdout 后才调用发布；响应投影仅挑异常和部分状态。对比短财报已在输入解析前立下开始身份。**复验条件**是启动前记录原请求引用及版本，面向同一发生记录成功、预期拒绝或失联，原用量未知可保守冷读，恢复无采集；CWP 已证明的三表原因与用量有可冷读引用。 [三表入口](</C:/Users/郑曾波/Projects/filing-fetch/scripts/fetch_statements.py:77>) · [三表结果选取](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_statement_feedback.py:47>) · [三表发布](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_statement_feedback.py:116>) · [总控步骤口径](</C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/interfaces.md:33>)

### P1 · 详情候选读取和持久投递确认分离不足

**实际执行。** 真实 `ff_job.py submit/run/get_status` 配同一合成三表 partial，分别令覆盖目录 `RESEARCH_FEEDBACK_DIR` 和默认 `--jobs-dir/observations` 中的两个详情位置故障。路径由原作业 ID 和尝试确定，包名按 `feedback-` 加 `uuid5(NAMESPACE_URL, compact_json(["filing-fetch", job_id, "1", job_id + "/1", "complete"])).hex`，详情为同名 `.cause.json`。把要阻断的详情路径预建为目录，允许同根 `.jsonl/.ready/.sent` 正常写入。两例各运行一次并用公开 `get-diagnostic` 冷读；先后比较覆盖目录与默认目录，移除阻断后再 `get_status`，比较同一包字节。

- 只阻断覆盖目录时，默认目录成功保留详情，观察携带 `details_ref`。按覆盖目录及同一 `--jobs-dir` 读回却退出 1；直接读默认目录退出 0 并得到三表原因和原用量 1/315/0。修复覆盖路径后可以读回同一内容。
- 两处均阻断时，业务正常退出 0、`succeeded/partial`、费用 known、一次执行；stderr 给出 `feedback detail unavailable (PermissionError)`。包剥掉 `details_ref` 却写了 `.sent`。解除故障后，同一作业 `get_status` 继续给出原业务结果，原包字节一致、详情仍退出 1，替身增量为 0。完整目录阻断后复投已有绿色用例，该用例未触发仅详情不可写。

**根因。** 读取当前候选发生 I/O 或解码错误立即退出循环，丢掉合法 fallback。发布允许详情与观察部分成功，但 `.sent` 没有记住详情待补，冷读据此跳过原终态补投。**复验条件**是合法 fallback 能按原引用读取，详情故障可在恢复时补齐同一发生的可冷读详情，原业务 JSON、费用和调用计数一致。 [冷读候选](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_feedback.py:459>) · [详情降级与确认](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_runtime_feedback.py:217>) · [补投判断](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_feedback.py:96>)

### P2 · 结构和回归边界还有明确余项

仓内 `ff_job_runner` 调用 `ff_job_feedback`，其公开对账反向调用 runner；`JobStore.load_checked(fix=True)` 在持锁写失联终态后调用发布。这是真实恢复路径的运行依赖，涉及状态读、业务对账及副作用三个职责。原启动/终态日志与 owner 提交的顺序已产生上述故障。另有 `fetch_filing → transcript_companion → fetch_filing` 的延迟运行导入，分别由伴随电话会及独立电话会触发，未观察到业务递归。矩阵 `run.py ↔ cli_main.py` 等九模块内部环仍在，`run.py` 兼任 CLI 和 Context/fixtures 的依赖来源。现有矩阵入口能运行，公共 CWP 调用已独立于这些同仓环；路径处理以配置显式命令为首选，legacy `PYTHONPATH` 注入仍限 CWP 公开 CLI 和本地工具。S4 扩面宜以已证持久化故障和 Windows 实跑为验收点。 [runner 依赖](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_runner.py:44>) · [反向调用](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_job_feedback.py:206>) · [独立转录调用](</C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_companion.py:270>) · [矩阵 CLI 反向导入](</C:/Users/郑曾波/Projects/filing-fetch/tools/offline_contract_matrix/cli_main.py:16>)

## 本轮测试和部署复核

`python -B -m pytest -q -p no:cacheprovider` 选择 `tests/test_s1_windows_tick_logging.py`、`tests/test_ff_t3_receipt.py`、`tests/test_s3_matrix_owner_boundary.py`、`tests/test_feedback_ordinary_failures.py`、`tests/financial_statements/test_fetch_statements_subprocess.py`、`tests/test_ff_job_feedback_lookup.py`、`tests/test_ff_slot_feedback_lookup.py`，初次 88 通过、4 失败。四项均为 T3 测试夹具用普通 Path 读取 Windows 沙箱深层临时路径触及 MAX_PATH。改用公司仓内短隔离 `--basetemp`，T3 文件全部 16 通过。源码和业务路径未改，已清该独占短目录。三组原创探针使用 Python 临时目录并自动清理。安装器 `python -B tools/sync_installs_b3.py --check --json` 显式指定四个技能父目录，仅 `references/company-wiki-connection.md` 与 `references/identity.md` 显示字节差异，工作树分别 30、38 个 CRLF，安装为 LF。以换行规范化后逐字节相等。安装器保持用户配置，不作部署。 [T3 路径实现](</C:/Users/郑曾波/Projects/filing-fetch/scripts/ff_t3_receipt.py:90>) · [CI 发布记录](https://github.com/zhengcb81/filing-fetch/actions/runs/45702059828)
