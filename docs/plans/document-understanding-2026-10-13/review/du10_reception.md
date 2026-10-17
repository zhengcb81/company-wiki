# DU10 ROOT 最终接收 — 2026-10-17

工程验收：三包 PASS，独立审查未解决项 0。发布状态和精确 SHA 见 [机器记录](du10_reception.json)。作者完整历史均用 merge 保留，作者工区只读；未修改原件、生产配置或 Dayu。

| 包 | 作者最终 HEAD | ROOT 验收与修复 | 主线 |
|---|---|---|---|
| FF41 | ff2ba400 | 原41 CaseSpec/oracle不变；完整41/41及中断新attempt41/41收据有效，独立42PASS。按组seed优化、分组收据隔离 | main/origin f1a939e，754PASS＋78subtests；CI39072192244运行中 |
| CWP Goldset | faf5e580 | 修复6组标注口径、真实v2 SourceRef及canonical HTML locator；71PASS，11/11来源回放，独立8问题全部闭环 | master，待本次正常提交/推送 |
| ET Fidelity | cb8e29cd | 进一步修复带`>`未闭属性/注释、main直挂/inline文本丢失；304PASS，独立15控制PASS | main/origin 2584b7e 已核 |

## 大节点实证

- **A**：实际作者最终HEAD、范围、原独审绑定源码核对；不把历史签收/“COMPLETE”当源码正确的依据，不添加新的许可文件。
- **B**：ET根因新测试6FAIL/4PASS→304PASS；Gold语义8FAIL→71PASS（包含真实临时Catalog5个正反控）。中间65PASS/1FAIL为旧测试把中文口号当期间覆盖，改为明确断言不同TTM真实期间，未放松语义要求。最终独立agent复审全部问题闭环。
- **C**：FF→ROOT最新ET companion/transport/launch/budget 117PASS/17.09秒；ET无字段/版本合同变更，不需重复全湖处理；Gold register_sources→query_ref→open_version真实读取11例，HTML精确unit/locator及批量replay，10原件SHA/size/mtime未变、配置SHA未变、临时catalog与sentinel恢复。正常main快进和push，未跳hook。

## FF完整C的范围

作者41/41 PASS用97.6772秒；中断重启v3为**新attempt**，41/41 PASS用144.542秒，12/12恢复/清理控制；旧v2的1PARTIAL保留并拒绝。两工程文件/恢复测试与作者最终独审源码SHA一致，ROOT重用其有效完整C，不为签收再跑一次长矩阵。原始大输出已在作者独审后按卡删除，ROOT不声称用compact收据重新执行oracle。固定依赖/正常负载的C节点关闭，不承诺任意机器负载或线上供应商质量。

## 数据与验收边界

Gold六组语义修正覆盖Verisk单一分部总额、阿里去重口径、东方电缆原文冲突、中微设备子行业/产品时间点、名创发言人角色、宁德产能期间。详见 [Gold ROOT记录](../parallel/du10-2026-10-17/goldset/ROOT_RECEPTION.md) 和其中独审收据。旧错误报告保留为历史，由ROOT最终结论覆盖。

Gold是**已看过的回归标注集**；不能充当未见holdout，也没有跑正式LLM摘要。回放PASS证明来源/locator，不单凭程序断言经济事实正确。ET只拒绝词法未结束标记，不声称检查任意句中截断；一个标准tokenizer预检加一个BeautifulSoup DOM，未伪称单tokenization。真实线上MF DOM未下载复测。

## 保持与清理

全程0收费、0下载、0翻译、0原文副本。作者工区不清理；ROOT接收工区在主线包含完整交付、树干净后正常移除。主仓FF未跟踪密钥只核大小/mtime不读内容，ET既有3文件保持；测试隔离目录按具体绝对路径限定清理，收据保留小型JSON/MD，生产库不写。

## 下一步

回到 [PDF生产接线方案](pdf_page_intent_implementation.md)：原生导航、唯一matcher、POLICY+PLANNER、统一WorkBudget、source单parse，然后真实深页、配置供应商正式摘要、缓存恢复与新盲样本验收。三包完成不表示整个PWF目标完成；FF41固定C不再OPEN。
