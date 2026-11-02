# R7 核心最终只读扫查

状态：**3 类遗漏已证实，ROOT 已安排同 owner TDD 修复**。这是修复前证据，后续实施另写 `R7-final-sweep-core-implementation`，不覆盖本记录。基线为当前 `bd911a2bd1125fe46d7c5a0f605fe3b0104f17be`；没有改 src/tests/Git/主 PWF，没有读取历史运行目录、原件、配置秘密或调用模型。

使用 CodeGraph context 定位公开合同及调用入口，再检查当前源码。全 src 及三个核心树字面扫描只作导航，不把常量或命中数当缺陷；精读位置、SHA 和纯合成观察见 JSON。不宣称逐行审查全部仓库。

## 仍需清理：少而明确

### F1 / P2：batch 请求藏有固定 100 文档与 2 MiB 上限

`automation/narrative_batch_cli.py` 读取请求后调用 `NarrativeBatchRequest.from_dict`。`narrative_batch_request.py:194-195` 在实际工作预算之前拒绝 >100 个显式 work item；`:263-264` 又拒绝用户显式设置 `max_final_bytes > 2MiB`，即使已有 `max_seconds/max_tokens/max_cost_usd/max_final_bytes/max_persistent_bytes/max_scratch_bytes`。

纯公开请求反控：相同合法配置的 100 个不同 SourceRef 通过，101 个失败 `batch must contain 1 to 100 explicit work items`；单文档请求显式 2,097,153 字节 final 配额失败 `one final artifact cannot exceed the 2 MiB emergency cap`。没有执行任务或读取 key。

这不是保留真实资源预算：问题在于又有不可配置的上限否决显式预算。建议移除固定天花板，继续要求非空有限列表、合法/一致 item、正整数/数据库可表示计数和用户所有真实累计资源限额；不新增 override flag、不抬另一个阈值。

### F2 / P2：可选来源附加信息 >16 KiB 否决整个入库

`source_catalog/canonical_writer.py:292-306` 的公开 `import_staged` 在字节 owner 之前测 `provenance_extensions` canonical JSON，超过固定 16 KiB 立即 `CanonicalImportError`。真实 caller 包括 `transcript_import.py:158`；官方/共享原件方法则直接调用同一 `_commit_staged`，不走这个固定帽，形成同层分裂。

对公开方法作纯边界观察：合法小 JSON 到达 staged/commit port；相同结构 17,000 字符 optional diagnostic 被拒，两个 storage port 均未调用。port 用替身，未触磁盘/数据库，不冒称真实原件入库已跑。正常 JSON/身份仍须验证，建议只去固定尺寸许可，不丢附加信息或伪造完成；实际总存储/下载预算继续由其 owner 负责。

### F3 / P2：原文路径字符串被当作存储位置，阻断整份材料

`automation/narrative_contracts.py:169-179` 对所有字符串判 Windows drive/UNC/file URI。公开 `NarrativeSelectResult.from_dict` 经 `_assert_pathless_reading_wire` 在真实 `_result_dict` 组装后调用此检查；`NarrativeSelectHandler.__call__` 将错误映射为 `INPUT_SCHEMA_INVALID` terminal failure。

纯公开 DTO 反控：用 `EvidenceSpan.create` 重新绑定 locator/output/span hash 后，普通经营句通过；相同句前带原文 `C:\subscription\contract — ...` 则 `PhysicalPathLeakError: physical path value is forbidden`。这里是 `evidence_spans[].raw_text` 的原文内容，不是实际库路径元数据。

建议由同一个 pathless 合同 owner 识别已知的原文/claim 正文语义槽；正文仍完整保留，真正 `path/root/object_key` 元数据和非法额外字段继续拒绝。不能全面关闭路径保护，不能凭任意名为 text 的键在未知结构中放行。

## 已清理或保留的边界

- G1 已移除的 selected/summary/bundle/report/context 成功结果尺寸 gate 本轮未发现活动回退；相关老常量及 limit 形参有保留别名，调用不再据其否决。不能因字符串仍在就重复施工。
- G2 自动坏 cache 跳过诊断继续；显式 pin、同 run 冻结产物和未知费用仍严格。这些保护的是恢复/已付费响应归属，不是人工放行。
- G4 同一 VerifiedContent 上层只绑定身份；真实 reader 每次实际开原件核 SHA。缓存处的 artifact SHA、来源 SHA、locator replay 是不同边界，不算重复人工身份验证。
- 默认 steady 链未见 canary、manual approval、plan/policy hash/expiry 重新授权。旧 activation/runtime schema1、remediation 和兼容 authorization 名称存在，但不作为当前默认运行的许可。`allow_download` 在请求/CLI表达“执行下载而非只读发现”，不是第二份人工授权 JSON。
- `source_processing_complete=False`、语言 observer unavailable 不直接禁止其它独立充分材料；G3 的已证/未知分轴保留。原文未知不得伪装成事实或已完整检查。
- optional review 的 reader 缺失/损坏降诊断；CWP wire 对未知 shape/不一致 source 仍有格式拒绝。本次没有证实一个由当前 producer 生成的、完全合法且仅诊断规模较大的 payload 因此被拒，不把它伪列成新实质问题；F3 是已证正文语义错位。
- HTTP request/response 明确预算、parse/OCR memory/pixel/output/deadline、WorkBudget、POS 能力上界返回 unknown、显式源候选读取/下载预算保留。它们在实际工作中计量或标明未处理，不是成功结果的额外许可。ET importer 的 16/25 MiB inbound 默认、标准 JSON 自身可编码性、summary 协议显式请求的 claim 数及每任务份额，不在未证明资源/协议责任失当时直接删掉；后续若改变应在所属单层统一真实预算/协议版本。
- 查询 limit/offset 的分页、诊断 sample 的总数/limited 标记、物理坐标层级一致性、币种/单位/issuer/期间/as-of、有限数值、完整 source context 保留。它们不要求签收；不以本轮简化为由制造语义支持或丢限定。
- H1 父节点已知 P2 属结构内容理解，明确排除，不用它凑门禁发现，也不改 H1 源树。

探针首次 receipt fixture 用了不合法 `adapter_version='1'`，被正确拒绝；改为既有 semantic-version 合同 `1.0.0` 后才保存完整观察。没有放宽该校验或将此夹具错误算成新产品缺陷。

ROOT 已明确安排 F1/F2；F3 现也已在公开 DTO 证实。后续用窄 TDD 与必要邻域验证，保新旧失败历史，不跑全仓或真实付费样本。本只读阶段到此冻结。
