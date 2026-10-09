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
4. 调原文与解析产物核实PARSER_INCOMPLETE是否适当financial-only过滤、真实业务表/异常PDF定位未覆盖、或OCR/HTML兼容缺陷；US executor初报7位analyst，逐原文核实实际6位；原0.2 selected仅两qa_group，须比全解析/选择，不把selected-excerpts coverage误说成全篇问答覆盖。
5. M3四独立reviewers与专家汇总后，确定共用修复卡，按大节点真实原四个失败材料复跑并加未见样本，原预算扣旧费用和未知；不增加每小节点审批。

## 分开的执行偏差

HK首次wrapper未继承scope.process_environment使ET工具未配置；继承后真实ETunsupported_market/0request，与产品不配置不同。HK不同finite输入复用work baseline被拒绝，独占work后真H1select失败，不是有模型费用的重试。US首批P2而scope P1、100MB声明caps而scope32MiB/64MiB，实际仍未超占，但声明与profile偏离须记执行缺陷；不能拿实际少用空间核销，不能为了重跑cache假称符合P1。这些问题独立于供应商截断，先在handoff/skill caller明确目前已有合同，不加人签/身份许可。

## 配置和计量施工细则（先冻结方案，待四审归因后实施）

真实producer查验：Config.llm_for_provider对非主/备用模型仅复用max_tokens/max_document_chars/temperature/reasoning_split，DeepSeek选用已配置loader默认；现有主profile及MiMo fallback没有deepseek thinking字段。NarrativeHTTPModel有thinking参数，但只接受disabled/adaptive且loader不投影；SDK/urllib两个LLMClient wire入口同样无DeepSeek策略。不能只在一个summary wrapper硬塞disabled，另外入口继续provider默认，亦不能把适用于MiMo的adaptive误送DeepSeek。

1. 仍在唯一config.yaml/Config内配置，方案必须明确provider与叙述用途，未配置保持omitted。只增加必要thinking/reasoning选项，不另造第二profiles文件/dispatcher库，不将某provider设置继承给另一个provider；真实primary/fallback/显式DeepSeek选择都验证。按供应商当前值域投影，不改变model/endpoint/key/8192/累计预算。最终purpose值由共因施工节点一次设定并记录依据，不在执行agent按文档临时猜。当前冻结M3仍按旧config走，生产config尚未改。
2. 先用tmp配置TDD：primary/fallback/显式provider选择精确值；遗漏不发送；合法值和混provider不串；非法type/value在config层具名拒绝；NarrativeHTTPModel、SDK、urllib发送相同已配置策略。标准usage/错误usage/缺失usage分开，旧unknown记录不修改。
3. 当前reservation request SHA已含实际wire body SHA，因此新thinking/effort必须改变reservation/gen输入pin，旧缓存不得冒充新策略结果。先测试同source同strategy新AUTO零HTTP/零reservation，策略改变只重算对应summary、source原件/parse不重复下载，旧artifact/version保留。
4. 采集usage.completion_tokens_details.reasoning_tokens作为可选安全整数，0与unknown/null分开，不能超过completion总量或吞掉错类型；不存在细项时总input/output仍可结算，reasoning未知不能反算成0。通过现有ModelResponse/错误diagnostic/attempt输出写有限meter，不新增账本或完整思维链存储。若需要可回查截断失败，仅保留有界final content与其SHA，永不以partial JSON发布成功摘要；raw envelope可只存安全hash/byte数，不保存隐藏reasoning。
5. 离线模型模拟至少覆盖thinking-only满cap且content空、mixed截断、正常短JSON、provider未报reasoning细项、报错误usage、超过配置cap的实际计量（真实8194要照计而非clamp），所有已可能计费尝试结算并不自动盲重试。大节点再按真实失败材料CN H1/IPO、HK PPT、US call及一个未见材料付费复验，不改旧failed/reservation。
6. 选择/解析是另一个因果问题：HK H1与US release/metrics无可回放精选证据不能归因thinking；真实US官方电话会executor逐段纠正为6位analyst（初报7属执行计数错），native选择只有2组，须对完整parse/unit→select→group证据比较，既查丢失答案也保留完整源限制，不用“selected coverage_complete”代替全篇QA覆盖。

验收按一个配置/模型/选择整合大节点进行，责任层短测试加入既有push/CI共用入口；长/真实收费矩阵不加入每commit。只同步涉及运行文件，保留三个executor旧freeze/版本delta和配置SHA。
