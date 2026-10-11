# W06-AUDIT-MEASURES：财务数字口径与关系审查工具

**独立开工，不等 W05/ROOT。** 工作目录 C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures；分支 codex/w06-audit-measures；基线 c0993332623637d53f059350a382d99a95ef731d。先读 AGENTS.md、skills/revenue-forecast-audit/SKILL.md、numeric_audit.py/test_numeric_audit.py、本树 docs/handoffs/w06-audit-measures/input/。PWF .planning/w06-audit-measures/。只在这棵已准备的树施工。

## 实证和完成目标

现 numeric_audit 只验证提供的 scale/FX 转换，PASS 不证明出处或经济定义。补充独立 additive 工具，让审查 agent 能显式检查币种、million/billion/万/亿、百分比/百分点、存量/流量、期间与派生关系；未知作为可见诊断，不能用一条 PASS 替代实读来源。尚未证明每类问题都在真实研究发生，不写虚假事故描述。

## 排他写集

- 新 skills/revenue-forecast-audit/scripts/financial_measure_audit.py。
- 新 references/financial-measure-audit.md（在上述技能目录中）。
- 新 tests/test_financial_measure_audit.py、test_financial_measure_audit_cli.py、tests/fixtures/financial_measures/。
- 新 tools/run_financial_measure_e2e.py；本线 PWF/交接。

现 numeric_audit.py、audit_contracts.py、audit_run.py、review_protocol.py、document_status_join.py 全部只读复用。**不写 W05 的 pool_progress/测试/合同，SKILL.md/loop/workflow/shared references 不改；ROOT 接线和安装。** 不改 RF/CWP/FF、生产账、旧 runs/goldens/真实审查。

## 接口（先写小型明文 contract，再 TDD）

新输入 schema financial-measure-ledger/1，顶层 observations/relations/as_of_date；pure `audit_measures(ledger) -> report`。CLI `financial_measure_audit.py --ledger <json> --out-root <new-attempt-root>`，用既有 new_attempt_dir/write_attempt/Redactor，不能覆盖旧输出。

每 observation 显式 id/value（有限 Decimal）/scale/currency/measure_kind(stock|flow|ratio|growth|count)/entity_key/definition/period_start/period_end/point_date/evidence_role(reported_fact|management_guidance|analyst_assumption|scenario_stress)/source_ref(source_id,locator)。量纲定义不得靠数值大小或公司名字猜；ratio 无币种，stock 用 point_date，flow 用 window，未来 guidance/assumption 合法但不能改成 actual。缺必要口径是 UNRESOLVED，结构/有限数错误是 INVALID。不重新解析身份、不造许可。

relation 引用 observation ids，固定 op：scale_conversion、fx_conversion、sum、difference、growth_rate、cagr、share；结果也是 observation。可按操作所需增加 explicit fx(from/to/rate/date/source)、years 或 rounding，contract 明确字段，不支持 eval/任意表达式。scale/FX 能复用 numeric_audit.verify_row 就复用；其他算式用 Decimal/localcontext。不能为了运行全绿暗改旧工具。

sum/difference 要相同实体/定义/币种与兼容时间口径；flow 求和可拼不重叠窗口，缺口可明确指出，不默认为0；stock 快照不得求和当收入。growth 用相同定义/币种/量纲的不同时间观察，base=0/负基数不硬套通用百分比；share denominator=0 具名不能算，分母/分子范围要明确包含关系；CAGR 需明确正基数/末值和正 years，负值/跨定义不假算。**不实现 RF 预测或自动年化，不重建 W05 日期公式。** 提供日期只是审核上下文，消费窗口由输入明示。

percent=0.01、decimal=1 与 percentage_points 是不同语义：10%→12% 为+2pp/+20%growth，不能混成+2%。必须有显示精度依据才允显式 rounding；不得允许巨大 absolute_tolerance 把数量级错误掩掉。金额的 USD billion→CNY 亿需要显式 FX，而 USD billion→USD 亿只变 scale。RMB→CNY 可做明确记录的同币种 alias；未知代码不自猜。

report schema financial-measure-audit/1，逐条 expected/actual/units/time/diagnostics、PASS/FAIL/INVALID/UNRESOLVED/NOT_CHECKED、source_ref、coverage 分母，overall 只表示声明口径/算式检查。**source_truth_verified=false、economic_reasonableness=not_evaluated 恒明确**；没有实读 source byte 不能称引用已验真。零 observations 拒伪造 coverage PASS；无 relation 只能 observation checks，不能称关系完整。未知不能归PASS。

## 三个大节点和测试

A：实读旧七类覆盖，设计 typed contract。行为 stub→RED：币种静默变换、billion当亿、pp错增长、余额当收入、重叠流量双计、0基数、CAGR期间错、巨大容差、不兼容实体/定义、指向不存在 observation、空 coverage。保留真实失败，不算 ImportError。

B：实现＋单元/集成。另测 Decimal 精度、bool/NaN、负金额允许范围、相同窗口不同定义、合法按窗口拼接、同比/环比差异、非12-31财年显示、unknown context、显式 assumptions、每 op 正负例、CLI脱敏/不覆盖。接真实 numeric_audit 并证明其旧输出不变。

```powershell
python -B -m unittest discover -s tests -p "test_financial_measure*.py" -v
python -B -m unittest discover -s tests -p "test_numeric_audit.py" -v
```

C：`python -B tools/run_financial_measure_e2e.py --owned-root <new-root> --receipt <small-json>`，起真实 CLI 子进程，三份明确 synthetic CN/HK/US ledgers；一份合法、一份单位错误、一份口径未知，检查退出码/实际 JSON/隔离/初末 sentinel。再将同 ledger 改一个 relation，旧报告不可覆盖。无网络/LLM/真实费用。最终全 audit unittest 一次，不加每小步全集门。

按 input/handoff_contract.md 给正常 commit、JSON/MD/manifest/RED/GREEN/E2E/接口/新增安装候选清单。只有实际工具行为通过才 COMPLETE；未知来源和经济质量仍交四审，不冒签。持久小记录≤8MiB，scratch恢复原状。ROOT 最后把调用加入审查技能。
