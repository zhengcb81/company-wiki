# RF 架构质量独立只读 peer review

Reviewer：quality_ff，2026-10-13；RF 作者目录 architecture-quality-20261013/revenue-forecast。审查时HEAD仍为b9208a2117b8423f4b355dfca885aaf0d56a05bb，改造代码尚未commit，因此以以下文件SHA界定review范围；ROOT验最终交接SHA/文件内容，不把baseline HEAD当已审过最终commit。

## 范围与方法

先用canonical RF CodeGraph context定位calculator/constraints；索引尚不含新增forecast.dependencies，随后只读具体新增module与calc/research/native_dependencies/drivers/source_narrative_context consumers、native recognition/三种constraint/annual-consumption/type角色代码，以及作者新增tests。以python -B -X utf8只在内存构造11项小样本调用真实run_forecast、apply_revenue_recognition和visitor；没有运行全套、没有写作者目录/主线、没有网络/付费模型/原件读写。两次先期sum-cap扰动未保scenario ordering而被正确拒绝，已修正为合法scenario caps，未把fixture错误当项目失败。

## 结论

未发现本次改造新增的P1数值回归；native计算主体/stock-rate算式没有被visitor改写，SourceRef/叙述只增加证据链接。短carry漏读的修正有效，active recognition分支选择符合native计算，horizon<lag仍由native拒绝，scenario隔离、scope weights/elimination和shared-excerpt伪反证行为已独立验证。发现两项继承的P2依赖语义缺口，已第一时间报告ROOT；不能声称这份visitor已是“每个recognized/effective输出cell的完整因果图”。由ROOT与作者决定本轮收口或明确加入后续实施，勿把它们隐去。

## 实际观察

| 检查 | 真正native结果 | 判断 |
|---|---|---|
| lag1短carry | FY2026 recognized95，FY2027 recognized110；carry只纳入FY2026 roots | 修复有效 |
| horizon2 < lag3 | 直接apply_revenue_recognition抛Segment A lag_years exceeds forecast horizon | 既有合法边界保持；visitor不把非法carry变成默认值 |
| point-in-time/modeled_as_recognized里的inactive carry/progress字段 | 两种unused IDs均不在parameter_uses | active分支保持 |
| linked_ratio exact A→B | A全部scenario driver×1.1，B base FY2026 44→48.4；A pid不在B dependency set | P2-DEP-CROSS |
| proportional sum_cap | 合法low/base/high cap140/150/160；A所有scenario driver×1.1，B base FY2026 50→46.875；A pid不在B set | P2-DEP-CROSS |
| fixed_weights cap | B FY2026=60，B ratio weight在B依赖/不在A，ratio参数值保持不变 | 没把weight当收入金额；target scope正确 |
| scoped elimination | B FY2026≈50，B adjustment在B依赖/不在A，参数值保持 | 作用scope正确 |
| 非derived参数的input_parameter_ids metadata | ancestry只有原pid，不加入metadata pid | 不把文本metadata伪造为计算依赖 |
| 同命题不同claim ID、大小写/空白改写support/contrary | native拒绝the same excerpt cannot support and contradict the same proposition | 伪反证仍拒绝 |
| 同一table excerpt的Q2恢复/H1下滑不同事实 | native接受，fixture evidence_status=limited，给NOT_EVALUATED语义说明 | 不能仅以物理excerpt重复拒绝多事实，也未计算经济判断 |
| lag1 fiscal cell标签 | segment_roots FY2027返回0_base_2027（unrecognized tail），native FY2027 recognized来自0_base_2026 | P2-DEP-CLOCK |

## P2-DEP-CROSS：跨segment constraint传递影响未入图

位置forecast/dependencies.py:_constraint_uses与forecast/calc.py:base_segment_parameter_ids；growth_driver参数归属通过research/drivers.py:_validate_growth_driver_parameters消费。当前只把cap/ratio/本segment weight/elimination IDs挂到目标segment，没有把source_segment既有effective路径/比例cap其他成员的参数传递过去。真实linked_ratio的B=effective(A)*ratio，真实proportional cap的B=recognized(B)*cap/sum(A,B)，两例均证明A参数改变B，但B依赖集无A ID。

这在基线旧base_segment_parameter_ids也存在，所以不是本次数学回归；新统一visitor需要明确它现在只是“直接声明的输入用途”。改进应先写合法linked_ratio/proportional counterexample，再在共享dependency层描述ordered constraints的segment-output依赖边，并让输出用途/归属消费者展开这些边。不要把所有scenario、segment的参数简单混在一起；不要实现第二calculator。源clock / final effective output / 原recognition账期仍分别保留。原价/ratio绝不因为参与收入公式而重新分类为revenue数值。

## P2-DEP-CLOCK：输入期不等于recognized输出期

segment_parameter_uses给model driver的year取原输入array位置，同时output标recognized_revenue；研究segment_roots按year取这些项。lag1时FY2026 activity兑现FY2027，FY2027 activity留tail。当前标签如果解释为“输入期”可以成立，但direct_parameter_cells与季度revenue scope校验不能误用为完整recognized输出cell ancestry。短carry改进仅补出carry，没有改变driver时间映射。

改进应把input_year与output_year用途区分（或明确ParameterUse.year=input clock，并为output consumers另用共享recognition映射），按现有lag/progress/model计算表达真实影响，覆盖first carry、middle shifted activity和unrecognized tail。保留尾部activity作为真实模型输入/敏感性输入，不把它假称本预测期内已确认收入。不复制计算器，不增加来源许可。研究scope_components季度bridge有输出语义，须跟同一映射接线；这是需作者与ROOT确认的接口语义，而不是可在peer目录自行patch的改动。

## shared excerpt语义边界

机器实际保留同一claim复用/归一化结论重复的拒绝；不同命题留NOT_EVALUATED说明。它不具备自然语言同义推理，不能证明任意改写都是独立反证；本fixture limited不是对任意文档全局降级保证。资深买方economic review仍需审查多事实、不同期间和真正反证关系，现有大节点即可，不新设小节点审批或逐条许可。

## FF安装附记：diff一致不能证明runtime可运行

ROOT真实fresh-process发现.codex的10个本次新改runtime SHA一致，但旧ff_provider_cause缺build_request_diagnostic，导入失败；.agents/.claude正常。此独立review只读核对tools/sync_installs_b3.py:_scope/plan_installations/_apply：--file仅比对/写选中文件，completed确实只表示所选copy完成；低层行为按现合同工作。系统缺口是发布编排只按diff挑文件并把这项结果解释为整技能可运行，未验证此前owned dependency drift。

应让plan追加只读完整owned runtime drift与所选module imports闭包/未验证状态，清楚列scope外drift；ROOT补明确依赖清单后原子定点写入。不要默认扩大写scope，不全目录覆盖，保留configs、unknown、outputs和keys，不以manifest/hash作为许可。fresh subprocess至少验证普通入口与lazy ET路径（仅--help并不加载所有lazy模块），结合既有离线FF→ET→CWP大节点。ROOT正在做这一补救；本peer不改已提交FF，不另增审批准入链。后续施工应把这种“旧依赖drift＋partial update＋fresh import”负例固化进安装层测试。

## 审查快照

初始/最终probe中的六文件hash一致；本报告写入前核对：True。当前HEAD：`b9208a2117b8423f4b355dfca885aaf0d56a05bb`。

```json
{
  "reviewed_sha256": {
    "scripts/forecast/dependencies.py": "6f6bfe6a31182e4e693d740cfcf6f5cde576907619448f393d6e3ec9c5158789",
    "scripts/forecast/calc.py": "acd82f9236fe34ac93b6517d100dc0c515d15e0b65f782a40d047d8178caea83",
    "scripts/research/native_dependencies.py": "5f2b285a6e56191736c212ed532d3a55e49de1c753aafe67de676a70cdd498e2",
    "scripts/research/drivers.py": "5ba825340431fc6ebf1f38e8facc1b23ae4ced9222312ccd63fbfe9199a9dd1f",
    "scripts/source_narrative_context.py": "c66eb197d26bb3bbec56b52a17fcfdf582433b0ed0475e8ec33fbe7f82828759",
    "scripts/contracts/evidence.py": "909f1c7aa03e66fb740798843630ec6caac84d1c5d43351e66821b31ed97a3a8"
  },
  "current_sha256": {
    "scripts/forecast/dependencies.py": "6f6bfe6a31182e4e693d740cfcf6f5cde576907619448f393d6e3ec9c5158789",
    "scripts/forecast/calc.py": "acd82f9236fe34ac93b6517d100dc0c515d15e0b65f782a40d047d8178caea83",
    "scripts/research/native_dependencies.py": "5f2b285a6e56191736c212ed532d3a55e49de1c753aafe67de676a70cdd498e2",
    "scripts/research/drivers.py": "5ba825340431fc6ebf1f38e8facc1b23ae4ced9222312ccd63fbfe9199a9dd1f",
    "scripts/source_narrative_context.py": "c66eb197d26bb3bbec56b52a17fcfdf582433b0ed0475e8ec33fbe7f82828759",
    "scripts/contracts/evidence.py": "909f1c7aa03e66fb740798843630ec6caac84d1c5d43351e66821b31ed97a3a8"
  },
  "reviewed_matches_current": true
}
```
