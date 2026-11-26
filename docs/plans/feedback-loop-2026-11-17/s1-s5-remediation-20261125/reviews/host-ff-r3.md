# filing-fetch 第三版与 F4 环境边界独审

## filing-fetch 第三冻结候选

**本轮整改项通过。** 源基线 `7651f70d06b5ee411b4e9221751f5db3f7fd7526`，补丁 SHA-256 `382793dd33c99688997b54260321025a5fdeec7f31e5af72ec6738715a5a5eac`，候选 bundle `cefddfbb7d93622e77389687bc6db23d8b3cde003b232965f83480eb8a54765e`。清单文件本身 SHA-256 `1950c204715ab9e7fbebdef883f62ffc9bfc661433e7533bb3f3683fdc99a5d2`。33 路径实际内容逐项匹配，源仓 `git apply --check --whitespace=error-all` 通过。

| 验收项 | 独立结果 |
|---|---|
| 显式 sidecar 兼容、附属日志故障、原结果及原次数 | 从同版候选重跑 `tests/test_ff_runtime_lifecycle.py` 与上一轮显式 sidecar 回归，共 17 项全绿。 |
| 两处详情路径故障、原业务退出与只读对账 | 复用实际子进程探针，两处详情不可写时原 exit 0、状态 complete，原业务调用 1。恢复路径后，公开查询与两次 F4 reconcile 均返回同一原 trace 和明细，均保持终态包仍缺失，独立维护端口负责投递。 |
| 两处完整出箱同时阻断、自动恢复与去重 | 重跑冻结候选附带真实 F4 `host-flush-probe.py`。保持独占短路径与系统环境允许列表。真实入口的原退出 0、原业务调用 1，恢复出箱后由宿主调用公开 `flush-observations`，原运行号及尝试号的 5 个观察均落入 F4 账本，重复 drain 处理 0。 |
| 短财报输入、原 run/attempt 与费用 | 同版定向保留上轮覆盖的公开冷查、输入范围和未知用量信息。纯查询保持业务成果且没有派发。 |

同版完整 CI、真实排程与实际安装采用仍待正式发布。第三版独审沿以前录得的代表性实时跨仓矩阵范围，没有新增同版全矩阵成功证据。[第二轮矩阵计时、旧版机器输出逐字节对照及附加短财报探针](host-ff-r2.md)

如需定向重跑，从 FF 第三冻结候选目录执行。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
Remove-Item Env:RESEARCH_FEEDBACK_DIR -ErrorAction SilentlyContinue
Remove-Item Env:RESEARCH_FEEDBACK_OUT -ErrorAction SilentlyContinue
C:/Miniconda/python.exe -B -m pytest -q -p no:cacheprovider --basetemp ../v3ff tests/test_ff_runtime_lifecycle.py tests/test_ff_slot_feedback_lookup.py::test_ff_job_reference_keeps_its_established_lookup_beside_slot_records
C:/Miniconda/python.exe -B docs/plans/ff-runtime-remediation-20261125/host-flush-probe.py --cwp-root 'C:/Users/郑曾波/Projects/company-wiki'
```

## F4 宿主

原同址、启动后恢复、并行 owner 分流、Windows 无额外 RPC 与原投递去重共 5 项通过。独立重启探针实测同址首次唤醒和冷进程恢复均传递已声明合成变量，未声明变量均未传递。原动作仅有一次身份，重启继续唤醒原动作。动作路由存储允许变量的名称。

**两个不同的兼容入口待修。** 实际复验源码 `host.py` SHA-256 `499cf2850a73564a5fa09fd44c76ca7a674e40d343e4d8c6707ba09fcc1ce5d0`，`local_host.py` SHA-256 `f7a3144c169a3b76416a40dff6185d59a5ec3829665c917d3d1c7c0855b942b1`。

| 路由和情形 | 可复现证据 | 责任边界 |
|---|---|---|
| 直接运行本仓公开 `local_host rpc`，方法 lookup、类型 reconcile | 支持的独占 registry 仅声明合成 `TEST_R25_ALLOWED`，实际 owner 读取到 allowed=true、private=true。 | 独立 RPC 的 `handle(environment=None)` 将 `None` 传入对账层，真实公开 owner 子进程继承原调用环境。自身 registry 已有变量声明，应与同址调用使用同一过滤。 |
| `intake drain` 显式给出非默认 `--hosts explicit-owners.json`，调用 owner flush | 同一声明，实际 owner 读取到 allowed=false、private=false。drain 无诊断。 | 本次 drain 已取得显式 registry，`LocalHost` 的维护分支仍自行猜默认 registry，丢失已允许变量。恢复及维护应复用同一明确的 registry 来源。 |

从 CWP 根执行独立原探针，三个入口都应只见合成 allowed 值的存在。探针只输出是否存在，隔离状态随执行清理。

```powershell
$env:PYTHONPATH = (Get-Location).Path + [IO.Path]::PathSeparator + (Join-Path (Get-Location) 'src')
$probe = 'docs/plans/feedback-loop-2026-11-17/s1-s5-remediation-20261125/reviews/host-ff-probes.py'
C:/Miniconda/python.exe -B $probe host-restart-environment
C:/Miniconda/python.exe -B $probe host-public-rpc-environment
C:/Miniconda/python.exe -B $probe host-explicit-registry-environment
```

[独立离线探针](host-ff-probes.py)
