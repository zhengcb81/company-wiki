# 三仓架构与代码质量升级

PLAN_ID: architecture-quality-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
状态：A/B完成，三仓代码已接本地主线；C跨仓工程测试通过，正常发布/精确CI收口中。

## 目标与边界

针对company-wiki、filing-fetch、revenue-forecast的现有主线做架构全景检查，按有证据的共用根因消除路径/公司/模型硬编码、冗余实现、错误掩盖、职责交叉和不必要门禁。不是以行数或任意抽象层数量为目标。公开CLI、SourceRef/SourceExport/NarrativeRef和RF结果语义保持兼容；需要调整接口时由ROOT统一记录、修改消费者并测跨仓。

原件保留；生产配置、密钥、原有WIP不写穿；不动Dayu和invest-quick-scan。文档理解三条DU外包线及其独占目录/DU/1接口保持不变，新审查不得抢写它们。DU已承担的路由/结构问题列为关联改进，不能重复实现第二套引擎。LLM供应商遵循配置，本轮工程改造先离线，无必要不调用付费模型。

## 分工与接口

三名agent各独占自己的质量改造worktree及本计划results/company-wiki、results/filing-fetch、results/revenue-forecast。ROOT拥有本计划、母PWF、三仓接收/并线/安装/推送，不与agent同时写同一checkout。agent先全面调查、写报告及优先级，再向ROOT报告具体改造范围后实施；存在跨仓接口或DU冲突时先报告，继续不依赖该冲突的工作。

每仓report.md须有：模块/入口及调用关系、已读范围、硬编码与重复的证据位置、可复现问题、根因和改造范围、兼容性、暂未实施事项及原因。handoff.json须含schema_version=architecture-quality/1、repository、baseline_sha、worktree、findings[{id,severity,root_cause,evidence,disposition,changed_paths,test_refs}]、commits、tests[{command,result,counts,duration_seconds}]、public_interface_changes、remaining、preserved_inputs、cleanup。不能把全部异常捕获/协议常量/必要边界校验一律删除。

## 阶段与验收

- A [complete] 各仓独立结构审查＋配置/依赖/测试/历史PWF对照已给出具体范围。每项真实缺陷有证据和影响面；DU负责路由/章节，冻结legacy仍有调用的模块不盲删。详细报告见results各仓目录。
- B [complete] 三仓共用根因和第二收口已实改/集中测试/正常提交，全部接本地主线。报告根因与兼容范围，不以放松断言掩盖错误；旧同命题反证、原数值和资源边界仍测。
- C [in_progress] 集中跨仓离线E2E工程检查通过（48 PASS/0 FAIL），九型G2 PASS，配置/原件/WIP和临时目录恢复。FF/RF完整owned runtime及fresh安装入口已核。正常提交推送与精确SHA CI收口中；离线不可证明的真实资料/供应商范围留母计划，不伪称全技能完成。

正常CI不加入网络/模型/慢公司审查。最终工程套件只跑必要受影响范围与既有快测，剩余真实G2/G4/G5仍由母计划承担；代码质量检查不能替代业务事实质量验收。

## 已协调实施细则

| 仓 | 共享责任收敛 | 验收重点 |
|---|---|---|
| CWP | writer以当前RootSpec+relative_path定位可复用原件；基础设施统一同目录唯一临时文件+replace提交，保留immutable raw独立语义 | 整根移动/配置删除后的去重、实际SHA/类型、并发原子提交、失败旧文件保持、临时清理；不动DU包 |
| FF | root/ET/doctor共用有界配置读取和原有token展开；query/ensure共用SourceRef候选投影与绑定；真实日历日期；便携hook | 读期间上限、UTF-8/未知token一致、nested物理字段不外泄且合法业务字段不过度拒绝、非法日期0provider、原CLI/E2E不退化 |
| RF | 原生参数用途/derived依赖visitor供数学/研究/叙述消费共用；运行包清单与内容manifest统一；数值异常统一ForecastInputError | recognition短carry-in/进度、并表adjustment依赖可追溯，stock/rate不洗成收入；合法数值保持，非法幂/overflow诚实拒绝；修改代码改变指纹、工程残留不改变指纹、安装等价 |

集中反例进一步发现并纳入B：CWP 1.x/2.x/3.x配置类型验证分叉（字符串false被当true）复用同层校验；local_reconcile重复按root.kind识别文件布局改为调用已配置adapter的有界发现。Dayu只读外部，不改其代码。RF相同excerpt不能等同相同命题：保留同claim/同具体命题冒充正反证据的拒绝，不同具体事实共享物理引用只留语义关系NOT_EVALUATED诊断，独立经济审查不被替代；原负例改成真实同命题换ID，不删断言。

ROOT不代写agent模块，不并发改它们的checkout。跨仓契约无变更预期；确需变更先协调消费者，不能“内部绿”替代跨仓验收。最终对照现有三家公司固定经济结果与31原生组合、九文档型叙述回放；明确离线fixture不认证真实供应商摘要或完整研究。

发布编排统一：定点安装前先用既有安装器读取完整owned runtime plan，检查旧依赖漂移；只同步本次改动及明确缺失/漂移依赖，保存旧SHA，配置/密钥/output/unknown保持。完成仅表示选中copy完成，不能直接当整包可运行；再做fresh进程正常/失败入口和相关lazy入口验证。FF实测.codex旧ff_provider_cause缺build_request_diagnostic，仅补此1依赖后完整plan无差异，三安装面invalid-date均request_error且0calls/0downloads，目录恢复。

第二收口：CWP存储扫描routes用有序first-match（include且非exclude），route adapter/profile真正用于group original_primary归属；各adapter最多一次枚举但预算全局共享，去掉固定9路径重叠许可；便携hook三仓统一当前环境。RF删除无消费者的生产内存Demand enqueue，保留确有调用的compat边界；独立peer发现跨segment约束传递及input/output clock范围需按实际消费明确/修复，不得用base dependency宣称完整最终cell依赖。

FF安装工具第二收口：复用已有owned manifest给plan/result加入完整runtime及scope外drift只读诊断，apply仍仅写明确scope；byte-complete不等于fresh运行通过，不作为许可或hash放行门。避免未来较弱执行者把subset copy success当整包就绪。新测试验证旧依赖drift、partial写、alias和配置/unknown保留。

## Next Step

完成三仓正常发布并核对精确CI，将最终receipt/空间清理和剩余母计划范围写回本计划与母PWF，然后接DU三独立包；不再重复派发本轮质量改造。

## Errors Encountered

- 沙箱内对RF/FF执行Git状态报must be run in a work tree；外部只读核查确认真实仓库正常且RF原有三份运行记录未提交。后续Git写入正常使用明确范围的escalated操作。
