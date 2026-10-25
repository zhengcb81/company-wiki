# ST-A13独立首轮审查：需要修复

范围：ROOT新named recognition scope规则、WorkBudget线性预收、cache实现身份，以及attempt03当前来源输入。未修改生产源码/原件/旧证据，未调用模型/网络。

1. **P2 所有权与回指误绑。** `本集团客户的设备维护服务属于在某一时段内履行的履约义务。`、供应商版本均产生`business_recognition_scope`；分号中另一个owner/业务插入后，后文“上述业务”仍会借给最初scope。`主营业务`、`核心业务`、`Our core services`等未具名泛称也误升级。需在同一个语法owner处理范围所有权和有界回指，不增加公司特例。
2. **P2 缓存缺新owner实现SHA。** 虚拟修改helper文件字节（不写文件）时，`decision_inventory._versions()`整体不变。policy/19隔离18→19初版，但不能隔离将来的helper-only规则变更。应纳入既有business_algorithms依赖闭包并做原生契约反例。
3. **P2 实际扫描超出线性预收。** 重复generic scope再接普通确认规则，80组仅2103字，但完整tail回指正则累计扫描85360字，超过helper8×2103=16824；40组1063字扫描21880。应保证算法线性/有界，不能仅调大固定收费系数。

attempt03：112spans/9088chars/63tasks；新公司具体Testing/Biology按时段确认段在t59，财报标题与本地“1、在某一时段内履行的履约义务”标题齐全；实际payload独立重编译SHA与model-view一致。全部旧10个PASS目标所需引句仍在。退出的原page184时点段仅metadata换ID（全文仍在）；page15总收入/15.84%段和page126通用时点判断退出。A02仍有page17收入15.84%，A13公司具体归属虽改善但精确时段/时点金额仍缺，原目标仍PARTIAL。模型语义NOT_REVIEWED/currentRF OPEN。

初始代码SHA、最小独立反例与数量证据见initial-findings.json及independent_probe.py；最终代码修复后必须重新审查并绑定新的源码/回放SHA。
