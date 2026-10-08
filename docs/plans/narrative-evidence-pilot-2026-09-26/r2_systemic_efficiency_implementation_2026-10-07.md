# R2：按需处理整条链的系统性效率修复

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

用户追加要求：发现的效率问题系统性修复，不能只为当前文件打补丁。本细则属于全部PWF目标的R2，先写方案再实施；R3/R4/R5继续保留。原件与现有来源/版本/用户配置不丢，Dayu不改，IQS不动，不引入第二任务库或人工门禁。

## 一、已查实的责任混合

1. CanonicalSourceWriter新增原件后调用整个company_raw的scan_catalog；正式库23530文档/46606位置，一份新增TXT会连带整个根枚举、sidecar读取、位置SELECT和missing reconciliation。这是登记与全库发现混用，非模型速度问题。
2. 有限扫描初步修复只约束hash仍不充分：旧实现每次读取所有根位置，且为company_raw来源补URL会扫描外部Dayu所有meta.json。指定来源登记不能隐含跨根发现；兼容回填只属于显式全库盘点。
3. build_batch_events在worker前，为缺language来源打开完整字节并提取前5页确认原语言；select/verify分别对当前版本字节复核。语言探测本身有界，完整PDF解析在select一次；后续调查恢复是否重复做准备。不能通过删除SHA/版本/locator复核“优化”。
4. 现有metadata缺日期/身份或旧retire不能靠换fixtures绕开。旧capture与现行来源身份投影必须统一；官方同SHA验证已支持年报和IR，不能给legacy TXT伪造HTTP receipt。

## 二、职责与统一接口

| 层 | 只负责 | 复杂度约束 |
|---|---|---|
| Discovery | 明确的全根扫描、发现未登记/丢失文件、旧跨根元数据回填 | 仅用户显式全根scan执行；新增/复用不得触发 |
| Registration | 同一已配置根的指定原件/完整元数据组、统一分类/归并/SourceRef | 输入N组，只枚举所选原件及sidecar、SELECT其位置，不改未选记录/完整根水位；有限扫描不推断missing |
| Source read/export | ID/hash/身份/期间/公开日期投影，打开验真实字节 | 不scan、不下载、不解析整库，不暴露存储路径给消费者 |
| AUTO batch | 显式SourceRef批次、一个Store、已有bounded process/模型并发/费用与outbox恢复 | 只准备/处理本批；同run恢复不重复模型/终态正文；未知费用保留 |
| Selection/final | 一次文档解析、精选business evidence、原语言摘要/短final | 不永久存全文MD/重复正文；纯流程0模型；final/scratch/持久增量有界 |

保留scanner既有归并/事务算法作唯一事实写入实现，增加独立有限登记边界，与全根reconciliation分离；不复制一套“快速scanner”、不按公司/样本写特判。canonical所有新PDF/TXT/JSON入口统一使用有限登记；已有raw复用仍0登记扫描。

## 三、实施顺序（TDD）

1. 写出并复现有限登记反例：未选文件真实删除、另组byte/mtime改变、陌生/空/越界范围、全组sidecar；全根盘点仍识别missing。已有7个新用例从缺接口RED到GREEN，增加全组/不walk保护后8例绿。
2. 抽出有限发现/登记scope责任模块，统一服务/CLI/canonical caller；明确无锁内二次锁（canonical已有catalog锁），不新增许可flag。避免finite路径加载外根URL和全根SQL，为这些系统性成本写计数/调用边界断言。
3. 保留v1/v2 root adapter语义：宣告adapter不得换reader；有限适配器若尚需枚举，记录限制，不能冒称整个外根也O(N)。本次company_raw输入具备精确路径，做到有限枚举。常规全扫不变。
4. 按SourceRef查询、摘要准备、终态resume调用图复查重复成本；只对实证热点写RED与实现，不盲目加持久全文缓存。若需要保存language，仅保存来源SHA绑定小事实；不凭market猜语言，不用旧语言掩盖原文变更。
5. 生产元数据修复走同一事实入口；旧retire有明确原因且官方同SHA时经restore审计。ET旧TXT只登记真实复用/legacy_unverified，没有原下载凭据就不造receipt；源文本原样，无翻译。
6. 一次集中责任包：有限/全扫描、canonical新建/重复、transcript未知日期/无翻译、adapter优先级；真实两PDF公共CLI及独立TXT调用链。最后生产正式批次/consumer/ref/search/resume统一在R3，不在每helper新增验收门。

补充实证：三种adapter均在enumerate时用read_bytes算原件SHA，但dispatch丢掉该SHA，scanner再hash；adapter新增统一relative_paths/compute_hash=False发现模式，真实哈希由SourceManifest唯一负责，默认直接枚举接口保持带SHA。Sidecar宣称SHA的校验移交登记后仍须拒绝不符；已发现size/mtime复用会绕新sidecar不符的真实RED，已修复并保留反例。company/directory/dayu三种legacy根和三种配置adapter使用同一纯source_group_scope选择组，原根规则保留，不改dayu-agent。

AUTO调用图又发现batch准备/收尾反复list_jobs全任务库，以及终态resume启动worker后立即停止。下一TDD给Store增加按event/job IDs在SQL层选范围，foreign running仅exists查询；同run全部终态时0子进程启动。保留原文打开SHA、metadata/policy输入hash与outbox恢复，不删除正确性校验、不加缓存全文。

用户追问旧canary配置说明简化是否遗漏：确有遗漏。现场510B runtime_policy.json仍为canary-2026-08-10，v2_scan_shadow/v2_resolve_active/shadow=true但legacy_bridge_enabled=false；新有限登记已按root.adapter_id而非旧全局开关选实现，读取仍受该旧配置影响，旧无assertion文档的capture字段被隐藏。它是灰度切换控制，不是用户目录权限。不能只补当前年报：盘点所有运行入口，在隔离库复现相同旧snapshot和真实legacy metadata；用统一退役入口、当前配置/来源断言规则迁移，保留已生效断言、原件SHA/版本/撤回状态、policy变更可检测性。生产变更保存小型旧配置审计、精确旧SHA前置核对，使用现有catalog操作锁，不恢复大型备份、不按样本绕过reader。历史迁移工具可只读解释旧记录；不重新启用canary或人工签收。

全库核对发现16条active/verified断言属于旧canary，另2条legacy/verified、4条candidate。因此不可简单删除JSON：旧默认v1会隐藏这16条。迁移目标为schema2 steady快照，只留根配置hash/更新时间/自身hash，不再有六flag、epoch或cohort开关；当前读取合并已生效active及legacy verified（排除shadow/candidate/rejected），断言字段优先，旧capture补充缺项，保留元数据冲突诊断/真实字节拒绝。全根发现按每根adapter选择，有限登记相同；旧schema1仅为历史工具/测试兼容，生产明确CAS转换。先写正反例：无断言旧文档可读、active断言优先、shadow/rejected不可替代、跨根/不同SHA/retired仍拒绝、相同CAS重复无写、变更快照pin仍检测。不要把v1回退当作简化完成。

## 四、验收与效率证据

按行为计数验证而非脆弱秒级硬阈值：新增1组无全raw walk、无Dayu元数据读取、SQL不返回未选位置；原件复用0scan；未选来源整行、原件SHA/mtime不变；完整scan仍发现missing。报告同时记实际时间/输入组/读hash次数/生产DB变化/派生字节，比较的是相同责任范围。

正常commit/push及精确代码CI；生产改动与测试区分，测试根原先absent则结束清掉。没有新paid权限/费用增量，具体生产请求预算预检后再处理必要额度。

## 当前状态

in_progress。系统性代码2cad90d已推，精确CI37582474369全部步骤success；集中202项/64.81秒绿，全部改动Python Ruff、新纯scope/登记mypy绿，真实融资PDF公共register及三配置provider本地HTTP/子进程恢复完成，付费POST0。14隔离测试根恢复absent，生产DB/两配置SHA保持。现场canary与默认steady收敛现在由优先级更高的[G2-00](gate_simplification_reaudit_2026-10-07.md)接管；G2还先处理无效pin/AUTO故障/旧CLI和工程工具，随后回本阶段有限登记/恢复生产来源及真实请求预算。生产metadata/正式运行R3未完成，不据源码绿标R2完成。
