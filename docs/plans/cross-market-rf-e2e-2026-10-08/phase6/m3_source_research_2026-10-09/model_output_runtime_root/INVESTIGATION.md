# M3真实叙述输出与选择覆盖共因：调查阶段

## 已实测，不能被旧工程绿覆盖

CN H1/IPO、HK Q2 PPT、US official call实际DeepSeek Flash均finish_reason=length/MODEL_OUTPUT_TRUNCATED；调用按现配置8192，已知usage结算，unknown/unsettled=0，不盲收费重试。CN content_bytes=951/0，US=2017；reasoning_tokens未保存，不能反填精确推理量，也不能宣称完整失败body存档。

原证据：CN execution/narrative/model_diagnostics.json；US execution/narrative-native-diagnostics.json、execution/model_options_observed.json；三各自新run m3-20261009T184946-*。具体job/attempt/request SHA留原账。HK实测H1和US release/metrics有PARSER_INCOMPLETE；这是选择/可回放证据边界，不能直接解释为没有有用信息。

## 根因证据与待证推断

当前NarrativeHTTPModel的model_options_from_config保留DeepSeekFlash/8192/temp1，却无thinking或reasoning_effort配置投影；已有Config/LLMClient也没有DeepSeek的该控制字段。当前供应商[Thinking Mode官方说明](https://api-docs.deepseek.com/guides/thinking_mode/)和[Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)确认未指定时默认开启thinking/high，生成cap与最终content竞争；温度在thinking中无效。三份实际8K耗尽/短内容与此一致，但缺reasoning计量，尚不能断言所有截断完全由这一个原因造成。

旧输出plan的target_claim_count是提示启发式，不是可证明的token上界；没有显式provider推理策略和实际reasoning计量，synthetic只产短JSON的测试覆盖不了这类真实耗尽。禁止立即猜新模型/把8192升大/一刀缩去业务证据/截断JSON后发布partial为成功。

## 下一调查与施工接口

1. 保持原失败、原配置和全部费用；收集三家公司规划/实际响应安全metrics，只保留token计量/finish_reason/byte counts，不记录隐含思维链或credential。
2. 从已有单一Config/LLMClient/HTTP port统一支持显式thinking/reasoning控制（先TDD、配置投影优先），每provider按真实官方语义且默认omitted兼容；用途策略必须写配置，不能模型调用临时拍脑袋，也不能新增第二配置库。确定有证据方案后再实施，不提前在此登记完成或改生产config。
3. 现有预算/reservation/gen input SHA包含实际wire option；新增配置改变需生成不同pin、实际旧artifact不改。对thinking-only cap耗尽、mixed answer、no-thinking shortJSON与unknownusage固化离线责任测试；长期只留安全meter，不落完整provider reasoning。
4. 调原文与解析产物核实PARSER_INCOMPLETE是否适当financial-only过滤、真实业务表/异常PDF定位未覆盖、或OCR/HTML兼容缺陷；US原文7位analyst与selected仅两qa_group之间先比全解析/选择，不把selected-excerpts coverage误说成全篇问答覆盖。
5. M3四独立reviewers与专家汇总后，确定共用修复卡，按大节点真实原四个失败材料复跑并加未见样本，原预算扣旧费用和未知；不增加每小节点审批。

## 分开的执行偏差

HK首次wrapper未继承scope.process_environment使ET工具未配置；继承后真实ETunsupported_market/0request，与产品不配置不同。HK不同finite输入复用work baseline被拒绝，独占work后真H1select失败，不是有模型费用的重试。US首批P2而scope P1、100MB声明caps而scope32MiB/64MiB，实际仍未超占，但声明与profile偏离须记执行缺陷；不能拿实际少用空间核销，不能为了重跑cache假称符合P1。这些问题独立于供应商截断，先在handoff/skill caller明确目前已有合同，不加人签/身份许可。
