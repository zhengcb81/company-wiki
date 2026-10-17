# DU8-RF-COMPARISON ROOT 独立审查

## 最终结论：PASS，0 个未解决问题

- Reviewer: `/root/du8_rf_root_review`。
- 实际作者交付 `8845bc18`，作者工区全程只读；ROOT最终工程 `b41dceef6479af29e0063c439508e3710ed34c01`，接收工区干净，无未提交受审源码 delta。
- 最终12个源/测试文件工作区原始 SHA256 与 Git blob 均已核对。3个文件仅CRLF checkout / LF仓内差别，两组SHA详见同名JSON；所有内容归一换行一致。工程commit未改变独立探针审阅过的字节，提交后只做绑定，未重复不变测试。
- 此PASS涵盖比较owner/报告/兼容及独立行为验收。mainline发布、精确CI和技能同步由ROOT另记；不代表真实公司买方模型、CWP PDF/正式摘要或全项目完成。

## ROOT-RF-R1：比较verdict类型完整性遗漏（P2，已根治）

作者 `scripts/revenue_report.py` legacy分支的 `bool(actual) is bool(expected)`，以及typed行/最终ledger的dict equality，会把JSON数字0/1与布尔False/True混同。7个完整synthetic模型中，替换 `meets_target` 为对应0/1、重新封印payload/receipt/result SHA，公开 `validate_forecast_output(result,data)` 仍接受；首轮35条篡改中9条被漏过（包括重复false/0变体）。legacy本轮由旧严格identity退化；typed则是同一Python相等语义的既有遗漏。原失败JSON保留。

ROOT用统一 `_require_target_decision_identity(actual, expected, target_id)` 在typed/legacy消费owner返回行后逐scenario做singleton identity核对；不复制数值公式，不改变货币/期间/归属/容差数学，不增加授权或人工签收。

合法null实读且公开复现：typed growth `comparison_basis.base_period=None` → `not_comparable / missing_base_period / meets_target=None`，仍正确接受；不能用bool强制转换或一律拒绝null。legacy有比较行时只应bool。

## 独立行为证据

| 验证 | 结果 |
|---|---|
| 原样复放首轮探针，7完整model正常、35条重新封印篡改 | 正常7/7；篡改35/35明确ForecastInputError拒绝，原9条遗漏均修复 |
| Decimal独立手算、ledger声明绑定、季度/单位、null、兼容、回声 | 38/38 PASS |
| typed与legacy分别poison owner返回verdict、echo wrapper自证 | 4/4 PASS |

38项包括5模型的收入/目标/ratio/strict-bool手算锚点、5次coherent伪造声明tolerance均拒；季度105.84 billion ×1000=105840 million，不乘四、不造区间中点；typed合法null；超期/未建模空comparison；旧3.1/3.2/3.3 wire；双参数剥离发布答案。4项额外探针确保owner输出若被忽略只本地重算会暴露，且typed/legacy回声都无答案可读。不是仅比较两个同函数输出。

自身38项探针初稿误配schema3.3/engine3.3.0，被documented compatibility正确拒绝；查证3.3实配3.4.0后纠正审查夹具，不算工程缺陷。

## 对集中回归中测试清理的独立审查

ROOT集中回归首见559PASS/2FAIL/7SKIP：2FAIL要求 `require(comparisons == owner(...))` 内联AST形状，不允许语义等价的 `expected_rows = owner(...)`。第3个共享helper测试只扫描两个公开wrapper，真正owner在 `_validate_forecast_output`，可vacuous PASS。独立核对最终diff仅移除这3条重复/无效测试及2专用helper（142行）。所有旧gold、手算、公开CLI、篡改拒绝、owner-output-poison和withholding行为测试保留。

ROOT另新增57项参数化bool/null wire测试。首RED48FAIL/9PASS中20为新消息regex过窄；保留首次收据后仅取消错误消息匹配，正确语义RED28FAIL/29PASS时源码尚未变。最终ROOT集中28套件558PASS/7SKIP，另163subtests，26.09秒；ruff/precommit通过。此集中结果由ROOT执行，本独审不冒充自己重复执行；独立探针结果见上。减少的3条计入分母变化，不隐藏2个中间FAIL。

## 架构与门禁审查

`target_comparison`作为唯一比较入口，typed继续委托已冻结DU6数学，legacy明确保留approximately一单位floor及legacy band兼容差异；不猜测输入量级选分支。report只绑定收入/目标/期间，并消费owner的决策，双参数剥离发布答案。未发现新增private/public、私人根、授权JSON、canary、人签或逐材料许可。typed禁止调用者覆盖自有period是既有数据归属契约。旧3.1–3.3历史read兼容豁免不冒充现代input-binding。

作者handoff顶部67b15a60“最终冻结”和JSON缺最近两commit属过时叙述，不作为本次身份或通过证据；实际以完整Git历史及最终12SHA验明。ROOT接收/发布收据应指出该差异。

## 证据、隔离和清理

同名JSON记录完整SHA/命令/原问题与解决；本地证据位于 `.planning/shared-reading-production/du8-rf-reception/reviewer/`：`probe-results.json`首问题、`probe-final-results.json`、`behavioral-results.json`、`behavioral-final-results.json`、`owner-binding-results.json`和对应独立脚本。ROOT可小体积保存到交接receipt，不覆盖原始结果。

所有probe import前设置独立 `REVENUE_PUBLICATION_REGISTRY`，使用CWP自有TemporaryDirectory、Python -B/no bytecode；sentinel字节/mtime保持，临时目录finally清除。0 HTTP/供应商/收费/原件拷贝/生产配置写入/作者写入。未运行作者tools攻击脚本或初始化其CodeGraph。
