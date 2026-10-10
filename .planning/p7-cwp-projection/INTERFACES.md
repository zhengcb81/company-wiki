# P7共同接口与写入边界

状态：施工输入，三卡未实施。冻结的是边界/兼容行为，不把计划描述当运行能力。

## 项目与文件互斥

| Owner | source写集 | 禁止共享写入 |
|---|---|---|
| MAIN | CWP automation/**、其source-view组合/公共CLI；原根PWF及本分包汇总 | 不写P7 projection源模块、RF校准、audit技能 |
| P7-CWP-PROJECTION | CWP source_catalog/official_json_projection.py，可新official_json_snapshot.py；两新责任test与专属fixture/PWF | 所有automation、source reader/CLI/structure/layout/import、根PWF/旧reports/config/raw |
| P7-RF | RF research/evidence_roles.py/native_dependencies.py，可新calibration_binding.py和独立diagnostics CLI；指定tests/reference/SKILL小段，必要版本常量/CHANGELOG | CWP/FF/audit、RF model/period/annual/source准备、assurance/output/artifacts/config、旧PWF和CI/hooks |
| P7-AUDIT | audit单技能scripts/references/SKILL，指定四类新tests/fixture和独立PWF | 所有邻仓、安装/真实run/公司池/旧skill-buildPWF |

三工作目录物理不同；同CWP的MAIN/source卡虽然共享Git object store，改不同路径、用不同branch，不共用工作文件。提交只staging允许文件。各卡的中央SHA副本/独立PWF可记录实施，不改中央卡。新增helper仅用卡声明名；需额外修改共享源时给MAIN小patch建议，不越界施工。

## I-PROJECTION：source → MAIN

旧函数/默认producer1.0.1保留。新增两个builder keyword-only projection_version（default1.0.1，opt-in1.0.2）；load/replay从封存producer选择算法，new identity确定/深层快照隔离；SourceRef2.0/projectionref1/export1旧字段不变，真实母页/locator完整。to_dict仍普通独立JSON对象，span producer跟真实版本。

MAIN可以先继续1.0.1构建自己的subject/view；最终新generation显式选择1.0.2。source卡不改generation、artifact、任务库、model或AUTO事件；MAIN不反向修改source算法。旧sealed投影不重新排序或重签。结构parser1.0.1保持，producer升级不冒作结构解析升级。

## I-CALIBRATION：RF → audit/MAIN

operating-research/1/native input及收入计算不变；修共用scope/period/转换与输出绑定诊断。新增economic-support-diagnostics/1仅是可选只读结果：input SHA、请求年、segment/year/scenario、支持状态/关系ID/具体原因、economic_truth_inferred=false。引用端点独立于收入DAG，实际转换必须属真实目标scope/period/scenario。

Audit卡按现有4.2/3.9及来源DTO构建自己的风险协议，不等待本CLI；未来只增加可选诊断消费。native诊断语义变化如需补丁版由RF卡给真实变更、MAIN统一安装/回放验证；旧emitter原字节与pinned语义保留。不得额外升级schema或把诊断当授权/全局硬许可。

## I-AUDIT：audit → MAIN

请求生成保持原生上游合同；audit自身小索引不再定义SourceRef/Provider/费用producer。request actual bytes与capture consumed SHA一致；document/call/result准确join且一call费用不重复；quote/actor/date保真。报告v1兼容、coverage diagnostic和quality_status=not_evaluated并存，四独立agent实读才作质量结论。

自己的helper输入/输出样例在M1冻结到PWF；独立CLI fake-child可完整自测，无邻仓变化。安装只列runtime候选，MAIN同步。不清零旧budget、不改clean streak、不替换旧四报告。

## 完成与大节点

每卡：责任RED→实现GREEN→一次集中E2E/恢复及独立关键不变量检查→正常commit（有remote推自己branch）→交接。分支CI未触发记not_triggered，audit无remote记no_remote；MAIN合后使用真实exact HEAD CI。缺真实供应商/经济证据列remaining，不伪造PASS。

测试只用自有TEMP，既有初始文件保留恢复；不用完整原库备份演练。零项目外部provider/model调用，原件/config/邻仓ownerWIP/旧sealed不改。费用/cap/hash检查属于责任层技术约束，不新增人工授权、签收链或逐材料审批。
