# MAIN 22 页 PPTX：有限 OCR 组合节点

`run_acceptance.py` 是独立验收脚本。准备阶段只执行真实公开 CLI 的 `--help`、纯请求/既有回执契约验证与本地 SHA 校验，不导入或再次纯解析 22 页原件，不运行 OCR，不请求供应商。

**真实 batch 尚未运行。** `PREPARED_NOT_RUN` 不能代表组合工程通过、产品通过或真实 M2 投资研究通过。共享 normalization composition 的代码接线由另一 owner 负责；脚本不编辑它，真实运行会暴露其实际表现。

## 固定对象与调用链

- 读取 `benchmarks/cross_market_rf/cases.json` 中 US-MSFT 的 `src_presentation`，经其 `audit_index` 选择 retained object，验证两个索引的 object 路径绑定。
- 封存原件 SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`；4,016,522 B。流式 hash，不 dump 原件。记录原件 SHA、size、mtime_ns 前后。
- 当前 `config/local_ocr.json` 的显式资源和指纹快照进 owned root。三个 ONNX 的实际 SHA 校验不初始化引擎、不跑 OCR、不下载。
- `official_source_cli --operation import` 的默认操作，以真实 archive 本地 copy、实际 capture 时间和字节身份登记；0 download。`investor_relations`、公布日 `2026-09-02`、year/period null、语言 null 供真实检测。capture 是 `local_document`，不是 HTTP 或 fetch 收据。
- `scripts/narrative_batch_configured.py --llm-provider deepseek` 采用当前公开 Config loader 的真实模型、endpoint、输出上限和温度；只保存非秘密配置，API key 仅留子进程环境。无 provider fallback、假模型或 mock transport。
- public `narrative_transport_cli --operation reference/read` 从导入的真实 SourceRef 取得并读取 NarrativeRef，校验完整 artifact SHA/size 和 batch pin。`as_of_date=null` 表示当前读取，不能把本次 capture 时间伪装为历史信息时点。
- 第二个独立 AUTO DB/run 沿同一 config/profile/model、同一 catalog 默认 reuse（省略 `refresh`），要求 `generation_status=reused`、返回完全同一 pin、零 AUTO reservation 和零收费账。预算 miss 会在 POST 之前拒绝。零新 POST 是原生 admission/reuse 证据推断，不伪造 HTTP observer 收据。

## 预算与诚实质量

| run | max_seconds | max_tokens | max_cost_usd | max_micro_usd |
|---|---:|---:|---:|---:|
| first | 600 | 30,000 | 0.1 | 100,000 |
| reuse | 600 | 1 | 0 | 0 |

价格固定为 R3 保守口径：输入 `333334`、输出 `1333334` microUSD / 1M tokens。first/reuse 都有 2 MiB final、128 MiB persistent、256 MiB scratch 原生上限。batch 及 read 子进程外层 660 秒 stop；Windows 超时结束该进程树，保留 origin AUTO，不猜 unknown=0。

报告复制实际 AUTO reservations、charged budget、unknown/unsettled 和 terminal job 状态。累计账从 `phase6/main_budget_preparation.json` 读取，保留历史 7 unknown 和 FX guard；已计入历史总额的 R3 native reservation 不重复相加。first 的原生 charged 账只加一次，reuse 的真实账必须为零。该 preparation 是本节点基线，MAIN 应确保运行期间没有别的付费节点同时消耗这份可用额度；准备脚本不修改 MAIN 共享账或建立第二种计费库。

必须有真实 selected spans、英文原语言摘要、`translate=false`、summary completed、public read replay verified，同时 `selection.coverage_complete=false`。这份图像 deck 不能宣称全页完整抽取。允许保留真实 partial/needs_review；选中证据不能带 low_ocr_confidence 或非 parsed。质量标记、实际 span 页码、版本和 read receipt 原样记录，不要求所有页成为已验证证据，不把双列文本虚构为表格。

## 命令

在当前 CWP 根目录，使用已经安装本地依赖的 Python（不安装新依赖）：

```powershell
python -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/run_acceptance.py preflight
```

MAIN 在共享接线完成、允许真实供应商执行后运行：

```powershell
python -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/run_acceptance.py run
```

run 创建短路径 `%TEMP%/mOCR-*` 独占 root，catalog config 位于其 `config/source_catalog.yaml`（public transport 按 config parents[1] 确定 project root）。配置、copy、catalog、两份 AUTO、请求、work dirs 和 stdout/stderr 均在该 root。公开调用的精确 argv、退出码、开始/结束时间、输出 SHA/size 在 `logs/*.command.json`；请求体不含 key。

失败保留整个 origin root。用输出的 `recovery_command`，或：

```powershell
python -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/run_acceptance.py resume --owned-root "$env:TEMP/mOCR-实际目录"
```

resume 保留 origin run ID、AUTO、request 和 frozen config；已完成阶段不另起付费 run。冻结配置/原件变化拒绝恢复。native runtime 对 unknown/lease 的恢复规则继续生效；不能通过新 run、改 request 或预算身份消除 unknown。未完成的 official import 可以重新本地导入去重，仍然零下载。

本目录已有 live workflow 的 durable receipt 时，`run` 拒绝启动新的 run，要求使用 origin `resume`。`live_batch_executed` 标记是否进入 live workflow；具体 import/batch/read 是否真正执行及成功，以实际 `logs/*.command.json` 和原生 AUTO 为准。

成功也默认保留 root 供复查。仅完整 PASS 且两个 origin run 当前都 terminal、无 active attempts、无 unknown/unsettled，且 durable report 已写入时可清理：

```powershell
python -B docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/run_acceptance.py cleanup --owned-root "$env:TEMP/mOCR-实际目录"
```

cleanup 验证绝对路径在系统 TEMP 的直接子目录、marker 精确绑定以及树内无 symlink/junction，再删除单个 owned root。失败不自动清理，不要求人工签收。preflight 无 AUTO/任务/推理，help 子进程均退出后仅清理自己的 TEMP。

## 证据与限制

`runs/<attempt>/acceptance.json` 和其 `logs/requests` 是本次脚本执行的实际证据；不复制大原件或 AUTO，不记录环境/key。生产 config、local OCR config、`.env`（仅 hash）、三份主 PWF、预算 preparation 的 SHA/mtime 前后对照。脚本不写这些文件，也不为其他 owner 的并发修改做自动回滚。

free schema check 使用已交付 HTML bundle/read receipt 作为既有契约样本，明确不把它冒充本 deck 的 SourceRef、live import 或模型响应。official import 没有独立 public request parser，free check 只调用实际 pure metadata validator 加 capture 字节/时间校验；真正的整件原件验证留在 live public import 中。工程组合通过仅证明这一个真实有限节点，不代表经济研究结论。

## 本次实际准备结果

当前主线 HEAD `979792e0a4105b18aed06dc7053f7bc239de6865`。已执行两次免费 preflight；每次 3 个真实 CLI help exit 0、7 项纯契约检查，0 vendor request、0 OCR inference、0 deck normalization。最新实际证据见 [preflight receipt](runs/mocr-20261009T045353-c9b78ccb/acceptance.json)。两次正常 owned TEMP 均已移除，original SHA/mtime 与 protected config/PWF/hash 前后相等。源 SHA 为固定封存值，模型为当前 loader 实际 `deepseek-flash`，没有安装或提交。

首次默认 sandbox invocation 因 TEMP 写权限 PermissionError 未完成；其最终 `acceptance.json` 写入也被拒绝。随后用授权只读 archive/owned TEMP 的 escalation 完成免费检查。原 sandbox TEMP 的精确路径检查为不存在；该失败没有被当作一次成功检查，详情保留在 [preparation checks](preparation_checks.json)。最后三处 live branch 防护（missing job 拒绝、configured model ID 验证、已有 live run 禁止另起）经代码核对，最终脚本做 AST 语法解析，但没有借此启动 live 路径或追加职责测试。
