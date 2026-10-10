# 官方分页 JSON 原件、公司投影与证据定位合同调查

状态：只读共因调查与实施提案；未修改运行源码，未宣称 M3 或 JSON 链路修复完成。基线为 `13a7648cee20362fc082f68248e286468837612d`。本调查不是公司投资审查，也不新增签收、授权材料、任务库或数据库。

## 1. 核验范围与原件发现

核验 sealed run：`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012`。`execution/manifest.json` 的实际 SHA-256 为 `33efe76877f539ceb2acb3b81fe5e5fa3b04673ad5453f28ef176e0e22547d25`。逐一重算 86 个成功表单页的字节数、SHA，全部与 reconciliation 和 sealed manifest 登记吻合；共 668,749 字节。各流实测如下：

| 流 | 原页 | 原记录 / 流内唯一 ID | 对目标公司的记录类型 |
|---|---:|---:|---|
| latest | 65 | 195 / 195 | 7 个已回答问答、1 个公司结束致辞 |
| questions | 11 | 33 / 33 | 15 个未回答问题 |
| precollect | 10 | 29 / 29 | 1 个预征集问题，原记录同时含非空 `answer` |

总计 257 条原记录，其中目标公司 24、其它公司 231、未归属 2；原件中非空 `companyId` 共涉及 21 个不同值。三流之间未发现相同 record ID；在这批已回答记录中未见 `qactivityCompanyId != aactivityCompanyId`，这不排除其它活动存在跨公司问答。86 页均为 `success=true, code=200`。这些计数证明本次观察的页与 ID 覆盖，不证明供应商提供了原子时间点快照，更不证明 257 条均属于一个 issuer。

来源捕获核验采用实际冻结输入/stdout/stderr及 call ledger：例如 call `0be19f4759db4457a8a7c25442630277`，`input_complete=true`、`output_complete=true`、exit 0。对应 input、consume、stdout、stderr 四个文件的 SHA/长度也与 sealed manifest 一致，stderr 为 0 字节。stdout 记录实际 POST、表单 body、HTTP 200、`application/json;charset=UTF-8`、各页字节数及 SHA。冻结输入说明编码为 `application/x-www-form-urlencoded`、数组重复字段；这组证据没有记录发送到 socket 的完整 request bytes，不得把输入 JSON 序列化结果当真实 wire body。

**必须更正的旧说明定位：** `IMPLEMENTATION.md` 将 `qa-latest-form-01.raw` 的 `/datas/0/records/2` 写成 ID 2508385。实际该位置是 ID **2508409、清溢光电、activityCompanyId/aactivityCompanyId 57808**。ID **2508385、中微公司、57790** 的真实位置是 `qa-latest-form-18.raw` 的 `/datas/0/records/2`，页 SHA `fc1c2a8ebb7cb44b3cf6f82a5ecfa5641cf81478ed35e615c0928f36a2a389fe`。保留旧错误作为回归反例，不修改原 JSON。

另一个不能由流名替代的事实：`qa-precollect-form-10.raw` 的 `/datas/0/records/1`，ID **36395**，具有 `question` 和非空 `answer`，同时有 `companyId=145565`、`stockCode=688012`、正式公司名及 shortName。`crtTime=2026-09-04 18:55:49`，`updTime=2026-09-10 15:19:54`；原字段没有具体回答人或独立 answer 发布时间。可以称为“公司归属的官方预征集答复”，不能凭字段缺口补造 speaker 或答复精确发布时刻。“7 答复”只适用于 latest 已回答问答，不能推成全部流仅有 7 个非空答复。

配套 [JSON_EVIDENCE_INDEX.json](JSON_EVIDENCE_INDEX.json) 只存 4 页、6 个代表记录的引用、ID、身份/状态字段和严格字节区间，不存第二份全文。区间由严格树遍历建立 JSONPointer，再独立对原 bytes 切片 `json.loads` 核验。

## 2. 现有入口与拒绝机制

先使用 CodeGraph `status/search/context/explore/node/callers/files` 调查结构；索引已初始化，995 files / 21,730 nodes。两次 explore 已用完。索引对部分近期函数、CLI 和 normalization 文件不完整，且 official import 的索引行号落后于当前文件；只在索引已定位文件或明确缺失文件中补读实际源码，未把 legacy writer 当当前入口。

| 责任层与现有入口 | 已核验的行为及缺口 |
|---|---|
| `source_catalog/official_source_cli.py::main` | 公共 module CLI 支持 import/discover/capture/recover；import 输入绝对原件文件、显式 tmp config；输出 SourceRef。不是 `source_catalog/cli.py` 的子命令。 |
| `official_source_flow.py::_metadata`（92）、`_validate_bytes`（150） | metadata 要求单一 entity；JSON 与 TXT 一起交给 transcript extractor。 |
| `transcript_json_extract.py::_record_content`（44）、`_encoded_content_span`（58） | 仅接受 root object 的字符串 `content` 或长度恰一的数组中的该 object；并拒绝其它同名 content 的歧义。该限制适用于单条电话会 JSON。 |
| `official_source_flow.py::_persist_capture`（340）、`_import_retained`（396）、`recover_official_source`（725） | 原 bytes 与实际 capture observation 先写入现有 staging；失败保留、AcquisitionJournal 登记，恢复可复用确切 bytes。不是新队列。 |
| `CanonicalSourceWriter::import_original_staged`（315）、`_destination`（437） | 验 SHA、大小、存储边界，统一去重/原件/登记；原件路径与 metadata 仍依赖 `SourceRequest.entity`。 |
| `SourceRequest` / `SourceVersionReader::_query_local` | 公司、market/security、kind/期间、as-of 是查询资格；不能为混合原页伪造一个公司以满足它。 |
| `SourceRef` 2.0 / `SourceVersionReader::open_version`（620） | Ref 本身绑定 document/source/SHA/size/MIME，无 entity 字段；正常 read 验 exact version 和实际返回 bytes。适合继续代表不可变原页。 |
| `document_normalization::normalize_document` / `normalization_identity` | 当前支持 HTML/PPTX/DOCX；没有通用 JSON pointer parser。 |
| `source_catalog/normalizer.py::_json_xml_markdown`（1324） | 将 JSON 原文本作为一个 paragraph 的 fenced block，parser=`structured_text/1.0.0`；没有逐字段 JSONPointer，也不是 AUTO 选择所用 JSON 路由。不能把这一能力称为新合同已经满足。 |
| `automation/narrative_formats.py::source_class_for`（26） | 凡 TXT/JSON 均分类 transcript；单修 importer 后 AUTO 仍会按电话会再失败。 |
| `NarrativeSelectHandler::_select`（288）、`_select_transcript`（367） / `automation/narrative_replay.py` | 按 source_class 分 filing/transcript；JSON 又走 transcript material/line binding；生成与 replay 必须一同扩展。 |
| parser 版本选择 | 没有发现独立通用 `ParserRegistry`；实际版本登记是 `narrative_formats::parser_component`、`NarrativeNormalization.identity`、normalization `require_parser_version` 和 `transcript_parser_contract` 的 frozen layouts。不得改现有名字下的旧算法。 |
| `EvidenceCoordinates` / `EvidenceSpan` | `loc:v1` 坐标只有 page/paragraph/table/row/column/chars；没有 JSONPointer 或 byte fields。已有 `structured_value.source_locator` 可承载版本化格式 locator，unit/span hash 绑定该结构。 |

本次只运行无配置、无写库的两个纯函数对真实首个 latest 页核验：`_record_content` 返回 `JsonTranscriptError: expected exactly one transcript record`；`_validate_bytes(..., application/json)` 返回 `OfficialSourceError: invalid_text_original`。未启动公共 import CLI、模型、供应商测试或公网请求。

因此至少有三层共因：**MIME admission 的电话会结构条件、单 issuer 的 raw metadata/存储意图、AUTO 的 MIME 即 transcript 路由**。只修改第一层不构成可用修复。

## 3. 建议合同：原页、投影、消费请求分别有身份

以下名字/版本是建议的新 DTO，不是已存在接口。保持原 `SourceRef` **2.0** 字节身份与旧 `SourceRequest` 公司查询语义。

### 3.1 原页登记

新增 `official-source-import-request/2`，接受原 bytes 的 source identity 与 typed `source_subject`：

```json
{
  "source_subject": {
    "kind": "multi_issuer_event",
    "event_namespace": "official-provider-event",
    "event_id": "observed-provider-event-id",
    "issuer_refs": [],
    "attribution_status": "partial"
  }
}
```

`kind` 仅允许 single_issuer / multi_issuer_event / unattributed；单 issuer 仍要求有真实 identity 证据。数组是“原页关联主体”，不是原页 owner；不把 publisher、活动名、entity hint 或请求目标公司填进 issuer 槽位。issuer_refs 只含通过现有身份责任层解析的 canonical ID 和其来源证明；provider company ID 与 canonical security ID 保持两个字段。尚未解析的 provider ID 作为诊断保留，不能冒充 canonical ID。

原页 import 内部改为 source-oriented storage intent，含 provider/event/page/request identity，复用现有 CanonicalSourceWriter、SHA 去重与注册事务；混合原页的路径由存储层在现有配置根内选择共享来源位置，消费者不传路径，不在每个公司 raw 中重复 copy，不用一个虚构公司名绕过 `_destination`。现有 `_OfficialOriginal` / `SourceRequest` 到 storage 的桥接须同时调整。

`SourceManifest` 1.0.0 已支持多个 `entity_ids`，但要求至少一个；这说明多关联主体可表达，不能证明现 importer/resolver 已支持共享原页。如果 identity 层尚不能给任何 canonical issuer，现 manifest v1 不可硬塞空数组或假 ID：实施时显式提供 versioned source-subject/manifest **2.0.0** 合同，允许 unknown/partial attribution 并保留真实 provider/event 身份；旧 manifest 1.0.0 继续严格读。已完整身份的旧来源不需要重写原件。混合页的 source `published_date` 未经页面发布证据证明时为 null，不能取 capture 日期或任一 record 的日期充当页面发布日期。

通用合法 JSON 原页可登记为 raw source / parse pending 或 unsupported layout。错误响应只能留在原 capture/recovery observation，不成为可选业务证据。as-of 资格不因 raw 能入库而放宽。

### 3.2 公司投影

新增 immutable `source-projection-ref/1`：

| 字段 | 约束 |
|---|---|
| `parent_source_ref` | 原页 SourceRef 2.0；多页投影使用有界、顺序固定的 parent refs 数组，逐页 SHA 绑定。 |
| `projection_id` / `projection_sha256` | 由 parent refs、schema adapter/version、issuer identity 及证明、筛选规则/version、stream/活动、as-of/期间范围、记录定位清单共同 canonical hash；不能只用原页 SHA。 |
| `adapter` | 明确 name/version、layout ID 和映射 fingerprint。 |
| `issuer` | canonical entity/market/security 与 provider company IDs 分列；附 identity evidence 的原页 Ref + pointer。 |
| `records` | 仅有 record pointer、provider record/logical key、该记录原 token hash、字段绑定/role/state 与质量；不嵌完整 raw record、整页或第二全文。 |
| `coverage` | 原页已解析、全流分页覆盖、issuer attribution、selected evidence 覆盖分别报告，未知值不可变成 true。 |

投影不是原件：`open_version(parent_source_ref)` 返回整页真实 bytes；投影 read 返回派生清单和引用。投影的 hash 不能成为原页的 `content_sha256`。同页另一个 issuer 创建另一个投影，复用同一个 raw SourceRef，不能触发 `source_identity_conflict` 后改原页 owner。

公开查询新增 `source-projection-query-request/1`，内含现有 `SourceRequest`（公司/期间/as-of）和页集合或 event scope。resolver 可以按关联主体找到候选 raw，但返回 source + projection，不能把 multi issuer raw 作为单公司 SourceHandle。SourceExport 扩展使用显式 **2.1** 或独立 `source-projection-export/1`，保持旧严格 2.0 收包不被新增字段悄悄改变；传出 source refs、projection refs、EvidenceSpan，不共享可变数据库、不写 RF/StockWiki 目录。

### 3.3 JSON 结构 parser 与声明式 layout adapter

新增纯 `cwp_json_structure_parser/1.0.0` 和 `official-paged-qa/1.0.0` adapter。parser 负责合法结构、原 bytes token span、JSONPointer；adapter 负责已声明 collection path、分页 envelope、记录身份字段与 Q/A 字段映射。SSE 所见 `/datas/0/records` 是一种注册 layout；不得写 `if issuer == 688012`、固定公司 ID 57790/145565、公司名称匹配或 SSE 专用 importer 绕过。未知 official JSON layout 应保留 raw，报告 `unsupported_json_layout`，不能递归搜索每个 `content` 并拼成电话会。

layout DTO 建议 `official-json-layout/1`，限定已注册 collection pointer、success/error/pagination 字段、ID及issuer字段、text field角色规则和时间字段；不接可执行表达式、eval、任意递归 wildcard。其它官方布局使用同一 parser 和新声明式映射，并以未见 fixture 验证；语义字段尚无证据时保留 unknown。原字段为 provider translation 的 `contentEn/questionContentEn` 不可冒称原语言回答；原语言和 provider 译文字段分别定位、分别标明来源。

选择与 replay 的 parser identity 均登记 JSON format、精确 parser/adapter version；建议 JSON 派生 parser 对外名 `cwp_official_json/1.0.0`，明确 composition 包含上述结构与adapter版本，unit identity 也绑定 mapping/projection fingerprint。原 transcript extractor `transcript-original-json/1.0.0`、`transcript-material/2` 与 transcript parser 0.1.0/0.1.1/0.2.0/0.3.0 的历史算法不变。

AUTO source class 新增 official_json，使用版本化 event/select/bundle 合同（例如现 2.0 之外的新 **3.0**），显式带 projection ref。`NarrativeBatchRequest` 目前按 document_id 去重；新版必须按 source+projection identity 去重，否则同页两个 issuer 会相互覆盖。generation 必须绑定 parser/adapter、projection/filter/as-of、selector/profile 与当前预算；旧结果只按其记录的版本 replay，不自动“升级合格”。

## 4. JSON 合法性、定位、角色与时间的硬约束

### 4.1 有界 admission

byte validation 与文档资格分开，但并非任何 JSON 都可变成业务来源。新 parser 在构建大对象前用 token/结构计数检查，不在 `json.loads` 成功后才检查无限递归；复用 `NormalizationLimits` 的 byte/text/unit/deadline 预算，并新增正整数 `max_json_depth`、`max_json_nodes`、`max_json_string_bytes`。建议首版默认 depth 64、nodes 200,000、单 string 4 MiB；source/output 默认仍遵循现 normalization 64/16 MiB，实际取请求/部署上限与 importer 128 MiB 上限的较小值。这些是提案值，不修改生产 config。分页使用显式总页/总字节/总秒数范围和现 acquisition budget，不无限追下一页。

| 情况 | 明确行为 |
|---|---|
| 空 bytes、仅空白、非法 UTF-8、截断、HTML 伪 JSON | 具名 `empty_original` / `invalid_json_encoding` / `invalid_json_syntax` / `mime_mismatch`；保留实际 capture，不能激活业务证据。 |
| 重复 object key | 按解码后的 key 判重复（包括 escaped 同名），任何深度均拒绝 `duplicate_json_key`；否则 pointer 含义不唯一。 |
| NaN/Infinity/-Infinity、溢出数值 | 拒绝非标准 constant；数字 token 不转成无穷 float；用有界词法/精确数值表示，报告 `nonfinite_json_number`。 |
| lone surrogate、非法 escape | 拒绝；UTF-8/BOM 是否支持须明确，若支持 BOM，其 3 个 bytes 仍计入 raw offsets。 |
| depth/node/string/output/deadline 超限 | 精确 budget code；不静默截断，不宣称 complete。 |
| `{}`、`[]`、null、标量、无文本字段 | JSON 语法可合法，但不自动具有业务资格；unknown/empty layout 原件可留存，`no_business_payload`，0 selected。 |
| 成功的分页 envelope + `records=[]/total=0` | 合法空页观察；可得到 complete/no evidence，不能拿 line_count=1 或伪空文字使 `DocumentStructure.coverage_complete` 通过。JSON coverage DTO 必须真实表示零记录。 |
| HTTP 非 2xx，或声明式 envelope `success=false`、error/status/code 失败 | `response_is_error`；实际原件与费用保留，但不作公司事实。仅字段名含 error、或业务文本出现错误一词，不能泛化拒绝。 |

本批有实际 negative control：最初三个 JSON body 请求返回 JSON `status=500, error=Internal Server Error`，分别 138/138/141 字节，已在极小索引中列 SHA。HTTP 状态和 payload status 必须分别保留；不得因可解码为 JSON 就把它们规范化为公司正文。

### 4.2 原 bytes 回放与连续 locator

每个记录和字段须可按 **原页 SourceRef + RFC 6901 JSONPointer + zero-based half-open raw byte range** 重定位。pointer 的 `/`、`~` 必须按 `~1`、`~0` 处理，数组顺序只指真实原页序号；不能从 URL、record ID 或目标公司投影重编号推断 pointer。token 范围含引号/括号，string body 范围不含引号；两种范围需分字段命名。

建议格式 locator：`cwp-json-pointer/1|p=<UTF-8 percent-encoded RFC6901 pointer>|b=<start>:<end>|d=<decoded-start>:<decoded-end>|x=<transform-version>`。编码使 pointer 不能被 `|`、斜线、非 NFC key 的显示规范化破坏。解码字符串中的 offset 与 raw bytes offset 分开；固定 transform 为 JSON string decode + 现 NFC/空白规范化，保留其版本。substring 必须在完整 JSON value decode 后按合法 decoded 字符边界切，不在 `\\u` 转义、surrogate pair 或多字节 UTF-8 中间截断。

复用 EvidenceSpan v1：`coordinates.paragraph_index` 为原页内字段的稳定词法 ordinal，不能因 issuer 过滤而重排；`char_start/end` 如使用，仅是指定文本坐标，绝不塞 byte offset。`structured_value` 保存真正 `source_locator`、pointer、byte ranges、record ID/roles、parser/adapter/projection identity。`loc:v1/paragraph:...` 是证据坐标，JSON source_locator 是原件定位，两者都校验。相同 text 的不同记录保留独立定位与 role，不能按文本去重丢掉主体。

一次展示的 Q+A 可组成 context group，但每个原字段分别是连续、真实的证据片段，group 保存各成员原页和 locator。**2508385 的 answer content 在 bytes `[5037,5557)`，questionContent 在 `[6703,6766)`，真实字节顺序是答复在问题之前**；显示 Q 后 A 不能伪称它们在 raw 中连续，也不能沿用 transcript bindings 单调行顺序的假设。多页/跨字段组不能发明一个连续 byte range 包住其它公司内容。最小首版可保留整字段并明确长字段 budget refusal，不能删条件后发布部分管理层事实。

replay 必须：正常 SourceReader 验整页 SHA/size → 按记录的 parser version 一次解析 → 同时验证 pointer、token范围、decoded片段、transform、role、identity/record关联、unit/span hash → 验 selected evidence 全部成功。只验证 byte slice 可解码或显示 text 相同仍不足。除精选证据和小型 manifest/locator 外，不长期写第二全文或 JSON 重序列化“原件”。

### 4.3 角色与归属

| 观察字段组合 | 生成的证据角色与边界 |
|---|---|
| latest record：questionId/questionContent + 非空 content + isAnswered true | 问题=`investor_question`；答复在 speaker/issuer 证据成立时=`management`；Q/A 各自 provider company 字段、时间和 pointer 保留；`questionId` 显式关联，不靠相邻行推断。 |
| questions：content + isAnswered false | `investor_question` / `question_unanswered`；其陈述和数值不是公司的确认。 |
| latest 2508406：questionType 3、无 questionId、isAnswered false | `company_statement/closing_remark` source subtype；可证明公司致辞，不算一条已回答 QA。不能仅因姓名属于管理层而让感谢语占业务配额。 |
| latest 2508509：无 issuer 字段的路演结束发言 | event/editorial 或 unknown；不能归给目标 issuer。 |
| precollect 36395：question + answer + companyId/stockCode/companyName | 问题独立；答复为 company official answer subtype，可映射现 summary 的 `company_filing` source role，speaker 字段保持 null。映射成立的依据是公司 identity + 官方答复字段，不是“像回答”的文本。 |
| 归属字段缺失、互相冲突或跨公司 Q/A | 记录原字段/诊断；Q 和 A 的 issuer 不互改。只有对应 issuer 的投影可选其字段；不能以 answer 的公司覆写 question 的目标公司。 |

已有 `narrative_evidence::_validate_claim_roles` 只允许 management/company_filing 支持 company_statement，analyst/investor_question 支持 analyst_question 且 modality=question，须保留这项约束。adapter 的未知角色不能自动映射 management。语义问答投影与全文 preview 不同，raw 中所有未知/其它 issuer 仍可回放，不进入目标公司的事实选择。

### 4.4 期间、发布时间与 as-of

原 JSON 时间保留原字段原值；provider 时区不经官方证据证明，不把无 tz 字符串直接转 UTC。`crtTime`、`updTime`、`auditTime`、`questionDate`、`questionUpdDate` 不互相替代。每个字段的可用日期资格附 `date_semantics` / `publication_evidence`；无答案独立 publication 字段时报告该缺口，不能把更新时刻无条件当首次公开时刻。

对历史 as-of，raw 可留存，但记录/答复晚于 as-of、答复时刻未知、同 ID 后续修订无历史版本，都不能成为“该时点已知”的公司事实。管理层谈未来项目的 **statement 发布时间** 和 **计划发生日期** 不混淆：计划 2027 投产可以出现在 2026 已发表答复中，但资料系统不据此生成 2027 收入预测。fiscal period 保留披露指向的报告期或 unknown，不按发布时间年自动设置。

## 5. 分页、HTTP、恢复与费用

目前 `capture_official_source` 固定 `client.stream("GET", source_url)`，而 sealed UI/原生捕获证明三流均为 POST。不能把 POST 的 raw 假装成 GET URL 原件，也不能为了连通去猜 query 参数。未来 capture request **/2** 必须显式 method、已证明的编码/请求字段、request identity，支持有界 POST；import **/2** 可先复用已捕获原页，完全不发公网请求。

分页 DTO 保存 stream、activity/event、真实 pageNo/pageSize/current/pages/total、capture window、每页 raw ref/请求 fingerprint、record IDs与版本、expected/fetched counts、duplicate/missing/conflict IDs、coverage status。complete 至少满足：成功 envelope、页码唯一且连续、页内条数合理、页总数/total 一致、实际累计数与唯一 ID 数核对；total 波动、同 ID 不同版本、页乱序或缺页具名 partial/conflict。重试仅补明确缺页，在累计预算内，不能把不稳定多次观察合并冒称同一 snapshot。

费用/空间复用现 AcquisitionBudget、staging、AcquisitionJournal 与 AUTO Store 的 lease/generation/outbox。失败后的完整原件可 recover，partial bytes 不可 append 后冒充一次 HTTP 完整响应。相同 SHA 页复用零新网络；同 source+projection+generation 完成结果复用零新模型/零 reservation；filter/parser/profile 改变仅重算需要的派生，旧 bytes 不重下载。页面共享、不同 issuer 和失败恢复均计入现累计 byte/token/cost/time/持久化/临时空间上限，不增加另一账本。

捕获已发生后 importer 失败仍需保留 HTTP actual observation、decoded bytes、已知 wire bytes、usage completeness、费用未知状态。此次 668,749 是成功原页的已保存字节数，**不是所有失败尝试的 wire bytes，也不是本 run 的总网络量或总费用**；历史缺失 usage 不能在新导入时变成零。新离线 import 的 acquisition usage 才是零新增，不改写原捕获费用。

## 6. 责任测试与一个公共 CLI 离线联调节点

下面均为实施验收清单，本调查未运行矩阵，未测真实供应商或模型。测试 config、来源根、AUTO DB、工作目录只用自己有界 TEMP 夹具；不能改 `config/source_catalog.yaml`。真实 sealed 原页只读、测试需要保存时由公共 importer 在独立根落原件。

| 责任 | RED/正常控制/失败控制 |
|---|---|
| admission/import | 真实 latest 首页经过公共 CLI 当前 RED=`invalid_text_original`；修后按新 multi issuer DTO 成功，SHA/size逐 byte 相同；FMP golden 单 root content / singleton array、旧 TXT 仍正常；旧两record电话会拒绝继续成立。重复key、NaN/溢出、孤surrogate、深度/节点/单string/时间/字节超限、截断、伪HTML、空/error envelope逐项负控。 |
| source identity/storage | 同页两个 issuer 两个投影、一份raw、同SourceRef；owner不改；错误market/security、错误provider ID映射、缺/冲突归属不可静默通过；共享父页失效/被改 bytes 正常read拒绝；原件同SHA重用不新增copy。 |
| structural parser/replay | 中文直接UTF-8、escaped中文、emoji/surrogatepair、escaped换行/引号/backslash、`~`/`/` key、同文本重复记录、字符串中的“content”文字、数组nested布局、可选BOM；pointer/byte/token/text/role/version任一篡改都拒绝。固定2508409/2508385错误页回归；固定answer在question前的非连续group。 |
| adapter/selector | 7 latest answers / 1 company closing / 15 unanswered / 1 answered precollect分别可回放；host致辞和其它issuer负控；question内容不能生成company statement；specific business answer保留否定/条件/计划语言。新issuer和另一声明式官方JSON布局未见fixture不改公司逻辑；未知layout诚实unsupported。 |
| date/coverage | 记录未来时刻、answer publication未知、provider时区未知、同ID更新、total漂移、缺页、重复页/ID、跨stream逻辑关联、合法total=0、crossissuer问答负控；完整raw page≠完整event snapshot≠完整issuer projection。 |
| AUTO/recovery/export | 旧generation/旧transcript replay保持；新projection入generation；lostresponse/restart/lease失效/outbox恢复不重复保存/付费；repeat零新download/model/reservation；现空间预算失败不发布half result。正常SourceRead/SourceExport及RF公共consumer读取SourceRef+projection+locator，禁物理路径补洞。 |

**一个离线联调方案（共用整合节点，不新增项目许可）：**

1. 在独立 TEMP 创建与现 integration fixture 相同的最小 catalog root/config；断网运行子进程，关闭 dotenv/生产供应商配置读取，冻结每步 argv/stdin/stdout/stderr/exit 与 original SHA。使用完整真实四个 representative raw 页（first latest、page18 answer、first question、last precollect），另用两种未见的小型 layout、FMP golden/TXT 和真实 500 error controls。离线资料不是公网 companyfilter 成功证据。
2. 现存公共命令先固定 RED：`python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --operation import --project-root <TEMP> --config <TEMP>/config/source_catalog.yaml --input-file <ABSOLUTE_SEALED_RAW> --request <TEMP>/import.json`。现版本仅能用旧请求复现格式失败；不能把mixedpage旧request目标公司误标签当正确GREEN。实施后以 import-request/2 和真实source_subject运行相同入口。
3. 原件读取保持现 `python -m company_wiki.source_catalog.source_reader_cli --config <TEMP_CONFIG> --document-id <D> --source-id <S> --content-sha256 <SHA> --purpose source_export`，stdout严格等于输入原bytes；重复import和read哈希一致、零下载。混合页的issuerquery通过建议 `source-projection-query-request/1`，不让旧单公司query伪装已支持。
4. 在同一 official CLI **建议新增** `--operation project`，request-schema=`official-json-projection-request/1`，输入parent SourceRefs、注册layout ID、目标issuer/identity证据、as-of与限额；不接受raw path作为消费者fallback。返回ProjectionRef、selected EvidenceSpan及coverage，选择/replay全为纯本地。这个operation当前不存在，不能提前写“已通过”。
5. 对每个selected span由SourceReader取父页，公共project/replay及建议SourceProjectionExport验证JSONPointer/真实byte/role/identity。将响应交RF公共读取合同的离线consumer fixture，核验“其它issuer/未答问题不能作为公司确认”；不运行收入预测、估值或模型质量评估。若需要覆盖现AUTO summary→verify→transport节点，整合负责人可使用现loopback的固定协议响应fixture；这是离线传输/合同测试，不能代替真实供应商验收。当前调查没有发这类调用。
6. 用同一TEMP继续lostresponse/recover/repeat和budgetnegative control；只保留小型结果/locator/usage证据，先验绝对目标确属自己的TEMP再原生PowerShell清理。M3原run、raw/config及其它owner目录不动。短责任测试进入现有CI，大分页/付费/真实companyfilter验证留在已安排的大整合节点。

## 7. 必须继续实测的官方 companyfilter 与未知边界

sealed `qa-chunks-3.raw` 为 153,140 bytes，SHA `fe9a81a9242d87bbcb1d5df45675694ac1e96a868875266fba1a1b72e3d785ec`。已只读核对 `getQuesList()` 和 `getPreSolicitation()` 的实际代码：前者POST data含pageNo/pageSize/questionType/questionTypeList/activityId/askTypes，后者含activityId/pageNo/pageSize；这两个所见请求没有公司筛选字段。UI也出现用于提问表单的 `quesForm.companyId`，不能据此推断它是“读取问答按公司筛选”的参数。已有原生成功捕获同样没有server companyfilter，且返回明确多公司records。

下一次实测要保存：真实official UI中的公司筛选操作对应请求、method/编码、确切field及其ID命名空间、实际server原bytes与SHA；目标issuer和另一issuer的对照请求；每页所有record归属、target总量、unknown/crossissuer记录、全部页覆盖、错误ID的negativecontrol。需要证明它改变**服务器响应**且覆盖目标公司，而非UI本地过滤/忽略未知参数。若发现无官方过滤能力或只是localfilter，保留共享原页并使用上述投影。不得凭名字猜 `activityCompanyId/companyId` 参数并发公网GET。

仍未知：官方filter存在性/真实行为、queryType等枚举的完整官方定义、无tz时间的官方时区语义、answer首次公开时刻与historicalrevision接口、event快照一致性、跨公司Q/A的实际案例、另一官方真实layout，以及新source-subject/manifest版本与RF读取端的完整兼容验收。已证明的是当前原件与拒绝共因、定位更正及可实施的合同边界；不能据此宣称全部provider支持、总结已被RF采用、或研究模型已经通过。

本调查新增费用与公网请求为零；未读其它公司reviewer报告，未写raw/生产config/跨仓文件，唯一交付为本文件与小型证据索引。后续源码实现和完整审查由MAIN整合节点负责。
