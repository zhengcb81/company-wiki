# D4-04 handoff — 电话会导入 wire 与内部类型分离

状态：**实现、测试与独立审查已完成，等待 ROOT 接收。** 本卡只改 CWP 的 request decoder 与本仓契约测试；FF 生产 emitter、ET、source acquisition/write path、`integration/` runner 均未触碰。

## 版本与交付

| 项 | 值 |
|---|---|
| 基线 HEAD | `503f6510`（母仓 master 同点） |
| 交付 commit | `5daf7e1e7` 实现、`84764733c` 本文档、`90e9c7e26` 审查加固（分支 HEAD，接收以 HEAD 为准） |
| 施工位置 | 独立 worktree `C:/Users/郑曾波/Projects/company-wiki-d4-04-wire` |
| 改动路径 | `src/company_wiki/source_catalog/transcript_import_cli.py`、`tests/contract/test_transcript_import_cli_e2e.py`、新增 `tests/fixtures/transcript_import/{ff_import_request_v2.json,generic_html_import_request_v2.json,README.md}` |
| 写域外改动 | 无。`.githooks/pre-push` 仅文件模式差异，属母仓既有状态，未 stage |

## 公开协议（唯一合同）

- `REQUEST_SCHEMA = "company-wiki-transcript-import-request/2"`，`RESPONSE_SCHEMA = "company-wiki-transcript-import-response/3"`，均**未改**。
- 入站 envelope 仍是四字段 `schema_version/source_request/candidate/transcript_result`，精确集合，未加字段。
- `source_request` 仍为 14 字段：`schema_version, entity, market, security_id, document_kind, form_type, fiscal_year, fiscal_period, language, provider, provider_document_id, as_of_date, mode, allow_download`。
- `candidate` 仍为 19 字段：`candidate_id, provider, provider_document_id, market, entity, title, source_url, document_kind, filing_date, fiscal_year, form_type, fiscal_period, language, amended, etag, last_modified, remote_size, adapter_payload_json, schema_version`。
- 解码改为显式表 `_SOURCE_REQUEST_WIRE` / `_CANDIDATE_WIRE`（`(wire 字段, owner 属性)` 对），并导出只读 `SOURCE_REQUEST_WIRE_FIELDS` / `CANDIDATE_WIRE_FIELDS`。**不再调用 `dataclasses.fields(SourceRequest/DownloadCandidate)`**。
- 字段集必须精确相等：缺字段与多余字段分别报 `source_request fields differ from schema` / `candidate fields differ from schema`；owner 构造失败（含错误 `schema_version`）报 `source_request is invalid` / `candidate is invalid`；错误类型仍是 `TranscriptImportCliError(ValueError)`，CLI 仍输出 `status:"rejected"` + 退出码 2。
- 内部演进规则：owner 新增**带默认值**字段不进表 → 该字段取 owner 自己的默认值，wire 不变；要把它放上 wire，必须同时改表并升 `REQUEST_SCHEMA`。owner 新增**无默认值**字段会在解码处以 `... is invalid` 显式失败，而不是由 decoder 凭空补值。

## 字面 fixture

`tests/fixtures/transcript_import/ff_import_request_v2.json`
- `source_request` 逐字段取自 FF `508aba30` `scripts/transcript_tool_transport.py::_source_request`（191-219）：`provider/provider_document_id/language/form_type` 为 `null`、`mode="exact"`、`allow_download=true`。
- `candidate` 逐字段取自同文件 `_candidate`（825-864），含 `adapter_payload_json` 的 `sort_keys` 紧凑拼写 `{"exchange":"nasdaq","market":"US","security_id":"MSFT"}`。
- `transcript_result` 取自 ET producer golden `tests/fixtures/transcript_fmp/fmp_v2.fetched.json`（ET `4924d57`），仅 `request_id` 替换为 CWP 对同一 `source_request` 的实际哈希 `urn:company-wiki:source-request:sha256:7bb1c2ea677e9b94bb348a17854f0b1e690bec4597961fc0d112d39a9b143a8f`。该 id 是 FF 从 CWP lookup 取回再转交 ET、ET 原样回显的值，属真实 wire 的一部分。
- 该值由 `test_literal_ff_fixture_tracks_the_producer_golden` 守护：除 `request_id` 外必须与 ET golden 完全一致，golden 更新时测试失败，迫使刻意刷新而非静默漂移。
- 同一字面 `request_id` 也是 identity 投影的哨兵：一旦 `SourceRequest.identity_dict()` 被改动（新增/改名 identity 字段），该值不再匹配，导入会以 `result request_id does not match request` 失败。这是**有意的**公开身份变更，必须与 `REQUEST_SCHEMA` 一起决策，不能靠顺手刷新 fixture 绕过。

`tests/fixtures/transcript_import/generic_html_import_request_v2.json`
- 非 FMP（HTML）分支的同一 envelope，冻结原先由 `datetime.now()` 与 owner 模型在运行时生成的日期/hash，使本文件不再有任何运行时推导的期望。

两个 fixture 都是缩进排版的静态 JSON，字段名与值是冻结对象；JSON 空白不属于 wire。测试只读不写，已用 CRLF 版本复跑验证与宿主换行无关。

## 逐项闭合

1. **先 RED**：在父提交 `503f6510` 的原 decoder 上跑 `test_internal_defaulted_field_does_not_change_the_wire` → `1 failed`（`TranscriptImportCliError: source_request fields differ from schema`）。修复后该文件 20 例全绿。
2. **真实进口路径**：字面 fixture 字节直接喂真实 CLI → `run_import` → 真实 scratch catalog → `CanonicalSourceWriter.import_staged` → 写后 `SourceVersionReader.query_ref` + `open_version` + `extract_transcript_material.verify`，并核对 sidecar `transcript_acquisition` 审计字段；第二次导入为 `deduplicated_after_download` 且 `source_ref` 不变。
3. **内部默认字段演进**：`_EvolvedSourceRequest` / `_EvolvedDownloadCandidate` 各加一个带默认值字段（并断言字段数确实 +1，防止测试空转），monkeypatch 到 decoder 后同一 fixture 仍 `imported`，落盘原始字节一致；测试还用构造记录断言 decoder 真的构造了这两个派生类型（若将来把 import 挪进函数体使 monkeypatch 失效，测试会立刻失败而不是空转）。把同名字段写进 wire 仍被 `fields differ from schema` 拒绝。
4. **保留的硬检查**：重复 JSON key、`NaN` 常量、非 UTF-8、超 `--max-envelope-bytes` 全部按原样拒绝；`--max-original-bytes 256` 对 862B 原件仍拒绝且不落盘。

## 未放松的 owner 校验（实测逐项拒绝）

ticker、fiscal_period、as_of_date、provider、provider_document_id、source_url、provider_payload_sha256、canonical_content_sha256、candidate.provider_document_id、source_request.security_id、source_request.fiscal_period 各一例；每例断言 `status:"rejected"`、无原件、无 staging 残留。响应体与 lookup 响应递归扫描确认不含物理路径。

## 确切测试命令与结果

工作树内（venv 在母仓，用 `PYTHONPATH` 指向本 worktree 的 `src`）：

```
cd "C:/Users/郑曾波/Projects/company-wiki-d4-04-wire"
PYTHONPATH="C:/Users/郑曾波/Projects/company-wiki-d4-04-wire/src" \
  "C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe" \
  -m pytest tests/contract/test_transcript_import_cli_e2e.py \
           tests/contract/test_decoupled_import_budget.py \
           tests/contract/test_transcript_architecture.py \
           tests/contract/test_transcript_original_import.py \
           tests/contract/test_transcript_fmp_admission.py \
           tests/contract/test_transcript_json_material.py \
           tests/e2e/test_transcript_provider_full_chain.py \
           -p no:cacheprovider -q
```

结果：**68 passed in 69.12s**（其中本卡文件 20 passed）。RED 复现：

```
git checkout 503f6510 -- src/company_wiki/source_catalog/transcript_import_cli.py
# 同上命令 + -k internal_defaulted_field  →  1 failed, 19 deselected
git checkout HEAD -- src/company_wiki/source_catalog/transcript_import_cli.py
```

静态检查：`ruff check` 通过；`python -m mypy src` → `Success: no issues found in 422 source files`；pre-commit 范围内 hook（ruff + mypy）Passed。未跑全仓测试，只跑新增与受影响域。

## 临时目录与恢复

- 所有测试用 `tmp_path`；本文件内的 scratch 根由 `_remove_fixture` 显式删除并断言 `not root.exists()`，staging 目录断言为空。
- 未写生产 `companies/`、`config/`、原件或数据库；未调用 provider/模型/网络。
- 施工期探针脚本与手工临时根已删除（`_probe_*.py`、`_gen_generic_fixture.py`、`d404-*` 目录）。
- 交付前删除本地 pre-commit 缓存 `.pc-home/`（未提交）。为跑通仓库自带 pre-commit 钩子，在母仓 `.venv` 安装了开发工具 `pre-commit==4.7.0`（钩子本身要求 `python -m pre_commit`，此前缺失导致提交被阻断）；产品依赖未变。

## 独立审查

未参与实现的审查 agent（只读）结论 **PASS**，检查了 FF 字面 fixture 独立性、内部默认字段演进是否真 RED、写入后 verified read、owner 校验是否放松、envelope 硬化、写域与测试自证性；其 4 条意见全部处理：

1. 测试里 `SourceRequest(**wire)` 直接展开 wire 名 → 改为按 `_SOURCE_REQUEST_WIRE` 映射构造。
2. fixture 与 ET golden 无漂移守卫 → 新增 `test_literal_ff_fixture_tracks_the_producer_golden`。
3. import 主响应未做路径泄漏断言 → 新增 `_assert_no_local_path`，并对 lookup 响应同做（原 `str(root) not in stdout` 因 JSON 转义实际无效，已替换）。
4. 缺 handoff/commit → 本文与 `5daf7e1e7`。

## 需 ROOT 做的 FF→ET→CWP 组合

本卡只证 CWP 侧收口，不证跨仓组合。ROOT 在 D4 汇总节点应：

1. 取 FF `508aba30` 未改的 `EarningsTranscriptsTransport`，用独立端点/临时 CWP 根（`--wiki-root` 指向新建临时目录，含最小 `config/source_catalog.yaml` 与 `companies/`），不指向生产根。
2. 走两条 FF 分支各一次：默认 `provider=None` 的跨源复用（`_query_local`）与显式 `--provider fmp`（lookup envelope）；两者对同一 `source_request` 产生同一 `request_id`，可用于核对本 fixture 的 id。
3. 断言：`company-wiki-transcript-import-response/3`、`canonical_status`、`request_id` 与 lookup 返回一致、`source_ref.byte_size/content_sha256` 等于实际原件、身份/期次/as-of 由 CWP 复核、写后 verified open 字节一致、staging 清空、临时根可整目录删除。
4. 组合失败若指向 wire 形状差异，先核对 FF `_source_request`/`_candidate` 是否在 `508aba30` 之后改动；本卡未改 wire，不应需要 FF 同步改造。

## 边界与未做

- 未给 `tests/fixtures/transcript_import/*.json` 加 `.gitattributes` 的 `text eol=lf`（该文件不在本卡写域）。仓库 `core.autocrlf=true`，Windows 检出会转 CRLF；测试已按 CRLF 复跑通过，若 ROOT 要求 blob 级字节稳定，可在 ROOT 层加一条属性。
- 非 FMP 的 HTML 分支仍由本文件覆盖（`generic_html_import_request_v2.json`），但 FF 生产当前只发 FMP 形状；该 fixture 不代表新的 producer 合同。
- 未改 `transcript_tool_contract.py` 的 `_RESULT_FIELDS`（它本就是字面集合，且不在本卡写域）。
- 本次为隔离合成 fixture，不替代后续真实摘要/缓存/RF 采用；D4 关闭后按 ROOT 顺序回 T4/SEM。
