# Phase E / E4：Narrative handlers 详细实施规格（2026-09-28）

> **状态：实施前冻结的施工卡，后附 E4.1–E4.8 实施收据。** 原始合同与顺序先冻结，再从 RED 测试开始实现。
>
> **边界：** E4 只把已完成的 verified source reader、Phase C 叙述证据选择、Phase D transcript material/权利门接入 Automation Worker。E4 不写 catalog、不发布对象、不启动生产 Worker、不访问真实付费模型、不删除 raw/旧派生、不修改 revenue-forecast、filing-fetch、StockWiki 或 earnings-transcripts。最终对象写入和单 writer projector 属于 E5。

## 1. 第一性原理目标

E4 的输入不是“一个文件路径”，而是一个已经登记、带 SHA-256 和读取政策 pin 的来源版本。三个 job 只做三件事：

1. `source.narrative_select`：从已验证 bytes 完整扫描并选择少量叙述性证据；
2. `source.narrative_summarize`：只把已选证据交给单一 model process，生成同语种、带 evidence ID 的草稿；
3. `source.narrative_verify`：重新打开同一 raw、回放 locator、重验摘要和当前政策，生成唯一 canonical bundle 与逻辑 publish effect。

这三个阶段不得把永久路径、整份 PDF Markdown、整份 transcript 派生文本、全部行映射或模型原始响应写入结果。低价值文档在完整扫描后只产生小型 skip 收据。E4 的成功只表示来源身份、解析覆盖、locator 和摘要格式合同通过，不表示投资判断成立。

## 2. 已核实的复用面与缺口

### 2.1 直接复用

- `SourceVersionReader` 已按 `document_id + source_id + content_sha256` 读取 bytes，并在每次 open 时重验 catalog、root admission、runtime/read policy、实际长度和 SHA；公开结果不含路径。
- Phase C 已有 `parse_pdf`、`parse_transcript_text`、`select_narrative_evidence`、`verify_*_evidence_spans`、`validate_summary_draft`、`NarrativeEvidencePackage`、`SourceSummaryDraft`。
- Phase D 已有 `extract_transcript_material`，能把 TXT/HTML 原件确定性转换为未翻译 UTF-8 行并逐行映射回原始 byte locator；`authorize_transcript_actions` 会逐 action 独立判定。
- E1–E3 已提供原子 claim/heartbeat/finish、dependency promotion、Windows spawn、多进程隔离和 lease 恢复。

### 2.2 E4 必须补齐

1. `SourceVersionReader` 目前只接受 `preview | filing_reuse | source_export`；新增明确的 `narrative_derivation` purpose，并沿用 remediation、root/read-policy 和 exact-version 复核。`VerifiedContent.review` 与 `VerifiedVersionReceipt.review` 在该 purpose 下返回当前 source/policy-bound review snapshot；后者新增 optional default 字段以保持现有调用兼容。
2. PDF parser/replay 目前以 `Path` 为公开入口；新增 bytes 入口，内部共用同一解析实现。handler 永远不把永久路径传给 parser，也不落临时 PDF。
3. Worker 目前只给 handler `{"job_id", "subject_id"}`；改为强类型 `JobExecutionContext`，从一个一致性 DB snapshot 装载 event 与成功 dependency results。
4. `source.revision_registered` 目前仍计划旧的 `source.normalize → source.analyze`；改成三阶段 narrative DAG，并从默认 registry 移除这两个无实际 handler 的旧 source job。
5. 现有 legacy `llm_summarizer.py` 会围绕 normalized 文档写 `summary.md`，不适用于本流水线；E4 新建窄的、进程内注入的 summary model protocol。

## 3. 冻结合同

### 3.1 Source revision event

`source.revision_registered` 的 `payload_json` 必须是以下 exact-key schema；未知字段、缺字段、非 canonical JSON、路径字段或不匹配的 hash 一律拒绝：

```json
{
  "schema_version": "source-revision-event/1.0",
  "source_ref": {
    "schema_version": "2.0",
    "document_id": "...",
    "source_id": "...",
    "content_sha256": "<64 lowercase hex>",
    "byte_size": 123,
    "mime_type": "application/pdf"
  },
  "expected_read_policy_sha256": "<64 lowercase hex>",
  "source_metadata": {
    "source_class": "filing",
    "title": null,
    "document_kind": "annual_report",
    "language": "zh"
  },
  "transcript_policy": null
}
```

电话会议把 `source_class` 设为 `transcript`，并把 `transcript_policy` 设为：

```json
{
  "provider_id": "...",
  "source_url": "https://...",
  "content_class": "earnings_call_transcript",
  "expected_provider_policy_sha256": "<64 lowercase hex>"
}
```

冻结规则：

- `event.subject_type="source_revision"`，`event.subject_id=source_ref.document_id`。
- `event.input_hash = sha256(canonical_json(payload).encode("utf-8"))`；三份 job 沿用该 hash。
- `source_class` 只允许 `filing | transcript`；`language` 首版只允许 `zh | en | mixed`。缺失/未知语言不能默认为英文。`title` 允许 `null` 或非空捕获标题；不能用物理文件名补造标题，缺标题时 selector 依赖 catalog `document_kind` 路由。
- filing 的 `transcript_policy` 必须为 `null`；transcript 必须提供完整政策 pin。
- event 只保存逻辑身份和捕获事实，不保存 root、路径、文件名推断标题或 provider 政策文件位置。
- handler 每次运行都通过 reader 的 pathless metadata/read API 比对当前 source identity、kind、language、provider 和 URL；payload 不能自行扩权。

### 3.2 Automation execution snapshot

新增 automation-only 的不可变模型：

```text
ExecutionSnapshot
  job: Job
  attempt: Attempt
  event: Event
  dependencies: tuple[DependencyExecutionResult, ...]

DependencyExecutionResult
  job_id / job_type / handler_version
  attempt_id / attempt_no
  result: HandlerResult
```

`AutomationStore.read_execution_snapshot(claimed, now)` 在一个只读 transaction/snapshot 内完成：

1. gate 仍 enabled，generation 与 attempt 相同；
2. job 仍 RUNNING，claimed attempt 是最新、未完成且 token/lease 匹配；
3. `created_from_event_id` 指向存在且 identity 与 job 一致的 event；
4. 每条直接 dependency 都是 SUCCEEDED，并有一个最新 `outcome=succeeded` 的 canonical `HandlerResult`；
5. dependency job type 唯一，结果按 job type 稳定排序。

Store 不导入 source_catalog、parser、provider 或 model 类型。snapshot 读到 malformed/unknown dependency result 必须具名失败，不得返回部分上下文。

### 3.3 JobExecutionContext

`ExecutionContextFactory` 把 snapshot 转成：

```text
JobExecutionContext
  job / attempt / event
  payload: SourceRevisionEventPayload
  dependency_results: read-only mapping[job_type, HandlerResult]
  checkpoint: Callable[[], None]
```

规则：

- `HandlerExecutor.execute(job_type, context)` 只接受 `JobExecutionContext`；不保留 dict 兼容分支。现有测试 fake handler 一次性迁移到 context，避免两套生产接口长期并存。
- `checkpoint()` 只观察 heartbeat/取消/lease failure，不打开 catalog、不执行 parser/LLM、不在 handler 内发起另一套 claim。
- 每个 handler 在开始、verified read 后、耗时 parse/model 后和返回前调用 checkpoint。heartbeat 线程仍是唯一续租者。
- `select` 必须零 dependency；`summarize` 必须且只需一个 `source.narrative_select`；`verify` 显式依赖 `select` 和 `summarize` 两项，不能通过摘要结果间接复制 selection。
- context、payload、dependency decoder 都拒绝任何永久路径；没有 handler 可以从 context 获得 wiki root 或 raw path。

### 3.4 三类 job registry

| job type | llm/network | effect | attempts | retryable | blocked human | terminal |
|---|---|---|---:|---|---|---|
| `source.narrative_select` | false/false | artifact_only | 3 | `IO_TRANSIENT, STORE_BUSY, LEASE_LOST` | `PARSER_INCOMPLETE, SOURCE_UNAVAILABLE` | `INPUT_SCHEMA_INVALID, SOURCE_HASH_MISMATCH, POLICY_DENIED, UNSUPPORTED_SOURCE_TYPE, RESULT_TOO_LARGE` |
| `source.narrative_summarize` | true/true | artifact_only | 3 | `MODEL_TIMEOUT, MODEL_RATE_LIMIT, IO_TRANSIENT, LEASE_LOST` | `MODEL_NOT_CONFIGURED, PROMPT_REVIEW_REQUIRED` | `INPUT_SCHEMA_INVALID, DEPENDENCY_INVALID, POLICY_DENIED, MODEL_RESPONSE_INVALID, SUMMARY_INVALID, RESULT_TOO_LARGE` |
| `source.narrative_verify` | false/false | knowledge_write | 2 | `IO_TRANSIENT, STORE_BUSY, LEASE_LOST` | `LOCATOR_REPLAY_FAILED, SOURCE_UNAVAILABLE, PROMPT_REVIEW_REQUIRED` | `INPUT_SCHEMA_INVALID, DEPENDENCY_INVALID, SOURCE_HASH_MISMATCH, POLICY_DENIED, SUMMARY_INVALID, RESULT_TOO_LARGE` |

补充规则：

- summarize 声明 `network=True`，即使测试使用 replay adapter；规划时 policy 必须同时显式允许 LLM 和 network。默认 policy 继续拒绝。
- 三类 handler 的 `allowed_paths=()`；verified reader 的读取权限不伪装成 effect path allowlist。
- verify 的 effect 是内部 catalog publish 意图，逻辑 target 不含文件路径；E4 不 apply effect。
- 未列入 registry 的 error code 即 fail closed；不能用 `HANDLER_EXCEPTION` 代替可预期业务错误。

### 3.5 DAG

```text
select ───────► summarize
  │                │
  └──────────────► verify
```

- 三个 job 一次 materialize；root 为 READY，另外两个为 PLANNED。
- verify 显式依赖 select 和 summarize，便于一次 snapshot 取得两类严格结果，同时防止 summary 复制全部 evidence。
- `source.normalize`、`source.analyze` 从该 event mapping 和默认 registry 删除；不再生成无 handler 的旧 source DAG。
- 相同 event 重放得到相同 temp IDs/job keys/dependency set；payload 或 handler version 改变必须产生新 identity，不能覆盖旧 job。

## 4. 结果合同与空间上限

所有结果使用 automation `canonical_json`。decoder 要求 exact keys、schema version、source/policy identity 与上下文完全一致。编码后先做 byte cap，再构造成功 `HandlerResult`；禁止截断、压缩成不可审计 blob 或落外部临时文件。

### 4.1 Select result：`narrative-select-result/1.0`

包含：

- source ref、read policy pin、source class/title/kind/language；
- parser/selector name + version；
- `selection_status`、`coverage_complete`、page/line/table scan counters、dropped-financial count；
- 仅选中的 `EvidenceSpan.to_dict()`；
- 与 source SHA、review policy hash 绑定的当前 prompt-injection review snapshot；
- transcript 时的 material lineage 摘要和“仅与已选 evidence 对应”的原始 byte locator bindings；
- 本次 transcript action policy hash 与每个 action 的 evidence hash；
- `summary_scope="selected_evidence_only"`。

明确不包含：重复的 `summary_input` 正文、未选 units、整份 transcript text、全部 transcript line map、raw bytes、path。摘要 handler 从已选 EvidenceSpan 临时构造 prompt。上限 `1 MiB`；skip 结果目标 `<=8 KiB`。

### 4.2 Summary result：`narrative-summary-result/1.0`

包含：

- source ref、language、`translate=false`；
- `status=completed | summary_not_needed`；
- completed 时为严格序列化的 `SourceSummaryDraft`，skip 时 draft 为 null；
- model adapter/model/prompt version 和响应内容 SHA，不保存原始响应；
- transcript 的 generate_summary 权利政策/evidence hash。

上限 `64 KiB`。skip 必须零 model call。输出为空、语言漂移、未知 evidence ID、角色错误或 needs-review 规则错误均不得成功。

### 4.3 Verify result：`narrative-bundle/1.0`

包含：

- source ref、read/provider policy pins；
- selection/coverage/counters；
- 已选 EvidenceSpans；
- summary draft 或 `summary_not_needed`；
- parser/selector/material/model/prompt/bundle producer versions；
- replay contract 与 transcript 已选 byte bindings；
- `quality_status=verified | needs_review | skipped_no_narrative`。

verify result 同时返回：

- `bundle_sha256 = sha256(canonical_bundle_bytes)`；
- 恰好一个 `Effect(status=PENDING)`，`target="narrative_bundle/<work_key>"`；
- effect key 和 work key 都由 source identity、producer/policy versions 确定性计算；
- `created_at` 使用 job/event 的固定时间，不使用重试时钟，以保证重放一致。

不生成 `ArtifactRef.path`。完整 bundle 上限 `1.25 MiB`，skip bundle 上限 `16 KiB`。E5 projector 以后通过 `effect.job_id` 读取该 verify attempt result，校验 bundle hash 后发布。

### 4.4 递归路径泄漏检查

三个 decoder/encoder 都递归拒绝：

- key 为 `path, absolute_path, local_path, file_path, root_path, wiki_root, catalog_path`；
- 值为 drive absolute path、UNC path、`file://` URI；
- 未声明的 location/root 对象。

允许业务 locator，例如 `page:12`、`line:31-35`、`byte:100:220`，以及 HTTPS `source_url`。测试必须同时覆盖拒绝物理路径和允许 locator，避免误伤证据坐标。

## 5. Handler 逐步算法

### 5.1 Select

1. checkpoint；严格解码 event，核对 event/job identity 与零 dependency。
2. 对 transcript 从 runtime 固定配置根加载当前 `config/provider_use_policy.json`，要求 hash 等于 event pin；按注入 clock 的当前 UTC 日期逐项授权 `derive_text`、`select_evidence`。
3. `SourceVersionReader.open_version(..., purpose="narrative_derivation", expected_read_policy_sha256=...)`；比对返回 bytes、ref、pathless metadata，并读取与 exact source SHA/policy 绑定的 prompt-injection review snapshot。
4. PDF 调用 `parse_pdf_bytes`；transcript 调用 `extract_transcript_material`、`material.verify(original)`、`parse_transcript_text(material.text_utf8)`。
5. checkpoint；运行唯一 Phase C selector。只有 `coverage_complete=true` 且没有 parser error 时才允许 `skipped_no_narrative`。
6. transcript 只投影已选 span 覆盖的 line→original byte bindings；不持久化未选 mapping。
7. 严格编码、路径泄漏检查、size cap、checkpoint，返回成功。parser 不完整进入 `PARSER_INCOMPLETE`，不能伪装 skip。

### 5.2 Summarize

1. checkpoint；严格解码 select dependency，核对 source/policy/version/cap。
2. 用 `verify_version(..., purpose="narrative_derivation")` 重验 exact source/read policy，防止在外发前使用已撤回来源；检查 receipt 同时返回的当前 prompt-injection review，只有合法的 `not_detected | detected_and_ignored` receipt 才可进入模型，缺失、非法或与 source SHA/review policy 不绑定时返回 `PROMPT_REVIEW_REQUIRED`。
3. transcript 重新加载当前 provider policy，只授权本次 `generate_summary`；select 阶段的许可不能转移。
4. 若 select 为 skip，返回 `summary_not_needed`，并断言 model adapter 调用次数为 0。
5. 从 EvidenceSpans 在内存构造 bounded structured request；明确 `translate=false`、目标语言等于 source language、只能引用给定 evidence IDs。来源正文只能进入 data 字段，不能拼进 system/developer 指令。
6. child-local model adapter 执行。`MODEL_NOT_CONFIGURED` 在任何网络调用前返回；timeout/429 具名 retry；不自动切换未知 provider。
7. 用 `validate_summary_draft` 验 source/language/citations/roles/review status；丢弃原始模型响应，只记录其 hash 和结构化草稿。
8. cap/checkpoint 后返回。

### 5.3 Verify

1. checkpoint；严格解码 select + summarize 两个直接 dependency，核对彼此与 event identity。
2. 重新 `open_version(..., purpose="narrative_derivation")` 获取已验证 bytes。
3. transcript 重新加载当前 policy；若有摘要，重验 `derive_text + select_evidence + generate_summary`，skip 则只重验实际执行过的前两项。政策撤销发生在 model 后也必须阻止 publish effect。同时重验 prompt-injection review receipt 仍绑定当前 source SHA/review policy；失效时不产生 effect。
4. PDF 用 bytes replay；transcript 重新提取 material、验证 original、重跑 parser，并检查已选 original byte bindings。
5. 要求全部 evidence ID locator replay 成功；再次运行 summary validator。
6. 构造 canonical bundle、hash、work key 和一个逻辑 effect；不写对象、catalog、legacy wiki 或任何路径。
7. cap/checkpoint 后返回；任何 replay/summary/policy 失败均为零 effect。

## 6. Model adapter 边界

新增最小协议：

```text
NarrativeSummaryModel.summarize(NarrativeSummaryRequest) -> NarrativeSummaryResponse
```

- request 只有 source identity、language、translate flag、已选 evidence 与 prompt version；没有路径、catalog、raw 全文。证据放在结构化 data envelope，adapter 的 system/developer 指令固定且不接受来源文本覆盖。
- response 只有结构化 draft、adapter/model ID、响应 hash；没有 provider SDK object。
- `ReplayNarrativeSummaryModel` 和 deterministic fake 放在测试 support；生产 runtime factory 可选构造真实 adapter，但 E4 不做真实 API 调用。
- model client 只在 model worker spawn 后构造；compute worker runtime 若持有 model adapter 继续由 E3 hard validation 拒绝。
- 凭证检查是 adapter construction/first-call 的显式状态，不读取或记录 key 内容。

## 7. TDD 实施顺序

小步先 RED 后 GREEN，但只在 E4 完成时跑一次 E4 合并门；不为每个 helper增加人工复核。

### E4.1：strict contracts 与 path-leak gate

先新增：

- `tests/unit/test_narrative_job_contracts.py`
- event/result exact keys、canonical input hash、source/policy identity、unknown schema；
- 三种 size cap 边界值；
- 递归物理路径拒绝和 page/line/byte locator 允许；
- EvidenceSpan/SummaryDraft round trip；
- transcript 只保存 selected bindings、不保存全文/全部行图。

实现候选：`automation/narrative_contracts.py`。此步不接 Worker。

**E4.1 实施收据（2026-09-28）**

- RED：合同模块不存在，12 项测试在 collection 处按预期失败；实现首轮为 **3 passed / 9 failed**，暴露 selection 计数字段使用无序集合导致的位置错配。
- GREEN：event/source/policy exact schema、canonical input hash、selected-only result、summary/bundle dependency validation、四类 byte cap、skip、同语种、`translate=false`、transcript selected bindings 和递归 path-leak gate 已实现，聚焦 **12 passed**；加 automation models 回归为 **41 passed**。
- `summary_input`、整份 transcript text/line map 和模型原始响应不在合同中；EvidenceSpan 是唯一持久化的 selected text 载体。
- Ruff、C901 `<=10` 与 strict mypy 通过；所有 `C:\cwt\m3-e4-contract-*` 根已在 finally 后清理。此步未接 Worker、reader、provider/model 或 catalog。

### E4.2：一致性 execution snapshot 与 context

先新增/调整：

- `tests/unit/test_automation_execution_context.py`
- `tests/integration/test_automation_execution_snapshot.py`
- stale token/generation/expired lease/非最新 attempt 拒绝；
- event/job hash 漂移、缺/多/失败 dependency、malformed result 拒绝；
- 用两个 Store connection 在 event/dependency 更新竞争下证明只返回旧完整或新完整 snapshot，不返回混合状态；
- 所有现有 fake handler 接收到 context，不再接收到 dict。

实现：`automation/execution_context.py`、`automation/execution_snapshot.py`、Store 的单一 read operation，以及 Worker/HandlerExecutor 的一次性接口迁移。

**E4.2 实施收据（2026-09-28）**

- RED：两个新模块不存在，context/snapshot 测试在 collection 处失败；首轮实现 **11 passed / 2 failed**，两项均定位为夹具没有满足新合同，而不是放宽生产校验。
- GREEN：Store 在一个显式 SQLite read transaction 中读取 runtime gate、当前 claim、source event 与全部直接前置结果；stale token/generation、过期 lease、非最新 attempt、event/job identity 漂移、未成功或损坏 dependency 均 fail closed。
- Worker 只向 handler 传冻结的 `JobExecutionContext`；payload 和 dependency mapping 不可变，narrative 三种 job 的前置类型集合必须精确匹配，checkpoint 复用 heartbeat failure boundary。`WorkerStore` 与 handler callable 均为显式窄接口。
- 双连接竞争测试证明 snapshot 只观察一个 SQLite read view。旧 multiprocess helper 的同一 source 下重复建 event 做法违反 event natural key，已改为下游复用父 event；生产 natural key 没有放宽。
- 聚焦 context/snapshot/Worker/Supervisor/multiprocess 为 **43 collected，修正损坏 gate 夹具后全绿**；最终全部 automation、narrative contract、race、multiprocess、CLI 与 Store boundary 为 **244 passed in 42.93s**。
- 四个边界模块 strict mypy、修改文件 Ruff、C901 `<=10`、config doctor 与 diff check 全绿；所有 `C:\cwt\m3-e4-*-*` 本轮测试根均在 finally 后精确清理。未接 reader/provider/model/catalog，production Worker 未启用。

### E4.3：registry 与三阶段 DAG

先改 planner/registry tests：

- source event 精确产生三 job/三 edge（select→summarize、select→verify、summarize→verify）；
- old normalize/analyze 不再出现；
- default policy 拒绝 LLM/network，显式允许后规划成功；
- handler versions/error sets/attempt budgets 完全等于本卡；
- 重复 materialize identity 不变。

再改 `registry.py`、`planner.py`。不注册实际 handler 前，runtime factory 不得启用这些 job。

**E4.3 实施收据（2026-09-28）**

- RED：先将既有 planner tests 改成 exact narrative registry/DAG 合同，得到 **9 failed / 14 passed**；失败全部对应旧 `source.normalize/source.analyze` specs、两阶段映射和仅允许 LLM 的政策假设。
- GREEN：默认 registry 删除两个旧 source job，新增三项冻结 spec；`source.revision_registered` 精确生成 select、summarize、verify 三 job 和三 edge。默认 policy 及仅 `allow_llm` 都因 network 声明 fail closed，只有同时显式允许 LLM/network 才可规划。
- scheduler 重复 materialize 首次固定为 3 jobs/3 dependencies，第二次为 0 新增且 3/3 existing；controller shadow 只把 select 置 READY，另外两项保持 PLANNED，并验证 verify 的两个直接前置。
- 通用 Worker/恢复测试改用 `timer.execute_step`，真实多进程并发测试改用只存在于 test factory 的 `test.compute/test.model` specs，避免用未实现的 narrative handler 制造假绿，也没有把 test job 注册进产品 registry。
- 聚焦 planner/registry/scheduler/controller/Worker/Supervisor/真实 multiprocess 为 **70 passed in 25.36s**。三个修改产品模块 strict mypy、Ruff 与 C901 `<=10` 全绿；CLI 的 read-only plan 显式 admission 两项能力，但不会调用网络或模型。

### E4.4：reader purpose 与 PDF bytes facade

先新增 contract/unit tests：

- `narrative_derivation` purpose 的 open/verify 都通过 exact read并返回 source/policy-bound review snapshot；remediation/read-policy/root/source status/hash drift 继续拒绝；
- 未知 purpose 继续拒绝；公开结果无路径；
- `parse_pdf(path)` 与 `parse_pdf_bytes(bytes)` 结果完全一致；
- `verify_pdf_evidence_spans_bytes` 与 path facade 一致；hash 不匹配拒绝；
- monkeypatch 临时文件 API，证明 bytes 路径不落盘。

再让 path/bytes facade 共用一个内部 PyMuPDF document parser，禁止复制选择规则。

**E4.4 实施收据（2026-09-28）**

- RED：新 PDF bytes 测试因 `parse_pdf_bytes` 不存在在 collection 失败；reader 合同为 **2 failed / 23 passed**，分别命中 unsupported purpose 与 remediation gate 未覆盖。
- GREEN：`narrative_derivation` 进入 verified reader 的显式 purpose 集合，并与 filing reuse/source export 一样受 remediation、当前 root/source/read-policy/SHA 约束；open 与 verify 都返回同一 source SHA/policy 绑定的 `ReviewSnapshot`，公开对象不含路径。
- `parse_pdf(path)` 与 `parse_pdf_bytes(bytes)` 共用 `_parse_pdf_document`；bytes 路径先核对 SHA，再以内存 stream 打开 PyMuPDF。replay 同样新增 bytes binding/plan，未复制 selector 或 locator 匹配规则。
- 测试 monkeypatch `Path.write_*` 和 Python tempfile API 后，parse/replay 仍通过；错误 SHA 在解析前拒绝。PDF bytes + 原有 narrative parser 为 **37 passed**，reader contract **25 passed**。
- 直接 reader/export 消费回归与真实 bytes E2E **41 passed in 22.77s**。三个产品模块 strict mypy 通过，reader 已加入 CI/pre-commit mypy 范围并实际触发钩子；PDF 模块 Ruff/C901 `<=10` 与 repository complexity ratchet 全绿。reader 既有四个大函数复杂度债务未借本切片扩张为第二套 reader。

### E4.5：select handler

先 RED 覆盖：

- 年报/招股书/IR 的 PDF bytes 正常选择；
- transcript TXT/HTML 原件→material→选择→selected byte bindings；
- 完整低价值文档可 skip；parser error/coverage incomplete 不可 skip；
- transcript 缺 `derive_text` 或 `select_evidence`、政策 hash 变化/撤销立即拒绝；
- source hash/read-policy/metadata 漂移拒绝；
- cap 与路径泄漏失败零 effect。

再实现独立 select handler 和错误映射；不写 DB/catalog 文件。

**E4.5 实施收据（2026-09-28）**

- RED→GREEN：模块缺失先在 collection 失败；首轮实现后 15 项通过。补入策略撤销、selected-only binding 和损坏 PDF 后，损坏 PDF 用例以未捕获 `FileDataError` 精确变红（1 failed / 16 passed），增加窄 parser 错误映射后 **17 passed**。
- handler 只接 `JobExecutionContext`、verified bytes 与注入 ports。年报、招股书、IR PDF 和 TXT/HTML transcript 均从内存处理；不接 Path、不落 temp、不写 DB/catalog/artifact/effect。打开内容重新计算 SHA，source/read-policy/metadata/provider-policy 任一漂移均 fail closed。
- transcript select 独立要求当前 policy 同时授权 `derive_text` 与 `select_evidence`；撤销或缺任一动作均拒绝。结果只保存 selected EvidenceSpan 对应的 original byte ranges 和无正文 lineage，不保存整份 material、`summary_input` 或模型输入。
- 完整低价值文档产生小型 `skipped_no_narrative`；parser errors、opaque/incomplete coverage 与不可回放 transcript 不得伪装成 skip。结果 cap/path leak 都在零 effect 下失败。
- 直接依赖组合门覆盖 handler、strict contracts、PDF bytes、selector、provider policy 与 transcript material，共 **97 passed in 1.64s**。Ruff、C901 `<=10` 与 strict mypy 全绿；CI/pre-commit mypy 范围扩至 E4 automation boundary。
- strict mypy 首次暴露 summary contract 的 `claim_type/modality/status` Literal 收窄缺失；新运行时负例先得到 2 failed / 1 passed，修复后非法投资结论型 claim、非法 modality 和 `accepted` draft status 均被合同拒绝，没有用 cast 掩盖未验证输入。

### E4.6：summarize handler

先 RED 覆盖：

- deterministic fake/replay 同输入得到同 canonical result；
- skip 零 model call；zh/en/mixed 保持语言，`translate=false`；
- 未知 evidence ID、角色混淆、空 claim、unstable locator 未标 review 拒绝；
- 无凭证在网络前 `MODEL_NOT_CONFIGURED`；prompt review 缺失/非法/绑定漂移在网络前 `PROMPT_REVIEW_REQUIRED`；429/timeout 可重试且有界；malformed response 不重试；
- transcript 必须单独拥有 `generate_summary`；select 权限不能替代；
- prompt 仅包含已选 evidence，没有 raw 全文/路径。

再实现 model protocol、adapter errors 和 summarize handler。

**E4.6 实施收据（2026-09-28）**

- RED：新测试因 `automation.narrative_model` 不存在在 collection 失败。首轮实现收集 18 项并得到 2 failed / 16 passed；两项均为 fixture 与正式合同不一致（把 line range 当 EvidenceCoordinates 字段、把 byte range 写成数组），修正夹具而未放宽合同后为 18 passed。
- 增加模型 port、canonical selected-evidence-only request 与 opaque response bytes 边界。固定指令和 evidence data 分离；request 只含 selected spans/source identity/language/title/kind，不含全文、路径或 `summary_input`。原始 model response 不持久化，只保存 SHA、adapter/model/prompt version。
- missing model 在 review/provider/model 调用前进入 `MODEL_NOT_CONFIGURED`；skip 为零 model、零 review lookup、零 provider-policy lookup。zh/en/mixed 原样输出，`translate=false`。
- prompt review 当前值必须与 select snapshot 完全一致且已审核；transcript 重新按当前 policy 单独授权 `generate_summary`。select 的 `derive_text/select_evidence` 或下载许可不能替代，policy hash 漂移/撤销在 model 前拒绝。
- timeout/429 每次 handler 只调用模型一次并交给 durable job 的三次 attempt 上限；非法 UTF-8/JSON、重复 key、transport cap、prompt version 与路径泄漏均 terminal 且不重试。未知 evidence、角色混淆、空 claim、unstable locator 未标 review 均为 `SUMMARY_INVALID`。
- 扩展后 handler 单测 **23 passed**；select/contracts/parser/provider/material 直接依赖组合门 **118 passed in 2.08s**。新增两模块 strict mypy、Ruff、C901 `<=10` 全绿并纳入 CI/pre-commit。

### E4.7：verify handler 与 effect intent

先 RED 覆盖：

- PDF/transcript locator 全量回放；任一失败零 effect；
- transcript selected byte binding 与 original 不匹配拒绝；
- model 后撤销 provider policy 或失效 prompt review 阻止 effect；
- select/summary identity/version/cap 漂移拒绝；
- 相同依赖重复执行产生 byte-identical bundle/hash/effect key；
- skip bundle 小于 16 KiB；完整 bundle 小于 1.25 MiB；
- 成功恰好一个 PENDING effect，target 只含 logical work key；无 ArtifactRef path、无 catalog 写入。

再实现 verify handler 和 runtime registry facade。E5 前不实现 effect apply。

**E4.7 实施收据（2026-09-28）**

- RED：新 verify suite 因 `automation.narrative_verify` 缺失在 collection 失败。首轮实现后 verify+select regression 为 2 failed / 26 passed；失败均为测试端对 frozen Mapping 直接 canonicalize、以及低价值 fixture 未复刻 select 的 full-table completion，修正夹具后全绿，未放宽产品合同。
- 抽出 `narrative_source_guard.py` 供 select/verify 共享 source ref、实际 bytes SHA、read-policy、metadata 与 review snapshot 绑定，避免两个 handler 复制底层 root/路径判断。select 原有 17 项随 refactor 保持全绿。
- verify 从同一 execution snapshot 读取 select+summary，检查 source/read-policy/metadata、parser/selector/prompt version 和 transcript policy pin；重新 open verified bytes 后再核 current prompt review 与所有实际 transcript actions。
- PDF 对全部 selected locators 运行 bytes replay；transcript 重建 deterministic material，核 lineage、span line range、每个 original byte range，再运行 speaker-block replay。任一 locator、binding、review 或 policy 失败均零 artifact/零 effect。
- 成功构造 canonical `NarrativeBundle`，skip 小于 16 KiB、普通 bundle 小于 1.25 MiB；恰好一个 deterministic `PENDING` effect，target 为 logical URN，`intended_after_hash` 等于 bundle canonical hash，不含物理路径，也不 apply/write catalog。
- handler/refactor suite **29 passed**；select/summarize/contracts/parser/provider/material/reader 直接依赖组合门 **157 passed in 7.37s**。新增/改模块 strict mypy、Ruff、C901 `<=10` 全绿并纳入 CI/pre-commit。

### E4.8：隔离集成链

在 `C:\cwt\m3-e4-<nonce>` 建立短根，运行：

1. 临时 catalog 注册一个小 PDF、一个 transcript、一个低价值 fixture；
2. 创建严格 source revision events，materialize 三个 DAG；
3. P1 compute/model 顺序执行到三个 verify job 留在 VERIFYING/outbox pending；
4. replay model 产生固定草稿；
5. 断言 dependency result 经 DB snapshot 传递、source locator 全部回放、skip 不调模型、没有 catalog artifact/version row；
6. 同 event 重放不增加 job/effect/outbox；
7. 分别注入 reader refusal、model 429/timeout、policy revoke，断言具名状态与零错误 effect；
8. 测试结束验证 exact root 位于 `C:\cwt` 且名称以 `m3-e4-` 开头，在 `finally` 清理并确认同前缀为 0。

E4 集成不替代 E6 四份真实文档/P2 并发，也不 apply projector。

**E4.8 实施收据（2026-09-28）**

- 新增 `automation/narrative_runtime.py` 作为显式 composition root，依赖 reader、model、catalog review loader、provider policy loader 与日期函数；只把三类 handler 注册到注入的 registrar，不创建全局状态或生产 Worker。
- 新增 `tests/integration/test_narrative_runtime_e2e.py` 与固定 replay model fixture。使用独立临时 catalog/Automation DB 和正式 `companies/.../raw/` + `company_raw_v1` adapter；4 个隔离场景覆盖 PDF 年报、低价值 IR skip、TXT transcript、幂等 pending outbox、reader policy refusal、429/timeout、模型生成后 provider revoke。原始字节 hash 不变，skip 不调用模型，失败无 effect，Catalog 不新增 artifact/version。
- RED 阶段先确认 runtime module 缺失；后续夹具错误定位为使用了不存在的 `earnings_call_transcript` 文档类型和不符合 company_raw 目录的 fixture。按真实契约改成 `investor_call_transcript` 及 raw 路径后，E2E 为 **4 passed**。
- E4 合并门覆盖叙述 handlers/contracts、全部 automation unit、Store/runtime race、Windows multiprocess、provider policy、source reader、transcript material/import：**420 passed in 70.65s**。Ruff、C901、runtime strict mypy 全绿；config doctor healthy；host assumption guard `new=0`；`git diff --check` 通过。
- runtime composition 尚未接入 CLI/production；进程检查未发现运行中的 production Worker。E4 测试及 gate 只写短根临时目录，结束后 `C:\\cwt\\m3-e4-*` 为 0；只修改本卡、CI 检查列表、runtime/test 文件，没有触及 raw、production catalog 或生产配置。
- RF 边界只读复核保持 `fcap@ee0a82bf`，其既存工作区改动未触碰。详见本计划 progress 的跨仓状态核对。

## 8. 测试门与审查节奏

E4 完成时只跑以下合并门：

1. E4 新增 unit/integration；
2. automation 全部 unit + Store/race/multiprocess integration；
3. Phase C narrative annual/prospectus/IR/transcript 与 locator suites；
4. Phase D provider policy/material/import 相关离线 suites；
5. Ruff；新增/改边界模块 strict mypy；新函数 C901 `<=10`；
6. config doctor、host guard、production pause/runtime absence；
7. RF 只读 boundary check；
8. `C:\cwt\m3-e4-*` 为 0、production raw/catalog/config hash 不变。

不在每个 helper 后重跑 200+ 全集；失败只跑对应 RED 和直接依赖，E4.8 后统一跑上述一次。E-B 仍是 E3–E7 唯一大节点集中审查。

## 9. 精确文件变更表

| 文件 | 动作 | 禁止事项 |
|---|---|---|
| `automation/narrative_contracts.py` | 新建 strict event/result/bundle schema、cap/path leak | 不导入 Store/catalog/model SDK |
| `automation/execution_snapshot.py` | 新建 automation-only snapshot models/SQL helper | 不拥有 transaction、不解析 source payload |
| `automation/execution_context.py` | 新建 context factory/dependency decoder/checkpoint | 不打开 raw/路径 |
| `automation/store.py` | 增加单一 read snapshot operation | 不逐次公开读拼上下文 |
| `automation/worker.py` | executor 一次性迁移到 context | 不保留 dict 双接口 |
| `automation/registry.py` | 三类 narrative spec，移除旧 source job | 不注册 research writer |
| `automation/planner.py` | source event 三阶段 DAG | 不建立跨仓 job |
| `automation/narrative_model.py` | 窄 request/response/protocol/error | 不共享 client、不翻译 |
| `automation/narrative_handlers.py` 或 `automation/handlers/narrative_*.py` | 三 handler 与 runtime 注册 | 单函数 C901≤10；不写 catalog |
| `source_catalog/source_reader.py` | `narrative_derivation` purpose | 不返回路径、不放松现有 purpose |
| `source_catalog/narrative_evidence.py` 及已拆 parser 模块 | bytes parse/replay facade | 不复制 selector、不落 temp PDF |
| `tests/support/narrative_model_fixture.py` | deterministic fake/replay | 不导入生产 provider SDK |
| E4 unit/integration files | 依本卡新增 | 不使用 production root/config |

实现时若单个 `narrative_handlers.py` 超过约 300 行或任一函数 C901>10，立即按 select/summarize/verify 拆文件；不以复杂度豁免通过。

## 10. 回退、收据与开始条件

- E4 默认仍 paused。回退代码只需移除 runtime handler registration；已存在的 event/job/attempt 审计记录保持可读，不删除 raw。
- E4 没有 catalog visible 写入，因此失败回退只清理精确测试根和未提交代码。
- 实施收据必须记录：RED→GREEN 次数、测试计数/耗时、三种 cap 实测、skip model call=0、source/policy drift 反例、locator replay 数、effect/outbox 幂等、测试根清理、production 不变和 RF 只读状态。

开始 E4.1 前必须满足：

- [x] E0–E3 已完成且 commit；
- [x] production Worker paused、runtime absent；
- [x] RF 当前仍 `fcap@ee0a82bfd1ee`、`origin/main@3a69f9c5b651`，既存 dirty planning/assurance 内容只读未碰；
- [x] 本卡先于 E4 产品代码建立；
- [x] 本卡随纯规划变更单独提交且工作树可解释；
- [x] 从 E4.1 RED 开始实现，不跳到 handler happy path；E4.1–E4.8 均完成。
