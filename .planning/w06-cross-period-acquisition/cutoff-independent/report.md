# W06 cutoff 非作者验收

## 当前结论

**FAIL_USAGE_PROJECTION_P1**：ET 来源日期原因、FF 合法 cutoff 映射和 receipt 绑定已通过；仍有一个共因使错误 stdout 丢失已经验证过的独立实际用量。小独立节点：**39 PASS / 3 FAIL，1.27 秒**，无 skip。不能把作者的 4 个缺显式路径可选 SKIP 计入通过，也不能把本次剩余失败更改成预期缺省或删掉探针。

验收对象为 ET `et-cutoff-root` 和 FF `ff-contract-matrix-root`，冻结 SHA `e13ee23e64e0ec720edce6e4f5c6847f0dea2ead17a8d112d63874cd0e4cf28a`。8 个产品文件、30 份旧 golden、205 个既有 CaseSpec/工具及交付文件均与其冻结一致，测试前后未变。没有修改产品、Git、安装、配置、密钥、原件、旧证据或共享 PWF。

## 阻断项：实测用量不应依赖正文 JSON 有效

**P1，统一错误投影缺陷**。`scripts/transcript_tool_transport.py::_et_result` 在读取 child 后已经独立验证 `usage_stderr` 并保存在 `_last_provider_usage`。随后 JSON 解码失败及 decoded result 非 dict 两个分支，返回 `_provider_usage(b"", request_id)`，把已有真实计数重置成 unknown。

独立反例为三种 stdout：`{broken-json`、`[]`、`null`；每种 stderr 均是当前 request ID 绑定、schema 合法、`usage_complete=true`、`requests_used=1`、`response_bytes_used=987` 的回执。真实结果：`provider_unavailable/provider_result_invalid` 正确，但 `provider_requests=null`、`provider_response_bytes=null`、`provider_usage_complete=false`。原始响应和实际投影在 `trace.jsonl` 的 `ff_malformed_wire` 行；失败断言在 `probes.py::test_ff_malformed_stdout_does_not_erase_valid_usage`。

根因是把两个独立信道错误地绑定：**结果载荷损坏不能抹掉已经验真的用量信道**。stdout 无效时继续拒绝导入，有限错误码和关闭重试规则保持；仅通过同层共用错误投影保留 `_last_provider_usage`（包括确实 unknown 的情况）。不新增身份库、人工许可、合同签收或再次校验原文。作者修复后只需重验当前集中小节点；ROOT 原 41 矩阵继续属于另一个整链验收责任。

## 已通过的具体范围

- FMP `/1` 与 `/2`：真正唯一目标期晚一天产生 `call_after_as_of`；空数组没有 cutoff；其他公司/年度/季度或非规范日期维持 provenance 拒绝；边界当天 fetched，但 `publication_date=null/as_of_cutoff_verified=false`；两个合法候选保留 ambiguous。每条只有一次 fake HTTP，没有额外请求。
- Motley fetch/discover：真正目标期发表日晚一天产生 `publication_after_as_of`；空列表、别期未来记录、别公司未来记录不冒 cutoff；边界当天合法；discovery 不取正文，cutoff 不取正文。全部使用不同于作者的 BETA、2024-Q2、2025-03-20 向量。
- FF `/1` 旧 missing 与 `/2` 新 cutoff：有限 reason 投影正确；任意正文诊断或数组不会洗成 cutoff；缺 usage 保持 unknown，不伪造零。
- FF 的 schema/request ID/period/candidate count/child exit receipt 绑定：反例关闭且保留合格的实际用量，没有假 cutoff。
- 公开 `resolve_companion_transcript` → transport → `_transcript_result`：两个 cutoff reason 在最终结果保留，ET 一次、CWP query 一次、import/open 零次、SourceRef 不被伪造；请求 1 次及 987 响应字节保留。
- API 文件系统探针没有正文落盘；没有 translator/LLM 调用。真实 supervisor/worker 通道由作者既有 E2E 和 ROOT 原 41 CLI 回放覆盖，本次没有声称重复执行它们。

## 冻结和 CWP 既有版本差异

独立启动前，原 CWP 来源修复冻结 `1a753dd...` 所指树有一个**既存差异**：`operation_contract.py` 实际 SHA `580e89da8d3afc9dbacb34c6e6f0837c7e118ca5d0f57b14f946255d3b4491dd`，8697 bytes；原冻结 `954c6cb5f0955c0246aecb12f62388f27f494dd3681305a1c967dd03bc17dbde`，8681 bytes。其余 11 个文件匹配原冻结。已向 ROOT 报告，不能声称全部 12 与旧冻结一致；本次 12 个实际观察值前后完全一致，亦未调用 CWP 产品原文流程。ET/FF 本次 8 文件均匹配其正式新冻结。

这个启动前版本差异与三个已重现 FF 用量失败分开记录，不以其掩盖、归因或放宽用量断言。ROOT 负责确认并绑定最新 CWP 正式版本。

## 可复现性、恢复与 STOP

`run_review.py` 先核对冻结，再用 Windows 必要环境 allowlist 启动独立 pytest，HOME/USERPROFILE/TEMP 都指向唯一新建的 `company-wiki/.tmp/cut-review-<uuid>`。真实 credential 环境未继承，未读取或哈希实际 FMP/LLM key；socket connect、解析和 create_connection 均拒绝，供应商只用内存 fixture。

`probe-result.json` 留完整命令、全部前后 SHA、环境字段及 `scratch_restored=true/freeze_unchanged=true`。已删除仅本次自有 scratch，保留原先存在的 `.tmp` 父目录和其他任务文件。正式证据仅此独立目录。未重复作者 56/134/195 套件或完整 41 矩阵。

原失败证据冻结后 **STOP**。ROOT 可让作者按共同根因修复并另行重新冻结；之后 reviewer 只针对新的明确版本复验必要小节点。
