# W17-AUDIT-COVERAGE：覆盖、内容和实际采用的分维度观察

可以立即开工，不等新摘要或W16/W18。独占目录`C:/Users/郑曾波/Projects/revenue-forecast-audit-w17-coverage`；分支`codex/w17-audit-coverage-20261025`；固定代码基线`bb41d9beda94fead3aba4bc65ed8c6dce4314e97`。`PLAN_ID=w17-audit-coverage-2026-10-25`，`PWF_PLAN_ROOT=docs/plans`。先读本仓AGENTS、自己的START_HERE、本卡及COMMON。

## 已观察到的共同问题

微软10-K原生扫描完整；112/484候选入选，HTML没有bbox；另一次零费用v4预检支持8/8必需事实；旧v5付费结果43条claim均待审、RF未采用。这些事实可以同时成立。候选未全选、语义section未映射、没有bbox、源侧金标有支持、模型语义通过、RF实际采用是不同维度，不能由一个coverage_complete或测试绿推出其他结论。

当前`summary_review_import.py`把`coverage_complete`、candidate_count、source_units、unread等原样放进scope，已有`document_status_join.py`区分prepared/read/use；应复用它们，增加可解释的报告观察，消除审查和交接反复混淆。不能重做W10逐文档join/W15可移位执行，也不能让程序替独立reviewer宣布来源真值或摘要PASS。

## 写范围

允许`skills/revenue-forecast-audit/scripts/summary_review_import.py`、`summary_review_contracts.py`、`document_status_join.py`及新`coverage_observations.py`；必要既有report/CLI接线；直接相关references和SKILL的简短操作说明；`tests/test_w17_*.py`及相关既有测试、小型fixture；本地PWF、`delivery/w17/**`。

禁止CWP/FF/RF任意写入，禁止安装副本、模型/预算/凭证变更，不跑真实公司RF或付费摘要，不改旧执行/审查报告。本仓无remote，不创建公开remote。产品代码不新增任务库、状态权威、人工许可或强制逐文档命令。

## 固定接口与验收

| ID | 要求 |
|---|---|
| O01 | A从冻结公开bundle/读取收据/原生RF消费/独立review报告列出真实JSON pointer、版本及字段语义；内部Python属性不能被假装成已公开字段。原生字段缺失则unknown，不要求修改上游schema才能完成本卡 |
| O02 | 共享一个观察owner，经已有导入/文档报告入口输出加法维度：源扫描、候选选择、layout几何、独立源侧目标支持、摘要响应语义、RF实际采用。每维保留原始值、status(observed/unknown/conflict等既有等价)、证据文件SHA/pointer、适用scope/attempt/version；没有证据不能填false或PASS |
| O03 | legacy coverage_complete保留原值；只有实际版本的公开语义明确时才能映射源扫描，不能一律解释“所有候选已读”或“摘要合格”。selected/candidate/unassigned/deferred计数有各自分母，不凭减法把所有余项叫必需事实遗漏；矛盾/负数/超界/bool当数字给诊断，不静默修数据 |
| O04 | HTML无bbox只能说明几何不可用，不能推成文字未扫描；8/8源金标有支持不等于新摘要已正确表达。只选材/编译payload的回放不能变成模型响应审查；v5排序产物不能当v4自然语言摘要。已在当前工具满足的边界复用现测试，不造第二套规则 |
| O05 | RF使用只接受当前attempt原生读取/消费引用，由现有document_status_join证明的部分沿用；prepared/read/use彼此不升级，旧attempt/无locators/同源异文档等保持unknown或诊断。不把Audit自己的观察当原生消费证据 |
| O06 | 不合成overall_pass/自动业务验收，不让缺某维度阻断其余维度或生产运行。报告明确六维各自证明范围。所有新增检查都是报告型，复用现有实读/大小限制，不加重复hash/身份校验链 |
| O07 | 从已有CLI进行实际import→source/output packet→附独立review→比较/报告的适用链；没有review时如实not_reviewed。用中性fixture验证source完整/选择不完整、无bbox但文字可读、金标支持但未摘要、旧v5与新v4、RF只prepared/只read/已use、字段缺失及冲突、旧新attempt混用。既有命令/旧bundle结果保持兼容 |
| O08 | 至少一组冻结真实公开产物的只读回放，原始字节SHA绑定；可从ROOT已提交review目录取得最小实际产物，找不到就实报unknown，不编造当前生产字段。结果只报告真实观察，测试fixture与真实回放分别标注 |

向上游缺字段的建议写interface_requests，但本卡必须能对现有输入正确给unknown，不能以新增schema未合并为等待理由。若某项核心链确实无法执行则按COMMON交INCOMPLETE并给具体证据。

## 实施与审查

A冻结六维语义和反控，B写RED后改共享观察/当前报告入口，C集中运行相关tests和实际CLI。参考命令：

```powershell
python -B -m unittest discover -s tests -p "test_w17_*.py" -v
python -B -m unittest discover -s tests -p "test_summary_review*.py" -v
python -B -m unittest discover -s tests -p "test_document_status*.py" -v
```

按本仓AGENTS在最终大节点跑全测试一次，不反复跑超时。技能结构校验使用已安装skill-creator的quick_validate.py，仅校验当前技能树；不安装/覆盖任何副本。

之后调用独立agent，直接检查完整diff和O01–O08，独立在新scratch跑一条CLI链，新增“扫描/金标均好但响应/采用未做”及一条计数冲突反例。必须修完全部问题、复测并由独立agent复查最终代码，才交接COMPLETE。初审原报告与修复后复审分开保留。

## 输出

`delivery/w17/handoff.md/json`、`review.md/json`，按O01–O08逐项证据；最终审查commit/SHA，六维字段表/示例，旧契约兼容结果、真实回放/中性fixture区别、测试前后恢复和新增字节。给ROOT定点安装文件清单，但由ROOT统一合线与安装。本卡不能把annual14 8/6/0或旧公司FAIL改为PASS。
