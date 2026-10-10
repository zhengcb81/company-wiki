# W04 有界 failed-final 诊断：真实接口最小设计

日期：2026-10-11。状态：**只读契约设计，未实施、未关闭 W04**。ROOT 已发布候选主线 795a076d；本设计读取 MAIN 隔离树真实接口并进行纯内存序列化试验，未调用供应商。实施与现有 W04 PWF 更新由 ROOT 统一承担，不新发卡、不造调用账本。

## 1. 实际责任链与边界

当前源码不存在 `CallOutcome` 类型。实际链为：

`NarrativeHTTPModel._response(body: bytes)` → `ModelOutputTruncatedError` → `BudgetedNarrativeCaller.generate / _settle` → `NarrativeBudgetCallError` → `NarrativeSummarizeHandler._failure` → `HandlerResult.result` → `Store.finish_attempt / _update_finished_attempt` → `canonical_json(result.to_dict())` 写入 `attempt.result_json` → `narrative_batch._attempt_model_diagnostics`。

不新增 `CallOutcome`、第二账本、结果文件、完整响应副本或每个 helper 的协议。新 typed 对象只负责本次失败诊断；费用继续由既有 reservation 和 HandlerMetrics 负责，正式摘要仍由原成功路径负责。

建议在既有模型合同模块定义一个冻结 scalar DTO（例如 `FailedFinalDiagnostic`），由 HTTP 异常与 caller 异常各增加默认 `None` 的 `failed_final` 属性，同一对象传递；summary 将其隔离序列化进已有 `result={"failed_final": ...}`。DTO 名称是建议，ROOT 可按实际命名选择；下列字段语义与容量规则应冻结。

## 2. 最小字段与类型

建议对象 wire schema：`narrative-failed-final/1`，只含以下八个字段，不重复 usage、请求、model/config 身份或错误描述。

| 字段 | 类型 | 唯一语义 |
|---|---|---|
| `schema_version` | 固定字符串 | `narrative-failed-final/1` |
| `provider_response_sha256` | 64 位小写 hex 或 null | 完整已接收 HTTP entity **原始 bytes** 的 SHA-256 |
| `provider_response_bytes` | 非负 int 或 null | 同一完整原始 entity 的实际字节数 |
| `final_content_sha256` | 64 位小写 hex 或 null | 已观察到 `message.content` 字符串、按 strict UTF-8 编码后的完整 bytes SHA |
| `final_content_bytes` | 非负 int 或 null | 同一 decoded final 字符串的完整 UTF-8 长度 |
| `final_prefix` | str 或 null | 原 final 的连续 codepoint 前缀；未观察到 final 时 null |
| `prefix_bytes` | 非负 int | 前缀 strict UTF-8 长度；无前缀为 0 |
| `clipped` | bool | 对已观察的 final，`prefix_bytes < final_content_bytes`；没有 final 时 false，**不表示内容完整** |

整数严格排除 bool，哈希严格检查格式，字段不开放任意 provider 文本。HTTP 原响应长度由已经执行的响应上限限定；final 长度由现有 `MODEL_RESPONSE_MAX_BYTES` 限定。所有下游保留 scalar 隔离值，不暴露异常的任意 `__dict__`。

### 不可混淆的三种观测

1. 有完整 `body` 和 final 文本：两个 SHA 分开计算，provider SHA 包含 JSON envelope 的原 bytes，final SHA 仅对 decoded `content.encode("utf-8")`。不对 parsed payload 重新 dumps 后冒充原 wire；不 strip、NFC 或更改换行。
2. 显式 `content=""`：观察到了 0 字节 final，`final_content_bytes=0`、SHA=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`、prefix=""、prefix_bytes=0、clipped=false。length 的主错误仍 `MODEL_OUTPUT_TRUNCATED`，非 length 空正文仍保持现有 `MODEL_RESPONSE_INVALID / response_stage=empty_content`。
3. `content=None` 或未观察到 final：final 的 SHA/bytes/prefix 都为 null，prefix_bytes=0，clipped=false。即使旧 decoder 为分类临时把 None 转成 ""，也必须在转换前记下未观察语义；不能用旧默认 `content_bytes=0` 推导“观察到空字符串”。新 null 分支的 legacy 内容计数应保持 unknown/省略，不伪造 0；旧封存计数不回填。

直接构造的模型异常/fixture 若没有完整原响应 bytes，`provider_response_sha256 / provider_response_bytes` 保持 null。可已知 final 而未知 wire，两者独立；不得从 final 或 canonical payload 假造 response SHA。超限中断读取、超时或 JSON 无法解析，也不能把读到的部分 body 标成完整响应。首片只扩充明确观察到的 length/空 final 责任，其余旧错误默认无新对象，不强行统一。

escaped lone surrogate 不是 strict UTF-8 final，沿用当前 typed invalid-envelope 分类；不以 replacement/ignore 编码后伪造哈希。合法 emoji 与组合 Unicode 按原 decoded codepoints 保留；UTF-8 安全前缀不承诺 grapheme 完整，更不作为可发布引文。

## 3. 容量是整个 attempt JSON，而不是原文 prefix

硬不变量：**新记录 `len(canonical_json(handler_result.to_dict()).encode("utf-8")) < 16_384`**，最多 16,383 字节；计量整条持久化 HandlerResult，包含 outcome、result、artifacts/effects 空数组、metrics 与静态 error。现有 store 在 `automation/store.py:445` 就使用这一个 canonical 序列化；沿用 ensure_ascii=False、sort_keys=True、紧凑 separators、allow_nan=False，不建立第二个序列化口径。

固定 16KiB 原文前缀一定不合格。引号/反斜线、CR/LF 和 C0 controls 会变成 JSON escape；NUL 一个原 UTF-8 字节在 JSON 中占六字节。中文、emoji、组合 Unicode 也必须按 UTF-8 bytes，而非字符计数。不能截断已生成的 JSON 文本或其编码 bytes，否则可能破坏 JSON/UTF-8。

### 最小拟合算法

- HTTP 只计算原 response/final 的全长和 SHA 一次，并先取不超过目标控制容量的有效 final codepoint 前缀；不将全部 body 留进异常。prefix 仅在有限内存中，DTO 的最终持久化版本在 summary envelope 已知后确定。
- summary 先构造 **空 prefix** 的完整 failure HandlerResult（保留两个 SHA、完整长度、真实 metrics、主 error；final 未观察时 prefix=null）。该新失败路径 error 使用现有固定说明，artifacts/effects 为空，故 fixed envelope 足够小。
- 在已有前缀的 codepoint 边界上二分最长 `k`，每次构造完整候选 HandlerResult，调用真实 `canonical_json(...).encode("utf-8")` 判断 `<16_384`。每次同步 `prefix_bytes` 与 clipped，再测**整个** envelope；选最终值后再测一次硬界。
- 若上游已经截出有限前缀，clipped 必须与**完整 final_content_bytes** 比较，不能与临时 prefix 字符长度比较；不可把中间片当完整 final。
- 若 prefix="" 的新 failure envelope 也超界，先省略 optional 诊断，保留主 error 和真实 metrics；不得丢费用、改成 success、改写旧 receipt 或抛新的“裁剪错误”盖住原失败。实际本责任固定 error/metrics 的 baseline 约数百字节，测试需把该前提框住。若无诊断 baseline 自身也超界，这是主错误构造的问题，不能靠清掉 usage 解决。

无需反复写库试大小：这是一个纯函数拟合，然后 Store.finish_attempt 一次写入。prefix 后续不能继续增长；公开读取与 resume 直接消费原存储对象，不重新取 provider 数据、不重签、不过期重建。

### 纯内存试验：当前真实 HandlerResult/canonical_json

使用八字段建议 DTO、真实 `HandlerResult.to_dict` / `from_dict`、真实 `canonical_json`。synthetic metrics=8267 tokens、reasoning=7000、cost_usd=0.001；仅为序列化试验，不计真实费用。全部 roundtrip 保持值，下一 codepoint（如存在）均越过硬界。

| 样本 | full final UTF-8 bytes | prefix UTF-8 bytes | entire attempt UTF-8 bytes | clipped |
|---|---:|---:|---:|---|
| 中文 951B | 951 | 951 | 1593 | false |
| 显式空字符串 | 0 | 0 | 635 | false |
| 未观察 final（None） | null | 0 | 560 | false |
| 中文 18,000B | 18000 | 15735 | 16383 | true |
| NUL controls | 18000 | 2622 | 16380 | true |
| quote/backslash | 18000 | 7868 | 16383 | true |
| emoji | 20000 | 15732 | 16380 | true |
| 组合 Unicode | 18000 | 15735 | 16383 | true |
| 中文/CRLF/NUL/quote/emoji 混合 | 18000 | 9832 | 16382 | true |

这些数字只适用于上述 error/metrics envelope，不能写死为通用 prefix 配额。另证实未知 raw-response 的 null 两字段能真实 DTO roundtrip；lone surrogate strict UTF-8 失败，无替换编码。没有写测试源码或 provider 调用。

## 4. settle / 费用 / output 的最小规则

现有 `NarrativeRunStore.settle_model_usage` 的 `response_sha256` 对成功响应取 `NarrativeModelResponse.response_sha256`，即 decoded final 的 SHA。为保持同一列语义，新观察到的 length final 可传 `final_content_sha256`；没有 final 为 None。**不得把 provider envelope SHA 塞进该列**。provider SHA 只在 failed_final 中留一份。旧已结算 None 不补写，也不借这次设计修改历史 values/hash。

- usage 合法就按原 `ModelUsage(input, output)` settle；8194 completion 仍是 8194，即使保留正文只有 951 或 0 字节；超预留仍由现有 run store 诚实标记超限。
- reasoning 是 completion 子集，只保留现有 meter/invalid observation；unknown 不造 0，不将 reasoning 再加到费用。
- 没有合法 usage/after-send unknown 继续保守原 reservation 费用，不能因有 SHA/prefix 就当作免费或已知 usage。
- length/空输出没有正式摘要：`settle_output(output_bytes=0, output_sha256=None)`、artifacts/effects 空。保存诊断不能变成 output artifact、bundle 或 cache hit，也不能将 prefix 长度伪填正式产物 output 账。
- 单 attempt 诊断是既有 attempts 控制记录，单记录固定有界且不另存 body/JSON；其真实数据库占用应在既有 footprint 统计出现。本片不新造空间/费用账本；不能假报正式 output SHA 来替代控制记录的空间统计。
- 只结算一次；settlement 的现有幂等 receipt 语义不变。纯诊断构造/序列化失败只省略诊断，不替换主 code 和 metrics。**真正费用结算存储失败**仍保持现有 `MODEL_BUDGET_STORE_FAILURE` 与保守 reservation，不宣称已结算/0费用；能附加已观察 length 的静态原因则附加，但不得执行第二次 HTTP。

## 5. 公开读取 / 恢复 / 不自动重试

`narrative_batch._attempt_model_diagnostics` 当前 guard 只有 reasoning/usage 两字段。需要在原入口增加 failed_final 分支，即使 reasoning 未返回，也能公开诊断；仍只 parse 一次真实 HandlerResult。新 observation 的既有 usage_status/input/output/reasoning 字段沿旧账投影，按需加入 `failed_final`；旧记录无该对象时原 shape 保持，不能回填空对象/null哈希。

可选诊断无法解码时，沿现有 `stored_observation_unreadable` 诊断标记处理，不改变 job/outcome/费用。公开输出不包含原 HTTP body、request、headers、URL credentials、reasoning_content 或任意异常 repr。

`MODEL_OUTPUT_TRUNCATED` 保持 terminal failure；非 length empty 的现有 typed terminal 分类保持。SDK/HTTP 无新重试、无模型 fallback，公开 batch/resume 不因有 prefix 或 hash 重新发送。其他现有 timeout/429 分类不在本片偷改；**unknown 的存在不能由新诊断触发自动重发**。同 run 的已 terminal 只读恢复只读原 attempt/ledger：无新 reservation/POST/settle，没有源材料重签；若费用 receipt 未确定则仍如实 unknown，不以“恢复成功”消掉未知费用。

terminal compaction 不得剥掉这条已小于16KiB的失败诊断，也不能把它压成成功 summary pin；读取后两个 SHA、final observed/null 语义、prefix/clipped 和原 usage 都应保持。只测一次完整公共恢复责任，不给每个 helper 添人工门。

## 6. 最小实施验收矩阵（供 ROOT 纳入原 W04）

1. HTTP 真 decoder：951 / 0 / None / 18,000B；两个 hash 的来源正确，null≠empty，raw bytes 变但 parsed payload相同则 response SHA 变、final SHA 不变；未持有 raw body 的直接 fixture response SHA 为 None。hidden reasoning 未留存。
2. 纯完整-envelope拟合：上述中文、C0、quotes、emoji、组合/控制混合；严格小于16KiB、roundtrip、原 final 不改写；额外 large baseline 的诊断省略负控不改变主 error/metrics。
3. caller→summary→真实 attempt：8194 known 正确 settle一次/仍no-output，unknown旧预留保留；诊断写/清理错误不能造success/零费用；legacy无字段shape不变。
4. **一个隔离公共CLI大节点**：真实子进程、loopback length/body951→实际入库→public diagnostic→重开/terminal处理→两次同run只读resume，严格一次POST/reservation、零正式bundle、零追加收费。同夹具保留 empty 与 None 区分；结束 owned TEMP 恢复，无 production/source/config mutation。

先完成这些工程责任，再用真实已配置模型/原失败资料验证最终输出与四路质量；这些离线设计试验不能关闭真实供应商截断、业务召回或研究质量问题。

## 调查边界

只读源码已定位：`narrative_http_model.py:381–457`、`narrative_model_caller.py:190–325`、`narrative_summarize.py:92–105/180–202`、`models.py:108–116/588–630`、`store.py:429–453`、`narrative_run_store.py:724–829`、`narrative_batch.py:1852–1876`。结构问题先 CodeGraph；已知文件精确读实际 MAIN。CodeGraph未找到 CallOutcome/settle_model_attempt，实际名字已据源码校正。

本报告是唯一文件写入。无源码/tests/PWF/DB/原件/配置/安装改动，无密钥读取/输出，无外部网络、provider 或 LLM 调用；对协作子任务的尝试因并发槽已满未启动。纯内存数字不算真实费用或工程通过签收。
