> **历史检查点，已被后续进度取代。** 本文记录B2实施前的RF/FF接收与CWP producer发布；不是当前源码/待办清单。B2和C普通工程链已有后续通过记录。当前唯一入口：[CURRENT_STATUS.md](../CURRENT_STATUS.md)。

# DU11 两份外包接收与三仓发布收尾

接手后续主线请先读[当前主线接手指南](harness-handoff.md)；本文件只记录已完成的接收、发布和仍保留的收尾事项。

## 该检查点的接收结论

两份卡的功能工程交付已接收且作者提交已并入主线，CWP/FF配套发布和技能安装完成。RF最终依赖pin已推送；其精确CI39095818018也已completed/success。三仓本轮实际发布CI全部绿。

| 仓库 | 已发布实现/配套 | 真实检查与精确CI |
|---|---|---|
| company-wiki | master0ccdc689；含32ab6e06、2022432e | 6801PASS24SKIP346.26s＋142合同PASS48.31s；39094787278 success |
| revenue-forecast | runtime f8002f5f；依赖表e7364639→9669c4d7 | runtime CI39092538354、第一pin CI39094965965 success；final pin416PASS＋36子测73.74s，CI39095818018 success |
| filing-fetch | main e8740748；作者8a83e278及ROOT a9c2dcf7/61011be6/15670bb7均在主线 | 873PASS7SKIP78subtests91.13s；39095654355 success；6物理文件安装并imports/help通过 |

唯一RF compatibility/current.json固定filing=e8740748、wiki=0ccdc689、revenue=f8002f5f，皆实际可fetch；不把自己的manifest commit递归pin自己，也不跟随纯docs HEAD。RF安装版不另加compatibility副本。FF/ RF技能各为3runtime×2物理根=6文件，.claude junction不重复写；不整套覆盖config/output。

## 实际修复和审查边界

- RF：上下文/支持引用和原始金额单位贯通，18个不同独立控制通过；未知真实发布日期仍未知，不能以新签收文件替代事实。
- FF：最终reader manifest的日期/provider优先于陈旧query；显式fmp不冒认未知provider；唯一市场代码owner在CWP，FF只比对canonical projection，不复制去零规则。独立28边界＋1实际HK TXT→CWP→FF复用链跨次29不同控制通过，0ET/public-network，原文篡改拒绝并恢复。
- CWP：一次metadata观察和真实SHA验读、可选canonical identity port；真实PDF MIME/per-pair coverage、线性共享预算/grammar hash cache以及页内序号/未知counter readiness根修。受审4生产文件与主线字节相同，2文本测试仅checkout行尾不同且相同Git blob，实际完整单测和CI也通过。
- 额外发布缺口：ASCII JSON固定CLI传输协议，保留原中文/emoji路径语义与非零错误；唯一CI清单35→38补3已有DU11纯回归；类型schema加准确class-info注解；既有pre-commit同一公共mypy只扩大scripts触发，公共检查约4s，不增加新门/全仓mypy。
- 正常FF推送3次=type RED、旧fixture RED、最终GREEN。fixture只补当前provider/date证明以真正隔离“未知日期不重复下载”，原0调用/SourceRef/asof=False断言和未知provider拒绝控均保留。失败日志未覆盖，没有测试删除/阈值放宽/绕hook。

## 原件、清理与保留项

原件、gold、生产config和key不改；作者工区只读；无新收费模型调用；Dayu/IQS不动。FF未跟踪0字节占位最初删除命令被平台拒绝，未绕过删除；标准Git也先安全拒绝覆盖。随后原生精确移动保留该空文件到本仓自有planning路径，再正常fast-forward；原bytes保留，凭证不读不stage。

RF旧3个assurance WIP不包含本任务提交。第一pin阶段观察weekly_manifest内容变化但未猜writer/恢复旧值；第二阶段保护本轮实际起点，前后相同。output未碰。

**仍有一处清理例外：** `C:/Users/郑曾波/AppData/Local/Temp/rf-du11-final-3a_yd5_8` 为本次RF审查源码/合成夹具外层Temp，内部端到端恢复已通过；外层删除PermissionError后平台拒绝原生清理，ROOT只读确认仍存在，不换通道重试、不声称全清。历史原件/生产配置不在其中。详见du11-rf-reception.md/json。

## 该检查点当时的后续项（已由后续B2/C推进）

工程接收不等于正式内容C。t32诊断不再selected，t34先行词仍OPEN；按antecedent-source-interface-final.md实施唯一source/operating owner的有界前驱和namespace引用映射，联合正文/原context/声明保持8units、4个(source,page,block)、2048chars与同parent16M。必要声明超限则该卡defer，不编产品事实。随后真实三源、正式配置三供应商摘要、费用/activation恢复、同跨run缓存、真实FF/RF C、holdout和RF审查循环。

## 可复查证据

- du11-rf-reception.md/json、du11-rf-publication.md/json
- du11-cwp-publication.md/json、cwp-main-reviewed-equivalence.json
- du11-ff-final-integration.md/json、du11-ff-publication.md/json、du11-ff-installed-runtime.json、du11-ff-exact-ci.json
- du11-dependency-pin-publication.md/json（两阶段同一报告）
- full-unit-workers-independent.md/json、page-local-readiness-independent.md/json
- du11-ff-publication-maintenance-independent.md/json、du11-ff-type-route-independent.md/json
