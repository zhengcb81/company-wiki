# Phase D / M2-provider 实施细则（2026-09-28）

> 本页是 [清洁架构与 TDD 实施总图](clean_architecture_tdd_execution_plan_2026-09-27.md) 的 Phase D 施工卡。先冻结实施顺序、接口所有权和大节点验收，再改产品代码。历史 G1e 文档保留调查证据；若状态或模块边界冲突，以本页为准。

> **完成状态（2026-09-28）：company-wiki 侧 D0–D7 已完成。** fake-provider HTML/TXT 全链和失败矩阵已通过 verified reader；四个复杂度冻结项已移除。真实 E-T `/2` HTML 的 canonical text 定义与 CWP deterministic material 不同，作为 Phase F producer-contract 阻断项保留，不能以本阶段 fake 结果替代。

## 1. 阶段目标和边界

本阶段只解决四件事：

1. 把电话会议的来源权限、候选授权、下载结果验证、schema `/2` 解码、canonical admission、确定性英文文本派生拆成可独立测试的端口。
2. 保留现有严格行为：精确 US security + FY/Q + as-of；原件 SHA/MIME/URL/大小重新验证；英文不翻译；长期 raw 只保存一份。
3. 增加一条真正跨进程的离线 E2E：fake provider discovery → company-wiki discovery gate → candidate gate → fake provider fetch-candidate `/2` → stdin importer → verified reader → TXT/locator replay。
4. 移除或显著下调本阶段四个临时复杂度豁免，不增加第二套任务库、provider registry 或持久化模型。

本阶段不做：

- 不修改 revenue-forecast，也不依赖其未提交文件。
- 不在 company-wiki 实现 filing-fetch 的 companion 编排；正式跨仓 caller 留到 Phase F。
- 不调用 FMP 付费正文端点，不访问 Motley Fool/Seeking Alpha/Koyfin 正文，不新增 provider。
- 不把 `transcript_text` 提前注册为共享 artifact role，不持久化逐行 locator 大表。
- 不启动 Worker，不删除历史派生文件，不迁移 46 GiB 旧数据。
- 不把用户对外部 LLM 的授权重新解释成 provider 自动访问或内容再分发许可；本阶段不存在 private/public 数据分级门。

## 2. 2026-09-28 现状基线

| 能力 | 已有事实 | Phase D 缺口 |
|---|---|---|
| provider 权利 | `ProviderUsePolicy.decide()` 支持逐 provider/URL/content/action 判断；MF 有 hard deny | transcript admission 与政策 schema 同文件，两个顶层函数复杂度最高 38 |
| candidate preflight | CLI 可构造精确 `DownloadAuthorization` 并绑定 request/candidate/runtime/policy hash | CLI 同时负责 JSON、配置、计划、时间、授权和投影；最高复杂度 23 |
| `/2` import | 可校验 payload、身份、FY/Q、MIME、effective URL、SHA、byte cap 并写唯一 canonical raw | 解码、身份验证、临时文件、post-fetch、派生、writer、cleanup 聚在一个复杂度 41 函数 |
| 英文派生 | HTML/TXT 可确定性生成严格 UTF-8 文本和 byte locator；紧凑 lineage 可重放 | extraction 与 lineage validation 仍在一个复杂度 19 模块；没有正式 reader E2E |
| subprocess 测试 | importer CLI 已单独跨进程；preflight 分别有测试 | `/2` 仍由测试手写；没有 provider 子进程、timeout、reader CLI 和完整串联 |
| earnings-transcripts | 本地未提交分支已有 discovery/fetch-candidate、raw payload `/2`；`transcript_tool.py` 永不翻译；scraper 有 `--disable-translation` | 代码尚未提交；仓库无 CodeGraph；Phase D 只按公开 JSON 边界做 fake，不直接改其内部实现 |
| revenue-forecast | `fcap=ee0a82bf`，`origin/main=3a69f9c5`；本地有 planning/assurance 未提交改动 | 只作冲突预警；本阶段零写入 |

现有测试各自证明局部功能，但不能宣称 provider 全链完成：

- `test_transcript_import_cli_e2e.py` 手工构造 `/2` 结果；
- `test_fake_provider_rechecks_then_imports_and_replays_transcript` 使用同进程 fake object，并绕过 stdin importer 与正式 reader；
- 没有超时/坏 stdout/超限 stdout 后的零残留全链断言。

## 3. 目标依赖方向

```text
provider subprocess (untrusted JSON/bytes)
        |
        v
transcript tool transport contract
        |
        v
prefetch policy + exact candidate authorization
        |
        v
postfetch receipt/staged-byte validation
        |
        v
canonical transcript admission service
        |
        +--> immutable raw + provenance extension
        |
        v
deterministic untranslated material
        |
        v
SourceVersionReader.open_version + locator replay
```

依赖规则：

- policy domain 不导入 CLI、catalog、writer 或 subprocess。
- `/2` transport parser 不读取配置、不写文件、不决定 provider 权利。
- post-fetch validator 只验证 receipt、staging 和 policy，不提交 canonical raw。
- admission service 只编排已验证组件；唯一清理责任在该 service 的 `finally`。
- narrative selector 不知道 provider；调用它的 transcript application service 必须先拿到 `select_evidence` 动作许可。摘要调用同理要求 `generate_summary`。本阶段只实现和测试授权端口及 fake 链，不接真实 Worker。
- verified reader 按 `document_id + source_id + content_sha256` 交付原件字节；测试不得从响应中的绝对路径直接读取。

## 4. 文件级施工图

最终名称可在 RED 测试暴露更合适的边界时微调，但职责不得重新合并。

### D1. 保留纯 provider-use policy

`provider_use_policy.py` 只保留：

- policy/rule schema、hash、load、site hard deny、逐 action `decide()`；
- 不含 transcript request/candidate/receipt/staging 逻辑。

新增 `transcript_use_policy.py`：

- `TranscriptUseContext`：provider、source/effective URL、content class、policy hash；
- `authorize_transcript_actions(...)`：显式 actions tuple，返回稳定 code 和 policy/evidence hash；
- action 不传递：允许 fetch 不代表允许 retain/derive/select/summarize/export；
- 不引入 private/public 或用户角色 ACL。

### D2. 拆分 prefetch 与 postfetch

新增 `transcript_fetch_admission.py`：

- 校验精确 request、candidate、security identity、as-of；
- 复用正式 `validate_download_authorization()`；
- 组合 `automated_fetch + retain_original + derive_text` 三项权利；
- 产出 typed `TranscriptFetchAdmission`。

新增 `transcript_fetch_validation.py`：

- 重新加载后的 policy hash 必须等于 prefetch pin；
- 验证 receipt identity、2xx、MIME、byte cap、时间；
- 以 `Resolve-Path`/`Path.resolve` containment 验证 staging；拒绝 symlink/junction/非普通文件；
- 流式重算 staged SHA/size；
- 对 effective URL 再检查三项权利；
- 只返回 validation，不导入、不删除。

兼容策略：

- 原 `provider_use_policy.py` 可短期 re-export 两个公开入口和 dataclass；
- 全仓 consumer scan 后若没有仓外 Python import，可在本阶段末更新仓内 import 并移除 re-export；
- JSON reason code 保持不变，避免把重构伪装成行为变更。

### D3. 拆分 `/2` transport contract

新增 `transcript_tool_contract.py`：

- 单一拥有 `earnings-transcript-result/2` consumer schema；
- 有界 UTF-8 JSON、拒绝重复 key/NaN/未知字段；
- base64 严格解码并重算 provider payload SHA；
- 校验 request/provider/document/ticker/exchange/FY/Q/as-of/published date/source/effective URL/MIME/HTTP/timestamp/content hash；
- 产出 typed `ValidatedTranscriptPayload`，其中原件为 bounded bytes，绝不写路径。

禁止：

- 根据 filename 或正文猜 fiscal period；
- 把 E-T 回显的 exchange 当成独立证券身份来源；caller 必须先提供已解析 NYSE/NASDAQ identity；
- 在 stdout、异常或 sidecar 中复制 base64/全文/API key。

### D4. 拆分 canonical admission service

新增 `transcript_admission_service.py`：

1. 验证 preflight admission pin。
2. 调用 `/2` contract 得到 typed payload。
3. 在 writer 分配的 staging root 中创建唯一临时文件并写入原件。
4. 构造 `DownloadReceipt` 并调用 postfetch validator。
5. 调用 deterministic material extractor。
6. 调用 `CanonicalSourceWriter.import_staged()`；provenance extension 仅保存短审计字段。
7. 验证 canonical source ID 等于原件 hash source ID。
8. `finally` 只删除本次创建且仍位于精确 staging root 的文件。

`transcript_import.py` 缩为兼容 facade：parse/application 调用和公开 result 类型；不得再拥有 staging 或 policy 细节。

重复导入必须复用同一 source version，不重写既有原件或制造第二份全文；测试记录原件路径集合、SHA 和数量。

### D5. 拆分英文 material 与 replay

保留 `transcript_material.py` 的公开类型和 facade，内部拆为：

- `transcript_text_extract.py`：严格 UTF-8 HTML/TXT → text lines + exact original byte ranges；
- `transcript_lineage.py`：紧凑 lineage schema、hash/size/version 校验和确定性重放。

永久输出仍不保存全量 line locator；只有 selected evidence 保存必要 locator。HTML/TXT 原件与派生文本都不翻译。

### D6. 缩薄 CLI

`transcript_import_cli.py` 只负责：

- bounded stdin/stdout；
- operation 分派；
- wiki config/runtime/provider policy 组合根；
- JSON DTO 与 application command/result 的转换；
- 稳定 exit code 和无正文响应。

将 discovery/candidate preflight 的纯命令处理移到 `transcript_preflight_service.py`。Clock 由函数参数或单一 UTC helper 注入，避免每个 helper 自行取时。

## 5. TDD 施工顺序

严格按下列顺序；每一小步只跑最小红/绿测试，D7 才跑 M2-provider 大门。

### D0. 冻结基线

1. 记录 CWP/RF/E-T refs 和 dirty 状态；不修改 RF/E-T。
2. 运行现有四组 transcript/provider tests，保存数量和耗时。
3. 记录四个复杂度上限：38/41/23/19。
4. 用 literal schema scan 列出公开 import 和 JSON schema consumer。

### D1. RED：层次与复杂度

先写架构测试：

- policy domain 禁止导入 catalog/writer/CLI/subprocess/tempfile；
- transport contract 禁止导入 writer/catalog/config；
- validation 禁止调用 canonical writer；
- facade 顶层函数复杂度和所有新模块均 `<=10`；
- 旧四项 `FROZEN_MAX` 在阶段完成前必须下降或删除。

RED 证据必须显示当前模块违反至少一个目标；不能先改 threshold 让测试变绿。

### D2. RED/GREEN：prefetch policy

参数化负例：

- 非 US、非 transcript、FY/Q 缺失、非 exact；
- security identity/market/exchange 漂移；
- candidate 日期晚于 as-of；
- authorization request/provider/accession/plan/runtime hash/cap/expiry 漂移；
- policy 缺失、过期、撤销、site hard deny；
- fetch/retain/derive 任一动作缺失。

正例从正式 `SourceRequest`、`DownloadCandidate`、`DownloadAuthorization` producer 生成，不手写近似 JSON。

### D3. RED/GREEN：postfetch 与 `/2`

负例矩阵：

- duplicate JSON key、unknown schema/field、bad UTF-8/base64/NaN；
- request/provider/document/ticker/venue/FY/Q/as-of/source/effective URL 漂移；
- 非 2xx、MIME 不支持、payload/content SHA 错、byte cap 超限、未来 timestamp；
- staged path 越界、symlink/junction、非普通文件、size/SHA 改写；
- 下载后 policy hash 变化、effective URL 权利不符。

所有拒绝路径断言：raw=0、sidecar=0、catalog source=0、staging=0、stdout 无全文。

### D4. RED/GREEN：admission、重复导入和 material replay

- 合法 HTML 和 TXT 各一例；canonical raw bytes 与 provider payload 完全相等。
- 同一 payload 第二次导入返回 reuse，原件和 sidecar 数量不增加。
- provenance extension 有 policy/auth/effective URL/adapter/extractor hashes/versions，无 base64、正文、API key、absolute staging path。
- compact lineage 不含 `lines` 数组；从 verified raw 确定性重建文本和 locator。
- selected evidence 使用 locator 回放到原文；翻译器调用计数为零。

### D5. RED/GREEN：完整 fake-provider 子进程 E2E

测试 harness 只负责串联正式端口，不成为生产 orchestrator。fake provider 是独立子进程，支持 `discover` 和 `fetch-candidate` 两个 operation，输出 earnings-transcripts 已冻结的 JSON schema。

成功链的精确步骤：

1. 在短路径 `C:\\cwt\\m2p-<run-id>` 创建开始时不存在的 wiki/run root。
2. 写测试专用 catalog/runtime/provider policy；baseline 记录目录成员和 raw SHA。
3. 调用 fake provider `discover`，只得候选 metadata，不得正文。
4. 调用 CWP `preflight-discovery`；未 allowed 则测试失败且 fetch 调用计数必须为零。
5. 用唯一候选调用 CWP `preflight-candidate`，取得正式 authorization/admission。
6. 调用 fake provider `fetch-candidate --include-source-payload`；父进程同时限制 timeout 与 stdout bytes。
7. 把原样 `/2` object 交给 CWP stdin importer；响应不得含全文/base64/绝对路径。
8. 从 importer 的 source ID/hash 和 catalog document identity 建 `SourceRef`，调用正式 `SourceVersionReader.open_version()` 或 reader CLI；禁止直接打开 canonical path。
9. 从 verified bytes 重新派生英文文本，运行 transcript selector，逐 locator 回放至少两条业务叙述。
10. 第二次执行先 resolve/reuse；fake provider fetch 调用计数不增加，raw 数量/SHA 不变。
11. `finally` 验证精确 root containment、无 reparse path 后删除；结束状态恢复为 run root 不存在。

同一文件内集中覆盖失败链：

| 场景 | 必须断言 |
|---|---|
| discovery deny | fetch=0，catalog/staging/raw=0 |
| candidate action 缺失 | fetch=0，catalog/staging/raw=0 |
| provider timeout | child 被回收，import=0，staging/raw=0 |
| stdout 超限/坏 JSON | importer 未调用，staging/raw=0 |
| redirect/effective URL 漂移 | importer 拒绝，staging/raw=0 |
| policy 在 fetch 后变化 | importer 拒绝，staging/raw=0 |
| import 后 reader hash 不匹配 | reader fail closed，不回退到任意路径 |

### D6. earnings-transcripts 兼容核对

本阶段不把 E-T 内部代码复制进 CWP。只对以下 producer contract 做只读/离线兼容测试：

- request schema `/1`、discovery result `/1`、candidate-fetch request `/1`、result `/2`；
- `--include-source-payload` opt-in 才返回 bounded raw；
- tool 无翻译入口；scraper 的 `--disable-translation` 仅影响旧批量工作流；
- provider tool stdout 只有一个 JSON object，stderr 不泄漏 key/正文。

E-T 当前改动未提交，因此 Phase D 收据必须列出其 commit/dirty 状态；在 Phase F 正式 caller 接线前，先把 E-T 自有测试和合同提交成可引用版本。CWP 不以未提交外仓实现作为生产依赖。

### D7. M2-provider 集中验收

只在上述小步全绿后运行一次：

1. provider policy/admission/validation 单元与合同测试；
2. importer/material/preflight CLI 集成测试；
3. 完整 fake-provider subprocess E2E；
4. Phase C 的 12 件 narrative E2E 中 transcript 两例和 locator replay；
5. architecture/complexity ratchet；
6. Ruff、strict mypy、config doctor、pre-commit scoped hook、`git diff --check`。

不在每个 helper 后重复跑全仓。全仓回归留到 Phase F consumer 接线或最终合并门。

## 6. 明确验收指标

### 功能

- 完整链至少 1 个 HTML 和 1 个 TXT 成功；英文内容逐字不翻译。
- discovery/candidate/fetch/import/reader 的 request、security、FY/Q、as-of、provider document ID 全部同一身份。
- provider 原件只保存一份；重复运行 raw 数量和 SHA 不变。
- 至少两条 selected evidence 可从 verified reader bytes 回放。

### 安全与清理

- 所有 prefetch 拒绝均为零正文 provider 调用。
- 所有 postfetch 拒绝均为零 canonical raw/sidecar/catalog source，staging 清空。
- timeout/坏 JSON/超限 stdout 不留下 child、临时文件或部分 catalog。
- 测试前不存在的 run root 在 finally 后仍不存在；禁止清理仓库根或共享 TEMP。

### 架构与复杂度

- 新模块每个顶层函数 custom McCabe `<=10`，Ruff C901 `<=10`。
- `provider_use_policy.py`、`transcript_import.py`、`transcript_import_cli.py`、`transcript_material.py` 的 38/41/23/19 freeze 全部移除，或每项下调至实际 `<=10` 后才可签收；不得只换文件名保留同样巨函数。
- domain/contract 层没有 Path 配置、SQLite、subprocess、writer 反向依赖。

### 空间

- canonical raw 永久增量等于唯一 provider payload；不再持久化第二份全文。
- lineage/provenance/selected evidence 分别计字节；逐行 locator 表永久字节为零。
- E2E 输出 raw、sidecar、catalog、selected bundle 的分项字节和 derived/raw 比率。

## 7. 阶段停止条件

出现任一项立即停止 Phase D 并记录：

- 需要修改 RF 文件或读取其未提交实现才能继续；
- 需要真实付费 provider 才能使默认测试通过；
- canonical raw 被覆盖、删除或重复写入；
- fail path 有 staging/raw/catalog 残留；
- 为让测试通过而放宽 SHA、identity、FY/Q、as-of 或 URL 校验；
- company-wiki 开始编排 filing + transcript partial success；该职责属于 Phase F 的 filing-fetch adapter；
- E-T 需要翻译凭证或翻译调用才能产出原文。

## 8. 收据格式和提交策略

Phase D 完成时在 `progress.md` 写一份节点收据，至少包含：

- CWP/RF/E-T refs 与 dirty 摘要；
- RED 失败事实和对应修复；
- 测试命令、passed/failed、耗时；
- fake provider 调用计数、raw/staging/catalog 数量；
- raw/sidecar/lineage/selected bytes；
- 复杂度前后表；
- 测试根清理收据；
- 未覆盖的真实 provider 权利和 Phase F 工作。

提交分两次：

1. 本实施细则和基线记录单独提交；
2. Phase D 产品代码、测试和完成收据在集中验收绿后提交。

均不推送。外仓不与 CWP 同一提交，不用跨仓未提交 diff 作为依赖。
