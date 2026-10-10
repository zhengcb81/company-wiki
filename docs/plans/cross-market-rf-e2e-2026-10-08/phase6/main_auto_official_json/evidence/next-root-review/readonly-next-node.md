# 下一 MAIN 根因节点：只读核对报告

调查日期：2026-10-11。调查树：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`。依据根 `task_plan.md / findings.md / progress.md`、W03/W04/W05 原卡、既有真实失败调查及当前源码。ROOT 正常发布正在进行，本报告不宣称候选已有新的远端 CI。

## 结论与下一步

**下一最优 MAIN 实施节点是 W04：把 length 失败的有界最终正文诊断从 HTTP 解析贯通到失败 attempt、公开批次及只读恢复。它尚未接通，不能被 reasoning meter 或 AUTO/P7 工程绿替代。** 此后先修 W03 的重要业务组漏选，再完成 W04 的期间/范围摘要责任；W05 工程由正在施工的 P7-AUDIT 交付后接收。最后集中做原失败资料的真实收费复验和独立四审，避免对已知漏选输入先重复付费。

已完成的 AUTO 混合身份、generation/显式 effort、预算异常分类、终态收缩和历史恢复，不在本报告重新列作待修根因。责任测试有重叠，不相加，也不重复此前最终 9 场景。P7-RF/P7-AUDIT 排他源码未读写；只读取 P7-AUDIT 施工卡判断任务边界。

## 1. W04：最终正文只剩字节数，缺口贯穿整条失败链

| 当前实际位置 | 实际行为 | 尚缺什么 |
|---|---|---|
| `automation/narrative_http_model.py:62`、`:381`、`:437` | `ModelOutputTruncatedError` 保留 finish reason、content bytes、usage 等，明确不保留响应正文 | 有界 provider 原响应 SHA、最终 content SHA、UTF-8 前缀和 clipped |
| `automation/narrative_model_caller.py:233` | length 失败仍按实际 usage settle；`response_sha256=None / no_output=True` | typed 诊断透传与持久化；失败不能伪成功 |
| `automation/narrative_summarize.py:92` | `_failure` 返回 `result={}`；detail 只拼接截断原因/字节数 | 小型结构化失败诊断，而非把文本塞入错误字符串 |
| `automation/narrative_batch.py:1852` | attempt 公开诊断只投影 reasoning/usage metrics | failed final 的公开读取、重开/恢复兼容 |

这是当前代码缺口，非仅卡片状态过时。W04 原卡明确“final16KiB正文未实现”；`model_output_runtime_root/IMPLEMENTATION_CONTRACT.md` 与 `INVESTIGATION.md` 同样把已绿的配置、usage 和尚未完成的最终正文/真实复验分开。旧真实 DeepSeek Flash 样本有 final 951 字节、0 字节等，不能凭旧未保存的正文补造诊断。

### 已执行的最小内存反例（0 HTTP、0 provider、0 文件写入）

直接调用当前 `NarrativeHTTPModel._response`，三个合法 synthetic 响应都为 `finish_reason=length`，实际 prompt 73、completion 8194、reasoning 7000；正文分别为 951 字节、空正文、18,000 字节多字节文本。三者均抛真实 `ModelOutputTruncatedError`，其 retained keys 只有：

`content_bytes, duration_ms, finish_reason, input_tokens, model_id, output_tokens, reasoning_tokens, usage_diagnostic`。

三者均不存在 provider response SHA、final content SHA、final prefix；8194 与 reasoning 7000 则如实保留。18,000 字节样本证明“仅计数字节”不能验收 16KiB UTF-8 留存。951 字节样本最终 content SHA 为 `95c0d8678c535fa7192f4c9e598cff59264010d2e8de8709e055adc5fa164006`；空正文 SHA 为标准空字符串 SHA。未保存 synthetic 隐藏 reasoning 正文。

### 建议最小 TDD / 一次集中 E2E

1. **HTTP decoder RED**：951 / 0 / 18,000 字节三样本。provider envelope SHA 与 decoded final SHA 分开；前缀最多 16,384 UTF-8 字节且可完整解码，真实全长和 clipped 保真；隐藏 reasoning 只计 token 不留正文。未返回 reasoning 保持 unknown，0 保持 0；completion 8194 不截成配置 8192，不把 reasoning 子集再加一次费用。
2. **失败链 RED**：真实 decoder → budget caller → summary handler → 既有 attempt.result_json → store 重开 → public batch。沿现有小型诊断容器透传，不加第二库、逐材料许可或正文备份。旧无诊断记录仍可读且旧可选字段缺省 wire 保持；failed attempt 仍 no_output，不产生正式摘要。
3. **有界负控**：最终序列化诊断最多 32KiB（中文 JSON 转义也计实际字节），纳入既有空间上限。诊断写入/清理失败保留主错误与已发生的 usage，不改报为新的摘要错误；保留真实 hash/全长，空间不足时可明确省略 prefix，不能盲重试或丢主异常。
4. **一个真实公共 CLI 离线 E2E**：owned TEMP、真实子进程、loopback length 响应带 951 字节正文及 8194 completion；只有一次实际 reservation/settle，typed 截断失败、有界诊断可公开读取，零正式产物；同 run 两次 resume 零新增 POST/费用。沿用 `tests/integration/test_narrative_batch_cli_e2e.py:664` 的真实 meter/重开责任与既有 fixture，另补最终正文断言，不重新铺每小节点全套门。

配置已发表的 policy/meter 责任无需重做。实施时核对**不含密钥**的实际 resolved provider/model/purpose/options；生产没有显式 DS narrative disabled 的旧卡状态不能被推测为已生效，也不能临时猜新模型、提高输出上限掩盖截断。供应商行为仍须后续真实复验。

## 2. W03：当前真实业务召回反例仍成立

对仓内真实 `tests/fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt` 执行原语言材料提取、原字节 verify、默认真实 `parse_transcript_text` 和真实 `select_narrative_evidence`，全部内存完成；原字节前后 SHA 不变。

- 原件 66,324 字节，SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`。
- 当前 parser **0.3.1**、489 native units、51 selected spans，status=selected，coverage_complete=true。
- native QA group 5 有 2,956 字符，角色 analyst/management/operator，包含安全业务；**selected 0**。
- native QA group 6 有 2,773 字符，包含 ROI 与管理层回答；**selected 0**。

因此 actor/body/end 的 57 项责任绿不能关闭 R04。`coverage_complete` 表示载体解析覆盖，不表示所有关键业务主题召回；本报告不要求每份文档所有 Q&A 无条件入选，也不把该 flag 本身列作错误。

W03 下一最小 RED 应固定 QA5/QA6 的业务命题与限制条件及各自角色/group/locator，再加另一 issuer/布局的正负控，避免 MSFT 特判。保留 question/answer 离散证据，不能合成一段连续引文。原 W03 中 CN CVD/HAR/ALD 与 LPCVD 安装数量的主体区分、HK 首页业务与后段融资套话区分，以及 HK 半年报可读正文与不透明封面/表格的诚实 partial，仍是对应责任样本。

新 MAIN generation 与同代复用/失效工程已通过；不能再把整个 R26 一概称未实现。仍待的是这些真实资料业务召回、独立质量审查和收费执行的最终证明。

W04 R05 的摘要语义应消费 W03 已有 group/有限证据。最小期间/范围反例仍是 HK goodwill 与其他减值 277m/合计 2122m、US 三个月 39/31 与半年 40/30、CN “今年”与原文目标年/vintage。引用 ID 合法不等于命题 supported；自动检查能约束声明的 period/scope/group，不能证明所有自然语言含义正确。

## 3. W05：不另开重叠施工

`phase6/p7_parallel_handoff_2026-10-10/p7_audit_execution_review.md` 已覆盖 W05 工程主干：scope→实际 child request/SHA/profile/caps/config-env、request/call/document result join、partial SourceRef、一次真实调用多个文档结果、quote/composite/OCR/actor/date/numeric provenance、四路 coverage 与 delivery trust 链。

它仍由外部 harness 施工，ROOT 最新 PWF 未收到 P7-RF/P7-AUDIT 完成通知。MAIN 应等待接收并在共同接口层接入 W04 诊断，而非改其排他脚本、计划或安装副本。P7-RF 的 optional operating calibration 诊断同样待实际交付，不能拿工程合同绿签收预测质量。

W05 原真实失败的终验仍要检查：实际 scope P1，32/64MiB 与 final 2MiB 请求被 child 真正消费；configured env 保持但无密钥日志；stdout≠逐文档成功，partial 与真实工具/原件复用完整记录。P7 工程绿不代替一次新的真实四审报告。

## 集中关闭节点建议

顺序：**W04 有界失败链 → W03 关键组/可读正文选择 → W04 期间与支持范围 + P7-AUDIT 接线验收 → 一次原失败资料收费复验与四审 → 换新公司泛化/原后续 loop**。

只有大节点集中验收。后续真实费用和 token 继续累计 USD20 / 2M，包含旧 unknown，不能归零。保留旧 failed 原件与证据，不追加恢复备份演练。真实研究关闭依据必须包括完整 source summary/bundle/read→RF 消费、准确实际配置/finish reason/meter/diagnostic、四个独立责任审查；synthetic 工程 green 不足以宣布原三家、新三家或条件八家公司完成。

## 调查冻结与边界

当前读取源码 SHA-256：

- `narrative_http_model.py`：`d108b491685d0df24eff3e6536d607a2f47109a9bc93f23f868c86e3771e2955`
- `narrative_model_caller.py`：`844e10de77884a14efc89c2449bd5099fe3ab745f7931a485c340c899cb10c30`
- `narrative_summarize.py`：`4127b3093252ca633f1f9bb827e65260bff7f407c07b431555483344a034caa9`
- `narrative_batch.py`：`7e17b29becfee0dbd22a753a0123e58ad7206130dfc5e2ba01009b26cae08dfd`

结构查询先使用 canonical CodeGraph；已明确文件与实际 MAIN 新源码再精确读取。未查/输出密钥，未读生产配置内容，未访问网络或收费模型。此调查只新写本报告；源码、共享 PWF、原件、DB、安装和其他证据不变。初次 probe 的 mixed int/string QA 排序错误已在 probe 中用 `key=str` 修正，属于报告代码错误，不列成产品缺陷。
