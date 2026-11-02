# 整改清单逐项核对结果

原始正式清单 **41项**（Q01–Q14及六份R7原审计）全部有明确对应，遗漏ID为0。T01再展开为8个实际工具入口。另记录3个本轮新发现的实质遗漏、2个未做的可选优化；不把增量/父子条目重复计成缺陷数或项目进度百分比。

**原41项：40项工程处置已完成，Q11经边界论证保留。** 这些结论各有范围，尤其Q09仅本地主线，Q01/Q02/Q12的新版真实C仍未完。

本轮新增补修：SourceExport两仓加载后16MiB许可；付费响应保存层256KiB隐藏顶帽。TDD历史CWP2F1P、StockWiki1F保留，修后受影响CWP54P/13.00s、StockWiki33P/5.21s；真实loopback大响应完整持久化、中断、unknown、新lease及无凭证恢复仅一次POST。独审/CI当前状态见同名JSON，不用旧389a10fbCI给新代码签收。

沿保存链追加发现运行binding_json的256KiB顶帽，已1RED→23P/5.21s；完整500条canonical元数据重开不丢、重复创建幂等、篡改run binding仍拒。请求解析通过不代持久化全链通过，已纳入本表及最终独审。

新补修独审：通过；新源码精确CI：通过。

所有逐项完整路径/符号、源码SHA、测试责任、独审版本、发布与限制见下表链接的同ID dossier及[机器对照表](checklist.json)。本轮只补跑新受影响域，未重跑原整仓；四个早期R7源码CI成功是历史有效证据。

## 原代码质量Q01–Q14

|ID|要求／条目|核对结论|逐项源码、测试与独审证据|
|---|---|---|---|
|Q01|陌生行业完整经营陈述不因有限动词/对象词表被丢弃；可读资格与事件/量值/发行人证明分轴。|工程完成；真实C未完|[Q01完整记录](q-items-independent.md)|
|Q02|实际阅读算法/数据/runtime依赖变化使真实缓存失效，不适用格式变化不误伤。|工程完成；真实C未完|[Q02完整记录](q-items-independent.md)|
|Q03|精确公司查询不先受全库同文种20k计数拖累；保纠错/别名/冲突候选超集及最终语义。|工程完成|[Q03完整记录](q-items-independent.md)|
|Q04|空间增量归实际run；轮询不反复扫共享CAS；并发/崩溃不能降账或放大额度。|工程完成|[Q04完整记录](q-items-independent.md)|
|Q05|去除旧parser-name全范围DELETE，不让一次性legacy prune删除当前引用证据。|工程完成|[Q05完整记录](q-items-independent.md)|
|Q06|CAS put现存对象及FileExists竞争分支都按expected_size+1有界验证。|工程完成|[Q06完整记录](q-items-independent.md)|
|Q07|退役硬机器目录复制及默认真实公司/原地清水印脚本，不依赖sitecustomize。|工程完成|[Q07完整记录](q-items-independent.md)|
|Q08|架构测试用AST覆盖relative/qualified/alias/__init__/常量动态import；注释不误报，owner豁免不能basename绕过。|工程完成|[Q08完整记录](q-items-independent.md)|
|Q09|StockWiki在读取期流式限制stdout/stderr并回收超额/超时进程树，避免全量缓冲。|工程完成；StockWiki仅本地主线|[Q09完整记录](q-items-independent.md)|
|Q10|纯SourceExport不强绑具体SourceVersionReader；writer不经高层reader构建身份。|工程完成|[Q10完整记录](q-items-independent.md)|
|Q11|评估同次bytes重复SHA，只合并真正同owner热点；不删公开接收/跨时间复核。|按理由保留|[Q11完整记录](q-items-independent.md)|
|Q12|按原文材料、依赖闭合、准入与预算组合阶段拆责任，保单次准备和旧facade。|工程完成；真实C未完|[Q12完整记录](q-items-independent.md)|
|Q13|reader CLI区分invalid_request与环境/存储unavailable，坏hash在catalog前验证且错误pathless。|工程完成|[Q13完整记录](q-items-independent.md)|
|Q14|正常scan/preview不依赖旧snapshot/伪两轮零diff；旧运维CLI退役，历史回放兼容。|工程完成|[Q14完整记录](q-items-independent.md)|

## CWP核心、原观察器与增量

|ID|要求／条目|核对结论|逐项源码、测试与独审证据|
|---|---|---|---|
|R7-G1|多层成功结果/可选诊断的固定尺寸和深度|工程完成|[R7-G1完整记录](core-and-integration.json)|
|R7-G2|自动坏缓存不应否决新任务|工程完成|[R7-G2完整记录](core-and-integration.json)|
|R7-G3|同一个原生成员内未知子句连坐已证子句|工程完成|[R7-G3完整记录](core-and-integration.json)|
|R7-G4|同次已验证源buffer和metadata重复验证|工程完成|[R7-G4完整记录](core-and-integration.json)|
|R7-G5|几何导航多个32/64/4096任意天花板|工程完成|[R7-G5完整记录](core-and-integration.json)|
|F1|batch100和输出2MiB隐藏顶帽|工程完成|[F1完整记录](core-and-integration.json)|
|F2|provenance扩展16KiB许可|工程完成|[F2完整记录](core-and-integration.json)|
|F3|原文C:/file://被误判为物理存储路径|工程完成|[F3完整记录](core-and-integration.json)|
|ADD-AVAILABILITY|availability metadata同一父预算和终态取消/deadline|工程完成|[ADD-AVAILABILITY完整记录](core-and-integration.json)|
|ADD-MODEL-FINAL|模型真实读取成功后又按128KiB否决|工程完成|[ADD-MODEL-FINAL完整记录](core-and-integration.json)|
|ADD-EXTRACTIVE|extractive默认56KiB衍生顶帽|工程完成|[ADD-EXTRACTIVE完整记录](core-and-integration.json)|
|ADD-EXECUTION|summary execution/result完整收据|工程完成|[ADD-EXECUTION完整记录](core-and-integration.json)|
|ROOT-OBSERVER|原300KB/16KB/32祖先观察门|工程完成|[ROOT-OBSERVER完整记录](core-and-integration.json)|

## 工具全部入口及明确未做事项

|ID|要求／条目|核对结论|逐项源码、测试与独审证据|
|---|---|---|---|
|R7-T01.01|pre-push stdout/stderr日志体积|工程完成|[R7-T01.01完整记录](tooling-independent.md)|
|R7-T01.02|PhaseC prepared／generation／capsule checkpoint|工程完成|[R7-T01.02完整记录](tooling-independent.md)|
|R7-T01.03|identity-audit结果输出|工程完成|[R7-T01.03完整记录](tooling-independent.md)|
|R7-T01.04|narrative_g2_replay完整报告|工程完成|[R7-T01.04完整记录](tooling-independent.md)|
|R7-T01.05|source_root_portability完整报告|工程完成|[R7-T01.05完整记录](tooling-independent.md)|
|R7-T01.06|storage_footprint输出规模|工程完成|[R7-T01.06完整记录](tooling-independent.md)|
|R7-T01.07|RAW-DUP明细／头部／报告体积|工程完成|[R7-T01.07完整记录](tooling-independent.md)|
|R7-T01.08|cross_market_suite运行观察与JUnit property|工程完成|[R7-T01.08完整记录](tooling-independent.md)|
|R7-T02|holdout全树clean许可|工程完成|[R7-T02完整记录](tooling-independent.md)|
|R7-SWEEP-T01|PhaseC已持久成功结果的128KiB观察否决|工程完成|[R7-SWEEP-T01完整记录](tooling-independent.md)|
|R7-SWEEP-T02|final_material默认表示帽|工程完成|[R7-SWEEP-T02完整记录](tooling-independent.md)|
|R7-SWEEP-T03|完整CI重复Unit节点|工程完成|[R7-SWEEP-T03完整记录](tooling-independent.md)|
|R7-SWEEP-T04|PDF cold probe固定rev／禁止重跑|工程完成|[R7-SWEEP-T04完整记录](tooling-independent.md)|
|R7-O01|PDF部署同inode重复SHA优化|可选未做|[R7-O01完整记录](tooling-independent.md)|
|R7-SPY-200-SAMPLE-MARKER|consumer-spy 200条样本完整度标记|可选未做|[R7-SPY-200-SAMPLE-MARKER完整记录](tooling-independent.md)|
|R7-KEPT-OWNER-RESOURCES|真实资源／源真实性／不覆盖保护|按理由保留|[R7-KEPT-OWNER-RESOURCES完整记录](tooling-independent.md)|
|R7-KEPT-EXPLICIT-PRODUCER|holdout本次显式producer commit|按理由保留|[R7-KEPT-EXPLICIT-PRODUCER完整记录](tooling-independent.md)|
|R7-REAL-C|真实H1／新版摘要／缓存恢复／RF实际采用|真实验收未完|[R7-REAL-C完整记录](tooling-independent.md)|
|R7-T01|工具日志/收据/报告表示门（全部8个入口）|工程完成|[R7-T01完整记录](tooling-independent.md)|

## RF／FF／invest及保留边界

|ID|要求／条目|核对结论|逐项源码、测试与独审证据|
|---|---|---|---|
|RF-01|删除完整叙述/reading_context/assessment重复固定size/count/depth许可，实际资源预算归transport。|工程完成|[RF-01完整记录](crossrepo-independent.md)|
|RF-02|去proof128KiB、摘录10–500及采用理由2048许可，保持完整局部closure和真实引用。|工程完成|[RF-02完整记录](crossrepo-independent.md)|
|RF-03|坏/缺/未知review、assessment和producer recipe不得反向否决已实读来源，统一诊断owner。|工程完成|[RF-03完整记录](crossrepo-independent.md)|
|RF-04|全局publication registry可重建、不可成为有效artifact使用许可，不全历史预验/反复chmod。|工程完成|[RF-04完整记录](crossrepo-independent.md)|
|RF-05|同事务原文只验/哈希一次，内部复用immutable值，公开raw反序列化仍独立验。|工程完成|[RF-05完整记录](crossrepo-independent.md)|
|FF-CURRENT|核FF仍否有manual/authorization/expiry/canary/clean许可；区别兼容字段与真实门禁。|按理由保留|[FF-CURRENT完整记录](crossrepo-independent.md)|
|SW-INV-QUOTE|invest通用摘录10–500为多余许可：改非空，保hash/source/币种单位/期间。|工程完成|[SW-INV-QUOTE完整记录](crossrepo-independent.md)|
|SW-RF-QUOTES|RF target builder/backtest残余摘录10–500与主证据owner对齐。|工程完成|[SW-RF-QUOTES完整记录](crossrepo-independent.md)|
|SW-RF-DRIVERS|总driver和每driver evidence10条帽不能拒完整DAG材料。|工程完成|[SW-RF-DRIVERS完整记录](crossrepo-independent.md)|
|SW-FF-CONFIG|原审暂保64KiB后续证实为active配置表示门，必须去掉而非抬帽。|工程完成|[SW-FF-CONFIG完整记录](crossrepo-independent.md)|
|SW-LOCAL-DIAGNOSTICS|FF/RF附注128KiB/8层/32键/1024项及ET usage8192不得否决真实主因或改已知用量。|工程完成|[SW-LOCAL-DIAGNOSTICS完整记录](crossrepo-independent.md)|
|SW-RF-AVAILABILITY-TEXT|availability evidence_ref/locator2048字符不能否决合法proof。|工程完成|[SW-RF-AVAILABILITY-TEXT完整记录](crossrepo-independent.md)|
|SW-E2E-FIXTURE-PERMIT|Biren冻结错pair/伪host_signed和强制registry不能换tag/吞golden；真实CLI分阶段必须执行。|工程完成|[SW-E2E-FIXTURE-PERMIT完整记录](crossrepo-independent.md)|
|SW-INV-REPEAT|run_company/run_bundle/当前bundle read相邻同对象两次RF强验统一归reference owner。|工程完成|[SW-INV-REPEAT完整记录](crossrepo-independent.md)|
|INV-CONSUMER|下游不得默认registered/host_signed作为使用许可，不能削弱真实RF输出重算。|工程完成|[INV-CONSUMER完整记录](crossrepo-independent.md)|
|INV-HOOK|commit/push不重十组件全suite/E2E或隐式全局同步；验真实staged bytes。|工程完成|[INV-HOOK完整记录](crossrepo-independent.md)|
|INV-INSTALL|同步只写明确文件，保配置/其他文件，不得每push整套覆盖。|工程完成|[INV-INSTALL完整记录](crossrepo-independent.md)|
|RETAINED-RESOURCES|不把真实下载/HTTP/子进程bytes、timeout、token/费用/空间/本地读工作预算混为表示许可。|按理由保留|[RETAINED-RESOURCES完整记录](crossrepo-independent.md)|
|RETAINED-CORRECTNESS|源字节/公司/期次/as-of、引用partition、币种单位/公式重算与真实signed声明仍需严格。|按理由保留|[RETAINED-CORRECTNESS完整记录](crossrepo-independent.md)|
|RETAINED-FORMULA|500字符公式与自然语言摘录不同，属于受限递归算术工作保护。|按理由保留|[RETAINED-FORMULA完整记录](crossrepo-independent.md)|
|RETAINED-CREDENTIAL|FF credential scalar4096是凭证读取，不是财报/配置表示许可。|按理由保留|[RETAINED-CREDENTIAL完整记录](crossrepo-independent.md)|
|RETAINED-LEGACY-DIAGNOSTICS|明确退休/显式audit/version工具不应再当正常canary门禁重复删除。|按理由保留|[RETAINED-LEGACY-DIAGNOSTICS完整记录](crossrepo-independent.md)|
|CROSS-DEPLOYMENT|canonical通过还需覆盖实际三个技能安装根，并防整目录覆盖/配置漂移。|工程完成|[CROSS-DEPLOYMENT完整记录](crossrepo-independent.md)|
|REAL-C-AND-COMPANY-LOOP|工程/合成/部署绿不等于真实摘要、缓存恢复、RF经济采用及全部公司循环完成。|真实验收未完|[REAL-C-AND-COMPANY-LOOP完整记录](crossrepo-independent.md)|

## 本轮新发现、已直接补修

|ID|要求／条目|核对结论|逐项源码、测试与独审证据|
|---|---|---|---|
|R7-RESIDUAL-V2-WIRE-CAP|本轮新发现：两仓公开JSON加载后16MiB表示门|工程完成|[R7-RESIDUAL-V2-WIRE-CAP完整记录](residual-repair.json)|
|R7-RESIDUAL-PAID-RESPONSE-CAP|本轮新发现：已配置HTTP响应仍被256KiB持久化顶帽拒绝|工程完成|[R7-RESIDUAL-PAID-RESPONSE-CAP完整记录](residual-repair.json)|
|R7-RESIDUAL-RUN-BINDING-CAP|本轮追加：运行冻结元数据256KiB表示门|工程完成|[R7-RESIDUAL-RUN-BINDING-CAP完整记录](residual-binding-repair.json)|

## 不能合并成“已完成”的剩余事项

- T4：H1的三个已选视图仍继承旧备注子标题；12/12召回不是父链正确的证明。先在来源树owner根修，再单份原预算复验。
- 新版真实摘要、付费中断及同run/跨run缓存零重复、同artifact实际RF参数/公式/报告/snapshot采用仍待验收；合成loopback只证明技术恢复。
- R4六共因、研究质量与审查检测进化、固定公司和三家clean要求继续归原主计划。
- 两项可选优化：PDF部署对同inode重复SHA；consumer-spy最多200条样本尚无sample_limited标记。全量异常计数仍保留，均不阻断资料处理，不作主线前置许可。
- StockWiki未配置remote；正常本地主线提交另有收据，不能写成已推送或远端CI绿。

- RF另有两处非阻断旧注释待顺手整理：register_publication的Raises说明、pre-push“与CI同表”注释；实际控制流已简化。它们单列为文字事项，不误报新门禁，也不冒称本轮已改。

## 记录更正

原README/implementation的初期未实施/失败/暂停已与当前状态明确分界；R7主计划、STATUS、CURRENT_STATUS、HANDOFF、task_plan与本表对齐。旧FAIL、作者待审交接和旧进度日志保留为有日期的历史，不替换成通过。
