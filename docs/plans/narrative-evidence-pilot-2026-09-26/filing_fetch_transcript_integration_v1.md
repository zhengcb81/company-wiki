# filing-fetch × earnings-transcripts × company-wiki 集成合同草案 v1

日期：2026-09-27。用途：指导 G1e 跨项目实现和关键 E2E；不是生产授权，也不改变 revenue-forecast、company-wiki Worker 或 provider 权利状态。

## 1. 现状核对

- company-wiki 已有 `investor_call_transcript` document kind，canonical writer 将原件放到公司目录 `raw/investor_relations/transcripts/`；新隔离 helper 可从 HTML/TXT 建未翻译文本和原文 byte locators，但尚无正式派生 artifact role。
- earnings-transcripts 当前可调用入口是 `transcript_tool.py` 的 stdin/stdout JSON 子进程，不是 MCP server。新版接口可以按 ticker、exchange、FY/Q、as-of 查询，要求请求内 `download_authorized=true` 且 CLI `--allow-download`，正文英文不翻译；支持 Motley Fool HTML 与 FMP JSON，且没有文件、日志、缓存或翻译副作用。
- E-T 默认结果 schema `/1` 含 `provider_payload_sha256` 和 `canonical_content_sha256`，不返回原始 HTML/JSON 字节或 effective URL；2026-09-27 已增加显式 `--include-source-payload`/`include_source_payload=True` opt-in，返回 schema `/2` 的 bounded base64 原件、normalized MIME 与无查询凭据的 effective URL，并省略重复的 `content_utf8`。除非调用此 opt-in，不能以结果计算真实 raw source ID 或声称原件完整；即使 opt-in，company-wiki 仍须解码、重算 hash、独立复验 rights/identity 后方可持久化。
- filing-fetch 代码 `FILING_REQUEST_SCHEMA_VERSION=1.2`、已知字段不含 transcript companion；技能说明仍标 schema 1.1，形成文档/代码漂移。代码的主流程是 identity → company-wiki resolve/ensure → 深度验证单个 filing handle；`--allow-download` 与授权 block 面向 filing。它没有 transcript response/status，也没有 partial-success contract。
- `filing-fetch` 现有 `PausedWorkerScope` 围绕 company-wiki ensure 下载。集成不能持有 catalog lock 等待外网；应将网络请求放在 company-wiki 写事务之外，只在短暂 canonical import 需要时使用 Worker pause/lock 协议，且不得恢复用户原先暂停的 Worker。

## 2. Provider 使用门禁

- Motley Fool 自动抓取在本计划的来源权利评估中被判为禁止路径；Seeking Alpha 没有本机 provider adapter，个人订阅条款也不授予程序化抓取权。两者必须在请求发出前被 hard-deny，不能因为 UI/CLI 双重 `allow-download` 就放行。
- FMP 精确电话会 endpoint 的真实 canary 返回 HTTP 402；其日期字段只有 call date，且保存/展示 transcript 的权限需单独确认。不得重试付费 endpoint，不得将 call date 冒充 publication date。
- 因此本合同先用 fake provider 做端到端互操作；**没有任何当前 E-T provider 获得生产下载或持久化放行**。后续任何许可都要由独立、带 hash 和有效期的 provider/action policy 决定，涵盖 discover、fetch、retain、derive、select、summarize、export。

## 3. 目标编排与数据合同

### 3.1 请求

filing-fetch 升级到新请求 schema 时增加可选 `companion_transcript` 对象；不改变既有 request 的 reuse-first 默认值。

```json
{
  "mode": "reuse_only | fetch_if_missing",
  "fiscal_year": 2026,
  "fiscal_quarter": 2,
  "provider": "provider-id-or-omitted"
}
```

- FY/Q 必须单独、明确给出；不得推断“年报 = Q4”或“季报日期 = 电话会期次”。调用方未提供准确电话会期次时返回 `not_requested`/`not_applicable`，绝不模糊下载。
- transcript 下载须同时满足请求内专用 transcript authorization 和独立 CLI/process 开关（如 `--allow-transcript-download`）。原有 `--allow-download` 只授权 filing，不级联授权 transcript。
- request strict-schema 必须继续拒绝未登记字段。新版 SKILL.md、`filing_contracts.py`、测试和调用方示例同一提交更新，不能只改文档。

### 3.2 编排顺序

1. filing-fetch 先验证请求与唯一 active identity；US ticker/exchange 缺失、身份歧义或 transcript period 不明确时不调用 E-T。
2. 以 entity/security/ticker、`investor_call_transcript`、明确 FY/Q、language=en、as-of 先问 company-wiki resolver。找到 capture-ready 原件则返回 `reused`，provider 调用必须为零。
3. 未命中时先做 discovery endpoint/action 和用户授权预检。任一不通过即返回 `rights_blocked`/`not_authorized`，provider 请求计数为零。
4. **候选 discovery 与正文 fetch 必须隔开，除非 policy 已对整个受限 provider path 授予 discover+fetch 权且 authorization 先限定 ticker/FY/Q 与 byte cap。** discovery 只能返回元数据；候选必须精确绑定 ticker/security、FY/Q、provider document ID、source URL 和 as-of 证据。ambiguous 候选全部停止，不自动挑一个。对候选本身的 fetch/retain/derive 授权要在正文请求之前落定。
5. 只有候选授权通过后，E-T/future adapter 才取正文；默认结果 schema `/1` 仅供旧调用。集成调用 opt-in schema `/2`，返回有界原始 provider payload（base64）、原件 MIME、安全 effective HTTPS URL、原件 SHA、extractor 版本、精确期次和日期语义；不带 API key、成功响应不重复 `content_utf8`。父进程须先限制 stdout 上限，不能无界 `capture_output` 后才检验 JSON。
6. filing-fetch 将结果交给 company-wiki 专用 stdin JSON importer。importer 独立复验 request/candidate/receipt、rights policy hash、final URL、MIME、大小、payload SHA 和 FY/Q，再调用现有 canonical writer；provider 原件只落一份 raw。company-wiki 从该原件重新生成英文文本和紧凑 lineage；未选中的全量 locator 表留内存，不重复落盘。若 canonical sidecar 不能表示 final URL 与 discovery URL，必须 fail closed 或由 transcript 专用轻量 provenance sidecar 保存两者；不能静默丢弃 effective URL。
7. filing 主 handle 与 companion transcript 采用**分项状态**：filing 成功 + transcript 失败仍返回 filing success；transcript 输出只含状态、canonical handle、source ID/hash 和摘要处理状态，不把整篇正文复制到 stdout。
8. transcript 的 raw 下载和解析不得持有全局 catalog lock。canonical commit 使用明确 operation lock；worker 当前 paused，测试不能启动真实 Worker；将来只在 owner 启用时沿用“尊重用户已有 pause，不擅自 resume”的规则。

### 3.3 输出状态

固定 `transcript.status` 至：`not_requested`、`not_applicable`、`reused`、`downloaded`、`rights_blocked`、`not_authorized`、`not_found`、`ambiguous`、`upstream_error`、`validation_error`、`persist_error`。每个 failure 只影响 transcript 子对象；需要重试时区分 provider 暂时错误与身份/权限永久拒绝。

`transcript.handle` 复用 company-wiki `SourceHandle`，至少可核验 source/document ID、exact FY/Q、provider、HTTPS source URL、raw SHA、MIME、byte size、published/call date 精度、原件路径与 capture-ready。FMP 的 `publication_date=null`、`as_of_cutoff_verified=false` 必须保留。

## 4. 原始响应传输选择

优先在 E-T JSON 子进程响应中增加 opt-in 的 bounded base64 原始 payload + MIME + effective URL：API 默认仍返回现有小结果、默认无文件副作用；只有经授权的集成请求加显式 flag 才返回 payload。最大输出应由原始字节上限推导并在父进程再限长。company-wiki 收到后先解码验 SHA、落到 run-id private staging、完成二次 rights check，再 canonical import；成功后仅 raw 进入长期目录。禁止 E-T 自行写生产公司目录或保留另一份 durable raw。

如果 stdout 尺寸测试表明 base64 峰值不满足内存/Windows 子进程预算，再单独评估调用方指定 staging sink；该 fallback 必须防路径穿越/覆盖/重解析点，并由 E2E 证明运行目录归零。不得因为实现更简单而把 E-T 持久目录当第二份 canonical store。

## 5. 实施阶段与验收

| 子阶段 | 产物 | 关键验收 |
|---|---|---|
| G1e-B E-T response v2 | 双兼容、opt-in 的 raw payload/MIME/final URL 字段；provider contract 文档 | 已完成：全量离线 **100 passed, 1 deselected**（仅跳过依赖缺失 LLM key 的既有测试）、Ruff 通过。22 项接口测试覆盖 HTML/FMP JSON 字节/哈希往返、redirect、MIME、secret redaction、默认无 payload及 CLI 双授权；rights gate 仍关闭 |
| G1e-B2 fetch 前候选授权能力 | 分阶段 discovery→candidate-bound fetch，或有文档/rights 证据的 exact URL 预授权；不得在 CWP 检查前取正文 | E-T half 已完成：新增 `discover`（候选 metadata only）与 `fetch-candidate`（一份绑定候选的正文请求）；旧 combined fetch 被标为 integration-ineligible。完整 E-T 离线 **106 passed, 1 deselected**，其中假 HTTP 验明 discovery 不取正文、候选错/未授权不发正文请求。G1e-C 仍必须证明 CWP caller 的 policy `discover` preflight 与候选下载授权真实发生在子进程调用前 |
| G1e-C company-wiki importer | importer library + stdin JSON CLI；复用 `DownloadAuthorization`、rights helper 和 canonical writer | **library core 已在隔离 worktree 完成**：要求绑定的 preflight admission；校验严格 `/2` envelope、request/candidate/provider/ticker/exchange/FY/Q/as-of/source/effective URL、原始 payload SHA/MIME/HTTP/time 和新鲜 rights policy；错误输入在写 raw 前拒绝；成功仅存一份 canonical 原件，紧凑 TXT locator 留内存，并把 rights/auth hashes 写入 namespaced provenance extension。核心+writer/acquisition/sidecar 合同 56 passed。**尚未完成/不得标 G1e-C 通过**：缺 stdin CLI、真实 CWP 调用顺序、discover policy preflight、filing-fetch caller 在 E-T 子进程前的 exact auth 测试。E-T exchange 当前回显请求参数；调用方须先用公司身份映射到明确 NYSE/NASDAQ，禁用 `auto`，unknown fail closed。 |
| G1e-D filing-fetch companion | request/response schema、独立开关、E-T 子进程 seam、分项 partial success | 未授权零 provider 调用；已有 transcript 零 provider 调用；transcript 失败不吞掉 filing 成功；工具超时/坏 JSON/越权 payload fail closed；worker pause/resume 行为按原合同 |
| G1e-E 跨项目 E2E | 独立 tests/e2e run root + fake ET/filing/CWP tools | 从 identity → filing resolve → transcript reuse/fetch → CWP raw import → 摘要/locator；校验内容未翻译、exact period/as-of、parent/hash、final URL、sidecar、输出不含全文；运行前后测试树完全相同 |

每个 E2E run root 必须在启动前不存在，由本次 run-id 唯一创建；正常/异常/超时清理必须恢复到基线；运行后检查 raw、base64 JSON、TXT、sidecar、catalog DB、lock 和 Worker 状态，不能遗留测试下载。

## 6. 当前依赖与明确 Hold

- G1e-A company-wiki helper、post-fetch gate 和 company-wiki fake-provider import/replay E2E 已在托管隔离分支完成：历史最终合并组 34 passed；它不是 filing-fetch 跨仓 E2E。G1e-B 的 E-T raw-payload opt-in API 与 G1e-B2 candidate-bound fetch 已完成；E-T 离线回归 **106 passed, 1 deselected**（唯一排除项是本机未配置 LLM 后端的既有 translator 测试）。G1e-C importer library 已实现，相关核心+writer/acquisition/sidecar 合同 **56 passed**，但 stdin CLI 与 caller-order E2E 未完成；不可据 library 测试宣称接入完成。
- CWP importer 的 `DownloadAuthorization` 必须匹配 `SourceRequest.request_id`；已补显式检查。权限与授权摘要及 action receipt 写入 `.source.json` 的 `provenance_extensions.transcript_acquisition`，扩展被限制为小于 16 KiB。一个有效原件的 effective URL 必须等于选定 candidate URL；redirect 仍 fail closed。原始 `exchange="auto"` 或候选缺少明确 venue 会被拒绝。
- revenue-forecast 已只读复核至 Round 120 / register §162：I-17-A 在飞，Worker paused，G0 仍未通过；本集成不修改其文件、工作树或 source/artifact role。
- `transcript_text` 新 role 仍需 G0 后全链评审；G1e importer 可验证原件与 TXT lineage，但不得提前扩展共享 `SourceBundle`/role DAG。
- 眼下 provider 权利/可用性不满足真实抓取；完成假 provider E2E 只代表代码路径互操作，不代表任何数据源可上线。

## 7. 回滚

- E-T tool、filing-fetch request 和 CWP importer 都保留旧 schema/无 companion 的路径；`companion_transcript` 缺失时行为字节级保持原 filing 流程。
- 任一响应/验证/权利 gate 出错，只删除本次 private staging；不得触碰 filing 成功结果、现有 raw、历史 transcript 库或用户暂停状态。
- provider 发出生产调用之前必须同时有 rights policy、明确用户授权、写入目标审批、provider canary 和真实 raw→locator E2E 收据；任一缺失即保持 fetch off。
