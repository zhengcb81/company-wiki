# F4 宿主与 filing-fetch 独立复审

## 结论

F4 的两处原创反例经修复后独立复验通过，原先 17 项定向组已通过，同版最终组合由 ROOT 核验。FF 待修。FF 在主要路径恢复了原终态、原用量及原调用次数，仍有一个兼容回归和两组未闭合的复原行为。

## F4 宿主

| 检验 | 原样结果 |
|---|---|
| 当前 intake 候选的第一轮定向组 | 17 项通过。包括源配置故障、原进程强停、原进程退出、双收件箱失败、历史库失败回落、开放查询和原先标记重排。正常启动仅一次。 |
| 仅配置原生收件箱的合法路由，宿主数据库暂不可用 | 独立探针在首版发现冷查缺失。ROOT 修改后再跑相同探针，原退出 0，原生收件箱无宿主标记，宿主恢复目录保留回执，数据库恢复并 drain 后可按原 run ID 冷查 exit 0。 |
| 原进程失败，写出收件箱后在首次消费前收件箱短时不可达 | 旧行为为红。原退出 17，一个原 ready 标记，宿主数据库保留历史 exit 17。临时移开原收件箱后，原生 drain 返回 processed 0 和 remaining 0，故障观察失联。ROOT 修改后，收件箱不可达期间 processed 1、remaining 0，历史 exit 17 可查。恢复原目录再 drain，整个 SQLite 账本恰好一个 observe，remaining 0。 |

第三行的根因为生产方在文件发布后立刻调用 `history.delivered()`。这是已提供文件的证据。消费者成功结算才表示已经消费。修复令 SQLite 待投递项活到消费者持久确认。文件及账本批次共用同一 occurrence identity。独立复验覆盖文件投递后不可达和文件恢复后再次 drain，均保留一个原操作和一个观察。

第一次 17 项结果对应 `intake.py` 文件 SHA-256 `18ab0d187e0e2cf711da48dd84564449d980537aef73630a7c2a38c006966727`。原生专用路由绿色复验与消费窗口红例对应 `86d50522bb6207469826b15b92166aba85006060d7d3104c4d856ceb80435ce9`。消费窗口最后的绿色独立测试对应 `99a2d4327c8cd65891d91299f6ec68a62d28cdbdbc989c97443e3ede192f807d`。均用同一 `process_history.py` SHA-256 `93951dc144badd73b12ab535964bbb8845675fc91328a4e1b920a22614a903f6`。均为隔离假 owner，无真实外发或费用。

### 重跑

从 company-wiki 根执行。探针在受验文件旁另建独占临时根。需要对照 `host-native-only` 的 `history=found`，以及同一关闭窗口修复后的 `host-post-offer` 会处理原观察且原 exit 17 可查。

```powershell
$env:PYTHONPATH = (Get-Location).Path + [IO.Path]::PathSeparator + (Join-Path (Get-Location) 'src')
$probe = 'docs/plans/feedback-loop-2026-11-17/s1-s5-remediation-20261125/reviews/host-ff-probes.py'
C:/Miniconda/python.exe -B $probe host-native-only
C:/Miniconda/python.exe -B $probe host-post-offer
```

[隔离复现脚本](host-ff-probes.py)

## filing-fetch

15 个候选文件与清单哈希匹配。源仓当前 `7651f70d06b5ee411b4e9221751f5db3f7fd7526` 使用 `git apply --check --whitespace=error-all` 核验可应用。候选补丁 SHA-256 为 `55e9799106738c4616eb6903d6a7fffd27d5d9151b1358901329b441a8823d56`。

同版独立重跑交接的六个测试文件，46 项通过，1 项失败。提交终态早于附属日志且保持原费用、强停的三表任务可按已取得的原引用冷读、已有详情在备用盘可查。上述通过是定向证据。全量 CI、实际 Windows 周任务和受管安装均沿候选 PWF 记为待证。

| 缺口 | 原样证据 | 修复验收建议 |
|---|---|---|
| 显式 sidecar 的旧落盘边界变化 | `test_ff_job_reference_keeps_its_established_lookup_beside_slot_records` 失败。普通已成功财报作业在原显式 sidecar 之外创建了本仓 `observations/*.sent`。公开 reconcile 仍返回相同原费用，副作用已在调用查询前出现。 | 保留可补投作业所需确认，普通成功明确 owner 输出时沿旧写入语义。对显式和缺失 sidecar 分别查整个状态树。 |
| 三表直启的终态详情从待补状态丢失 | 两处该运行的 `.cause.json` 同时暂不可写，原 CLI 退出 0 且只有一次合成请求，向 stderr 告警。原 trace 的终态和详情两次冷读均正常。解除阻断后仍只有开始 packet，没有原终态 packet，`get-diagnostic` 退出 1。 | 在已有三表原运行记录上保存待投递终态及详情，沿明确的 owner 恢复入口重投。恢复应在重复执行时复用同一原引用和次数。 |
| 原运行号和请求缺少反向查回入口 | `get-statement-run` 只收 `ff-statement/1/<随机值>`。候选回归先读取测试目录的 `.ready/.jsonl` 才拿到引用。正常 stdout 沿用原协议，日志只留 stdin 的 SHA，查询不能给出脱敏后的原请求参数或定位。 | 公开查询可按原 run/attempt 解析原发生，留存可复验请求参数或已有输入引用。原文件或机读结果格式保持兼容。 |

两个附带分工仍需落实。当前 `get_status` 可以经恢复包装修改终态并补投，S1–S5 统一合同规定纯回读和维护投递分开。FF 旧的短财报版本和输入复验、电话会伴随及离线矩阵同仓耦合由候选交接记为余项。

### 重跑

从 FF 隔离候选运行首个失败用例。显式 sidecar 由测试自身设置，正常进程原来未设置观察目录覆盖路径。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
Remove-Item Env:RESEARCH_FEEDBACK_DIR -ErrorAction SilentlyContinue
C:/Miniconda/python.exe -B -m pytest -q -p no:cacheprovider --basetemp ../vr tests/test_ff_slot_feedback_lookup.py::test_ff_job_reference_keeps_its_established_lookup_beside_slot_records
```

从 company-wiki 根使用同一隔离探针执行三表的第二行故障。现有结果为 `exit=0`、`business_status=complete`、`same_cold_result=true`、`trace_has_details=true`、`native_terminal_exists=false`、`get_diagnostic_exit=1`、`calls=1`。将候选脚本复制到独占根进行测试，防止覆盖路径故障写入候选的默认作业目录。

```powershell
C:/Miniconda/python.exe -B 'docs/plans/feedback-loop-2026-11-17/s1-s5-remediation-20261125/reviews/host-ff-probes.py' ff-direct-detail
```

[隔离复现脚本](host-ff-probes.py)
