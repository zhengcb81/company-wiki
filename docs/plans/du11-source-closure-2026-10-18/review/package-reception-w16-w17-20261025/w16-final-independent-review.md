# W16 ROOT 最终独立复核

2026-10-25。结论：**PASS（工程组件接收范围）**。第一轮 F1–F4 已按以下限定修复，未发现新的本范围未解决 finding。第一轮 `w16-independent-review.md/json` 与原始失败收据保留，本报告不覆盖它们。

该结论不等同于真实公司 RF、ST-A02、来源原文内容或 claim 摘录语义审核通过。结构化引用和同组 ID 不能替代阅读原文。

## 被审版本

只读候选：`C:/Users/郑曾波/Projects/revenue-forecast-w16-root-acceptance`，branch `codex/root-w16-acceptance-20261025`，**611b1d62b2eb3228df037c95145a1d8d8d1f01d8 之上的未提交文件版本**。本结论绑定本报告 JSON 的实际文件 SHA，不把未提交修改冒称为已有 commit。ROOT 后续若只提交这些相同字节，无需重跑；若改产品/测试字节，应补审相应差异。

逐路径读取 ROOT 确认的全部 10 个变更：SKILL、reference、document contract、template、共享 revenue_basis、backtest、report、两份既有 W16 测试及新增 ROOT 测试。另核 DU5/input_quantities 和 lint 未变。Git 工作树 diff 在本沙箱仍报 work-tree 权限错误；使用作者 611b1d62 物理文件与冻结候选做有界逐文件差异审查，未申请越权、checkout 或修改 Git。候选关键链运行前后 12 项 SHA 相同，定向测试后再次确认；另绑定实际运行的 backtest/data_contract 测试 SHA，共 14 项。

## 第一轮 findings 的处置

| Finding | 最终处置与实测 |
|---|---|
| F1 同 restated 标签被当作可比 | CLOSED。operations/status 相等只得到 not_declared；需相同业务边界、比较组、逐观测现有 policy_support claim 的有效 target/source 链接。原无桥双 restated 公开 CLI 成功保留数值，报告改为“口径未声明或可比依据不足”，不再称同口径可比。有来源同组正例真实 CLI/快照/回测成功；不同 group 的独立反例标不可比并停用历史基准 |
| F2 组件显式冲突被忽略 | CLOSED（结构与计算责任层）。组件显式 status/boundary/group/period 必须与父记录一致，未支持的组件键报错，组件 claim 来源需属于组件；数值、FY、文档单位及 Decimal 容差仍沿用原 owner。原 restated/after-disposal + as_reported/before-disposal 反例现 exit 2。缺组件字段继承父声明；嵌套关系与 exact-value 引用的原文是否真正支持总分关系，明确保留给来源/公司内容审核，未据算术成立宣称来源真实 |
| F3 公开回测盲用不可比历史 | CLOSED。_benchmark_diagnostics 复用 history_basis_status。原 mixed 输入的真实 create/evaluate 均成功，其 historical_cagr_mae、MASE、RMSSE 和训练尺度变为 null，并给 statement_status 原因；逐年不再有 historical_cagr_forecast。flat-base MAE 仍为 15，不依赖该比较的普通误差继续 |
| F4 continuing 锚点无法实际对齐 | CLOSED。reported_total 参数的可选 revenue_basis 由同一 owner 校验，policy claim 必须 target 到该参数，采用观测与参数的 operations/status/boundary/group 需一致。独立有来源 continuing 参数与历史基数走真实 CLI exit 0，base_revenue=150，报告明确“持续经营/重述”。借用历史 policy claim 的参数反例 exit 2，指出不支持 parameter:reported_total；未声明参数继续已有 total 锚语义，未放松 continuing 错替 total 的原拒绝 |

没有新增公司、页码或来源内容特判，没有新的人工许可/数据库。不同 statement_status 仍不自动生成调整；输入应提供来源已重述至同一比较组的值。纯旧输入没有任何 basis 声明时继续数值兼容，回测加注 legacy_numeric_only；显式但依据不足的输入不会再喂给历史 CAGR/尺度指标。

## 独立关键链与反例

执行源码均来自冻结候选，未执行作者或主仓脚本。稳定 pre-W16 完整输入/actuals 构造器复用，未复用 W16/ROOT 的 supported_basis、_basis 或 CLI runner；补充声明与正反例由审查者生成。

在自有中文/空格 scratch 中实际运行 **18 次公开 CLI**（累计子进程 44.846 秒）：forecast --help、forecast、snapshot create、evaluate。覆盖原四例及五个补充案例，**10 项独立具体断言全部通过**：

- 无桥双 restated 不再标可比；混合历史停用 CAGR/MASE/RMSSE，理由非空。
- 组件显式冲突拒绝；continuing 参数实际采用。
- 有来源同组重述可用历史基准；不同比较组停用基准。
- legacy 的 2026 历史 CAGR 基准仍为 160.71428571428572，MASE 仍为 0.8250000000000028，且明确标 legacy_numeric_only。
- 有来源 continuing 基数成功；参数不能借用历史观测的 policy target。

完整命令、退出码、输入/输出及其 SHA：

`.planning/w16-w17-root-acceptance/review-w16/counterexamples-a5fc49e493/receipt.json`

receipt SHA-256：`544c6db5d043c83a3011630a625729f21ef4f5a70f2ca649b064010e94cc401b`。其中原 F4 说明在执行后仅作文字修正，未改命令、结果、输入输出或源文件 SHA；该修正已在 receipt 明记。

## 独立定向回归

实际执行：

```powershell
C:/Miniconda/python.exe -m pytest -q -p no:cacheprovider tests/test_w16_root_basis_integrity.py tests/test_backtest.py tests/test_data_contract.py
```

候选 cwd 下 **60 passed in 8.60s，exit 0**；含进程准备的运行器耗时 23.64 秒。未重复全量 gate。ROOT 的 50 项/157 项日志仅作为上下文读取，未代称为本审查者实跑。

独立日志/收据：`.planning/w16-w17-root-acceptance/review-w16/final-tests-e783aa05c7/tests.log`、同目录 `receipt.json`。receipt SHA-256：`0c85305fae442863e33726926fd52f4eadd5fbbf39ef009010962ac658ff1923`。

## B01–B08 最终范围

| ID | 最终判断 |
|---|---|
| B01 | PASS：已核真实责任路径，首轮失败与最终变化均留痕 |
| B02 | PASS：可选元数据、DU5/来源引用复用、legacy 数值兼容 |
| B03 | PASS（工程契约）：边界/比较组/列报/期间与实际基数对齐；unknown 不冒称可比；不造来源语义真值 |
| B04 | PASS（结构/数值范围）：显式组件冲突拒绝、来源归属、FY/单位、双侧与 Decimal 复算；原文总分/重述关系语义仍需公司审核 |
| B05 | PASS：真实 forecast/报告/快照/evaluate 消费，持续经营基数实际采用，公开回测闭环 |
| B06 | PASS（组件矩阵）：原 CLI 测试正例改为真实 policy 引用，标签不足的未知分支仍测；独立公开链正反例及 60 项回归通过 |
| B07 | 原作者只读校对证据保留，本轮未重审原件；不签真实公司或来源内容 |
| B08 | PASS：同一 owner，无公司特判/第二货币表/新人工门；定向相关消费者回归通过 |

## 写入与恢复边界

未改作者、主仓或候选代码/测试。TMP/TEMP、publication registry、测试输出均限定自有唯一 scratch，PYTHONDONTWRITEBYTECODE=1，pytest cache 禁用；常见收费模型凭证从子进程 env 副本移除。下载/模型调用 0。关键链保留 36 个合成证据文件，共 1,622,583 bytes（不含 receipt）；首轮失败证据继续保留。没有复制真实原件，没有删除其他任务文件或原件。

未解决本范围 finding：**0**。后续由 ROOT 处理提交/合并；真实公司 RF、ST-A02 和来源内容验收仍单独进行。
