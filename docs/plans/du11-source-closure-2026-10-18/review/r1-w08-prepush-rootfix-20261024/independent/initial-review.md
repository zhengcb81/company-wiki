# W08 pre-push ROOT修复：独立初轮未通过

Conda Python3.13.9真实执行 **42项：34P/8F/0E/0skip，3.23秒**。原pre-push失败的5个精确nodeid全部通过，原17个promoted独立断言全部通过；另20个中性语法正负控有12P/8F。未跑358项或全量pre-push，也不重签W11。

绑定 `narrative_predicate_state.py` raw SHA `cf38419cb9514bd42ab51aa96f6a02d8aeb5e8ce5949d1bf54119f06f72c6ca9`。源码/旧测试/新18测试的13项运行前后SHA一致；11个旧consumer/source/test的规范化LF与HEAD blob完全一致，未把newline/stat状态误报为语义变更。所有版本和实际import见initial-receipt.json。

## I08-01：普通project名词仍被当成预测动词（P2）

最小反例：`Projects reached 384 during the reporting period.`，metric=Projects。

实际：modality=expected、period=current、observed=False、forward_outlook=True；公共policy仅给operating_plan。语法上Projects是已披露存量的主语，reached是实绩谓词，不存在预测动词。

同根因5个失败：Projects reached、Projects stood at、Our completed projects reached、Projects have increased、Projects were。当前 `_NOMINAL_PROJECT` 与 `_PROJECT_NOUN_PREDICATE` 仍依赖有限前词/后谓词分支，覆盖totaling/grew却未覆盖同类名词所有格/定量/完成等位置。应在同一owner依据目标metric/名词短语及实际谓词归属处理；保留We/Management project、is projecting与明确未来auxiliary反控，不改期待或补公司词典。

已通过负控包含真正project动词的四例、quantified noun、totaled noun，说明不能为消除这些失败而把全部project(s)一律忽略。

## I08-02：leading assumption前有状语时假设被洗成实绩（P2）

最小反例：`In this scenario, under the assumption that renewals remain stable, customers total 384.`

实际：modality=actual、has_condition=False、observed=True。`_LEADING_HYPOTHESIS.match(prior)`锚定整个prior句首；prior先有In this scenario等独立状语时，即使紧邻主断言前明确under/on/based on assumption，条件也不会生效。

三失败分别为：In this scenario, under the assumption…；For this projection, on the assumption of…；For planning, based on the assumption…。应从紧邻条件从句的边界判定其是否治理当前assertion，而非要求它是整句第一个词；继续保留rejected assumption、独立句/分号断言和真实未来条件不泄漏等正控。本轮这些控制均已通过。

## 架构、证据与恢复

CodeGraph先定位PredicateObservation与observe_metric_predicate，静态确认数量policy和revenue guidance均引用同一owner，当前delta只在该owner内；未发现两个consumer新复制模态词表。问题是该共享语法owner仍未完全泛化，不应把358相关绿覆盖中性反例。

reproducible.py.txt含完整20个新断言、原5精确nodeid提取、原17入口、禁网sitecustomize与清理步骤；无需隐式外部fixture。运行命令：

```powershell
& 'C:/Miniconda/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w08-prepush-rootfix-20261024/independent/reproducible.py.txt'
```

该历史命令会写initial-*，修复后复审应另用新输出名保留本轮RED。真实stdout/stderr/JUnit及receipt都在同目录。pytest实际import来自母src；所有socket/DNS均禁（含loopback），0原件、0网络、0模型。独占.planning/r1-w08-prepush-independent-20261024初始不存在，核绝对父路径后删除，本轮结束不存在。

未修改产品、原/新正式测试、Git、PWF或任何旧报告。已交ROOT修复；本复核冻结原20中性断言和RED，等待新源码SHA后有限复审，不扩变体。
