# W07 真实生命周期与公开 RF 读取：非作者独立复核

**结论：本次工程生命周期通过，保留如下证据边界；不签收内容正确性、完整 RF 公式流程或预测质量。**

审查者 /root/r1_w04_summary_runtime 未编写 W07 工具，未执行这次付费过程。基于发布 CWP755e87cd85de7ca02bcb88b8e34f79c35f3763f3 的7个实际工具/恢复实现文件、19件封存包 SHA、真实 AUTO 的只读 SQL、真实对象字节、独立命令捕获复核；不是照抄 controller.status=passed。可复现检查器与65项有限断言见同名目录 check_readonly.py/checks.json。

## 独立核实的关键事实

| 检查点 | 直接证据与结果 |
|---|---|
| 发布版本 | 7个工作树工具/恢复文件 LF字节与755e87cd Git对象一致；CI39847355377后续成功收据绑定同HEAD。未重跑7088条单测，也未把旧CI in_progress快照当成功。 |
| 实际配置与输入 | 已冻结 generation 为 DeepSeek deepseek-flash、配置端点 api.deepseek.com、8192输出、selector0.9.0、reading-model-input/5、narrative-model-request/6。真实HTTP body73560B/SHA ca04ce5a…与两次预检、POST和恢复前预检一致；旧预检81880上界超60974余量，0POST，不靠缩小输出或估算器放行。 |
| 一次真实付费 | POST观察恰1且无拒绝重发/输入变更事件；原生唯一 reservation 为known；持久化4478B响应 SHA68ae4656…实读匹配，HTTP200/model及usage16405输入+924输出=17329。配置价代理逐项重算6701microUSD一致，非发票。 |
| 真正的重试恢复 | 实读 AUTO：付费summary attempt d49c896b…为 retryable/IO_TRANSIENT，后续633d7c1a…为 succeeded，attempt1→2、fence6→8，lease哈希不同；观测pid5052→15192。同request/paid pin/response/费用/冻结generation，原生 _recover 与 replay_response 均真实执行。故障是测试本地付费落盘后的注入，不是供应商报错。 |
| 激活恢复 | 实际第二段返回activation_pending/exit2，随后同run exit0/completed；catalog 当前可见 artifact narrative-7396…实读415965B/SHA d4aaddb1…，与reservation最终output一致。 |
| 新run缓存 | 新run before.run=null且无reservation；cache后仍无reservation、0token/0费用，generation_status=reused，实读与前述完全同一artifact。cache结果scratch_peak0；当前cache工作目录不存在。**没有单独的调用前目录清单，因此不能独立证明开始时工作目录为空。** |
| 公开RF读取 | 真实安装路径 .agents/skills/revenue-forecast/scripts/narrative_source_preparation.py 由透明文件输入适配器运行；输入冻结SHA一致，capture exit0、stderr0、stdout418917B未截断，原stdout与便携副本SHA953da486…一致。schema revenue-narrative-context/1，96spans。 |
| 来源与状态 | 原年报PDF实读hash7f1431d6…/1608226B匹配SourceRef，未复制或重下载。selection partial / coverage_complete=false / quality needs_review；249页已读并不等于1413候选全部纳入，模型任务完成也不等于全文业务覆盖。 |
| 用户预算与未知hold | 独立按母账DB+attempt去重：1561352预算charged tokens/631959microUSD，2M/$20上限未变，4项新unknown和7项旧baseline hold保留。公司100k→150k仅ROOT自定较窄额度重分配，单请求仍100k/$余量不变。 |
| 封存索引恢复 | 初始manifest SHA ee087537…/639项及被影响旧索引SHA55ab1ff4…/3763B重新独立核验一致；新attempt索引保留全部旧引用加新run。没有重拷或重验整湖639个正文；“639全部匹配”全量核验属于ROOT封存恢复收据，独审只重核manifest和受影响索引。 |

## 不能淡化的反证与限制

1. **公司56355tokens/16421microUSD不是全为已知实际消耗。**其中已知24184tokens/9693microUSD，另旧MiMo unknown预留32171tokens/6728microUSD；本次W07已知17329tokens/6701microUSD。母/公司预算数字包含未知hold是正确的保守账义。审查器初版假定公司全known，被原生unknown行反证；改正的是审查器错误前提，未改任何原账来适应检查。
2. 旧CI快照确实为in_progress；之后独立读到同HEAD的success收据。原封存索引也确曾被追加，后按初始SHA恢复；这些过程记录没有被抹掉。
3. 没有cache工作目录调用前清单。只签“新run/no reservations、cache后目录不存在/无scratch”，不把“初始空目录”签成已实测。ROOT已确认同样边界，无需本轮重跑付费。
4. 选择仍partial，质量needs_review，RF消费标记not_consumed。已公开读取≠确实进入native分部参数/公式≠预测正确；本报告不替代四路内容、数字与买方模型审查。
5. 本轮真实模型只覆盖这份A股年报、配置中的DeepSeek。MiMo/MiniMax、其他文档、港美股新公司不由本次结果代签。

## 下一步（已有大节点顺带留证）

W06继续把实际使用片段绑定参数及native分部公式，回原件核数字，并完成四路质量审查。下一家真实缓存验收，在现有调用前快照顺带记录目标cache工作目录 exists 和有界即时条目摘要；不新加人工许可或小节点审查。本轮不重做付费。

## 操作与清理

审查只运行自有只读检查器，SQLite URI mode=ro + query_only；未构造会迁移DB的store，未调用收费模型/下载/API，未提取密钥值，仅核配置文件SHA。未改native状态、原件、作者attempt、CURRENT_STATUS或产品源码。仅新增本报告及小型证据；未创建临时scratch、无副本湖/数据库备份需要清理。ROOT拥有提交本报告与后续发布。
