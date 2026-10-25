# A01/A05剩余共因：局部原文流与几何证明

## 状态与确定事实

这是本节点的**下一实施项**，尚未实施或验收。不能由206项工程测试通过关闭A01/A05真实目标。

真实资料：药明康德FY2025年报SourceRef SHA `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`。生产SourceVersionReader验原件，249页全部读取；当前原件/目录库/配置无改动。变化分页计数在最终方案可被正证识别；第13→14页的page_neighbour终于被实际调用一次，拒绝原因是`CONTINUITY_PAGE_COVERAGE_UNPROVEN`。

`real-native-context-afterlocal.json`记录coverage_complete=false、unique=true，unproven_pages含11/32/108以后多页，**不含13/14**。代码`narrative_reading._understand`把`parsed.coverage_complete`直接映射native_scan；该属性同时受任何deferred_table_pages/opaque/errors影响。由此发生“别的页金融表格未完整提取→当前两页原文流均不能被证明”的耦合。此处不能简单把partial改complete：目前泛型errors、页读取和文档整体状态还承担真实漏读保护。

同时两个真实端点的column均为None。当前物理校验在coverage拒绝后才检查column，因此**尚未实际观察到第二项拒绝**，只能写潜在下一约束。不得提前断言仅修coverage就可通过，也不能将None硬填0。当前完整模型输入仍缺Chemistry父级，A05保持OPEN。

**解析维度已进一步实读冻结：** `parser-dimensions-next-node.json`由相同SourceVersionReader原件生成：page_count=pages_read=249、errors=[]、opaque_pages=[]，但overall_coverage_complete=false，存在deferred_table_pages；第13/14页共62原始unit的column全None。该回放只parse一次，work569,544/16M，配置/目录库前后稳定。现在已能确认本例global partial由deferred_table_pages字段触发，而不是原生文本未读。进一步代码调查发现该字段直接取自geometry_session.deferred，名称未必准确描述全部延期用途，必须核对实际意图；不能提前宣称仅金融表增强，也不能据此给其他失败类型放行或宣称lane已知。

## 分层职责与实现边界

1. **解析/来源观察owner**负责正面证明哪些物理页的原生文字块已全部观察，区分文字扫描、金融表格增强、版面增强三个维度。先查parse_pdf_bytes和DocumentStructure的pages_read/errors/opaque/deferred实际生成路径；泛型errors若混合失败类型，先在已有解析结果扩展有类型的瞬时观察，不能按错误字符串猜。不要增加授权、签收JSON、身份库、任务库或第二份原件。
2. **NativeSourceContext**借用一次已观察的页覆盖和物理证据；当前页不完整时仍拒绝，另页未提取财表不应使已证明的当前页失效。不得仅因页不在unproven_pages就推定已读完整；必须有来源owner的正证。整体coverage_complete仍准确保留partial。已有SourcePageFlow与同budget/context复用，避免另造并行状态。
3. **layout/geometry owner**负责column/lane正证。先读现有layout_hints.columns及geometry_intent/native frontend；它目前没有把“无column gap”当成已知单栏，这个缺省不能直接升级成安全。只有完整源观察确实证明边界区域/页面的单栏或对应栏位时才输出已有lane字段；数据不足仍unknown。优先从已有native view/按需精细几何中取得，不重跑全文PDF→MD，不改消费者猜测、不按公司/页码开特例。
4. **sections**只消费来源证明和原生编号/缩进，在现有树中保留编号业务→bullet服务→roman事实；不得自己认证页面可用性或把结构端点当业务支持。**reading/compiler**只消费逐target的context和物理refs，不扩大8原始unit/4block/2048字符、112span、16M work上限。
5. 原有`decision_inventory`的实现SHA闭包必须包含实际变动依赖；新增helper若不在旧闭包，集中补入。旧缺项缓存须失效；原文/locator保持不变。没有摘要重算需求时不得重发旧付费请求。

## TDD与实施顺序（一个工程大节点）

### A：冻结能复现的来源正反例

- 中性完整原生扫描、三页资料，第3页仅金融表提取延期，第1→2页业务list有完整源观察与显式已知lane：当前整体partial保留，但局部上下文应能成立。
- 把延期改成第1/2页的真实原生文字遗漏、缺页、截断、未知错误、无法证明覆盖：拒绝连接。表增强延期与文字遗漏的边界必须取自解析器实际语义，不在测试编造有利旗标。
- 原生页视图/精细几何证明确为单栏的正例；双栏、相互穿插栏位、未知几何、表格跨栏、页框/rotation不一致、相同bbox但异source的负例。缺少column本身不等于有单栏正证。
- 现有未知column/局部无覆盖的负例保留；若旧测试混淆维度，先记录原断言的真实含义，再以更精确的负例和新正例约束架构。不得改断言来迎合实现。

### B：在单一owner补来源事实和最小接线

- 先实现解析结果/观察的维度区分，再接一次共享NativeSourceContext；文字、table、geometry状态独立，不扩大下游权限。
- 正证几何仍走现有producer/按需请求；请求在单一预算下预检并计费，页/区域/字节/超时上限不变；无需资料复制、下载或模型调用。
- 集中运行相关source parse、native continuity/physical observer、section ancestry、预算与cache测试；Ruff/mypy。不要反复跑全量/超时检查。

### C：真实资料、泛化与独审

- 同一SourceRef完整重放；直接断言第13页Chemistry原始head/intro作为第14页D&M/TIDES各相关roman事实的祖先、citation context及实际任务成员，不能由另一任务中的Chemistry名字替代；Testing/Biology不能混入这些任务。
- footer/header仅作为结构见证，不能进入模型support；同一页边物理发现一次，context各自有界；真实源字节/配置/目录库/源码前后稳定，无原件副本。
- 当前10个已通过来源断言和A13具名确认原文仍可在实际输入中找到；对年度14项做新独立复核后再改评分。跨公司/跨市场布局样本至少一个未参与修复者，不依赖W18未交付新代码。
- 独立agent审查最终源码/实际modelview/预算与清理收据，范围内问题全修；原文流和A01/A05真实目标通过后，才按配置做新正式摘要、paid cache恢复及RF实际采用。工程绿不能代替这一内容节点。

## 完成定义

本followup结束需同时有：所有负例仍有效；真实A01/A05任务父级闭合；source/table/layout三维不再相互冒充；旧通过项保持；缓存身份正确；独审完成；正常提交推送与精确CI。若真实lane仍无正证，保持OPEN并具体记录缺什么源观察，不改成“等待人工批准”。

## 独立架构设计核对

[下一节点设计独审](next-node-design-review/README.md)绑定8a258b93的13源码SHA，仅设计审查、未实施产品代码。它确认原生文字覆盖与几何请求延期须分维度，现有多栏接线已存在，单栏尚缺正证。缓存闭包已含reading/pipeline/adapter/layout_bridge；本次若改narrative_document或layout_hints的入口/columns，需要加入实际源码哈希，而非重复已有owner或只加版本号。见同目录source-hashes.json。
