# M3-FLOW：RF 期间 flow 与机制证据角色

## 可以立即接管的工作目录

唯一执行PWF已经存在：本工作树 .planning/m3-period-evidence-20261010/。启动时 PWF_PLAN_ROOT 指向本卡RF工作树绝对路径、PLAN_ID=m3-period-evidence-20261010。直接恢复该三文件，不初始化竞争的root计划。


C:/Users/郑曾波/AppData/Local/Temp/rf-period-evidence-20261010，branch codex/m3-period-evidence-20261010，base 0c248d9a07a2dd7a2c756946d88507479d5e9d15。已核对前内置agent terminal errored，只留下 .planning/m3-period-evidence-20261010/ 的前期记录，无源码变更。使用此独立工作树，不能在主 revenue-forecast 脏树施工；不要再复制49k tracked files/整仓。

本卡任务是 RF 合同层的系统修复：明确3/6/12月flow、版本兼容、经营机制证据角色和作者工具。未来收入数字的研究校准属于后续独立研究，不以本卡代码GREEN认定预测正确。

## 必读

主文档根 C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/。本目录 INTERFACES.md、HANDOFF_TEMPLATE.md、handoff.schema.json；冻结 phase6/m3_root_remediation_2026-10-09/work_packages/W07.md；自己的已有 .planning；实际 scripts/contracts/constants.py、document.py、research/drivers.py、schema_compatibility.py 和 references/input-construction.md。结构先CodeGraph projectPath=C:/Users/郑曾波/Projects/revenue-forecast。

之前未找到 RF AGENTS.md；如果当前存在则读当前。schema-engine-matrix.json/authoring.py 并不存在，不能按猜测路径写新第二套registry；实际版本登记在 scripts/schema_compatibility.py。schema3.9/engine4.2.0只是前期提案，须依据现有矩阵正式决定，不能声称已支持。

## 已证根因

旧 time_basis 只有annual/point_in_time，至少18条半年收入流被写annual：HK十条H1和五条H2，CN三条H1。同属flow但所覆盖的3/6/12个月不同，不能只把标签换字或乘2。

drivers只排除peer_analogy，就把支持node的两个source/type计为triangulated；历史收入基数、融资背景、仅方向事实不能因此成为未来增长机制的交叉支持。

## 排他写集

只改 INTERFACES.md M3-FLOW 范围。不得改 scripts/filing_fetch_client.py、filing_upstream_cause.py、source_preparation.py（USAGE线），不得改 scripts/revenue_report.py、output、assurance/runs、SKILL.md、安装目录（MAIN/其他owner）。旧forecast/result/snapshot/report只读，不重写其中annual旧标签或triangulated旧结果。

如果需要新的output consumer/version release接线，写最小 patch/RED到 INTERFACE_CHANGE.md/MAIN_INTEGRATION_PATCH.patch 并继续授权合同部分；MAIN串行合，不新增人工许可。

## 实施顺序

1. CodeGraph确认 TIME_BASES、validate_parameters、drivers evidence的定义/callers/impact；列完整合同→authoring→calc→render→strongcheck消费者到 contract_consumer_map.json。不能只改输入validator便宣布全流程完成。
2. 新版本/feature矩阵TDD：显式period_flow与period_start/period_end，date有效和财政期间一致；annual/point_in_time旧意义不动。旧3.7/3.8与其engine pin读取、hash/结果原字节保留，新能力不得偷偷由旧schema接受。
3. flow纯规则TDD：3/6/12月、非12月财年、跨日历年；金额属于覆盖期间，H1+H2=annual、单位币种不变；point stock不乘2，3month和6month不同scope不能混。未知财期不要假补开始日。
4. 机制角色TDD：history_base/融资/peer/contrary/仅方向不算未来机制；真正同命题scope/期间的独立mechanism支持可triangulated。混合node保留实际有效支持与所有反证，不全部删除、不凭来源类别加confidence。
5. 修改authoring/helper/合同与文案，交新旧schema/engine feature例和output consumer red test/patch。签名base adjustment、input tolerance、opening residual、DAG/sensitivity正确行为保持；复用原接受证据，不重做那套模型。
6. 对真实18半年flow只读映射出新的独立最小 input 控制，列原flow ID/原字节SHA/真实起止/单位出处；日期无法证实时保留unknown，不能为了凑18PASS瞎填。不得修改原run或发表研究报告。
7. 授权scope GREEN、changed静态检查、旧版本控制后正常commit/pushbranch和exactCI；给MAIN具体runtime/ref changed SHA闭包，不自行合主线或安装。

## 独立测试包

| 类别 | 正常/反例 |
|---|---|
| Contract Unit | 合法period_flow，非法日期/缺字段/反向期间/错财年，旧schema拒绝新字段，stock/annual旧数据不变 |
| Role Unit | 旧HK history+融资反例，第二公司同结构反例；真同命题机制可支持，不同scope/期/方向和contrary不假triangulated |
| Integration | 新input→lint/hash/validate→compute涉及的纯消费者；H1+H2和signed增量/敏感性旧控制不变 |
| Compatibility | 旧3.7/3.8冻结字节和原declared engine读一致；新feature只由新明确矩阵处理 |
| MAIN output包 | render/strong recompute/registry/snapshot最小新DTO红测；本线不修改原owner source文件，等待MAIN大节点接线 |

建立 tests/test_m3_period_flow_contract.py、test_m3_evidence_roles.py、test_m3_schema_compatibility.py（新文件），以及受改旧 test_growth_driver_tree.py。运行 python -X utf8 -B -m unittest discover -s tests -p test_m3_period_flow_contract.py，另外两文件同方式；现有runner若pytest则用实际规范，不新建第二测试系统。记录真正collected，错误文件路径/环境失败不冒产品RED。

网络/provider/model费用0；独立TEMP中合成最小inputs，真实资料只读；所有初始文件SHA/配置恢复，新增测试下载不存在且不可留下。保存RED/GREEN原日志，一个工程节点汇总，不每个小步骤人审、不扩大commit检查。

## 交接和接收

自己的 .planning/m3-period-evidence-20261010/ 下 HANDOFF.md、handoff.json、INTERFACE_CHANGE.md、contract_consumer_map.json、原日志/restore receipt。输出采用本目录统一 schema。分别列contract_core、main_output_integration、real_research状态；后两项不可被合同绿写complete。

交 base/head/changedfiles/SHA/版本矩阵/真实flow映射、旧结果控制与 MAIN patch/runner。研究三年幅度和jointstress仍后续任务；不加研究信心分冒验证，不修改CWP/FF/StockWiki/IQS/其他项目。
