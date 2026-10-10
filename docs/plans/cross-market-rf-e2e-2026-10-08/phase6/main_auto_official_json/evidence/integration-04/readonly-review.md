# MAIN 官方 JSON 接线独立只读审查

日期：2026-10-10。审查者：main_json_source_adapter_design。工作树：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`。

## 范围和结论

独立审查 ROOT 的 batch request/items、generation、freeze/thaw/resume、reuse、public transport/evidence view 以及 publication/terminal 接线。本人此前实现的 adapter/select/verify/runtime/factory 不作为本次独立验收对象，只作真实上游依赖。源码与生产配置只读；零外部 provider/LLM、零费用；探针及测试全部独占 TEMP，结束恢复。P7 叶模块验收另记。

**当前结论：身份、父页、公开视图和 publication/terminal 的责任测试通过；全公共 mixed CLI 尚未验收通过。** 首轮 24 项中 22 PASS、2 FAIL，后续 53 项全部 PASS。不能用责任层局部绿宣称 AUTO 全链完成。ROOT 已接收以下三个共因，修复完成后必须重跑对应大节点，而非增加逐小步骤签收。

## 已确认问题及最小反例

### R1：raw generation 遗漏 reasoning_effort（配置/复用共因）

用真实 `NarrativeBatchRequest.from_dict` 构造同一原文、同模型/endpoint/profile 两份请求，仅 reasoning_effort 从 low 改为 max；分别调用真实 `_item_generation`。

- request SHA 不同。
- raw `narrative-generation/1` SHA **相同**，effective model keys 为 model_id、endpoint、max_output_tokens、output_token_field。
- 相同两请求的 projected `narrative-generation/2` SHA 不同。

所以跨 run raw exact-generation lookup 能错误复用另一 reasoning_effort 配置的结果。建议新 raw 请求显式包含此字段时将其绑定为因果输入；历史无此字段的封存 manifest 保持原字节和原解释，不能恢复时重签。ROOT 已确认修复；本报告暂不将其记为修复后 PASS。

### R2：projection generation 拒绝模型层已支持的 adaptive

真实公共请求 model.thinking='adaptive' 经 `NarrativeBatchRequest.from_dict` / `NarrativeHTTPModel` 配置验证成功，随后 `_item_generation(request, official_payload)` 抛 `projection generation thinking is unsupported`。

这是同一配置字段在不同责任层支持集合不一致；应跟真实模型配置契约一致，不能改模型配置或默认值绕过。ROOT 已确认修复，待集中验收。

### R3：单一 run prompt 被错误当成每个 mixed item 的 prompt

实际公共 CLI 首轮 mixed 三项运行：raw 完成并记账 92 tokens/111 micro-USD；两个 projection 在 HTTP 前因 `MODEL_BUDGET_DENIED` 终止。单个 projection 请求也 0 收费失败。底层 `reserve_model_attempt` 把 item 的 official-json/1.0.0 与 run 的旧 raw 1.7.0 硬比较；调用层又将 RunConflictError 误报为预算不足。

ROOT/store agent 同时独立确认共因，ROOT 正在按冻结的 item generation prompt 修复。保留旧 raw run 治理版本、每项实际 prompt 从 binding4 generation 取得；不能放松成任意 prompt 可进入，也不能按 subject 前缀猜版本。还须保留 unknown reservation 的保守收费和幂等恢复。

## 已验证的不变量

独立真实 source import/2 + persist + catalog 探针：

- 两个不同 issuer 的 projection 共享**两个相同真实 parent**，再加一个旧 TXT raw，共 3 个 distinct item_key、3 个独立 event。
- 新 binding4 freeze/thaw 完整还原每项 manifest；raw read-policy map 只有真实 raw item，不为 projection 伪造 policy。
- 真实 source_metadata.title 或 document_kind 单独变化，均改变 projected generation SHA。
- 原 TXT bytes 与 catalog config bytes 不变；TEMP 移除；零外部调用。

源码责任核对：

- `_item_generation` 的 raw 路径剔除 projection_prompt/projection_model_request_schema/official_json_adapter，防止官方适配器变化无谓重算旧 raw。
- 官方 source preparation/dispatcher/read/compaction 均通过 source view/loader；artifact layer 只核 parent 关系，source port 核当前真实字节及语义；没有把 anchor document 当成完整 projection。
- exact subject/generation 发现与 public ref/read 按完整 subject、generation 和实际 object SHA/byte_size，raw latest 查询排除 projection。
- resume 的 binding4 保存 request SHA、版本、generation 设置/每项 source_inputs、job membership 与 reuse pin；恢复用旧 manifest 验真，不重新签 persisted events/jobs。
- generation recovery pointer 对非 known reservation 保留恢复要求，不把未知费用退款或静默开始同 generation 的新收费。
- final publication 使用完整 projection subject + generation target；终态压缩前读取和哈希真实 visible artifact，复核源 view 后保留紧凑 receipt。

这些源码观察不代替修复后真实 whole-batch E2E。

## 实际运行记录

1. `readonly-main-integration-tests.log`：真实 preparation + mixed subprocess/HTTP loopback + publication/terminal，**22 PASS / 2 FAIL**，pytest 50.13 秒。15 项 publication/terminal 全绿，覆盖 ACK 后崩溃/reconcile、第二母页损坏、不同 issuer 同母页独立发布/压缩、generation/原文字段伪造拒绝。2 FAIL 均为 R3。
2. `readonly-main-contracts-views.log`：ROOT batch identity/subject contracts/evidence view + transport，**53 PASS**，pytest 17.09 秒。包含上下文/旧 raw wire、3.0 身份、每个真实父页检索、错误 issuer/as-of/generation、artifact 损坏不能当缓存 miss、重签文本/metadata 不能伪造回放。
3. `readonly-source-snapshot.json`：报告时实际源码 SHA。ROOT 正在并行修复，因此是带时间的观察快照，不冒充一个封存 commit。

测试环境：Python 3.13.9；禁第三方 autoload，显式 pytest_timeout、禁 cacheprovider、独占 basetemp。Windows 路径插件实际 relocation/cleanup 均 removed=true；外层 TemporaryDirectory 移除。唯一 pytest warning 是禁插件后现有配置项提示，不是断言失败。

## 余项（大节点，不增许可）

- ROOT 修复 R1/R2/R3 后，重跑 public mixed 初次/同 run 恢复/跨 run reuse/部分 reuse/refresh，以及已冻结 request/实际 prompt/model body 变更的正负控。
- 补/运行 projected model attempt unknown 使用量及恢复测试，确认同 attempt 不重复 HTTP、费用保留、真预算耗尽与配置/身份冲突各自报真实原因。
- 全链绿后再看最终 retained-byte/terminal receipts、旧 raw 七参 pin wire、原件/config 一致和 TEMP 恢复；本轮 source-only/P7 通过不代表这一步完成。
- 没有把施工期间缺参数/未落地接口当最终产品漏洞；没有创建人工签收/新审批链。


## 追加：ROOT 修复后的独立责任验收

R1、R2 已通过实际重验，**可关闭配置根因项**。运行 generation + caller + run-store + preparation 集中责任组：**101 PASS / 12.00秒**，日志 readonly-generation-caller-fix.log。caller 真预算耗尽、run binding、scope、lease、busy SQLite 各自保留静态诊断，0 HTTP 前拒绝；unknown 使用量继续按保守界记账，不退款。

真实 public request→TEMP source catalog→AUTO scheduler/materialized jobs→create run→freeze/resume 探针（readonly-generation-fix-probes.json）：

- raw low/max generation SHA 现不同，None/省略保持相同历史无字段身份。
- public adaptive 请求及实际 projected generation 同时接受。
- mixed 两个真实 model job 分别冻结1.7.0和official-json/1.0.0；run ledger不导入source模型语义，由coordinator提供不可变job→prompt映射，create_run精确覆盖scoped summarize jobs。
- resume保持原manifest和event字节，thaw一致；改一个job prompt被BATCH_FROZEN_BINDING_INVALID拒绝，不默认/猜别的prompt。
- 全部临时目录移除，0外部调用。

历史兼容补充观察：构造忠实旧 generation1（explicit-low请求但封存manifest中无effort），一致重算wrapper所有settings/generation hash后，真实mixed resume仍报BATCH_FROZEN_BINDING_INVALID。不能据此说生产库已经有此类run；这是可复现的兼容边界。ROOT已收到，若承诺这种旧历史可读取，应只在封存缺字段时保持旧比较语义，新run继续新键，不能重签。

R3 per-job prompt admission的责任组已通过；ROOT/store agent报告实际mixed已发3次loopback POST并准确计量。当前whole-batch终态compaction仍在修同一旧run-prompt假设；本报告保留最终公共CLI/恢复/终态大节点待验，不将101局部绿当AUTO全部完成。后续由ROOT一次集中最终验收，不增加小节点许可。
