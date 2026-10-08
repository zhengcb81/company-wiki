# R5：当前入口、历史临时材料及最终交接

**Status: complete，A/B实质审计与正常发布完成。** R2/R3正式生产与全部验收已完成，用户已批准220000 tokens/$10；[完整最终对账](r5_full_closeout_2026-10-08.md)覆盖原全部家族。[R3清理](harness_lanes/results/r3_owned_cleanup_2026-10-08.json)补本次94840547B临时副本，原件/final/AUTO保留。下方旧“待R3/增额”仅当时施工顺序。

## A. 当前入口与零费用清理（本轮）

1. 以当前Git、生产应用/精确CI和预算收据重写task_plan/findings/progress及all_pwf实施单，删除重复“当前状态”和历史暂停/待并线指令。历史全文固定链接到本次修改前已推送6dd5601，不另复制大归档；保留全部计划家族的证据或明确剩余项。
2. 当前文档只保留一个Next Step，列清R3未执行、必要token增量未获答复、未知公开日与来源资格、单batch资源限额、生产AUTO与唯一work-dir、当前消费者/locator/恢复/footprint的大节点验收。README/完成证据/历史交付卡顶部引用同一入口；不以外包或隔离绿替代生产final。
3. 只读盘点五个g2未提交根及已发现的cw-retire-r1、旧pilot、slow-canary-drill：原生路径/大小/类型/无reparse/是否tracked，结合PWF文字和Git历史辨识责任。未明文件保留，不因叫tmp就删；pdfs原件区、外包交接树、owner WIP不触碰。
4. 可删除根必须证明是已收口测试夹具/中间物，无当前进程占用、唯一原件或未保存恢复/usage事实。逐项清单和必要小测试结果先持久化，再原生Remove-Item -LiteralPath；实测字节不当allocation承诺。pilot历史预算库及账目保持，未知费用不清账。处理结束核原件/config/生产事实保护。

### A 的实际结果（complete；B实质审计亦已完成）

八个精确owned目标已删除，共119913476B、1123文件；26个原件/config/原侧录及旧pilot保护文件SHA、大小均保持，生产DB size/mtime未变。唯一原件删除0；canary年报测试副本与公司目录原件SHA一致后只删副本。历史pilot账本及unknown费用、tracked历史收据、tmp/pdfs、外包交接和owner资料保留。

当前三PWF与实施单已改为唯一当前入口，120份历史卡加导航；原文历史固定在已推送6dd5601。新增R3A后当前129份计划文档的目录与链接检查作为导航数据持久化，不构成新门禁。A的纯文档/清理收据没有源码变化，复用6ae7ddc的精确CI37705927320全绿，不重复长测试；后续R3A源码及联调测试分别观察自己的精确CI，不借用该绿。

- [归属与保护盘点](harness_lanes/results/r5_temporary_ownership_2026-10-08.json)
- [实际删除与保护结果](harness_lanes/results/r5_owned_cleanup_2026-10-08.json)
- [当前计划目录与链接结果](harness_lanes/results/all_pwf_inventory_2026-10-08.json)
- [正常发布后的跨仓只读核对](harness_lanes/results/r5_readonly_repositories_2026-10-08.json)：A提交117dbaa；CWP/RF/FF/SID/ET实时远端一致，StockWiki无remote且独立quick-scan已推进9f9e0af。历史消费证明对应04dfc51，R3需用当前已提交版；owner文件保留，未介入独立项目。
- 后续[R3A](r3_current_material_read_implementation_2026-10-08.md)complete：RF main c672a5e已推/精确CI绿，SW master42fba06本地合入；CWP联调测试f0ad6b9已推、精确CI37712551891全绿。自己创建的两个已合入工作树91161217B副本及精确测试临时目标已清，见[R3A清理](harness_lanes/results/r3a_owned_cleanup_2026-10-08.json)。副本字节不计入S5/S6生产净释放；生产原件/DB/26保护与342 owner保持。

## B. R3之后的最终验收（已通过；检查点34141d3d已推送/远端一致/CWP干净）

1. 检查实际已提交的R3请求、原语言业务final、真制度零模型skip、引用回放、NarrativeRef/reference/read/search/exact、RF与StockWiki当前已提交消费者、相同run零新POST/不重复费用/不重复对象、真实DB/WAL/对象/scratch测量。未知公开日期不获as-of资格，不要求捏造日期才能消费原文。
2. 按完整PWF引用家族核证据，不复活退休writer/Gate0–5/人工review/许可/私有权限，不将S7的29/33解释成33/33。R4不做收益不足的对象化已是证据决策，不以删除原件换完成。
3. 各仓当前HEAD/远端执行分支及交付归属重新只读核对，保留owner WIP、SID简易版执行分支、SW无remote和Dayu外部边界。正常提交/push；纯文档复用精确源码绿，不重跑长包。
4. 此A/B大节点仅做文档链接/状态一致性、事实/归属账、真实剩余测试和发布检查；不加helper复核、签收或每commit pytest。

## 输出

- 当前三PWF入口、实施单、README/完成证据及交付卡导航；历史固定Git链接。
- `harness_lanes/results/r5_temporary_ownership_2026-10-08.json`、实际清理/保护收据。
- R3后完整requirements→evidence→当前结果表；未完成/未知明确保留。

**Next Step:** 无必要施工剩余，检查点34141d3d已正常发布并验证远端一致/CWP干净；仅发布此最终状态后关闭原目标，不重做A/B、不新调用模型。
