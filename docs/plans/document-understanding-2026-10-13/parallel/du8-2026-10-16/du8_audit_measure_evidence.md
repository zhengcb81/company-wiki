# DU8-AUDIT-MEASURE-EVIDENCE — 数值口径审查的实读证据连接

## 开工信息

- 工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-audit-du8-measures`
- 自有计划：`docs/plans/du8-measures-2026-10-16/task_plan.md`
- 分支：`codex/du8-audit-measures-20261016`；源码基线`f5e7f4988148a1348661d737faa92a9c5b5cd31e`，随后仅启动种子。
- 本仓没有origin；作者正常本地commit，不创建远端、不安装技能。可以现在开工，不等新CWP bundle。

## 1. 已调查的边界与目标

现`numeric_audit.py`和`financial_measure_audit.py`只核声明的金额/单位/期间/公式，明确source_truth_verified=False；`review_evidence.py`已有同次字节读、SHA/locator/pointer和共享Budget，`review_evidence_reconcile.py`已有证据覆盖观测。DU6 summary importer是摘要claim映射，不能替代金融口径的数值来源连接。本卡把两类已有能力用薄adapter接起来，形成每个数值观察的“实读了什么、哪些字段真能对照、哪些仍未知”报告。

不是重写数字parser，不是靠引用存在或一段话出现同一个数字就宣布经济口径真。尤其source_value自己瞎填、金额换币种、billion/亿、GMV/收入、stock/flow、YoY/YTD、截至日/报告窗、归属比例/净额，都可能算术自洽却来源不对。要让这种缺口可发现/可复现，不能让arithmetic PASS被循环技能误当事实通过。

## 2. 精确写范围

- 新`skills/revenue-forecast-audit/scripts/financial_measure_evidence.py`：唯一薄组合入口。
- `financial_measure_audit.py`仅可添加缺省关闭的证据adapter入口/连接，不改原算式、ledger原schema、旧输出/CLI缺省行为。
- 新`tests/test_du8_financial_measure_evidence.py`、`tests/test_du8_measure_evidence_cli.py`、`tests/fixtures/du8_measure_evidence/`。
- 新`skills/revenue-forecast-audit/references/financial-measure-evidence.md`，`SKILL.md`仅补短链接和适用范围；自有PWF。

现`review_evidence.py`/reconcile、audit_blob_store、numeric_audit、summary_review_*、四审协议、loop/scheduler、RF/CWP/FF源码、旧tests/gold、安装、配置、CI全部只读。若reader缺真实必需port，给反例与ROOT提案，不复制reader/decoder/第二预算或把已有根当private权限。

## 3. 接口必须先冻结

优先`audit_measure_evidence(ledger, evidence_map, *, reader)`，reader为调用者创建的既有EvidenceReader、同一预算，不内部重建。复用原financial-measure-ledger/1和audit_measures；只新增可选map和加法报告，不回写source_ref/ledger/原数学结果。map绑定整份ledger实际bytes SHA、observation id及既有reader reference格式；若允许field绑定，复用reader已有JSON Pointer/定位，不新写locator parser。

A读取真实reader/reconcile后冻结最小map/report字段，记录在自有INTERFACES补充；必须含ledger id、actual observation id、实际读取/定位状态、文件SHA/引用、field检查范围、budget/unread、术语/期间是否未核验。已存在金融审核结果保持source_truth_verified=False；加法报告把`bytes_verified`/`declared_field_match`/`semantic_source_truth`分开，最后一项不能因locator存在而True。对结构化且有明确字段绑定的原生JSON可逐字段精确/同币单位对照；非结构化自由文字不能用数值正则猜主体/期间，保留UNRESOLVED/NOT_CHECKED供独立审查，不误报FAIL/通过。

空映射、缺原文、缺SHA、错误pointer、重复引用/冲突映射、截断、未知source time必须是诊断，不补0、不创建人工签收。输入map即普通任务数据，不是许可文件。

## 4. 扎实测试包

A先证明“同一ledger算术PASS但原始JSON金额/币种/窗口被改或source不存在”现两工具无法联动发现的实际缺口；手工预期不来自被测算式。冻结旧金融口径CLI输入/输出回放。

B至少覆盖：billion↔亿、RMB/CNY同币别名、HKD/USD无FX、%与pp、stock/flow、annual/quarter/YTD、GMV/revenue名称、available_by/as-of、同数字多主体/两期间、字段pointer missing/type mismatch、字节篡改、相同引用缓存只读一次/累计预算、0预算/耗尽/未知输入、不修改原ledger。复用原reader实际行为，不mock掉SHA/文件读取。不能用新regex将自由文本数值自动升级为事实真。

C实际新CLI→现reader→原math audit→加法report，在独立Temp完成：一个结构化字段可核对正控、一个改币种/量纲/期间的反例、一个自由文字语义未判定、一次预算超限和重复执行。输出只引用原evidence、不复制整正文；原输入/预存sentinel前后相同，原不存在的输出/测试DB结束移除。沿现audit_contracts fresh attempt和redaction，不另建签收日志系统。

集中旧W06 measure audit、numeric、reader/reconcile、DU6 importer相关测试和新测试一次；0供应商/0网络/0真实公司预测。报告分别标合成与retained真实，不把synthetic说线上。

## 5. ROOT接收接口

作者仅交本仓代码/测试/文档；ROOT之后可把本轮真实摘要/公司审查产生的numeric ledger和实读证据map送入本工具，不需要作者读取未发布v4或主仓资料。给出一条完整可复现argv与最小输入、允许诊断/未知的解释、旧输出不变证据、清理收据。正常commit后冻结STOP，ROOT负责独审/安装/并线。
