# Findings：当前事实、风险与证明范围

**2026-10-08，目标active。** 本页只放当前事实；历史完整调查见[6dd5601完整findings](https://github.com/zhengcb81/company-wiki/blob/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26/findings.md)。施工状态只取[task_plan](task_plan.md)。

## 架构与门禁

CWP只维护immutable来源、解析/质量、精选业务描述、证据定位与只读export；StockWiki独占研究状态。SourceRef/Export v2/NarrativeRef隔离存储目录。现有AUTO统一预算、lease/generation/outbox，子进程客户端隔离、有限多文档P4；不新造队列或全量永久MD。Dayu/IQS不写，CN维护SID简易执行分支。

G2十四组与A/B已发布，[最终验收](g2_consolidated_node_2026-10-08.md)证明steady、旧canary/签收/人工review/工程长门退出。固定SHA许可表已删除；真实reader开字节SHA及身份/期间/公开日/版本/资源限额保留。RF/FF真实定点安装和重复0写已验收，不重做。旧卡中要求review/签字/双下载许可的文字是历史，不反过来覆盖用户简化授权。

## 来源事实与真实质量

R2正式4restore/九事实/TXT统一登记完成；[生产应用](harness_lanes/results/r2_production_source_application_2026-10-08.json)逐项记录六表差异。S05/S06融资类型，S07/S08证券身份，S01–S04官方日期与期间已校正；S07/S08/S09公开日unknown，不从活动、会议或URL日期捏造。旧ET TXT66324B保持原语言/SHA，sidecar589B明确legacy_unverified和无历史HTTP receipt。未选文档/根水位/原采集声明保持。

SourceCatalog.record_source_facts单事务追加事实+查询投影，缺键不改/null明确unknown；相同观察时间变化不重复，64KiB累计证据/2048字符事实有界。重登同capture继续用有效事实，新真正矛盾仍拒绝。当前101责任/真实九原件E2E绿，6ae7ddc/精确CI37705927320绿。

S7当前selector0.4.2/parser0.1.1/prompt1.6.0，九样本29/33 required、761定位回放；四miss解释、optional取舍、重复6保留，不改golden凑分。旧N4C真实run10有20 claims/46locators/99479B、15管理层/5分析师，六主题证据覆盖/五主题短摘要覆盖；全部是隔离数据，不能当R3已生产。

## 空间及本轮归属

S5/S6生产净释放5659443210B、原件0删除，DB222408704B；R2主文件不增长，WAL1240152B是合法小事务，TXT/metadata新增66913B。R4已登记内部逻辑重复上界98845393B，实读额外36191979B，allocation/releasable未知，因此不做收益不足的对象化，不声称释放GB。

R5已读8根：五G2及cw-retire-r1是closed pytest夹具；canary PDF与companies原件实读同SHA，删其untracked副本和catalog缓存，保留tracked历史4文件。合计119913476B/1123文件，26保护SHA及生产DB stat不变；[归属](harness_lanes/results/r5_temporary_ownership_2026-10-08.json)、[清理](harness_lanes/results/r5_owned_cleanup_2026-10-08.json)。旧pilot461338B含未知usage/recovery事实，保留整根；tmp/pdfs和外包交接/owner不动。逻辑字节不等同allocation承诺。

## 真正剩余与预算

R3模型尚未POST，production final0。现生产TXT49段/10873B HTTP，完整19193token/14591microUSD；当前余9965token，220000累计token增量待答，费用上限0.12不变。历史190035/100502/unknown7/FX2764照计，未知usage不退款。模型配置不改；不重新要求已明确的同资料向DeepSeek外发授权。

正式AUTO路径.source_catalog/automation.sqlite3目前未创建，是现有AUTO实现的首次生产实例，work-dir.source_catalog/r3；历史tmp pilot不是第二生产队列。当前请求不能说明已经有final或完整预测。R3须真实有限批次/当前消费者/恢复/真实空间一次大节点，随后R5逐条完整审计及正常发布。

## 已知错误与限制

R3A发现原NarrativeReadRequest/producer/RF/SW均强制ISO日期与已知公开日，所以前一份R3方案的“当前普通读取+未知日期不造假”不能实际成立；历史fixture日期消费绿不能代替此生产能力。[R3A](r3_current_material_read_implementation_2026-10-08.md)现complete：显式null仅表示当前资料，指定历史日期仍严格校验公开日。CWP38单测/26责任包及源码CI绿；RF67pass/1个Windows skip，SW68pass/0skip；四真实原件公共CLI节点1pass/0skip/49.98秒，本地loopback3、恢复新增0、真实provider0。RF main c672a5e已推/精确CI37712024241全绿，SW master42fba06本地已合入，无remote。CWP联调测试f0ad6b9已推/精确CI37712551891全绿，live仍0，费用/模型配置和正式batch不变。

RF仓跟踪约4.7万历史planning文件，复制整仓工作树会制造无用副本。本次明确归属的隔离RF工作树使用Git稀疏检出，最终仅295文件/3144753B；两个已合入工作树现已移除91161217B副本，不删主仓历史。342 owner文件保持，RF一个接口文件定点安装的480未选文件保持/重复零写。兼容测试原以固定兄弟路径找仓，在隔离位置9次WinError267，实际三仓布局19绿，不改oracle迁就错误目录。测试清理的PowerShell Split-Path参数集错误有先前Python边界检查和后续.NET父目录/absent复核，不隐去该错误。

产品RED：缺事实公开接口、重新登记的假分类冲突、旧host固定SHA门；均有当前GREEN与源码CI。夹具/调用错误：错路径、缺expected SHA/reader关闭、xunit2 record_property、退休后query_ref，均独立记录，不当产品失败。额外--strict旧Any错误不是配置CI门，实际配置mypy绿。Windowsbrace/CIM沙箱错误改显式文件列表/正常OS只读查询；删除前每文件exclusive open检查，无当前匹配进程。完整过程见Git历史及R2/R5收据，不隐去费用/timeout/truncation风险。

FMP真实402只证明套餐边界，不是下载成功；未实测现金账单硬限额不冒称支持。SW无remote、SID维护执行分支，邻仓owner WIP和Dayu外部限制仍真实，最终Git核对待R5。不为这些状态重造人工签收。
