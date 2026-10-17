# C节点：只读复用与统一来源事实投影

状态：实施前细则；承接母PWF，不另起项目。2026-10-17。

## 实测问题

正式摘要的只读登记预检三例均未付费、原件/配置/生产DB保持，独立Temp均恢复。CN/US被测试工具的manifest语言精确比较拦住，分别实际zh-CN和None；正式narrative_batch早已有locale归一及SHA验证后的原字节语言检测。这是重复门禁，应删除，不能伪造或覆盖实际language。

HK原件实际上已登记且SourceRef/open可用，但缺登记身份/期间/日期。已有ROOT核实的官方descriptor可经公有record_source_facts以真实locator/SHA绑定记录在owned catalog，不改raw或capture，不伪造HTTP receipt。Temp已确认记录和幂等，describe_version能见正确事实；query_local仍在读取事实前按旧目录实体筛掉，导致假not_found。这是读查询与事实投影脱节，不是需要再下载或再审批。

## 所有权与接口

- ROOT：CWP source_reader/resolver及专属来源事实回归；母PWF、实际集成与发布。
- 内部工具作者：仅phase_c_readonly_source.py、tests/test_phase_c_readonly_source.py与其独立子PWF；不改source runtime、母PWF或作者外包树。
- 用户已派发RF/FF两卡：保持独占各自worktree；本节点不编辑它们。

不新增事实数据库、许可文件、下载provider、语言分类器或identity registry。沿用SourceCatalog.record_source_facts、_source_metadata当前事实投影、原issuer alias index、SourceRequest、SourceVersionReader与正式batch准备入口。

## A/B：先反例、同一责任层修复

1. 测试工具移除query_local已负责的issuer/kind/period/asof重复manifest精确比较。保存实际manifest、SourceRef与原件SHA验证；locale/en-US与None应交正式语言owner处理，真正错误issuer/period仍由query拒绝。未知日期保持原source资格，不写成已知。
2. 构造独立湖：任意目录名下的真实合成原件，公有SHA绑定source facts登记真实entity与期间；先证明describe能见事实但query失败。断言正确entity可找到同SHA原件、错误entity/市场/期间及历史asof仍拒绝；目录名不能冒充已明确来源事实的权威身份。
3. SourceReader与SourceResolver两入口先获取同一当前可见metadata，再交唯一实体匹配owner。匹配使用已明确display_name/canonical identity和原alias index；无新权威实体事实时保留旧兼容回退。不得每层重复加载/扫描，禁止将新正确名字与旧错误目录名一起无条件当真。
4. 仍保留原件真实字节SHA、实际根/配置、来源状态、期间/asof与严格引用闭包；不靠去掉全部身份过滤获得绿。目录只负责定位，来源事实负责身份。

## C：真实复用、摘要与恢复（一个集中节点）

1. 修复后重新三例registered_readonly预检，先验证CN/US正式language准备；HK仅在owned catalog以已有可核对descriptor和真实证据locator调用原record_source_facts，再走公共query/open。真实事实不足单列NOT_RUN，禁止补造。
2. 沿唯一runner/当前purpose配置/同一母费用账做原语言正式摘要；先看实际选材和required_business支持，不满足则0POST。保留已有授权，不创建新许可。
3. 公共read、同run/crossrun0额外POST、激活前中断恢复、原件/策略变化拒绝，费用unknown不归零。缓存恢复沿原Store/outbox，不另造管理器。
4. 来源/语言/身份回归、已有reader/resolve/事实回归、实际三源只读链集中验证，独立agent审最终源SHA和质量；全部确认问题修复再提交/推送，核精确CI。测试原件/根/配置/测试目录前后核对；只留简收据。

模型token/费用预算保持已配置累计200万/$20；本机16M工作计数是另一责任层。工程选材B已通过，不代表本C摘要/恢复/盲样本完成。
