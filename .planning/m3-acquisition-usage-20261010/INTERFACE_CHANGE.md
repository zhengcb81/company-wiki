# INTERFACE_CHANGE.md — M3-USAGE（lane_id=M3-USAGE）

冻结日期：2026-10-10。本文件是先于源码修改的合同：实际字段、完整/下界/未知三态、
success/failure/reuse 样例、旧版本兼容、CWP→FF→RF 消费者路径、MAIN 接线 patch。

## 0 决策：observation sibling（不改旧版本）

- `acquisition_usage/1.0`（严格 `response_bytes`+`cost_usd` 三键）与 `acquisition-failure/1`
  （严格七键）字段与语义一字不动；validated_usage/validated_failure 不放宽。
- 新增 **sibling DTO `acquisition-observation/1`**，与 acquisition_failure 平级挂在
  operation 结果上；旧消费者（子集校验）不认识它只是忽略，不 break。
- 旧 1.0 的 `response_bytes` 保持原实现语义（adapter 回执里的 entity/materialized bytes）。
  新 DTO 用独立键名 `wire_body_bytes` / `entity_body_bytes`，绝不复用 `response_bytes` 名字，
  避免 silently 变义。

## 1 DTO 定义：acquisition-observation/1

```json
{
  "schema_version": "acquisition-observation/1",
  "usage_scope": "operation",
  "outcome": "downloaded_new",
  "provider_started": true,
  "usage_complete": true,
  "wire_body_bytes": 2841,
  "wire_usage_complete": true,
  "entity_body_bytes": 8192,
  "http_exchanges": 3,
  "http_exchanges_complete": true,
  "cost_usd": "0.0004",
  "http_observation": {
    "status_code": 200,
    "mime_type": "application/pdf",
    "content_encoding": "gzip",
    "wire_content_length": 2841
  }
}
```

### 字段语义（操作范围，operation scope）

| 键 | 类型 | 语义 |
|---|---|---|
| schema_version | const | `"acquisition-observation/1"` |
| usage_scope | const | `"operation"`；计数跨同一 ensure/close-gap 操作的全部 invocation 累积（既有 AcquisitionBudget），不是最后一次 adapter invocation |
| outcome | closed set | `downloaded_new` / `deduplicated_after_download` / `reused_before_download` / `reused_after_discovery` / `missing` / `ambiguous` / `gap_plan` / `gap_plan_provider_unavailable` / `failed`（producer journal 词表） |
| provider_started | bool \| null | 操作内任一 invocation 的存在性执行证明（既有 monotone merge） |
| usage_complete | bool \| null | true=已观察值是最终完整操作总量；false=下界；null=无法判定 |
| wire_body_bytes | int ≥ 0 | 已观察 HTTP 响应正文 wire bytes 累计：transfer-decode 之后、content-decode 之前的 body 字节；不含 status line/headers/TCP/TLS |
| wire_usage_complete | bool \| null | false ⇒ wire_body_bytes 是下界（如 entity>0 而 wire 未回执） |
| entity_body_bytes | int ≥ 0 | 已观察 materialized/解压后 body bytes（= 旧 1.0 response_bytes 的实现语义），≠ 原件磁盘大小 ≠ wire |
| http_exchanges | int ≥ 0 | 已观察 HTTP 请求/响应交换次数（收到响应即 +1；发送失败未收到响应不计）。总是发布已观察值 |
| http_exchanges_complete | bool \| null | true=计数可信；false=下界（操作不完整，可能还有未计交换）；null=不可测（legacy 回执不报计数） |
| cost_usd | decimal string \| null | null=费用未知（provider 无费用回执）；非 null=provider 已观察累计费用（usage_complete=false 时为下界）。**cap0、初始 counter0、无回执都不写成已知 0** |
| http_observation | object \| null | 可选；操作中最后被观察响应的有限协议元数据，四键闭合：`status_code`(int)、`mime_type`(str ≤128，content-type 首 token 小写)、`content_encoding`(str ≤128，默认 identity)、`wire_content_length`(int \| null)。沿用 bounded_http.response_observation 既有形状 |

校验（validated_acquisition_observation，fail-closed）：闭键集、上述类型/闭集全查、
cost_usd 为有限非负 decimal 字符串；不认识 ⇒ 整体丢弃（None），绝不部分采纳。
键名不含 path/location/root/bundle（projection 物理字段守卫天然通过）。

### 三态规则（诚实性核心）

- **完整**：usage_complete=true 且对应 *_complete=true ⇒ 值即最终操作总量。
- **下界**：任一 *_complete=false ⇒ 对应计数是已观察下界（post-send timeout、hard kill、
  mid-body 截断后的 checkpoint）。
- **未知**：null / 缺观察 ⇒ 不冒充 0。费用仅在有 provider 回执时非 null；
  `provider_started=false` 的 pre-launch 失败：http_exchanges=0、wire/entity=0、
  usage_complete=true（没跑就是完整零）；费用仍 null（除非 provider 明示 0 回执）。
  计数完整性由 `*_complete` 承载：false=下界（如 hard kill 后 checkpoint），null=不可测
  （legacy 回执不报交换数，此时计数保持 0 而非编造）。

## 2 producer 挂载点（CWP）

1. 成功/gap/missing/ambiguous/reuse：`SourceEnsureResult.to_dict()` 新增可选键
   `acquisition_observation`（由 `_finish` 从共享 budget 构建，budget=None 时整个键缺省）。
2. v2 operation DTO：`project_operation_result`（source_operation.py facade）平级附加
   `acquisition_observation = observation_from_result(payload)`（与 acquisition_failure 同法）。
3. 失败：`attach_acquisition_failure` 同时在异常上设 `acquisition_observation` 属性；
   stderr 发布需 MAIN patch（见 §6.1）。预算/清理二次异常只 add_note，不覆盖属性。
4. 计数来源=既有 AcquisitionBudget 新增字段：`http_exchanges_used/_complete`、
   `cost_reported`、`last_http_observation`。bounded_http `_headers` 每响应 +1 交换并
   stash http_observation；adapter 回执协议新增可选顶层键 `http_exchanges`、
   `http_observation`（与既有 `http_wire_bytes` 平级；缺省=未知，不拒收）。
   dayu_sdk_cli 成功 stdout / 失败 stderr / progress checkpoint 同步带上两键。

## 3 消费者路径

### CWP→FF
- FF `_SOURCE_OPERATION_FIELDS` += `acquisition_observation`（子集校验本就兼容，此处使其
  被主动消费）；`ff_provider_cause.validated_acquisition_observation`（FF 侧同规则校验，
  深拷贝原样保真，不重算、不补账、不重验 MIME/身份）。
- `ff_v2_envelope`（success/gap/error 三分支）：`acquisition_observation` 放 **envelope 顶层**
  （与 calls/downloads 同为 operation 级账目；有效才带）。filing 保持既有闭合形状不动，
  RF 的 source_candidate 严格闭集合同零改动。
- FF 不从磁盘/原件大小推网络账；`calls` 仍是 CWP 子进程调用数（语义不变）。

### FF→RF
- `filing_fetch_client`：成功 envelope 原样返回（观察自动随行）；非零退出时
  `failure_observation` 投影 `acquisition_observation` 进 `_ClientError` 属性
  （顶层优先，detail 兜底兼容平铺旧形状）。
- `source_preparation`：`FilingSourcePreparationError` 镜像同属性；成功侧 envelope 整体
  进 sidecar（既有行为，观察自动随行）；reuse_receipt 语义不动（download_events 仍是
  0/1 下载事件证明）。

## 4 样例（真实形态，测试会逐字钉住）

- **success/downloaded_new**（2×metadata GET + 1×gzip body GET）：
  outcome=downloaded_new, provider_started=true, usage_complete=true,
  wire_body_bytes=metadata1+metadata2+gzip(body) < entity_body_bytes=metadata1+metadata2+解压body,
  http_exchanges=3, cost_usd=provider 回执值, http_observation={200, body mime, gzip, wire len}。
- **reuse（reused_before_download，无 adapter 工作）**：http_exchanges=0, wire/entity=0,
  usage_complete=true, cost_usd=null（无回执不冒充 0）。
- **reuse（reused_after_discovery）**：http_exchanges=discovery metadata 数, entity=metadata
  entity 和, download_events=0。
- **pre-launch 失败**（provider_started=false）：http_exchanges=0, wire/entity=0,
  usage_complete=true, cost_usd=null。
- **post-send timeout / mid-body 截断**：usage_complete=false（下界），checkpoint 已计
  wire/entity 保留，cost 有回执才非 null。
- **未知费用**：provider 回执无 cost ⇒ cost_usd=null（budget.cost_reported=false）。
- **legacy adapter**（不回执 wire/exchanges）：http_exchanges=0、
  http_exchanges_complete=null（不可测），wire_usage_complete=false（既有 entity>0∧wire=0 规则）。

## 5 旧版本兼容矩阵

| 消费者 | 旧 CWP 输出（无新键） | 新 CWP 输出 |
|---|---|---|
| FF（改前） | 正常 | 正常（子集校验忽略新键） |
| FF（改后） | 正常（缺省=无观察） | filing.acquisition_observation |
| RF（改前） | 正常 | 成功 envelope 随行；失败投影缺省无观察 |
| RF（改后） | 正常 | failure_observation 带 acquisition_observation |
| 旧 acquisition_usage/1.0 持有者 | 不变 | 不变（无字段重载） |
| 旧 acquisition-failure/1 持有者 | 不变 | 不变（七键不动） |

旧 7 未知模型 + 1 旧 FF 未知采集：不回填、不核销，保持原未知。

## 6 MAIN 接线 patch（本线不 commit）

### 6.1 CWP error_taxonomy.structured_error（3 行）
```python
    from .acquisition_observation import published_acquisition_observation
    observation = published_acquisition_observation(exc)
    if observation is not None:
        result["acquisition_observation"] = observation
```
（本线 E2E 实验在专属临时集成副本应用，不混入 commit。）

### 6.2 无 cli.py patch
成功路径经 to_dict + facade 附加，`--source-ref-v2` 既有旗标即出口；无需新旗标。
FF 侧 `--source-ref-v2` 行为不变。

### 6.3 MAIN 大节点必须重跑的测试包
- CWP：`python -X utf8 -B -m pytest -q tests/unit/test_m3_acquisition_usage*.py tests/integration/test_m3_acquisition_usage*.py`（新）
  以及受改责任回归：tests/unit/test_acquisition_failure_diagnostic.py、test_acquisition_usage_recovery.py、
  test_adapter_process_budget.py、tests/contract/test_acquisition_failure_return_paths.py、
  tests/integration/test_acquisition_failure_cli_e2e.py、test_dayu_sdk_fetch.py、test_bounded_http.py。
- FF：`python -X utf8 -B -m pytest -q tests/test_m3_acquisition_usage*.py tests/test_failure_usage_continuity.py`
  （+ tools/ci_tests.py 既有列表；新套件加入 CI_TESTS）。
- RF：`python -X utf8 -B -m pytest -q tests/test_m3_acquisition_usage*.py tests/test_source_failure_observations.py`（新+既有）。

## 7 明确不做

- 不加身份验证、格式白名单、授权 receipt/TTL、人审、第二账本。
- 不改 journal schema、AUTO 模型/存储、official JSON 线文件、RF drivers/contracts。
- 不恢复 115B 旧 SEC 差异或旧收费账；不宣称真实 SEC/ET 公网大节点已运行。
- Dayu 纯外部零代码修改（dayu_sdk_cli.py 是 CWP 自有 CLI，属本线写集，不属于 Dayu 仓）。
