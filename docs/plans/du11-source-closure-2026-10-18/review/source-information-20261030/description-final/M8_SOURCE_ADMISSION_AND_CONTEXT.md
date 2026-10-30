# M8：共享来源准入、连续性与主体前提

状态：根因调查/TDD准备；未签代码、源召回或真实摘要通过。唯一入口仍 CURRENT_STATUS.md/json。M1–M6已发布局部成果保持，不重复旧付费摘要，不以本步替代完整RF公司循环。

## 固定输入与问题

使用[M7原冻结结果](m7-frozen-source-regression/README.md)及其本地normalized快照，不再全PDF解析。华利r2、Berkshire r3是旧结果对照，不能覆盖。已确认重要原文不是PDF提取丢失：全部20支持集合存在normalized；风电装机、保险份额等在候选前被context_only/no_independent_business_support排除。另有支持轴已是support，相关性轴却为False，造成二次拒绝。完整逐级调查须区分业务准入、连续性、排序/任务上限和实际work消耗，不能只凭计数改词库。

GEICO正文we/our缺主体前提、华利“活性。”独立入选说明原字节quote还必须带完条件/归属上下文。问题发生在共享源owner，不能让RF补猜主体、让FF重新下载或用模型改写修复。

## A：一次根因设计与红测试

1. 分别记录每个重要冻结正例在normalized→候选→selected→task→source-card的状态、reason和上下文；身份、行业/财务口径是context，不强求各产主卡。区分真实运行与fresh-work重放，不能误报作者snapshot序列化故障为产品parser失败。
2. 明确三个责任：来源是否是完整可读的有意义叙述及归属，来源经营/行业相关性排序，状态/数值可不可以作本公司实际事实。不能把未知实体、未命中动态动词当“无有用内容”，也不能把读到的行业/客户文字提升为issuer事实。
3. 中性TDD先红：未知命名/产品的中英静态结构、子业务/客户/行业事实、条件计划、数量/订单/因果及其否定；同义跨语言对照。负例：纯三表结果/数列、规则模板、问候套话、空泛愿景、问题内假设、无头表格，均不能借邻段证明。新能力不能依赖华利、GEICO、PacifiCorp等公司词。
4. 连续性测试：上一页未完句/下一页句尾、跨段代词/子业务主体、中文条件、英文计划/限制、问答角色、明确换主体/换QA阻止过度合并。缺上下文要保留未解诊断，不能静默升格或全卷串联。

## B：共享owner实施与免费回归

1. 以A的实际证据确定最小共享接口。来源角色/完整性和业务排序复用一次prepared assessment；不新增第二事实库或公司特例，不在消费者重新扫描。明确非经营/财务/模板排除保留，但上下文财务数字的经营解释不能仅因finance词出现整段误杀。
2. 连续性/引用窗口由源引擎负责，support与context保持原ID/locator/raw文本及边界，主体/条件不被当新的投资结论。原文不修改，summary quote不人工拼写。
3. 实际word/work扫描在现有统一budget内，预算不足须deferred/unassessed，不能被伪装为内容无价值；同输入同budget可复现。fresh-work与生产parse账不同的结果应明确限定，不据此轻率新增产品修复。
4. 新规则升级既有reading policy/digest坐标；旧immutable选择/请求/摘要/缓存按旧解释读取。禁止为了新结果匹配旧artifact篡改hash；显式/5仍是本主线quote方案，不擅改旧省略/4。
5. 保存红→绿日志。先受影响单元/集成和M7 normalized免费回放，逐事实检查主体/条件/未入原因；扩测仅对新失败或真实风险。不增加全量CI门禁或提高超时、费用、token。

## C：大节点独立审查后端到端

独立agent审代码、测试强度、边界与真实正负source结果，发现问题从共因修到0阻塞，再正常提交/推送并记录精确CI。不是每个小函数验收。

免费源阶段通过后才运行配置内有界/5真实rank：同一支持集合/主体/条件进入正式artifact；保存原付费response与generation，验证activation、被中断后的恢复、同run与跨run0重复POST。对正式结果独立逐条审语义/口径/归属，不能用quotecopy天然证明上下文充分。继续RF真实SourceRef读取→summary_use→参数/公式→native报告/snapshot，保留原非期次未知URL/pub且不编FY；完整原报告归RF。首轮已验本地M1–M6不能冒称M7新源也通过。

原件/config/DB/母账及RF外来3WIP/147output前后核对，测试临时目录恢复；不新建完整恢复备份、不改Dayu/IQS/Dashboard或外包工区。新问题/PASS证据回写本页和5个主入口，下一步维持单一。之后回药明康德W12新attempt→药明合联→Snowflake完整八步审查循环；全项目仍OPEN。
