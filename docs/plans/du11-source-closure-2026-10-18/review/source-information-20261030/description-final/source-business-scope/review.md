# M2 来源业务范围：独立终审

**结论：PASS（仅 M2 限定范围），当前审查发现的问题均已修复并复验；M3 未实施、未验收。** 基线 `6894f5ee21f4c883c7c4376984c962a88f0ed076`，审查最终三个未提交文件的稳定 SHA，未修改产品、未付费、未下载、未重新解析 PDF。

## 最终验证

- 固定 21 例只读 probe：真实捕获 t3/t7 两例，以及会计、模板、问句、目标客户、已售范围、研发数量、软件功能、否定/条件/异主体边界。
- 独立限定测试 **31 passed in 12.14s**：M2 永久测试 29 例，加旧 legacy/semantic 不消费 reading value 和旧 reading_plan/1 排序两项兼容检查。详细命令、完整输出和执行前后 SHA 见 `final-tests.json`。
- 三个产品/测试文件在本次测试前后 SHA 完全一致，probe 使用的 assertion_roles SHA 也与该快照一致。
- 来源扫描费用由 6 增至 **10**，包含三个有限 composition-boundary 搜索和一个开发数量扫描，纳入现有 `READING_BUSINESS_SCAN_PASSES`，没有提高母文档 work 上限。21 例重复读取缓存的新增 work 均为 0。

## 真实材料与语义边界

| 核对项 | 最终观察 |
|---|---|
| 真实 t3 九目化学完整客户链 | support、meaningful_fact；`function_or_event` helper 仍 false，未被改造成发行人生产事件 |
| 真实 t7 已售产品和超 300 种开发 | support、meaningful_fact；前面的名词枚举不再吞掉后续开发数量，从句边界可独立处理 |
| 会计政策开发数量，中英 | context_only、不抬 material，未变成经营开发事件 |
| 开发数量模板，中英；客户/已售模板 | context_only、不抬 material |
| 问句及错误“吨”计数单位 | context_only；没有用数值存在替代闭合开发种类事实 |
| future major / 目标客户 | 不抬 observed material scope，保留为前瞻描述 |
| 真实软件功能支配会计对象 | 两个回归正例恢复 baseline operating/support；产品名中含软件的正控也通过 |
| 条件、未确认、客户行为+发行人否定 | 原文完整保留；可以有意义，不等于实际正向事实；本 probe 未产生发行人完成开发/生产的 stage relations |

这里检验的是 source scope、业务重要性和来源支持用途。`material_payload` 或语法 `function_or_event` 不是对 issuer 归属、事件已发生或数量真实性的证明。负面澄清和具体条件仍可以是重要来源内容，不能为了少误报把它们全部删除。

## 审查中发现并修复的共用根因

1. **真实客户链被首个 composition 的 target 吞掉。** 初稿只匹配“主要产品”，后续“下游客户”不能形成独立 material_scope；开发数量后接逗号也无法独立 closed。主线复用同一 composition frame 形成有限新谓词边界，真实 t3/t7 已复验。
2. **开发数量仅凭泛化对象就升级。** 中英会计政策、模板示例误入经营事实。主线修复 governing 会计对象及模板主谓语义，永久负对照与独立 probe 已通过。
3. **prospective 仅识别紧邻修饰词。** “future major customers”漏过；改为有限名词修饰链后中英负对照通过。
4. **会计过滤一度误伤软件功能。** “Our software provides accounting policy management tools.”和“Our software identifies accounting policies and automates compliance.”曾从 baseline support 回归 context_only。主线保留实际软件谓词对会计对象的支配后，两例恢复 True→True，未靠取消会计负对照解决。

这些是 source owner 的共用语法/范围修复，没有在 SourceCard 重新分类，没有用公司名或材料名补词。初轮和中轮状态保存在 `review.json`，部分中间 probe 另保存在 `probe-result-round2.json`；不要把中间测试绿冒充最终验收。

## 稳定快照

| 文件 | SHA-256 |
|---|---|
| `assertion_roles.py` | `15591a3cff5c9b5ec01b1d3a10912fbd2c3a51f6d7aa96311fa57e51d3758a8d` |
| `narrative_business_policy.py` | `c9236ff506feef5f83aa1a42a4f024603de92c4121d071c87737229a4bca58fb` |
| `test_source_observed_business_scope.py` | `b7622d6d7e987e55e31f0fd6437dcf73dfbe4b2dd2613de13970f235e0521908` |

`probe.py` 从已捕获 input JSON 取真实 t3/t7，只在内存加载基线 assertion_roles 做差异对照，并写本目录 `probe-result.json`；不操作生产来源、数据库或母计划。复现命令：`python .planning/summary-quality-20261030/source-scope-independent/probe.py`。

## 明确未验收的部分

没有重新执行完整 0.8 PDF 回放、全仓审计或新模型实验。已验证的是限定旧 policy/budget 兼容测试，以及 standalone 新例的 legacy detect_business_fact 未变成事实；不能扩大成所有历史 selector 的完整回放承诺。

**M3 的 task completeness、新闻归属、单 modality、summary_assessment 和 source replay/summary semantics 区分仍未实施。** M2 来源重要性修好不能证明真实模型会保留所有业务事实，也不能把之前六条摘要的 `verified` 升级为语义通过。
