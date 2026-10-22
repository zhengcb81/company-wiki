# R1 独立根因诊断记录

结论：四路26问题全部有根因、工作包与测试；未实施产品、未宣称修复完成。15P1/11P2；11根因中RC11为既有DU11-R2携带缺陷，不增加reviewer问题数。另COORD-OBS-001是有证据的记录表示问题。机器索引只是诊断。

## 共用责任链

|根因|责任/实施包|已证机制与边界|
|---|---|---|
|RC01|FF→RF W02|closed operation DTO缺local_preparation/blocked，nonzero有效business stdout被transport先丢|
|RC02|FF companion/RF W02|被请求但未dispatch的companion硬标not_requested；无真实ET账户拒绝证据|
|RC03|CWP source W01|identity-only发现、先集齐再登记，17个旧历史原件触16限额且零进展|
|RC04|CWP temporal W01/W02|legacy元数据未知；已有可靠availability未接prepare资格，不能重造发布日期|
|RC05|CWP reading W03|真正initial0.8无reading_context，现成0.9未正式消费验收；遗漏与跨分部拼分母|
|RC06|研究 W06|已合格Q1与相邻注释/最新H1未进入事实/目标/模型库存|
|RC07|研究 W06|45条件率/压力幅度无独立校准，RPO/子项/交付取消时序桥未完成|
|RC08|RF target W05|typedratio可误带CNY；旧schema非空string已有dimensionless可用|
|RC09|RF target W05|custom声明允许但native只company/单segment；需有限同成员scope|
|RC10|ROOT验收 W07|恢复/失效/峰值未跑、latestcause手写旧值、网络记录缺、复合locator不可机读|
|RC11|CWP runtime W04|实验retry混同job/paidattempt/finalslot；激活遍历已partial0记录；paid单pin限制另一路径|

## 已排除的误诊

最新H1末次原因是local_candidate_limit（journal21:20:22），不是早次publication_date_unknown（21:04:25）；旧2025H1已可信scope排为not_relevant。不能继续只升上限或当不存在下第二份。scopehint用于排序，不充期间事实。

SourceRef根映射与RFcontext消费已经实现且storage路径审查PASS。跨根行为需要反例和后续SNOW实物复用，无需在FF/RF新增目录分支。0.9/B2已有组件与回放不代表本轮0.8真实运行已验收。

c4把测试和生物学两个“超30%”分母拼成无分部结论；专家视觉复核p14确见两段业务标题。旧RF只引用CRDMO机制而未引用c4，不能编其已改变收入金额。c1actual/2026plan、c6总口径47.64%仍要修语义。新0.9也须逐claim回原件，不能默认其一定解决。

年报p183视觉复核确见Testing/Biology全时段确认；discontinued合并格不能拆。Q1全年TIDES约40%与最新H1约45%目标属于不同日期信息。97baseline/105stress、85引文、3952numeric leaves、1276独立比较零算术错保留；45未来率/6暴露/2冲击未校准，研究缺口不能改成算术bug或靠硬拒所有假设解决。管理58500–60500范围是比较锚，不是应填Base。

COORD工具1616rows：194OBSERVED/13UNAVAILABLE/1283UNVERIFIABLE/126MISMATCH；126全json_pointer_unresolved，封存报告“/parameters; /segments; /operating_research”这种复合locator导致，不是126raw/事实错误。2.67MB数字ledger超过默认1MiB实读cap，独立process实际全量复算另有证据；不调无限上限、不改封存报告。新attempt每evidence一个有效locator。

## 时间资格的最少操作

已有source_availability.py验证canonicalDownloadReceipt同SHA/size/mime/provider/HTTP，公开receipt2.2，不重hash；RFsource_clock已有prior_verified_capture/primary_archive消费，CWPqualify仍publication-only。优先接既有proof。没有旧proof时，可在现有source-owner verifiedopen真实UTC/同rawbuffer产生小provenance/receipt，增加current_verified_open basis，仅证明实际当日及以后，published_date仍null，过去asof仍失败。RFclosedbasis需要W02小兼容；禁止把该观察伪装HTTPcapture。若现有writer无法小接，则报告具体接口并用一次必要有界官方验证，不能声称全部legacy已经可qualify，也不能靠mtime/裸firstseen填日。

## R2去留比较与决策

新multi-operation框架必须统一caller/retrycandidate/AUTOretry/finalslot多边接口；当前功能默认OFF且不再为CN两条遗漏付费，扩大付费状态机会增加验证成本。移除新增coverage补写派发，同时修原生finalowner解析即可解决已证activation0→positive冲突并保留普通恢复。因此W04推荐退役入口，保留旧partial/merged结果和原账，按实际verify所用SUCCEEDED结果证明最终结算owner，不能按latest/跳0/error_code为空猜。

历史已mergedfinal、首笔0+次笔未结算应零POST恢复。多pin未完成重放没有精确身份不放宽len(paid)==1，保留具名不可用且输出/收费可读。真实存在的fallbackfinal若无合法slot需具体盘点并保持namedunresolved，不能改旧0或伪称全部历史恢复；只有必要时在现有runjob补最小slotreceipt，不新库。普通singleoperation paid后激活前是W07真实必验，不受退役免除。旧AUTO路径不存在，历史dirtyfingerprint不能当干净可重放源码。

## 已有计划与owner

R5 a5214bda已受影响195项/7047+24skip/142smoke/独审并随feaef48a推送CI39682544340SUCCESS，不重做。ROOT新增0622f242是初审/R2/CI索引文档提交，不能回写initial实际版本。ROOT最新预检FFtrackedclean、RF三assuranceWIP/output保留；早期普通gitstatusworktree错误由escalatedGit已解，不新增权限审计。runtime可复用既有CWPworktree，ROOT主工区source/catalog、runtime工区automation，避免batch冲突。

NVDA旧24issue/14根因/7包、旧unknown、company-pool campaign与原八家目标都保留；药明康德修复复验后药明合联→SNOW，行为版本变更重置clean，不把开发三源当新holdout。

## 证据与限制

完整每issue映射在../diagnosis/coverage.json，根因源码/封存proof在root_causes.json，定点同步旧SHA在baseline_files.json。专家没有产品TDD/真实E2E、付费或下载；已有reviewer最小probe/R2四RED一PASS与专家源码/视觉核对是诊断证据。产品修复仍由ROOT按包实施，外部账户/缺源/预算只在真实发生后标external_limit。
