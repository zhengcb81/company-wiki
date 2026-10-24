# M2 独立审查：需修复，尚未验收通过

## 当前结论

候选版集中测试 **382 通过、3 失败，28.72 秒**。执行前后整个 `src` 字节一致，实际 imports 均来自母仓 `src`，独占临时目录已删除。绑定和命令见 `candidate1-semantic-receipt.json`，失败完整保留，不以中间45P代签最终候选。

### 必修产品共因（2项反例，同一个根因）

`AnonymousTurnObserver.clear()` 同时清除 active 和 closed。DOCX 已观察到 `End of transcript` 后，后续真实标题或表格调用 clear，会重开一个已经结束的转写会话，随后编辑附录中的 timestamped Speaker 重新获得原生发言身份。

最小共用修复：结构边界仅清 active；closed 属于整个原件会话，保持至新建 observer。不要增加编辑词黑名单，不在 adapter 重扫正文。独立两项 RED 在 `closed-boundary-red.xml` 和候选全包 XML 中。

### 必修测试契约（1项）

旧 `test_a_real_cross_page_restriction_stays_readable_despite_structural_proof_use` 要求真实业务限制只在 context。新设计把该内在限制升级 citation support，故原断言失败。独立实读证明每条相关 view 的 support 均包含左右跨度，实际 source card 同时保留“已交付”和“尚未完成量产认证、不代表批量销售”。见 `old-context-test-contract.json`。更新测试应强化 support/card 契约，不回退产品、不删除测试。

## 已验证的行为

- 正文结束、空标题、真实 speaker 切换、有效/无效时钟、同actor空白与跨原件身份边界。
- TXT 原事件流无匿名旁路；128个连续段每个 locator 至多观察一次。
- 经营意向动作不被连接词吞掉；业务复合中心词与产品培训手册/支出记录区分；不捏造 actual。
- 同原文、同 parser、同角色、同原生 turn 的直接相邻计划限定才绑定；跨speaker、中间原文、其他主体不借。
- 限定进入实际 model-input/5→schema6 和 source card；普通问题仍只是 context。
- 原 WorkBudget 耗尽诚实 partial；超过既有2048包络时整体 PARSER_INCOMPLETE，没有删掉限定后的裸计划。
- 旧 DOCX1.0/1.1与当前1.2单位ID隔离且原文可回放；实际 batch option assembler→JSON→normalization 接受1.2。version作者还以真实 worker factory 构造/重建和port replay补验，不能误称全生命周期验收。

## 真实原件（0模型）

吉比特原DOCX只读，SHA保持 `63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a`。当前实际 SelectHandler0.9→DTO JSON→原文replay→模型结构/source cards 共23跨度/23卡；新增p5/6/16/89保留，p16未定计划原文到达模型和卡片，所有匿名角色保持unknown。没有翻译、纠ASR或调用模型。绑定见 `real-gbits-final-source-seam.json`；若ROOT改动源树需比对/重跑，不能拿此签新字节。

这不是原oldgold overall、正式摘要、完整缓存崩溃恢复或RF全流程PASS。M1由另一独审负责，本报告不重新签其gold。

## 完整度和后续

ROOT修复closed状态并强化旧support契约后，运行现成 `run_final_review.py`（保留candidate1失败历史），再次运行真实源seam；全部内部发现修复后才能写最终PASS。当前不要求新增人工门或小节点审批。

独审自身初次工具错误（短英文fixture未证明正文、MappingProxy JSON、locator方法、raw_text字段、generator长度）已在自有文件修正，没有误报为产品缺陷。仅写本独占目录，未改产品/旧测试/PWF/配置/原件/索引。
