# CF1–CF4主线实施（2026-10-25，进行中）

## 当前结果与验收边界

CF3共享效率第一节点已实现、独审PASS，待本次正常提交发布；**CF1–CF4整体未完成**。原件、生产config/catalog、16M同一账户和112片段上限不变，0模型/API/下载/原件副本。没有新增权限、身份验证、签收或预算库。

| 根因 | 实施和证据 | 当前判决 |
|---|---|---|
| 单列多页扫描所有页；单语DOM/不等长列展开不可能配对；单书写系统几何仍两两比较 | 同source/page建索引，付费线性判定后只跳过确定不可能的组合；真双语保留次序、最近邻/tie/几何条件。独审另关闭异kind几何误连 | 中性RED→GREEN，差分/来源隔离通过 |
| 结构子算法未进入decision/cache身份 | 现有business_algorithms绑定整个owned structure Python包，自动覆盖新增/删除子模块、LF规范化及跨宿主位置，wire字段不变 | 2项真RED通过；旧12参数测试改为真实源码字节注入，same/changed断言不变 |
| 每个opaque/deferred页重扫所有units生成诊断 | 实际reserve caller定位5,154,576工作；改为一次页→原始unit IDs索引，保留全部页项/顺序/重复/空页/独立列表，预付输入/页数及输出copy | 3项RED→GREEN；独立500 helper及24完整结构对照逐项相等 |

### 真实IPO：有进展，仍是partial

`cf3-ipo-indexed-replay.json`从SourceRef读取中微原招股书，SHA不变；429页/14,025units/parse420,052与冻结旧结果一致。understand_units从11,473,800降到6,334,220，减少5,139,580（约44.8%）；这是**该阶段逻辑工作量**，不代表全流用量或CPU减少44.8%。同16M账户最终15,998,158，候选阶段因而能继续并保留112span（旧0span），status=partial且exhausted=true。未提高预算，未删除缺页诊断或假称全文读完。

候选阶段当前9,229,860包含更多有效工作，不能与旧提前停止的4,091,862直接判为性能恶化。正式IPO内容gold未建立，内容NOT_GRADED；未编译或外发耗尽后的模型请求。选中112并不代表这些内容完整或覆盖全文。

第一次改后`cf3-ipo-replay.json`使用venv/PyMuPDF1.28.2，产生14,006units，逐次Path规范化也增加诊断开销；收据原样保留，不作同backend耗时基准。后一次用默认Conda/PyMuPDF1.26.7，固定深度profile只记录原始code位置，落盘才规范路径，记录环境版本。旧冻结runner未保存环境版本，不能宣称严格CPU A/B。两次无生产写入，代码/config/catalog完整SHA稳定。

### 测试、独审与执行卫生

- 关系10项真RED阶段4失败，单书写系统几何另有真RED；当前11关系+2算法身份通过。相关198PASS包含这些项。
- 覆盖诊断3项真RED→147相关PASS（与198重叠，不相加）；mypy src375零错、Ruff通过。
- 最终`cf3-independent-review.md/json` PASS、0OPEN：74项独立测试；750关系差分（285有关系正例、127仅删除异kind误配）及250跨来源对照；500 coverage helper和24完整structure/coverage/diagnostics逐项对照。真实profile各caller accepted之和与唯一账本一致，运行绑定源码SHA匹配。
- 自有测试临时目录恢复不存在。沙箱TEMP首轮遗留已精确删除，失败日志保留；未全库清理、未做完整恢复备份演练。

### 唯一下一步

正常commit/push本节点，记录精确CI；然后继续CF1真实HTML业务标题/原生列表依赖、CF2港股中报未闭句及单位/限定条件；CF3下一节点按实际候选热点优化已有owner内重复事实/声明观察，不加第二cache或公司特判。三市场新attempt来源独审合格后，再正式v4摘要→缓存恢复零重复费用→RF实际采用→四路公司审查。W18/W19作者路径、Dayu/IQS不写。

## 实施开始时的调查快照（以下Next Step已被上方取代）

唯一上级计划du11-source-closure-2026-10-18。W16/W17已完成接收并线安装，不重跑。当前主线先恢复真实来源关系/完整句并解决长文工作量，再正式摘要/cache/RF。

初查CF1：HTML最近block-owner文本在子owner之后发出，保留dom_path但仅原生h1–h6有heading_level，粗体业务小标题及原生列表祖先没有结构化传给共享structure；需要实际DOM正证而非发行人字符串。不得把所有bold都当业务标题。CF2断句须定位native block原边界。CF3已委托独立只读CodeGraph调查，不重跑真实16M耗尽；有明确O(P²)/same-language组合预留线索，先有界中性计量。

本轮TDD依次冻结失败/正反控→共享owner根修→集中相关测试→独立大节点复审和真实三源回放。若改变解析语义，显式当前/旧parser replay与cache依赖跟进，不改旧原件/金标/0.6–0.8选择语义。无新增审批、身份库、预算账户或全量常驻转换。

## Next Step

读绑定原件的DOM证据与CF3计量；将已证实共因固化为中性RED，决定最小共享实施。W18/W19作者路径及storage/schema不写，Dayu/IQS不动。
