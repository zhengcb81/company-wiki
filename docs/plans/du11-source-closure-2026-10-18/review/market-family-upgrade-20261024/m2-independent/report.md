# M2 独立审查通过（限定工程与真实来源接线）

## 最终证据

- **386项通过，0失败，31.14秒**，其中47项为独立中性反例。覆盖作者新载体/意向/限定/版本能力测试、旧TXT兼容、DOCX标题/结构/脚注、native连续/依赖/载体、reading模型/传输和完整du11_source_quality。
- 整个src共374个Python文件执行前后与真实源重放前后完全一致，聚合SHA：`55d7bb8c0eadce29bd309f199f8d8fca45e79bf0b2b2326c5f16d95e116ec560`。实际imports及所有源码逐文件SHA见final-semantic-receipt.json；测试文件SHA见report.json。
- 独占basetemp精确清理，结束为absent。未改产品、旧测试、PWF、配置、原件或Git索引。

## 共因与修复复审

1. 共享observer现在结构边界仅清active，不重开closed。真正新原件使用新observer；结束后标题/表格无法复活发言身份。
2. TXT匿名轮次复用原正文与speaker事件流，不设旁路。正文证明共用去timestamp标签后的实际内容；短CJK正文保留，空标签和仅一个CJK字符夹ASCII不冒充正文。
3. 同actor空白变体、不同原件不凑成多speaker电话会；角色unknown不会被标题/编号升级为管理层或issuer。实名native身份与话语角色分开。
4. 经营意向保持有限marker→action→对象中心词语法，不吞掉更新/continue动作，不把business/product/customer修饰行政手册或支出记录当业务对象。合法service platform复合头可保留，没有公司专用allowlist。
5. 同原文、同parser/角色、同native turn的直接相邻明确计划限定进入既有局部依赖、包络、citation support和实际model/card。跨speaker、跨原件、中间段落和其他对象不借；普通问题仍context。原WorkBudget耗尽诚实partial；超2048包络整体PARSER_INCOMPLETE，不产生删除限定后的裸计划。
6. DOCX版本能力由normalization owner统一，旧1.0/1.1可重放、与新1.2单位ID隔离。真实batch选项组装→JSON→normalization→原文replay通过。版本作者还提供实际worker factory构造/重建port回放，不把这些冒充完整生命周期。
7. 旧跨页限制测试已按语义强化：每条包含左事实的support同时含右限制，实际source card保留两者。没有通过删除测试或把限制降回context取得绿色。

## 真实原件source-only验收

吉比特DOCX原件SHA保持`63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a`。
实际SelectHandler0.9→DTO JSON→原文replay→model-input/5(schema6)→source_cards通过：**23跨度/23卡**，p5/6/16/89保留，p16未定计划的原语言限定进入模型和卡片；全部匿名source_role仍unknown。原文不改、不翻译、不纠ASR，模型调用0。
这项验收使用隔离内存FakeReader验证真实字节到来源材料的接线，不冒称生产catalog下载、日期识别或RF运行。

## 范围与历史

本报告仅签M2工程与真实来源接线。M1 gold由另一独审负责；oldgold overall、正式LLM摘要、RF分析质量和完整OS worker崩溃/历史/cache生命周期均不能由这份PASS代签，ROOT正在另做实际public-history集成。

候选失败历史完整保留：candidate1-semantic为382P/3F；两个closed反例与旧context契约均有实证、已修复并在本最终386P复验。candidate1-report、最初反例XML、独审自身fixture/API错误说明均保留，不回写为绿色历史。

无未修内部发现；无需新增人工门禁或小节点签收。
