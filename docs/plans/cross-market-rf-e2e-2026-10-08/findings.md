# Findings

2026-10-08 新任务。CWP 生产根 company_raw / dayu_portfolio / dropbox_stock / future_lake 由同一配置接入。RF 仓 main=7cf337e1，FF main=211a56ff；RF 三份 assurance 日志是既有 owner WIP，保持。RF 实际 runtime=4.1.0，五个来源运行文件 repo/installed SHA 相同（不存在所疑安装漂移）。EARNINGS_TRANSCRIPTS_TOOL 当前环境未配置，必须真实验证配置路径，不能冒称电话会已自动下载。

## 第一轮真实链路缺陷

- RF 客户端仅认 legacy capture_ready，拒绝 FF schema2 source_candidate；真实 CN/US 失败已留原日志。
- raw source reader 和 source builder 对原始 retrieved_at=null 强制 datetime 校验；前轮 narrative reader 修复没覆盖 raw 路径。原件和公开日不修改，null 保留，新的 local capture 使用实际 verified read_at。
- annual 请求省略可选 fiscal_period 与 canonical FY 冲突；仅 annual 的唯一 FY 可默认，季度不能猜。
- FF schema2 极简 pathless candidate 与旧 metadata-rich candidate 不同；builder 应接受确切 v2 shape，并从实读 manifest 获取身份/标题/日期，不伪造缺省 producer metadata。
- 六新增回归先6失败，四责任文件修复后69测试绿，定点安装4文件×2物理副本；配置不改。
- Dayu HK/US 下载在当前有限预算策略下不可用：MAIN 同请求直接 CWP ensure 得到 `adapter dayu-sec-cli does not support bounded acquisition`。先定位CWP adapter边界，绝不修改Dayu/取消预算来假装成功。
- HK年报可选language=zh导致no_local_match，去掉后CWP source query fiscal_year mismatch；公开日期/正文均有，需要进一步源元数据追踪。
- CN年报 source_url仍HTTP；不能私自改为HTTPS，需官方HTTPS实际验真后按producer source-facts机制登记。

## 第二轮原文与契约核实（07:17 UTC）

- CN 官方 HTTPS 实际 GET 得到相同原件 SHA 后，使用 producer source-facts 仅登记 source_url；原件、原始 retrieved_at=null 保留。FY2025 RF→FF→CWP 两次零下载复用已经成功。
- HK 年报 sidecar 没有 fiscal_year/language，query 返回 null 并导致 RF拒绝；执行 agent 实读封面/正文后，以标准 source-facts 登记 FY2024/FY2025 和语言，原件SHA不变，随后两年 source-preparation 均成功。不是目录差异导致。
- StockInfoDLSimple 将 semi/quarterly 都映射到 annual 分类。实际 688012 官方 POST：年报 category_ndbg_szsh 只给年报；半报 category_bndbg_szsh 给2026H1（1225482884）；Q1 category_yjdbg_szsh；Q3 category_sjdbg_szsh（本期未发布）。不存在通用 category_jdbg_szsh，它会被官方忽略而返回208个公告。再次真实联合分类 yjdbg;sjdbg 只返回Q1一条772B，证实可用。
- 分类回归先2失败/1通过；修复后 CN官方API、预算、适配器、latest分页四责任包绿。初次测试错误引用不存在文件导致收集失败，保留日志，不计通过；纠正实际文件路径后集中重跑。
- 三公司真实分部均有 mixed timing/presentation，而 RF只允许一种。新增仅 `modeled_as_recognized`+`direct_growth/direct_revenue` 的已确认聚合 mixed 描述，要求 aggregation_boundary+原确认政策引用，拒绝progress/lag/carryin和活动模型。先9回归失败，最终64责任测试绿；数值保持已确认收入，不再填 progress=1冒充单一确认政策。定点同步3文件，安装配置未变。
- MSFT 2026-09-02 官方 FY2027 segments/metrics 原稿为图片PPT，执行 agent逐页实际打开，不依赖无文本OOXML；两新分部、FY2025/FY2026比较及八收入流必须由独立 reviewer 复看。
- Dayu外部代码零修改。CWP旧dayu_cli_v1不支持bounded，ensure在provider启动前拒绝。SDK已有client注入，但CLI没有metadata-only/budget入口；本轮不能把网页补充资料算成Dayu集成新下载。完整桥接需CWP-owned预算transport+SDK边界另行实现，不能只加supports=true。
- ET/FMP真实精确fetch诊断返回 provider_entitlement_required；discover返回 candidate_discovery_unavailable。未订阅、未翻译、未调用外部LLM，不能声称 FF自动补电话会成功。
- SEC HTML在当前 CWP narrative worker不支持；US agent临时BS4解析与consumer capture分别记录，不声称worker处理过。季度/纯定性管理层目标不能偷换成年FY数值，以原材料旁表+data_gap保留。

## 独立审查实际发现（持续更新）

- HK reviewer已核38命令配对/output SHA、所有manifest artifacts/runtime SHA、69claims excerpt对原PDF页逐一重提匹配。
- 但文本语义绑定不等于excerpt存在：paid_social_stabilization反证使用259m vs264m订阅数，却仅绑定H1 PDF47收入表；需PDF6真实claim。
- NetEase H1+8.3%及竞争franchises被benchmark/行业/反证使用，但69claims零条绑定NetEase来源；需完整原文claim，不只是把source列入source_ids。
- customers维度写top-five6.5%/largest3.4%，未有对应披露claim。不能以strong validator green宣称全部事实证据已闭环。
- 上述为HK执行产物修复队列；待完整初审后执行者产新版本，独立reviewer复查改变的依赖。当前并发4槽满，向已完成执行agent发消息被工具thread limit拒绝；不偷偷超额并发或让reviewer自己改写签收。

- US独立逐页确认22/22官方PPT全部关键重述数值/互斥流/季度guidance正确，90manifest artifact SHA与42命令成对有效；manifest41count因seal finish在写manifest之后，按最终ledger计数，不当成数据错。
- **US P1输入数值错误**：8个敏感性name写FY27 growth ±5pp，但ratio维度percentage_point shock_value=5.0实际直接加减5即±500pp；应0.05。代码按契约计算，错误在输入单位语义，strong validator仅算术一致无法读自由文本意图。修复8项及sensitivity/confidence/report/snapshot依赖，新版复审；当前旧版不能称敏感性可靠。
- US72个未来growth rationale_support claims仅截各stream FY26基数，不能支持range/fade rationale；虽然未来值明确analyst assumption，需绑定完整历史growth上下文、实际需求/供给、季度guidance与外部benchmark，且CC季度与reported annual不当同口径下限。独立审查继续列完整定位。
- HK FY2025登记HKEX URL实际404，正文与公司身份/期间核对成立，但当前URL不能重证public provenance；reviewer只读查官方真实PDF与公开日/同SHA，再给producer修复建议，不能直接改旧raw。

- US consumer_cycle支持与反证绑定同一库存上升句；反证应为真实gaming FY27恢复增长预期且不外推Windows。enterprise_migration服务扩张不受license下降一句支持。四根季度falsifier与年度模型口径错位，需同口径年度条件或有原始季度阈值。
- HK独立实复现RF registry audit误报：by_generation以四元组为key，却用input_sha字符串做成员检查；所有已登记产物均被报never registered。MAIN新增注册正例、跨版本/快照、未注册/冲突/日期过滤、真实CLI退出码7回归；先3 RED/4 PASS，修复单独registered_anchors集合后与发布事务集中37 PASS。链/hash/冲突验证未放宽。
- 定点安装首次选择新测试文件被当前runtime闭包拒绝，零安装写入；改为只同步审计程序与契约参考。测试留仓库，实际安装约定优先于历史文档推测。

## 最终归总（09:10 UTC）

- CN v3/HK v4/US v2经原独立reviewer复查，模型技术及透明条件预测可接受；三公司产品全E2E均PARTIAL，不据此签采集/Worker全部完成。逐条关闭与残留见acceptance_summary.md及各最终recheck。
- HK v3仍有质量标签错误：网易竞争背景被one_step支持而误升Games triangulated。独立复查再次FAIL，执行v4改contrary并恢复limited/confidence limitation，数值不变，v4复查通过。合法摘录、正确算术和相同分值不能替代证据角色核对。
- CN残差/售后范围已收窄；9公告59页补读，达产属地贡献300000万元目标period未知，不套邻近专利计划年份、不并入公司年营收；激励schedule仍缺。辅助公告仅SID到研究目录，不冒称FF→CWP入库。
- HK官方年报认证/真实公开日仍未完全证明；2026-10-08仅为实读可用上界。US33管理指引原季度/CC/定性边界保留，不虚造年度中点。
- 原R3微软TXT正式摘要49证据在CWP与RF当前公共read实测通过，但显式信息日read拒绝公开日unknown，本輪输入没有消费；不会把已有能力泛称不存在，也不会重复付费生成。
- 已审研究产物与来源按SHA交付RF output，原input/snapshot/manifest不改；测试TEMP237文件清理，原始资料字节保留。归档辅助错误混用两种SHA后按公开强校验器修正，不更改模型或测试成功标准。
- 后续优先修CWP-owned Dayu有界桥、FF→ET exact能力/预算/套餐诊断、SEC HTML初处理和RF证据构建/目标表达，完整施工设计在follow_up_plan.md，尚未实施。
