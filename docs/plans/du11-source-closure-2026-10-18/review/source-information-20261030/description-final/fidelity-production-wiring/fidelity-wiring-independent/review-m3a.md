# M3 CWP 接线工程节点：独立终审

**结论：PASS（仅 CWP 工程接线限定范围）；RF、真实收费与完整真实缓存验收仍 OPEN。** 基线 `6c12970609024b3cc09eeb238e4d66cd8296d186`。只读审查 12 个源文件及相应永久测试，没有改产品、下载原件、解析 PDF、调用模型或写生产配置。

## 最终证据

- 独立限定测试 **58 passed in 5.30s**：fidelity runtime、fidelity artifacts、summary assessment、旧 scoped runtime 四个模块；12 个源文件与两个新永久测试文件的执行前后 SHA 完全一致。完整输出、命令和 14 文件快照见 `final-tests.json`。
- 明确 `/6` → prompt `reading-source-scoped/4.2.0` → request `/7`；实际 material marker 和 output cap 都是 40。没有显式选择新协议的 generation 仍为 `/4`、prompt4.1、bundle2.0。
- raw/projected 正常完成分别产出 **2.1/3.1、producer1.1**，与真实 batch `_item_generation` 的 manifest 格式一致；wrapper2 能按 selected source 重新核对报告，质量风险仍为 needs_review。
- raw/projected skip 同样保持 **2.1/3.1、producer1.1**，声明所选 prompt4.2，但 summary.model、versions.model、summary_assessment 都为 null；没有伪造模型调用或评估。null 字段保留，DTO 精确 roundtrip 通过。
- 九类删除、降级或造假均被拒绝：移除 assessment、改为旧 schema、错 producer、伪造 plan、伪造 admitted/requested 完整集合、抹掉 claim 风险标记、bare summary、wrapper1 降级、wrapper 的 source plan 造假。
- reasoning/usage 可选 meter 均不存在时，batch receipt 仍能看到 wrapper2 assessment，不再被廉价字符串过滤跳过。
- 对 `6c129706` 基线旧引擎进行独立内存加载比较，**旧 `/4` 和 `/5` 请求 data_json、instruction、input hash 均精确保持**。旧3.0 projected fixture 的 wire 与无 assessment 结构保持。
- 实际捕获 v3 的旧2.0 bundle 解析再序列化后，**canonical bytes 完全一致**，SHA-256 仍为 `3a33d89419d325bdfc3be4facb1c7f85761384ba9a5e304c2c16008577ee5679`。

## 本节点发现并修复的两个共用问题

### W1 · P1 · 已关闭：skip 丢失显式协议，格式与 manifest 不一致

初稿根据 summary.model.prompt 选择 bundle recipe。合法 skip 的 model=None，于是显式 `/6` 请求实际产出旧2.0/producer1.0；generation manifest 却声明新2.1/1.1。这个差异会让合法 skip 产物在后续 generation/cache 对齐时被拒绝。

复现只需已有 selected DTO：清空 evidence、置 skipped_no_narrative、保留合法 source metadata，调用 `_skip_result`、`_bundle` 与 `_item_generation`；无需 PDF 或来源 SDK 解析。

修复通过 raw/projected verify execute 传递冻结的明确 reading projection 到 `_bundle`。新协议 skip 保持新格式与 producer，versions.prompt 表达所选协议；只有合法 summary_not_needed/skipped_no_narrative 才允许 assessment:null，模型字段保持 None。独立 raw 和 projected 两条路径均已复验。

### W2 · P2 · 已关闭：batch receipt 的 marker 过滤漏掉 wrapper2

初稿 `extract_summary_execution` 已支持 wrapper2，但 `_attempt_model_diagnostics` 的快速过滤只识别旧 execution/wrapper1。正常没有 reasoning_tokens、usage_diagnostic 等可选 meter 时，含完整 assessment 的 wrapper2 仍返回空 observations。

修复使用 wrapper owner 的共享 marker 清单，batch 不再各自硬码旧版本。独立 `_success(summary6, execution=report)` → HandlerResult → fake attempt store → `_attempt_model_diagnostics` 已确认保留 assessment。该问题属于可观测性丢失，原本并不意味着 bundle 本身已丢质量字段。

## 工程判断与边界

新协议的 decoder 在旧质量投影之后应用已知风险；summary 完成阶段在语言观察后按最终 claims 重算报告；wrapper 和 bundle 持有完整来源材料时继续重算 source plan、admission、requested/emitted 及诊断，并验证风险标记不能被抹去。单凭 claim ID 前缀、合法引用或自报“完整”不能通过。

publication effect 使用 bundle 的实际 producer，generation 使用相同 recipe。工程测试验证了它们的一致性；这不等于已经跑过实际 AUTO Store 发布、恢复和跨 run 零 POST 缓存全过程。

历史 validator recipe 保留为记录性软件元数据，未强迫它等于当前安装文件；报告的 source/claim 派生观察仍须重新核对。独立测试使用构造的历史 recipe 指纹验证“保留历史描述”，**不将其称为历史软件真实性认证**。真实性和原始字节身份由不可变 artifact/hash 存储负责，不由一个自含 JSON 指纹证明。

无论观察到多少项任务发出、是否命中有限风险诊断，`semantic_status` 和子事实覆盖仍为 not_evaluated。工程接线通过不能把旧 v3 六条摘要变成语义通过，也不能声称新 prompt 已在真实模型上解决遗漏。

## 可复查资料

- `probe.py` / `probe-result.json`：所有固定工程构造、九类拒绝、raw/projected manifest、普通/skip、旧请求精确比较和旧捕获字节 roundtrip。
- `review.json`：两项问题的修复前实际复现值、最终状态与范围。
- `final-tests.json`：58P 与 14 文件稳定指纹。
- `seal.json`：最终限定签署及审查证据 hash。

复现：从仓库根目录运行 `python .planning/summary-quality-20261030/fidelity-wiring-independent/probe.py`。该脚本只使用本地 DTO、合成回复和旧 bundle JSON；不将旧收费回复改标签冒充新模型结果，只更新本独审目录。

## 明确未签署

本节点没有审查或执行 RF 消费接口，没有真实模型/收费实验，没有完整真实缓存复用与恢复实验，没有 source locator/PDF 重新回放，也没有签署全仓 CI。旧2.0实际字节兼容与旧3.0 fixture roundtrip，应分别理解为已验证的工程证据，不能扩大为所有历史格式的完整来源回放承诺。

**本 seal 只覆盖当前稳定 CWP 接线快照；M3 整体仍须等待 RF、真实收费及相应真实恢复/缓存验收。**
